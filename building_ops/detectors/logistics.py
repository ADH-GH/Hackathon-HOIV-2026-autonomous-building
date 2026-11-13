"""Logistics: order an extra waste pickup or vending restock before it is too late.

The regular services run on fixed weekdays (waste Tue and Fri 07:00, vending Mon
and Thu 10:00, Vienna time). An extra service can be ordered with about 24 hours
of lead time. Whether the container overflows or the machine runs dry before the
next regular visit depends on how many guests are in the house, and that is known
ahead from the bookings.

At every hourly reading, using only that reading, the past 72 hours and the
bookings created so far:

1. consumption per guest-hour over the past 72 hours,
2. projected forward over the guests booked for each coming hour,
3. if the limit is reached more than 8 hours before the next regular service and
   an extra service ordered now would still arrive at least 6 hours before that
   regular service, order it. One order per service cycle.

Ordering a waste pickup or a restock is an autonomous action in the brief.
"""
from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Iterable

from ..dataset import Dataset, parse_ts, to_float
from ..decisions import Decision
from ..signals import fmt_local, local, local_day_time

IMPLEMENTED = True

HOUR = timedelta(hours=1)
LEAD = timedelta(hours=24)            # extra service lead time (dataset README)
HISTORY = 72                          # hours used to estimate consumption per guest-hour
MIN_USEFUL = timedelta(hours=6)       # an extra visit closer than this to the regular one is not worth ordering
MIN_OUTAGE = timedelta(hours=8)       # a limit reached later than this before the regular service is tolerated
SERVICE_JUMP = {"fill_pct": -25.0, "stock": 15.0}
# The container fills in one daily step whose size varies; an extra pickup costs money. Order one
# only if the projection overshoots the limit by this many points. A dry vending machine is cheap
# to prevent, so it gets no such margin.
OVERSHOOT = {"full": 15.0, "empty": 0.0}

# asset, metric -> (limit kind, regular weekdays (Mon=0), local hour, service kind, label, unit, driver)
# Driver: what the consumption scales with. Drinks and snacks follow the guests in the house.
# The waste container fills in one step per day, when housekeeping empties the floor bins after
# the check-outs, so it follows the departing guests.
TARGETS = {
    ("WASTE_MAIN", "fill_pct"): ("full", (1, 4), 7, "waste_pickup", "central waste container", "% full", "departures"),
    ("VEND1", "stock_drinks"): ("empty", (0, 3), 10, "restock", "vending machine drinks", "units", "guests"),
    ("VEND1", "stock_snacks"): ("empty", (0, 3), 10, "restock", "vending machine snacks", "units", "guests"),
}


def _next_regular(at: datetime, weekdays: tuple[int, ...], hour: int) -> datetime:
    day = local(at).date()
    for i in range(8):
        d = day + timedelta(days=i)
        moment = local_day_time(d, hour)
        if d.weekday() in weekdays and moment > at:
            return moment
    return at + timedelta(days=7)


class _Guests:
    """Guests in the house per hour, counting only bookings created up to a moving "now".

    `advance(now)` adds the bookings that became known; `at(hour)` then reads the count.
    Time only moves forward within one pass, so each booking is added once.
    """

    def __init__(self, ds: Dataset):
        rows = []
        for b in ds.rows("bookings"):
            if b["status"] != "confirmed":
                continue
            created, arrival, departure = parse_ts(b["created_utc"]), parse_ts(b["arrival_utc"]), parse_ts(b["departure_utc"])
            if created and arrival and departure and departure > arrival:
                rows.append((created, arrival, departure, int(to_float(b["guest_count"]) or 1)))
        self.rows = sorted(rows)
        self.origin = min((r[1] for r in rows), default=None)
        self.reset()

    def reset(self) -> None:
        self.count: dict[int, int] = defaultdict(int)
        self.leaving: dict[int, int] = defaultdict(int)
        self.next = 0

    def _index(self, hour: datetime) -> int:
        return int((hour - self.origin).total_seconds() // 3600)

    def advance(self, now: datetime) -> None:
        while self.next < len(self.rows) and self.rows[self.next][0] <= now:
            _, arrival, departure, n = self.rows[self.next]
            self.next += 1
            first = self._index(arrival) + (1 if arrival.minute or arrival.second else 0)
            for i in range(first, self._index(departure - timedelta(seconds=1)) + 1):
                self.count[i] += n
            self.leaving[self._index(departure)] += n

    def at(self, hour: datetime, driver: str = "guests") -> int:
        if not self.origin:
            return 0
        return (self.leaving if driver == "departures" else self.count).get(self._index(hour), 0)


def detect(ds: Dataset) -> Iterable[Decision]:
    guests = _Guests(ds)
    series: dict[tuple[str, str], list[tuple[datetime, float]]] = defaultdict(list)
    for r in ds.rows("logistics"):
        key = (r["asset_id"], r["metric"])
        ts, value = parse_ts(r["timestamp_utc"]), to_float(r["value"])
        if key in TARGETS and ts is not None and value is not None:
            series[key].append((ts, value))

    for key, points in series.items():
        kind, weekdays, hour, service, label, unit, driver = TARGETS[key]
        asset, metric = key
        jump = SERVICE_JUMP["fill_pct" if metric == "fill_pct" else "stock"]
        ordered_for: datetime | None = None
        guests.reset()
        used: list[tuple[datetime, float, int]] = []     # time, consumption, guests in the house then
        for (t0, v0), (t1, v1) in zip(points, points[1:]):
            delta = v1 - v0
            serviced = delta <= jump if kind == "full" else delta >= jump
            if serviced:
                ordered_for = None
                continue
            guests.advance(t1)
            used.append((t1, max(0.0, delta if kind == "full" else -delta), guests.at(t1, driver)))
            recent = [x for x in used[-HISTORY:] if t1 - x[0] <= HOUR * HISTORY]
            if len(recent) < 24:
                continue
            regular = _next_regular(t1, weekdays, hour)
            if ordered_for == regular:
                continue
            guest_hours = sum(g for _, _, g in recent)
            consumed = sum(u for _, u, _ in recent)
            if guest_hours <= 0 or consumed <= 0:
                continue
            per_guest_hour = consumed / guest_hours
            remaining = ((100.0 - v1) if kind == "full" else v1) + OVERSHOOT[kind]
            limit_at, level, booked = None, remaining, []
            step = t1
            while step < regular:
                step += HOUR
                g = guests.at(step, driver)
                booked.append(g)
                level -= per_guest_hour * g
                if level <= 0:
                    limit_at = step
                    break
            if limit_at is None or limit_at > regular - MIN_OUTAGE or t1 + LEAD > regular - MIN_USEFUL:
                continue
            ordered_for = regular
            arrives = t1 + LEAD
            in_time = arrives <= limit_at
            what = "overflow" if kind == "full" else "run empty"
            state = f"{v1:.0f} {unit}" if kind == "full" else f"{v1:.0f} {unit} left"
            avg_guests = sum(booked) / len(booked) if booked else 0
            people = (f"{sum(booked)} guests are booked to check out until then" if driver == "departures"
                      else f"about {avg_guests:.0f} guests are booked in the house until then")
            evidence = [
                f"logistics.csv:{asset}:{metric}:{t1.strftime('%Y-%m-%dT%H:%MZ')} {state}",
                f"logistics.csv:{asset}:{metric}: {consumed:.1f} {'points' if kind == 'full' else 'units'} used in the past {len(recent)} h "
                f"with {guest_hours} {'departing guests' if driver == 'departures' else 'guest-hours'}",
                f"bookings.csv: {people}, as known at {fmt_local(t1)}",
            ]
            yield Decision(
                timestamp_utc=t1, affected_assets=[asset], issue_type="logistics", action="order_service", service_kind=service,
                priority="high" if not in_time else "medium",
                episode_id=f"logistics:{asset}:{metric}:{local(regular).date().isoformat()}",
                reason=(f"The {label} will {what} around {fmt_local(limit_at)}, before the next regular "
                        f"{'pickup' if kind == 'full' else 'restock'} on {fmt_local(regular)}: now {state}, and {people}. Order an extra "
                        f"{'pickup' if kind == 'full' else 'restock'} now; with about 24 h lead it arrives around {fmt_local(arrives)}"
                        + ("." if in_time else ", which is after the projected limit but still shortens the outage.")),
                evidence=evidence, confidence=0.6,
                expected_outcome=(f"No {'overflow' if kind == 'full' else 'stock-out'} before the regular service (simulated estimate; "
                                  "the replay does not react to the order)."),
                verification_plan=(f"{metric} {'drops' if kind == 'full' else 'rises'} after the extra service; no "
                                   f"{'waste_bin_full' if kind == 'full' else 'vending_out_of_stock'} event before {fmt_local(regular)}."))
