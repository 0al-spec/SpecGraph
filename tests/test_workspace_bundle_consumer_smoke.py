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


@pytest.mark.parametrize("accept_foreign", [False, True])
def test_identity_negative_uses_restored_candidate(monkeypatch, tmp_path, accept_foreign):
    import json
    import sys
    from types import SimpleNamespace

    module = smoke_module()
    workspace_id = "example"
    candidate_path = "runs/example/repaired_active_idea_to_spec_candidate.json"
    original = b'{"candidate": "healthy"}'
    bundle = tmp_path / "bundle"
    (bundle / candidate_path).parent.mkdir(parents=True)
    (bundle / candidate_path).write_bytes(original)
    (bundle / "artifact_manifest.json").write_text(
        json.dumps({"files": [{"path": candidate_path}]}), encoding="utf-8"
    )
    answers = iter(["a" * 40, ""])
    monkeypatch.setattr(module.subprocess, "check_output", lambda *args, **kwargs: next(answers))
    roots = []
    original_copy = module.shutil.copytree

    def copy(source, destination, *args, **kwargs):
        if not roots:
            roots.append(destination)
        return original_copy(source, destination, *args, **kwargs)

    monkeypatch.setattr(module.shutil, "copytree", copy)
    observed = []

    class Provider:
        def __init__(self, delegate, selected):
            self.selected = selected

        def read_idea_to_spec_workspace(self):
            root = roots[0]
            content = (root / candidate_path).read_bytes()
            listed = json.loads((root / "artifact_manifest.json").read_text())["files"]
            healthy = content == original and any(
                entry["path"] == candidate_path for entry in listed
            )
            observed.append((self.selected, healthy))
            available = healthy and (self.selected == workspace_id or accept_foreign)
            return 200, {
                "workspace": {"available": available, "id": workspace_id, "ready": True},
                "summary": {"candidate_node_count": 8, "missing_artifact_count": 0},
                "workspace_binding": {"status": "ready", "trusted": True},
            }

    fake = SimpleNamespace(
        HttpSpecGraphProvider=lambda **kwargs: None,
        HttpArtifactCache=lambda: None,
        ProductWorkspaceHttpProvider=Provider,
    )
    monkeypatch.setitem(sys.modules, "viewer", SimpleNamespace(specspace_provider=fake))
    if accept_foreign:
        with pytest.raises(ValueError, match="identity from another workspace"):
            module.run(bundle, tmp_path, workspace_id, "a" * 40)
    else:
        report = module.run(bundle, tmp_path, workspace_id, "a" * 40)
        assert report["checks"]["foreign_workspace_rejected"] is True
    assert observed == [
        (workspace_id, True),
        (workspace_id, False),
        (workspace_id, False),
        (workspace_id, True),
        ("foreign-workspace", True),
    ]
    assert (bundle / candidate_path).read_bytes() == original
