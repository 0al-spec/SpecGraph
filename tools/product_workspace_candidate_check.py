"""Inspect the identity of one explicitly selected product draft."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from yaml import YAMLError

from product_workspace_next_moves_support import safe_workspace_path
from spec_yaml import load_yaml_text


def check_candidate(workspace_root: Path, candidate_file: str) -> dict[str, Any]:
    relative = Path(candidate_file)
    if (
        not safe_workspace_path(candidate_file)
        or relative.parts[:2] != ("docs", "drafts")
        or relative.suffix not in {".yaml", ".yml"}
    ):
        raise ValueError("candidate file must be a workspace-relative YAML path under docs/drafts")

    root = workspace_root.expanduser().resolve(strict=True)
    path = root / relative
    try:
        if path.resolve(strict=True) != path or not path.is_file():
            raise ValueError("candidate file must be regular and cannot traverse symlinks")
    except RuntimeError as exc:
        raise ValueError("cannot resolve candidate file") from exc
    raw = path.read_bytes()
    try:
        document = load_yaml_text(raw.decode("utf-8"))
    except (ValueError, TypeError, YAMLError) as exc:
        raise ValueError(f"invalid candidate YAML: {exc}") from exc

    if document.get("kind") != "spec" or document.get("id") != path.stem:
        raise ValueError("candidate must have kind: spec and an id matching its filename")

    authored_status = {key: document[key] for key in ("status", "draft_status") if key in document}
    if any(not isinstance(value, str) for value in authored_status.values()):
        raise ValueError("candidate status and draft_status must be strings when present")
    return {
        "artifact_kind": "product_workspace_candidate_check",
        "schema_version": 1,
        "status": "checked",
        "canonical": False,
        "source": {
            "path": relative.as_posix(),
            "spec_id": document["id"],
            "sha256": hashlib.sha256(raw).hexdigest(),
        },
        "authored_status": authored_status,
        "checked": ["yaml_mapping", "spec_kind", "file_id_match"],
        "next_action": "review_candidate",
    }
