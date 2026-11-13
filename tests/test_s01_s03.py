import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from building_ops.dataset import Dataset
from building_ops.detectors import s01_turnaround as s01
from building_ops.detectors import s03_energy_comfort as s03
from building_ops.detectors import s04_maintenance as s04
from building_ops.detectors import logistics
from building_ops.signals import fmt_local, local_day_time

Q = timedelta(minutes=15)


def z(ts):
    return ts.strftime("%Y-%m-%dT%H:%M:%SZ")


def write(root: Path, name: str, header: str, rows):
    (root / name).write_text(header + "\n" + "".join(",".join("" if v is None else str(v) for v in r) + "\n" for r in rows))


def base(root: Path, rooms=("R101", "R102")):
    (root / "building.json").write_text(json.dumps({"building": {"rooms": [{"id": r} for r in rooms]}}))
    write(root, "bookings.csv", "booking_id,room_id,created_utc,arrival_utc,departure_utc,guest_count,channel,status", [])
    write(root, "staff_roster.csv", "shift_id,resource_id,role,start_utc,end_utc,status,status_known_utc", [])
    write(root, "guest_requests.csv",
          "request_id,timestamp_utc,room_id,booking_id,channel,language,request_type,text,priority,response_due_utc,requires_guest_consent", [])
    write(root, "weather.csv", "timestamp_utc,outdoor_c,cloud_cover_pct", [])
    write(root, "weather_forecast.csv", "issued_utc,target_utc,outdoor_c_forecast", [])
    write(root, "tariff.csv", "timestamp_utc,price_eur_kwh,published_utc", [])
    write(root, "equipment.csv", "timestamp_utc,asset_id,metric,value", [])
    write(root, "room_telemetry.csv",
          "timestamp_utc,room_id,temperature_c,setpoint_c,humidity_pct,co2_ppm,presence,window_open,housekeeping_state", [])
    (root / "events.jsonl").write_text("")


class LocalTimeTest(unittest.TestCase):
    def test_winter_and_summer_time(self):
        self.assertEqual(fmt_local(datetime(2026, 1, 24, 11, 15, tzinfo=timezone.utc)), "2026-01-24 12:15 CET")
        self.assertEqual(fmt_local(datetime(2026, 7, 24, 11, 15, tzinfo=timezone.utc)), "2026-07-24 13:15 CEST")

    def test_local_wall_clock_to_utc(self):
        self.assertEqual(local_day_time(datetime(2026, 1, 24).date(), 7), datetime(2026, 1, 24, 6, 0, tzinfo=timezone.utc))
        self.assertEqual(local_day_time(datetime(2026, 7, 24).date(), 7), datetime(2026, 7, 24, 5, 0, tzinfo=timezone.utc))


class WaitingGuestTest(unittest.TestCase):
    def run_events(self, events, roster):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base(root)
            write(root, "staff_roster.csv", "shift_id,resource_id,role,start_utc,end_utc,status,status_known_utc", roster)
            (root / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
            return [d.finalize() for d in s01.detect(Dataset(root))]

    def test_free_cleaner_is_assigned_and_robot_never_releases(self):
        day = "2026-01-24"
        roster = [("S1", "CLEANER_2", "cleaner", f"{day}T06:00:00Z", f"{day}T14:30:00Z", "scheduled", "2026-01-01T00:00:00Z"),
                  ("S2", "CLEANER_1", "cleaner", f"{day}T06:00:00Z", f"{day}T14:30:00Z", "sick", f"{day}T05:30:00Z")]
        events = [
            {"event_id": "E1", "timestamp_utc": f"{day}T11:15:00Z", "type": "arrival_waiting_room", "room_id": "R101", "booking_id": "BK1"},
            {"event_id": "E2", "timestamp_utc": f"{day}T11:30:00Z", "type": "robot_floor_cleaning_completed", "room_id": "R101", "resource_id": "ROBOT_1"},
            {"event_id": "E3", "timestamp_utc": f"{day}T11:30:00Z", "type": "cleaning_started", "room_id": "R101", "resource_id": "CLEANER_2"},
            {"event_id": "E4", "timestamp_utc": f"{day}T12:15:00Z", "type": "cleaning_completed", "room_id": "R101", "resource_id": "CLEANER_2"},
        ]
        found = self.run_events(events, roster)
        plan = next(d for d in found if d["action"] == "schedule_cleaning")
        self.assertEqual(plan["resource_id"], "CLEANER_2")           # the sick cleaner is never scheduled
        self.assertEqual(plan["priority"], "critical")
        release = [d for d in found if d["action"] == "release_room"]
        self.assertEqual([d["timestamp_utc"] for d in release], [f"{day}T12:15:00Z"])   # at the human cleaning, not the robot's
        self.assertIn("12:15 CET", plan["reason"] + release[0]["reason"])

    def test_no_cleaner_in_the_evening_asks_for_on_call_approval(self):
        events = [{"event_id": "E1", "timestamp_utc": "2026-01-24T15:00:00Z", "type": "arrival_waiting_room",
                   "room_id": "R101", "booking_id": "BK1"}]
        found = self.run_events(events, [])
        ask = next(d for d in found if d["action"] == "request_human_approval")
        self.assertTrue(ask["requires_human_approval"])
        self.assertEqual(ask["resource_id"], "ONCALL_1")
        self.assertFalse(any(d["action"] == "schedule_cleaning" for d in found))   # no capacity is invented


class HeatPumpTest(unittest.TestCase):
    def run_hp(self, factor_by_step, blank_from=None, steps=96 * 3, outdoor=-5.0):
        t0 = datetime(2026, 1, 10, 0, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base(root)
            eq, weather = [], []
            for i in range(steps):
                ts = z(t0 + i * Q)
                weather.append((ts, outdoor, 50))
                cop = (s03.COP_A + s03.COP_B * outdoor) * factor_by_step(i)
                blank = blank_from is not None and i >= blank_from
                eq.append((ts, "HP1", "status", "running"))
                eq.append((ts, "HP1", "electric_kw", None if blank else 20.0))
                eq.append((ts, "HP1", "heat_output_kw", None if blank else round(20.0 * cop, 3)))
            write(root, "equipment.csv", "timestamp_utc,asset_id,metric,value", eq)
            write(root, "weather.csv", "timestamp_utc,outdoor_c,cloud_cover_pct", weather)
            return [d.finalize() for d in s03.detect(Dataset(root))]

    def test_healthy_plant_is_silent(self):
        self.assertEqual(self.run_hp(lambda i: 1.0 + (0.02 if i % 2 else -0.02)), [])

    def test_degradation_is_one_episode_and_service_needs_approval(self):
        found = self.run_hp(lambda i: 0.85 if i >= 96 else 1.0)
        self.assertEqual(len({d["episode_id"] for d in found}), 1)
        self.assertEqual([d["action"] for d in found], ["flag_anomaly", "order_service"])   # no technician in the roster
        self.assertTrue(found[1]["requires_human_approval"])

    def test_data_gap_is_not_degradation(self):
        self.assertEqual(self.run_hp(lambda i: 1.0, blank_from=96), [])


class MaintenanceCascadeTest(unittest.TestCase):
    """Day operation 06:00-22:00 UTC at normal fan power, reduced operation at night."""

    def run_ahu(self, dp_of_day, gap_days=(), roster=(), days=14):
        t0 = datetime(2026, 7, 10, 0, 0, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base(root)
            write(root, "work_orders.csv", "work_order_id,created_utc,asset_id,type,status,scheduled_utc,completed_utc,assigned_to,summary", [])
            write(root, "staff_roster.csv", "shift_id,resource_id,role,start_utc,end_utc,status,status_known_utc", roster)
            eq = []
            for i in range(days * 96):
                ts, day, night = z(t0 + i * Q), i // 96, not 24 <= i % 96 < 88
                dp = dp_of_day(day + (i % 96) / 96)
                fan = min(5.4, 3.2 + max(0.0, dp - 100) * 0.0125)
                air = 4200.0 if dp < 280 else 4200.0 - (dp - 280) * 40
                if night:
                    dp, fan, air = dp * 0.5, 1.8, 3100.0
                eq.append((ts, "AHU1", "filter_dp_pa", None if day in gap_days else round(dp, 1)))
                eq.append((ts, "AHU1", "fan_kw", round(fan, 2)))
                eq.append((ts, "AHU1", "airflow_m3h", round(air)))
            write(root, "equipment.csv", "timestamp_utc,asset_id,metric,value", eq)
            return [d.finalize() for d in s04.detect(Dataset(root))]

    def test_slow_loading_and_night_mode_are_silent(self):
        self.assertEqual(self.run_ahu(lambda d: 150 + 1.5 * d), [])

    def test_sensor_gap_on_a_healthy_plant_is_data_quality_only(self):
        found = self.run_ahu(lambda d: 150 + 1.5 * d, gap_days=(5, 6))
        self.assertEqual([(d["issue_type"], d["priority"]) for d in found], [("data_quality", "low")])

    def test_cascade_through_a_sensor_gap_with_technician_away(self):
        away = [(f"S{i}", "TECH_1", "technician", f"2026-07-{10 + i:02d}T06:00:00Z", f"2026-07-{10 + i:02d}T14:30:00Z",
                 "vacation", "2026-06-01T00:00:00Z") for i in range(14)]
        found = self.run_ahu(lambda d: 150 + (30 * (d - 3) if d > 3 else 0), gap_days=(6, 7, 8, 9), roster=away)
        self.assertEqual(len({d["episode_id"] for d in found}), 1)
        self.assertEqual([d["stage"] for d in found if d["action"] == "flag_anomaly"], ["rising", "gap", "airflow"])
        services = [d for d in found if d["action"] != "flag_anomaly"]
        self.assertTrue(all(d["action"] == "order_service" and d["requires_human_approval"] for d in services))   # absent technician is not scheduled
        self.assertEqual(found[-1]["priority"], "critical")


class LogisticsTest(unittest.TestCase):
    """Vending stock drops one unit per guest every four hours; restock Monday and Thursday 10:00 local."""

    def run_vending(self, guests_by_day):
        t0 = datetime(2026, 3, 2, 0, 0, tzinfo=timezone.utc)          # a Monday
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base(root)
            bookings, rows, stock = [], [], 100.0
            for day, n in enumerate(guests_by_day):
                for g in range(n):
                    a = t0 + timedelta(days=day, hours=14)
                    bookings.append((f"B{day}-{g}", f"R{101 + g}", z(a - timedelta(days=20)), z(a), z(a + timedelta(hours=20)), 1, "web", "confirmed"))
            write(root, "bookings.csv", "booking_id,room_id,created_utc,arrival_utc,departure_utc,guest_count,channel,status", bookings)
            for h in range(len(guests_by_day) * 24):
                ts, day, hour = t0 + timedelta(hours=h), h // 24, h % 24
                if ts.weekday() in (0, 3) and hour == 9:
                    stock = 100.0
                here = guests_by_day[day] if hour >= 14 else (guests_by_day[day - 1] if day and hour < 10 else 0)
                stock = max(0.0, stock - here * 0.25)
                rows.append((z(ts), "VEND1", "stock_drinks", round(stock, 1)))
            write(root, "logistics.csv", "timestamp_utc,asset_id,metric,value", rows)
            return [d.finalize() for d in logistics.detect(Dataset(root))]

    def test_quiet_week_orders_nothing(self):
        self.assertEqual(self.run_vending([4] * 10), [])

    def test_full_weekend_orders_one_restock_ahead_autonomously(self):
        found = self.run_vending([4, 4, 4, 4, 30, 30, 30, 4, 4, 4])      # Friday to Sunday full
        self.assertEqual(len(found), 1)                                  # one order per service cycle
        order = found[0]
        self.assertEqual((order["action"], order["service_kind"], order["requires_human_approval"]), ("order_service", "restock", False))
        self.assertLess(order["timestamp_utc"], "2026-03-08T00:00:00Z")  # ordered before Sunday, when the machine runs dry


if __name__ == "__main__":
    unittest.main()
