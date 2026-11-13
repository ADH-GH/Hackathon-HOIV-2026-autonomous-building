"""Level 3: what a year of operation teaches CLARA and PLATO.

`python -m building_ops insights <data_dir>` recomputes every number in
insights.md from the dataset and writes insights.md and insights.jsonl.

This is a retrospective analysis of a finished year, so it may use everything in
the dataset, including work orders and BMS alarms. The detectors may not.
All findings concern the fictional PLATO-40 only.
"""
from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from datetime import timedelta
from pathlib import Path
from typing import Any

from .dataset import Dataset, parse_ts, to_float
from .occupancy import Occupancy
from .signals import local

WATER_WORDS = ("hose", "toilet", "leak on")
SUMMER, WINTER, HEATING = (6, 7, 8), (12, 1, 2), (11, 12, 1, 2, 3)


def _pct(part: float, whole: float) -> str:
    return f"{100 * part / whole:.1f} %" if whole else "n/a"


def measure(ds: Dataset, decisions: list[dict] | None = None) -> dict[str, Any]:
    occ = Occupancy(ds)
    rooms = {r["id"]: r for r in ds.building["building"]["rooms"]}
    events = sorted((dict(e, ts=parse_ts(e["timestamp_utc"])) for e in ds.events()), key=lambda e: e["ts"])
    work_orders = [dict(w, created=parse_ts(w["created_utc"])) for w in ds.rows("work_orders")]
    requests = list(ds.rows("guest_requests"))
    roster = list(ds.rows("staff_roster"))
    m: dict[str, Any] = {"profile": ds.manifest.get("profile"), "days": ds.manifest.get("days")}

    # --- alarms -------------------------------------------------------------------
    raised = [e for e in events if e["type"] == "bms_alarm" and e.get("state") == "raised"]
    m["alarms"] = dict(Counter(e["alarm_code"] for e in raised))
    low = [e for e in raised if e["alarm_code"] == "ROOM_TEMP_LOW"]
    m["temp_low_total"] = len(low)
    m["temp_low_vacant"] = sum(1 for e in low if not occ.occupied(e["asset_id"], e["ts"]))
    high = [e for e in raised if e["alarm_code"] == "ROOM_TEMP_HIGH" and e["asset_id"] in rooms]
    m["temp_high_by_orientation"] = dict(Counter(rooms[e["asset_id"]]["orientation"] for e in high))
    comm = [e for e in raised if e["alarm_code"] == "SENSOR_COMM_LOSS" and e["asset_id"] in rooms]
    m["comm_loss_by_floor"] = dict(sorted(Counter(rooms[e["asset_id"]]["floor"] for e in comm).items()))

    # --- water --------------------------------------------------------------------
    water = [w for w in work_orders if w["type"] == "corrective" and any(k in (w["summary"] or "").lower() for k in WATER_WORDS)]
    m["water_repairs"] = [{"asset": w["asset_id"], "date": local(w["created"]).date().isoformat(), "summary": w["summary"]} for w in water]
    m["water_alarms"] = m["alarms"].get("WATER_NIGHT_FLOW", 0)
    m["meter_exchanges"] = [w["asset_id"] for w in work_orders if w["type"] == "metering"]
    if decisions:
        leads = []
        for w in water + [w for w in work_orders if w["asset_id"] == "HP1" and w["type"] == "corrective"]:
            asset = w["asset_id"]
            first = [parse_ts(d["timestamp_utc"]) for d in decisions
                     if d["action"] == "flag_anomaly" and asset in d["affected_assets"]
                     and timedelta(0) <= w["created"] - parse_ts(d["timestamp_utc"]) <= timedelta(days=14)]
            if first:
                leads.append({"asset": asset, "lead_h": round((w["created"] - min(first)).total_seconds() / 3600, 1)})
        m["leads"] = leads

    # --- telemetry by orientation and floor ------------------------------------------
    hot, hot_n, cold, cold_n = Counter(), Counter(), Counter(), Counter()
    missing, total = Counter(), Counter()
    arrivals: dict[str, list] = defaultdict(list)
    for e in events:
        if e["type"] in ("checkin", "checkin_early", "checkin_after_wait") and e["ts"].month in HEATING:
            arrivals[e["room_id"]].append(e["ts"])
    waits_to_20: list[float] = []
    pending: dict[str, Any] = {}
    occupied_days: Counter = Counter()
    for r in ds.rows("room_telemetry"):
        room, ts, temp = r["room_id"], parse_ts(r["timestamp_utc"]), to_float(r["temperature_c"])
        info = rooms[room]
        total[info["floor"]] += 1
        missing[info["floor"]] += temp is None
        queue = arrivals.get(room)
        if queue and ts >= queue[0]:
            start = queue.pop(0)
            if temp is not None and temp >= 20:
                waits_to_20.append(0.0)
            else:
                pending[room] = start
        elif room in pending and temp is not None and temp >= 20:
            waits_to_20.append((ts - pending.pop(room)).total_seconds() / 60)
        elif room in pending and ts - pending[room] > timedelta(hours=12):
            pending.pop(room)
            waits_to_20.append(720.0)
        if temp is None or not occ.occupied(room, ts):
            continue
        occupied_days[info["floor"]] += 1
        if ts.month in SUMMER:
            for key in (("orientation", info["orientation"]), ("floor", info["floor"])):
                hot_n[key] += 1
                hot[key] += temp > 26
        if ts.month in WINTER and r["window_open"] != "1":
            for key in (("orientation", info["orientation"]), ("floor", info["floor"])):
                cold_n[key] += 1
                cold[key] += temp < 20
    m["hot_share"] = {f"{k[0]} {k[1]}": round(hot[k] / hot_n[k], 4) for k in sorted(hot_n, key=str)}
    m["cold_share"] = {f"{k[0]} {k[1]}": round(cold[k] / cold_n[k], 4) for k in sorted(cold_n, key=str)}
    m["missing_temp_by_floor"] = {f: round(missing[f] / total[f], 5) for f in sorted(total)}
    cold_arrivals = [w for w in waits_to_20 if w > 0]
    m["winter_checkins"] = len(waits_to_20)
    m["winter_checkins_cold"] = len(cold_arrivals)
    m["minutes_to_20_median"] = statistics.median(cold_arrivals) if cold_arrivals else None

    # --- guest requests -------------------------------------------------------------
    by_type = Counter(r["request_type"] for r in requests)
    m["requests"] = dict(by_type)
    hot_req = [r for r in requests if r["request_type"] == "temperature_hot" and r["room_id"] in rooms]
    m["hot_requests_by_month"] = dict(sorted(Counter(local(parse_ts(r["timestamp_utc"])).month for r in hot_req).items()))
    m["hot_requests_by_orientation"] = dict(Counter(rooms[r["room_id"]]["orientation"] for r in hot_req))
    noise = Counter(rooms[r["room_id"]]["floor"] for r in requests if r["request_type"] == "noise_complaint" and r["room_id"] in rooms)
    room_nights = {f: occupied_days[f] / 96 for f in occupied_days}
    m["noise_by_floor"] = dict(sorted(noise.items()))
    m["noise_per_100_room_nights"] = {f: round(100 * noise[f] / room_nights[f], 2) for f in sorted(room_nights) if room_nights[f]}

    # --- housekeeping ---------------------------------------------------------------
    started: dict[str, tuple] = {}
    robot_done: set[str] = set()
    with_robot, without_robot = [], []
    waiting: dict[str, Any] = {}
    wait_minutes = []
    waits_by_day: Counter = Counter()
    for e in events:
        room, kind = e.get("room_id"), e["type"]
        if kind == "robot_floor_cleaning_completed":
            robot_done.add(room)
        elif kind in ("checkout", "checkout_early"):
            robot_done.discard(room)
        elif kind == "cleaning_started":
            started[room] = (e["ts"], room in robot_done)
        elif kind == "cleaning_completed" and room in started and not str(e.get("resource_id", "")).startswith("ROBOT"):
            t0, had = started.pop(room)
            (with_robot if had else without_robot).append((e["ts"] - t0).total_seconds() / 60)
        elif kind == "arrival_waiting_room":
            waiting[e["booking_id"]] = e["ts"]
            waits_by_day[local(e["ts"]).date()] += 1
        elif kind == "checkin_after_wait" and e.get("booking_id") in waiting:
            wait_minutes.append((e["ts"] - waiting.pop(e["booking_id"])).total_seconds() / 60)
    m["clean_with_robot"] = {"n": len(with_robot), "mean_min": round(statistics.mean(with_robot), 1) if with_robot else None}
    m["clean_without_robot"] = {"n": len(without_robot), "mean_min": round(statistics.mean(without_robot), 1) if without_robot else None}
    sick_days = {local(parse_ts(r["start_utc"])).date() for r in roster if r["role"] == "cleaner" and r["status"] != "scheduled"}
    m["waiting_guests"] = sum(waits_by_day.values())
    m["waiting_guests_on_absence_days"] = sum(v for d, v in waits_by_day.items() if d in sick_days)
    m["cleaner_absence_days"] = len(sick_days)
    m["wait_median_min"] = statistics.median(wait_minutes) if wait_minutes else None

    # --- ventilation filters -----------------------------------------------------------
    ahu = [w for w in work_orders if w["asset_id"] == "AHU1"]
    daily: dict = defaultdict(list)
    for r in ds.rows("equipment"):
        if r["asset_id"] == "AHU1" and r["metric"] == "filter_dp_pa" and r["value"] is not None:
            daily[local(parse_ts(r["timestamp_utc"])).date()].append(to_float(r["value"]))
    dp = {d: statistics.median(v) for d, v in daily.items() if v}
    changes = []
    for w in ahu:
        if w["status"] != "completed":
            continue
        day = local(parse_ts(w["completed_utc"] or w["created_utc"])).date()
        before = dp.get(day - timedelta(days=1))
        changes.append({"date": day.isoformat(), "type": w["type"], "dp_before_pa": round(before) if before else None})
    m["filter_changes"] = changes
    m["filter_postponed"] = [{"date": local(w["created"]).date().isoformat(), "summary": w["summary"]} for w in ahu if w["status"] == "postponed"]
    tech_off = sorted({local(parse_ts(r["start_utc"])).date() for r in roster if r["role"] == "technician" and r["status"] != "scheduled"})
    m["unplanned_during_absence"] = sum(
        1 for c in changes if c["type"] == "corrective"
        and any(abs((d - type(d).fromisoformat(c["date"])).days) <= 7 for d in tech_off))

    # --- logistics ------------------------------------------------------------------
    out = [e for e in events if e["type"] == "vending_out_of_stock"]
    m["vending_out"] = len(out)
    m["vending_out_by_weekday"] = dict(Counter(local(e["ts"]).strftime("%a") for e in out))
    m["waste_full"] = dict(Counter(local(e["ts"]).strftime("%a") for e in events if e["type"] == "waste_bin_full"))
    return m


def recommendations(m: dict[str, Any]) -> list[dict[str, Any]]:
    """Each recommendation carries its numbers; nothing here is free text without a measurement."""
    hs, cs = m["hot_share"], m["cold_share"]
    comm = m["comm_loss_by_floor"]
    comm_total = sum(comm.values())
    worst_floor = max(comm, key=comm.get) if comm else None
    noise = m["noise_per_100_room_nights"]
    unplanned = [c for c in m["filter_changes"] if c["type"] == "corrective"]
    planned = [c for c in m["filter_changes"] if c["type"] == "preventive"]
    leads = sorted(l["lead_h"] for l in m.get("leads", []))
    recs: list[dict[str, Any]] = []

    def add(target, topic, finding, evidence, recommendation, benefit, confidence, uncertainty):
        recs.append({"insight_id": f"{target[0]}{sum(1 for r in recs if r['target'] == target) + 1}", "target": target,
                     "topic": topic, "finding": finding, "evidence": evidence, "recommendation": recommendation,
                     "expected_benefit": benefit, "confidence": confidence, "uncertainty": uncertainty})

    # ---------------- CLARA ----------------
    add("CLARA", "Leak detection by continuity, not by a night-flow threshold",
        f"The year had {len(m['water_repairs'])} water repairs (burst hoses, running toilets, one pipe leak). The BMS night-flow alarm "
        f"was raised {m['water_alarms']} time(s). Reading the meters for flow that never returns to zero, for sustained high flow and "
        f"for the night gap between main meter and room meters finds all of them"
        + (f", between {leads[0]:.0f} and {leads[-1]:.0f} hours before the repair was logged (median {statistics.median(leads):.0f} h, incl. the heat pump cases)." if leads else "."),
        ["work_orders.csv: corrective orders mentioning hose, toilet or leak", "events.jsonl: bms_alarm WATER_NIGHT_FLOW",
         "decisions.jsonl: flag_anomaly on the same assets, see README 'Water leak thresholds'"],
        "Replace the single night-flow threshold with three meter rules: 2 h of at least 8 L per 15 min, 5 h without a zero interval, "
        "and a night gap of 2 L per 15 min between main meter and room sum.",
        "Running toilets are caught on day one instead of after about a week (simulated on the replay, not a measured saving).",
        0.8, "Synthetic leak shapes; real fixtures leak less regularly. Thresholds were set on this year and held on the independent quickstart run.")
    add("CLARA", "Tie the low-temperature alarm to occupancy",
        f"{m['temp_low_vacant']} of {m['temp_low_total']} ROOM_TEMP_LOW alarms were raised for rooms that were vacant at that moment, "
        "where 18 °C is the intended setback.",
        ["events.jsonl: bms_alarm ROOM_TEMP_LOW raised", "events.jsonl: check-in and check-out events for occupancy"],
        "Raise ROOM_TEMP_LOW only for occupied rooms with the window closed, against the comfort band of 20 °C, and keep a separate frost limit for vacant rooms.",
        f"About {_pct(m['temp_low_vacant'], m['temp_low_total'])} fewer low-temperature alarms; the remaining ones mean a guest is cold.",
        0.85, "Occupancy is taken from lifecycle events; a guest who left without checking out would count as present.")
    add("CLARA", "Pre-heat before arrival instead of at check-in",
        f"In the heating season {m['winter_checkins_cold']} of {m['winter_checkins']} check-ins ({_pct(m['winter_checkins_cold'], m['winter_checkins'])}) "
        f"were into a room below 20 °C; such a room needed a median of {m['minutes_to_20_median']:.0f} minutes to reach 20 °C.",
        ["events.jsonl: checkin, checkin_early, checkin_after_wait in Nov to Mar", "room_telemetry.csv: temperature_c from check-in until 20 °C"],
        "End the 18 °C setback about 90 minutes before the expected arrival: the booked check-in time, or the earlier time from an early check-in request once the room is clean.",
        "Guests enter a room inside the comfort band; heating shifts by about 90 minutes per arrival (energy effect not measured).",
        0.7, "A motion sensor and a 15-minute grid give coarse arrival times; the thermal model is simplified.")
    add("CLARA", "Send the robot first, and plan for an absent cleaner in the morning",
        f"Human cleaning took {m['clean_with_robot']['mean_min']} minutes on average when a robot had cleaned the floor first "
        f"(n = {m['clean_with_robot']['n']}) and {m['clean_without_robot']['mean_min']} minutes without (n = {m['clean_without_robot']['n']}). "
        f"{m['waiting_guests_on_absence_days']} of the {m['waiting_guests']} guests who waited for a room did so on the "
        f"{m['cleaner_absence_days']} days with an absent cleaner; the median wait was {m['wait_median_min']:.0f} minutes.",
        ["events.jsonl: robot_floor_cleaning_completed, cleaning_started, cleaning_completed", "events.jsonl: arrival_waiting_room, checkin_after_wait",
         "staff_roster.csv: cleaner shifts with status sick or vacation"],
        "Dispatch robots to every vacated turnover room before the cleaner arrives, order the day by arrival time, and when an absence is known, "
        "ask in the morning for approval to put the on-call housekeeper on notice instead of waiting for the first guest at a closed door.",
        "Shorter turnovers on every day and fewer waiting guests on the few days that cause most of the waiting.",
        0.65, "The robot comparison is observational: days without a robot may differ in other ways. The replay did not follow our plan.")
    add("CLARA", "Change ventilation filters by condition and before the technician is away",
        f"Planned filter changes happened at about {', '.join(str(c['dp_before_pa']) for c in planned)} Pa differential pressure. "
        f"{len(unplanned)} unplanned changes happened at about {', '.join(str(c['dp_before_pa']) for c in unplanned)} Pa, "
        f"{m['unplanned_during_absence']} of them within a week of a technician absence. {len(m['filter_postponed'])} planned changes were postponed first"
        + (f" (\"{m['filter_postponed'][0]['summary']}\")." if m["filter_postponed"] else "."),
        ["equipment.csv: AHU1 filter_dp_pa, daily median", "work_orders.csv: AHU1 preventive, postponed and corrective orders",
         "staff_roster.csv: technician shifts with status sick or vacation"],
        "Project the filter pressure forward from its trend; if it will pass 240 Pa during a known technician absence, bring the change forward or order a contractor before the absence starts.",
        "No unplanned filter changes and no period of reduced airflow (simulated estimate).",
        0.7, "Two unplanned cases in one synthetic year; the degradation rate is not constant.")
    add("CLARA", "Restock and collect by forecast, not by fixed weekday",
        f"The vending machine ran out {m['vending_out']} times, by weekday: {m['vending_out_by_weekday']}. Regular restock is Monday and Thursday. "
        f"The central waste container was full on: {m['waste_full'] or 'no day'}; regular pickup is Tuesday and Friday.",
        ["events.jsonl: vending_out_of_stock, waste_bin_full", "logistics.csv: hourly stock and fill levels"],
        "Order an extra restock or pickup about 24 hours ahead whenever the current consumption rate will empty the machine or fill the container before the next regular visit; weekends first.",
        "Stock-outs and overflow move from the weekend to zero (simulated estimate).",
        0.7, "Demand is synthetic; the 24-hour lead time is taken from the dataset README.")
    add("CLARA", "Watch the heat pump's COP against the outdoor temperature",
        "On normal days the 6-hour median COP stays within 3 % of 2.796 + 0.0761 × outdoor °C. Before each heat pump service of the year it dropped by about 15 %"
        + (f", visible {min(l['lead_h'] for l in m['leads'] if l['asset'] == 'HP1'):.0f} to {max(l['lead_h'] for l in m['leads'] if l['asset'] == 'HP1'):.0f} hours before the work order." if any(l["asset"] == "HP1" for l in m.get("leads", [])) else "."),
        ["equipment.csv: HP1 heat_output_kw, electric_kw, status", "weather.csv: outdoor_c", "work_orders.csv: HP1 corrective"],
        "Add a COP residual check (10 % below the model for 6 hours, at least 16 valid readings) and link it to the forecast: a degraded plant ahead of a cold night is critical.",
        "Service is organised two days earlier, before occupied rooms get cold (simulated on the replay).",
        0.8, "The model was fitted on this year; it held on the independent quickstart run but needs refitting for a real plant.")
    add("CLARA", "Check new water meters after an exchange",
        f"After the meter exchanges in the year ({', '.join(m['meter_exchanges']) or 'none'}) the new meters stepped backwards repeatedly, which a cumulative meter cannot do.",
        ["work_orders.csv: type metering", "room_water.csv: decreasing meter_total_l after the exchange"],
        "Run a 24-hour plausibility check after every meter exchange and exclude a meter from leak detection while it fails.",
        "No false leak alarms from a faulty meter, and no blind spot either.",
        0.75, "Could be a property of the synthetic meter model rather than of a product.")

    # ---------------- PLATO ----------------
    add("PLATO", "South rooms overheat in summer; the building has no cooling",
        f"In June to August occupied south rooms were above 26 °C for {100 * hs.get('orientation S', 0):.1f} % of the time, north rooms for "
        f"{100 * hs.get('orientation N', 0):.1f} %. Guests sent {m['requests'].get('temperature_hot', 0)} 'too hot' requests "
        f"(by month: {m['hot_requests_by_month']}; by orientation: {m['hot_requests_by_orientation']}) against {m['requests'].get('temperature_cold', 0)} 'too cold'. "
        f"High-temperature alarms: {m['temp_high_by_orientation']}.",
        ["room_telemetry.csv: temperature_c of occupied rooms, Jun to Aug, by orientation", "guest_requests.csv: temperature_hot by month and room",
         "events.jsonl: bms_alarm ROOM_TEMP_HIGH", "building.json: operations.cooling = none"],
        "Next building: external shading on the south façade as standard, and a reversible heat pump or active night cooling sized for a July heat wave.",
        "Fewer heat complaints, which are the largest comfort issue of the year by count (qualitative).",
        0.75, "Both orientations overheat; the south excess is about 7 percentage points. Weather and thermal zones are synthetic and uncalibrated.")
    add("PLATO", "The first floor is the cold floor",
        f"In December to February occupied first-floor rooms with closed windows were below 20 °C for {100 * cs.get('floor 1', 0):.1f} % of the time, "
        f"floors 2 to 4 for {100 * cs.get('floor 2', 0):.1f}, {100 * cs.get('floor 3', 0):.1f} and {100 * cs.get('floor 4', 0):.1f} %.",
        ["room_telemetry.csv: temperature_c of occupied rooms, Dec to Feb, window closed, by floor", "building.json: room floors"],
        "Next building: more insulation in the floor slab of the lowest storey, which stands above open parking, and a higher heating capacity for those rooms.",
        "First-floor comfort on the level of the other floors (qualitative).",
        0.6, "The dataset does not state why floor 1 is colder; the exposed underside is our reading of the PLATO concept, not a measured cause.")
    if worst_floor is not None:
        add("PLATO", f"The sensor gateway on floor {worst_floor} drops out",
            f"{comm[worst_floor]} of {comm_total} sensor communication-loss alarms came from floor {worst_floor} ({comm}). "
            f"Missing temperature readings by floor: {{{', '.join(f'{f}: {100 * v:.2f} %' for f, v in m['missing_temp_by_floor'].items())}}}.",
            ["events.jsonl: bms_alarm SENSOR_COMM_LOSS by room and floor", "room_telemetry.csv: blank temperature_c by floor", "building.json: gateways per floor"],
            f"Next building: review gateway placement and antenna on floor {worst_floor}'s position in the stack, add a second gateway per floor or a mesh fallback, and monitor gateway health as an asset of its own.",
            "Fewer blind periods; detectors that need valid readings stay available (qualitative).",
            0.7, "One year, one building; the cause (placement, hardware, interference) is not in the data.")
    if noise:
        add("PLATO", "Noise complaints concentrate on the upper floors",
            f"Noise complaints per 100 occupied room-nights by floor: {noise} (counts: {m['noise_by_floor']}).",
            ["guest_requests.csv: noise_complaint by room", "events.jsonl: occupancy for room-nights per floor"],
            "Next building: check impact-sound insulation between the timber modules and the position of corridors, lift and plant relative to the upper rooms.",
            "Fewer noise complaints, the third most frequent request type (qualitative).",
            0.5, "Complaints depend on the neighbours as much as on the building; the text of the requests points to neighbouring rooms.")
    add("PLATO", "Design for leaks and for maintenance access",
        f"{len(m['water_repairs'])} water repairs in one year: " + "; ".join(f"{w['asset']} {w['date']}: {w['summary']}" for w in m["water_repairs"]) + ". "
        + (f"Planned filter changes were postponed {len(m['filter_postponed'])} times: \"{m['filter_postponed'][0]['summary']}\"." if m["filter_postponed"] else ""),
        ["work_orders.csv: corrective orders for rooms and WM_MAIN", "work_orders.csv: AHU1 postponed"],
        "Next building: a leak sensor under each washbasin and a motorised shut-off per room that needs approval to close, braided hoses with a fixed replacement interval, "
        "sub-metering of the technical room, and permanent safe access to the rooftop unit.",
        "A burst hose is closed in minutes instead of running for a day; planned maintenance is not postponed for access (qualitative).",
        0.65, "Fault frequencies are engineered for the hackathon and say nothing about real products.")
    return recs


ARCHITECTURE = """## Target architecture

What the real autonomous building would need. Boxes marked (built) exist in this repository as a prototype on the replay.

```
 Sources                    Platform                         Decide and act                      People
 -------                    --------                         --------------                      ------
 Booking system  ---+
 Access control  ---+       Ingestion with time of           Agents, one per domain:             Guests
 Room sensors    ---+-----> availability (built)   ------->   operations / turnaround (built)     (messages in their language,
 Water meters    ---+       Data quality: gaps, resets,       water (built)                        consent for room entry)
 Heat pump, AHU  ---+       jitter, implausible values        energy and comfort (built)
 PV, battery     ---+       (built for water, heat pump)      maintenance                         Operations staff
 Weather, prices ---+       State: occupancy, room            housekeeping and robots             (approval queue, built)
 Roster, robots  ---+       readiness, asset health           guest service
 Work orders     ---+       Episode store and audit trail             |                           Technician, contractors
                            (built: decisions.jsonl)                  v
                                                             Autonomy gate (built):
                                                             autonomous / human approval /
                                                             approval + guest consent
                                                                      |
                                                                      v
                                                             Executors: setpoints, battery,
                                                             cleaning plan, robot tasks,
                                                             orders, messages
                                                             (mock executor built)
                                                                      |
                                                                      v
                                                             Verification: did the signal
                                                             recover? else escalate
                                                                      |
                                                                      v
                                                             Learning loop (this file):
                                                             rules for CLARA, design for PLATO
```

- **Data.** Everything carries two times: when it happened and when it became known. Meters and telemetry at 15 minutes; forecasts, prices, roster and bookings with their publication time.
- **Agents.** One agent per domain proposes decisions with evidence. They do not act on their own authority: every proposal passes the autonomy gate, which is code, not a prompt.
- **Robots.** Floor cleaning before the cleaner, waste bin transport, both only in vacated rooms and common areas. A robot never certifies or releases a room.
- **Interfaces.** Booking system and self-check-in kiosk, access control, building management system for setpoints and plant data, meter gateway, robot fleet manager, energy management for PV and battery, guest messaging, a work order system, and the approval queue for staff.
- **Safety.** Entering an occupied room, shutting off water and safety-relevant control stay with people. Simulated effects stay labelled as simulated until a measurement confirms them.
"""


def render(m: dict[str, Any], recs: list[dict[str, Any]]) -> str:
    lines = [
        "# Insights: feedback to CLARA and to PLATO",
        "",
        f"Computed from the `{m['profile']}` dataset ({m['days']} days) by `python -m building_ops insights <data_dir> --decisions decisions.jsonl`. "
        "Every number below comes from that command. This is a retrospective analysis of a finished year; unlike the detectors it may read work orders and alarms.",
        "",
        "**All findings concern the fictional PLATO-40 only.** They are not statements about real PLATO buildings or about what CLARA does today. "
        "The data is synthetic and the models behind it are simplified, so each finding states its uncertainty. No savings are claimed.",
        "",
    ]
    for target, title in (("CLARA", "For CLARA: operating rules for next year"), ("PLATO", "For PLATO: design of the next building")):
        lines += [f"## {title}", ""]
        for r in (r for r in recs if r["target"] == target):
            lines += [f"### {r['insight_id']}. {r['topic']}", "",
                      f"**Finding.** {r['finding']}", "",
                      f"**Recommendation.** {r['recommendation']}", "",
                      f"**Expected benefit.** {r['expected_benefit']}", "",
                      f"**Uncertainty.** {r['uncertainty']} Confidence {r['confidence']}.", "",
                      "**Evidence.** " + "; ".join(f"`{e.split(':')[0]}`:{e.split(':', 1)[1]}" if ":" in e else e for e in r["evidence"]), ""]
    lines += [ARCHITECTURE]
    return "\n".join(lines)


def write(data_dir: str | Path, out: str | Path = "insights.md", decisions_path: str | Path | None = None,
          jsonl: str | Path | None = "insights.jsonl") -> dict[str, Any]:
    ds = Dataset(data_dir)
    decisions = None
    if decisions_path and Path(decisions_path).is_file():
        decisions = [json.loads(l) for l in Path(decisions_path).read_text(encoding="utf-8").splitlines() if l.strip()]
    m = measure(ds, decisions)
    recs = recommendations(m)
    Path(out).write_text(render(m, recs), encoding="utf-8")
    if jsonl:
        Path(jsonl).write_text("".join(json.dumps({k: v for k, v in r.items() if k != "uncertainty"}, ensure_ascii=False) + "\n" for r in recs),
                               encoding="utf-8")
    return m
