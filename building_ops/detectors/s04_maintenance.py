"""S04 The Maintenance Cascade: ventilation filter, sensor gap, technician away.

The air handling unit's filter loads slowly in normal operation (about 1.5 Pa of
differential pressure per day). In a cascade it loads fast, then the pressure
sensor drops out for days, and the technician is not there.

Three steps, each on what was known at that moment:

1. rising:  the 6-hour median pressure climbed 15 Pa or more within 24 hours.
            Flag it and organise the filter change with whoever is really
            available: the technician's next known shift, or a contractor.
2. gap:     the pressure sensor is silent for 6 hours. That is a data gap, not a
            recovery and not a fault by itself. Fan power and airflow are read
            instead, because they come from other sensors.
3. airflow: the fan runs at its limit or the airflow falls below 95 % of nominal.
            The filter is now restricting ventilation, whatever the pressure
            sensor says. Escalate.

A sensor gap with a healthy fan and airflow is reported once as data quality.
Planned reduced operation at night (low fan power, low airflow) is not a fault:
only readings taken at normal fan power are compared.
"""
from __future__ import annotations

import statistics
from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Iterable

from ..dataset import Dataset, parse_ts, to_float
from ..decisions import Decision
from ..signals import fmt_local

IMPLEMENTED = True

STEP = timedelta(minutes=15)
WINDOW = 24                    # 6 h of 15-min readings
MIN_POINTS = 16
RISE_PA_PER_DAY = 15.0         # normal loading in dev: about 1.5 Pa per day; cascades: about 30
RISE_MIN_LEVEL_PA = 140.0      # a fresh filter settling in is not a cascade
GAP_STEPS = 24                 # 6 h without a pressure reading
FAN_LIMIT_KW = 5.3             # the fan saturates at 5.4 kW
AIRFLOW_SHARE = 0.95           # of nominal airflow
RECOVERED_PA = 120.0
REDUCED_FAN_KW = 3.0           # below this the unit runs in planned reduced (night) mode; clean-filter day value is about 3.3
TECH_SOON = timedelta(hours=48)


def _z(ts: datetime) -> str:
    return ts.strftime("%Y-%m-%dT%H:%MZ")


def detect(ds: Dataset) -> Iterable[Decision]:
    nominal = next((a.get("nominal_airflow_m3h") for a in ds.building.get("building", {}).get("assets", [])
                    if a.get("id") == "AHU1"), None) or 4200.0
    tech = [dict(r, start=parse_ts(r["start_utc"]), end=parse_ts(r["end_utc"]), known=parse_ts(r["status_known_utc"]))
            for r in ds.rows("staff_roster") if r["role"] == "technician"]
    orders = [dict(w, created=parse_ts(w["created_utc"])) for w in ds.rows("work_orders") if w["asset_id"] == "AHU1"]

    def next_shift(at: datetime) -> datetime | None:
        starts = []
        for s in tech:
            absent_known = s["status"] != "scheduled" and s["known"] is not None and s["known"] <= at
            if not absent_known and s["end"] and s["end"] > at:
                starts.append(max(s["start"], at))
        return min(starts) if starts else None

    def access_note(at: datetime) -> str:
        known = [w for w in orders if w["created"] <= at and w["status"] == "postponed"]
        return f" An earlier order was postponed: \"{known[-1]['summary']}\"; plan for that." if known else ""

    rows: dict[datetime, dict[str, float | None]] = defaultdict(dict)
    for r in ds.rows("equipment"):
        if r["asset_id"] == "AHU1":
            ts = parse_ts(r["timestamp_utc"])
            if ts:
                rows[ts][r["metric"]] = to_float(r["value"])

    dp_win: deque = deque(maxlen=WINDOW)
    fan_win: deque = deque(maxlen=WINDOW)
    air_win: deque = deque(maxlen=WINDOW)
    medians: deque = deque(maxlen=96)              # 6 h medians of the last 24 h
    silent = 0
    episode: str | None = None
    done: set[str] = set()
    gap_reported = False

    def med(win: deque) -> float | None:
        vals = [v for v in win if v is not None]
        return statistics.median(vals) if len(vals) >= MIN_POINTS else None

    for ts in sorted(rows):
        m = rows[ts]
        dp, fan, air = m.get("filter_dp_pa"), m.get("fan_kw"), m.get("airflow_m3h")
        # Planned reduced operation at night lowers airflow and pressure together. It is not a
        # restriction and not a recovery, so those readings are left out of the comparison.
        reduced = fan is not None and fan < REDUCED_FAN_KW
        dp_win.append(None if reduced else dp)
        fan_win.append(None if reduced else fan)
        air_win.append(None if reduced else air)
        silent = silent + 1 if dp is None else 0
        if dp is not None:
            gap_reported = False
        dp_med, fan_med, air_med = med(dp_win), med(fan_win), med(air_win)
        medians.append(dp_med)
        restricted = (fan_med is not None and fan_med >= FAN_LIMIT_KW) or (air_med is not None and air_med < nominal * AIRFLOW_SHARE)
        state = (f"fan {fan_med:.2f} kW" if fan_med is not None else "fan power missing") + ", " + (
            f"airflow {air_med:.0f} of {nominal:.0f} m3/h nominal" if air_med is not None else "airflow missing")

        # close the episode when a fresh filter is seen
        if episode and dp_med is not None and dp_med < RECOVERED_PA and not restricted:
            episode, done = None, set()

        # 1. fast loading
        day_ago = medians[0] if len(medians) == medians.maxlen else None
        if (episode is None and dp_med is not None and day_ago is not None
                and dp_med - day_ago >= RISE_PA_PER_DAY and dp_med >= RISE_MIN_LEVEL_PA):
            episode = f"ventilation_maintenance:AHU1:{_z(ts)}"
            done = {"rising"}
            nxt = next_shift(ts)
            soon = nxt is not None and nxt - ts <= TECH_SOON
            fact = (f"AHU1 filter pressure rose from {day_ago:.0f} to {dp_med:.0f} Pa in 24 h "
                    f"(6 h medians; normal loading is about 1.5 Pa per day)")
            evidence = [f"equipment.csv:AHU1:filter_dp_pa:{_z(ts - timedelta(hours=30))}..{_z(ts)} 6 h median {day_ago:.0f} -> {dp_med:.0f} Pa",
                        f"equipment.csv:AHU1:{_z(ts - timedelta(hours=6))}..{_z(ts)} {state}"]
            yield Decision(
                timestamp_utc=ts, affected_assets=["AHU1"], issue_type="ventilation_maintenance", action="flag_anomaly",
                priority="high", episode_id=episode, stage="rising",
                reason=(f"The ventilation filter is loading fast: {fact}. Airflow is still normal ({state}), so there is time to act "
                        "before ventilation suffers."),
                evidence=evidence, confidence=0.8,
                expected_outcome="The filter change is organised before airflow drops.",
                verification_plan="After the change the pressure falls to about 90 Pa and fan power to about 3.3 kW.")
            avail = (f"TECH_1's next shift, as known now, starts {fmt_local(nxt)}" if nxt else "no technician shift is known in the roster")
            yield Decision(
                timestamp_utc=ts, affected_assets=["AHU1"] + (["TECH_1"] if soon else []), issue_type="ventilation_maintenance",
                action="dispatch_technician" if soon else "order_service", service_kind=None if soon else "contractor",
                resource_id="TECH_1" if soon else None, priority="high", episode_id=episode, stage="rising",
                reason=(f"Organise the AHU1 filter change: {fact}. {avail}"
                        + ("" if soon else "; that is too late for a filter loading at this rate, so order a contractor")
                        + f". A call-out needs approval.{access_note(ts)}"),
                evidence=evidence + [f"staff_roster.csv: technician availability as known at {fmt_local(ts)}"],
                confidence=0.75, dependencies=["flag_anomaly for the same episode"],
                expected_outcome="Filters replaced before the fan reaches its limit.",
                verification_plan="A work order for AHU1 is completed; pressure and fan power return to the clean-filter level.")

        # 2. the pressure sensor is silent
        if silent == GAP_STEPS and not gap_reported:
            gap_reported = True
            since = ts - STEP * (GAP_STEPS - 1)
            evidence = [f"equipment.csv:AHU1:filter_dp_pa:{_z(since)}..{_z(ts)} no reading for 6 h",
                        f"equipment.csv:AHU1:{_z(ts - timedelta(hours=6))}..{_z(ts)} {state}"]
            if episode and "gap" not in done:
                done.add("gap")
                yield Decision(
                    timestamp_utc=ts, affected_assets=["AHU1"], issue_type="ventilation_maintenance", action="flag_anomaly",
                    priority="high", episode_id=episode, stage="gap",
                    reason=(f"The filter pressure sensor has been silent since {fmt_local(since)}, in the middle of a fast-loading filter. "
                            f"A missing reading is not a recovery. The filter is now followed through fan power and airflow instead: {state}."),
                    evidence=evidence, confidence=0.8,
                    expected_outcome="The open filter case stays open while the sensor is blind.",
                    verification_plan="Fan power below 5.3 kW and airflow at nominal; escalate when either limit is crossed.")
            elif episode is None:
                yield Decision(
                    timestamp_utc=ts, affected_assets=["AHU1"], issue_type="data_quality", action="flag_anomaly",
                    priority="medium" if restricted else "low", episode_id=f"data_quality:AHU1:{_z(since)}", stage="gap",
                    reason=(f"The AHU1 filter pressure sensor has been silent since {fmt_local(since)}. This is a data gap, not a plant fault: "
                            f"{state}. No filter decision is taken on missing data."),
                    evidence=evidence, confidence=0.8,
                    expected_outcome="The sensor or its gateway is checked at the next visit.",
                    verification_plan="Pressure readings return; fan power and airflow stay normal meanwhile.")

        # 3. ventilation is restricted
        if restricted and "airflow" not in done:
            if episode is None:
                episode = f"ventilation_maintenance:AHU1:{_z(ts)}"
            done.add("airflow")
            nxt = next_shift(ts)
            soon = nxt is not None and nxt - ts <= timedelta(hours=24)
            blind = dp_med is None
            fact = (f"{state}" + ("; the pressure sensor gives no valid reading" if blind else f"; filter pressure {dp_med:.0f} Pa"))
            evidence = [f"equipment.csv:AHU1:fan_kw,airflow_m3h:{_z(ts - timedelta(hours=6))}..{_z(ts)} {state}"]
            yield Decision(
                timestamp_utc=ts, affected_assets=["AHU1", "BUILDING"], issue_type="ventilation_maintenance", action="flag_anomaly",
                priority="critical", episode_id=episode, stage="airflow",
                reason=((f"Ventilation is now restricted: {fact}. The fan is at its limit and cannot compensate further"
                         if air_med is not None and air_med < nominal * AIRFLOW_SHARE else
                         f"The fan has reached its limit to hold the airflow: {fact}. Any further loading now reduces ventilation")
                        + (". This is real plant degradation, seen on sensors that are still working, not a data gap." if blind else ".")),
                evidence=evidence, confidence=0.85,
                expected_outcome="The filter change becomes urgent.",
                verification_plan="Airflow back at nominal and fan power at about 3.3 kW after the change.")
            avail = (f"TECH_1's next shift, as known now, starts {fmt_local(nxt)}" if nxt else "no technician shift is known in the roster")
            yield Decision(
                timestamp_utc=ts, affected_assets=["AHU1"] + (["TECH_1"] if soon else []), issue_type="ventilation_maintenance",
                action="dispatch_technician" if soon else "order_service", service_kind=None if soon else "contractor",
                resource_id="TECH_1" if soon else None, priority="critical", episode_id=episode, stage="airflow",
                reason=(f"Replace the AHU1 filters now: {fact}. {avail}"
                        + ("" if soon else "; waiting for it leaves the building under-ventilated, so order a contractor")
                        + f". A call-out needs approval.{access_note(ts)}"),
                evidence=evidence + [f"staff_roster.csv: technician availability as known at {fmt_local(ts)}"],
                confidence=0.8, dependencies=["flag_anomaly for the same episode"],
                expected_outcome="Airflow restored within a day of approval.",
                verification_plan="A corrective work order for AHU1 is completed and the airflow returns to nominal.")
        if not restricted and "airflow" in done and dp_med is not None and dp_med < RECOVERED_PA:
            episode, done = None, set()
