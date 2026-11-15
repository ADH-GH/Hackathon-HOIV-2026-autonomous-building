"""Optional HA discovery/mapping and bounded cached-state shadow collection."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import time
import subprocess

from .adapters.http_readonly import MAX_BYTES, decode, finite
from .gardena import Reader, entity_id, normalize, CumulativeFlow, detect
from .decisions import Decision
from .telemetry import TelemetryError, alias, timestamp, utc

POLICY=dict(max_age_seconds=180,max_skew_seconds=60,max_gap_seconds=120,
            persistence_seconds=60,settle_seconds=30,flow_tolerance_l_min=.1,battery_low_percent=20)
DIAGNOSTICS={'active_watering','remaining_open_seconds','battery_percent'}


def validate_mapping(config):
    if not isinstance(config,dict) or set(config)!={'schema_version','devices'} or type(config['schema_version']) is not int or config['schema_version']!=1:
        raise TelemetryError('HA mapping schema_version 1 and devices required')
    if not isinstance(config['devices'],list) or not 1<=len(config['devices'])<=10: raise TelemetryError('map one to ten devices')
    assets,entities=set(),set()
    for device in config['devices']:
        if not isinstance(device,dict) or set(device)!={'asset_id','device_model','model_verification','entities','flow','policy'}:
            raise TelemetryError('invalid device mapping fields')
        asset=alias(device['asset_id'])
        if asset in assets: raise TelemetryError('duplicate asset alias')
        assets.add(asset)
        if device['device_model']!='1889-20' or device['model_verification'] not in ('owner_declared','unknown'):
            raise TelemetryError('model must be 1889-20, explicitly owner-declared or unknown, never authenticated by entity naming')
        bindings=device['entities']
        if not isinstance(bindings,dict) or 'valve_state' not in bindings or not set(bindings)<={'valve_state'}|DIAGNOSTICS:
            raise TelemetryError('explicit valve and supported optional diagnostic mappings required')
        policy=device['policy']
        if not isinstance(policy,dict) or set(policy)!=set(POLICY) or any(not finite(v) or v<0 or v>86400 for v in policy.values()):
            raise TelemetryError('all monitoring policy values must be explicitly finite, nonnegative and bounded')
        if min(policy[k] for k in ('max_age_seconds','max_gap_seconds'))<=0 or policy['battery_low_percent']>100:
            raise TelemetryError('invalid freshness, coverage or battery policy')
        configured=list(bindings.values()); flow=device['flow']
        if flow is not None:
            if not isinstance(flow,dict) or set(flow)!={'entity_id','kind','independent','hydraulic_scope_confirmed','calibration_reference','max_interval_seconds'}:
                raise TelemetryError('invalid independent flow mapping')
            if flow['kind'] not in ('rate','cumulative') or any(type(flow[k]) is not bool for k in ('independent','hydraulic_scope_confirmed')):
                raise TelemetryError('explicit flow kind and Boolean scope declarations required')
            if flow['calibration_reference'] is not None and (not isinstance(flow['calibration_reference'],str) or not 0<len(flow['calibration_reference'])<=128):
                raise TelemetryError('short calibration reference or null required')
            if not finite(flow['max_interval_seconds']) or not 0<flow['max_interval_seconds']<=86400: raise TelemetryError('bounded cumulative interval policy required')
            if entity_id(flow['entity_id']).split('.')[0]!='sensor': raise TelemetryError('flow must map a separate sensor entity')
            configured.append(flow['entity_id'])
        for key,value in bindings.items():
            domain=entity_id(value).split('.')[0]
            if key=='valve_state' and domain not in {'valve','switch'} or key!='valve_state' and domain not in {'sensor','binary_sensor','switch'}:
                raise TelemetryError('entity domain does not support the mapped metric')
        for value in configured:
            entity_id(value)
            if value in entities: raise TelemetryError('an entity cannot be reused across metric or asset scopes')
            entities.add(value)
    return config


def flow_qualified(device):
    flow=device['flow']
    return bool(flow and flow['independent'] and flow['hydraulic_scope_confirmed'] and flow['calibration_reference'])


def candidates(states, *, reveal=False):
    found=[]
    for state in states:
        entity=entity_id(state.get('entity_id')); attributes=state.get('attributes',{})
        if not isinstance(attributes,dict): continue
        domain=entity.split('.')[0]; unit=attributes.get('unit_of_measurement'); dc=attributes.get('device_class')
        metrics=[]
        if domain in {'valve','switch'}: metrics.append('valve_state')
        if domain=='binary_sensor': metrics.append('active_watering')
        if domain=='sensor':
            if dc=='battery' and unit=='%':metrics.append('battery_percent')
            if unit in ('s','min'):metrics.append('remaining_open_seconds')
            if unit in ('L/min','L/h','L/s','m³/h','m3/h'):metrics.append('flow_rate_candidate')
            if unit in ('L','m³','m3') and attributes.get('state_class') in ('total','total_increasing'):metrics.append('cumulative_volume_candidate')
        if metrics:
            row=dict(entity_sha256=hashlib.sha256(entity.encode()).hexdigest(),metric_candidates=metrics,
                     model_verification='not_established_by_state_api')
            if reveal:row['entity_id']=entity
            found.append(row)
    return sorted(found,key=lambda row:row['entity_sha256'])


def validate_frames(frames):
    if not isinstance(frames,list) or not 1<=len(frames)<=1000: raise TelemetryError('one to 1000 snapshots required')
    seen={}; output=[]
    for frame in frames:
        if not isinstance(frame,dict) or not {'received_utc','states'}<=set(frame)<= {'received_utc','states','transport'}:
            raise TelemetryError('each frame needs receipt UTC and state list or null')
        at=utc(timestamp(frame['received_utc']));states=frame['states']
        transport=frame.get('transport',{})
        if not isinstance(transport,dict) or not set(transport)<={'state','attempts','reason','http_status','payload_sha256'}:
            raise TelemetryError('unsupported transport metadata')
        if transport.get('state','file_import') not in ('received','unavailable','invalid_payload','file_import','not_read'):
            raise TelemetryError('invalid transport state')
        if transport.get('attempts') is not None and (type(transport['attempts']) is not int or not 0<=transport['attempts']<=3):
            raise TelemetryError('invalid retry count')
        if transport.get('reason') is not None and (not isinstance(transport['reason'],str) or len(transport['reason'])>256):
            raise TelemetryError('invalid transport reason')
        if transport.get('http_status') is not None and (type(transport['http_status']) is not int or not 100<=transport['http_status']<=599):
            raise TelemetryError('invalid HTTP status')
        sha=transport.get('payload_sha256')
        if sha is not None and (not isinstance(sha,str) or len(sha)!=64 or any(c not in '0123456789abcdef' for c in sha)):
            raise TelemetryError('invalid payload hash')
        if states is not None:
            if not isinstance(states,list) or len(states)>10000: raise TelemetryError('bounded state objects required')
            ids=set()
            for state in states:
                if not isinstance(state,dict):raise TelemetryError('state objects required')
                entity=entity_id(state.get('entity_id'))
                if entity in ids:raise TelemetryError('duplicate entity in one snapshot')
                ids.add(entity)
        try: digest=hashlib.sha256(json.dumps(frame,sort_keys=True,allow_nan=False).encode()).hexdigest()
        except (ValueError,TypeError,OverflowError) as exc: raise TelemetryError('snapshot must contain finite JSON values') from exc
        if at in seen:
            if seen[at]!=digest:raise TelemetryError('conflicting snapshots at one receipt time')
            continue
        seen[at]=digest;output.append(dict(frame,received_utc=at))
    return sorted(output,key=lambda frame:timestamp(frame['received_utc']))


def analyze_frames(frames,config,*,synthetic=False):
    validate_mapping(config);frames=validate_frames(frames)
    environment='synthetic_fixture' if synthetic else 'external_shadow'
    mode='simulated_fixture' if synthetic else 'imported_observation'
    records=[]; findings=[]; quality_report=[]
    for device in config['devices']:
        asset=device['asset_id'];policy=device['policy'];flow=device['flow'];qualified=flow_qualified(device)
        counter=CumulativeFlow(flow['max_interval_seconds']) if flow and flow['kind']=='cumulative' else None
        asset_records=[];unavailable=False;battery_low=False
        for frame in frames:
            now=timestamp(frame['received_utc']);states={s['entity_id']:s for s in frame['states'] or []}
            bindings=dict(device['entities'])
            if flow:bindings['cumulative_volume_l' if counter else 'flow_l_min']=flow['entity_id']
            batch=[]
            for metric,entity in bindings.items():
                raw=states.get(entity,dict(entity_id=entity,state='unavailable',last_reported=None,attributes={}))
                row=normalize(raw,asset=asset,metric=metric,now=now,max_age=policy['max_age_seconds'])
                row.update(environment=environment,source_mode=mode,device_model='1889-20',model_verification=device['model_verification'])
                batch.append(row)
                if metric=='cumulative_volume_l':batch.append(counter.rate(row))
            critical=[row for row in batch if row['metric']=='valve_state' or flow and row['metric']=='flow_l_min']
            bad=any(row['quality']!='valid' for row in critical)
            if bad and not unavailable:
                findings.append(Decision(timestamp_utc=now,affected_assets=[asset],issue_type='data_quality',action='flag_anomaly',priority='low',
                    episode_id=f'ha_telemetry:{asset}:{utc(now)}',reason='Mapped HA telemetry is unknown, stale or invalid. The last valve report does not establish closure or continuing water flow.',
                    evidence=[f'HA report quality:{r["metric"]}:{r["quality"]}:{r.get("reason", "")}' for r in critical],
                    extra=dict(source='gardena_ha',source_mode=mode,environment=environment,shadow_only=True)).finalize())
            unavailable=bad
            for row in batch:
                if row['metric']=='battery_percent' and row['quality']=='valid':
                    low=row['value']<policy['battery_low_percent']
                    if low and not battery_low:
                        findings.append(Decision(timestamp_utc=now,affected_assets=[asset],issue_type='irrigation_maintenance',action='flag_anomaly',priority='low',
                            episode_id=f'ha_battery:{asset}:{utc(now)}',reason=f'HA reports battery {row["value"]:.1f}% below configured monitoring threshold {policy["battery_low_percent"]}%; inspection only, not a manufacturer fault determination.',
                            evidence=[f'HA battery report:{row["source_timestamp"]}:sha256:{row["payload_sha256"]}'],
                            extra=dict(source='gardena_ha',source_mode=mode,environment=environment,shadow_only=True)).finalize())
                    battery_low=low
            asset_records.extend(batch)
        if qualified:
            findings.extend(detect(asset_records,{**policy,'hydraulic_scope_confirmed':True,'environment':environment}))
        quality_report.append(dict(asset_id=asset,model_verification=device['model_verification'],flow_configured=flow is not None,
            flow_checks_qualified_by_declaration=qualified,calibration_authenticated=False,
            reported_flow_kind=flow['kind'] if flow else None))
        records.extend(asset_records)
    return records,sorted(findings,key=lambda d:(d['timestamp_utc'],d['event_id'])),quality_report


def collect_frames(reader, config, *, samples=1,interval=60,clock=None,sleep=time.sleep):
    validate_mapping(config)
    if type(samples) is not int or not 1<=samples<=10 or not finite(interval) or not 1<=interval<=60: raise TelemetryError('choose 1..10 snapshots, interval 1..60 seconds')
    wanted=set()
    for device in config['devices']:
        wanted.update(device['entities'].values())
        if device['flow']:wanted.add(device['flow']['entity_id'])
    result=[]
    for i in range(samples):
        try:
            rows=reader.states()
            # Keep only mapped states and measurement metadata, never friendly names/context identities.
            states=[]
            for row in rows:
                if row['entity_id'] in wanted:
                    attrs=row.get('attributes',{})
                    if not isinstance(attrs,dict):raise TelemetryError('invalid state attributes')
                    states.append({k:row.get(k) for k in ('entity_id','state','last_reported','last_changed','last_updated')} |
                                  {'attributes':{k:attrs[k] for k in ('unit_of_measurement','device_class','state_class') if k in attrs}})
        except TelemetryError:
            states=None
            if reader.last_transport.get('state')=='received':reader.last_transport['state']='invalid_payload'
        now=clock() if clock else datetime.now(timezone.utc)
        result.append(dict(received_utc=utc(now),states=states,transport=dict(reader.last_transport)))
        if i+1<samples:sleep(interval)
    return result


def write_report(frames,config,*,out,synthetic=False,sources=None):
    from .artifact_io import _write_json,_write_jsonl,_atomic_text
    frames=validate_frames(frames)
    records,decisions,devices=analyze_frames(frames,config,synthetic=synthetic)
    root=Path(out)
    if root.exists() and (not root.is_dir() or any(root.iterdir())):raise TelemetryError('HA output must be a new or empty evidence directory')
    root.mkdir(parents=True,exist_ok=True)
    public=[]
    for row in records:
        public.append({k:v for k,v in row.items() if k!='entity_id'} | {'entity_id_sha256':hashlib.sha256(row['entity_id'].encode()).hexdigest()})
    _write_jsonl(root/'observations.jsonl',public);_write_jsonl(root/'decisions.jsonl',decisions)
    wanted={e for d in config['devices'] for e in d['entities'].values()} | {d['flow']['entity_id'] for d in config['devices'] if d['flow']}
    private_frames=[]
    for frame in validate_frames(frames):
        selected=[]
        for row in frame['states'] or []:
            if row['entity_id'] in wanted:
                attrs=row.get('attributes',{})
                if not isinstance(attrs,dict):attrs={}
                selected.append({k:row.get(k) for k in ('entity_id','state','last_reported','last_changed','last_updated')} | {'attributes':{k:attrs[k] for k in ('unit_of_measurement','device_class','state_class') if k in attrs}})
        private_frames.append({**frame,'states':selected if frame['states'] is not None else None})
    _write_jsonl(root/'frames.private.jsonl',private_frames)
    report=dict(schema_version=1,source='gardena_ha',execution_mode='read_only_shadow',
        environment='synthetic_fixture' if synthetic else 'external_shadow',snapshots=len(validate_frames(frames)),
        normalized_records=len(records),decisions=len(decisions),devices=devices,sources=sources or {},
        transport_failures=sum(frame['states'] is None for frame in frames),
        quality_counts={q:sum(r['quality']==q for r in records) for q in ('valid','unknown','stale','invalid')},
        physical_state_verified=False,authenticated_guest_consent=False,
        real_world_resolution_rate={'status':'not_measured','numerator':None,'denominator':None,'percentage':None},
        building_connectivity='not_demonstrated',bridge_boundary='HA may perform its own BLE clock synchronization; PLATO only reads cached REST states')
    report['qualification']='failed' if not any(r['metric']=='valve_state' and r['quality']=='valid' for r in records) else 'partial' if any(r['quality']!='valid' for r in records) else 'complete'
    project=Path(__file__).resolve().parent.parent
    try: report['code_revision']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=project,stderr=subprocess.DEVNULL,timeout=5,text=True).strip()
    except (OSError,subprocess.SubprocessError): report['code_revision']=None
    report['implementation_sha256']={name:hashlib.sha256((project/name).read_bytes()).hexdigest() for name in ('building_ops/gardena.py','building_ops/gardena_ha_cli.py','building_ops/adapters/http_readonly.py','building_ops/artifact_io.py','building_ops/decisions.py')}
    _atomic_text(root/'evidence.md',f'# Home Assistant shadow evidence\n\n{report["snapshots"]} snapshots, {len(records)} normalized records, {len(decisions)} proposals.\n\nMode: {report["environment"]}. Device model and calibration are not authenticated.\nActual flow is unavailable without a separately mapped independent sensor.\nNo control command was issued; no real-world outcome was measured.\nRaw private frames/mappings must not be published as dashboard data.\n')
    report['artifacts']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in root.iterdir() if p.is_file()}
    _write_json(root/'evidence.json',report)
    return report


def add_parser(sub):
    parser=sub.add_parser('gardena-ha',help='optional cached Home Assistant observation; never controls')
    commands=parser.add_subparsers(dest='ha_command',required=True)
    discover=commands.add_parser('discover');discover.add_argument('--show-entity-ids',action='store_true')
    collect=commands.add_parser('collect');collect.add_argument('--mapping',required=True);collect.add_argument('--out',required=True)
    collect.add_argument('--samples',type=int,default=1);collect.add_argument('--interval-seconds',type=float,default=60)
    replay=commands.add_parser('replay');replay.add_argument('--input',required=True);replay.add_argument('--mapping',required=True);replay.add_argument('--out',required=True)
    for child in (collect,replay):child.add_argument('--synthetic',action='store_true')
    for child in (discover,collect):
        child.add_argument('--url',required=True);child.add_argument('--authorize-live',action='store_true');child.add_argument('--token-env')
        child.add_argument('--attempts',type=int,default=3);child.add_argument('--timeout',type=float,default=5)
    check=commands.add_parser('check-mapping');check.add_argument('--mapping',required=True)
    template=commands.add_parser('mapping-template');template.add_argument('--asset',required=True);template.add_argument('--valve-entity',required=True)
    template.add_argument('--flow-entity');template.add_argument('--flow-kind',choices=['rate','cumulative'],default='rate');template.add_argument('--out',required=True)


def run(args):
    from .artifact_io import _write_json
    if args.ha_command=='mapping-template':
        flow=dict(entity_id=args.flow_entity,kind=args.flow_kind,independent=False,hydraulic_scope_confirmed=False,
                  calibration_reference=None,max_interval_seconds=300) if args.flow_entity else None
        config=dict(schema_version=1,devices=[dict(asset_id=args.asset,device_model='1889-20',model_verification='unknown',
                    entities={'valve_state':args.valve_entity},flow=flow,policy=dict(POLICY))])
        validate_mapping(config)
        if Path(args.out).exists():raise TelemetryError('mapping output already exists')
        _write_json(args.out,config);return {'mapping':args.out,'flow_checks_enabled':False}
    if args.ha_command in {'collect','replay','check-mapping'}:
        with Path(args.mapping).open('rb') as stream:config=validate_mapping(decode(stream.read(MAX_BYTES+1)))
        if args.ha_command=='check-mapping':return {'valid':True,'devices':len(config['devices']),'flow_qualified_by_declaration':[flow_qualified(d) for d in config['devices']]}
        target=Path(args.out)
        if target.exists() and (not target.is_dir() or any(target.iterdir())):raise TelemetryError('existing HA evidence is preserved')
    if args.ha_command in {'collect','discover'}:
        reader=Reader(args.url,live_authorized=args.authorize_live,token_env=args.token_env,attempts=args.attempts,timeout=args.timeout)
        if args.ha_command=='discover':return {'candidates':candidates(reader.states(),reveal=args.show_entity_ids),'model_verification':'not_established'}
        if args.synthetic and not reader.loopback:raise TelemetryError('synthetic transport requires literal loopback')
        frames=collect_frames(reader,config,samples=args.samples,interval=args.interval_seconds)
        sources={'mapping':str(args.mapping),'mapping_sha256':hashlib.sha256(Path(args.mapping).read_bytes()).hexdigest(),'endpoint_sha256':hashlib.sha256(args.url.encode()).hexdigest()}
    else:
        with Path(args.input).open('rb') as stream:raw=stream.read(MAX_BYTES+1)
        if len(raw)>MAX_BYTES:raise TelemetryError('snapshot file exceeds limit')
        frames=[decode(line) for line in raw.splitlines() if line.strip()]
        sources={'input':str(args.input),'input_sha256':hashlib.sha256(raw).hexdigest(),'mapping':str(args.mapping),'mapping_sha256':hashlib.sha256(Path(args.mapping).read_bytes()).hexdigest()}
    return write_report(frames,config,out=args.out,synthetic=args.synthetic,sources=sources)
