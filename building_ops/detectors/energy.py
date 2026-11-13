"""Level 2, building and energy optimisation: a battery plan for each day.

When the day-ahead prices for a day are published (13:00 Vienna time the day before), plan the
battery for that day: charge from PV surplus and in the cheapest hours, discharge in the most
expensive ones. Inputs are only what is known at that moment: the published prices, and the load
and PV of the last complete day as the forecast (two days before the planned day).

The plan moves electricity in time; it does not touch heating setpoints, so the comfort band is
never involved. Pre-heating before a cold snap is decided in S03.

Assumptions, stated because the dataset does not fix them: electricity fed into the grid earns
nothing; the battery starts the day at its lower bound; charging and discharging each lose the
square root of the round-trip efficiency. Every figure a decision carries is a simulated estimate.
"""
from __future__ import annotations

import math
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Iterable

from ..dataset import Dataset, parse_ts, to_float
from ..decisions import Decision
from ..signals import fmt_local, local

IMPLEMENTED = True

STEP_KWH = 5.0                 # resolution of the plan
CYCLE_COST = 0.004             # EUR per kWh moved: keeps the plan from cycling for nothing
MIN_SAVING_EUR = 10.0          # below this a day's plan is routine and is not logged as a decision


def battery(ds: Dataset) -> dict[str, float]:
    spec = next((a for a in ds.building.get("building", {}).get("assets", []) if a.get("id") == "BAT1"), {})
    lo, hi = spec.get("soc_bounds_kwh", [10, 95])
    eff = math.sqrt(spec.get("round_trip_efficiency", 0.9))
    return {"lo": float(lo), "hi": float(hi), "charge": float(spec.get("max_charge_kw", 40)),
            "discharge": float(spec.get("max_discharge_kw", 40)), "eff": eff}


def plan_day(prices: list[float], net: list[float], bat: dict[str, float]) -> tuple[list[float], float, float]:
    """Cheapest battery schedule for one day by dynamic programming over the state of charge.

    prices and net (load minus PV, kWh per hour) have one entry per hour. Returns the change of the
    state of charge per hour (positive = charging), the cost with the plan and the cost without a battery.
    """
    states = [bat["lo"] + i * STEP_KWH for i in range(int((bat["hi"] - bat["lo"]) / STEP_KWH) + 1)]
    moves = [m * STEP_KWH for m in range(-int(bat["discharge"] / STEP_KWH), int(bat["charge"] / STEP_KWH) + 1)]
    n = len(prices)
    best = [[math.inf] * len(states) for _ in range(n + 1)]
    back = [[0.0] * len(states) for _ in range(n + 1)]
    best[0][0] = 0.0
    for h in range(n):
        for i, soc in enumerate(states):
            if best[h][i] == math.inf:
                continue
            for move in moves:
                j = i + int(round(move / STEP_KWH))
                if not 0 <= j < len(states):
                    continue
                grid = net[h] + (move / bat["eff"] if move > 0 else move * bat["eff"])
                cost = best[h][i] + max(0.0, grid) * prices[h] + abs(move) * CYCLE_COST
                if cost < best[h + 1][j]:
                    best[h + 1][j], back[h + 1][j] = cost, move
    j = min(range(len(states)), key=lambda k: best[n][k])
    plan = [0.0] * n
    for h in range(n, 0, -1):
        plan[h - 1] = back[h][j]
        j -= int(round(back[h][j] / STEP_KWH))
    with_plan = cost_of(plan, prices, net, bat)
    without = sum(max(0.0, x) * p for x, p in zip(net, prices))
    return plan, with_plan, without


def cost_of(plan: list[float], prices: list[float], net: list[float], bat: dict[str, float]) -> float:
    """Grid cost of a day when the battery follows `plan` against the given net load.

    The plan is clipped to what the battery can do, so it can also be run against the measured day.
    """
    soc, cost = bat["lo"], 0.0
    for move, price, x in zip(plan, prices, net):
        move = max(bat["lo"] - soc, min(bat["hi"] - soc, move))
        soc += move
        grid = x + (move / bat["eff"] if move > 0 else move * bat["eff"])
        cost += max(0.0, grid) * price
    return cost


class Days:
    """Hourly prices, load and PV per Vienna day."""

    def __init__(self, ds: Dataset):
        self.price: dict[date, dict[int, float]] = defaultdict(dict)
        self.published: dict[date, datetime] = {}
        for r in ds.rows("tariff"):
            ts, p, pub = parse_ts(r.get("timestamp_utc")), to_float(r.get("price_eur_kwh")), parse_ts(r.get("published_utc"))
            if ts is None or p is None or pub is None:
                continue
            l = local(ts)
            self.price[l.date()][l.hour] = p
            self.published[l.date()] = max(self.published.get(l.date(), pub), pub)
        load: dict[date, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
        pv: dict[date, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
        imp: dict[date, dict[int, list[float]]] = defaultdict(lambda: defaultdict(list))
        for r in ds.rows("energy"):
            ts = parse_ts(r.get("timestamp_utc"))
            if ts is None:
                continue
            l = local(ts)
            for store, key in ((load, "building_load_kw"), (pv, "pv_kw"), (imp, "grid_import_kw")):
                v = to_float(r.get(key))
                if v is not None:                       # a blank reading is missing, not zero
                    store[l.date()][l.hour].append(v)
        mean = lambda d: {h: sum(v) / len(v) for h, v in d.items() if v}
        self.load = {d: mean(v) for d, v in load.items()}
        self.pv = {d: mean(v) for d, v in pv.items()}
        self.grid_import = {d: mean(v) for d, v in imp.items()}

    def hours(self, day: date) -> list[int]:
        return sorted(self.price.get(day, {}))

    def net(self, day: date, hours: list[int]) -> list[float] | None:
        load, pv = self.load.get(day), self.pv.get(day)
        if not load or not pv or any(h not in load or h not in pv for h in hours):
            return None
        return [load[h] - pv[h] for h in hours]


def _spans(plan: list[float], hours: list[int], sign: int) -> str:
    """'01:00-05:00 (60 kWh)' for the charging (sign 1) or discharging (sign -1) hours."""
    out, start, total = [], None, 0.0
    for h, move in list(zip(hours, plan)) + [(None, 0.0)]:
        if h is not None and move * sign > 0:
            start = h if start is None else start
            total += abs(move)
            last = h
        elif start is not None:
            out.append(f"{start:02d}:00-{(last + 1) % 24:02d}:00 ({total:.0f} kWh)")
            start, total = None, 0.0
    return ", ".join(out) or "none"


def detect(ds: Dataset) -> Iterable[Decision]:
    days, bat = Days(ds), battery(ds)
    for day in sorted(days.price):
        hours = days.hours(day)
        if len(hours) < 23 or day not in days.published:
            continue
        basis = day - timedelta(days=2)                  # the last complete day when the prices appear
        net = days.net(basis, hours)
        if net is None:
            continue
        prices = [days.price[day][h] for h in hours]
        plan, with_plan, without = plan_day(prices, net, bat)
        saving = without - with_plan
        if saving < MIN_SAVING_EUR:
            continue
        at = days.published[day]
        surplus = sum(-x for x in net if x < 0)
        yield Decision(
            timestamp_utc=at, affected_assets=["BAT1", "PV1"], issue_type="energy_optimization", action="optimize_energy",
            priority="low", episode_id=f"energy_optimization:BAT1:{day.isoformat()}",
            reason=(f"Battery plan for {day.strftime('%A')} {day.isoformat()}, made when its prices were published: charge "
                    f"{_spans(plan, hours, 1)}, discharge {_spans(plan, hours, -1)} (Vienna time). Prices range from "
                    f"{min(prices):.3f} to {max(prices):.3f} EUR/kWh and about {surplus:.0f} kWh of PV surplus is expected. "
                    f"Simulated estimate: {with_plan:.1f} EUR grid cost instead of {without:.1f} EUR without a battery. "
                    "The plan moves electricity in time only; no setpoint changes, the comfort band is not involved."),
            evidence=[f"tariff.csv: {len(hours)} hourly prices for {day.isoformat()}, published {fmt_local(at)}",
                      f"energy.csv: load and PV of {basis.isoformat()} as the forecast, the last complete day at that time",
                      "building.json: BAT1 usable 100 kWh, 40 kW, state of charge 10 to 95 kWh, round-trip efficiency 0.9"],
            confidence=0.5,
            expected_outcome=f"About {saving:.1f} EUR lower grid cost that day than without a battery (simulated on a forecast, not measured).",
            verification_plan="energy.csv of that day: grid import in the expensive hours, PV exported, state of charge within 10 to 95 kWh.",
            extra={"plan_kwh": [round(x, 1) for x in plan], "plan_hours_local": hours, "simulated": True})
