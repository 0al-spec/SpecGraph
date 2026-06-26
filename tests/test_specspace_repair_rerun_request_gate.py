from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

from test_specspace_repair_drafts_to_rerun_artifacts import (
    active_candidate,
    build_import_preview,
    draft_state_for_repair_session_path,
    promotion_gate,
    repair_session_for_requests_path,
    valid_candidate_graph,
    valid_clarification_requests,
    valid_intake,
    valid_repair_session,
    write_json,
)

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "specspace_repair_rerun_request_gate.py"
REQUEST_ID = "repair-rerun-request.team-decision-log.20260626T100000Z"


def load_module(path: Path, name: str) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def valid_request_state(
    *,
    import_preview_ref: str = "runs/specspace_repair_draft_import_preview.json",
    repair_session_ref: str = "runs/idea_to_spec_repair_session.json",
) -> dict[str, object]:
    return {
        "artifact_kind": "specspace_idea_to_spec_repair_rerun_request_state",
        "schema_version": 1,
        "state_owner": "SpecSpace",
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "source_artifacts": {
            "idea_to_spec_repair_session": repair_session_ref,
            "specspace_repair_draft_import_preview": import_preview_ref,
        },
        "requests": [
            {
                "id": REQUEST_ID,
                "status": "requested",
                "requested_action": "prepare_repair_draft_rerun",
                "workspace_id": "team-decision-log",
                "candidate_id": "team-decision-log",
                "repair_session_id": "repair-session.team-decision-log",
                "repair_session_ref": repair_session_ref,
                "draft_state_ref": "specspace-state://idea_to_spec_repair_drafts.json",
                "import_preview_ref": import_preview_ref,
                "rerun_report_ref": "runs/specspace_repair_draft_rerun_report.json",
                "requested_by": "operator://specspace-local",
                "created_at": "2026-06-26T10:00:00Z",
                "updated_at": "2026-06-26T10:00:00Z",
                "draft_count": 1,
                "accepted_for_rerun_count": 1,
                "operator_command": (
                    "make product-workspace-repair-draft-rerun "
                    f"SPECSPACE_REPAIR_DRAFT_RERUN_IMPORT_PREVIEW={import_preview_ref}"
                ),
                "canonical_mutations_allowed": False,
                "tracked_artifacts_written": False,
                "may_execute_specgraph": False,
                "may_run_make_target": False,
                "may_mutate_candidate_source_artifacts": False,
                "may_mutate_canonical_specs": False,
                "may_write_ontology_package": False,
                "may_accept_ontology_terms": False,
                "may_create_branch_or_commit": False,
                "may_open_pull_request": False,
                "may_execute_git_service_operation": False,
            }
        ],
        "summary": {
            "status": "rerun_requested",
            "request_count": 1,
            "active_request_count": 1,
            "workspace_count": 1,
        },
        "consumer_boundary": {
            "specspace_owned_state": True,
            "for_product_repair_workflow": True,
            "may_execute_specgraph": False,
            "may_execute_prompt_agent": False,
            "may_apply_to_specgraph": False,
            "may_apply_answers": False,
            "may_apply_decisions": False,
            "may_mutate_candidate_source_artifacts": False,
            "may_mutate_canonical_specs": False,
            "may_write_ontology_package": False,
            "may_accept_ontology_terms": False,
            "may_create_branch_or_commit": False,
            "may_open_pull_request": False,
            "may_execute_git_service_operation": False,
        },
        "authority_boundary": {
            "rerun_request_state_is_authority": False,
            "specgraph_execution_authority": False,
            "specgraph_artifact_authority": False,
            "ontology_authority": False,
            "git_service_authority": False,
            "canonical_mutations_allowed": False,
        },
    }


def build_gate_report(request_state: dict[str, object] | None = None) -> dict[str, object]:
    module = load_module(TOOL_PATH, "specspace_repair_rerun_request_gate_under_test")
    return module.build_specspace_repair_rerun_request_gate(
        request_state=request_state or valid_request_state(),
        import_preview=build_import_preview(),
        repair_session=valid_repair_session(),
        request_state_path=ROOT / "runs" / "idea_to_spec_repair_rerun_requests.json",
        import_preview_path=ROOT / "runs" / "specspace_repair_draft_import_preview.json",
        repair_session_path=ROOT / "runs" / "idea_to_spec_repair_session.json",
        workspace_id="team-decision-log",
    )


def finding_ids(report: dict[str, object]) -> set[str]:
    return {
        str(finding.get("finding_id"))
        for finding in report.get("findings", [])
        if isinstance(finding, dict)
    }


def test_specspace_repair_rerun_request_gate_accepts_operator_intent() -> None:
    report = build_gate_report()

    assert report["artifact_kind"] == "specspace_repair_rerun_request_gate"
    assert report["proposal_id"] == "0174"
    assert report["contract_ref"] == (
        "specgraph.idea-to-spec.specspace-repair-rerun-request-gate.v0.1"
    )
    assert report["readiness"]["ready"] is True
    assert report["summary"]["selected_request_id"] == REQUEST_ID
    assert report["selected_request"]["may_run_make_target"] is False
    assert report["authority_boundary"]["may_execute_specgraph_from_request"] is False
    assert report["authority_boundary"]["may_run_make_target_from_request"] is False
    assert report["recommended_invocation"]["make_target"] == (
        "product-workspace-requested-repair-draft-rerun"
    )


def test_specspace_repair_rerun_request_gate_rejects_make_authority_claim() -> None:
    request_state = valid_request_state()
    request_state["requests"][0]["may_run_make_target"] = True

    report = build_gate_report(request_state)

    assert report["readiness"]["ready"] is False
    assert "request_record_authority_expanded" in finding_ids(report)


def test_specspace_repair_rerun_request_gate_rejects_import_preview_ref_mismatch() -> None:
    request_state = valid_request_state(import_preview_ref="runs/stale_import_preview.json")

    report = build_gate_report(request_state)

    assert report["readiness"]["ready"] is False
    assert "request_import_preview_ref_mismatch" in finding_ids(report)


def test_specspace_repair_rerun_request_gate_cli_strict_fails_when_not_ready(
    tmp_path: Path,
) -> None:
    request_path = tmp_path / "idea_to_spec_repair_rerun_requests.json"
    preview_path = tmp_path / "specspace_repair_draft_import_preview.json"
    session_path = tmp_path / "idea_to_spec_repair_session.json"
    output_path = tmp_path / "specspace_repair_rerun_request_gate.json"
    request_state = valid_request_state(
        import_preview_ref=preview_path.as_posix(),
        repair_session_ref=session_path.as_posix(),
    )
    request_state["requests"][0]["may_create_branch_or_commit"] = True

    write_json(request_path, request_state)
    write_json(preview_path, build_import_preview())
    write_json(session_path, valid_repair_session())

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--request-state",
            str(request_path),
            "--import-preview",
            str(preview_path),
            "--repair-session",
            str(session_path),
            "--workspace-id",
            "team-decision-log",
            "--output",
            str(output_path),
            "--strict",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    report = load_json(output_path)
    assert "request_record_authority_expanded" in finding_ids(report)


def test_product_workspace_requested_repair_draft_rerun_make_target_threads_paths(
    tmp_path: Path,
) -> None:
    request_path = tmp_path / "idea_to_spec_repair_rerun_requests.json"
    draft_state_path = tmp_path / "idea_to_spec_repair_drafts.json"
    preview_path = tmp_path / "specspace_repair_draft_import_preview.json"
    gate_path = tmp_path / "specspace_repair_rerun_request_gate.json"
    repair_session_path = tmp_path / "idea_to_spec_repair_session.input.json"
    requests_path = tmp_path / "idea_to_spec_clarification_requests.json"
    active_candidate_path = tmp_path / "active_idea_to_spec_candidate.json"
    intake_path = tmp_path / "idea_event_storming_intake.json"
    candidate_graph_path = tmp_path / "candidate_spec_graph.json"
    promotion_gate_path = tmp_path / "idea_to_spec_promotion_gate.json"
    outputs = {
        "answers": tmp_path / "idea_to_spec_clarification_answers.json",
        "ontology_decisions": tmp_path / "product_ontology_gap_review_decisions.json",
        "rerun_input": tmp_path / "idea_to_spec_answer_rerun_input.json",
        "rerun_preview": tmp_path / "idea_to_spec_rerun_preview.json",
        "rerun_materialization": tmp_path / "idea_to_spec_rerun_materialization.json",
        "repair_session": tmp_path / "idea_to_spec_repair_session.json",
        "rerun_report": tmp_path / "specspace_repair_draft_rerun_report.json",
    }
    draft_state = draft_state_for_repair_session_path(repair_session_path)
    repair_session = repair_session_for_requests_path(requests_path)
    request_state = valid_request_state(
        import_preview_ref=preview_path.as_posix(),
        repair_session_ref=repair_session_path.as_posix(),
    )
    request_state["requests"][0]["repair_session_id"] = "repair-session.team-decision-log"

    write_json(request_path, request_state)
    write_json(draft_state_path, draft_state)
    write_json(repair_session_path, repair_session)
    write_json(requests_path, valid_clarification_requests())
    write_json(active_candidate_path, active_candidate(promotion_gate_path.as_posix()))
    write_json(intake_path, valid_intake())
    write_json(candidate_graph_path, valid_candidate_graph())
    write_json(promotion_gate_path, promotion_gate())

    result = subprocess.run(
        [
            "make",
            "product-workspace-requested-repair-draft-rerun",
            f"PYTHON={sys.executable}",
            f"SPECSPACE_REPAIR_RERUN_REQUEST_STATE={request_path}",
            f"SPECSPACE_REPAIR_RERUN_REQUEST_IMPORT_PREVIEW={preview_path}",
            f"SPECSPACE_REPAIR_RERUN_REQUEST_REPAIR_SESSION={repair_session_path}",
            f"SPECSPACE_REPAIR_RERUN_REQUEST_OUTPUT={gate_path}",
            "SPECSPACE_REPAIR_RERUN_REQUEST_WORKSPACE_ID=team-decision-log",
            f"SPECSPACE_REPAIR_DRAFT_IMPORT_DRAFTS={draft_state_path}",
            f"SPECSPACE_REPAIR_DRAFT_IMPORT_REPAIR_SESSION={repair_session_path}",
            f"SPECSPACE_REPAIR_DRAFT_IMPORT_CLARIFICATION_REQUESTS={requests_path}",
            f"SPECSPACE_REPAIR_DRAFT_IMPORT_OUTPUT={preview_path}",
            f"SPECSPACE_REPAIR_DRAFT_RERUN_REPAIR_SESSION={repair_session_path}",
            f"SPECSPACE_REPAIR_DRAFT_RERUN_CLARIFICATION_REQUESTS={requests_path}",
            f"SPECSPACE_REPAIR_DRAFT_RERUN_ACTIVE_CANDIDATE={active_candidate_path}",
            f"SPECSPACE_REPAIR_DRAFT_RERUN_INTAKE={intake_path}",
            f"SPECSPACE_REPAIR_DRAFT_RERUN_CANDIDATE_GRAPH={candidate_graph_path}",
            f"SPECSPACE_REPAIR_DRAFT_RERUN_PROMOTION_GATE={promotion_gate_path}",
            f"IDEA_TO_SPEC_CLARIFICATION_ANSWERS_OUTPUT={outputs['answers']}",
            f"PRODUCT_ONTOLOGY_GAP_REVIEW_DECISIONS_OUTPUT={outputs['ontology_decisions']}",
            f"IDEA_TO_SPEC_ANSWER_RERUN_INPUT_OUTPUT={outputs['rerun_input']}",
            f"IDEA_TO_SPEC_RERUN_PREVIEW_OUTPUT={outputs['rerun_preview']}",
            f"IDEA_TO_SPEC_RERUN_MATERIALIZATION_OUTPUT={outputs['rerun_materialization']}",
            f"IDEA_TO_SPEC_REPAIR_SESSION_OUTPUT={outputs['repair_session']}",
            f"SPECSPACE_REPAIR_DRAFT_RERUN_REPORT_OUTPUT={outputs['rerun_report']}",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    gate = load_json(gate_path)
    rerun_report = load_json(outputs["rerun_report"])
    assert gate["readiness"]["ready"] is True
    assert gate["summary"]["selected_request_id"] == REQUEST_ID
    assert rerun_report["summary"]["status"] == "repair_draft_rerun_ready"
    assert outputs["repair_session"].exists()
