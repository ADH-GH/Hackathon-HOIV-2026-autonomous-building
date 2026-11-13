"""Check a decisions.jsonl against the output contract and the autonomy rules.

Run it before every commit of a submission file. It reads the file as written,
so it also catches decisions that did not come through `Decision.finalize()`.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .decisions import ACTIONS, APPROVAL_ACTIONS, AUTONOMOUS_SERVICES, PRIORITIES

REQUIRED = ("event_id", "timestamp_utc", "affected_assets", "issue_type", "action",
            "priority", "reason", "requires_human_approval")


def check(path: str | Path) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    rows: list[dict[str, Any]] = []
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {n}: not JSON ({exc.msg})")
            continue
        rows.append(row)
        where = f"line {n} ({row.get('event_id', '?')})"
        for key in REQUIRED:
            if key not in row or row[key] in (None, "", []):
                errors.append(f"{where}: missing {key}")
        if row.get("action") not in ACTIONS:
            warnings.append(f"{where}: action {row.get('action')!r} is outside the vocabulary; document it")
        if row.get("priority") not in PRIORITIES:
            errors.append(f"{where}: priority {row.get('priority')!r}")
        if not isinstance(row.get("requires_human_approval"), bool):
            errors.append(f"{where}: requires_human_approval must be true or false")
        if not str(row.get("timestamp_utc", "")).endswith("Z"):
            errors.append(f"{where}: timestamp_utc must be UTC ending in Z")
        action = row.get("action")
        needs_approval = action in APPROVAL_ACTIONS or (
            action == "order_service" and row.get("service_kind") not in AUTONOMOUS_SERVICES)
        if needs_approval and row.get("requires_human_approval") is not True:
            errors.append(f"{where}: {action} without human approval breaks the autonomy rules")
        if row.get("requires_guest_consent") and row.get("requires_human_approval") is not True:
            errors.append(f"{where}: guest consent without human approval")
        if not row.get("evidence"):
            warnings.append(f"{where}: no evidence")

    ids = Counter(r.get("event_id") for r in rows)
    errors += [f"duplicate event_id {i}" for i, c in ids.items() if c > 1]
    spam = Counter((r.get("episode_id"), r.get("action"), tuple(r.get("affected_assets") or []), r.get("stage"))
                   for r in rows if r.get("episode_id"))
    warnings += [f"{c} decisions for episode {k[0]} / {k[1]}: alert spam" for k, c in spam.items() if c > 1]
    if rows != sorted(rows, key=lambda r: str(r.get("timestamp_utc"))):
        warnings.append("decisions are not sorted by timestamp_utc")

    return {
        "file": str(path), "decisions": len(rows), "ok": not errors,
        "errors": errors, "warnings": warnings,
        "by_issue_type": dict(Counter(r.get("issue_type") for r in rows)),
        "by_action": dict(Counter(r.get("action") for r in rows)),
        "by_priority": dict(Counter(r.get("priority") for r in rows)),
        "needs_human_approval": sum(1 for r in rows if r.get("requires_human_approval")),
        "needs_guest_consent": sum(1 for r in rows if r.get("requires_guest_consent")),
    }
