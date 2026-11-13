"""Run all detectors over one data directory and write decisions.jsonl."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from .dataset import Dataset
from .decisions import dedupe
from .detectors import REGISTRY
from .executor import execute


def run(data_dir: str | Path, out: str | Path = "decisions.jsonl",
        actions_out: str | Path | None = None) -> dict[str, Any]:
    ds = Dataset(data_dir)
    decisions: list[dict[str, Any]] = []
    per_detector: dict[str, int | str] = {}
    for name, (detect, implemented) in REGISTRY.items():
        if not implemented:
            per_detector[name] = "not implemented"
            continue
        try:
            found = [d.finalize() for d in detect(ds)]
        except FileNotFoundError as exc:
            # A missing input file disables one detector, not the whole run.
            per_detector[name] = f"skipped: missing {Path(exc.filename).name}"
            continue
        per_detector[name] = len(found)
        decisions.extend(found)
    decisions = dedupe(decisions)

    _write_jsonl(out, decisions)
    if actions_out:
        _write_jsonl(actions_out, execute(decisions))

    summary = {"data_dir": str(ds.dir), "out": str(out), "decisions": len(decisions),
               "detectors": per_detector}
    print(json.dumps(summary, indent=1), file=sys.stderr)
    return summary


def _write_jsonl(path: str | Path, records: list[dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
