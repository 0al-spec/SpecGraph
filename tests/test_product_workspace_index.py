from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import decision_nodes  # noqa: E402
import supervisor  # noqa: E402


def decision_document() -> dict[str, object]:
    return {
        "apiVersion": "specgraph.io/v0alpha1",
        "kind": "Node",
        "metadata": {
            "id": "01JQ4M8N7QAZP6Y4N2M8T5V9KR",
            "key": "decision.workspace.read-only-index",
            "type": "decision",
            "title": "Read-only Decision index",
            "status": "reviewed",
            "createdAt": "2026-09-24T06:00:00Z",
            "updatedAt": "2026-09-24T06:00:00Z",
            "revision": 1,
        },
        "spec": {
            "statement": "The workspace can query canonical Decisions.",
            "rationale": "Decision records need a deterministic read path.",
        },
        "provenance": {
            "sources": [{"doc": "docs/adr/decision-index.md"}],
            "authoredBy": "workspace-owner",
            "authority": "authored",
        },
    }


def write_yaml(path: Path, value: dict[str, object]) -> None:
    import yaml

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def test_product_workspace_index_separates_decisions_from_legacy_specs(
    tmp_path: Path,
) -> None:
    specs_root = tmp_path / "specs"
    legacy_path = specs_root / "nodes" / "APP-SPEC-001.yaml"
    decision_path = specs_root / "nodes" / "decision.yaml"
    write_yaml(
        legacy_path,
        {"id": "APP-SPEC-001", "title": "Legacy product spec", "kind": "spec"},
    )
    write_yaml(decision_path, decision_document())
    before = {path: path.read_bytes() for path in (legacy_path, decision_path)}

    index = supervisor.load_product_workspace_index(specs_root)

    assert [spec.id for spec in index.specs] == ["APP-SPEC-001"]
    assert index.decisions.get_by_key("decision.workspace.read-only-index").id == (
        "01JQ4M8N7QAZP6Y4N2M8T5V9KR"
    )
    assert index.decisions.get_by_id("01JQ4M8N7QAZP6Y4N2M8T5V9KR").key == (
        "decision.workspace.read-only-index"
    )
    assert {path: path.read_bytes() for path in before} == before


def test_product_workspace_index_propagates_invalid_decision_error(
    tmp_path: Path,
) -> None:
    specs_root = tmp_path / "specs"
    invalid = decision_document()
    invalid["metadata"]["id"] = "x"  # type: ignore[index]
    write_yaml(specs_root / "nodes" / "decision.yaml", invalid)

    with pytest.raises(decision_nodes.DecisionWorkspaceError, match="metadata.id"):
        supervisor.load_product_workspace_index(specs_root)
