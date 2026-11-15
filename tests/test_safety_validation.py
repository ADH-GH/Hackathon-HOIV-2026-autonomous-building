import json
import tempfile
import unittest
from pathlib import Path

from building_ops.decisions import DecisionError, RISK_FIELDS, validate_decision
from building_ops.executor import execute
from building_ops.check import check
from tests.test_decisions import make


class SafetyValidationTest(unittest.TestCase):
    def test_reserved_metadata(self):
        for key in ('autonomy', 'requires_human_approval', 'requires_guest_consent',
                    'event_id', 'risk_context', 'service_kind', 'reason', *RISK_FIELDS):
            with self.subTest(key=key), self.assertRaises(DecisionError):
                make(extra={key: False}).finalize()
        row = make(extra={'proposed_message': 'test', 'plan_kwh': [1]}).finalize()
        self.assertEqual(row['plan_kwh'], [1])

    def test_risks_and_positive_controls(self):
        for key in RISK_FIELDS:
            row = make('adjust_room_setpoint' if key == 'outside_comfort_band' else 'flag_anomaly', **{key: True}).finalize()
            self.assertTrue(row['requires_human_approval'])
            self.assertIn('awaiting', execute([row])[0]['status'])
            bad = dict(row, autonomy='autonomous', requires_human_approval=False,
                       requires_guest_consent=False)
            with self.assertRaises(DecisionError):
                execute([bad])
        self.assertEqual(execute([make().finalize()])[0]['status'], 'executed_in_simulation')
        self.assertTrue(execute([make(autonomy='human_approval').finalize()])[0]['simulated'])

    def test_bad_records_are_controlled_failures(self):
        good = make().finalize()
        changes = [dict(timestamp_utc='not-a-timeZ'), dict(timestamp_utc='2026-02-30T00:00:00Z'),
                   dict(action='unknown'), dict(action=[]), dict(reason=4), dict(affected_assets=[[]]),
                   dict(confidence=float('nan')), dict(confidence=True), dict(evidence='wrong'),
                   dict(autonomy='human_approval'), dict(requires_guest_consent=True),
                   dict(requires_human_approval=1), dict(risk_context={}), dict(service_kind=[])]
        for row in [None, [], 5, 'x'] + [dict(good, **c) for c in changes]:
            with self.subTest(row=row):
                with self.assertRaises(DecisionError):
                    validate_decision(row)
                with tempfile.TemporaryDirectory() as tmp:
                    p = Path(tmp) / 'bad.jsonl'
                    p.write_text(json.dumps(row) + '\n')
                    self.assertFalse(check(p)['ok'])
                with self.assertRaises(DecisionError):
                    execute([good, row])
        with self.assertRaises(DecisionError):
            execute([good, good])

    def test_legacy_is_audit_only(self):
        row = make().finalize()
        del row['risk_context']
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'legacy.jsonl'
            p.write_text(json.dumps(row) + '\n')
            self.assertTrue(check(p)['ok'])
            self.assertTrue(any('risk_context' in w for w in check(p)['warnings']))
            self.assertFalse(check(p, strict_safety=True)['ok'])
        with self.assertRaises(DecisionError):
            execute([row])
        del row['autonomy']; del row['requires_guest_consent']
        validate_decision(row)

    def test_historical_files_remain_auditable(self):
        root = Path(__file__).resolve().parent.parent
        for name, count in [('decisions.jsonl', 904), ('decisions_holdout.jsonl', 1143)]:
            result = check(root / name)
            self.assertTrue(result['ok'], result['errors'])
            self.assertEqual(result['decisions'], count)
            self.assertFalse(check(root / name, strict_safety=True)['ok'])
