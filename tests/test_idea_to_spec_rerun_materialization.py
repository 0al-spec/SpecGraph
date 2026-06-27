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
                        "confidence": "review_safe",
                        "match": {
                            "gap_id": "ontology-gap.decision-owner",
                            "node_id": "candidate-spec.product-boundary",
                            "decision_id": "clarification.owner",
                            "match_kind": "exact",
                            "confidence": "review_safe",
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
    assert node["ontology_gap_resolutions"][0]["confidence"] == "review_safe"
    assert node["ontology_gap_resolutions"][0]["match"]["normalized_gap_term"] == ("decision owner")
    assert (
        node["ontology_gap_resolutions"][0]["resolution_preview"]["decision"]
        == "project_local_term"
    )
    dumped = json.dumps(report)
    assert "private prompt trace" not in dumped


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
