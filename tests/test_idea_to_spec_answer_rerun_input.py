from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANSWERS_TOOL_PATH = ROOT / "tools" / "idea_to_spec_clarification_answers.py"
RERUN_TOOL_PATH = ROOT / "tools" / "idea_to_spec_answer_rerun_input.py"
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "idea_to_spec_clarification_answers"
REQUESTS_FIXTURE = FIXTURE_DIR / "clarification_requests_blocking.json"
ANSWERS_READY_FIXTURE = FIXTURE_DIR / "answers_ready.json"


def load_module(path: Path, name: str) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def finding_ids(report: dict[str, object]) -> set[str]:
    findings = report["findings"]
    assert isinstance(findings, list)
    return {finding["finding_id"] for finding in findings if isinstance(finding, dict)}


def ready_answer_report() -> dict[str, object]:
    answers_module = load_module(
        ANSWERS_TOOL_PATH,
        "idea_to_spec_clarification_answers_for_rerun_test",
    )
    return answers_module.build_idea_to_spec_clarification_answers(
        clarification_requests=load_json(REQUESTS_FIXTURE),
        answer_set=load_json(ANSWERS_READY_FIXTURE),
        requests_path=REQUESTS_FIXTURE,
        answer_set_path=ANSWERS_READY_FIXTURE,
    )


def ready_answer_report_with_answer(
    *,
    answer_kind: str,
    value: object,
    request_kind: str,
    target_ref: str,
) -> dict[str, object]:
    report = copy.deepcopy(ready_answer_report())
    answer = report["answers"][0]
    assert isinstance(answer, dict)
    answer["answer_kind"] = answer_kind
    answer["value"] = value
    answer["request_snapshot"] = {
        "kind": request_kind,
        "severity": "review_required",
        "target_artifact": "runs/candidate_spec_graph.json",
        "target_ref": target_ref,
        "suggested_answer_shape": "test-shape",
    }
    return report


def test_answer_rerun_input_builds_project_local_term_overlay() -> None:
    module = load_module(
        RERUN_TOOL_PATH,
        "idea_to_spec_answer_rerun_input_under_test",
    )

    report = module.build_idea_to_spec_answer_rerun_input(
        answers_report=ready_answer_report(),
        answers_path=ROOT / "runs" / "idea_to_spec_clarification_answers.json",
    )

    assert report["artifact_kind"] == "idea_to_spec_answer_rerun_input"
    assert report["proposal_id"] == "0165"
    assert report["canonical_mutations_allowed"] is False
    assert report["tracked_artifacts_written"] is False
    assert report["readiness"]["ready"] is True
    assert report["readiness"]["review_state"] == "rerun_input_ready"
    boundary = report["authority_boundary"]
    assert boundary["may_apply_answers_to_source_artifacts"] is False
    assert boundary["may_write_ontology_package"] is False

    overlay = report["rerun_input_overlay"]
    project_terms = overlay["ontology_review_hints"]["project_local_terms"]
    assert project_terms == [
        {
            "term": "Decision Owner",
            "term_scope": "project_local",
            "request_id": "clarification.repair.repair-review-unresolved-gaps",
            "answer_kind": "propose_project_local_term",
            "target_artifact": "runs/candidate_repair_loop_report.json",
            "target_ref": "candidate_graph.gaps",
            "request_kind": "ontology_gap",
        }
    ]
    assert report["summary"]["project_local_term_count"] == 1


def test_answer_rerun_input_captures_direct_active_frame_fields() -> None:
    module = load_module(
        RERUN_TOOL_PATH,
        "idea_to_spec_answer_rerun_input_active_frame_direct_test",
    )
    answer_report = ready_answer_report_with_answer(
        answer_kind="answer_question",
        value={"domain_refs": ["domain.team_decision_log"]},
        request_kind="missing_context",
        target_ref="active_frame.domain_refs",
    )

    report = module.build_idea_to_spec_answer_rerun_input(
        answers_report=answer_report,
    )

    frame_hints = report["rerun_input_overlay"]["intake_overlay"]["active_frame_hints"]
    assert frame_hints == [
        {
            "answer_kind": "answer_question",
            "request_id": "clarification.repair.repair-review-unresolved-gaps",
            "request_kind": "missing_context",
            "target_artifact": "runs/candidate_spec_graph.json",
            "target_ref": "active_frame.domain_refs",
            "value": {"domain_refs": ["domain.team_decision_log"]},
        }
    ]


def test_answer_rerun_input_routes_non_ontology_reject_to_candidate_hints() -> None:
    module = load_module(
        RERUN_TOOL_PATH,
        "idea_to_spec_answer_rerun_input_candidate_reject_test",
    )
    answer_report = ready_answer_report_with_answer(
        answer_kind="reject",
        value={"reason": "Not part of the first candidate."},
        request_kind="candidate_gap",
        target_ref="candidate-spec.product.gaps.gap.optional-flow",
    )

    report = module.build_idea_to_spec_answer_rerun_input(
        answers_report=answer_report,
    )

    ontology_hints = report["rerun_input_overlay"]["ontology_review_hints"]
    candidate_hints = report["rerun_input_overlay"]["candidate_review_hints"]
    assert ontology_hints["rejected_terms"] == []
    assert candidate_hints["other"][0]["answer_kind"] == "reject"
    assert candidate_hints["other"][0]["request_kind"] == "candidate_gap"


def test_answer_rerun_input_blocks_project_local_term_without_value() -> None:
    module = load_module(
        RERUN_TOOL_PATH,
        "idea_to_spec_answer_rerun_input_missing_term_test",
    )
    answer_report = ready_answer_report_with_answer(
        answer_kind="propose_project_local_term",
        value={},
        request_kind="ontology_gap",
        target_ref="candidate-spec.product.gaps.ontology-gap.decision-owner",
    )

    report = module.build_idea_to_spec_answer_rerun_input(
        answers_report=answer_report,
    )

    assert report["readiness"]["ready"] is False
    assert "project_local_term_value_missing" in finding_ids(report)
    assert report["rerun_input_overlay"]["ontology_review_hints"]["project_local_terms"] == []


def test_answer_rerun_input_keeps_rejected_preview_edges_in_graph_hints() -> None:
    module = load_module(
        RERUN_TOOL_PATH,
        "idea_to_spec_answer_rerun_input_reject_edge_test",
    )
    answer_report = ready_answer_report_with_answer(
        answer_kind="reject_preview_edge",
        value={"edge_id": "preview.edge.product-to-command"},
        request_kind="graph_repair",
        target_ref="candidate_graph.preview_edges.preview.edge.product-to-command",
    )

    report = module.build_idea_to_spec_answer_rerun_input(
        answers_report=answer_report,
    )

    graph_edges = report["rerun_input_overlay"]["candidate_review_hints"]["graph_edges"]
    assert graph_edges[0]["answer_kind"] == "reject_preview_edge"
    assert graph_edges[0]["value"] == {"edge_id": "preview.edge.product-to-command"}


def test_answer_rerun_input_blocks_unready_answer_report() -> None:
    module = load_module(
        RERUN_TOOL_PATH,
        "idea_to_spec_answer_rerun_input_unready_test",
    )
    answer_report = copy.deepcopy(ready_answer_report())
    answer_report["readiness"]["ready"] = False
    answer_report["readiness"]["blocked_by"] = ["clarification.unresolved"]

    report = module.build_idea_to_spec_answer_rerun_input(
        answers_report=answer_report,
    )

    assert report["readiness"]["ready"] is False
    assert "answers_not_ready_for_rerun" in finding_ids(report)
    assert report["summary"]["project_local_term_count"] == 0


def test_answer_rerun_input_rejects_wrong_artifact_kind() -> None:
    module = load_module(
        RERUN_TOOL_PATH,
        "idea_to_spec_answer_rerun_input_wrong_kind_test",
    )
    answer_report = copy.deepcopy(ready_answer_report())
    answer_report["artifact_kind"] = "other_artifact"

    report = module.build_idea_to_spec_answer_rerun_input(
        answers_report=answer_report,
    )

    assert report["readiness"]["ready"] is False
    assert "answers_wrong_artifact_kind" in finding_ids(report)


def test_answer_rerun_input_strips_raw_trace_fields() -> None:
    module = load_module(
        RERUN_TOOL_PATH,
        "idea_to_spec_answer_rerun_input_privacy_test",
    )
    answer_report = copy.deepcopy(ready_answer_report())
    answer_report["answers"][0]["answer_kind"] = "answer_question"
    answer_report["answers"][0]["value"] = {
        "active_frame": {
            "domain_refs": ["domain.team_decision_log"],
            "raw_prompt": "private prompt trace",
        },
        "raw_model_output": "private model trace",
    }

    report = module.build_idea_to_spec_answer_rerun_input(
        answers_report=answer_report,
    )

    dumped = json.dumps(report)
    assert "private prompt trace" not in dumped
    assert "private model trace" not in dumped
    assert "domain.team_decision_log" in dumped


def test_answer_rerun_input_cli_writes_output(tmp_path: Path) -> None:
    answers_report = tmp_path / "idea_to_spec_clarification_answers.json"
    output = tmp_path / "idea_to_spec_answer_rerun_input.json"

    answer_result = subprocess.run(
        [
            sys.executable,
            str(ANSWERS_TOOL_PATH),
            "--requests",
            str(REQUESTS_FIXTURE),
            "--answers",
            str(ANSWERS_READY_FIXTURE),
            "--output",
            str(answers_report),
            "--strict",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert answer_result.returncode == 0

    result = subprocess.run(
        [
            sys.executable,
            str(RERUN_TOOL_PATH),
            "--answers",
            str(answers_report),
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
    assert report["artifact_kind"] == "idea_to_spec_answer_rerun_input"
    assert report["readiness"]["ready"] is True
    assert "rerun_input_ready" in result.stdout
