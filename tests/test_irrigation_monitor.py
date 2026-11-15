import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime,timedelta,timezone

from building_ops.detectors.irrigation_monitor import MonitoringPolicy,analyze
from building_ops.telemetry import TelemetryError,observation,validate_observation

ROOT=Path(__file__).resolve().parent/'fixtures'/'gardena_ble'
T=datetime(2026,11,15,12,tzinfo=timezone.utc)

def sample(seconds=0,opened=True,**changes):
    values=dict(valve_state=opened,active_watering=opened,remaining_open_seconds=300,
                manual_watering_seconds=300,battery_percent=82,activation_reason='manual')
    values.update(changes)
    return observation(device_alias='fixture',observed_at=T+timedelta(seconds=seconds),source_mode='simulated_fixture',values=values,model='1889-20',model_verification='owner_declared')

class IrrigationTest(unittest.TestCase):
    def test_normal_and_prolonged_watering(self):
        rows=[sample(i) for i in (0,60,120,180)]
        self.assertEqual(analyze(rows),[])
        result=analyze(rows,policy=MonitoringPolicy(watering_limit_seconds=60))
        self.assertEqual([d['issue_type'] for d in result],['irrigation_duration'])
        self.assertEqual(result[0]['timestamp_utc'],'2026-11-15T12:02:00Z')
        self.assertIn('monitoring limit 60',result[0]['reason'])
        self.assertTrue(result[0]['shadow_only'])
        self.assertEqual(result,analyze(rows+rows,policy=MonitoringPolicy(watering_limit_seconds=60)))
        self.assertEqual(result,analyze(list(reversed(rows)),policy=MonitoringPolicy(watering_limit_seconds=60)))
        self.assertEqual(analyze(rows,as_of='2026-11-15T12:01:00Z',policy=MonitoringPolicy(watering_limit_seconds=60)),[])

    def test_disconnect_and_stale_keep_last_known_not_current_state(self):
        lost=observation(device_alias='fixture',observed_at=T+timedelta(seconds=60),source_mode='simulated_fixture',connection='disconnected')
        result=analyze([sample(),lost])
        self.assertEqual([d['issue_type'] for d in result],['irrigation_telemetry'])
        self.assertIn('Last usable valve state was open',result[0]['reason'])
        self.assertIn('unknown',result[0]['reason'])
        self.assertEqual(lost['valve_state'],'unknown')
        result=analyze([sample()],as_of='2026-11-15T12:04:00Z')
        self.assertEqual(result[0]['issue_type'],'irrigation_telemetry')
        self.assertIn('current state and flow remain unknown',result[0]['reason'])
        # Reconnection cannot prove an open session spanning the blind period.
        self.assertFalse(any(d['issue_type']=='irrigation_duration' for d in analyze([sample(),lost,sample(120)],policy=MonitoringPolicy(watering_limit_seconds=60))))

    def test_missing_valve_does_not_hide_battery_diagnostic(self):
        result=analyze([sample(valve_state=None,battery_percent=10)])
        self.assertEqual({d['issue_type'] for d in result},{'irrigation_battery','irrigation_telemetry'})
        self.assertTrue(all(d['action']=='flag_anomaly' for d in result))

    def test_independent_flow_qualification(self):
        policy=MonitoringPolicy(flow_tolerance_l_min=.1,flow_settle_seconds=0,flow_persistence_seconds=60)
        for opened,flow,expected in [(False,2,True),(True,0,True),(False,0,False),(True,2,False)]:
            rows=[sample(i,opened=opened) for i in (0,60,120)]
            flows=[dict(device_alias='fixture',timestamp_utc=r['observed_at_utc'],flow_liters_per_minute=flow,
                        quality='VALID',source='independent_meter',source_mode='simulated_fixture',hydraulic_scope_confirmed=True,
                        calibration_reference='synthetic_calibration') for r in rows]
            result=analyze(rows,policy=policy,flow_observations=flows)
            self.assertEqual(bool(result),expected)
            self.assertEqual(analyze(rows,policy=policy),[])
            unknown=[dict(f,quality='UNAVAILABLE',flow_liters_per_minute=None) for f in flows]
            self.assertEqual(analyze(rows,policy=policy,flow_observations=unknown),[])
            wrong=[dict(f,source_mode='physical_device_read') for f in flows]
            self.assertEqual(analyze(rows,policy=policy,flow_observations=wrong),[])
            stale=[dict(f,timestamp_utc='2026-11-15T11:00:00Z') for f in flows]
            self.assertEqual(analyze(rows,policy=policy,flow_observations=stale),[])
            misplaced=[dict(f,hydraulic_scope_confirmed=False) for f in flows]
            self.assertEqual(analyze(rows,policy=policy,flow_observations=misplaced),[])

    def test_replay_cli_and_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'decisions.jsonl'
            args=[sys.executable,'-m','building_ops','gardena','replay','--input',str(ROOT/'abnormal_duration.jsonl'),
                  '--out',str(out),'--watering-limit-seconds','60']
            r=subprocess.run(args,capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)
            first=out.read_bytes()
            report=json.loads(out.with_suffix('.evidence.json').read_text())
            self.assertEqual(report['source_modes'],['simulated_fixture'])
            self.assertEqual(report['operational_outcome'],'not_measured')
            self.assertFalse(report['hotel_data_combined'])
            r=subprocess.run(args,capture_output=True,text=True)
            self.assertNotEqual(r.returncode,0)
            self.assertEqual(first,out.read_bytes())
        for name in ('closed','watering','disconnected','stale','abnormal_duration'):
            for line in (ROOT/(name+'.jsonl')).read_text().splitlines():validate_observation(json.loads(line))
