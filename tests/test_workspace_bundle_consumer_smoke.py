from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def smoke_module():
    path = Path(__file__).resolve().parents[1] / "tools/workspace_bundle_consumer_smoke.py"
    spec = importlib.util.spec_from_file_location("workspace_consumer_smoke", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_consumer_source_pin_rejected_before_import_or_server(monkeypatch, tmp_path):
    module = smoke_module()
    monkeypatch.setattr(module.subprocess, "check_output", lambda *args, **kwargs: "a" * 40)
    with pytest.raises(ValueError, match="selected consumer source pin"):
        module.run(tmp_path / "absent", tmp_path / "no-consumer", "example", "b" * 40)


def test_dirty_consumer_rejected_before_import_or_server(monkeypatch, tmp_path):
    module = smoke_module()
    answers = iter(["a" * 40, " M viewer/specspace_provider.py"])
    monkeypatch.setattr(module.subprocess, "check_output", lambda *args, **kwargs: next(answers))
    with pytest.raises(ValueError, match="uncommitted changes"):
        module.run(tmp_path / "absent", tmp_path / "no-consumer", "example", "a" * 40)


def test_complete_blocked_domain_state_is_not_a_publication_failure():
    module = smoke_module()
    payload = {
        "workspace": {"available": True, "id": "example", "ready": True},
        "summary": {"status": "blocked", "candidate_node_count": 6, "missing_artifact_count": 0},
    }
    assert module.require_workspace_content(payload, "example")["status"] == "blocked"


@pytest.mark.parametrize("nodes,missing", [(0, 0), (8, 1)])
def test_incomplete_content_is_rejected(nodes, missing):
    module = smoke_module()
    payload = {
        "workspace": {"available": True, "id": "example", "ready": True},
        "summary": {
            "status": "partial",
            "candidate_node_count": nodes,
            "missing_artifact_count": missing,
        },
    }
    with pytest.raises(ValueError, match="incomplete candidate content"):
        module.require_workspace_content(payload, "example")
