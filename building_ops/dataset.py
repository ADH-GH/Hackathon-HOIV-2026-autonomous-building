"""Loading the PLATO-40 dataset directory.

Rules from the brief that live here, so no detector can forget them:

- Blank means missing, never zero: empty cells become None.
- Timestamps are UTC.
- Information has a time of availability: `known_at()` filters rows to what was
  known at a decision time.

Column names come from the dataset README (PLATO-40 v2). `AVAILABILITY` maps a
table to the column that says when a row became known.
"""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from functools import cached_property
from pathlib import Path
from typing import Any, Iterator

CSV_TABLES = (
    "bookings", "access_log", "room_telemetry", "room_water", "water_main", "energy",
    "weather", "weather_forecast", "tariff", "equipment", "logistics", "staff_roster",
    "work_orders", "guest_requests",
)
JSON_FILES = ("building", "manifest")
EVENTS_FILE = "events.jsonl"

# table -> column holding the time the row became known (dataset README, "Time of
# availability"). Tables without an entry are observations stamped at their own
# timestamp_utc; known_at() refuses to guess for them.
AVAILABILITY: dict[str, str] = {
    "bookings": "created_utc",
    "tariff": "published_utc",
    "weather_forecast": "issued_utc",
    "staff_roster": "status_known_utc",
    "work_orders": "created_utc",
}

Row = dict[str, Any]


def parse_ts(value: str | None) -> datetime | None:
    """ISO 8601 to an aware UTC datetime; None for blank."""
    if value is None or value == "":
        return None
    ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)  # the brief: timestamps are UTC
    return ts.astimezone(timezone.utc)


def to_float(value: Any) -> float | None:
    """A number, or None for blank or unparseable. Never 0 for missing."""
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class Dataset:
    def __init__(self, data_dir: str | Path):
        self.dir = Path(data_dir)
        if not self.dir.is_dir():
            raise FileNotFoundError(f"data directory not found: {self.dir}")

    def has(self, name: str) -> bool:
        return self._path(name).is_file()

    def _path(self, name: str) -> Path:
        if name in JSON_FILES:
            return self.dir / f"{name}.json"
        if name == "events":
            return self.dir / EVENTS_FILE
        return self.dir / f"{name}.csv"

    @cached_property
    def building(self) -> dict[str, Any]:
        return json.loads(self._path("building").read_text(encoding="utf-8"))

    @cached_property
    def manifest(self) -> dict[str, Any]:
        return json.loads(self._path("manifest").read_text(encoding="utf-8"))

    def rows(self, table: str) -> Iterator[Row]:
        """Stream a CSV table. Blank cells are None."""
        with self._path(table).open(newline="", encoding="utf-8") as fh:
            for raw in csv.DictReader(fh):
                yield {k: (v if v != "" else None) for k, v in raw.items()}

    def table(self, table: str) -> list[Row]:
        return list(self.rows(table))

    def events(self) -> Iterator[Row]:
        with self._path("events").open(encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    yield json.loads(line)

    def known_at(self, table: str, at: datetime) -> Iterator[Row]:
        """Rows of `table` that were already known at decision time `at`."""
        column = AVAILABILITY.get(table)
        if column is None:
            raise KeyError(
                f"no availability column configured for {table!r}; "
                "set it in dataset.AVAILABILITY from the dataset README")
        for row in self.rows(table):
            known = parse_ts(row.get(column))
            if known is not None and known <= at:
                yield row


def inspect(ds: Dataset) -> dict[str, Any]:
    """What is in the directory: files, columns, row counts, share of blank cells."""
    report: dict[str, Any] = {"dir": str(ds.dir), "tables": {}, "missing": []}
    for name in JSON_FILES:
        if ds.has(name):
            data = getattr(ds, name)
            report[name] = sorted(data) if isinstance(data, dict) else type(data).__name__
        else:
            report["missing"].append(f"{name}.json")
    for table in CSV_TABLES:
        if not ds.has(table):
            report["missing"].append(f"{table}.csv")
            continue
        count, blanks, columns = 0, {}, []
        for row in ds.rows(table):
            if not columns:
                columns = list(row)
                blanks = dict.fromkeys(columns, 0)
            count += 1
            for key, value in row.items():
                if value is None:
                    blanks[key] += 1
        report["tables"][table] = {
            "rows": count,
            "columns": columns,
            "blank_share": {k: round(v / count, 4) for k, v in blanks.items() if v and count},
        }
    if ds.has("events"):
        types: dict[str, int] = {}
        keys: set[str] = set()
        for event in ds.events():
            keys.update(event)
            kind = str(event.get("type", event.get("event_type", "?")))
            types[kind] = types.get(kind, 0) + 1
        report["events"] = {"rows": sum(types.values()), "keys": sorted(keys), "types": types}
    else:
        report["missing"].append(EVENTS_FILE)
    return report
