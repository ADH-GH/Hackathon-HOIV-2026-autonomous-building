"""Independent flow assertions never turn BLE valve status into a water meter."""
import unittest
from building_ops.detectors.irrigation_monitor import analyze,MonitoringPolicy,validate_flow
from building_ops.telemetry import TelemetryError
from tests.test_irrigation_monitor import sample


def flow(row,value=2,**changes):
    return dict(device_alias='fixture',timestamp_utc=row['observed_at_utc'],flow_liters_per_minute=value,quality='VALID',
                source='independent_meter',source_mode='simulated_fixture',hydraulic_scope_confirmed=True,
                calibration_reference='synthetic_calibration',schema_version=2,units='L/min',independent=True,
                hydraulic_zone='fixture_zone',time_sync_reference='synthetic_shared_clock',timestamp_uncertainty_seconds=0,**changes)


class FlowEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.rows=[sample(t,opened=False) for t in (0,60,120)]
        self.flows=[flow(r) for r in self.rows]
        self.policy=MonitoringPolicy(flow_tolerance_l_min=.1,flow_settle_seconds=0,flow_relationships={'fixture':'fixture_zone'})

    def test_qualified_both_directions_and_negative_scope_controls(self):
        found=analyze(self.rows,policy=self.policy,flow_observations=self.flows)
        self.assertEqual(len(found),1);self.assertIn('closed_with_flow',found[0]['reason'])
        opened=[sample(t) for t in (0,60,120)]
        self.assertIn('open_without_flow',analyze(opened,policy=self.policy,flow_observations=[flow(r,0) for r in opened])[0]['reason'])
        for changes in ({'independent':False},{'hydraulic_scope_confirmed':False},{'hydraulic_zone':'different_zone'},
                        {'timestamp_uncertainty_seconds':61},{'quality':'UNAVAILABLE','flow_liters_per_minute':None}):
            with self.subTest(changes=changes):self.assertEqual(analyze(self.rows,policy=self.policy,flow_observations=[dict(f,**changes) for f in self.flows]),[])
        self.assertEqual(analyze(self.rows,policy=MonitoringPolicy(flow_tolerance_l_min=.1),flow_observations=self.flows),[])

    def test_invalid_units_time_calibration_and_conflicts_fail(self):
        for changes in ({'units':'m3/h'},{'calibration_reference':''},{'timestamp_utc':'tomorrow'},
                        {'timestamp_uncertainty_seconds':float('nan')},{'time_sync_reference':''},{'schema_version':True}):
            with self.subTest(changes=changes),self.assertRaises(TelemetryError):validate_flow(dict(self.flows[0],**changes))
        with self.assertRaises(TelemetryError):analyze(self.rows,policy=self.policy,flow_observations=self.flows+[dict(self.flows[0],flow_liters_per_minute=9)])

    def test_cached_legacy_future_and_stale_never_establish_persistence(self):
        self.assertEqual(analyze(self.rows,policy=self.policy,flow_observations=[self.flows[0]]),[])
        self.assertEqual(analyze(self.rows,policy=self.policy,flow_observations=[self.flows[-1]]),[])
        legacy=[{k:v for k,v in f.items() if k not in {'schema_version','units','independent','hydraulic_zone','time_sync_reference','timestamp_uncertainty_seconds'}} for f in self.flows]
        self.assertTrue(validate_flow(legacy[0])) # auditable, not promoted to qualified evidence
        self.assertEqual(analyze(self.rows,policy=self.policy,flow_observations=legacy),[])
        self.assertEqual(analyze(self.rows+ self.rows,policy=self.policy,flow_observations=self.flows+self.flows),analyze(self.rows,policy=self.policy,flow_observations=self.flows))
