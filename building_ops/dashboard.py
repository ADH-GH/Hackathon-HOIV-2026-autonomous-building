"""Dashboard: one self-contained HTML file showing every case with its evidence.

For each episode in decisions.jsonl it embeds the slice of the raw data the
decision rests on (meter flow, COP against the model, forecast, room readings,
the room's events of the day), the chain of decisions with autonomy level and
verification, and, where the dataset has one, the work order written later.

Work orders and later events are shown for checking only and are labelled as
such; the detectors never read them. No server, no dependencies, works offline.
"""
from __future__ import annotations

import json
import statistics
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from . import planning
from .dashboard_page import PAGE
from .dataset import Dataset, parse_ts, to_float
from .detectors import energy as energy_plan
from .detectors.s02_water_leak import HIDDEN_MIN_ROOMS, NIGHT
from .detectors.s03_energy_comfort import COP_A, COP_B, HEATING_SEASON_BELOW_C
from .signals import local

PRIORITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}
SCENARIO = {"room_turnaround": "S01", "occupancy_surge": "S05", "water_leak": "S02",
            "data_quality": "S02", "heating_comfort": "S03", "ventilation_maintenance": "S04", "logistics": "LOG", "energy_optimization": "ENG"}


def _read(path: str | Path | None) -> list[dict[str, Any]]:
    if not path or not Path(path).is_file():
        return []
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def _ms(ts: datetime) -> int:
    return int(ts.timestamp() * 1000)


def _kind(episode_id: str) -> tuple[str, str]:
    """(chart kind, subject) from the episode id."""
    parts = episode_id.split(":")
    head, subject = parts[0], parts[1] if len(parts) > 1 else ""
    if head == "water_leak":
        return ("main_gap", "WM_MAIN") if subject == "WM_MAIN" else ("room_flow", subject)
    if head == "energy_optimization":
        return "energy", parts[-1]
    if head == "logistics":
        return "logistics", subject + ":" + (parts[2] if len(parts) > 2 else "")
    if head == "ventilation_maintenance" or (head == "data_quality" and subject == "AHU1"):
        return "ahu", "AHU1"
    if head == "data_quality":
        return "room_meter", subject.replace("WM_", "")
    if head == "heating_comfort":
        if subject == "HP1":
            return "cop", "HP1"
        if subject == "cold_snap":
            return "forecast", "BUILDING"
        return "room_temp", subject
    if subject == "day":
        return "day_plan", "BUILDING"
    return "room_day", subject


def _building(ds) -> dict | None:
    """Rooms with floor and orientation. The dataset has no floor plan; the view derives a schematic from these two."""
    if not ds.has("building"):
        return None
    b = ds.building.get("building", {})
    rooms = [{"id": r["id"], "floor": r.get("floor"), "o": r.get("orientation")} for r in b.get("rooms", []) if r.get("id") and r.get("floor")]
    return {"floors": b.get("floors"), "rooms": rooms, "assets": [a["id"] for a in b.get("assets", []) if a.get("id")]} if rooms else None


def build(data_dir: str | Path, decisions_path: str | Path, out: str | Path,
          actions_path: str | Path | None = None, title: str = "PLATO-40 Autonomous Operations",
          voice_agent: str | None = None, web_fonts: bool = False, api_docs: str | None = None) -> Path:
    ds = Dataset(data_dir)
    decisions = _read(decisions_path)
    actions = {a["event_id"]: a for a in _read(actions_path)}

    episodes: dict[str, dict[str, Any]] = {}
    for d in decisions:
        ep = episodes.setdefault(d["episode_id"], {"id": d["episode_id"], "decisions": []})
        ep["decisions"].append(d)
    for ep in episodes.values():
        ds_ = ep["decisions"]
        ep["kind"], ep["subject"] = _kind(ep["id"])
        ep["scenario"] = "S04" if ep["kind"] == "ahu" else SCENARIO.get(ds_[0]["issue_type"], "Other")
        ep["issue_type"] = ds_[0]["issue_type"]
        ep["start"] = min(parse_ts(d["timestamp_utc"]) for d in ds_)
        ep["end"] = max(parse_ts(d["timestamp_utc"]) for d in ds_)
        ep["priority"] = min((d["priority"] for d in ds_), key=PRIORITY_RANK.get)
        ep["routine"] = (ep["kind"] in ("room_day", "room_temp") and ep["priority"] in ("low", "medium")
                         and not any(d.get("stage") in ("waiting", "released") for d in ds_))

    work_orders = [dict(w, created=parse_ts(w["created_utc"])) for w in ds.rows("work_orders")] if ds.has("work_orders") else []
    events = [dict(e, ts=parse_ts(e.get("timestamp_utc"))) for e in ds.events()] if ds.has("events") else []
    events = sorted((e for e in events if e["ts"] is not None), key=lambda e: e["ts"])   # an event without a time cannot be placed
    requests = [dict(r, ts=parse_ts(r["timestamp_utc"])) for r in ds.rows("guest_requests")] if ds.has("guest_requests") else []

    _water(ds, episodes)
    _heat_pump(ds, episodes)
    _ahu(ds, episodes)
    _logistics(ds, episodes, events)
    _energy(ds, episodes)
    _forecast(ds, episodes)
    _room_temp(ds, episodes)
    _room_days(episodes, events, requests)

    for ep in episodes.values():
        asset = {"room_flow": ep["subject"], "main_gap": "WM_MAIN", "cop": "HP1",
                 "ahu": "AHU1" if ep["issue_type"] == "ventilation_maintenance" else None}.get(ep["kind"])
        if asset:
            later = [w for w in work_orders if w["asset_id"] == asset and w["type"] == "corrective"
                     and ep["start"] <= w["created"] <= ep["start"] + timedelta(days=14)]
            if later:
                w = min(later, key=lambda w: w["created"])
                ep["check"] = {"t": _ms(w["created"]), "text": w["summary"], "id": w["work_order_id"],
                               "lead_h": round((w["created"] - ep["start"]).total_seconds() / 3600, 1)}

    manifest = ds.manifest if ds.has("manifest") else {}
    payload = {
        "title": title,
        "profile": manifest.get("profile", Path(data_dir).name),
        "range": [manifest.get("start_utc"), manifest.get("end_utc")],
        "source": str(decisions_path),
        "budget": planning.budget(ds),      # electricity priced with the tariff, by metered part; planning view only
        "staff": planning.staff(ds),        # who works in and for the building, with what they did and how reliably
        "building": _building(ds),          # floor and orientation per room, for the schematic 3D view
        "apiDocs": api_docs,                # link to the API description; None leaves the link out
        "voiceAgent": voice_agent,          # ElevenLabs agent id; None keeps the page free of any network request
        "actions": actions,
        "episodes": [
            {**{k: v for k, v in ep.items() if k not in ("start", "end")},
             "start": _ms(ep["start"]), "end": _ms(ep["end"])}
            for ep in sorted(episodes.values(), key=lambda e: e["start"])],
    }
    data = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    # The page asks for IBM Plex and Sora and falls back to system fonts. With web_fonts it loads them
    # from Google Fonts, which is the only network request the page then makes (besides opt-in voice).
    fonts = ('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600'
             '&family=IBM+Plex+Sans:wght@400;500;600&family=Sora:wght@500;600;700&display=swap">') if web_fonts else ""
    out.write_text(PAGE.replace("__FONTS__", fonts).replace("__DATA__", data).replace("__TITLE__", title), encoding="utf-8")
    return out


# --- evidence slices ---------------------------------------------------------------
def _water(ds: Dataset, episodes: dict[str, dict]) -> None:
    if not (ds.has("room_water") and ds.has("water_main")):
        return
    want: dict[str, list[tuple[datetime, datetime, dict, str]]] = defaultdict(list)
    for ep in episodes.values():
        if ep["kind"] == "room_flow":
            want[ep["subject"]].append((ep["start"] - timedelta(hours=30), ep["start"] + timedelta(hours=48), ep, "flow"))
        elif ep["kind"] == "room_meter":
            want[ep["subject"]].append((ep["start"] - timedelta(hours=36), ep["start"] + timedelta(hours=12), ep, "meter"))
    need_gap = any(ep["kind"] == "main_gap" for ep in episodes.values())
    prev: dict[str, tuple[datetime, float]] = {}
    room_sum: dict[datetime, float] = defaultdict(float)
    room_count: dict[datetime, int] = defaultdict(int)
    for row in ds.rows("room_water"):
        room, ts, value = row["room_id"], parse_ts(row["timestamp_utc"]), to_float(row["meter_total_l"])
        last = prev.get(room)
        delta = None
        if value is None:
            prev.pop(room, None)
        else:
            prev[room] = (ts, value)
            if last is not None and ts - last[0] == timedelta(minutes=15) and value >= last[1]:
                delta = value - last[1]
                if need_gap:
                    room_sum[ts] += delta
                    room_count[ts] += 1
        for lo, hi, ep, what in want.get(room, ()):
            if lo <= ts <= hi:
                series = ep.setdefault("series", {"t": [], "v": []})
                series["t"].append(_ms(ts))
                series["v"].append((None if delta is None else round(delta, 2)) if what == "flow" else value)
    if not need_gap:
        return
    nights: dict = defaultdict(list)
    last = None
    for row in ds.rows("water_main"):
        ts, value = parse_ts(row["timestamp_utc"]), to_float(row["meter_total_l"])
        if value is None:
            last = None
            continue
        before, last = last, (ts, value)
        if before is None or ts - before[0] != timedelta(minutes=15) or value < before[1]:
            continue
        if NIGHT[0] <= local(ts).hour < NIGHT[1] and room_count.get(ts, 0) >= HIDDEN_MIN_ROOMS:
            nights[local(ts).date()].append((ts, value - before[1] - room_sum[ts]))
    daily = sorted((pts[-1][0], statistics.median(g for _, g in pts)) for pts in nights.values() if len(pts) >= 8)
    for ep in episodes.values():
        if ep["kind"] == "main_gap":
            lo, hi = ep["start"] - timedelta(days=14), ep["start"] + timedelta(days=14)
            ep["series"] = {"t": [_ms(t) for t, _ in daily if lo <= t <= hi],
                            "v": [round(g, 2) for t, g in daily if lo <= t <= hi]}


def _heat_pump(ds: Dataset, episodes: dict[str, dict]) -> None:
    targets = [ep for ep in episodes.values() if ep["kind"] == "cop"]
    if not targets or not ds.has("equipment"):
        return
    outdoor = {parse_ts(r["timestamp_utc"]): to_float(r["outdoor_c"]) for r in ds.rows("weather")}
    hp: dict[datetime, dict] = defaultdict(dict)
    for r in ds.rows("equipment"):
        if r["asset_id"] == "HP1":
            hp[parse_ts(r["timestamp_utc"])][r["metric"]] = r["value"]
    hours: dict[datetime, list[tuple[float, float]]] = defaultdict(list)
    for ts, m in hp.items():
        heat, power, out = to_float(m.get("heat_output_kw")), to_float(m.get("electric_kw")), outdoor.get(ts)
        if m.get("status") == "running" and heat and power and power > 3 and out is not None and out < HEATING_SEASON_BELOW_C:
            hours[ts.replace(minute=0, second=0, microsecond=0)].append((heat / power, COP_A + COP_B * out))
    for ep in targets:
        lo, hi = ep["start"] - timedelta(days=4), ep["start"] + timedelta(days=5)
        keys = sorted(h for h in hours if lo <= h <= hi)
        ep["series"] = {"t": [_ms(h) for h in keys],
                        "v": [round(statistics.median(c for c, _ in hours[h]), 3) for h in keys],
                        "ref": [round(statistics.median(e for _, e in hours[h]), 3) for h in keys]}


def _ahu(ds: Dataset, episodes: dict[str, dict]) -> None:
    targets = [ep for ep in episodes.values() if ep["kind"] == "ahu"]
    if not targets or not ds.has("equipment"):
        return
    hours: dict[datetime, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for r in ds.rows("equipment"):
        if r["asset_id"] == "AHU1" and r["metric"] in ("filter_dp_pa", "fan_kw", "airflow_m3h"):
            value = to_float(r["value"])
            if value is not None:
                hours[parse_ts(r["timestamp_utc"]).replace(minute=0, second=0, microsecond=0)][r["metric"]].append(value)
    for ep in targets:
        lo, hi = ep["start"] - timedelta(days=5), ep["end"] + timedelta(days=12)
        keys = [lo.replace(minute=0, second=0, microsecond=0) + timedelta(hours=i) for i in range(int((hi - lo).total_seconds() // 3600) + 1)]
        pick = lambda h, k: round(statistics.median(hours[h][k]), 2) if h in hours and hours[h][k] else None
        ep["series"] = {"t": [_ms(h) for h in keys], "v": [pick(h, "filter_dp_pa") for h in keys],
                        "fan": [pick(h, "fan_kw") for h in keys], "air": [pick(h, "airflow_m3h") for h in keys]}


def _logistics(ds: Dataset, episodes: dict[str, dict], events: list[dict]) -> None:
    targets = [ep for ep in episodes.values() if ep["kind"] == "logistics"]
    if not targets or not ds.has("logistics"):
        return
    levels: dict[str, list[tuple[datetime, float | None]]] = defaultdict(list)
    for r in ds.rows("logistics"):
        levels[r["asset_id"] + ":" + r["metric"]].append((parse_ts(r["timestamp_utc"]), to_float(r["value"])))
    outages = [e for e in events if e["type"] in ("waste_bin_full", "vending_out_of_stock")]
    for ep in targets:
        lo, hi = ep["start"] - timedelta(days=3), ep["start"] + timedelta(days=5)
        points = [(t, v) for t, v in levels.get(ep["subject"], []) if lo <= t <= hi]
        ep["series"] = {"t": [_ms(t) for t, _ in points], "v": [v for _, v in points]}
        asset = ep["subject"].split(":")[0]
        later = [e for e in outages if e.get("asset_id") == asset and timedelta(0) <= e["ts"] - ep["start"] <= timedelta(days=4)]
        if later:
            e = min(later, key=lambda e: e["ts"])
            ep["outage"] = {"t": _ms(e["ts"]), "type": e["type"], "lead_h": round((e["ts"] - ep["start"]).total_seconds() / 3600, 1)}


def _energy(ds: Dataset, episodes: dict[str, dict]) -> None:
    targets = [ep for ep in episodes.values() if ep["kind"] == "energy"]
    if not targets or not (ds.has("tariff") and ds.has("energy")):
        return
    days, bat = energy_plan.Days(ds), energy_plan.battery(ds)
    for ep in targets:
        day = datetime.fromisoformat(ep["subject"]).date()
        d = ep["decisions"][0]
        hours, plan = d.get("plan_hours_local") or days.hours(day), d.get("plan_kwh") or []
        prices = [days.price[day].get(h) for h in hours]
        base = datetime(day.year, day.month, day.day, tzinfo=local(ep["start"]).tzinfo)
        ep["series"] = {"t": [_ms(base + timedelta(hours=h)) for h in hours], "v": prices, "plan": plan}
        actual, imported = days.net(day, hours), days.grid_import.get(day)
        if actual and imported and all(h in imported for h in hours) and None not in prices and len(plan) == len(hours):
            ep["costs"] = {"replay": round(sum(imported[h] * p for h, p in zip(hours, prices)), 1),
                           "plan": round(energy_plan.cost_of(plan, prices, actual, bat), 1),
                           "no_battery": round(sum(max(0.0, x) * p for x, p in zip(actual, prices)), 1)}


def _forecast(ds: Dataset, episodes: dict[str, dict]) -> None:
    targets = [ep for ep in episodes.values() if ep["kind"] == "forecast"]
    if not targets or not ds.has("weather_forecast"):
        return
    by_issue: dict[datetime, list[tuple[datetime, float]]] = defaultdict(list)
    for r in ds.rows("weather_forecast"):
        issued, target, value = parse_ts(r["issued_utc"]), parse_ts(r["target_utc"]), to_float(r["outdoor_c_forecast"])
        if issued and target and value is not None:
            by_issue[issued].append((target, value))
    measured = {parse_ts(r["timestamp_utc"]): to_float(r["outdoor_c"]) for r in ds.rows("weather")}
    for ep in targets:
        points = sorted(by_issue.get(ep["start"], []))
        ep["series"] = {"t": [_ms(t) for t, _ in points], "v": [v for _, v in points],
                        "ref": [measured.get(t) for t, _ in points]}


def _room_temp(ds: Dataset, episodes: dict[str, dict]) -> None:
    want: dict[str, list[tuple[datetime, datetime, dict]]] = defaultdict(list)
    for ep in episodes.values():
        if ep["kind"] == "room_temp":
            want[ep["subject"]].append((ep["start"] - timedelta(hours=12), ep["start"] + timedelta(hours=12), ep))
    if not want or not ds.has("room_telemetry"):
        return
    for row in ds.rows("room_telemetry"):
        spans = want.get(row["room_id"])
        if not spans:
            continue
        ts = parse_ts(row["timestamp_utc"])
        for lo, hi, ep in spans:
            if lo <= ts <= hi:
                s = ep.setdefault("series", {"t": [], "v": [], "ref": [], "window": []})
                s["t"].append(_ms(ts))
                s["v"].append(to_float(row["temperature_c"]))
                s["ref"].append(to_float(row["setpoint_c"]))
                s["window"].append(1 if row.get("window_open") == "1" else 0)


def _room_days(episodes: dict[str, dict], events: list[dict], requests: list[dict]) -> None:
    by_room_day: dict[tuple[str, Any], list[dict]] = defaultdict(list)
    by_day: dict[Any, list[dict]] = defaultdict(list)
    for e in events:
        day = local(e["ts"]).date()
        by_day[day].append(e)
        if e.get("room_id"):
            by_room_day[(e["room_id"], day)].append(e)
    req_room_day: dict[tuple[str, Any], list[dict]] = defaultdict(list)
    for r in requests:
        req_room_day[(r.get("room_id"), local(r["ts"]).date())].append(r)
    for ep in episodes.values():
        if ep["kind"] == "room_day":
            day = datetime.fromisoformat(ep["id"].split(":")[-1]).date()
            ep["timeline"] = (
                [{"t": _ms(e["ts"]), "type": e["type"], "who": e.get("resource_id") or e.get("booking_id") or ""}
                 for e in by_room_day[(ep["subject"], day)]]
                + [{"t": _ms(r["ts"]), "type": "request: " + r["request_type"], "who": r.get("booking_id") or "", "text": r.get("text")}
                   for r in req_room_day[(ep["subject"], day)]])
            ep["timeline"].sort(key=lambda x: x["t"])
        elif ep["kind"] == "day_plan":
            day = datetime.fromisoformat(ep["id"].split(":")[-1]).date()
            todays = by_day[day]
            waits, open_wait = [], {}
            for e in todays:
                if e["type"] == "arrival_waiting_room":
                    open_wait[e.get("booking_id")] = e
                elif e["type"] == "checkin_after_wait" and e.get("booking_id") in open_wait:
                    w = open_wait.pop(e["booking_id"])
                    waits.append({"room": e.get("room_id"), "from": _ms(w["ts"]), "to": _ms(e["ts"]),
                                  "min": round((e["ts"] - w["ts"]).total_seconds() / 60)})
            count = lambda kind: sum(1 for e in todays if e["type"] == kind)
            ep["day"] = {"checkouts": count("checkout") + count("checkout_early"),
                         "checkins": count("checkin") + count("checkin_early") + count("checkin_after_wait"),
                         "cleanings": count("cleaning_completed"), "oncall": count("oncall_housekeeping_called"),
                         "waits": waits}
