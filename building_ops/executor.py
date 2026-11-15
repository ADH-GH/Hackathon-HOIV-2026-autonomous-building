"""Mock executor: turns autonomous decisions into a simulated action trail.

The data is a replay; nothing here changes the building. Every record is
labelled `simulated`. Decisions that need approval or consent are queued, not run.
"""
from __future__ import annotations

from typing import Any

from .decisions import DecisionError, validate_decision


def execute(decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    for d in decisions:
        validate_decision(d, require_risk_context=True)
        if d["event_id"] in seen:
            raise DecisionError("duplicate event_id before simulated execution")
        seen.add(d["event_id"])
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
