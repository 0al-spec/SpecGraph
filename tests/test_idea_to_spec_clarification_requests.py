from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "idea_to_spec_clarification_requests.py"
SESSION_TOOL_PATH = ROOT / "tools" / "user_idea_intake_session.py"
INTAKE_TOOL_PATH = ROOT / "tools" / "idea_event_storming_intake.py"
REPAIR_TOOL_PATH = ROOT / "tools" / "candidate_repair_loop.py"
SESSION_FIXTURE = ROOT / "tests" / "fixtures" / "user_idea_intake_session"
NEEDS_CLARIFICATION_FIXTURE = SESSION_FIXTURE / "raw_idea_needs_clarification.json"
INTAKE_REVIEW_REQUIRED = (
    ROOT / "tests" / "fixtures" / "idea_event_storming_intake" / "idea_review_required.json"
)
REPAIR_FIXTURE = ROOT / "tests" / "fixtures" / "candidate_repair_loop"
CANDIDATE_REPAIRABLE = REPAIR_FIXTURE / "candidate_graph_repairable.json"
PRE_SIB_REPAIR_REQUIRED = REPAIR_FIXTURE / "pre_sib_repair_required.json"


def load_module(path: Path, name: str) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def supported_python() -> str:
    candidates = [
        sys.executable,
        str(ROOT / ".venv" / "bin" / "python"),
        *(shutil.which(name) or "" for name in ("python3.13", "python3.12", "python3.11")),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        candidate_path = Path(candidate)
        if candidate_path.is_absolute() and not candidate_path.exists():
            continue
        result = subprocess.run(
            [candidate, "tools/check_python_version.py"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return candidate
    pytest.skip("No Python >=3.10 interpreter available for Makefile integration test")


def request_ids(report: dict[str, object]) -> set[str]:
    requests = report["clarification_requests"]
    assert isinstance(requests, list)
    return {request["id"] for request in requests if isinstance(request, dict)}


def request_kinds(report: dict[str, object]) -> set[str]:
    requests = report["clarification_requests"]
    assert isinstance(requests, list)
    return {request["kind"] for request in requests if isinstance(request, dict)}


def request_by_id(report: dict[str, object], request_id: str) -> dict[str, object]:
    requests = report["clarification_requests"]
    assert isinstance(requests, list)
    for request in requests:
        if isinstance(request, dict) and request.get("id") == request_id:
            return request
    raise AssertionError(f"request not found: {request_id}")


def test_clarification_requests_collects_intake_session_questions() -> None:
    session_module = load_module(SESSION_TOOL_PATH, "user_idea_session_for_clarifications")
    clarification_module = load_module(TOOL_PATH, "clarification_requests_for_session")
    session, source = session_module.build_user_idea_intake_session(
        load_json(NEEDS_CLARIFICATION_FIXTURE),
        source_path=NEEDS_CLARIFICATION_FIXTURE,
    )

    report = clarification_module.build_idea_to_spec_clarification_requests(
        user_idea_intake_session=session,
    )

    assert source is None
    assert report["artifact_kind"] == "idea_to_spec_clarification_requests"
    assert report["proposal_id"] == "0163"
    assert report["canonical_mutations_allowed"] is False
    assert report["tracked_artifacts_written"] is False
    assert report["readiness"]["ready"] is False
    assert report["summary"]["request_count"] == 9
    assert report["summary"]["blocking_request_count"] == 9
    assert report["summary"]["review_required_request_count"] == 0
    assert "clarification.intake.question-active-frame-ontology-refs" in request_ids(report)
    assert "clarification.intake.question-event-storming-actors" in request_ids(report)
    assert request_kinds(report) == {"missing_context", "missing_event_storming_context"}
    dumped = json.dumps(report)
    raw_text = load_json(NEEDS_CLARIFICATION_FIXTURE)["idea"]["text"]
    assert raw_text not in dumped
    assert "private prompt trace" not in dumped


def test_clarification_requests_project_repair_context_actions() -> None:
    repair_module = load_module(REPAIR_TOOL_PATH, "repair_loop_for_clarifications")
    clarification_module = load_module(TOOL_PATH, "clarification_requests_for_repair_loop")
    pre_sib = load_json(PRE_SIB_REPAIR_REQUIRED)
    repair_loop = repair_module.build_candidate_repair_loop_report(
        candidate_graph=load_json(CANDIDATE_REPAIRABLE),
        pre_sib_report=pre_sib,
        candidate_graph_path=CANDIDATE_REPAIRABLE,
        pre_sib_report_path=PRE_SIB_REPAIR_REQUIRED,
    )

    report = clarification_module.build_idea_to_spec_clarification_requests(
        pre_sib_report=pre_sib,
        repair_loop=repair_loop,
    )

    kinds = request_kinds(report)
    assert {"ontology_gap", "weak_claim", "missing_acceptance_criteria", "graph_repair"} <= kinds
    assert "clarification.repair.repair-ontology-gap-candidate-spec-numeric-input" in request_ids(
        report
    )
    assert "clarification.repair.repair-review-unresolved-gaps" in request_ids(report)
    assert report["summary"]["blocking_request_count"] == 2
    pre_sib_request = next(
        request
        for request in report["clarification_requests"]
        if request["id"] == "clarification.pre-sib.pre-sib-orphan-nodes"
    )
    assert pre_sib_request["severity"] == "advisory"
    assert pre_sib_request["status"] == "covered_by_repair_preview"
    repair_request = next(
        request
        for request in report["clarification_requests"]
        if request["id"] == "clarification.repair.repair-review-unresolved-gaps"
    )
    assert repair_request["severity"] == "blocking"
    assert repair_request["suggested_actions"] == [
        "bind_existing_term",
        "alias",
        "propose_project_local_term",
        "reject",
        "defer",
    ]


def test_clarification_requests_collects_event_storming_context_questions() -> None:
    intake_module = load_module(INTAKE_TOOL_PATH, "event_storming_for_clarifications")
    clarification_module = load_module(TOOL_PATH, "clarification_requests_for_intake")
    intake = intake_module.build_idea_event_storming_intake(
        load_json(INTAKE_REVIEW_REQUIRED),
        source_path=INTAKE_REVIEW_REQUIRED,
    )

    report = clarification_module.build_idea_to_spec_clarification_requests(
        idea_event_storming_intake=intake,
    )

    assert report["readiness"]["ready"] is False
    assert report["summary"]["blocking_request_count"] > 0
    assert any(
        request["id"].startswith("clarification.event-storming.context-question")
        for request in report["clarification_requests"]
    )
    assert "missing_context" in request_kinds(report)
    assert "missing_event_storming_context" in request_kinds(report)
    subsystem_request = request_by_id(
        report,
        "clarification.event-storming.context-question-subsystem",
    )
    assert subsystem_request["suggested_answer_shape"] == "text"
    assert subsystem_request["blocks"] == ["active_frame.subsystem"]


def test_clarification_requests_rejects_missing_sources() -> None:
    clarification_module = load_module(TOOL_PATH, "clarification_requests_missing_sources")

    report = clarification_module.build_idea_to_spec_clarification_requests()

    assert report["readiness"]["ready"] is False
    assert report["findings"][0]["finding_id"] == "clarification_sources_missing"
    assert report["summary"]["request_count"] == 0


def test_clarification_requests_cli_writes_output(tmp_path: Path) -> None:
    session_module = load_module(SESSION_TOOL_PATH, "user_idea_session_for_cli")
    repair_module = load_module(REPAIR_TOOL_PATH, "repair_loop_for_cli")
    session, _source = session_module.build_user_idea_intake_session(
        load_json(NEEDS_CLARIFICATION_FIXTURE),
        source_path=NEEDS_CLARIFICATION_FIXTURE,
    )
    repair_loop = repair_module.build_candidate_repair_loop_report(
        candidate_graph=load_json(CANDIDATE_REPAIRABLE),
        pre_sib_report=load_json(PRE_SIB_REPAIR_REQUIRED),
        candidate_graph_path=CANDIDATE_REPAIRABLE,
        pre_sib_report_path=PRE_SIB_REPAIR_REQUIRED,
    )
    session_path = tmp_path / "user_idea_intake_session.json"
    repair_path = tmp_path / "candidate_repair_loop_report.json"
    output_path = tmp_path / "idea_to_spec_clarification_requests.json"
    session_path.write_text(json.dumps(session), encoding="utf-8")
    repair_path.write_text(json.dumps(repair_loop), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--session",
            str(session_path),
            "--repair-loop",
            str(repair_path),
            "--intake",
            str(tmp_path / "missing-intake.json"),
            "--candidate-graph",
            str(tmp_path / "missing-candidate-graph.json"),
            "--pre-sib",
            str(tmp_path / "missing-pre-sib.json"),
            "--ontology-gap-review",
            str(tmp_path / "missing-ontology-gap-review.json"),
            "--output",
            str(output_path),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    report = load_json(output_path)
    assert report["artifact_kind"] == "idea_to_spec_clarification_requests"
    assert report["summary"]["request_count"] == 14
    assert "clarification_required" in result.stdout
    repair_request = request_by_id(
        report,
        "clarification.repair.repair-review-unresolved-gaps",
    )
    assert repair_request["target_artifact"] == str(repair_path)


def test_clarification_requests_review_required_gaps_block_readiness() -> None:
    clarification_module = load_module(TOOL_PATH, "clarification_requests_candidate_gaps")
    candidate_graph = {
        "artifact_kind": "candidate_spec_graph",
        "contract_ref": "specgraph.idea-to-spec.candidate-spec-graph.v0.1",
        "nodes": [
            {
                "id": "candidate-spec.product-boundary",
                "gaps": [
                    {
                        "id": "gap.shared",
                        "kind": "vocabulary_question",
                        "statement": "Confirm the product term.",
                    }
                ],
            },
            {
                "id": "candidate-spec.workflow",
                "gaps": [
                    {
                        "id": "gap.shared",
                        "kind": "ontology_gap",
                        "statement": "Bind the workflow term.",
                    }
                ],
            },
        ],
    }

    report = clarification_module.build_idea_to_spec_clarification_requests(
        candidate_graph=candidate_graph,
        candidate_graph_target="custom/candidate_graph.json",
    )

    assert report["readiness"]["ready"] is False
    assert report["readiness"]["review_state"] == "clarification_review_required"
    assert report["summary"]["blocking_request_count"] == 0
    assert report["summary"]["review_required_request_count"] == 2
    product_gap = request_by_id(
        report,
        "clarification.candidate-gap.candidate-spec-product-boundary-gaps-gap-shared",
    )
    assert product_gap["kind"] == "candidate_gap"
    assert product_gap["target_artifact"] == "custom/candidate_graph.json"
    assert product_gap["target_ref"] == "candidate-spec.product-boundary.gaps.gap.shared"
    assert product_gap["blocks"] == ["candidate-spec.product-boundary.gaps.gap.shared"]
    assert product_gap["suggested_actions"] == [
        "answer_question",
        "provide_candidate_context",
        "reject",
        "defer",
    ]
    ontology_gap = request_by_id(
        report,
        "clarification.candidate-gap.candidate-spec-workflow-gaps-gap-shared",
    )
    assert ontology_gap["kind"] == "ontology_gap"
    assert ontology_gap["target_ref"] == "candidate-spec.workflow.gaps.gap.shared"
    assert ontology_gap["suggested_actions"] == [
        "bind_existing_term",
        "alias",
        "propose_project_local_term",
        "reject",
        "defer",
    ]


def test_clarification_requests_adds_depth_driven_event_storming_requests() -> None:
    clarification_module = load_module(TOOL_PATH, "clarification_requests_structure_depth")
    maturity = {
        "artifact_kind": "idea_maturity_metrics_report",
        "contract_ref": "specgraph.idea-to-spec.maturity-metrics-report.v0.1",
        "source_artifacts": ["runs/custom/idea_event_storming_intake.json"],
        "groups": {
            "candidate_structure_depth": {
                "actor_count": 0,
                "command_count": 2,
                "domain_event_count": 2,
                "policy_count": 0,
                "constraint_count": 1,
                "topology_edge_count": 0,
                "workflow_edge_count": 0,
                "requirement_count": 2,
                "acceptance_criteria_count": 2,
            }
        },
    }

    report = clarification_module.build_idea_to_spec_clarification_requests(
        idea_maturity_report=maturity,
        idea_event_storming_intake_target="runs/custom/idea_event_storming_intake.json",
        idea_maturity_target="runs/custom/idea_maturity_metrics_report.json",
    )

    assert report["readiness"]["ready"] is False
    assert report["readiness"]["review_state"] == "clarification_review_required"
    assert report["summary"]["blocking_request_count"] == 0
    assert report["summary"]["review_required_request_count"] == 2
    actor_request = request_by_id(report, "clarification.depth.actors")
    assert actor_request["kind"] == "event_storming_gap"
    assert actor_request["severity"] == "review_required"
    assert actor_request["target_artifact"] == "runs/custom/idea_event_storming_intake.json"
    assert actor_request["target_ref"] == "event_storming_hints.actors"
    assert actor_request["suggested_answer_shape"] == "event_storming_entry[]"
    assert actor_request["suggested_actions"] == ["answer_question", "defer_candidate"]
    assert actor_request["source_findings"][0]["evidence"]["source_ref"] == (
        "runs/custom/idea_maturity_metrics_report.json#groups.candidate_structure_depth.actor_count"
    )


def test_clarification_requests_missing_depth_group_is_not_faked() -> None:
    clarification_module = load_module(TOOL_PATH, "clarification_requests_structure_depth_missing")

    report = clarification_module.build_idea_to_spec_clarification_requests(
        idea_maturity_report={
            "artifact_kind": "idea_maturity_metrics_report",
            "contract_ref": "specgraph.idea-to-spec.maturity-metrics-report.v0.1",
            "groups": {},
        },
    )

    assert report["summary"]["request_count"] == 0
    assert report["readiness"]["ready"] is True
    assert report["readiness"]["review_state"] == "clarification_clear"


def test_clarification_requests_does_not_infer_depth_when_intake_not_loaded() -> None:
    clarification_module = load_module(
        TOOL_PATH,
        "clarification_requests_structure_depth_without_intake",
    )
    maturity = {
        "artifact_kind": "idea_maturity_metrics_report",
        "contract_ref": "specgraph.idea-to-spec.maturity-metrics-report.v0.1",
        "status": "ready",
        "source_artifacts": ["runs/candidate_spec_graph.json"],
        "groups": {
            "candidate_structure_depth": {
                "actor_count": 0,
                "command_count": 0,
                "domain_event_count": 0,
                "policy_count": 0,
                "constraint_count": 0,
            }
        },
    }

    report = clarification_module.build_idea_to_spec_clarification_requests(
        idea_maturity_report=maturity,
    )

    assert report["summary"]["request_count"] == 0
    assert report["readiness"]["ready"] is True


def test_clarification_requests_does_not_infer_depth_from_invalid_maturity() -> None:
    clarification_module = load_module(
        TOOL_PATH,
        "clarification_requests_invalid_structure_depth",
    )
    maturity = {
        "artifact_kind": "idea_maturity_metrics_report",
        "contract_ref": "specgraph.idea-to-spec.maturity-metrics-report.v0.1",
        "status": "invalid",
        "source_artifacts": ["runs/idea_event_storming_intake.json"],
        "groups": {
            "candidate_structure_depth": {
                "actor_count": 0,
                "command_count": 0,
                "domain_event_count": 0,
                "policy_count": 0,
                "constraint_count": 0,
            }
        },
    }

    report = clarification_module.build_idea_to_spec_clarification_requests(
        idea_maturity_report=maturity,
    )

    assert report["summary"]["request_count"] == 0
    assert report["readiness"]["ready"] is True


def test_clarification_requests_rejects_unsupported_maturity_contract() -> None:
    clarification_module = load_module(
        TOOL_PATH,
        "clarification_requests_unsupported_maturity_contract",
    )
    maturity = {
        "artifact_kind": "idea_maturity_metrics_report",
        "contract_ref": "specgraph.idea-to-spec.maturity-metrics-report.v0.0",
        "source_artifacts": ["runs/idea_event_storming_intake.json"],
        "groups": {"candidate_structure_depth": {"actor_count": 0}},
    }

    report = clarification_module.build_idea_to_spec_clarification_requests(
        idea_maturity_report=maturity,
    )

    assert report["readiness"]["ready"] is False
    assert report["findings"][0]["finding_id"] == "idea_maturity_contract_invalid"
    assert report["summary"]["request_count"] == 0


def test_product_workspace_raw_idea_writes_clarification_before_abort(tmp_path: Path) -> None:
    output_path = tmp_path / "idea_to_spec_clarification_requests.json"
    result = subprocess.run(
        [
            "make",
            "product-workspace-active-candidate",
            f"PYTHON={supported_python()}",
            f"PRODUCT_WORKSPACE_IDEA_SOURCE={NEEDS_CLARIFICATION_FIXTURE}",
            f"USER_IDEA_INTAKE_SESSION_OUTPUT={tmp_path / 'session.json'}",
            f"USER_IDEA_INTAKE_SESSION_SOURCE_OUTPUT={tmp_path / 'source.json'}",
            f"USER_IDEA_EVENT_STORMING_SEED_OUTPUT={tmp_path / 'seed.json'}",
            f"IDEA_TO_SPEC_CLARIFICATION_OUTPUT={output_path}",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert output_path.exists()
    report = load_json(output_path)
    assert report["readiness"]["ready"] is False
    assert report["summary"]["blocking_request_count"] == 9
    assert not (tmp_path / "source.json").exists()
