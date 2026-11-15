"""HA cached-state boundaries, tested with synthetic files and loopback only."""
import copy
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from building_ops.gardena import Reader, normalize, CumulativeFlow, detect
from building_ops.gardena_ha_cli import validate_mapping, validate_frames, candidates, analyze_frames, collect_frames, write_report
from building_ops.telemetry import TelemetryError,timestamp
from building_ops.decisions import validate_decision

ROOT=Path(__file__).parent/'fixtures'/'gardena_ha'
CONFIG=json.loads((ROOT/'mapping.json').read_text())
FRAMES=[json.loads(line) for line in (ROOT/'rate.jsonl').read_text().splitlines()]


class HomeAssistantCompleteTest(unittest.TestCase):
    def test_malformed_imports_fail_controlled_and_duplicate_metrics_rejected(self):
        for field in ('model_verification','kind'):
            cfg=copy.deepcopy(CONFIG)
            target=cfg['devices'][0] if field=='model_verification' else cfg['devices'][0]['flow']
            target[field]=[]
            with self.subTest(field=field),self.assertRaises(TelemetryError):validate_mapping(cfg)
        for metadata in ({'state':[]},{'http_status':True},{'payload_sha256':'bad'},{'reason':{}}, {'attempts':4}):
            with self.subTest(metadata=metadata),self.assertRaises(TelemetryError):validate_frames([{**FRAMES[0],'transport':metadata}])
        malformed=copy.deepcopy(FRAMES[0]);malformed['states'][0]['state']=float('nan')
        with self.assertRaises(TelemetryError):validate_frames([malformed])
        with self.assertRaises(TelemetryError):normalize(malformed['states'][0],asset='G',metric='valve_state',now=timestamp(FRAMES[0]['received_utc']))
        row=normalize(FRAMES[0]['states'][0],asset='G',metric='valve_state',now=timestamp(FRAMES[0]['received_utc']))
        with self.assertRaises(TelemetryError):detect([row,row],{**CONFIG['devices'][0]['policy'],'hydraulic_scope_confirmed':True})

    def test_mapping_requires_explicit_unique_scope_and_optional_flow(self):
        self.assertEqual(validate_mapping(copy.deepcopy(CONFIG)),CONFIG)
        optional=copy.deepcopy(CONFIG);optional['devices'][0]['flow']=None
        self.assertEqual(analyze_frames(FRAMES,optional)[2][0]['flow_configured'],False)
        for change in ('duplicate','unknown_metric','negative','wrong_domain'):
            cfg=copy.deepcopy(CONFIG);d=cfg['devices'][0]
            if change=='duplicate':d['flow']['entity_id']=d['entities']['battery_percent']
            elif change=='unknown_metric':d['entities']['set_valve']='switch.bad'
            elif change=='negative':d['policy']['max_age_seconds']=-1
            else:d['entities']['valve_state']='button.reset'
            with self.subTest(change=change),self.assertRaises(TelemetryError):validate_mapping(cfg)

    def test_discovery_is_candidate_only_and_identifiers_are_opt_in(self):
        found=candidates(FRAMES[0]['states'])
        self.assertTrue(found)
        self.assertTrue(all('entity_id' not in row and row['model_verification']=='not_established_by_state_api' for row in found))
        self.assertTrue(any('flow_rate_candidate' in r['metric_candidates'] for r in found))
        revealed=candidates(FRAMES[0]['states'],reveal=True)
        self.assertTrue(all('entity_id' in row for row in revealed))

    def test_rate_conflicts_both_directions_atomic_frames_and_cached_reports(self):
        _,found,_=analyze_frames(FRAMES,CONFIG,synthetic=True)
        conflicts=[d for d in found if d['issue_type']=='irrigation_state_conflict']
        self.assertEqual(len(conflicts),1)
        self.assertEqual(conflicts[0]['flow_discrepancy'],'closed_with_flow')
        opposite=copy.deepcopy(FRAMES)
        for frame in opposite:
            next(s for s in frame['states'] if s['entity_id'].startswith('valve.'))['state']='open'
            next(s for s in frame['states'] if s['entity_id']=='sensor.synthetic_flow')['state']='0'
        _,found,_=analyze_frames(opposite,CONFIG)
        self.assertEqual([d['flow_discrepancy'] for d in found if d['issue_type']=='irrigation_state_conflict'],['open_without_flow'])
        matching=copy.deepcopy(FRAMES[:3]);matching[-1]['states'][-1]['state']='0'
        self.assertFalse(any(d['issue_type']=='irrigation_state_conflict' for d in analyze_frames(matching,CONFIG)[1]))
        cached=copy.deepcopy(FRAMES)
        for frame in cached:
            for state in frame['states']:state['last_reported']=FRAMES[0]['received_utc']
        self.assertFalse(any(d['issue_type']=='irrigation_state_conflict' for d in analyze_frames(cached,CONFIG)[1]))

    def test_cumulative_units_resets_gaps_and_baseline_are_qualified(self):
        frames=[json.loads(line) for line in (ROOT/'cumulative.jsonl').read_text().splitlines()]
        cfg=copy.deepcopy(CONFIG);cfg['devices'][0]['flow']['kind']='cumulative'
        records,found,_=analyze_frames(frames,cfg)
        self.assertEqual(len([d for d in found if d['issue_type']=='irrigation_state_conflict']),1)
        rates=[r for r in records if r['metric']=='flow_l_min']
        self.assertEqual(rates[0]['value'],None)
        self.assertTrue(all(abs(r['value']-2)<1e-8 for r in rates[1:]))
        counter=CumulativeFlow(120)
        raw=frames[0]['states'][-1]
        first=normalize(raw,asset='G',metric='cumulative_volume_l',now=timestamp(frames[0]['received_utc']))
        self.assertEqual(counter.rate(first)['quality'],'unknown')
        second=normalize({**raw,'state':'1','last_reported':frames[1]['received_utc']},asset='G',metric='cumulative_volume_l',now=timestamp(frames[1]['received_utc']))
        reset=counter.rate(second);self.assertEqual(reset['quality'],'invalid');self.assertIn('reset',reset['reason'])
        late={**second,'source_timestamp':'2026-03-02T00:10:00Z','value':3}
        self.assertEqual(counter.rate(late)['quality'],'unknown')
        self.assertEqual(counter.rate(late)['quality'],'unknown') # repeated time is not a zero-flow interval
        converted=normalize({**raw,'state':'.5','attributes':{'unit_of_measurement':'m³','state_class':'total_increasing'}},asset='G',metric='cumulative_volume_l',now=timestamp(frames[0]['received_utc']))
        self.assertEqual(converted['value'],500)

    def test_no_cross_asset_pairing_or_unqualified_flow_promotions(self):
        records=[]
        for frame in FRAMES:
            now=timestamp(frame['received_utc'])
            records.append(normalize(frame['states'][0],asset='A',metric='valve_state',now=now))
            records.append(normalize(frame['states'][-1],asset='B',metric='flow_l_min',now=now))
        self.assertEqual(detect(records,{**CONFIG['devices'][0]['policy'],'hydraulic_scope_confirmed':True}),[])
        for flag in ('independent','hydraulic_scope_confirmed','calibration_reference'):
            cfg=copy.deepcopy(CONFIG);cfg['devices'][0]['flow'][flag]=None if flag=='calibration_reference' else False
            self.assertFalse(any(d['issue_type']=='irrigation_state_conflict' for d in analyze_frames(FRAMES,cfg)[1]))

    def test_loss_stale_recovery_and_battery_keep_unknown_distinct(self):
        frames=copy.deepcopy(FRAMES)
        frames[1]['states']=None
        records,found,_=analyze_frames(frames,CONFIG)
        self.assertTrue(any(r['metric']=='valve_state' and r['value'] is None and r['quality']=='unknown' for r in records))
        self.assertTrue(any(d['issue_type']=='data_quality' for d in found))
        self.assertTrue(any(d['issue_type']=='irrigation_state_conflict' for d in found))
        for frame in frames:
            if frame['states']:
                next(s for s in frame['states'] if s['entity_id']=='sensor.synthetic_battery')['state']='10'
        self.assertEqual(len([d for d in analyze_frames(frames,CONFIG)[1] if d['issue_type']=='irrigation_maintenance']),1)
        stale=normalize(FRAMES[0]['states'][0],asset='A',metric='valve_state',now=timestamp('2026-03-02T01:00:00Z'))
        self.assertEqual(stale['quality'],'stale');self.assertIsNone(stale['value'])

    def test_loopback_discovery_to_decisions_retries_and_no_controls(self):
        calls=[];headers=[];number=[0];fail=[False]
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                calls.append(('GET',self.path));headers.append(self.headers.get('Authorization'))
                self.send_response(503 if fail[0] else 200);self.send_header('Content-Type','application/json');self.end_headers()
                frame=FRAMES[min(number[0],len(FRAMES)-1)];number[0]+=1
                self.wfile.write(json.dumps(frame['states']).encode())
            def do_POST(self): calls.append(('POST',self.path));self.send_error(405)
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            with patch.dict('os.environ',{'HA_TOKEN':'synthetic-secret-marker'}):
                reader=Reader(f'http://127.0.0.1:{server.server_port}')
                number[0]=0
                clock=iter(timestamp(f['received_utc']) for f in FRAMES)
                frames=collect_frames(reader,CONFIG,samples=5,interval=1,clock=lambda:next(clock),sleep=lambda _:None)
                _,found,_=analyze_frames(frames,CONFIG,synthetic=True)
                self.assertTrue(any(d['issue_type']=='irrigation_state_conflict' for d in found))
                self.assertTrue(candidates(reader.states()))
                fail[0]=True
                with patch('building_ops.adapters.http_readonly.time.sleep'):
                    missing=collect_frames(reader,CONFIG,samples=1,interval=1,clock=lambda:timestamp(FRAMES[-1]['received_utc']))
                self.assertIsNone(missing[0]['states']);self.assertEqual(missing[0]['transport']['attempts'],3)
                self.assertTrue(all(value is None for value in headers))
                self.assertTrue(all(method=='GET' and path=='/api/states' for method,path in calls))
            with self.assertRaises(TelemetryError):Reader('https://example.invalid')
        finally:server.shutdown();server.server_close();thread.join(2)

    def test_deterministic_cli_evidence_and_private_identifiers(self):
        with tempfile.TemporaryDirectory() as tmp:
            outputs=[]
            for name in ('a','b'):
                target=Path(tmp)/name
                cmd=[sys.executable,'-m','building_ops','gardena-ha','replay','--input',str(ROOT/'rate.jsonl'),
                     '--mapping',str(ROOT/'mapping.json'),'--synthetic','--out',str(target)]
                p=subprocess.run(cmd,text=True,capture_output=True);self.assertEqual(p.returncode,0,p.stderr)
                report=json.loads(p.stdout);self.assertEqual(report['real_world_resolution_rate']['status'],'not_measured')
                self.assertFalse(report['physical_state_verified'])
                exported=(target/'observations.jsonl').read_text()
                self.assertNotIn('"entity_id":',exported);self.assertNotIn('valve.synthetic_gardena',exported)
                for line in (target/'decisions.jsonl').read_text().splitlines():validate_decision(json.loads(line),require_risk_context=True)
                outputs.append({p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in target.iterdir()})
                again=subprocess.run(cmd,text=True,capture_output=True);self.assertEqual(again.returncode,1);self.assertNotIn('Traceback',again.stderr)
            self.assertEqual(*outputs)
            template=Path(tmp)/'template.json'
            p=subprocess.run([sys.executable,'-m','building_ops','gardena-ha','mapping-template','--asset','G','--valve-entity','valve.private','--out',str(template)],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr);self.assertEqual(validate_mapping(json.loads(template.read_text()))['devices'][0]['flow'],None)
