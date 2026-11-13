"""Mock executor: turns autonomous decisions into a simulated action trail.

The data is a replay; nothing here changes the building. Every record is
labelled `simulated`. Decisions that need approval or consent are queued, not run.
"""
from __future__ import annotations

from typing import Any


def execute(decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    trail = []
    for d in decisions:
        if d["requires_human_approval"]:
            status = "awaiting_guest_consent_and_approval" if d.get("requires_guest_consent") else "awaiting_human_approval"
        else:
            status = "executed_in_simulation"
        trail.append({
            "event_id": d["event_id"],
            "timestamp_utc": d["timestamp_utc"],
            "action": d["action"],
            "affected_assets": d["affected_assets"],
            "status": status,
            "simulated": True,
            "note": "Mock executor. No effect was measured; a proposed guest message is not proof of delivery.",
        })
    return trail
