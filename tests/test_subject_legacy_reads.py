from __future__ import annotations

import copy
import json
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from subject_legacy_reads import parse_compatibility_document  # noqa: E402


def candidate_node(node_id: str = "node.a") -> dict[str, object]:
    return {
        "id": node_id,
        "requirements": [
            {"id": "req.a", "statement": " Requirement text ", "acceptance_criteria_refs": ["ac.a"]}
        ],
        "acceptance_criteria": [{"id": "ac.a", "statement": " Criterion text "}],
    }


def test_existing_candidate_fixture_retains_ids_and_local_references() -> None:
    data = json.loads(
        (ROOT / "tests/fixtures/candidate_spec_graph/candidate_ready.json").read_text()
    )
    inventory = parse_compatibility_document(data, "fixture://candidate-ready")

    assert not inventory.diagnostics
    assert len(inventory.nodes) == len(data["candidate_graph"]["nodes"])
    first = inventory.records[0]
    original = data["candidate_graph"]["nodes"][0]["requirements"][0]
    assert first.id == original["id"]
    assert first.statement == original["statement"]
    assert first.acceptance_criteria_refs == tuple(original["acceptance_criteria_refs"])
    assert first.scope.node_id == data["candidate_graph"]["nodes"][0]["id"]


def test_materialized_records_and_equal_legacy_occurrences_stay_separate() -> None:
    node = candidate_node()
    data = {
        "id": "CANDIDATE-DEMO-NODE-A",
        "acceptance": [" Criterion text ", " Criterion text "],
        "specification": {
            "candidate_source_id": "node.a",
            "requirements": node["requirements"],
            "acceptance_criteria": node["acceptance_criteria"],
        },
    }
    inventory = parse_compatibility_document(data, "fixture://materialized")

    assert not inventory.diagnostics
    assert inventory.nodes[0].scope.node_id == "CANDIDATE-DEMO-NODE-A"
    assert inventory.nodes[0].candidate_source_id == "node.a"
    assert inventory.records[0].statement == " Requirement text "
    assert len(inventory.legacy_acceptance) == 2
    assert inventory.legacy_acceptance[0].statement == inventory.legacy_acceptance[1].statement
    assert inventory.legacy_acceptance[0].locator != inventory.legacy_acceptance[1].locator
    assert not hasattr(inventory.legacy_acceptance[0], "id")
    assert not hasattr(inventory.records[0], "revision")
    assert not hasattr(inventory.records[0], "workspace_identity")


def test_missing_ids_never_generate_ids_and_inputs_are_unchanged() -> None:
    node = candidate_node()
    node["requirements"][0].pop("id")
    data = {"candidate_graph": {"nodes": [node, {"title": "No authored node ID"}]}}
    original = copy.deepcopy(data)
    inventory = parse_compatibility_document(data, "fixture://missing")

    assert data == original
    assert [record.id for record in inventory.records] == ["ac.a"]
    assert sum(issue.code == "missing_candidate_id" for issue in inventory.diagnostics) == 2
    with pytest.raises(FrozenInstanceError):
        inventory.records[0].id = "another"
    node["acceptance_criteria"][0]["statement"] = "Caller mutates input later"
    assert inventory.records[0].statement == " Criterion text "


def test_same_ids_in_different_node_and_artifact_scopes_are_preserved() -> None:
    data = {"candidate_graph": {"nodes": [candidate_node("node.a"), candidate_node("node.b")]}}
    first = parse_compatibility_document(data, "fixture://first")
    second = parse_compatibility_document(data, "fixture://second")

    assert not first.diagnostics
    assert not second.diagnostics
    assert first.records[0].id == first.records[2].id
    assert first.records[0].scope != first.records[2].scope
    assert first.records[0].scope != second.records[0].scope


@pytest.mark.parametrize("conflicting", [False, True])
def test_repeated_ids_within_node_scope_return_ambiguity(conflicting: bool) -> None:
    node = candidate_node()
    duplicate = copy.deepcopy(node["acceptance_criteria"][0])
    if conflicting:
        duplicate["statement"] = "Conflicting wording"
    node["acceptance_criteria"].append(duplicate)
    inventory = parse_compatibility_document(
        {"candidate_graph": {"nodes": [node]}}, "fixture://duplicates"
    )

    expected = "conflicting_candidate_definition" if conflicting else "duplicate_candidate_identity"
    assert [issue.code for issue in inventory.diagnostics] == [expected]
    assert len(inventory.records) == 3


def test_duplicate_candidate_nodes_do_not_silently_select_one() -> None:
    node = candidate_node()
    inventory = parse_compatibility_document(
        {"candidate_graph": {"nodes": [node, copy.deepcopy(node)]}}, "fixture://nodes"
    )
    assert [issue.code for issue in inventory.diagnostics] == ["duplicate_candidate_identity"]
    assert len(inventory.nodes) == 2


def test_equal_record_id_and_text_across_kinds_is_a_conflict() -> None:
    entry = {"id": "same", "statement": "Equal text"}
    inventory = parse_compatibility_document(
        {
            "candidate_graph": {
                "nodes": [{"id": "node", "requirements": [entry], "acceptance_criteria": [entry]}]
            }
        },
        "fixture://cross-kind",
    )
    assert [issue.code for issue in inventory.diagnostics] == ["conflicting_candidate_definition"]
    assert [record.kind for record in inventory.records] == ["requirement", "criterion"]


def test_unknown_refs_cannot_resolve_through_another_node() -> None:
    first = candidate_node("node.a")
    first["acceptance_criteria"] = []
    inventory = parse_compatibility_document(
        {"candidate_graph": {"nodes": [first, candidate_node("node.b")]}}, "fixture://local"
    )
    assert [issue.code for issue in inventory.diagnostics] == [
        "unknown_candidate_criterion_reference"
    ]
    assert inventory.records[0].acceptance_criteria_refs == ("ac.a",)


@pytest.mark.parametrize(
    "data, expected",
    [
        ([], "malformed_document"),
        ({"acceptance": "text"}, "malformed_list"),
        ({"acceptance": [None, {}, ""]}, "malformed_legacy_acceptance"),
        ({"candidate_graph": []}, "malformed_candidate_graph"),
        ({"candidate_graph": {"nodes": {}}}, "malformed_list"),
        ({"candidate_graph": {"nodes": [None]}}, "malformed_candidate_node"),
        ({"specification": []}, "malformed_specification"),
        (
            {"id": "materialized", "specification": {"requirements": [None]}},
            "malformed_candidate_record",
        ),
        (
            {
                "id": "materialized",
                "specification": {"requirements": [{"id": "r", "statement": False}]},
            },
            "malformed_candidate_statement",
        ),
    ],
)
def test_malformed_shapes_produce_diagnostics(data: object, expected: str) -> None:
    inventory = parse_compatibility_document(data, "fixture://malformed")
    assert expected in {issue.code for issue in inventory.diagnostics}


def test_malformed_reference_elements_and_source_id_are_diagnosed() -> None:
    data = {
        "id": "materialized",
        "specification": {
            "candidate_source_id": [],
            "requirements": [
                {"id": "r", "statement": "text", "acceptance_criteria_refs": [False, {}, "missing"]}
            ],
            "acceptance_criteria": None,
        },
    }
    inventory = parse_compatibility_document(data, "fixture://malformed")
    assert {issue.code for issue in inventory.diagnostics} == {
        "malformed_candidate_id",
        "malformed_candidate_reference",
        "malformed_list",
        "unknown_candidate_criterion_reference",
    }
    assert inventory.records[0].acceptance_criteria_refs == ("missing",)
