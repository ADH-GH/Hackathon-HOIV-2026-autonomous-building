"""Room occupancy as known at a point in time, from the guest lifecycle events."""
from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict
from datetime import datetime

from .dataset import Dataset, parse_ts

OCCUPY = {"checkin", "checkin_early", "checkin_after_wait", "stay_in_progress"}
VACATE = {"checkout", "checkout_early"}


class Occupancy:
    def __init__(self, ds: Dataset):
        changes: dict[str, list[tuple[datetime, str | None]]] = defaultdict(list)
        for e in ds.events():
            kind, room, ts = e.get("type"), e.get("room_id"), parse_ts(e.get("timestamp_utc"))
            if ts is None or room is None:
                continue
            if kind in OCCUPY:
                changes[room].append((ts, e.get("booking_id") or "unknown"))
            elif kind in VACATE:
                changes[room].append((ts, None))
        self._times: dict[str, list[datetime]] = {}
        self._state: dict[str, list[str | None]] = {}
        for room, items in changes.items():
            items.sort(key=lambda x: x[0])
            self._times[room] = [t for t, _ in items]
            self._state[room] = [s for _, s in items]

    def booking(self, room: str, at: datetime) -> str | None:
        """The booking occupying `room` at `at`, or None if vacant as far as the events say."""
        times = self._times.get(room)
        if not times:
            return None
        i = bisect_right(times, at) - 1
        return self._state[room][i] if i >= 0 else None

    def occupied(self, room: str, at: datetime) -> bool:
        return self.booking(room, at) is not None
