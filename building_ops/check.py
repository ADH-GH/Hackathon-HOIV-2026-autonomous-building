"""Check a decisions.jsonl against the output contract and the autonomy rules.

Run it before every commit of a submission file. It reads the file as written,
so it also catches decisions that did not come through `Decision.finalize()`.
"""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .decisions import DecisionError, validate_decision

REQUIRED = ("event_id", "timestamp_utc", "affected_assets", "issue_type", "action",
            "priority", "reason", "requires_human_approval")


def check(path: str | Path, *, strict_safety: bool = False) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    rows: list[dict[str, Any]] = []
    missing = 0
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"line {n}: not JSON ({exc.msg})")
            continue
        where = f"line {n}" + (f" ({row.get('event_id', '?')})" if isinstance(row, dict) else "")
        try:
            validate_decision(row, require_risk_context=strict_safety)
        except DecisionError as exc:
            errors.append(f"{where}: {exc}")
        if not isinstance(row, dict):
            continue
        # Safe projections retain diagnostics even for malformed object records.
        missing += "risk_context" not in row
        has_evidence = bool(row.get("evidence"))
        row = {k: v for k, v in row.items() if isinstance(v, (str, bool)) or
               (k == "affected_assets" and isinstance(v, list) and all(isinstance(x, str) for x in v))}
        rows.append(row)
        if not has_evidence:
            warnings.append(f"{where}: no evidence")

    if missing and not strict_safety:
        warnings.append(f"{missing} legacy records lack risk_context; action risks cannot be fully revalidated")
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
