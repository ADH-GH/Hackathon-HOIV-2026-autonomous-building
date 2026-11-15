"""Atomic individual JSON/text evidence writes; not a multi-file transaction."""
import json
import os
import tempfile
from pathlib import Path
from typing import Any


def _atomic_text(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.' + path.name + '-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def _write_json(path, value):
    _atomic_text(path, json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n')


def _write_jsonl(path: str | Path, records: list[dict[str, Any]]) -> None:
    _atomic_text(path, ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True, allow_nan=False) + '\n' for r in records))
