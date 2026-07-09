from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "idea_to_spec_rerun_materialization.py"


def load_module() -> object:
    spec = importlib.util.spec_from_file_location(
        "idea_to_spec_rerun_materialization_under_test",
        TOOL_PATH,
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def finding_ids(report: dict[str, object]) -> set[str]:
    findings = report["findings"]
    assert isinstance(findings, list)
    return {finding["finding_id"] for finding in findings if isinstance(finding, dict)}


def rerun_preview_artifact() -> dict[str, object]:
    return {
        "artifact_kind": "idea_to_spec_rerun_preview",
        "schema_version": 1,
        "contract_ref": "specgraph.idea-to-spec.rerun-preview.v0.1",
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "readiness": {
            "ready": True,
            "review_state": "rerun_preview_ready",
            "blocked_by": [],
        },
        "rerun_preview": {
            "ontology_gap_preview": {
                "resolved_ontology_gaps": [
                    {
                        "gap_id": "ontology-gap.decision-owner",
                        "node_id": "candidate-spec.product-boundary",
                        "term": "Decision Owner",
                        "source_ref": "actor.decision-owner",
                        "decision_id": "clarification.owner",
                        "decision_term": "Decision Owner",
                        "match_kind": "exact",
                        "confidence": "high",
                        "match": {
                            "gap_id": "ontology-gap.decision-owner",
                            "node_id": "candidate-spec.product-boundary",
                            "decision_id": "clarification.owner",
                            "match_kind": "exact",
                            "confidence": "high",
                            "gap_term": "Decision Owner",
                            "decision_term": "Decision Owner",
                            "normalized_gap_term": "decision owner",
                            "normalized_decision_term": "decision owner",
                        },
                        "resolution_preview": {
                            "decision": "project_local_term",
                            "term": "Decision Owner",
                            "request_id": "clarification.owner",
                            "raw_prompt": "private prompt trace",
                        },
                    }
                ],
                "unresolved_ontology_gaps": [
                    {
                        "gap_id": "ontology-gap.record-decision",
                        "node_id": "candidate-spec.product-boundary",
                        "term": "Record Decision",
                    }
                ],
            }
        },
    }


def rerun_preview_with_candidate_gap_resolutions() -> dict[str, object]:
    preview = rerun_preview_artifact()
    rerun_preview = preview["rerun_preview"]
    assert isinstance(rerun_preview, dict)
    rerun_preview["candidate_gap_preview"] = {
        "resolved_candidate_gaps": [
            {
                "gap_id": "gap.local-only-storage.enforcement-mechanism",
                "node_id": "candidate-spec.local-storage",
                "kind": "implementation_gap",
                "source_ref": "constraint.local-only-storage",
                "statement": "Define the enforcement mechanism for local-only storage.",
                "target_ref": (
                    "candidate-spec.local-storage.gaps.gap.local-only-storage.enforcement-mechanism"
                ),
                "request_id": "clarification.local-storage",
                "answer_kind": "answer_question",
                "resolution_kind": "enforcement_mechanism_added",
                "match_kind": "target_ref",
                "confidence": "explicit_target",
                "match": {
                    "gap_id": "gap.local-only-storage.enforcement-mechanism",
                    "node_id": "candidate-spec.local-storage",
                    "request_id": "clarification.local-storage",
                    "answer_kind": "answer_question",
                    "match_kind": "target_ref",
                    "confidence": "explicit_target",
                    "target_ref": (
                        "candidate-spec.local-storage.gaps."
                        "gap.local-only-storage.enforcement-mechanism"
                    ),
                },
                "resolution_preview": {
                    "request_id": "clarification.local-storage",
                    "answer_kind": "answer_question",
                    "request_kind": "candidate_gap",
                    "target_ref": (
                        "candidate-spec.local-storage.gaps."
                        "gap.local-only-storage.enforcement-mechanism"
                    ),
                    "value": "Store subscriptions in a local-only encrypted file.",
                    "raw_prompt": "private prompt trace",
                },
            }
        ],
        "unresolved_candidate_gaps": [
            {
                "gap_id": "gap.required-fields.enforcement-mechanism",
                "node_id": "candidate-spec.required-fields",
                "kind": "implementation_gap",
                "target_ref": (
                    "candidate-spec.required-fields.gaps.gap.required-fields.enforcement-mechanism"
                ),
            }
        ],
    }
    return preview


def candidate_graph_artifact() -> dict[str, object]:
    return {
        "artifact_kind": "candidate_spec_graph",
        "schema_version": 1,
        "contract_ref": "specgraph.idea-to-spec.candidate-spec-graph.v0.1",
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "nodes": [
            {
                "id": "candidate-spec.product-boundary",
                "gaps": [
                    {
                        "id": "ontology-gap.decision-owner",
                        "kind": "ontology_gap",
                        "source_ref": "actor.decision-owner",
                        "term": "Decision Owner",
                    },
                    {
                        "id": "ontology-gap.record-decision",
                        "kind": "ontology_gap",
                        "source_ref": "command.record-decision",
                        "term": "Record Decision",
                    },
                ],
            }
        ],
        "edges": [],
    }


def candidate_graph_for_workflow_topology() -> dict[str, object]:
    graph = candidate_graph_artifact()
    graph["nodes"] = [
        {
            "id": "candidate-spec.product-boundary",
            "kind": "product_boundary",
            "source_event_refs": [],
            "gaps": [],
        },
        {
            "id": "candidate-spec.record-pantry-item",
            "kind": "behavior_requirement",
            "source_event_refs": ["command.record-pantry-item"],
            "gaps": [],
        },
    ]
    graph["edges"] = []
    return graph


def rerun_preview_with_workflow_topology() -> dict[str, object]:
    preview = rerun_preview_artifact()
    preview["rerun_preview"]["workflow_topology_preview"] = {
        "workflow_edges": [
            {
                "id": "edge.command.record-pantry-item.pantry-item-recorded",
                "from": "candidate-spec.record-pantry-item",
                "to": "candidate-spec.product-boundary",
                "relation": "command_emits_event",
                "source_event_refs": [
                    "command.record-pantry-item",
                    "event.pantry-item-recorded",
                ],
                "command_ref": "command.record-pantry-item",
                "event_ref": "event.pantry-item-recorded",
                "review_only": True,
                "materialization_dependency": False,
            },
            {
                "id": "edge.command.record-pantry-item.pantry-item-reviewed",
                "from": "candidate-spec.record-pantry-item",
                "to": "candidate-spec.product-boundary",
                "relation": "command_emits_event",
                "source_event_refs": [
                    "command.record-pantry-item",
                    "event.pantry-item-reviewed",
                ],
                "command_ref": "command.record-pantry-item",
                "event_ref": "event.pantry-item-reviewed",
                "review_only": True,
                "materialization_dependency": False,
            },
        ],
        "workflow_edge_count": 2,
        "review_only": True,
        "materialization_dependency": False,
    }
    preview["rerun_preview"]["ontology_gap_preview"]["resolved_ontology_gaps"] = []
    preview["rerun_preview"]["ontology_gap_preview"]["unresolved_ontology_gaps"] = []
    return preview


def candidate_graph_with_candidate_gaps() -> dict[str, object]:
    graph = candidate_graph_artifact()
    graph["nodes"] = [
        {
            "id": "candidate-spec.local-storage",
            "gaps": [
                {
                    "id": "gap.local-only-storage.enforcement-mechanism",
                    "kind": "implementation_gap",
                    "source_ref": "constraint.local-only-storage",
                    "statement": "Define the enforcement mechanism for local-only storage.",
                }
            ],
        },
        {
            "id": "candidate-spec.required-fields",
            "gaps": [
                {
                    "id": "gap.required-fields.enforcement-mechanism",
                    "kind": "implementation_gap",
                    "source_ref": "constraint.required-fields",
                    "statement": "Define required fields enforcement.",
                }
            ],
        },
    ]
    return graph


def test_rerun_materialization_removes_resolved_gap_in_preview() -> None:
    module = load_module()

    report = module.build_idea_to_spec_rerun_materialization(
        rerun_preview=rerun_preview_artifact(),
        candidate_graph=candidate_graph_artifact(),
    )

    assert report["artifact_kind"] == "idea_to_spec_rerun_materialization"
    assert report["proposal_id"] == "0167"
    assert report["canonical_mutations_allowed"] is False
    assert report["tracked_artifacts_written"] is False
    assert report["readiness"]["ready"] is True
    assert report["summary"]["removed_gap_count"] == 1

    preview = report["materialization_preview"]["candidate_graph_preview"]
    node = preview["nodes"][0]
    assert [gap["id"] for gap in node["gaps"]] == ["ontology-gap.record-decision"]
    assert preview["summary"]["gap_count"] == 1
    assert node["ontology_gap_resolutions"][0]["gap_id"] == "ontology-gap.decision-owner"
    assert node["ontology_gap_resolutions"][0]["decision_id"] == "clarification.owner"
    assert node["ontology_gap_resolutions"][0]["decision_term"] == "Decision Owner"
    assert node["ontology_gap_resolutions"][0]["match_kind"] == "exact"
    assert node["ontology_gap_resolutions"][0]["confidence"] == "high"
    assert node["ontology_gap_resolutions"][0]["match"]["normalized_gap_term"] == ("decision owner")
    assert (
        node["ontology_gap_resolutions"][0]["resolution_preview"]["decision"]
        == "project_local_term"
    )
    dumped = json.dumps(report)
    assert "private prompt trace" not in dumped


def test_rerun_materialization_removes_resolved_candidate_gap_in_preview() -> None:
    module = load_module()

    report = module.build_idea_to_spec_rerun_materialization(
        rerun_preview=rerun_preview_with_candidate_gap_resolutions(),
        candidate_graph=candidate_graph_with_candidate_gaps(),
    )

    assert report["readiness"]["ready"] is True
    assert report["summary"]["resolved_candidate_gap_count"] == 1
    assert report["summary"]["unresolved_candidate_gap_count"] == 1
    assert report["summary"]["removed_gap_count"] == 1

    preview = report["materialization_preview"]["candidate_graph_preview"]
    first_node = preview["nodes"][0]
    assert first_node["gaps"] == []
    assert first_node["candidate_gap_resolutions"][0]["gap_id"] == (
        "gap.local-only-storage.enforcement-mechanism"
    )
    assert (
        first_node["candidate_gap_resolutions"][0]["resolution_kind"]
        == "enforcement_mechanism_added"
    )
    assert (
        first_node["candidate_gap_resolutions"][0]["resolution_preview"]["value"]
        == "Store subscriptions in a local-only encrypted file."
    )
    second_node = preview["nodes"][1]
    assert [gap["id"] for gap in second_node["gaps"]] == [
        "gap.required-fields.enforcement-mechanism"
    ]
    delta = report["materialization_preview"]["delta"]
    assert delta["candidate_resolution_records"][0]["request_id"] == "clarification.local-storage"
    assert delta["unresolved_candidate_gap_ids"] == ["gap.required-fields.enforcement-mechanism"]
    assert "private prompt trace" not in json.dumps(report)


def test_rerun_materialization_merges_review_only_workflow_topology_edges() -> None:
    module = load_module()

    report = module.build_idea_to_spec_rerun_materialization(
        rerun_preview=rerun_preview_with_workflow_topology(),
        candidate_graph=candidate_graph_for_workflow_topology(),
    )

    assert report["readiness"]["ready"] is True
    preview = report["materialization_preview"]["candidate_graph_preview"]
    edges = preview["edges"]
    assert len(edges) == 2
    edge = edges[0]
    assert edge["relation"] == "command_emits_event"
    assert edge["review_only"] is True
    assert edge["materialization_dependency"] is False
    assert preview["summary"]["edge_count"] == 2
    delta = report["materialization_preview"]["delta"]
    assert delta["added_workflow_topology_edge_count"] == 2
    assert {edge["event_ref"] for edge in delta["added_workflow_topology_edges"]} == {
        "event.pantry-item-recorded",
        "event.pantry-item-reviewed",
    }
    assert report["summary"]["removed_gap_count"] == 0


def test_rerun_materialization_preserves_node_scope_for_duplicate_candidate_gap_ids() -> None:
    module = load_module()
    candidate_graph = copy.deepcopy(candidate_graph_artifact())
    candidate_graph["nodes"] = [
        {
            "id": "candidate-spec.local-storage",
            "gaps": [
                {
                    "id": "gap.enforcement-mechanism",
                    "kind": "implementation_gap",
                    "source_ref": "constraint.local-storage",
                    "statement": "Define the enforcement mechanism for local-only storage.",
                }
            ],
        },
        {
            "id": "candidate-spec.required-fields",
            "gaps": [
                {
                    "id": "gap.enforcement-mechanism",
                    "kind": "implementation_gap",
                    "source_ref": "constraint.required-fields",
                    "statement": "Define required fields enforcement.",
                }
            ],
        },
    ]
    rerun_preview = rerun_preview_artifact()
    rerun_preview["rerun_preview"]["candidate_gap_preview"] = {
        "resolved_candidate_gaps": [
            {
                "gap_id": "gap.enforcement-mechanism",
                "node_id": "candidate-spec.local-storage",
                "kind": "implementation_gap",
                "source_ref": "constraint.local-storage",
                "statement": "Define the enforcement mechanism for local-only storage.",
                "target_ref": "candidate-spec.local-storage.gaps.gap.enforcement-mechanism",
                "request_id": "clarification.local-storage",
                "answer_kind": "answer_question",
                "resolution_kind": "enforcement_mechanism_added",
                "match_kind": "target_ref",
                "confidence": "explicit_target",
            },
            {
                "gap_id": "gap.enforcement-mechanism",
                "node_id": "candidate-spec.required-fields",
                "kind": "implementation_gap",
                "source_ref": "constraint.required-fields",
                "statement": "Define required fields enforcement.",
                "target_ref": "candidate-spec.required-fields.gaps.gap.enforcement-mechanism",
                "request_id": "clarification.required-fields",
                "answer_kind": "answer_question",
                "resolution_kind": "enforcement_mechanism_added",
                "match_kind": "target_ref",
                "confidence": "explicit_target",
            },
        ],
        "unresolved_candidate_gaps": [],
    }

    report = module.build_idea_to_spec_rerun_materialization(
        rerun_preview=rerun_preview,
        candidate_graph=candidate_graph,
    )

    assert report["summary"]["resolved_candidate_gap_count"] == 2
    assert report["summary"]["removed_gap_count"] == 2
    preview_nodes = report["materialization_preview"]["candidate_graph_preview"]["nodes"]
    assert [node["gaps"] for node in preview_nodes] == [[], []]
    assert {
        record["node_id"]
        for record in report["materialization_preview"]["delta"]["candidate_resolution_records"]
    } == {"candidate-spec.local-storage", "candidate-spec.required-fields"}


def test_rerun_materialization_rechecks_candidate_gap_source_fields_before_removal() -> None:
    module = load_module()

    for field, value in (
        ("source_ref", "constraint.local-storage.changed"),
        ("statement", "Define a regenerated local storage enforcement mechanism."),
    ):
        candidate_graph = candidate_graph_with_candidate_gaps()
        candidate_graph["nodes"][0]["gaps"][0][field] = value

        report = module.build_idea_to_spec_rerun_materialization(
            rerun_preview=rerun_preview_with_candidate_gap_resolutions(),
            candidate_graph=candidate_graph,
        )

        assert report["summary"]["resolved_candidate_gap_count"] == 0
        assert report["summary"]["removed_gap_count"] == 0
        preview = report["materialization_preview"]["candidate_graph_preview"]
        assert [gap["id"] for node in preview["nodes"] for gap in node.get("gaps", [])] == [
            "gap.local-only-storage.enforcement-mechanism",
            "gap.required-fields.enforcement-mechanism",
        ]


def test_rerun_materialization_source_ref_uses_output_path(tmp_path: Path) -> None:
    module = load_module()
    output = tmp_path / "custom_materialization.json"

    report = module.build_idea_to_spec_rerun_materialization(
        rerun_preview=rerun_preview_artifact(),
        candidate_graph=candidate_graph_artifact(),
        output_path=output,
    )

    preview = report["materialization_preview"]["candidate_graph_preview"]
    assert preview["source_ref"] == f"{output}#candidate_graph_preview"


def test_rerun_materialization_blocks_candidate_graph_mismatch(tmp_path: Path) -> None:
    module = load_module()
    rerun_preview = copy.deepcopy(rerun_preview_artifact())
    rerun_preview["source_artifacts"] = {
        "candidate_graph": {
            "source_ref": "runs/different_candidate_graph.json",
        }
    }
    candidate_graph_path = tmp_path / "candidate_spec_graph.json"

    report = module.build_idea_to_spec_rerun_materialization(
        rerun_preview=rerun_preview,
        candidate_graph=candidate_graph_artifact(),
        candidate_graph_path=candidate_graph_path,
    )

    assert report["readiness"]["ready"] is False
    assert "rerun_preview_candidate_graph_mismatch" in finding_ids(report)
    preview = report["materialization_preview"]["candidate_graph_preview"]
    assert [gap["id"] for gap in preview["nodes"][0]["gaps"]] == [
        "ontology-gap.decision-owner",
        "ontology-gap.record-decision",
    ]


def test_rerun_materialization_only_removes_matching_ontology_gaps() -> None:
    module = load_module()
    candidate_graph = candidate_graph_artifact()
    candidate_graph["nodes"][0]["gaps"][0]["kind"] = "implementation_gap"

    report = module.build_idea_to_spec_rerun_materialization(
        rerun_preview=rerun_preview_artifact(),
        candidate_graph=candidate_graph,
    )

    preview = report["materialization_preview"]["candidate_graph_preview"]
    assert [gap["id"] for gap in preview["nodes"][0]["gaps"]] == [
        "ontology-gap.decision-owner",
        "ontology-gap.record-decision",
    ]
    assert report["summary"]["removed_gap_count"] == 0


def test_rerun_materialization_blocks_failed_candidate_graph_readiness() -> None:
    module = load_module()
    candidate_graph = candidate_graph_artifact()
    candidate_graph["pre_sib_readiness"] = {
        "ready": False,
        "review_state": "pre_sib_review_required",
        "blocked_by": ["pre_sib_unresolved_gaps"],
    }

    report = module.build_idea_to_spec_rerun_materialization(
        rerun_preview=rerun_preview_artifact(),
        candidate_graph=candidate_graph,
    )

    assert report["readiness"]["ready"] is False
    assert "candidate_graph_not_ready_for_materialization" in finding_ids(report)


def test_rerun_materialization_blocks_unready_preview() -> None:
    module = load_module()
    rerun_preview = copy.deepcopy(rerun_preview_artifact())
    rerun_preview["readiness"]["ready"] = False

    report = module.build_idea_to_spec_rerun_materialization(
        rerun_preview=rerun_preview,
        candidate_graph=candidate_graph_artifact(),
    )

    assert report["readiness"]["ready"] is False
    assert "rerun_preview_not_ready" in finding_ids(report)


def test_rerun_materialization_rejects_wrong_candidate_graph_kind() -> None:
    module = load_module()
    candidate_graph = copy.deepcopy(candidate_graph_artifact())
    candidate_graph["artifact_kind"] = "other_artifact"

    report = module.build_idea_to_spec_rerun_materialization(
        rerun_preview=rerun_preview_artifact(),
        candidate_graph=candidate_graph,
    )

    assert report["readiness"]["ready"] is False
    assert "candidate_graph_wrong_artifact_kind" in finding_ids(report)


def test_rerun_materialization_cli_writes_output(tmp_path: Path) -> None:
    rerun_preview_path = tmp_path / "idea_to_spec_rerun_preview.json"
    candidate_graph_path = tmp_path / "candidate_spec_graph.json"
    output = tmp_path / "idea_to_spec_rerun_materialization.json"
    write_json(rerun_preview_path, rerun_preview_artifact())
    write_json(candidate_graph_path, candidate_graph_artifact())

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--rerun-preview",
            str(rerun_preview_path),
            "--candidate-graph",
            str(candidate_graph_path),
            "--output",
            str(output),
            "--strict",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    report = load_json(output)
    assert report["artifact_kind"] == "idea_to_spec_rerun_materialization"
    assert report["readiness"]["ready"] is True
    assert "rerun_materialization_ready" in result.stdout
