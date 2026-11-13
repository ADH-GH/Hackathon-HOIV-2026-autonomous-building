"""Column-agnostic signal helpers for the detectors.

Pure functions over (timestamp, value) series. Missing values stay missing:
nothing here fills a gap with zero or carries a value forward silently.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, Sequence
from zoneinfo import ZoneInfo

VIENNA = ZoneInfo("Europe/Vienna")

Point = tuple[datetime, float | None]


def local(ts: datetime) -> datetime:
    """UTC timestamp in the building's local time (operations follow Europe/Vienna)."""
    return ts.astimezone(VIENNA)


def fmt_local(ts: datetime, with_date: bool = True) -> str:
    """Vienna wall-clock time with its zone name: '2026-01-24 12:15 CET' or '... CEST' in summer."""
    return local(ts).strftime("%Y-%m-%d %H:%M %Z" if with_date else "%H:%M %Z")


def local_day_time(day, hour: int, minute: int = 0) -> datetime:
    """A Vienna wall-clock moment on `day` as an aware UTC datetime (DST handled by the zone)."""
    from datetime import timezone
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=VIENNA).astimezone(timezone.utc)


def is_night(ts: datetime, start_hour: int = 1, end_hour: int = 5) -> bool:
    """Local night window, where guest usage is lowest. Handles DST via the zone."""
    return start_hour <= local(ts).hour < end_hour


@dataclass(frozen=True)
class Delta:
    start: datetime
    end: datetime
    value: float | None      # consumption in the interval; None if not usable
    flag: str                # ok | missing | reset | gap


def meter_deltas(points: Sequence[Point], step: timedelta, max_gap_steps: int = 1) -> list[Delta]:
    """Interval consumption from a cumulative meter.

    - A blank reading makes the intervals touching it `missing`.
    - A negative step is a meter `reset` or artefact, not consumption.
    - Readings further apart than `max_gap_steps` steps are a `gap`: the total
      is real, but when it was used is unknown, so it is not spread over the gap.
    """
    out: list[Delta] = []
    for (t0, v0), (t1, v1) in zip(points, points[1:]):
        if v0 is None or v1 is None:
            out.append(Delta(t0, t1, None, "missing"))
        elif v1 < v0:
            out.append(Delta(t0, t1, None, "reset"))
        elif t1 - t0 > step * max_gap_steps:
            out.append(Delta(t0, t1, None, "gap"))
        else:
            out.append(Delta(t0, t1, v1 - v0, "ok"))
    return out


def robust_center_spread(values: Iterable[float | None]) -> tuple[float, float] | None:
    """Median and scaled MAD of the usable values; None if there are too few.

    Robust against the outliers we are trying to find, unlike mean and stdev.
    """
    xs = [v for v in values if v is not None]
    if len(xs) < 8:
        return None
    med = statistics.median(xs)
    mad = statistics.median(abs(x - med) for x in xs) * 1.4826
    return med, mad


def robust_z(value: float | None, center: float, spread: float, floor: float) -> float | None:
    """Distance from the baseline in robust standard deviations.

    `floor` is the smallest spread taken seriously, in the unit of the signal:
    a meter that is constant for weeks has a MAD of 0 and would otherwise turn
    every tick into an infinite score.
    """
    if value is None:
        return None
    return (value - center) / max(spread, floor)


@dataclass(frozen=True)
class Episode:
    start: datetime
    end: datetime
    points: int
    peak: float


def episodes(scored: Sequence[tuple[datetime, float | None]], threshold: float,
             min_points: int, max_break: timedelta) -> list[Episode]:
    """Group consecutive above-threshold points into incidents.

    One incident is one episode, however long it lasts: this is what keeps a
    week-long leak from becoming hundreds of alerts. Missing scores neither
    start nor end an episode; a break longer than `max_break` ends it.
    Episodes with fewer than `min_points` hits are dropped as blips.
    """
    found: list[Episode] = []
    start = last = None
    count, peak = 0, float("-inf")

    def close() -> None:
        if start is not None and count >= min_points:
            found.append(Episode(start, last, count, peak))

    for ts, score in scored:
        if score is None or score < threshold:
            if start is not None and ts - last > max_break:
                close()
                start, count, peak = None, 0, float("-inf")
            continue
        if start is not None and ts - last > max_break:
            close()
            start, count, peak = None, 0, float("-inf")
        if start is None:
            start = ts
        last, count, peak = ts, count + 1, max(peak, score)
    close()
    return found
