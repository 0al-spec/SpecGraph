from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "specspace_repair_drafts_to_rerun_artifacts.py"
IMPORT_PREVIEW_TOOL_PATH = ROOT / "tools" / "specspace_repair_draft_import_preview.py"
REQUEST_ID = "clarification.candidate-gap.ontology-gap-decision-record"
TARGET_REF = "candidate-spec.decision-record.gaps.ontology-gap.decision-record"


def load_module(path: Path, name: str) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def valid_clarification_requests() -> dict[str, object]:
    return {
        "artifact_kind": "idea_to_spec_clarification_requests",
        "schema_version": 1,
        "proposal_id": "0163",
        "contract_ref": "specgraph.idea-to-spec.clarification-requests.v0.1",
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "clarification_requests": [
            {
                "id": REQUEST_ID,
                "kind": "ontology_gap",
                "severity": "blocking",
                "status": "open",
                "target_artifact": "runs/candidate_spec_graph.json",
                "target_ref": TARGET_REF,
                "question": "Should Decision Record bind or remain local?",
                "suggested_actions": [
                    "bind_existing_term",
                    "alias",
                    "propose_project_local_term",
                    "reject",
                    "defer",
                ],
                "suggested_answer_shape": "ontology decision action",
            }
        ],
        "readiness": {
            "ready": False,
            "review_state": "clarification_required",
            "blocked_by": [REQUEST_ID],
        },
        "authority_boundary": {"may_write_ontology_package": False},
        "summary": {
            "status": "clarification_required",
            "request_count": 1,
            "blocking_request_count": 1,
        },
    }


def valid_repair_session() -> dict[str, object]:
    return {
        "artifact_kind": "idea_to_spec_repair_session_journal",
        "schema_version": 1,
        "proposal_id": "0171",
        "contract_ref": "specgraph.idea-to-spec.repair-session-journal.v0.1",
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "session": {
            "session_id": "repair-session.team-decision-log",
            "candidate_id": "team-decision-log",
            "workspace_route": "/team-decision-log",
            "workflow_lane": "product_idea_to_spec",
            "governance_profile": "product_workspace",
            "target_repository_role": "product_spec_workspace",
        },
        "source_artifacts": {
            "clarification_requests": {
                "artifact_kind": "idea_to_spec_clarification_requests",
                "contract_ref": "specgraph.idea-to-spec.clarification-requests.v0.1",
                "source_ref": "runs/idea_to_spec_clarification_requests.json",
            }
        },
        "workflow_journal": {"stages": [], "accepted_answers": [], "ontology_decisions": []},
        "readiness_impact": {
            "ready_for_candidate_approval": False,
            "ready_for_platform_promotion": False,
            "unresolved_ontology_gap_count": 1,
            "resolved_ontology_gap_count": 0,
        },
        "readiness": {
            "ready": True,
            "review_state": "repair_session_journal_ready",
            "blocked_by": [],
        },
        "authority_boundary": {
            "may_execute_prompt_agent": False,
            "may_apply_answers_to_source_artifacts": False,
            "may_apply_decisions_to_source_artifacts": False,
            "may_mutate_candidate_source_artifacts": False,
            "may_mutate_canonical_specs": False,
            "may_write_ontology_package": False,
            "may_accept_ontology_terms": False,
            "may_create_branch_or_commit": False,
        },
        "summary": {
            "status": "repair_session_journal_ready",
            "candidate_id": "team-decision-log",
            "unresolved_ontology_gap_count": 1,
        },
    }


def valid_draft_state() -> dict[str, object]:
    return {
        "artifact_kind": "specspace_idea_to_spec_repair_draft_state",
        "schema_version": 1,
        "state_owner": "SpecSpace",
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "source_artifacts": {
            "idea_to_spec_repair_session": "runs/idea_to_spec_repair_session.json"
        },
        "consumer_boundary": {
            "specspace_owned_state": True,
            "for_product_repair_workflow": True,
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
        },
        "authority_boundary": {
            "repair_draft_state_is_authority": False,
            "specgraph_artifact_authority": False,
            "ontology_authority": False,
            "git_service_authority": False,
            "canonical_mutations_allowed": False,
        },
        "drafts": [
            {
                "draft_id": "specspace-repair-draft::team-decision-log::decision-record",
                "workspace_id": "team-decision-log",
                "candidate_id": "team-decision-log",
                "repair_session_id": "repair-session.team-decision-log",
                "repair_session_ref": "runs/idea_to_spec_repair_session.json",
                "request_id": REQUEST_ID,
                "request_kind": "ontology_gap",
                "request_status": "open",
                "target_ref": TARGET_REF,
                "target_artifact": "runs/candidate_spec_graph.json",
                "allowed_action": "propose_project_local_term",
                "answer_value": {
                    "terms": ["Decision Record"],
                    "term_scope": "project_local",
                    "raw_operator_note": "private note",
                },
                "operator_ref": "operator://local-reviewer",
                "created_at": "2026-06-25T09:00:00Z",
                "updated_at": "2026-06-25T09:01:00Z",
                "source_artifact": "runs/idea_to_spec_repair_session.json",
                "canonical_mutations_allowed": False,
                "tracked_artifacts_written": False,
                "applies_to_specgraph": False,
                "applies_to_candidate_artifacts": False,
                "mutates_canonical_specs": False,
                "writes_ontology_package": False,
                "accepts_ontology_terms": False,
                "creates_branch_or_commit": False,
                "opens_pull_request": False,
            }
        ],
        "summary": {"status": "repair_drafts_recorded", "draft_count": 1},
    }


def draft_state_for_repair_session_path(path: Path) -> dict[str, object]:
    draft_state = deepcopy(valid_draft_state())
    draft_state["source_artifacts"]["idea_to_spec_repair_session"] = path.as_posix()
    draft_state["drafts"][0]["repair_session_ref"] = path.as_posix()
    draft_state["drafts"][0]["source_artifact"] = path.as_posix()
    return draft_state


def repair_session_for_requests_path(path: Path) -> dict[str, object]:
    session = deepcopy(valid_repair_session())
    session["source_artifacts"]["clarification_requests"]["source_ref"] = path.as_posix()
    return session


def active_candidate(promotion_gate_ref: str = "runs/idea_to_spec_promotion_gate.json") -> dict:
    return {
        "artifact_kind": "active_idea_to_spec_candidate",
        "schema_version": 1,
        "proposal_id": "0155",
        "contract_ref": "specgraph.idea-to-spec.active-candidate-source.v0.1",
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "candidate": {
            "candidate_id": "team-decision-log",
            "display_name": "Team Decision Log",
            "workflow_lane": "product_idea_to_spec",
            "public_route": "/team-decision-log",
            "governance_profile": "product_workspace",
            "target_repository_role": "product_spec_workspace",
        },
        "readiness": {
            "ready": False,
            "review_state": "active_candidate_review_required",
            "blocked_by": ["promotion_gate_not_ready"],
        },
        "source_artifacts": {"promotion_gate": {"source_ref": promotion_gate_ref}},
        "platform_handoff_surfaces": {
            "idea_to_spec_promotion_gate.json": {"source_ref": promotion_gate_ref}
        },
        "authority_boundary": {"may_mutate_canonical_specs": False},
        "summary": {"status": "active_candidate_review_required"},
    }


def valid_intake() -> dict:
    return {
        "artifact_kind": "idea_event_storming_intake",
        "schema_version": 1,
        "proposal_id": "0149",
        "contract_ref": "specgraph.idea-to-spec.event-storming-intake.v0.1",
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "active_frame": {
            "project": "TeamDecisionLog",
            "ontology_refs": ["ontology://specgraph-core"],
            "context_refs": ["context.idea_to_spec"],
            "domain_refs": ["domain.team_decision_log"],
        },
        "event_storming": {},
        "candidate_graph_readiness": {"ready": True},
        "authority_boundary": {"may_mutate_canonical_specs": False},
        "summary": {"status": "ready_for_candidate_graph"},
    }


def valid_candidate_graph() -> dict:
    return {
        "artifact_kind": "candidate_spec_graph",
        "schema_version": 1,
        "proposal_id": "0150",
        "contract_ref": "specgraph.idea-to-spec.candidate-spec-graph.v0.1",
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "nodes": [
            {
                "id": "candidate-spec.decision-record",
                "title": "Decision Record",
                "kind": "behavior_requirement",
                "gaps": [
                    {
                        "id": "ontology-gap.decision-record",
                        "kind": "ontology_gap",
                        "term": "Decision Record",
                        "source_ref": "event.decision-recorded",
                    }
                ],
                "requirements": [],
                "acceptance_criteria": [],
                "claims": [],
            }
        ],
        "edges": [],
        "pre_sib_readiness": {"ready": True, "review_state": "ready_for_pre_sib"},
        "authority_boundary": {"may_mutate_canonical_specs": False},
        "summary": {"status": "ready_for_pre_sib", "node_count": 1, "gap_count": 1},
    }


def promotion_gate() -> dict:
    return {
        "artifact_kind": "idea_to_spec_promotion_gate",
        "schema_version": 1,
        "proposal_id": "0154",
        "contract_ref": "specgraph.idea-to-spec.promotion-gate.v0.1",
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "readiness": {
            "ready": False,
            "review_state": "idea_to_spec_promotion_blocked",
            "blocked_by": ["promotion_paths_missing"],
        },
        "authority_boundary": {"may_create_branch_or_commit": False},
        "summary": {"status": "idea_to_spec_promotion_blocked", "promotion_path_count": 0},
    }


def build_import_preview() -> dict[str, object]:
    return build_import_preview_for_paths(
        draft_state_path=ROOT / "runs" / "idea_to_spec_repair_drafts.json",
        repair_session_path=ROOT / "runs" / "idea_to_spec_repair_session.json",
        requests_path=ROOT / "runs" / "idea_to_spec_clarification_requests.json",
    )


def build_import_preview_for_paths(
    *,
    draft_state_path: Path,
    repair_session_path: Path,
    requests_path: Path,
    draft_state: dict[str, object] | None = None,
    repair_session: dict[str, object] | None = None,
    clarification_requests: dict[str, object] | None = None,
) -> dict[str, object]:
    module = load_module(
        IMPORT_PREVIEW_TOOL_PATH,
        "specspace_repair_draft_import_preview_for_0173_test",
    )
    return module.build_specspace_repair_draft_import_preview(
        draft_state=draft_state or valid_draft_state(),
        repair_session=repair_session or valid_repair_session(),
        clarification_requests=clarification_requests or valid_clarification_requests(),
        draft_state_path=draft_state_path,
        repair_session_path=repair_session_path,
        clarification_requests_path=requests_path,
    )


def build_rerun_report(import_preview: dict[str, object] | None = None) -> tuple[dict, dict]:
    module = load_module(TOOL_PATH, "specspace_repair_drafts_to_rerun_under_test")
    return module.build_specspace_repair_drafts_to_rerun_artifacts(
        import_preview=import_preview or build_import_preview(),
        repair_session=valid_repair_session(),
        clarification_requests=valid_clarification_requests(),
        active_candidate=active_candidate(),
        intake=valid_intake(),
        candidate_graph=valid_candidate_graph(),
        promotion_gate=promotion_gate(),
        import_preview_path=ROOT / "runs" / "specspace_repair_draft_import_preview.json",
        repair_session_path=ROOT / "runs" / "idea_to_spec_repair_session.json",
        clarification_requests_path=ROOT / "runs" / "idea_to_spec_clarification_requests.json",
        active_candidate_path=ROOT / "runs" / "active_idea_to_spec_candidate.json",
        intake_path=ROOT / "runs" / "idea_event_storming_intake.json",
        candidate_graph_path=ROOT / "runs" / "candidate_spec_graph.json",
        promotion_gate_path=ROOT / "runs" / "idea_to_spec_promotion_gate.json",
        clarification_answers_output=ROOT / "runs" / "idea_to_spec_clarification_answers.json",
        ontology_decisions_output=ROOT / "runs" / "product_ontology_gap_review_decisions.json",
        rerun_input_output=ROOT / "runs" / "idea_to_spec_answer_rerun_input.json",
        rerun_preview_output=ROOT / "runs" / "idea_to_spec_rerun_preview.json",
        rerun_materialization_output=ROOT / "runs" / "idea_to_spec_rerun_materialization.json",
        repair_session_output=ROOT / "runs" / "idea_to_spec_repair_session.json",
        operator_ref="operator://local-reviewer",
    )


def test_specspace_repair_drafts_to_rerun_builds_standard_artifacts() -> None:
    report, artifacts = build_rerun_report()

    assert report["artifact_kind"] == "specspace_repair_draft_rerun_report"
    assert report["proposal_id"] == "0173"
    assert report["readiness"]["ready"] is True
    assert report["summary"]["clarification_answer_count"] == 1
    assert report["summary"]["ontology_decision_count"] == 1
    assert report["summary"]["resolved_ontology_gap_count"] == 1
    assert report["summary"]["unresolved_ontology_gap_count"] == 0
    assert report["summary"]["draft_provenance_count"] == 1
    assert report["draft_provenance"][0]["source_draft_id"] == (
        "specspace-repair-draft::team-decision-log::decision-record"
    )
    assert report["gap_count_semantics"]["unresolved_ontology_gap_count"].startswith("Actual")

    answers = artifacts["clarification_answers"]
    assert answers["artifact_kind"] == "idea_to_spec_clarification_answers"
    assert answers["readiness"]["ready"] is True
    assert answers["answers"][0]["request_id"] == REQUEST_ID
    assert answers["answers"][0]["answer_kind"] == "propose_project_local_term"

    decisions = artifacts["ontology_decisions"]
    assert decisions["artifact_kind"] == "product_ontology_gap_review_decisions"
    assert decisions["readiness"]["ready"] is True
    assert decisions["decisions"][0]["term"] == "Decision Record"

    rerun_input = artifacts["rerun_input"]
    assert rerun_input["artifact_kind"] == "idea_to_spec_answer_rerun_input"
    assert rerun_input["summary"]["ontology_decision_source"] == (
        "product_ontology_gap_review_decisions"
    )
    assert rerun_input["summary"]["project_local_term_count"] == 1

    materialization = artifacts["rerun_materialization"]
    assert materialization["artifact_kind"] == "idea_to_spec_rerun_materialization"
    assert materialization["summary"]["removed_gap_count"] == 1

    session = artifacts["repair_session"]
    assert session["artifact_kind"] == "idea_to_spec_repair_session_journal"
    assert session["readiness"]["ready"] is True
    assert session["summary"]["accepted_answer_count"] == 1
    assert session["summary"]["ontology_decision_count"] == 1

    encoded = json.dumps({"report": report, "artifacts": artifacts})
    assert "private note" not in encoded


def test_specspace_repair_drafts_to_rerun_blocks_unready_import_preview() -> None:
    import_preview = build_import_preview()
    import_preview["readiness"]["ready"] = False
    import_preview["readiness"]["review_state"] = "repair_draft_import_preview_review_required"
    import_preview["findings"].append(
        {
            "finding_id": "draft_target_ref_mismatch",
            "severity": "review_required",
            "message": "broken draft",
            "source": "test",
            "evidence": {},
        }
    )

    report, artifacts = build_rerun_report(import_preview)

    assert report["readiness"]["ready"] is False
    assert "import_preview_not_ready_for_rerun" in report["readiness"]["blocked_by"]
    assert report["summary"]["clarification_answer_count"] == 0
    assert artifacts["clarification_answers"]["readiness"]["ready"] is False
    assert artifacts["ontology_decisions"]["readiness"]["ready"] is False


def test_specspace_repair_drafts_to_rerun_blocks_mismatched_preview_sources() -> None:
    import_preview = build_import_preview()

    report, _ = build_rerun_report(import_preview)
    assert report["readiness"]["ready"] is True

    module = load_module(TOOL_PATH, "specspace_repair_drafts_to_rerun_mismatch_test")
    mismatched_report, _ = module.build_specspace_repair_drafts_to_rerun_artifacts(
        import_preview=import_preview,
        repair_session=valid_repair_session(),
        clarification_requests=valid_clarification_requests(),
        active_candidate=active_candidate(),
        intake=valid_intake(),
        candidate_graph=valid_candidate_graph(),
        promotion_gate=promotion_gate(),
        import_preview_path=ROOT / "runs" / "specspace_repair_draft_import_preview.json",
        repair_session_path=ROOT / "runs" / "stale_repair_session.json",
        clarification_requests_path=ROOT / "runs" / "idea_to_spec_clarification_requests.json",
        active_candidate_path=ROOT / "runs" / "active_idea_to_spec_candidate.json",
        intake_path=ROOT / "runs" / "idea_event_storming_intake.json",
        candidate_graph_path=ROOT / "runs" / "candidate_spec_graph.json",
        promotion_gate_path=ROOT / "runs" / "idea_to_spec_promotion_gate.json",
        clarification_answers_output=ROOT / "runs" / "idea_to_spec_clarification_answers.json",
        ontology_decisions_output=ROOT / "runs" / "product_ontology_gap_review_decisions.json",
        rerun_input_output=ROOT / "runs" / "idea_to_spec_answer_rerun_input.json",
        rerun_preview_output=ROOT / "runs" / "idea_to_spec_rerun_preview.json",
        rerun_materialization_output=ROOT / "runs" / "idea_to_spec_rerun_materialization.json",
        repair_session_output=ROOT / "runs" / "idea_to_spec_repair_session.json",
        operator_ref="operator://local-reviewer",
    )

    assert mismatched_report["readiness"]["ready"] is False
    assert (
        "import_preview_idea_to_spec_repair_session_source_ref_mismatch"
        in (mismatched_report["readiness"]["blocked_by"])
    )


def test_specspace_repair_drafts_to_rerun_keeps_defer_non_resolving() -> None:
    preview_module = load_module(
        IMPORT_PREVIEW_TOOL_PATH,
        "specspace_repair_draft_import_preview_defer_for_0173_test",
    )
    draft_state = valid_draft_state()
    draft_state["drafts"][0]["allowed_action"] = "defer"
    draft_state["drafts"][0]["answer_value"] = {"reason": "needs owner decision"}
    import_preview = preview_module.build_specspace_repair_draft_import_preview(
        draft_state=draft_state,
        repair_session=valid_repair_session(),
        clarification_requests=valid_clarification_requests(),
        draft_state_path=ROOT / "runs" / "idea_to_spec_repair_drafts.json",
        repair_session_path=ROOT / "runs" / "idea_to_spec_repair_session.json",
        clarification_requests_path=ROOT / "runs" / "idea_to_spec_clarification_requests.json",
    )

    report, artifacts = build_rerun_report(import_preview)

    assert report["readiness"]["ready"] is False
    assert report["summary"]["ontology_decision_count"] == 0
    assert artifacts["clarification_answers"]["answers"][0]["status"] == "deferred"
    assert artifacts["clarification_answers"]["readiness"]["blocked_by"] == [REQUEST_ID]
    assert artifacts["ontology_decisions"]["decisions"] == []


def test_specspace_repair_drafts_to_rerun_cli_writes_custom_outputs(tmp_path: Path) -> None:
    drafts_path = tmp_path / "idea_to_spec_repair_drafts.json"
    import_preview_path = tmp_path / "specspace_repair_draft_import_preview.json"
    repair_session_path = tmp_path / "idea_to_spec_repair_session.input.json"
    requests_path = tmp_path / "idea_to_spec_clarification_requests.json"
    active_candidate_path = tmp_path / "active_idea_to_spec_candidate.json"
    intake_path = tmp_path / "idea_event_storming_intake.json"
    candidate_graph_path = tmp_path / "candidate_spec_graph.json"
    promotion_gate_path = tmp_path / "idea_to_spec_promotion_gate.json"
    clarification_answers_output = tmp_path / "idea_to_spec_clarification_answers.json"
    ontology_decisions_output = tmp_path / "product_ontology_gap_review_decisions.json"
    rerun_input_output = tmp_path / "idea_to_spec_answer_rerun_input.json"
    rerun_preview_output = tmp_path / "idea_to_spec_rerun_preview.json"
    rerun_materialization_output = tmp_path / "idea_to_spec_rerun_materialization.json"
    repair_session_output = tmp_path / "idea_to_spec_repair_session.json"
    report_output = tmp_path / "specspace_repair_draft_rerun_report.json"

    promotion_gate_ref = promotion_gate_path.as_posix()
    draft_state = draft_state_for_repair_session_path(repair_session_path)
    session = repair_session_for_requests_path(requests_path)
    write_json(drafts_path, draft_state)
    write_json(
        import_preview_path,
        build_import_preview_for_paths(
            draft_state_path=drafts_path,
            repair_session_path=repair_session_path,
            requests_path=requests_path,
            draft_state=draft_state,
            repair_session=session,
        ),
    )
    write_json(repair_session_path, session)
    write_json(requests_path, valid_clarification_requests())
    write_json(active_candidate_path, active_candidate(promotion_gate_ref=promotion_gate_ref))
    write_json(intake_path, valid_intake())
    write_json(candidate_graph_path, valid_candidate_graph())
    write_json(promotion_gate_path, promotion_gate())

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--import-preview",
            str(import_preview_path),
            "--repair-session",
            str(repair_session_path),
            "--clarification-requests",
            str(requests_path),
            "--active-candidate",
            str(active_candidate_path),
            "--intake",
            str(intake_path),
            "--candidate-graph",
            str(candidate_graph_path),
            "--promotion-gate",
            str(promotion_gate_path),
            "--clarification-answers-output",
            str(clarification_answers_output),
            "--ontology-decisions-output",
            str(ontology_decisions_output),
            "--rerun-input-output",
            str(rerun_input_output),
            "--rerun-preview-output",
            str(rerun_preview_output),
            "--rerun-materialization-output",
            str(rerun_materialization_output),
            "--repair-session-output",
            str(repair_session_output),
            "--report-output",
            str(report_output),
            "--strict",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    for path in (
        clarification_answers_output,
        ontology_decisions_output,
        rerun_input_output,
        rerun_preview_output,
        rerun_materialization_output,
        repair_session_output,
        report_output,
    ):
        assert path.is_file(), path
    report = load_json(report_output)
    assert report["readiness"]["ready"] is True
    assert report["draft_provenance"][0]["source_draft_id"] == (
        "specspace-repair-draft::team-decision-log::decision-record"
    )
    answers = load_json(clarification_answers_output)
    assert answers["source_artifacts"]["answer_set"]["source_ref"] == "inline:answer_set"
    session = load_json(repair_session_output)
    assert session["readiness"]["ready"] is True
    for key, path in (
        ("clarification_answers", clarification_answers_output),
        ("ontology_decisions", ontology_decisions_output),
        ("rerun_input", rerun_input_output),
        ("rerun_preview", rerun_preview_output),
        ("rerun_materialization", rerun_materialization_output),
    ):
        assert session["source_artifacts"][key]["sha256"] == sha256(path)


def test_specspace_repair_drafts_to_rerun_cli_skips_artifact_writes_when_unready(
    tmp_path: Path,
) -> None:
    drafts_path = tmp_path / "idea_to_spec_repair_drafts.json"
    import_preview_path = tmp_path / "specspace_repair_draft_import_preview.json"
    repair_session_path = tmp_path / "idea_to_spec_repair_session.input.json"
    requests_path = tmp_path / "idea_to_spec_clarification_requests.json"
    active_candidate_path = tmp_path / "active_idea_to_spec_candidate.json"
    intake_path = tmp_path / "idea_event_storming_intake.json"
    candidate_graph_path = tmp_path / "candidate_spec_graph.json"
    promotion_gate_path = tmp_path / "idea_to_spec_promotion_gate.json"
    outputs = {
        "clarification_answers": tmp_path / "idea_to_spec_clarification_answers.json",
        "ontology_decisions": tmp_path / "product_ontology_gap_review_decisions.json",
        "rerun_input": tmp_path / "idea_to_spec_answer_rerun_input.json",
        "rerun_preview": tmp_path / "idea_to_spec_rerun_preview.json",
        "rerun_materialization": tmp_path / "idea_to_spec_rerun_materialization.json",
        "repair_session": tmp_path / "idea_to_spec_repair_session.json",
    }
    report_output = tmp_path / "specspace_repair_draft_rerun_report.json"

    draft_state = draft_state_for_repair_session_path(repair_session_path)
    session = repair_session_for_requests_path(requests_path)
    import_preview = build_import_preview_for_paths(
        draft_state_path=drafts_path,
        repair_session_path=repair_session_path,
        requests_path=requests_path,
        draft_state=draft_state,
        repair_session=session,
    )
    import_preview["readiness"]["ready"] = False
    import_preview["readiness"]["review_state"] = "repair_draft_import_preview_review_required"
    import_preview["findings"].append(
        {
            "finding_id": "draft_target_ref_mismatch",
            "severity": "review_required",
            "message": "broken draft",
            "source": "test",
            "evidence": {},
        }
    )

    write_json(drafts_path, draft_state)
    write_json(import_preview_path, import_preview)
    write_json(repair_session_path, session)
    write_json(requests_path, valid_clarification_requests())
    write_json(
        active_candidate_path,
        active_candidate(promotion_gate_ref=promotion_gate_path.as_posix()),
    )
    write_json(intake_path, valid_intake())
    write_json(candidate_graph_path, valid_candidate_graph())
    write_json(promotion_gate_path, promotion_gate())
    sentinel = {"sentinel": True}
    for path in outputs.values():
        write_json(path, sentinel)

    base_args = [
        sys.executable,
        str(TOOL_PATH),
        "--import-preview",
        str(import_preview_path),
        "--repair-session",
        str(repair_session_path),
        "--clarification-requests",
        str(requests_path),
        "--active-candidate",
        str(active_candidate_path),
        "--intake",
        str(intake_path),
        "--candidate-graph",
        str(candidate_graph_path),
        "--promotion-gate",
        str(promotion_gate_path),
        "--clarification-answers-output",
        str(outputs["clarification_answers"]),
        "--ontology-decisions-output",
        str(outputs["ontology_decisions"]),
        "--rerun-input-output",
        str(outputs["rerun_input"]),
        "--rerun-preview-output",
        str(outputs["rerun_preview"]),
        "--rerun-materialization-output",
        str(outputs["rerun_materialization"]),
        "--repair-session-output",
        str(outputs["repair_session"]),
        "--report-output",
        str(report_output),
    ]

    result = subprocess.run(
        base_args,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert load_json(report_output)["readiness"]["ready"] is False
    for path in outputs.values():
        assert load_json(path) == sentinel

    strict_result = subprocess.run(
        [*base_args, "--strict"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert strict_result.returncode == 1
    for path in outputs.values():
        assert load_json(path) == sentinel


def test_specspace_repair_drafts_to_rerun_make_target_threads_paths(tmp_path: Path) -> None:
    drafts_path = tmp_path / "idea_to_spec_repair_drafts.json"
    import_preview_path = tmp_path / "specspace_repair_draft_import_preview.json"
    repair_session_path = tmp_path / "idea_to_spec_repair_session.input.json"
    requests_path = tmp_path / "idea_to_spec_clarification_requests.json"
    active_candidate_path = tmp_path / "active_idea_to_spec_candidate.json"
    intake_path = tmp_path / "idea_event_storming_intake.json"
    candidate_graph_path = tmp_path / "candidate_spec_graph.json"
    promotion_gate_path = tmp_path / "idea_to_spec_promotion_gate.json"
    clarification_answers_output = tmp_path / "idea_to_spec_clarification_answers.json"
    ontology_decisions_output = tmp_path / "product_ontology_gap_review_decisions.json"
    rerun_input_output = tmp_path / "idea_to_spec_answer_rerun_input.json"
    rerun_preview_output = tmp_path / "idea_to_spec_rerun_preview.json"
    rerun_materialization_output = tmp_path / "idea_to_spec_rerun_materialization.json"
    repair_session_output = tmp_path / "idea_to_spec_repair_session.json"
    report_output = tmp_path / "specspace_repair_draft_rerun_report.json"

    draft_state = draft_state_for_repair_session_path(repair_session_path)
    session = repair_session_for_requests_path(requests_path)

    write_json(drafts_path, draft_state)
    write_json(repair_session_path, session)
    write_json(requests_path, valid_clarification_requests())
    write_json(
        active_candidate_path,
        active_candidate(promotion_gate_ref=promotion_gate_path.as_posix()),
    )
    write_json(intake_path, valid_intake())
    write_json(candidate_graph_path, valid_candidate_graph())
    write_json(promotion_gate_path, promotion_gate())

    result = subprocess.run(
        [
            "make",
            "product-workspace-repair-draft-rerun",
            f"PYTHON={sys.executable}",
            f"SPECSPACE_REPAIR_DRAFT_IMPORT_DRAFTS={drafts_path}",
            f"SPECSPACE_REPAIR_DRAFT_IMPORT_REPAIR_SESSION={repair_session_path}",
            f"SPECSPACE_REPAIR_DRAFT_IMPORT_CLARIFICATION_REQUESTS={requests_path}",
            f"SPECSPACE_REPAIR_DRAFT_RERUN_IMPORT_PREVIEW={import_preview_path}",
            f"SPECSPACE_REPAIR_DRAFT_RERUN_REPAIR_SESSION={repair_session_path}",
            f"SPECSPACE_REPAIR_DRAFT_RERUN_CLARIFICATION_REQUESTS={requests_path}",
            f"SPECSPACE_REPAIR_DRAFT_RERUN_ACTIVE_CANDIDATE={active_candidate_path}",
            f"SPECSPACE_REPAIR_DRAFT_RERUN_INTAKE={intake_path}",
            f"SPECSPACE_REPAIR_DRAFT_RERUN_CANDIDATE_GRAPH={candidate_graph_path}",
            f"SPECSPACE_REPAIR_DRAFT_RERUN_PROMOTION_GATE={promotion_gate_path}",
            f"IDEA_TO_SPEC_CLARIFICATION_ANSWERS_OUTPUT={clarification_answers_output}",
            f"PRODUCT_ONTOLOGY_GAP_REVIEW_DECISIONS_OUTPUT={ontology_decisions_output}",
            f"IDEA_TO_SPEC_ANSWER_RERUN_INPUT_OUTPUT={rerun_input_output}",
            f"IDEA_TO_SPEC_RERUN_PREVIEW_OUTPUT={rerun_preview_output}",
            f"IDEA_TO_SPEC_RERUN_MATERIALIZATION_OUTPUT={rerun_materialization_output}",
            f"IDEA_TO_SPEC_REPAIR_SESSION_OUTPUT={repair_session_output}",
            f"SPECSPACE_REPAIR_DRAFT_RERUN_REPORT_OUTPUT={report_output}",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    report = load_json(report_output)
    assert report["readiness"]["ready"] is True
    assert report["written_artifacts"]["repair_session"] == repair_session_output.as_posix()
    assert load_json(import_preview_path)["readiness"]["ready"] is True
    assert load_json(rerun_materialization_output)["summary"]["removed_gap_count"] == 1
