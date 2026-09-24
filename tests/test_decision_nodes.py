from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import decision_nodes  # noqa: E402


def decision_document(
    *,
    node_id: str = "01JQ4M8N7QAZP6Y4N2M8T5V9KR",
    key: str = "decision.workspace.read-only-index",
    status: str = "reviewed",
) -> dict[str, object]:
    return {
        "apiVersion": "specgraph.io/v0alpha1",
        "kind": "Node",
        "metadata": {
            "id": node_id,
            "key": key,
            "type": "decision",
            "title": "Read-only Decision index",
            "status": status,
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


def write_yaml(path: Path, data: dict[str, object]) -> None:
    import yaml

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def test_index_loads_canonical_decision_without_project_spec_timestamps(
    tmp_path: Path,
) -> None:
    root = tmp_path / "specs"
    decision_path = root / "nodes" / "decision.yaml"
    write_yaml(decision_path, decision_document())
    write_yaml(
        root / "legacy-project-spec.yaml",
        {"id": "APP-SPEC-001", "kind": "spec", "status": "outlined"},
    )

    index = decision_nodes.load_decision_index(root)

    assert index.get_by_key("decision.workspace.read-only-index").id == (
        "01JQ4M8N7QAZP6Y4N2M8T5V9KR"
    )
    assert index.get_by_id("01JQ4M8N7QAZP6Y4N2M8T5V9KR").key == (
        "decision.workspace.read-only-index"
    )
    with pytest.raises(TypeError):
        index.by_key["another"] = index.get_by_id("01JQ4M8N7QAZP6Y4N2M8T5V9KR")


@pytest.mark.parametrize("identity", ["key", "id"])
def test_index_rejects_duplicate_identity_deterministically(
    tmp_path: Path,
    identity: str,
) -> None:
    first = decision_nodes.parse_decision_document(decision_document(), tmp_path / "a.yaml")
    duplicate = decision_document(
        node_id=(
            "01JQ4M8N7QAZP6Y4N2M8T5V9KS" if identity == "key" else "01JQ4M8N7QAZP6Y4N2M8T5V9KR"
        ),
        key=(
            "decision.workspace.duplicate"
            if identity == "id"
            else "decision.workspace.read-only-index"
        ),
    )
    second = decision_nodes.parse_decision_document(duplicate, tmp_path / "b.yaml")

    with pytest.raises(decision_nodes.DecisionIndexError, match=f"duplicate Decision {identity}"):
        decision_nodes.index_decisions([second, first])


def test_invalid_lifecycle_and_provenance_are_reported(tmp_path: Path) -> None:
    invalid = decision_document(status="adopted")
    invalid["lifecycle"] = {"validFrom": "not-a-time"}
    invalid["provenance"]["authority"] = "product_rule_authority"  # type: ignore[index]

    with pytest.raises(decision_nodes.DecisionDocumentError) as error:
        decision_nodes.parse_decision_document(invalid, tmp_path / "bad.yaml")

    message = str(error.value)
    assert "metadata.status" in message
    assert "provenance.authority" in message
    assert "lifecycle.validFrom" in message


def test_unknown_key_is_rejected_without_falling_back_to_id(tmp_path: Path) -> None:
    path = tmp_path / "specs" / "decision.yaml"
    write_yaml(path, decision_document())
    index = decision_nodes.load_decision_index(path.parent)

    with pytest.raises(decision_nodes.DecisionIndexError, match="unknown Decision key"):
        index.get_by_key("01JQ4M8N7QAZP6Y4N2M8T5V9KR")


def test_cli_lists_and_queries_decisions_read_only(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = tmp_path / "specs"
    write_yaml(root / "decision.yaml", decision_document())
    before = (root / "decision.yaml").read_bytes()

    assert decision_nodes.main([str(root), "--key", "decision.workspace.read-only-index"]) == 0
    assert '"id": "01JQ4M8N7QAZP6Y4N2M8T5V9KR"' in capsys.readouterr().out
    assert (root / "decision.yaml").read_bytes() == before
