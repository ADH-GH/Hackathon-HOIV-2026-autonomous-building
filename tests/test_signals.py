import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from building_ops.check import check
from building_ops.decisions import Decision
from building_ops.signals import (episodes, is_night, local, meter_deltas, robust_center_spread,
                                  robust_z)

Q = timedelta(minutes=15)
T0 = datetime(2026, 1, 5, 0, 0, tzinfo=timezone.utc)


def series(values):
    return [(T0 + i * Q, v) for i, v in enumerate(values)]


class TimeTest(unittest.TestCase):
    def test_vienna_offset_follows_dst(self):
        self.assertEqual(local(datetime(2026, 1, 5, 0, 0, tzinfo=timezone.utc)).hour, 1)
        self.assertEqual(local(datetime(2026, 7, 5, 0, 0, tzinfo=timezone.utc)).hour, 2)

    def test_night_is_local(self):
        self.assertTrue(is_night(datetime(2026, 1, 5, 0, 30, tzinfo=timezone.utc)))    # 01:30 local
        self.assertFalse(is_night(datetime(2026, 1, 5, 12, 0, tzinfo=timezone.utc)))


class MeterTest(unittest.TestCase):
    def test_missing_is_not_zero(self):
        flags = [(d.value, d.flag) for d in meter_deltas(series([100, None, 104, 105]), Q)]
        self.assertEqual(flags, [(None, "missing"), (None, "missing"), (1, "ok")])

    def test_reset_is_not_consumption(self):
        d = meter_deltas(series([100, 3, 5]), Q)
        self.assertEqual([(x.value, x.flag) for x in d], [(None, "reset"), (2, "ok")])

    def test_gap_is_not_spread(self):
        pts = [(T0, 100.0), (T0 + 8 * Q, 180.0), (T0 + 9 * Q, 181.0)]
        self.assertEqual([x.flag for x in meter_deltas(pts, Q)], ["gap", "ok"])


class BaselineTest(unittest.TestCase):
    def test_too_few_points_gives_no_baseline(self):
        self.assertIsNone(robust_center_spread([1.0, None, 2.0]))

    def test_outlier_does_not_move_the_baseline(self):
        center, spread = robust_center_spread([1.0] * 20 + [500.0])
        self.assertEqual(center, 1.0)
        self.assertEqual(spread, 0.0)

    def test_floor_prevents_infinite_scores(self):
        self.assertEqual(robust_z(2.0, 1.0, 0.0, floor=0.5), 2.0)
        self.assertIsNone(robust_z(None, 1.0, 0.0, floor=0.5))


class EpisodeTest(unittest.TestCase):
    def test_one_long_incident_is_one_episode(self):
        scored = series([0, 5, 6, None, 7, 5, 0, 0])
        found = episodes(scored, threshold=4, min_points=3, max_break=2 * Q)
        self.assertEqual(len(found), 1)
        self.assertEqual((found[0].points, found[0].peak), (4, 7))

    def test_blip_is_dropped_and_break_splits(self):
        scored = series([5, 0, 0, 0, 0, 5, 5, 5])
        found = episodes(scored, threshold=4, min_points=2, max_break=Q)
        self.assertEqual([(e.points) for e in found], [3])


class CheckTest(unittest.TestCase):
    def run_check(self, rows):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "decisions.jsonl"
            path.write_text("".join(json.dumps(r) + "\n" for r in rows))
            return check(path)

    def good(self, **kw):
        base = dict(timestamp_utc="2026-01-05T06:30:00Z", affected_assets=["room_101"],
                    issue_type="water_leak", action="flag_anomaly", priority="high", reason="x",
                    evidence=["room_water.csv:R101:night_flow"])
        base.update(kw)
        return Decision(**base).finalize()

    def test_finalized_decisions_pass(self):
        report = self.run_check([self.good(), self.good(action="dispatch_technician")])
        self.assertTrue(report["ok"], report["errors"])
        self.assertEqual(report["needs_human_approval"], 1)

    def test_unsafe_autonomy_is_an_error(self):
        row = self.good(action="dispatch_technician")
        row["requires_human_approval"] = False
        self.assertFalse(self.run_check([row])["ok"])

    def test_missing_field_and_spam(self):
        row = self.good()
        del row["reason"]
        twin = dict(self.good(), event_id="dec-other")
        report = self.run_check([row, twin])
        self.assertFalse(report["ok"])
        self.assertTrue(any("spam" in w for w in report["warnings"]))


if __name__ == "__main__":
    unittest.main()
