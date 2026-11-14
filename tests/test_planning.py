import csv, json, tempfile, unittest
from pathlib import Path

from building_ops import planning
from building_ops.dataset import Dataset


def write(path, header, rows):
    with open(path, "w", newline="") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)


class PlanningTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())

    def test_budget_prices_each_interval_with_the_tariff_of_its_hour(self):
        write(self.dir / "tariff.csv", ["timestamp_utc", "price_eur_kwh", "published_utc"],
              [["2026-03-01T10:00:00Z", "0.20", "2026-02-28T12:00:00Z"], ["2026-03-01T11:00:00Z", "0.40", "2026-02-28T12:00:00Z"]])
        head = ["timestamp_utc", "building_load_kw", "hvac_electric_kw", "pv_kw", "battery_discharge_kw_signed", "battery_soc_kwh", "grid_import_kw", "grid_export_kw"]
        write(self.dir / "energy.csv", head, [["2026-03-01T10:00:00Z", "20", "8", "4", "0", "50", "16", "0"],
                                              ["2026-03-01T11:15:00Z", "20", "8", "0", "0", "50", "20", "0"],
                                              ["2026-03-01T12:00:00Z", "20", "8", "0", "0", "50", "20", "0"]])       # no price for 12:00: left out, counted
        write(self.dir / "equipment.csv", ["timestamp_utc", "asset_id", "metric", "value"], [["2026-03-01T10:00:00Z", "AHU1", "fan_kw", "2"]])
        b = planning.budget(Dataset(self.dir))
        parts = {p["key"]: p for p in b["parts"]}
        self.assertEqual(b["unpriced_intervals"], 1)
        self.assertEqual(parts["heat_pump"]["kwh"], 4)                     # 8 kW for two quarter hours
        self.assertAlmostEqual(b["load"]["kwh"], 10)
        self.assertAlmostEqual(b["bill"]["eur"], round(16 * 0.25 * 0.20 + 20 * 0.25 * 0.40))
        self.assertNotIn("water", b)                                       # no water table, no water figure

    def test_staff_counts_absences_and_measures_work_orders_against_their_slot(self):
        write(self.dir / "staff_roster.csv", ["shift_id", "resource_id", "role", "start_utc", "end_utc", "status", "status_known_utc"],
              [["S1", "CLEANER_1", "cleaner", "2026-03-01T06:00:00Z", "2026-03-01T14:30:00Z", "scheduled", "2026-02-01T00:00:00Z"],
               ["S2", "CLEANER_1", "cleaner", "2026-03-02T06:00:00Z", "2026-03-02T14:30:00Z", "sick", "2026-03-02T05:00:00Z"]])
        write(self.dir / "work_orders.csv", ["work_order_id", "created_utc", "asset_id", "type", "status", "scheduled_utc", "completed_utc", "assigned_to", "summary"],
              [["W1", "2026-03-01T08:00:00Z", "R101", "corrective", "completed", "2026-03-01T10:00:00Z", "2026-03-01T11:00:00Z", "EXTERNAL_PLUMBER", "x"],
               ["W2", "2026-03-01T08:00:00Z", "R102", "corrective", "completed", "2026-03-01T10:00:00Z", "2026-03-02T10:00:00Z", "EXTERNAL_PLUMBER", "x"]])
        (self.dir / "events.jsonl").write_text("\n".join(json.dumps(e) for e in [
            {"event_id": "E1", "timestamp_utc": "2026-03-01T09:00:00Z", "type": "cleaning_started", "room_id": "R101", "resource_id": "CLEANER_1"},
            {"event_id": "E2", "timestamp_utc": "2026-03-01T09:40:00Z", "type": "cleaning_completed", "room_id": "R101", "resource_id": "CLEANER_1"}]))
        s = planning.staff(Dataset(self.dir))
        by = {r["id"]: r for r in s["resources"]}
        self.assertEqual((by["CLEANER_1"]["shifts"], by["CLEANER_1"]["absent"], by["CLEANER_1"]["short_notice"]), (1, {"sick": 1}, 1))
        self.assertEqual((by["CLEANER_1"]["work"], by["CLEANER_1"]["median_min"]), ({"rooms cleaned": 1}, 40.0))
        self.assertEqual((by["EXTERNAL_PLUMBER"]["on_time"], by["EXTERNAL_PLUMBER"]["timed"], by["EXTERNAL_PLUMBER"]["internal"]), (1, 2, False))

    def test_missing_tables_give_no_view(self):
        self.assertIsNone(planning.budget(Dataset(self.dir)))
        self.assertIsNone(planning.staff(Dataset(self.dir)))


if __name__ == "__main__":
    unittest.main()
