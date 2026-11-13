import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from building_ops.dataset import Dataset
from building_ops.detectors import s02_water_leak as s02

T0 = datetime(2026, 3, 1, 0, 0, tzinfo=timezone.utc)
Q = timedelta(minutes=15)
STEPS = 4 * 24 * 4          # four days
ROOMS = [f"R{100 + i}" for i in range(1, 41)]


def z(ts):
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


class Fixture:
    """Forty quiet rooms; tests add flow to one of them."""

    def __init__(self):
        self.flow = {r: [0.0] * STEPS for r in ROOMS}      # litres per interval
        self.blank = set()                                 # (room, step) readings left empty
        self.override = {}                                 # (room, step) -> raw meter value
        self.main_extra = [0.0] * STEPS
        self.events = []

    def write(self, root: Path) -> Dataset:
        totals = {r: 1000.0 for r in ROOMS}
        main = 50000.0
        with (root / "room_water.csv").open("w") as rw, (root / "water_main.csv").open("w") as wm:
            rw.write("timestamp_utc,room_id,meter_total_l\n")
            wm.write("timestamp_utc,meter_total_l\n")
            for i in range(STEPS):
                ts = z(T0 + i * Q)
                for r in ROOMS:
                    totals[r] += self.flow[r][i]
                    main += self.flow[r][i]
                    if (r, i) in self.override:
                        totals[r] = self.override[(r, i)]
                    value = "" if (r, i) in self.blank else f"{totals[r]:.1f}"
                    rw.write(f"{ts},{r},{value}\n")
                main += self.main_extra[i]
                wm.write(f"{ts},{main:.1f}\n")
        (root / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in self.events))
        return Dataset(root)


def run(fx: Fixture):
    with tempfile.TemporaryDirectory() as tmp:
        return [d.finalize() for d in s02.detect(fx.write(Path(tmp)))]


def leaks(decisions):
    return sorted({d["episode_id"] for d in decisions if d["issue_type"] == "water_leak"})


class WaterLeakTest(unittest.TestCase):
    def test_normal_operation_is_silent(self):
        fx = Fixture()
        for r in ROOMS[:10]:
            for day in range(4):
                for k in range(3):                       # a 45-minute shower every morning
                    fx.flow[r][day * 96 + 28 + k] = 40.0
        self.assertEqual(run(fx), [])

    def test_burst_is_critical_and_blocks_a_vacant_room(self):
        fx = Fixture()
        for i in range(100, 160):
            fx.flow["R104"][i] = 26.0
        found = run(fx)
        self.assertEqual(len(leaks(found)), 1)
        self.assertEqual({d["action"] for d in found}, {"flag_anomaly", "request_inspection", "block_room"})
        self.assertTrue(all(d["priority"] == "critical" for d in found))
        # decided at the reading that completes 2 h of flow, not earlier and not later
        self.assertEqual(found[0]["timestamp_utc"], z(T0 + (100 + s02.BURST_STEPS - 1) * Q))
        inspection = next(d for d in found if d["action"] == "request_inspection")
        self.assertTrue(inspection["requires_human_approval"])
        self.assertFalse(inspection["requires_guest_consent"])

    def test_quiet_leak_in_occupied_room_needs_consent(self):
        fx = Fixture()
        fx.events.append({"event_id": "E1", "timestamp_utc": z(T0), "type": "checkin",
                          "room_id": "R105", "booking_id": "BK1"})
        for i in range(50, 300):
            fx.flow["R105"][i] = 1.0
        found = run(fx)
        self.assertEqual(len(leaks(found)), 1)
        self.assertEqual({d["action"] for d in found}, {"flag_anomaly", "request_inspection", "notify_guest"})
        inspection = next(d for d in found if d["action"] == "request_inspection")
        self.assertEqual(inspection["autonomy"], "approval_and_consent")
        self.assertTrue(inspection["requires_guest_consent"])

    def test_leak_that_pauses_is_one_incident(self):
        fx = Fixture()
        for i in list(range(50, 120)) + list(range(130, 200)) + list(range(210, 280)):
            fx.flow["R106"][i] = 1.0
        self.assertEqual(len(leaks(run(fx))), 1)

    def test_long_bath_is_not_a_leak(self):
        fx = Fixture()
        for i in range(60, 60 + s02.BURST_STEPS - 3):
            fx.flow["R107"][i] = 60.0
        for i in range(200, 200 + s02.QUIET_STEPS - 7):
            fx.flow["R107"][i] = 2.0
        self.assertEqual(run(fx), [])

    def test_meter_exchange_is_not_a_leak(self):
        fx = Fixture()
        fx.override[("R108", 150)] = 0.4
        self.assertEqual(run(fx), [])

    def test_jittery_meter_is_data_quality_not_a_leak(self):
        fx = Fixture()
        for i in range(100, 300):                         # up 1.0, down 0.6, never zero
            fx.flow["R109"][i] = 1.0 if i % 2 else -0.6
        found = run(fx)
        self.assertEqual(leaks(found), [])
        self.assertEqual([(d["issue_type"], d["affected_assets"]) for d in found], [("data_quality", ["WM_R109"])])

    def test_blank_reading_is_not_zero_and_not_flow(self):
        fx = Fixture()
        for i in range(100, 100 + s02.QUIET_STEPS + 6):
            fx.flow["R110"][i] = 1.0
        fx.blank.add(("R110", 110))                       # breaks the run before it is long enough
        self.assertEqual(run(fx), [])

    def test_hidden_leak_outside_the_rooms(self):
        fx = Fixture()
        for i in range(96, STEPS):
            fx.main_extra[i] = 7.0
        found = run(fx)
        self.assertEqual(len(leaks(found)), 1)             # several nights, one incident
        self.assertEqual({tuple(d["affected_assets"]) for d in found}, {("WM_MAIN",), ("BUILDING", "WM_MAIN")})

    def test_daytime_common_area_use_is_not_a_hidden_leak(self):
        fx = Fixture()
        for day in range(4):
            for i in range(day * 96 + 30, day * 96 + 70):  # irrigation and lobby use by day
                fx.main_extra[i] = 30.0
        self.assertEqual(run(fx), [])


if __name__ == "__main__":
    unittest.main()
