"""Detectors: one module per scenario class.

A detector reads the dataset and yields `Decision` objects. It must use only
what was known at the decision time, give evidence for every decision, and
group everything about one incident under one `episode_id`.
"""
from __future__ import annotations

from typing import Callable, Iterable

from ..dataset import Dataset
from ..decisions import Decision
from . import energy, logistics, s01_turnaround, s02_water_leak, s03_energy_comfort, s04_maintenance

Detector = Callable[[Dataset], Iterable[Decision]]

# name -> (detector, implemented?)
REGISTRY: dict[str, tuple[Detector, bool]] = {
    "s01_turnaround": (s01_turnaround.detect, s01_turnaround.IMPLEMENTED),
    "s02_water_leak": (s02_water_leak.detect, s02_water_leak.IMPLEMENTED),
    "s03_energy_comfort": (s03_energy_comfort.detect, s03_energy_comfort.IMPLEMENTED),
    "s04_maintenance": (s04_maintenance.detect, s04_maintenance.IMPLEMENTED),
    "energy": (energy.detect, energy.IMPLEMENTED),
    "logistics": (logistics.detect, logistics.IMPLEMENTED),
}
