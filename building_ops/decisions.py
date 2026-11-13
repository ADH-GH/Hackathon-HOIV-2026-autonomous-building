"""The decision record and the autonomy rules.

One `Decision` is one line in decisions.jsonl. `finalize()` is the single place
where the autonomy rules of the brief are applied: a detector may ask for more
oversight than the rules require, never for less.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

PRIORITIES = ("critical", "high", "medium", "low")

ACTIONS = (
    "schedule_cleaning", "dispatch_robot", "adjust_room_setpoint", "optimize_energy",
    "block_room", "release_room", "reassign_room", "request_inspection",
    "dispatch_technician", "order_service", "notify_guest", "flag_anomaly",
    "defer_action", "request_human_approval",
)

# Autonomy levels, lowest oversight first.
AUTONOMOUS = "autonomous"
HUMAN_APPROVAL = "human_approval"
APPROVAL_AND_CONSENT = "approval_and_consent"   # spelling of DECISION_CONTRACT.md
LEVELS = (AUTONOMOUS, HUMAN_APPROVAL, APPROVAL_AND_CONSENT)

# Actions that always need a person to approve (brief, "Autonomy Rules").
APPROVAL_ACTIONS = frozenset({
    "dispatch_technician", "block_room", "reassign_room", "request_human_approval",
})
# order_service is autonomous only for these kinds; a contractor call-out is not.
AUTONOMOUS_SERVICES = frozenset({"waste_pickup", "restock"})


class DecisionError(ValueError):
    """A decision that must not be written: it breaks the contract or a safety rule."""


def required_level(action: str, *, service_kind: str | None = None,
                   enters_occupied_room: bool = False, water_shutoff: bool = False,
                   safety_relevant: bool = False, notable_cost: bool = False,
                   outside_comfort_band: bool = False) -> str:
    """The minimum oversight the autonomy rules demand for this action."""
    if enters_occupied_room or water_shutoff or safety_relevant:
        return APPROVAL_AND_CONSENT
    if action in APPROVAL_ACTIONS or notable_cost:
        return HUMAN_APPROVAL
    if action == "order_service" and service_kind not in AUTONOMOUS_SERVICES:
        return HUMAN_APPROVAL
    if action == "adjust_room_setpoint" and outside_comfort_band:
        return HUMAN_APPROVAL
    return AUTONOMOUS


def _utc(ts: datetime | str) -> str:
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    if ts.tzinfo is None:
        raise DecisionError("timestamp without timezone; all timestamps are UTC")
    return ts.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class Decision:
    timestamp_utc: datetime | str
    affected_assets: list[str]
    issue_type: str
    action: str
    priority: str
    reason: str
    # Facts about the action that decide the autonomy level.
    service_kind: str | None = None
    enters_occupied_room: bool = False
    water_shutoff: bool = False
    safety_relevant: bool = False
    notable_cost: bool = False
    outside_comfort_band: bool = False
    # A detector may raise oversight above the rule; it cannot lower it.
    autonomy: str | None = None
    # Recommended fields of the contract.
    episode_id: str | None = None
    stage: str | None = None      # step within an episode; lets one episode hold follow-ups of the same action
    evidence: list[str] = field(default_factory=list)   # references, e.g. room_water.csv:R109:<from>..<to>
    resource_id: str | None = None                      # staff or robot assigned; must be available then
    expected_outcome: str | None = None
    verification_plan: str | None = None
    dependencies: list[str] = field(default_factory=list)
    guest_request_ids: list[str] = field(default_factory=list)
    confidence: float | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def finalize(self) -> dict[str, Any]:
        """Validate, apply the autonomy rules and return the JSON object to write."""
        if self.action not in ACTIONS:
            raise DecisionError(f"unknown action {self.action!r}; document it and add it to ACTIONS")
        if self.priority not in PRIORITIES:
            raise DecisionError(f"priority must be one of {PRIORITIES}, got {self.priority!r}")
        if not self.affected_assets:
            raise DecisionError("affected_assets is empty")
        if not self.reason.strip():
            raise DecisionError("reason is empty; every decision must be explainable")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            raise DecisionError("confidence must be between 0 and 1")
        if not all(isinstance(e, str) for e in self.evidence):
            raise DecisionError("evidence must be an array of strings (DECISION_CONTRACT.md)")
        if self.autonomy is not None and self.autonomy not in LEVELS:
            raise DecisionError(f"autonomy must be one of {LEVELS}")

        needed = required_level(
            self.action, service_kind=self.service_kind,
            enters_occupied_room=self.enters_occupied_room, water_shutoff=self.water_shutoff,
            safety_relevant=self.safety_relevant, notable_cost=self.notable_cost,
            outside_comfort_band=self.outside_comfort_band)
        asked = self.autonomy or needed
        level = max(needed, asked, key=LEVELS.index)

        ts = _utc(self.timestamp_utc)
        assets = sorted(self.affected_assets)
        episode = self.episode_id or f"{self.issue_type}:{'+'.join(assets)}:{ts[:10]}"
        digest = hashlib.sha256(
            json.dumps([episode, self.action, assets, ts, self.stage], sort_keys=True).encode()).hexdigest()[:16]

        out: dict[str, Any] = {
            "event_id": f"dec-{digest}",
            "timestamp_utc": ts,
            "affected_assets": assets,
            "issue_type": self.issue_type,
            "action": self.action,
            "priority": self.priority,
            "reason": self.reason.strip(),
            "requires_human_approval": level != AUTONOMOUS,
            "requires_guest_consent": level == APPROVAL_AND_CONSENT,
            "autonomy": level,
            "episode_id": episode,
            "evidence": self.evidence,
        }
        for key in ("expected_outcome", "verification_plan", "confidence", "service_kind", "resource_id", "stage"):
            value = getattr(self, key)
            if value is not None:
                out[key] = value
        for key in ("dependencies", "guest_request_ids"):
            value = getattr(self, key)
            if value:
                out[key] = value
        out.update(self.extra)
        return out


def dedupe(decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One decision per episode, action and stage: repeated alerts for one incident are spam.

    Keeps the earliest. Sorted by time, then id, so the output is deterministic.
    """
    ordered = sorted(decisions, key=lambda d: (d["timestamp_utc"], d["event_id"]))
    seen: set[tuple[str, str, tuple[str, ...]]] = set()
    kept = []
    for d in ordered:
        key = (d["episode_id"], d["action"], tuple(d["affected_assets"]), d.get("stage"))
        if key in seen:
            continue
        seen.add(key)
        kept.append(d)
    return kept
