"""Budget and staff figures for the dashboard, read from the dataset as it is.

Nothing here feeds a decision. Both functions summarise the year for planning:

* ``budget`` prices electricity with the hourly tariff and splits it by the parts the dataset meters
  separately. Electricity is the only thing the dataset prices: there is no water price, no wage and
  no cost on a work order, so those appear as volumes and counts, never as invented euros.
* ``staff`` lists who works in and for the building, internal and external, with what they did and
  how reliably. The dataset has resource ids, no names and no contact details.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from statistics import median
from typing import Any

from .dataset import Dataset, parse_ts
from .signals import local

STEP_H = 0.25                     # telemetry interval in hours
ON_TIME_H = 4.0                   # a work order counts as on schedule if finished within this many hours of its slot


def _f(value: Any) -> float | None:
    try:
        return float(value) if value not in ("", None) else None
    except (TypeError, ValueError):
        return None


def budget(ds: Dataset) -> dict | None:
    if not (ds.has("energy") and ds.has("tariff")):
        return None
    price = {}
    for r in ds.rows("tariff"):
        t, p = parse_ts(r["timestamp_utc"]), _f(r["price_eur_kwh"])
        if t and p is not None:
            price[t] = p
    fans: dict = {}
    if ds.has("equipment"):
        for r in ds.rows("equipment"):
            if r["metric"] == "fan_kw":
                t, v = parse_ts(r["timestamp_utc"]), _f(r["value"])
                if t and v is not None:
                    fans[t] = v
    parts = ("heat_pump", "fans", "rest")
    months: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    kwh: Counter = Counter()
    eur: Counter = Counter()
    unpriced = 0
    for r in ds.rows("energy"):
        t = parse_ts(r["timestamp_utc"])
        p = price.get(t.replace(minute=0, second=0, microsecond=0)) if t else None
        load = _f(r.get("building_load_kw"))
        if p is None or load is None:
            unpriced += 1
            continue
        hp = _f(r.get("hvac_electric_kw")) or 0.0
        fan = fans.get(t, 0.0)
        split = {"heat_pump": hp, "fans": fan, "rest": max(0.0, load - hp - fan)}
        month = local(t).strftime("%Y-%m")
        for k in parts:
            e = split[k] * STEP_H
            kwh[k] += e
            eur[k] += e * p
            months[month][k] += e * p
        for k in ("pv_kw", "grid_import_kw", "grid_export_kw"):
            e = (_f(r.get(k)) or 0.0) * STEP_H
            kwh[k] += e
            eur[k] += e * p
        months[month]["bill"] += (_f(r.get("grid_import_kw")) or 0.0) * STEP_H * p
    if not kwh:
        return None
    out: dict[str, Any] = {
        "parts": [{"key": k, "kwh": round(kwh[k]), "eur": round(eur[k])} for k in parts],
        "load": {"kwh": round(sum(kwh[k] for k in parts)), "eur": round(sum(eur[k] for k in parts))},
        "bill": {"kwh": round(kwh["grid_import_kw"]), "eur": round(eur["grid_import_kw"])},
        "pv": {"kwh": round(kwh["pv_kw"]), "eur": round(eur["pv_kw"])},
        "export": {"kwh": round(kwh["grid_export_kw"]), "eur": round(eur["grid_export_kw"])},
        "months": [{"month": m, **{k: round(v) for k, v in sorted(vals.items())}} for m, vals in sorted(months.items())],
        "unpriced_intervals": unpriced,
    }
    if ds.has("room_water") and ds.has("water_main") and ds.has("building"):
        floor = {r["id"]: r.get("floor") for r in ds.building.get("building", {}).get("rooms", [])}
        first: dict[str, float] = {}
        last: dict[str, float] = {}
        for r in ds.rows("room_water"):
            v = _f(r["meter_total_l"])
            if v is not None:
                first.setdefault(r["room_id"], v)
                last[r["room_id"]] = v
        per_floor: Counter = Counter()
        for room, v in last.items():
            if floor.get(room) and v >= first[room]:
                per_floor[floor[room]] += v - first[room]
        main = [v for v in (_f(r["meter_total_l"]) for r in ds.rows("water_main")) if v is not None]
        if main and per_floor:
            total = main[-1] - main[0]
            out["water"] = {"total_m3": round(total / 1000, 1), "floors": [{"floor": f, "m3": round(v / 1000, 1)} for f, v in sorted(per_floor.items())],
                            "outside_rooms_m3": round((total - sum(per_floor.values())) / 1000, 1)}
    if ds.has("work_orders"):
        groups: Counter = Counter()
        for w in ds.rows("work_orders"):
            a = w["asset_id"]
            groups[("Rooms" if a.startswith("R") and a[1:].isdigit() else a, w["type"])] += 1
        out["work_orders"] = [{"where": k[0], "type": k[1], "n": n} for k, n in sorted(groups.items(), key=lambda x: -x[1])]
    return out


def staff(ds: Dataset) -> dict | None:
    if not ds.has("staff_roster"):
        return None
    roles: dict[str, str] = {}
    if ds.has("building"):
        for r in ds.building.get("staff", {}).get("resources", []):
            roles[r["resource_id"]] = r.get("role", "")
    rows: dict[str, dict[str, Any]] = {}

    def row(rid: str, role: str = "", internal: bool = True) -> dict[str, Any]:
        return rows.setdefault(rid, {"id": rid, "role": roles.get(rid) or role, "internal": internal, "shifts": 0, "absent": Counter(),
                                     "short_notice": 0, "work": Counter(), "durations": [], "orders": 0, "hours": [], "on_time": 0,
                                     "timed": 0, "postponed": 0})

    for rid in roles:
        row(rid)
    absent_month: dict[str, Counter] = defaultdict(Counter)
    for r in ds.rows("staff_roster"):
        x = row(r["resource_id"], r.get("role", ""))
        start, known = parse_ts(r["start_utc"]), parse_ts(r.get("status_known_utc"))
        if r["status"] == "scheduled":
            x["shifts"] += 1
        else:
            x["absent"][r["status"]] += 1
            if start:
                absent_month[local(start).strftime("%Y-%m")][x["role"] or "other"] += 1
            if start and known and (start - known).total_seconds() < 24 * 3600:
                x["short_notice"] += 1
    if ds.has("events"):
        began: dict[tuple[str, str], Any] = {}
        label = {"cleaning_completed": "rooms cleaned", "robot_floor_cleaning_completed": "floor runs", "vending_restocked": "restocks",
                 "waste_pickup": "pickups", "floor_bin_emptied": "floor bins emptied"}
        for e in ds.events():
            rid, kind, t = e.get("resource_id"), e.get("type"), parse_ts(e.get("timestamp_utc"))
            if not rid or not kind:
                continue
            x = row(rid, internal=rid in roles or rid == "housekeeping")
            where = e.get("room_id") or e.get("asset_id") or ""
            if kind in ("cleaning_started", "robot_floor_cleaning_started"):
                began[(rid, where)] = t
            if kind in label:
                x["work"][label[kind]] += 1
                t0 = began.pop((rid, where), None)
                if t0 and t and kind != "vending_restocked":
                    x["durations"].append((t - t0).total_seconds() / 60)
    misses = Counter()
    if ds.has("events"):
        for e in ds.events():
            if e.get("type") == "vending_out_of_stock":
                misses["VENDOR_EXT"] += 1
            elif e.get("type") == "waste_bin_full":
                misses["MUNICIPAL_SERVICE"] += 1
    if ds.has("work_orders"):
        for w in ds.rows("work_orders"):
            rid = w.get("assigned_to")
            if not rid:
                continue
            x = row(rid, internal=rid in roles)
            x["orders"] += 1
            created, sched, done = parse_ts(w["created_utc"]), parse_ts(w.get("scheduled_utc")), parse_ts(w.get("completed_utc"))
            if w.get("status") == "postponed":
                x["postponed"] += 1
            if created and done:
                x["hours"].append((done - created).total_seconds() / 3600)
            if sched and done:
                x["timed"] += 1
                x["on_time"] += (done - sched).total_seconds() <= ON_TIME_H * 3600
    order = {"cleaner": 0, "robot": 1, "technician": 2, "on_call_housekeeping": 3}
    out = []
    for x in sorted(rows.values(), key=lambda x: (not x["internal"], order.get(x["role"], 9), x["id"])):
        out.append({"id": x["id"], "role": x["role"], "internal": x["internal"], "shifts": x["shifts"], "absent": dict(x["absent"]),
                    "short_notice": x["short_notice"], "work": dict(x["work"]),
                    "median_min": round(median(x["durations"]), 1) if x["durations"] else None,
                    "orders": x["orders"], "median_h": round(median(x["hours"]), 1) if x["hours"] else None,
                    "on_time": x["on_time"], "timed": x["timed"], "postponed": x["postponed"], "misses": misses.get(x["id"], 0)})
    return {"resources": out, "on_time_h": ON_TIME_H,
            "absent_months": [{"month": m, **dict(c)} for m, c in sorted(absent_month.items())]}
