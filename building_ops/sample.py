"""Hand-made sample decisions, to exercise the viewer before any detector exists.

These are NOT results. Asset names, numbers and times are invented for the
interface only and must never be committed as decisions.jsonl. The viewer shows
a banner when it is built from this sample.
"""
from __future__ import annotations

import json
from pathlib import Path

from .decisions import Decision, dedupe
from .executor import execute
from .report import build

NOTE = "SAMPLE: invented for the interface, not derived from data"


def decisions() -> list[dict]:
    raw = [
        Decision("2026-01-07T03:15:00Z", ["sample_room_A"], "water_leak", "flag_anomaly", "high",
                 "Sample: night-time flow stays above the room's own baseline for several hours while the room is vacant.",
                 episode_id="sample-leak-A", evidence=[NOTE], confidence=0.8,
                 expected_outcome="Sample: the anomaly is visible to operations.",
                 verification_plan="Sample: flow returns to the baseline after the inspection."),
        Decision("2026-01-07T03:20:00Z", ["sample_room_A"], "water_leak", "request_inspection", "high",
                 "Sample: inspect the vacant room before the next arrival.",
                 episode_id="sample-leak-A", evidence=[NOTE], dependencies=["flag_anomaly"],
                 verification_plan="Sample: inspection report closes or escalates the episode."),
        Decision("2026-01-09T02:40:00Z", ["sample_room_B"], "water_leak", "request_inspection", "critical",
                 "Sample: the room is occupied, so entering it needs approval and the guest's consent.",
                 episode_id="sample-leak-B", evidence=[NOTE], enters_occupied_room=True,
                 verification_plan="Sample: consent recorded before anyone enters."),
        Decision("2026-01-10T09:05:00Z", ["sample_room_C"], "turnaround_conflict", "schedule_cleaning", "medium",
                 "Sample: early arrival requested; cleaning is moved to the front of the shift.",
                 episode_id="sample-turnaround-C", evidence=[NOTE],
                 expected_outcome="Sample: room cleaned before the realistic time given to the guest.",
                 verification_plan="Sample: housekeeping state changes to cleaned before release."),
        Decision("2026-01-10T09:06:00Z", ["sample_room_C"], "turnaround_conflict", "notify_guest", "medium",
                 "Sample: the guest gets a realistic time instead of the requested one.",
                 episode_id="sample-turnaround-C", evidence=[NOTE], guest_request_ids=["sample-request-1"],
                 verification_plan="Sample: a proposed message is not proof of delivery."),
        Decision("2026-01-12T16:00:00Z", ["sample_heat_pump"], "heating_degradation", "dispatch_technician", "high",
                 "Sample: heating performance is reduced ahead of a forecast cold night.",
                 episode_id="sample-heating", evidence=[NOTE],
                 verification_plan="Sample: performance recovers after the service visit."),
        Decision("2026-01-12T16:05:00Z", ["sample_building"], "heating_degradation", "optimize_energy", "medium",
                 "Sample: pre-heat occupied rooms inside the comfort band during the cheaper hours.",
                 episode_id="sample-heating", evidence=[NOTE],
                 expected_outcome="Sample: simulated estimate only.",
                 verification_plan="Sample: room temperatures stay inside the comfort band overnight."),
    ]
    return dedupe([d.finalize() for d in raw])


def write_sample(out_dir: str | Path) -> Path:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rows = decisions()
    for name, records in (("sample_decisions.jsonl", rows), ("sample_actions.jsonl", execute(rows))):
        (out / name).write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in records),
                                encoding="utf-8")
    return build(out / "sample_decisions.jsonl", out / "sample_report.html", out / "sample_actions.jsonl",
                 title="PLATO-40 decision trail (sample)", sample=True)
