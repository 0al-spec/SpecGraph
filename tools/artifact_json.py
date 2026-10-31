"""Shared UTF-8 JSON object I/O; callers retain artifact policy and diagnostics."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_json_object(path: Path, *, object_error: str | None = None) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(
            object_error if object_error is not None else f"{path} must contain a JSON object"
        )
    return payload


def write_json_object(path: Path, payload: dict[str, Any], *, exclusive: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    with path.open("x" if exclusive else "w", encoding="utf-8") as stream:
        stream.write(text)
