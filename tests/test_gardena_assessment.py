"""P0: CLI, export and hotel view use one policy and one result."""
import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from building_ops.gardena_assessment import assess,load,replay
from building_ops.detectors.irrigation_monitor import MonitoringPolicy
from building_ops.external_dashboard import payload
from building_ops.telemetry import TelemetryError
from tests.test_irrigation_monitor import ROOT,sample


class AssessmentTest(unittest.TestCase):
    def test_cli_custom_and_default_findings_equal_dashboard(self):
        with tempfile.TemporaryDirectory() as directory:
            for limit,count in ((60,1),(3600,0)):
                output=Path(directory)/f'{limit}.jsonl'
                result=subprocess.run([sys.executable,'-m','building_ops','gardena','replay','--input',str(ROOT/'abnormal_duration.jsonl'),
                    '--out',str(output),'--watering-limit-seconds',str(limit)],capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stderr)
                manifest=output.with_suffix('.evidence.json');report=load(manifest)
                view=payload(ROOT/'abnormal_duration.jsonl',evidence=manifest)
                self.assertEqual(len(report['decisions']),count)
                self.assertEqual(view['findings'],report['decisions'])
                self.assertEqual(view['policy'],report['monitoring_policy'])
                self.assertEqual(report,load(manifest))
                self.assertEqual(output.read_text(),''.join(json.dumps(d,sort_keys=True)+'\n' for d in report['decisions']))

    def test_fixed_stale_cutoff_and_future_exclusion(self):
        rows=[sample(),sample(120)]
        result=assess(rows,as_of='2026-11-15T12:10:00Z',code_revision='fixture')
        self.assertEqual(result,assess(rows,as_of='2026-11-15T12:10:00Z',code_revision='fixture'))
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'report.json';path.write_text(json.dumps(result))
            view=payload(evidence=path)
            self.assertEqual(view['devices'][0]['quality'],'STALE')
            self.assertEqual(view['devices'][0]['current_valve_state'],'unknown')
            self.assertEqual(view['findings'],result['decisions'])
            with self.assertRaises(TelemetryError):payload(evidence=path,as_of='2026-11-15T12:00:00Z')
        self.assertFalse(assess(rows,as_of=rows[0]['observed_at_utc'])['decisions'])

    def test_incompatible_and_missing_policy_or_hash_rejected(self):
        result=assess([sample(0),sample(120)],policy=MonitoringPolicy(watering_limit_seconds=60))
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'report.json'
            for change in ('policy','missing','decision','input','schema'):
                report=copy.deepcopy(result)
                if change=='policy':report['monitoring_policy']['watering_limit_seconds']=3600
                if change=='missing':del report['monitoring_policy']['freshness_seconds']
                if change=='decision':report['decisions']=[]
                if change=='input':report['observations'][0]['battery_percent']=1
                if change=='schema':report['schema_version']=1
                path.write_text(json.dumps(report))
                with self.subTest(change=change),self.assertRaises(TelemetryError):load(path)
            path.write_text(json.dumps(result))
            with self.assertRaises(TelemetryError):load(path,observations_path=ROOT/'closed.jsonl')

    def test_existing_destinations_and_duplicate_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)/'out.jsonl'
            replay(ROOT/'watering.jsonl',out,policy=MonitoringPolicy())
            before=out.read_bytes()
            with self.assertRaises(TelemetryError):replay(ROOT/'watering.jsonl',out,policy=MonitoringPolicy())
            self.assertEqual(out.read_bytes(),before)
        with self.assertRaises(TelemetryError):assess([sample(),dict(sample(),battery_percent=1)])
