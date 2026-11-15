import unittest
from datetime import datetime, timezone
from building_ops.decisions import Decision, validate_decision


class TimestampPrecisionTest(unittest.TestCase):
    def test_fractional_proposal_time_is_not_rounded_before_observation(self):
        for at in ('2026-03-02T05:01:00.123456Z','2026-03-02T06:01:00.123456+01:00',
                   datetime(2026,3,2,5,1,0,123456,tzinfo=timezone.utc)):
            row=Decision(timestamp_utc=at,affected_assets=['sensor'],issue_type='data_quality',
                         action='flag_anomaly',priority='low',reason='synthetic timing control').finalize()
            self.assertEqual(row['timestamp_utc'],'2026-03-02T05:01:00.123456Z')
            validate_decision(row,require_risk_context=True)
