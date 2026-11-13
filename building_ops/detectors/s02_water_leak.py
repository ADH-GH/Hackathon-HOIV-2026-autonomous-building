"""S02 The Hidden Water Leak.

Three patterns, all read from the cumulative meters, none from the BMS alarm:

- burst:  a room meter runs at a high rate for hours (a burst hose).
- quiet:  a room meter never stops for hours (a running toilet). The rate is
          small, the tell is that a healthy room has long stretches of zero.
- hidden: at night the main meter runs ahead of the sum of all room meters
          (a leak outside the rooms).

Look-alikes handled: showers and baths (short), cleaning and legionella
flushing (short), meter exchange (counter restarts), a jittery meter (readings
go up and down: reported once as data quality, never as a leak), blank readings.

Thresholds were set on the dev year, see docs in README ("Water leak thresholds").
Every decision is stamped at the reading that completes the pattern, so it uses
only readings up to that moment.
"""
from __future__ import annotations

import statistics
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Iterable

from ..dataset import Dataset, parse_ts, to_float
from ..decisions import APPROVAL_AND_CONSENT, HUMAN_APPROVAL, Decision
from ..occupancy import Occupancy
from ..signals import fmt_local, local

IMPLEMENTED = True

STEP = timedelta(minutes=15)
BURST_RATE_L = 8.0          # litres per 15 min ...
BURST_STEPS = 8             # ... for 2 h. Longest benign stretch in dev: 5 steps.
QUIET_STEPS = 20            # 5 h without a single zero. Longest benign in dev: 13 steps.
SAME_INCIDENT = timedelta(hours=72)   # a leak that pauses and resumes is one incident
EXCHANGE_DROP = 0.5         # counter falls below half: meter exchanged, not consumption
JITTER_WINDOW = 96          # one day of readings
JITTER_STEPS = 8            # this many backward steps in a day: the meter is unreliable
NIGHT = (1, 5)              # local hours with the least guest use
HIDDEN_GAP_L = 2.0          # median night gap main - rooms, litres per 15 min. Dev normal: <= 0.1
HIDDEN_MIN_ROOMS = 38       # rooms with a usable reading in the interval
HIDDEN_MIN_STEPS = 8        # usable night intervals needed to judge a night


def _z(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%dT%H:%MZ")


class _Room:
    __slots__ = ("prev", "run_start", "run_len", "run_min", "run_sum", "burst_len", "burst_start",
                 "burst_sum", "back", "jitter_reported", "last_incident", "open_kind")

    def __init__(self) -> None:
        self.prev: tuple[datetime, float] | None = None
        self.run_start = self.burst_start = None
        self.run_len = self.burst_len = 0
        self.run_min = float("inf")
        self.run_sum = self.burst_sum = 0.0
        self.back: deque[int] = deque(maxlen=JITTER_WINDOW)
        self.jitter_reported = False
        self.last_incident: datetime | None = None
        self.open_kind: str | None = None

    def reset_runs(self) -> None:
        self.run_start = self.burst_start = None
        self.run_len = self.burst_len = 0
        self.run_min = float("inf")
        self.run_sum = self.burst_sum = 0.0


def detect(ds: Dataset) -> Iterable[Decision]:
    occupancy = Occupancy(ds)
    rooms: dict[str, _Room] = defaultdict(_Room)
    room_sum: dict[datetime, float] = defaultdict(float)
    room_count: dict[datetime, int] = defaultdict(int)

    for row in ds.rows("room_water"):
        ts, value, room = parse_ts(row["timestamp_utc"]), to_float(row["meter_total_l"]), row["room_id"]
        st = rooms[room]
        if ts is None or value is None:
            st.prev = None            # a blank reading breaks the series; it is not zero flow
            st.reset_runs()
            continue
        prev, st.prev = st.prev, (ts, value)
        if prev is None or ts - prev[0] != STEP:
            st.reset_runs()
            continue
        delta = value - prev[1]
        if delta < 0:
            if value < prev[1] * EXCHANGE_DROP:
                st.back.clear()       # counter restarted: meter exchange
            else:
                st.back.append(1)
            st.reset_runs()
        else:
            st.back.append(0)
            room_sum[ts] += delta
            room_count[ts] += 1

        if sum(st.back) >= JITTER_STEPS:
            st.reset_runs()
            if not st.jitter_reported:
                st.jitter_reported = True
                yield Decision(
                    timestamp_utc=ts, affected_assets=[f"WM_{room}"], issue_type="data_quality",
                    action="flag_anomaly", priority="low",
                    reason=(f"Water meter WM_{room} reads backwards repeatedly ({sum(st.back)} backward steps "
                            "in the last 24 h). Its consumption is unreliable, so it is excluded from leak "
                            "detection instead of being read as a leak."),
                    episode_id=f"data_quality:WM_{room}",
                    evidence=[f"room_water.csv:{room}:{_z(ts - STEP * JITTER_WINDOW)}..{_z(ts)} "
                              f"{sum(st.back)} decreasing meter_total_l steps"],
                    expected_outcome="Meter is checked at the next metering visit; no guest impact.",
                    verification_plan="Backward steps stop after the meter is checked or exchanged.",
                    confidence=0.9)
            continue
        if delta <= 0:
            if delta == 0:
                st.reset_runs()
            continue

        # flow in this interval
        if st.run_len == 0:
            st.run_start = prev[0]
        st.run_len += 1
        st.run_min = min(st.run_min, delta)
        st.run_sum += delta
        if delta >= BURST_RATE_L:
            if st.burst_len == 0:
                st.burst_start, st.burst_sum = prev[0], 0.0
            st.burst_len += 1
            st.burst_sum += delta
        else:
            st.burst_len = 0

        kind = None
        if st.burst_len == BURST_STEPS:
            kind = "burst"
        elif st.run_len == QUIET_STEPS and st.open_kind is None:
            kind = "quiet"
        if kind is None:
            if st.run_len >= QUIET_STEPS or st.burst_len >= BURST_STEPS:
                st.last_incident = ts
            continue
        recent = st.last_incident is not None and ts - st.last_incident <= SAME_INCIDENT
        st.last_incident = ts
        if recent and not (kind == "burst" and st.open_kind == "quiet"):
            continue                  # same incident resumed: no second alert
        st.open_kind = kind
        yield from _room_decisions(room, kind, ts, st, occupancy)

    yield from _hidden_leak(ds, room_sum, room_count)


def _room_decisions(room: str, kind: str, ts: datetime, st: _Room, occupancy: Occupancy) -> Iterable[Decision]:
    booking = occupancy.booking(room, ts)
    occupied = booking is not None
    if kind == "burst":
        start, hours = st.burst_start, BURST_STEPS / 4
        fact = (f"{st.burst_sum:.0f} L in {hours:.0f} h, every 15-min interval at least {BURST_RATE_L:.0f} L")
        what, priority, confidence = "Sustained high flow", "critical", 0.9
        why_not = "A shower or bath ends within about an hour; this did not."
    else:
        start, hours = st.run_start, QUIET_STEPS / 4
        fact = (f"{st.run_sum:.1f} L in {hours:.0f} h without a single interval at zero "
                f"(lowest {st.run_min:.1f} L per 15 min)")
        what, priority, confidence = "Continuous low flow", "high", 0.8
        why_not = "Normal use has long stretches of zero; a fixture that never stops points to a running toilet or a seeping fitting."
    episode = f"water_leak:{room}:{_z(start)}"
    state = f"Room is occupied (booking {booking})" if occupied else "Room is vacant"
    evidence = [f"room_water.csv:{room}:{_z(start)}..{_z(ts)} {fact}",
                f"events.jsonl:{room} occupancy at {_z(ts)}: {'occupied by ' + booking if occupied else 'vacant'}"]

    yield Decision(
        timestamp_utc=ts, affected_assets=[room, f"WM_{room}"], issue_type="water_leak",
        action="flag_anomaly", priority=priority,
        reason=f"{what} in {room} since {fmt_local(start)}: {fact}. {why_not} {state}.",
        episode_id=episode, evidence=evidence, confidence=confidence,
        expected_outcome="Operations see the suspected leak with its evidence.",
        verification_plan=f"WM_{room} returns to intervals of zero flow; escalate if the rate rises.")
    yield Decision(
        timestamp_utc=ts, affected_assets=[room], issue_type="water_leak",
        action="request_inspection", priority=priority,
        reason=(f"Inspect {room} for a leak ({what.lower()}, {fact}). "
                + ("Entering needs approval and the guest's consent; consent is not granted yet. "
                   if occupied else "Room is vacant; inspection needs approval. ")
                + "No water shutoff without authorisation."),
        episode_id=episode, evidence=evidence, confidence=confidence,
        enters_occupied_room=occupied, autonomy=APPROVAL_AND_CONSENT if occupied else HUMAN_APPROVAL,
        dependencies=["flag_anomaly for the same episode"],
        expected_outcome="Leak confirmed and repaired, or ruled out.",
        verification_plan=f"After the visit WM_{room} shows zero-flow intervals again; a work order records the finding.")
    if occupied:
        yield Decision(
            timestamp_utc=ts, affected_assets=[room], issue_type="water_leak",
            action="notify_guest", priority=priority,
            reason=(f"Propose a message to the guest in {room}: possible water fault, ask for consent to enter "
                    "and to report visible water. A proposed message is not proof of delivery."),
            episode_id=episode, evidence=evidence[:1],
            expected_outcome="Guest replies with consent or a time window.",
            verification_plan="A reply or a new guest request for this room arrives; otherwise follow up through approval.")
    elif kind == "burst":
        yield Decision(
            timestamp_utc=ts, affected_assets=[room], issue_type="water_leak",
            action="block_room", priority=priority,
            reason=f"Keep {room} out of sale until the suspected burst is inspected; blocking a room needs approval.",
            episode_id=episode, evidence=evidence[:1],
            expected_outcome="No guest is checked into a room with water damage.",
            verification_plan="Room is released only after the inspection passed and it is clean.")


def _hidden_leak(ds: Dataset, room_sum: dict[datetime, float], room_count: dict[datetime, int]) -> Iterable[Decision]:
    """Night gap between the main meter and the sum of the room meters."""
    nights: dict = defaultdict(list)
    prev: tuple[datetime, float] | None = None
    for row in ds.rows("water_main"):
        ts, value = parse_ts(row["timestamp_utc"]), to_float(row["meter_total_l"])
        if ts is None or value is None:
            prev = None
            continue
        last, prev = prev, (ts, value)
        if last is None or ts - last[0] != STEP or value < last[1]:
            continue
        hour = local(ts).hour
        if NIGHT[0] <= hour < NIGHT[1] and room_count.get(ts, 0) >= HIDDEN_MIN_ROOMS:
            nights[local(ts).date()].append((ts, value - last[1] - room_sum[ts]))

    open_since = None
    last_hit = None
    for day in sorted(nights):
        points = nights[day]
        if len(points) < HIDDEN_MIN_STEPS:
            continue
        gap = statistics.median(g for _, g in points)
        if gap < HIDDEN_GAP_L:
            continue
        if last_hit is not None and (day - last_hit).days <= 3:
            last_hit = day
            continue                  # same incident, another night
        open_since, last_hit = day, day
        first, decided = points[0][0], points[-1][0]
        fact = (f"main meter ran {gap:.1f} L per 15 min ahead of the sum of the room meters "
                f"(median of {len(points)} night intervals, normal is about 0)")
        episode = f"water_leak:WM_MAIN:{open_since.isoformat()}"
        evidence = [f"water_main.csv:{_z(first - STEP)}..{_z(decided)} minus room_water.csv sum of rooms: {fact}"]
        yield Decision(
            timestamp_utc=decided, affected_assets=["WM_MAIN"], issue_type="water_leak",
            action="flag_anomaly", priority="high",
            reason=(f"Water is used outside the rooms in the night to {fmt_local(decided)}: {fact}. No room meter explains it, "
                    "so the loss is in common areas or the technical room."),
            episode_id=episode, evidence=evidence, confidence=0.75,
            expected_outcome="Operations see the unexplained night loss.",
            verification_plan="Night gap between main meter and room meters returns to about 0.")
        yield Decision(
            timestamp_utc=decided, affected_assets=["WM_MAIN", "BUILDING"], issue_type="water_leak",
            action="request_inspection", priority="high",
            reason=(f"Inspect common areas, technical room and irrigation for a leak: {fact}. "
                    "Needs approval; no shutoff without authorisation."),
            episode_id=episode, evidence=evidence, confidence=0.75, autonomy=HUMAN_APPROVAL,
            dependencies=["flag_anomaly for the same episode"],
            expected_outcome="Leak located and repaired, or a benign consumer identified.",
            verification_plan="Night gap returns to about 0 after the repair; escalate if it grows.")
