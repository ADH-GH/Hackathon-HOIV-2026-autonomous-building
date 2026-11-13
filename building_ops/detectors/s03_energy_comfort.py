"""S03 Energy vs Comfort.

Three parts, each deciding on what was known at that moment:

A. Heat pump degradation. The heat pump's COP (heat out / electricity in) follows
   the outdoor temperature closely. When the 6-hour median falls 10 % below what
   the outdoor temperature explains, the plant is degraded: flag it, protect the
   occupied rooms, organise service. A data gap is not degradation: the check
   needs enough valid readings and says nothing without them.
B. Cold snap ahead. From the latest issued forecast and the published day-ahead
   prices: pre-heat occupied rooms inside the comfort band in the cheapest hours
   before the cold, instead of saving energy at the guests' expense.
C. A guest reports a cold room: look at the room's own readings (temperature,
   setpoint, window) and answer within the deadline in the guest's language.

The COP model was fitted on the dev year and checked on the quickstart run, which
is an independent simulation: COP = 2.796 + 0.0761 * outdoor °C (heating season).
"""
from __future__ import annotations

import statistics
from bisect import bisect_right
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Iterable

from ..dataset import Dataset, parse_ts, to_float
from ..decisions import Decision
from ..occupancy import Occupancy
from ..signals import fmt_local, local

IMPLEMENTED = True

COP_A, COP_B = 2.796, 0.0761     # fitted on dev, 19,486 running intervals
HEATING_SEASON_BELOW_C = 15.0    # above this the heat pump mostly makes hot water; model not valid
WINDOW = timedelta(hours=6)
MIN_POINTS = 16                  # of 24 intervals: fewer valid readings means "unknown", not "degraded"
DEGRADED = -0.10                 # 6 h median relative COP gap. Dev normal days: above -0.03; faults: about -0.155
RECOVERED = -0.04
RECOVERY_HOLD = timedelta(hours=24)
COLD_SNAP_C = -8.0               # forecast minimum that calls for pre-heating
COMFORT = (20.0, 23.0)           # occupied rooms, building.json constraints
PREHEAT_HOURS = 3
PREHEAT_LOOKBACK = timedelta(hours=8)   # heat stored earlier than this is lost again before the cold arrives

COLD_REPLY = {
    "de": "Danke für den Hinweis. Wir haben die Heizung in Zimmer {room} auf {sp:.0f} °C gestellt{extra}. Es sollte in Kürze wärmer werden.",
    "en": "Thank you for telling us. We have set the heating in room {room} to {sp:.0f} °C{extra}. It should get warmer shortly.",
    "it": "Grazie della segnalazione. Abbiamo impostato il riscaldamento della camera {room} a {sp:.0f} °C{extra}. Presto farà più caldo.",
    "fr": "Merci de nous avoir prévenus. Nous avons réglé le chauffage de la chambre {room} sur {sp:.0f} °C{extra}. Il fera bientôt plus chaud.",
    "es": "Gracias por avisarnos. Hemos ajustado la calefacción de la habitación {room} a {sp:.0f} °C{extra}. Pronto hará más calor.",
    "nl": "Bedankt voor de melding. We hebben de verwarming in kamer {room} op {sp:.0f} °C gezet{extra}. Het wordt snel warmer.",
}
WINDOW_HINT = {
    "de": "; bitte das Fenster schließen", "en": "; please close the window", "it": "; si prega di chiudere la finestra",
    "fr": "; merci de fermer la fenêtre", "es": "; por favor cierre la ventana", "nl": "; sluit alstublieft het raam",
}


def _z(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%dT%H:%MZ")


class _Context:
    def __init__(self, ds: Dataset):
        self.occupancy = Occupancy(ds)
        self.rooms = [r["id"] for r in ds.building.get("building", {}).get("rooms", [])]
        self.outdoor = {parse_ts(r["timestamp_utc"]): to_float(r["outdoor_c"]) for r in ds.rows("weather")}
        # forecasts: issue time -> [(target, temperature)]
        self.forecasts: dict[datetime, list[tuple[datetime, float]]] = defaultdict(list)
        for r in ds.rows("weather_forecast"):
            issued, target, value = parse_ts(r["issued_utc"]), parse_ts(r["target_utc"]), to_float(r["outdoor_c_forecast"])
            if issued and target and value is not None:
                self.forecasts[issued].append((target, value))
        self.issues = sorted(self.forecasts)
        self.tariff = sorted(
            (parse_ts(r["published_utc"]), parse_ts(r["timestamp_utc"]), to_float(r["price_eur_kwh"]))
            for r in ds.rows("tariff") if r["published_utc"] and r["timestamp_utc"] and r["price_eur_kwh"])
        self.tech = [dict(r, start=parse_ts(r["start_utc"]), end=parse_ts(r["end_utc"]), known=parse_ts(r["status_known_utc"]))
                     for r in ds.rows("staff_roster") if r["role"] == "technician"]

    def forecast_at(self, at: datetime) -> tuple[datetime, list[tuple[datetime, float]]] | None:
        """The newest forecast that had been issued at `at`, future targets only."""
        i = bisect_right(self.issues, at) - 1
        if i < 0:
            return None
        issued = self.issues[i]
        return issued, [(t, v) for t, v in self.forecasts[issued] if t >= at]

    def prices_known(self, at: datetime, start: datetime, end: datetime) -> list[tuple[datetime, float]]:
        return [(hour, price) for published, hour, price in self.tariff if published <= at and start <= hour < end]

    def occupied_rooms(self, at: datetime) -> list[str]:
        return [r for r in self.rooms if self.occupancy.occupied(r, at)]

    def next_technician(self, at: datetime) -> datetime | None:
        """Start of the next technician shift that, as known at `at`, will be worked."""
        starts = []
        for s in self.tech:
            status = s["status"] if (s["status"] == "scheduled" or (s["known"] and s["known"] <= at)) else "scheduled"
            if status == "scheduled" and s["end"] and s["end"] > at:
                starts.append(max(s["start"], at))
        return min(starts) if starts else None


def detect(ds: Dataset) -> Iterable[Decision]:
    ctx = _Context(ds)
    degraded = list(_degradation(ds, ctx))
    spans = [(d.timestamp_utc, d.extra.get("_until")) for d in degraded if d.stage == "detected" and d.action == "flag_anomaly"]
    for d in degraded:
        d.extra.pop("_until", None)
        yield d
    yield from _cold_snap(ctx, spans)
    yield from _cold_requests(ds, ctx, spans)


# --- A: heat pump degradation ------------------------------------------------------
def _degradation(ds: Dataset, ctx: _Context) -> Iterable[Decision]:
    hp: dict[datetime, dict[str, str | None]] = defaultdict(dict)
    for r in ds.rows("equipment"):
        if r["asset_id"] == "HP1":
            ts = parse_ts(r["timestamp_utc"])
            if ts:
                hp[ts][r["metric"]] = r["value"]

    window: deque[tuple[datetime, float, float, float]] = deque()   # ts, gap, cop, outdoor
    active: Decision | None = None
    healthy_since: datetime | None = None
    for ts in sorted(hp):
        m = hp[ts]
        heat, power, outdoor = to_float(m.get("heat_output_kw")), to_float(m.get("electric_kw")), ctx.outdoor.get(ts)
        if (m.get("status") == "running" and heat and power and power > 3 and outdoor is not None
                and outdoor < HEATING_SEASON_BELOW_C):
            cop = heat / power
            window.append((ts, cop / (COP_A + COP_B * outdoor) - 1, cop, outdoor))
        while window and window[0][0] <= ts - WINDOW:
            window.popleft()
        if len(window) < MIN_POINTS:
            continue                                   # not enough valid data: no statement
        gap = statistics.median(w[1] for w in window)

        if active is not None:
            if gap > RECOVERED:
                healthy_since = healthy_since or ts
                if ts - healthy_since >= RECOVERY_HOLD:
                    active.extra["_until"] = ts
                    active, healthy_since = None, None
            else:
                healthy_since = None
            continue
        if gap > DEGRADED:
            continue

        cop = statistics.median(w[2] for w in window)
        out = statistics.median(w[3] for w in window)
        expected = COP_A + COP_B * out
        episode = f"heating_comfort:HP1:{_z(window[0][0])}"
        fc = ctx.forecast_at(ts)
        ahead = [v for t, v in fc[1] if t <= ts + timedelta(hours=48)] if fc else []
        coldest = min(ahead) if ahead else None
        occupied = ctx.occupied_rooms(ts)
        severe = coldest is not None and coldest <= -5.0
        fact = (f"HP1 COP {cop:.2f} over the last 6 h against {expected:.2f} expected at {out:.1f} °C outdoors "
                f"({gap * 100:.0f} %, {len(window)} valid readings)")
        evidence = [f"equipment.csv:HP1:{_z(window[0][0])}..{_z(ts)} heat_output_kw / electric_kw, median COP {cop:.2f}",
                    f"weather.csv:{_z(window[0][0])}..{_z(ts)} median outdoor {out:.1f} °C; model COP = {COP_A} + {COP_B} * T"]
        if fc:
            evidence.append(f"weather_forecast.csv: issued {fmt_local(fc[0])}, minimum next 48 h {coldest:.1f} °C")
        nxt = ctx.next_technician(ts)
        flag = Decision(
            timestamp_utc=ts, affected_assets=["HP1"], issue_type="heating_comfort", action="flag_anomaly",
            priority="critical" if severe else "high", episode_id=episode, stage="detected",
            reason=(f"Heat pump performance is reduced: {fact}. Normal days stay within 3 %. "
                    + (f"The forecast shows {coldest:.1f} °C in the next 48 h and {len(occupied)} rooms are occupied, so comfort is at risk. "
                       if coldest is not None else f"{len(occupied)} rooms are occupied. ")
                    + "This is the plant, not a sensor gap: the check needs 4 h of valid readings in 6 h."),
            evidence=evidence, confidence=0.85,
            expected_outcome="Operations know about the degradation before guests feel it.",
            verification_plan="6 h median COP returns to within 4 % of the model for 24 h.", extra={"_until": None})
        active, healthy_since = flag, None
        yield flag
        avail = (f"TECH_1's next shift, as known now, starts {fmt_local(nxt)}" if nxt
                 else "no technician shift is known in the roster; an external contractor is needed")
        yield Decision(
            timestamp_utc=ts, affected_assets=["HP1"] + (["TECH_1"] if nxt else []), issue_type="heating_comfort",
            action="dispatch_technician" if nxt else "order_service", service_kind=None if nxt else "contractor",
            priority="critical" if severe else "high", episode_id=episode, stage="detected",
            resource_id="TECH_1" if nxt else None,
            reason=(f"Organise heat pump service: {fact}. {avail}. A technician or contractor call-out needs approval."),
            evidence=evidence + ["staff_roster.csv: technician availability as known at " + fmt_local(ts)],
            confidence=0.8, dependencies=["flag_anomaly for the same episode"],
            expected_outcome="Cause found and repaired before the coldest hours.",
            verification_plan="A corrective work order for HP1 is completed and the COP gap closes.")
        if occupied:
            yield Decision(
                timestamp_utc=ts, affected_assets=["HP1"] + occupied, issue_type="heating_comfort", action="optimize_energy",
                priority="high", episode_id=episode, stage="detected",
                reason=(f"Protect the {len(occupied)} occupied rooms while HP1 is degraded: keep their setpoints at the upper part of the "
                        f"comfort band ({COMFORT[0]:.0f} to {COMFORT[1]:.0f} °C), keep vacant rooms on the 18 °C setback, and do not shed "
                        "heating load in expensive hours. Comfort is not traded for cost. Effect is simulated, not measured."),
                evidence=evidence[:1] + [f"events.jsonl: {len(occupied)} rooms occupied at {fmt_local(ts)}"],
                expected_outcome="Occupied rooms stay at or above 20 °C (simulated estimate).",
                verification_plan="room_telemetry.csv temperature_c of occupied rooms with closed windows stays at or above 20 °C; escalate if it does not.")


def _in_span(ts: datetime, spans: list[tuple[datetime, datetime | None]]) -> bool:
    return any(start <= ts and (end is None or ts <= end) for start, end in spans)


# --- B: cold snap ahead ------------------------------------------------------------
def _cold_snap(ctx: _Context, spans: list) -> Iterable[Decision]:
    last_snap: datetime | None = None
    for issued in ctx.issues:
        points = ctx.forecasts[issued]
        coldest_t, coldest = min(points, key=lambda p: p[1])
        if coldest > COLD_SNAP_C:
            continue
        if last_snap is not None and issued - last_snap <= timedelta(hours=60):
            last_snap = issued
            continue                                   # same cold spell, forecast again
        new_spell = last_snap
        last_snap = issued
        occupied = ctx.occupied_rooms(issued)
        if not occupied:
            continue
        cold_start = min(t for t, v in points if v <= COLD_SNAP_C)
        prices = ctx.prices_known(issued, max(issued, cold_start - PREHEAT_LOOKBACK), cold_start)
        degraded = _in_span(issued, spans)
        evidence = [f"weather_forecast.csv: issued {fmt_local(issued)}, minimum {coldest:.1f} °C at {fmt_local(coldest_t)}"]
        if prices:
            cheap = sorted(sorted(prices, key=lambda p: p[1])[:PREHEAT_HOURS])
            hours = ", ".join(fmt_local(h, False) for h, _ in cheap)
            mean_cheap = statistics.mean(p for _, p in cheap)
            mean_all = statistics.mean(p for _, p in prices)
            plan = (f"pre-heat in the {len(cheap)} cheapest published hours of the 8 h before the cold starts at {fmt_local(cold_start)} "
                    f"({hours} on {local(cheap[0][0]).date()}, "
                    f"{mean_cheap:.3f} against {mean_all:.3f} EUR/kWh on average)")
            evidence.append(f"tariff.csv: {len(prices)} hourly prices published by {fmt_local(issued)} for the 8 h before the cold starts")
        else:
            plan = (f"pre-heat in the 8 h before the cold starts at {fmt_local(cold_start)}; day-ahead prices for those hours "
                    "are not published yet (they come at 13:00 local the day before), so the cheapest hours are chosen then")
        yield Decision(
            timestamp_utc=issued, affected_assets=["HP1"] + occupied, issue_type="heating_comfort", action="optimize_energy",
            priority="high" if degraded else "medium", episode_id=f"heating_comfort:cold_snap:{local(issued).date().isoformat()}",
            stage="forecast",
            reason=(f"Cold snap ahead: forecast minimum {coldest:.1f} °C at {fmt_local(coldest_t)}. For the {len(occupied)} occupied rooms, "
                    f"{plan}: raise setpoints to at most {COMFORT[1]:.0f} °C, never below {COMFORT[0]:.0f} °C. "
                    + ("HP1 is currently degraded, so comfort comes before cost. " if degraded else "")
                    + "Vacant rooms stay on setback. Savings are a simulated estimate, not a measurement."),
            evidence=evidence, confidence=0.6,
            expected_outcome="Occupied rooms enter the cold hours warm; part of the heating runs in cheaper hours (simulated).",
            verification_plan="Occupied rooms with closed windows stay within 20 to 23 °C through the forecast minimum; compare with measured weather.csv.")


# --- C: guest reports a cold room --------------------------------------------------
def _cold_requests(ds: Dataset, ctx: _Context, spans: list) -> Iterable[Decision]:
    requests = [dict(r, ts=parse_ts(r["timestamp_utc"]), due=parse_ts(r["response_due_utc"]))
                for r in ds.rows("guest_requests") if r["request_type"] == "temperature_cold" and r.get("room_id")]
    if not requests:
        return
    pending: dict[str, list[dict]] = defaultdict(list)
    for r in sorted(requests, key=lambda r: r["ts"]):
        pending[r["room_id"]].append(r)
    last: dict[str, dict] = {}
    snapshot: dict[str, dict | None] = {}
    for row in ds.rows("room_telemetry"):
        room = row["room_id"]
        queue = pending.get(room)
        if not queue:
            continue
        ts = parse_ts(row["timestamp_utc"])
        while queue and ts > queue[0]["ts"]:
            snapshot[queue.pop(0)["request_id"]] = last.get(room)
        last[room] = row
    for r in requests:
        room, t, lang = r["room_id"], r["ts"], r.get("language") or "en"
        seen = snapshot.get(r["request_id"], last.get(room))
        temp = to_float(seen["temperature_c"]) if seen else None
        setpoint = to_float(seen["setpoint_c"]) if seen else None
        window_open = bool(seen) and seen.get("window_open") == "1"
        degraded = _in_span(t, spans)
        target = COMFORT[1] if degraded or (temp is not None and temp < COMFORT[0]) else 22.0
        if setpoint is not None:
            target = max(target, min(setpoint, COMFORT[1]))
        when = fmt_local(parse_ts(seen["timestamp_utc"])) if seen else "no reading"
        reading = (f"{temp:.1f} °C" if temp is not None else "temperature missing") + (
            f", setpoint {setpoint:.0f} °C" if setpoint is not None else ", setpoint missing") + (
            ", window open" if window_open else ", window closed")
        cause = ("window is open" if window_open else
                 "heat pump is degraded (see HP1 episode)" if degraded else
                 "room is below the comfort band" if temp is not None and temp < COMFORT[0] else
                 "reading is inside the comfort band; the guest feels cold anyway" if temp is not None else
                 "no valid reading; act on the guest's report")
        episode = f"heating_comfort:{room}:{local(t).date().isoformat()}"
        evidence = [f"guest_requests.csv:{r['request_id']} temperature_cold {room}, answer due {fmt_local(r['due'])}",
                    f"room_telemetry.csv:{room}:{when} {reading}"]
        consent = r.get("requires_guest_consent") == "required"
        yield Decision(
            timestamp_utc=t, affected_assets=[room], issue_type="heating_comfort", action="adjust_room_setpoint",
            priority="high" if (temp is not None and temp < COMFORT[0]) or degraded else "medium",
            episode_id=episode, stage="request",
            reason=(f"Guest in {room} reports cold. Last reading: {reading}. Likely cause: {cause}. Set the setpoint to {target:.0f} °C, "
                    f"inside the comfort band; this is done remotely, nobody enters the room."),
            evidence=evidence, guest_request_ids=[r["request_id"]], confidence=0.7,
            expected_outcome=f"Room reaches at least {COMFORT[0]:.0f} °C (simulated, not measured).",
            verification_plan=("temperature_c of the room rises within 1 h; if not, request an inspection, which needs approval"
                               + (" and the guest's consent" if consent else "") + "."))
        text = COLD_REPLY.get(lang, COLD_REPLY["en"]).format(
            room=room, sp=target, extra=WINDOW_HINT.get(lang, WINDOW_HINT["en"]) if window_open else "")
        yield Decision(
            timestamp_utc=t, affected_assets=[room], issue_type="heating_comfort", action="notify_guest",
            priority="high", episode_id=episode, stage="request",
            reason=(f"Answer the cold-room report before {fmt_local(r['due'], False)} in the guest's language ({lang}). "
                    "Proposed message, not a confirmed delivery."),
            evidence=evidence, guest_request_ids=[r["request_id"]],
            expected_outcome="Guest knows that something was done.",
            verification_plan="No second cold report from this room within the stay.",
            extra={"proposed_message": text, "message_language": lang})
