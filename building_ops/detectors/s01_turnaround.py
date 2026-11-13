"""S01 The Perfect Checkout and S05 The Unexpected Weekend.

S01 is the single room: a guest wants in before the room is ready (triggers A and C).
S05 is the whole house: an event weekend fills it while cleaners are short (trigger B on a
surge day, issue type `occupancy_surge`), planned the day before from the bookings and again
on the morning itself.

Three triggers, each deciding only on what was known at that moment:

A. An early check-in request arrives: estimate when the room can realistically
   be ready, answer the guest in their language, and put the room's cleaning at
   the front of the queue. No promise before the room is clean.
B. The day starts (07:00 Vienna time) or a cleaner's absence becomes known: if
   more rooms must turn over by check-in than the cleaners on duty can manage,
   plan the day: order of rooms, robots ahead, on-call housekeeper on notice.
C. A guest stands in front of a room that is not ready: clean it next with a
   cleaner who is on shift and free, or ask for approval to call the on-call
   housekeeper, and give the guest a time. When a human finishes the cleaning,
   release the room. Robots never release a room.

Capacity is never invented: only shifts with status `scheduled`, as known at the
decision time, count. All times shown to people are Vienna local time.
"""
from __future__ import annotations

import re
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Iterable

from ..dataset import Dataset, parse_ts
from ..decisions import HUMAN_APPROVAL, Decision
from ..occupancy import OCCUPY, VACATE
from ..signals import fmt_local, local, local_day_time

IMPLEMENTED = True

CLEAN_MIN = 45                 # median human cleaning time in the data (30 to 60 min)
BUFFER_MIN = 15                # margin before a time is given to a guest
ROOMS_BY_CHECKIN = 6           # turnovers one cleaner manages between check-out and 15:00
SURGE_ARRIVALS = 18            # arrivals on one day that make it an occupancy surge
ONCALL_FROM, ONCALL_TO = (15, 30), (22, 0)
ONCALL_TRAVEL_MIN = 45
TIME_IN_TEXT = re.compile(r"\b([01]?\d|2[0-3])[:.]([0-5]\d)\b")

MESSAGES = {
    "ready": {
        "de": "Ihr Zimmer {room} ist voraussichtlich ab {time} Uhr bezugsfertig. Wir melden uns, sobald es freigegeben ist.",
        "en": "Your room {room} should be ready from {time}. We will let you know as soon as it is released.",
        "it": "La camera {room} dovrebbe essere pronta dalle {time}. La avviseremo appena sarà disponibile.",
        "fr": "Votre chambre {room} devrait être prête à partir de {time}. Nous vous prévenons dès qu'elle est disponible.",
        "es": "Su habitación {room} estará lista previsiblemente a partir de las {time}. Le avisaremos en cuanto esté disponible.",
        "nl": "Uw kamer {room} is naar verwachting vanaf {time} klaar. We laten het weten zodra de kamer is vrijgegeven.",
    },
    "released": {
        "de": "Ihr Zimmer {room} ist jetzt bezugsfertig. Willkommen!",
        "en": "Your room {room} is ready now. Welcome!",
        "it": "La camera {room} è pronta. Benvenuti!",
        "fr": "Votre chambre {room} est prête. Bienvenue !",
        "es": "Su habitación {room} ya está lista. ¡Bienvenidos!",
        "nl": "Uw kamer {room} is nu klaar. Welkom!",
    },
}


def _message(kind: str, lang: str | None, room: str, when: datetime | None = None) -> str:
    table = MESSAGES[kind]
    text = table.get(lang or "en", table["en"])
    return text.format(room=room, time=local(when).strftime("%H:%M") if when else "")


def _ceil_quarter(ts: datetime) -> datetime:
    extra = (15 - ts.minute % 15) % 15
    return (ts + timedelta(minutes=extra)).replace(second=0, microsecond=0)


class _World:
    """Everything S01 needs, indexed for "as known at time t" lookups."""

    def __init__(self, ds: Dataset):
        self.bookings: dict[str, dict] = {}
        self.departures: dict[tuple[str, date], list[dict]] = defaultdict(list)
        self.arrivals: dict[tuple[str, date], list[dict]] = defaultdict(list)
        self.by_day_dep: dict[date, list[dict]] = defaultdict(list)
        self.by_day_arr: dict[date, list[dict]] = defaultdict(list)
        for b in ds.rows("bookings"):
            b = dict(b, created=parse_ts(b["created_utc"]), arrival=parse_ts(b["arrival_utc"]),
                     departure=parse_ts(b["departure_utc"]))
            if None in (b["created"], b["arrival"], b["departure"]) or not b.get("room_id"):
                continue
            self.bookings[b["booking_id"]] = b
            if b["status"] != "confirmed":
                continue      # the data has no cancellation time; cancelled bookings are left out
            da, dd = local(b["arrival"]).date(), local(b["departure"]).date()
            self.arrivals[(b["room_id"], da)].append(b)
            self.departures[(b["room_id"], dd)].append(b)
            self.by_day_arr[da].append(b)
            self.by_day_dep[dd].append(b)

        self.shifts: list[dict] = []
        for r in ds.rows("staff_roster"):
            r = dict(r, start=parse_ts(r["start_utc"]), end=parse_ts(r["end_utc"]),
                     known=parse_ts(r["status_known_utc"]))
            if r["start"] and r["end"]:
                self.shifts.append(r)

        self.events = sorted(
            (dict(e, ts=parse_ts(e.get("timestamp_utc"))) for e in ds.events()),
            key=lambda e: (e["ts"], e.get("event_id", "")))
        self.requests = sorted(
            (dict(r, ts=parse_ts(r["timestamp_utc"]), due=parse_ts(r["response_due_utc"]))
             for r in ds.rows("guest_requests")), key=lambda r: r["ts"])
        self.lang: dict[str, list[tuple[datetime, str]]] = defaultdict(list)
        for r in self.requests:
            if r.get("booking_id") and r.get("language"):
                self.lang[r["booking_id"]].append((r["ts"], r["language"]))

    # --- staff, as known at `at` -------------------------------------------------
    def _status(self, shift: dict, at: datetime) -> str:
        """A shift counts as scheduled until its absence became known."""
        if shift["status"] != "scheduled" and (shift["known"] is None or shift["known"] > at):
            return "scheduled"
        return shift["status"]

    def staff_for_day(self, day: date, at: datetime, role: str) -> list[str]:
        return sorted({s["resource_id"] for s in self.shifts
                       if s["role"] == role and local(s["start"]).date() == day and self._status(s, at) == "scheduled"})

    def on_shift(self, at: datetime, role: str) -> list[str]:
        return sorted({s["resource_id"] for s in self.shifts
                       if s["role"] == role and s["start"] <= at < s["end"] and self._status(s, at) == "scheduled"})

    def shift_end(self, day: date, at: datetime) -> datetime | None:
        ends = [s["end"] for s in self.shifts if s["role"] == "cleaner"
                and local(s["start"]).date() == day and self._status(s, at) == "scheduled"]
        return max(ends) if ends else None

    # --- bookings, as known at `at` ----------------------------------------------
    def turnovers(self, day: date, at: datetime) -> list[str]:
        rooms = []
        for b in self.by_day_dep[day]:
            if b["created"] <= at and any(a["created"] <= at for a in self.arrivals[(b["room_id"], day)]):
                rooms.append(b["room_id"])
        return sorted(set(rooms))

    def language(self, booking_id: str | None, at: datetime) -> str:
        known = [l for t, l in self.lang.get(booking_id or "", []) if t <= at]
        return known[-1] if known else "en"


def detect(ds: Dataset) -> Iterable[Decision]:
    w = _World(ds)
    yield from _requests(w)
    yield from _capacity(w)
    yield from _waiting(w)


# --- A: early check-in requests ---------------------------------------------------
def _requests(w: _World) -> Iterable[Decision]:
    # room state replay: who is in, when it was vacated, when a human cleaned it
    idx = 0
    occupant: dict[str, str | None] = {}
    vacated: dict[str, datetime] = {}
    cleaned: dict[str, datetime] = {}
    for req in w.requests:
        t = req["ts"]
        while idx < len(w.events) and w.events[idx]["ts"] <= t:
            e = w.events[idx]
            idx += 1
            room = e.get("room_id")
            if e["type"] in OCCUPY:
                occupant[room] = e.get("booking_id")
            elif e["type"] in VACATE:
                occupant[room], vacated[room] = None, e["ts"]
            elif e["type"] == "cleaning_completed" and not str(e.get("resource_id", "")).startswith("ROBOT"):
                cleaned[room] = e["ts"]
        if req["request_type"] != "early_checkin":
            continue
        booking = w.bookings.get(req.get("booking_id") or "")
        room = req.get("room_id")
        if booking is None or not room or room == "BUILDING":
            continue
        day = local(booking["arrival"]).date()
        standard = booking["arrival"]                       # 15:00 local
        m = TIME_IN_TEXT.search(req.get("text") or "")
        wanted = local_day_time(day, int(m.group(1)), int(m.group(2))) if m else None

        previous = [b for b in w.departures[(room, day)] if b["created"] <= t and b["booking_id"] != booking["booking_id"]]
        in_house = occupant.get(room) not in (None, booking["booking_id"])
        dirty = room in vacated and cleaned.get(room, datetime.min.replace(tzinfo=t.tzinfo)) < vacated[room]
        needs_cleaning = bool(previous) or in_house or dirty

        cleaners = w.staff_for_day(day, t, "cleaner")
        turnovers = w.turnovers(day, t)
        tight = len(turnovers) > len(cleaners) * ROOMS_BY_CHECKIN
        shift_start = local_day_time(day, 7)

        if not needs_cleaning:
            ready, basis = max(t, wanted or t), "room is vacant and was cleaned by housekeeping"
        elif not cleaners:
            ready = local_day_time(day, *ONCALL_FROM) + timedelta(minutes=ONCALL_TRAVEL_MIN + CLEAN_MIN + BUFFER_MIN)
            basis = "no cleaner is scheduled that day; only the on-call housekeeper from 15:30"
        else:
            if in_house or (previous and room not in vacated) or (previous and vacated.get(room, t) < previous[0]["arrival"]):
                free_at, why = previous[0]["departure"] if previous else t, "previous guest checks out by 11:00"
            else:
                free_at, why = vacated.get(room, t), "room is already vacated"
            start = max(free_at, shift_start, t)
            ready = _ceil_quarter(start + timedelta(minutes=CLEAN_MIN + BUFFER_MIN + (CLEAN_MIN if tight else 0)))
            basis = f"{why}; cleaning {CLEAN_MIN} min plus {BUFFER_MIN} min margin" + (
                f"; busy day ({len(turnovers)} turnovers for {len(cleaners)} cleaners), one cleaning slot added" if tight else "")
        ready = min(ready, max(standard, ready)) if needs_cleaning else ready
        promise = max(ready, wanted) if wanted else ready
        feasible = wanted is not None and ready <= wanted
        if promise > standard and ready <= standard:
            promise = standard
        conflict = needs_cleaning and wanted is not None and not feasible

        episode = f"room_turnaround:{room}:{day.isoformat()}"
        ask = f"asks for check-in at {fmt_local(wanted, False)}" if wanted else "asks for an early check-in"
        evidence = [f"guest_requests.csv:{req['request_id']} early_checkin, {ask}, answer due {fmt_local(req['due'])}",
                    f"bookings.csv:{booking['booking_id']} {room} standard check-in {fmt_local(standard)}"]
        if previous:
            evidence.append(f"bookings.csv:{previous[0]['booking_id']} {room} departs {fmt_local(previous[0]['departure'])}")
        evidence.append(f"staff_roster.csv: cleaners scheduled {day.isoformat()} as known now: {', '.join(cleaners) or 'none'}")

        if needs_cleaning:
            yield Decision(
                timestamp_utc=t, affected_assets=[room], issue_type="room_turnaround", action="schedule_cleaning",
                priority="high" if conflict else "medium", episode_id=episode, stage="request",
                reason=(f"Guest {ask} for {room} on {day.isoformat()}. Put {room} at the front of the cleaning queue: {basis}. "
                        f"Earliest realistic time {fmt_local(ready)}. The room is not released before a cleaner reports it clean."),
                evidence=evidence, guest_request_ids=[req["request_id"]], confidence=0.7,
                expected_outcome=f"{room} is clean by {fmt_local(ready, False)} (planning estimate, not a measurement).",
                verification_plan="housekeeping_state of the room turns clean and a cleaning_completed event by a cleaner follows the check-out.")
        text = _message("ready", req.get("language"), room, promise)
        yield Decision(
            timestamp_utc=t, affected_assets=[room], issue_type="room_turnaround", action="notify_guest",
            priority="high" if conflict else "low", episode_id=episode, stage="request",
            reason=(f"Answer the early check-in request before {fmt_local(req['due'], False)}: "
                    + (f"the wanted time {fmt_local(wanted, False)} is realistic. " if feasible else
                       f"the wanted time cannot be promised; realistic is {fmt_local(promise, False)} ({basis}). " if wanted else
                       f"realistic time is {fmt_local(promise, False)} ({basis}). ")
                    + "This is a proposed message, not a confirmed delivery."),
            evidence=evidence, guest_request_ids=[req["request_id"]], confidence=0.7,
            expected_outcome="Guest knows a realistic time and does not wait at a closed door.",
            verification_plan="No waiting_for_room request from this booking; check-in happens at or after the given time.",
            extra={"proposed_message": text, "message_language": req.get("language") or "en"})


# --- B: day capacity --------------------------------------------------------------
def _ahead(w: _World, day: date, first: datetime, last: datetime) -> Iterable[Decision]:
    """S05, the day before: the bookings already show the surge, so plan it while there is time."""
    at = local_day_time(day - timedelta(days=1), 7)
    if not first <= at <= last:
        return
    arrivals = [b for b in w.by_day_arr[day] if b["created"] <= at]
    cleaners = w.staff_for_day(day, at, "cleaner")
    absent = sorted({s["resource_id"] for s in w.shifts if s["role"] == "cleaner"
                     and local(s["start"]).date() == day and w._status(s, at) != "scheduled"})
    turnovers = w.turnovers(day, at)
    capacity = len(cleaners) * ROOMS_BY_CHECKIN
    if len(arrivals) < SURGE_ARRIVALS or len(turnovers) <= capacity:
        return
    episode = f"occupancy_surge:day:{day.isoformat()}"
    weekday = day.strftime("%A")
    fact = (f"{len(arrivals)} arrivals are booked for {weekday} {day.isoformat()} and {len(turnovers)} rooms change guests that day; "
            f"{len(cleaners)} cleaner(s) are scheduled ({', '.join(cleaners) or 'none'})"
            + (f", {', '.join(absent)} absent" if absent else "") + f", enough for about {capacity} rooms by 15:00")
    evidence = [f"bookings.csv: {len(arrivals)} arrivals and {len(turnovers)} same-day turnovers on {day.isoformat()}, as known at {fmt_local(at)}",
                f"staff_roster.csv: cleaners scheduled {', '.join(cleaners) or 'none'}; absent {', '.join(absent) or 'none'}; as known at {fmt_local(at)}"]
    short = len(turnovers) - capacity
    yield Decision(
        timestamp_utc=at, affected_assets=["BUILDING"], issue_type="occupancy_surge", action="flag_anomaly",
        priority="high", episode_id=episode, stage="ahead",
        reason=(f"A full house is coming tomorrow: {fact}. That leaves about {short} room(s) that the shift cannot finish before check-in. "
                "Planning starts now, a day ahead; no capacity is assumed that the roster does not show."),
        evidence=evidence, confidence=0.75,
        expected_outcome="The shortfall is known a day early instead of at the first closed door.",
        verification_plan="Tomorrow's arrival_waiting_room events; the plan is revised at 07:00 tomorrow and whenever an absence becomes known.")
    yield Decision(
        timestamp_utc=at, affected_assets=["ONCALL_1", "BUILDING"], issue_type="occupancy_surge", action="request_human_approval",
        priority="high", episode_id=episode, stage="ahead", notable_cost=True,
        reason=(f"Ask today for approval to cover tomorrow's shortfall of about {short} room(s): an extra cleaner shift if someone can take it, "
                "otherwise the on-call housekeeper ONCALL_1 on notice from 15:30 local. Both cost money, so a person decides. "
                "Nothing is scheduled until that person confirms who is really available."),
        evidence=evidence, confidence=0.7,
        expected_outcome="Cover is arranged a day ahead, or the shortfall is consciously accepted.",
        verification_plan="The roster shows the extra shift, or oncall_housekeeping_called appears tomorrow only for waiting guests.")
    early = sorted({r["room_id"] for r in w.requests if r["request_type"] == "early_checkin" and r["ts"] <= at
                    and (b := w.bookings.get(r.get("booking_id") or "")) and local(b["arrival"]).date() == day})
    yield Decision(
        timestamp_utc=at, affected_assets=sorted({b["room_id"] for b in arrivals}), issue_type="occupancy_surge", action="notify_guest",
        priority="medium", episode_id=episode, stage="ahead",
        reason=(f"Tell tomorrow's {len(arrivals)} arriving guests today, each in their own language, that the house is full: rooms are ready from "
                f"15:00 and an earlier check-in cannot be promised"
                + (f" (early check-in was already requested for {', '.join(early)})" if early else "")
                + ". Proposed messages, not confirmed deliveries."),
        evidence=evidence, expected_outcome="Guests plan their arrival for 15:00 instead of waiting in the lobby.",
        verification_plan="Fewer early arrivals and waiting_for_room requests tomorrow than on other full days.",
        extra={"proposed_message": "Tomorrow we are fully booked. Your room will be ready from 15:00; an earlier check-in is unfortunately not possible. "
                                   "We will let you know as soon as your room is released.", "message_language": "per guest"})


def _capacity(w: _World) -> Iterable[Decision]:
    days = sorted(set(w.by_day_dep) | set(w.by_day_arr))
    first, last = (w.events[0]["ts"], w.events[-1]["ts"]) if w.events else (None, None)
    for day in days:
        if first is not None:
            yield from _ahead(w, day, first, last)
        moments = [local_day_time(day, 7)]
        moments += [s["known"] for s in w.shifts if s["role"] == "cleaner" and s["status"] != "scheduled"
                    and s["known"] and local(s["start"]).date() == day and moments[0] < s["known"] < s["end"]]
        for at in sorted(moments):
            if first is None or not first <= at <= last:
                continue
            cleaners = w.staff_for_day(day, at, "cleaner")
            absent = sorted({s["resource_id"] for s in w.shifts if s["role"] == "cleaner"
                             and local(s["start"]).date() == day and w._status(s, at) != "scheduled"})
            turnovers = w.turnovers(day, at)
            capacity = len(cleaners) * ROOMS_BY_CHECKIN
            if len(turnovers) <= capacity:
                continue
            arrivals = [b for b in w.by_day_arr[day] if b["created"] <= at]
            surge = len(arrivals) >= SURGE_ARRIVALS
            issue = "occupancy_surge" if surge else "room_turnaround"
            episode = f"{issue}:day:{day.isoformat()}"
            robots = w.staff_for_day(day, at, "robot")
            early = {r["room_id"] for r in w.requests if r["request_type"] == "early_checkin" and r["ts"] <= at
                     and (b := w.bookings.get(r.get("booking_id") or "")) and local(b["arrival"]).date() == day}
            order = sorted(turnovers, key=lambda r: (r not in early, r))
            late = order[capacity:]
            fact = (f"{len(turnovers)} rooms must turn over by check-in on {day.isoformat()}, "
                    f"{len(cleaners)} cleaner(s) on duty ({', '.join(cleaners) or 'none'})"
                    + (f", absent: {', '.join(absent)}" if absent else "")
                    + f"; about {capacity} rooms are realistic by 15:00 ({ROOMS_BY_CHECKIN} per cleaner)")
            evidence = [f"bookings.csv: {len(turnovers)} rooms with departure and arrival on {day.isoformat()}, {len(arrivals)} arrivals in total",
                        f"staff_roster.csv: cleaners {', '.join(cleaners) or 'none'}; absent {', '.join(absent) or 'none'}; as known at {fmt_local(at)}"]
            yield Decision(
                timestamp_utc=at, affected_assets=order, issue_type=issue, action="schedule_cleaning",
                priority="high", episode_id=episode, stage="day_plan",
                reason=(f"Capacity shortfall: {fact}. Clean in this order: rooms with an early check-in request first "
                        f"({', '.join(sorted(early & set(order))) or 'none'}), then the other turnovers; rooms without a same-day arrival last."),
                evidence=evidence, confidence=0.7,
                expected_outcome=f"The first {min(capacity, len(order))} rooms are clean by 15:00 (planning estimate).",
                verification_plan="cleaning_completed events follow the order; arrival_waiting_room events stay at zero for the first rooms.")
            if robots:
                yield Decision(
                    timestamp_utc=at, affected_assets=robots + order, issue_type=issue, action="dispatch_robot",
                    priority="medium", episode_id=episode, stage="day_plan",
                    reason=(f"Send {', '.join(robots)} to clean the floors of vacated turnover rooms ahead of the cleaners; this shortens "
                            "the human turnover. Robots enter vacated rooms only and never release a room."),
                    evidence=evidence[1:], expected_outcome="Shorter human cleaning per room (simulated, not measured).",
                    verification_plan="robot_floor_cleaning_completed precedes cleaning_started in each room.")
            if late:
                yield Decision(
                    timestamp_utc=at, affected_assets=["ONCALL_1"] + late, issue_type=issue, action="request_human_approval",
                    priority="high", episode_id=episode, stage="day_plan", notable_cost=True,
                    reason=(f"Ask for approval to put the on-call housekeeper ONCALL_1 on notice from 15:30 local: {len(late)} room(s) "
                            f"({', '.join(late)}) are beyond what the shift can finish. On-call is costly, one room at a time, about "
                            f"{ONCALL_TRAVEL_MIN} min to site, for waiting guests only."),
                    evidence=evidence, expected_outcome="Waiting guests are served in the evening instead of waiting for the next shift.",
                    verification_plan="No guest waits past 22:00 local; oncall_housekeeping_called only for rooms with a waiting guest.")
                when = local_day_time(day, *ONCALL_FROM) + timedelta(minutes=ONCALL_TRAVEL_MIN + CLEAN_MIN + BUFFER_MIN)
                yield Decision(
                    timestamp_utc=at, affected_assets=late, issue_type=issue, action="notify_guest",
                    priority="medium", episode_id=episode, stage="day_plan",
                    reason=(f"Tell the guests arriving in {', '.join(late)} today that the room may not be ready at 15:00 and give "
                            f"{fmt_local(when, False)} as the realistic latest time. Proposed messages, not confirmed deliveries."),
                    evidence=evidence, expected_outcome="Guests plan their arrival instead of waiting in the lobby.",
                    verification_plan="Fewer waiting_for_room requests from these bookings.",
                    extra={"proposed_message": _message("ready", "en", "(your room)", when), "message_language": "per guest"})
            break                                          # one plan per day


# --- C: a guest waits at a room that is not ready ----------------------------------
def _waiting(w: _World) -> Iterable[Decision]:
    waiting: dict[str, dict] = {}
    cleaning: dict[str, tuple[datetime, str]] = {}
    for e in w.events:
        t, kind, room = e["ts"], e["type"], e.get("room_id")
        if kind == "cleaning_started":
            cleaning[room] = (t, e.get("resource_id") or "")
        elif kind == "cleaning_completed":
            cleaning.pop(room, None)
            human = not str(e.get("resource_id", "")).startswith("ROBOT")
            if room in waiting and human:
                guest = waiting.pop(room)
                day = local(t).date()
                episode = f"room_turnaround:{room}:{day.isoformat()}"
                evidence = [f"events.jsonl:{e.get('event_id')} cleaning_completed {room} by {e.get('resource_id')} at {fmt_local(t)}",
                            f"events.jsonl:{guest['event_id']} arrival_waiting_room {room} at {fmt_local(guest['ts'])}"]
                yield Decision(
                    timestamp_utc=t, affected_assets=[room], issue_type="room_turnaround", action="release_room",
                    priority="high", episode_id=episode, stage="released",
                    reason=(f"Release {room}: a human cleaner ({e.get('resource_id')}) reported it clean at {fmt_local(t, False)} and the "
                            f"guest of booking {guest.get('booking_id')} has been waiting since {fmt_local(guest['ts'], False)}."),
                    evidence=evidence, confidence=0.9,
                    expected_outcome="Guest checks in right after the release.",
                    verification_plan="A checkin_after_wait event for this booking follows; housekeeping_state is clean.")
                lang = w.language(guest.get("booking_id"), t)
                yield Decision(
                    timestamp_utc=t, affected_assets=[room], issue_type="room_turnaround", action="notify_guest",
                    priority="high", episode_id=episode, stage="released",
                    reason=f"Tell the waiting guest that {room} is ready. Proposed message, not a confirmed delivery.",
                    evidence=evidence, expected_outcome="Guest goes to the room.",
                    verification_plan="checkin_after_wait follows within minutes.",
                    extra={"proposed_message": _message("released", lang, room), "message_language": lang})
        elif kind in ("checkin", "checkin_early", "checkin_after_wait"):
            waiting.pop(room, None)
        elif kind == "arrival_waiting_room":
            waiting[room] = e
            day = local(t).date()
            episode = f"room_turnaround:{room}:{day.isoformat()}"
            lang = w.language(e.get("booking_id"), t)
            evidence = [f"events.jsonl:{e.get('event_id')} arrival_waiting_room {room} booking {e.get('booking_id')} at {fmt_local(t)}"]
            hm = (local(t).hour, local(t).minute)
            if room in cleaning:
                start, who = cleaning[room]
                eta = _ceil_quarter(start + timedelta(minutes=CLEAN_MIN + BUFFER_MIN))
                evidence.append(f"events.jsonl: cleaning_started {room} by {who} at {fmt_local(start)}")
                how = f"cleaning by {who} is already running since {fmt_local(start, False)}"
            else:
                busy = {who for _, who in cleaning.values()}
                on_duty = w.on_shift(t, "cleaner")
                free = [c for c in on_duty if c not in busy]
                evidence.append(f"staff_roster.csv: cleaners on shift now {', '.join(on_duty) or 'none'}; busy {', '.join(sorted(busy)) or 'none'}")
                if on_duty:
                    who = free[0] if free else None
                    wait = 0 if free else CLEAN_MIN
                    eta = _ceil_quarter(t + timedelta(minutes=wait + CLEAN_MIN + BUFFER_MIN))
                    how = (f"{who} is on shift and free" if who else "all cleaners on shift are busy; next free cleaner takes it")
                    yield Decision(
                        timestamp_utc=t, affected_assets=[room], issue_type="room_turnaround", action="schedule_cleaning",
                        priority="critical", episode_id=episode, stage="waiting", resource_id=who,
                        reason=(f"A guest is waiting at {room}, which is not clean. Clean it next: {how}. "
                                f"Realistic ready time {fmt_local(eta, False)}. The room stays locked until a cleaner reports it clean."),
                        evidence=evidence, confidence=0.8,
                        expected_outcome=f"{room} clean by {fmt_local(eta, False)} (planning estimate).",
                        verification_plan="cleaning_started then cleaning_completed by a cleaner for this room; then release.")
                elif ONCALL_FROM <= hm < ONCALL_TO:
                    eta = _ceil_quarter(t + timedelta(minutes=ONCALL_TRAVEL_MIN + CLEAN_MIN + BUFFER_MIN))
                    how = "no cleaner is on shift; the on-call housekeeper needs approval and about 45 min to arrive"
                    yield Decision(
                        timestamp_utc=t, affected_assets=["ONCALL_1", room], issue_type="room_turnaround",
                        action="request_human_approval", priority="critical", episode_id=episode, stage="waiting",
                        notable_cost=True, resource_id="ONCALL_1",
                        reason=(f"A guest is waiting at {room} and no cleaner is on shift at {fmt_local(t, False)}. Ask for approval "
                                f"to call the on-call housekeeper (costly, one room at a time). Realistic ready time {fmt_local(eta, False)}."),
                        evidence=evidence, confidence=0.8,
                        expected_outcome=f"{room} clean by {fmt_local(eta, False)} if approved now (planning estimate).",
                        verification_plan="oncall_housekeeping_called for this room, then cleaning_completed by ONCALL_1.")
                else:
                    eta = None
                    how = "no cleaner is on shift and the on-call window (15:30 to 22:00 local) is closed"
                    yield Decision(
                        timestamp_utc=t, affected_assets=[room], issue_type="room_turnaround", action="request_human_approval",
                        priority="critical", episode_id=episode, stage="waiting",
                        reason=(f"A guest is waiting at {room}; {how}. A person must decide: another clean room, or wait for the "
                                "next shift. No capacity is invented."),
                        evidence=evidence, expected_outcome="A person offers the guest an alternative.",
                        verification_plan="room_reassigned or a later cleaning and check-in for this booking.")
            text = (_message("ready", lang, room, eta) if eta else
                    _message("ready", lang, room, local_day_time(day + timedelta(days=1), 9)))
            yield Decision(
                timestamp_utc=t, affected_assets=[room], issue_type="room_turnaround", action="notify_guest",
                priority="critical", episode_id=episode, stage="waiting",
                reason=(f"Guest of booking {e.get('booking_id')} is at {room} and cannot enter: {how}. Give a realistic time"
                        + (f" ({fmt_local(eta, False)})" if eta else "") + " instead of silence. Proposed message, not a confirmed delivery."),
                evidence=evidence, expected_outcome="Guest knows how long it takes.",
                verification_plan="No further waiting_for_room request from this booking before the given time.",
                extra={"proposed_message": text, "message_language": lang})
