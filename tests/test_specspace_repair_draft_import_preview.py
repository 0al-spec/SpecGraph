from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "specspace_repair_draft_import_preview.py"
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


def finding_ids(report: dict[str, object]) -> set[str]:
    findings = report["findings"]
    assert isinstance(findings, list)
    return {finding["finding_id"] for finding in findings if isinstance(finding, dict)}


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
                "question": "Should Decision Record bind, alias, remain local, or be rejected?",
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
        "workflow_journal": {
            "stages": [],
            "accepted_answers": [],
            "ontology_decisions": [],
        },
        "readiness_impact": {
            "ready_for_candidate_approval": False,
            "ready_for_platform_promotion": False,
            "unresolved_ontology_gap_count": 2,
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
            "unresolved_ontology_gap_count": 2,
        },
    }


def draft_record(**overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
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
            "raw_operator_note": "private",
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
    record.update(overrides)
    return record


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
        "drafts": [draft_record()],
        "summary": {
            "status": "repair_drafts_recorded",
            "draft_count": 1,
            "workspace_count": 1,
        },
    }


def build_report(
    draft_state: dict[str, object] | None = None,
    repair_session: dict[str, object] | None = None,
    clarification_requests: dict[str, object] | None = None,
) -> dict[str, object]:
    module = load_module(TOOL_PATH, "specspace_repair_draft_import_preview_under_test")
    return module.build_specspace_repair_draft_import_preview(
        draft_state=draft_state or valid_draft_state(),
        repair_session=repair_session or valid_repair_session(),
        clarification_requests=clarification_requests or valid_clarification_requests(),
        draft_state_path=ROOT / "runs" / "idea_to_spec_repair_drafts.json",
        repair_session_path=ROOT / "runs" / "idea_to_spec_repair_session.json",
        clarification_requests_path=ROOT / "runs" / "idea_to_spec_clarification_requests.json",
    )


def test_specspace_repair_draft_import_preview_builds_review_only_candidates() -> None:
    report = build_report()

    assert report["artifact_kind"] == "specspace_repair_draft_import_preview"
    assert report["proposal_id"] == "0172"
    assert (
        report["contract_ref"]
        == "specgraph.idea-to-spec.specspace-repair-draft-import-preview.v0.1"
    )
    assert report["readiness"]["ready"] is True
    assert report["canonical_mutations_allowed"] is False
    assert report["tracked_artifacts_written"] is False
    assert report["session"]["candidate_id"] == "team-decision-log"
    assert report["summary"]["accepted_for_rerun_count"] == 1
    assert report["summary"]["ontology_decision_candidate_count"] == 1
    assert report["summary"]["clarification_answer_candidate_count"] == 1
    assert report["summary"]["would_resolve_blocking_request_count"] == 1
    assert report["summary"]["would_leave_unresolved_gap_count"] == 1
    assert report["authority_boundary"]["may_import_into_specgraph"] is False
    assert report["authority_boundary"]["may_write_ontology_package"] is False
    answer = report["import_preview"]["clarification_answer_candidates"][0]
    assert answer["request_id"] == REQUEST_ID
    assert answer["status"] == "accepted_for_candidate"
    assert "raw_operator_note" not in json.dumps(answer)
    decision = report["import_preview"]["ontology_decision_candidates"][0]
    assert decision["decision_type"] == "propose_project_local_term"
    assert decision["term"] == "Decision Record"
    assert decision["writes_ontology_package"] is False
    assert decision["accepts_ontology_term"] is False


def test_specspace_repair_draft_import_preview_blocks_stale_draft_session_ref() -> None:
    draft_state = valid_draft_state()
    draft_state["drafts"][0]["repair_session_ref"] = "runs/stale_repair_session.json"

    report = build_report(draft_state=draft_state)

    assert report["readiness"]["ready"] is False
    assert report["summary"]["invalid_draft_count"] == 1
    assert "draft_repair_session_ref_mismatch" in finding_ids(report)


def test_specspace_repair_draft_import_preview_rejects_authority_expansion() -> None:
    draft_state = valid_draft_state()
    draft_state["consumer_boundary"]["may_apply_to_specgraph"] = True
    draft_state["drafts"][0]["applies_to_specgraph"] = True

    report = build_report(draft_state=draft_state)

    assert report["readiness"]["ready"] is False
    assert report["summary"]["invalid_draft_count"] == 1
    ids = finding_ids(report)
    assert "repair_draft_consumer_boundary_authority_expanded" in ids
    assert "draft_authority_expanded" in ids


def test_specspace_repair_draft_import_preview_rejects_input_authority_expansion() -> None:
    repair_session = valid_repair_session()
    repair_session["authority_boundary"]["may_create_branch_or_commit"] = True
    clarification_requests = valid_clarification_requests()
    clarification_requests["tracked_artifacts_written"] = True

    report = build_report(
        repair_session=repair_session,
        clarification_requests=clarification_requests,
    )

    assert report["readiness"]["ready"] is False
    ids = finding_ids(report)
    assert "repair_session_authority_boundary_expanded" in ids
    assert "clarification_requests_authority_expanded" in ids


def test_specspace_repair_draft_import_preview_resolves_duplicates_deterministically() -> None:
    older = draft_record(
        draft_id="specspace-repair-draft::team-decision-log::old",
        allowed_action="defer",
        answer_value={"reason": "needs owner"},
        updated_at="2026-06-25T09:00:00Z",
    )
    newer = draft_record(
        draft_id="specspace-repair-draft::team-decision-log::new",
        allowed_action="propose_project_local_term",
        answer_value={"terms": ["Decision Record"], "term_scope": "project_local"},
        updated_at="2026-06-25T09:10:00Z",
    )
    draft_state = valid_draft_state()
    draft_state["drafts"] = [newer, older]

    report = build_report(draft_state=draft_state)

    assert report["readiness"]["ready"] is True
    assert report["summary"]["accepted_for_rerun_count"] == 1
    assert report["summary"]["deferred_count"] == 0
    assert report["summary"]["superseded_draft_count"] == 1
    assert report["warnings"][0]["warning_id"] == "duplicate_repair_draft_resolved"
    assert report["import_preview"]["superseded_drafts"][0]["superseded_by"].endswith("::new")


def test_specspace_repair_draft_import_preview_keeps_defer_non_resolving() -> None:
    draft_state = valid_draft_state()
    draft_state["drafts"][0]["allowed_action"] = "defer"
    draft_state["drafts"][0]["answer_value"] = {"reason": "needs owner decision"}

    report = build_report(draft_state=draft_state)

    assert report["readiness"]["ready"] is True
    assert report["summary"]["accepted_for_rerun_count"] == 0
    assert report["summary"]["deferred_count"] == 1
    assert report["summary"]["ontology_decision_candidate_count"] == 0
    assert report["summary"]["would_resolve_blocking_request_count"] == 0
    assert report["summary"]["would_leave_unresolved_gap_count"] == 2
    answer = report["import_preview"]["clarification_answer_candidates"][0]
    assert answer["status"] == "deferred"


def test_specspace_repair_draft_import_preview_cli_writes_output(tmp_path: Path) -> None:
    drafts_path = tmp_path / "idea_to_spec_repair_drafts.json"
    session_path = tmp_path / "idea_to_spec_repair_session.json"
    requests_path = tmp_path / "idea_to_spec_clarification_requests.json"
    output_path = tmp_path / "specspace_repair_draft_import_preview.json"
    draft_state = valid_draft_state()
    draft_state["source_artifacts"]["idea_to_spec_repair_session"] = session_path.as_posix()
    draft_state["drafts"][0]["repair_session_ref"] = session_path.as_posix()
    draft_state["drafts"][0]["source_artifact"] = session_path.as_posix()
    repair_session = valid_repair_session()
    repair_session["source_artifacts"]["clarification_requests"]["source_ref"] = (
        requests_path.as_posix()
    )
    write_json(drafts_path, draft_state)
    write_json(session_path, repair_session)
    write_json(requests_path, valid_clarification_requests())

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--drafts",
            str(drafts_path),
            "--repair-session",
            str(session_path),
            "--clarification-requests",
            str(requests_path),
            "--output",
            str(output_path),
            "--strict",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    report = load_json(output_path)
    assert report["artifact_kind"] == "specspace_repair_draft_import_preview"
    assert report["summary"]["accepted_for_rerun_count"] == 1


def test_specspace_repair_draft_import_preview_make_target_threads_paths(
    tmp_path: Path,
) -> None:
    drafts_path = tmp_path / "idea_to_spec_repair_drafts.json"
    session_path = tmp_path / "idea_to_spec_repair_session.json"
    requests_path = tmp_path / "idea_to_spec_clarification_requests.json"
    output_path = tmp_path / "specspace_repair_draft_import_preview.json"
    draft_state = valid_draft_state()
    draft_state["source_artifacts"]["idea_to_spec_repair_session"] = session_path.as_posix()
    draft_state["drafts"][0]["repair_session_ref"] = session_path.as_posix()
    draft_state["drafts"][0]["source_artifact"] = session_path.as_posix()
    repair_session = valid_repair_session()
    repair_session["source_artifacts"]["clarification_requests"]["source_ref"] = (
        requests_path.as_posix()
    )
    write_json(drafts_path, draft_state)
    write_json(session_path, repair_session)
    write_json(requests_path, valid_clarification_requests())

    result = subprocess.run(
        [
            "make",
            "specspace-repair-draft-import-preview",
            f"PYTHON={sys.executable}",
            f"SPECSPACE_REPAIR_DRAFT_IMPORT_DRAFTS={drafts_path}",
            f"SPECSPACE_REPAIR_DRAFT_IMPORT_REPAIR_SESSION={session_path}",
            f"SPECSPACE_REPAIR_DRAFT_IMPORT_CLARIFICATION_REQUESTS={requests_path}",
            f"SPECSPACE_REPAIR_DRAFT_IMPORT_OUTPUT={output_path}",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    report = load_json(output_path)
    assert report["artifact_kind"] == "specspace_repair_draft_import_preview"
    assert (
        report["source_artifacts"]["specspace_repair_drafts"]["source_ref"]
        == drafts_path.as_posix()
    )
