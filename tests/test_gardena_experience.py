"""The complete offline acquisition-to-report positive control uses no hardware."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from building_ops.gardena_experience import doctor,demo,render
from building_ops.gardena_assessment import load
from building_ops.telemetry import TelemetryError


class ExperienceTest(unittest.TestCase):
    def test_demo_scenarios_strict_and_no_hardware(self):
        with tempfile.TemporaryDirectory() as directory,patch('building_ops.adapters.gardena_ble.NativeBackend',side_effect=AssertionError('no hardware')):
            root=Path(directory)/'demo';result=demo(root)
            report=load(root/'decisions.evidence.json')
            self.assertEqual(result['finding_count'],5)
            kinds={d['issue_type'] for d in report['decisions']}
            self.assertEqual(kinds,{'irrigation_duration','irrigation_battery','irrigation_telemetry','irrigation_flow_discrepancy'})
            affected={asset for d in report['decisions'] for asset in d['affected_assets']}
            self.assertNotIn('Normal_session',affected);self.assertNotIn('Flow_unqualified',affected)
            from building_ops.check import check
            self.assertTrue(check(root/'decisions.jsonl',strict_safety=True)['ok'])
            self.assertFalse(report['hardware_connection_verified']);self.assertFalse(report['actuator_control_enabled'])
            self.assertIn('simulated_fixture',(root/'experience.html').read_text())
            # Recovery is traceable, but no open interval bridges the disconnect.
            recovery=[r for r in report['observations'] if r['device_alias']=='Connection_recovery']
            self.assertEqual([r['connection_state'] for r in recovery],['connected','disconnected','connected'])

    def test_offline_cli_and_doctor_no_optional_imports(self):
        with tempfile.TemporaryDirectory() as directory:
            code="""import sys;from building_ops.gardena_experience import doctor,demo
assert doctor()['bluetooth_permission']=='not_verified'
demo(sys.argv[1])
assert 'bleak' not in sys.modules and 'gardena_bluetooth' not in sys.modules
"""
            result=subprocess.run([sys.executable,'-c',code,str(Path(directory)/'demo')],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
        info=doctor();self.assertEqual(info['device_connection'],'not_attempted')
        self.assertFalse(info['actuator_control_enabled'])

    def test_standalone_render_has_policy_evidence_stale_and_no_network(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'demo';demo(root)
            page=(root/'experience.html').read_text()
            for token in ('STALE','DISCONNECTED','Evidence references','watering_limit_seconds','60','Flow_discrepancy','obs-'):
                self.assertIn(token,page)
            self.assertNotIn('<script src=',page);self.assertNotIn('http://',page);self.assertNotIn('https://',page)
            report=load(root/'decisions.evidence.json')
            for row in report['observation_evidence']:self.assertIn(row['sha256'],page)
            for d in report['decisions']:self.assertIn(d['reason'],page)

    def test_reproducible_core_and_fixed_render_clock(self):
        with tempfile.TemporaryDirectory() as directory:
            one=Path(directory)/'one';two=Path(directory)/'two';demo(one);demo(two)
            for name in ('demo.jsonl','flow.jsonl','decisions.jsonl','decisions.evidence.json'):
                self.assertEqual((one/name).read_bytes(),(two/name).read_bytes())
            for root in (one,two):render(root/'decisions.evidence.json',root/'fixed.html',generated_at='2026-11-15T12:02:00Z')
            self.assertEqual((one/'fixed.html').read_bytes(),(two/'fixed.html').read_bytes())

    def test_existing_outputs_preserved_and_invalid_evidence_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)/'demo';demo(root);before=(root/'experience.html').read_bytes()
            with self.assertRaises(TelemetryError):demo(root)
            with self.assertRaises(TelemetryError):render(root/'decisions.evidence.json',root/'experience.html')
            self.assertEqual((root/'experience.html').read_bytes(),before)
            invalid=root/'invalid.json';invalid.write_text('{}')
            with self.assertRaises(TelemetryError):render(invalid,root/'no-report.html')
            self.assertFalse((root/'no-report.html').exists())
