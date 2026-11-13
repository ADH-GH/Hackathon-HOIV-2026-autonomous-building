import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from building_ops import dataset
from building_ops.dataset import Dataset, inspect, parse_ts, to_float
from building_ops.decisions import Decision
from building_ops.detectors import REGISTRY
from building_ops.executor import execute
from building_ops.pipeline import run


def write_fixture(root: Path) -> None:
    (root / "building.json").write_text(json.dumps({"rooms": []}))
    (root / "manifest.json").write_text(json.dumps({"profile": "fixture"}))
    (root / "tariff.csv").write_text(
        "timestamp_utc,price,published_utc\n"
        "2026-01-05T00:00:00Z,0.20,2026-01-04T12:00:00Z\n"
        "2026-01-06T00:00:00Z,,2026-01-05T12:00:00Z\n")
    (root / "events.jsonl").write_text('{"type": "alarm", "ts": "2026-01-05T01:00:00Z"}\n')


class DatasetTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        write_fixture(self.root)
        self.ds = Dataset(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_blank_is_missing_not_zero(self):
        rows = self.ds.table("tariff")
        self.assertIsNone(rows[1]["price"])
        self.assertIsNone(to_float(rows[1]["price"]))
        self.assertEqual(to_float(rows[0]["price"]), 0.20)

    def test_timestamps_are_utc(self):
        self.assertEqual(parse_ts("2026-01-05T01:00:00+01:00"),
                         datetime(2026, 1, 5, 0, 0, tzinfo=timezone.utc))
        self.assertIsNone(parse_ts(""))

    def test_known_at_refuses_to_guess(self):
        with self.assertRaises(KeyError):
            list(self.ds.known_at("events", datetime(2026, 1, 5, tzinfo=timezone.utc)))

    def test_known_at_hides_the_future(self):
        at = datetime(2026, 1, 5, 6, 0, tzinfo=timezone.utc)
        self.assertEqual(len(list(self.ds.known_at("tariff", at))), 1)

    def test_inspect_reports_blanks_and_missing(self):
        report = inspect(self.ds)
        self.assertEqual(report["tables"]["tariff"]["rows"], 2)
        self.assertEqual(report["tables"]["tariff"]["blank_share"], {"price": 0.5})
        self.assertIn("bookings.csv", report["missing"])
        self.assertEqual(report["events"]["types"], {"alarm": 1})


class PipelineTest(unittest.TestCase):
    def test_single_command_writes_valid_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_fixture(root)

            def fake(ds):
                yield Decision(timestamp_utc="2026-01-05T06:30:00Z", affected_assets=["room_101"],
                               issue_type="water_leak", action="request_inspection",
                               priority="high", reason="test", enters_occupied_room=True)

            REGISTRY["fake"] = (fake, True)
            try:
                out = root / "out" / "decisions.jsonl"
                actions = root / "out" / "actions.jsonl"
                summary = run(root, out, actions)
            finally:
                del REGISTRY["fake"]
            lines = [json.loads(l) for l in out.read_text().splitlines()]
            self.assertEqual(summary["decisions"], 1)
            self.assertTrue(lines[0]["requires_guest_consent"])
            trail = [json.loads(l) for l in actions.read_text().splitlines()]
            self.assertTrue(trail[0]["simulated"])
            self.assertEqual(trail[0]["status"], "awaiting_guest_consent_and_approval")

    def test_executor_runs_only_autonomous(self):
        d = Decision(timestamp_utc="2026-01-05T06:30:00Z", affected_assets=["room_101"],
                     issue_type="turnaround", action="schedule_cleaning", priority="medium",
                     reason="test").finalize()
        self.assertEqual(execute([d])[0]["status"], "executed_in_simulation")


if __name__ == "__main__":
    unittest.main()
