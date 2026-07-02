"""Materialize product workspace repair packs into SpecSpace-owned state."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_ID = "0182"
SCHEMA_VERSION = 1
PACK_KIND = "product_workspace_repair_pack"
PACK_CONTRACT_REF = "specgraph.idea-to-spec.product-workspace-repair-pack.v0.1"
DRAFT_STATE_KIND = "specspace_idea_to_spec_repair_draft_state"
RERUN_REQUEST_STATE_KIND = "specspace_idea_to_spec_repair_rerun_request_state"
PROJECT_LOCAL_DECISION_STATE_KIND = "specspace_project_local_ontology_review_decision_state"
PROJECT_LOCAL_LANE_KIND = "project_local_ontology_review_lane"

DEFAULT_PACK_PATH = (
    ROOT
    / "tests"
    / "fixtures"
    / "product_workspace_repair_packs"
    / "team_decision_log_happy_path_repair_pack.json"
)
DEFAULT_REPAIR_SESSION_PATH = ROOT / "runs" / "idea_to_spec_repair_session.json"
DEFAULT_CLARIFICATION_REQUESTS_PATH = ROOT / "runs" / "idea_to_spec_clarification_requests.json"
DEFAULT_DRAFTS_OUTPUT = ROOT / "runs" / "idea_to_spec_repair_drafts.json"
DEFAULT_REQUESTS_OUTPUT = ROOT / "runs" / "idea_to_spec_repair_rerun_requests.json"
DEFAULT_IMPORT_PREVIEW_REF = "runs/specspace_repair_draft_import_preview.json"
DEFAULT_RERUN_REPORT_REF = "runs/specspace_repair_draft_rerun_report.json"
DEFAULT_PROJECT_LOCAL_ONTOLOGY_LANE = ROOT / "runs" / "project_local_ontology_review_lane.json"
DEFAULT_PROJECT_LOCAL_ONTOLOGY_DECISIONS_OUTPUT = (
    ROOT / "runs" / "project_local_ontology_review_decisions.json"
)


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any, default: str = "") -> str:
    return value.strip() if isinstance(value, str) and value.strip() else default


def _relative_ref(path: Path | None) -> str:
    if path is None:
        return "inline:unknown"
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _false_boundary() -> dict[str, bool]:
    return {
        "may_execute_prompt_agent": False,
        "may_apply_to_specgraph": False,
        "may_apply_answers": False,
        "may_apply_decisions": False,
        "may_apply_drafts_to_source_artifacts": False,
        "may_apply_answers_to_source_artifacts": False,
        "may_apply_decisions_to_source_artifacts": False,
        "may_mutate_candidate_source_artifacts": False,
        "may_mutate_canonical_specs": False,
        "may_write_ontology_package": False,
        "may_write_ontology_lockfile": False,
        "may_accept_ontology_terms": False,
        "may_mark_candidate_graph_accepted": False,
        "may_create_branch_or_commit": False,
        "may_open_pull_request": False,
        "may_publish_read_model": False,
    }


def _consumer_boundary() -> dict[str, bool]:
    return {
        "specspace_owned_state": True,
        "for_product_repair_workflow": True,
        **_false_boundary(),
        "may_execute_specgraph": False,
        "may_run_make_target": False,
        "may_execute_git_service_operation": False,
    }


def _draft_authority_fields() -> dict[str, bool]:
    return {
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "applies_to_specgraph": False,
        "applies_to_candidate_artifacts": False,
        "mutates_canonical_specs": False,
        "writes_ontology_package": False,
        "accepts_ontology_terms": False,
        "creates_branch_or_commit": False,
        "opens_pull_request": False,
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
    }


def _request_authority_fields() -> dict[str, bool]:
    return {
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "may_execute_specgraph": False,
        "may_run_make_target": False,
        "may_execute_prompt_agent": False,
        "may_apply_to_specgraph": False,
        "may_apply_answers": False,
        "may_apply_decisions": False,
        "may_apply_drafts_to_source_artifacts": False,
        "may_apply_answers_to_source_artifacts": False,
        "may_apply_decisions_to_source_artifacts": False,
        "may_mutate_candidate_source_artifacts": False,
        "may_mutate_canonical_specs": False,
        "may_write_ontology_package": False,
        "may_write_ontology_lockfile": False,
        "may_accept_ontology_terms": False,
        "may_mark_candidate_graph_accepted": False,
        "may_create_branch_or_commit": False,
        "may_open_pull_request": False,
        "may_publish_read_model": False,
        "may_execute_git_service_operation": False,
    }


def _project_local_decision_authority_fields() -> dict[str, bool]:
    return {
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "applies_to_specgraph": False,
        "applies_to_candidate_artifacts": False,
        "mutates_canonical_specs": False,
        "writes_ontology_package": False,
        "updates_ontology_lockfile": False,
        "accepts_ontology_terms": False,
        "creates_branch_or_commit": False,
        "opens_pull_request": False,
        "may_publish_read_model": False,
        "may_execute_prompt_agent": False,
        "may_execute_specgraph": False,
        "may_execute_platform": False,
        "may_apply_to_specgraph": False,
        "may_apply_decisions": False,
        "may_mutate_candidate_artifacts": False,
        "may_mutate_candidate_source_artifacts": False,
        "may_mutate_canonical_specs": False,
        "may_write_ontology_package": False,
        "may_write_ontology_lockfile": False,
        "may_accept_ontology_terms": False,
        "may_mark_candidate_graph_accepted": False,
        "may_create_branch_or_commit": False,
        "may_open_pull_request": False,
    }


def _request_index(clarification_requests: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw_requests = _list(clarification_requests.get("clarification_requests"))
    return {
        _text(item.get("id")): item
        for item in [_dict(raw) for raw in raw_requests]
        if _text(item.get("id"))
    }


def _pack_record_index(pack: dict[str, Any]) -> list[dict[str, Any]]:
    records = [_dict(item) for item in _list(pack.get("drafts"))]
    if not records:
        records = [_dict(item) for item in _list(pack.get("repair_decisions"))]
    return records


def _accepted_for_rerun_count(drafts: list[dict[str, Any]]) -> int:
    accepted_request_ids: set[str] = set()
    for draft in drafts:
        if _text(draft.get("allowed_action")) == "defer":
            continue
        request_id = _text(draft.get("request_id"))
        if request_id:
            accepted_request_ids.add(request_id)
    return len(accepted_request_ids)


def _validate_pack(pack: dict[str, Any]) -> None:
    if pack.get("artifact_kind") != PACK_KIND:
        raise ValueError(f"repair pack must use artifact_kind {PACK_KIND}")
    if pack.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("repair pack schema_version must be 1")
    if pack.get("contract_ref") not in ("", None, PACK_CONTRACT_REF):
        raise ValueError(f"repair pack contract_ref must be {PACK_CONTRACT_REF}")
    for field in ("canonical_mutations_allowed", "tracked_artifacts_written"):
        if pack.get(field) is not False:
            raise ValueError(f"repair pack {field} must be false")


def _validate_project_local_lane(lane: dict[str, Any]) -> None:
    if lane.get("artifact_kind") != PROJECT_LOCAL_LANE_KIND:
        raise ValueError(
            f"project-local ontology lane must use artifact_kind {PROJECT_LOCAL_LANE_KIND}"
        )
    if lane.get("canonical_mutations_allowed") is not False:
        raise ValueError("project-local ontology lane canonical_mutations_allowed must be false")
    if lane.get("tracked_artifacts_written") is not False:
        raise ValueError("project-local ontology lane tracked_artifacts_written must be false")


def _project_local_review_policy(pack: dict[str, Any]) -> dict[str, Any]:
    policy = _dict(pack.get("project_local_ontology_review"))
    if not policy:
        raise ValueError(
            "repair pack requires project_local_ontology_review for ontology decisions"
        )
    if _text(policy.get("decision_policy")) != "keep_all_required_project_local":
        raise ValueError(
            "project_local_ontology_review.decision_policy must be keep_all_required_project_local"
        )
    return policy


def _required_project_local_terms(lane: dict[str, Any]) -> list[dict[str, Any]]:
    required_statuses = {"unreviewed", "deferred"}
    terms: list[dict[str, Any]] = []
    for raw_term in _list(lane.get("terms")):
        term = _dict(raw_term)
        term_key = _text(term.get("term_key"))
        status = _text(term.get("status"), "unreviewed")
        if term_key and status in required_statuses:
            terms.append(term)
    return terms


def _session_identity(
    *,
    pack: dict[str, Any],
    repair_session: dict[str, Any],
) -> tuple[str, str, str]:
    session = _dict(repair_session.get("session"))
    workspace_id = _text(pack.get("workspace_id")) or _text(session.get("candidate_id"))
    candidate_id = _text(pack.get("candidate_id")) or _text(session.get("candidate_id"))
    session_id = _text(pack.get("repair_session_id")) or _text(session.get("session_id"))
    if not workspace_id or not candidate_id or not session_id:
        raise ValueError("repair pack requires workspace_id, candidate_id, and repair_session_id")
    if _text(session.get("candidate_id")) and candidate_id != _text(session.get("candidate_id")):
        raise ValueError("repair pack candidate_id must match repair session")
    if _text(session.get("session_id")) and session_id != _text(session.get("session_id")):
        raise ValueError("repair pack repair_session_id must match repair session")
    return workspace_id, candidate_id, session_id


def build_product_workspace_repair_pack_states(
    *,
    pack: dict[str, Any],
    repair_session: dict[str, Any],
    clarification_requests: dict[str, Any],
    pack_path: Path | None,
    repair_session_path: Path,
    import_preview_ref: str = DEFAULT_IMPORT_PREVIEW_REF,
    rerun_report_ref: str = DEFAULT_RERUN_REPORT_REF,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _validate_pack(pack)
    workspace_id, candidate_id, session_id = _session_identity(
        pack=pack,
        repair_session=repair_session,
    )
    requests_by_id = _request_index(clarification_requests)
    repair_session_ref = _relative_ref(repair_session_path)
    operator_ref = _text(pack.get("operator_ref"), "operator://product-demo")
    generated_at = _text(pack.get("generated_at"), _now_iso())
    records = _pack_record_index(pack)
    drafts: list[dict[str, Any]] = []
    for index, record in enumerate(records):
        request_id = _text(record.get("request_id"))
        request = requests_by_id.get(request_id)
        if request is None:
            raise ValueError(f"repair pack request_id not found: {request_id}")
        allowed_action = _text(record.get("allowed_action"))
        drafts.append(
            {
                "draft_id": _text(
                    record.get("draft_id"),
                    f"specspace-repair-draft::{workspace_id}::{request_id}",
                ),
                "workspace_id": workspace_id,
                "candidate_id": candidate_id,
                "repair_session_id": session_id,
                "repair_session_ref": repair_session_ref,
                "request_id": request_id,
                "request_kind": request.get("kind"),
                "request_status": request.get("status"),
                "target_ref": request.get("target_ref"),
                "target_artifact": request.get("target_artifact"),
                "allowed_action": allowed_action,
                "answer_value": record.get("answer_value"),
                "operator_ref": _text(record.get("operator_ref"), operator_ref),
                "created_at": _text(record.get("created_at"), generated_at),
                "updated_at": _text(record.get("updated_at"), generated_at),
                "source_artifact": repair_session_ref,
                "source_repair_pack_ref": _relative_ref(pack_path),
                "repair_pack_record_index": index,
                **_draft_authority_fields(),
            }
        )

    draft_state = {
        "artifact_kind": DRAFT_STATE_KIND,
        "schema_version": SCHEMA_VERSION,
        "state_owner": "SpecSpace",
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "source_artifacts": {
            "idea_to_spec_repair_session": repair_session_ref,
            "product_workspace_repair_pack": _relative_ref(pack_path),
        },
        "consumer_boundary": _consumer_boundary(),
        "authority_boundary": {
            "repair_draft_state_is_authority": False,
            "specgraph_artifact_authority": False,
            "ontology_authority": False,
            "git_service_authority": False,
            "canonical_mutations_allowed": False,
        },
        "drafts": drafts,
        "summary": {
            "status": "repair_drafts_recorded",
            "workspace_id": workspace_id,
            "candidate_id": candidate_id,
            "repair_session_id": session_id,
            "draft_count": len(drafts),
            "source": "product_workspace_repair_pack",
        },
    }

    request_id = _text(
        _dict(pack.get("rerun_request")).get("id"),
        f"repair-rerun-request.{workspace_id}.happy-path",
    )
    requested_by = _text(
        _dict(pack.get("rerun_request")).get("requested_by"),
        operator_ref,
    )
    accepted_for_rerun_count = _accepted_for_rerun_count(drafts)
    request_state = {
        "artifact_kind": RERUN_REQUEST_STATE_KIND,
        "schema_version": SCHEMA_VERSION,
        "state_owner": "SpecSpace",
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "source_artifacts": {
            "idea_to_spec_repair_session": repair_session_ref,
            "specspace_repair_draft_import_preview": import_preview_ref,
            "product_workspace_repair_pack": _relative_ref(pack_path),
        },
        "requests": [
            {
                "id": request_id,
                "status": "requested",
                "requested_action": "prepare_repair_draft_rerun",
                "workspace_id": workspace_id,
                "candidate_id": candidate_id,
                "repair_session_id": session_id,
                "repair_session_ref": repair_session_ref,
                "draft_state_ref": _text(
                    _dict(pack.get("rerun_request")).get("draft_state_ref"),
                    "specspace-state://idea_to_spec_repair_drafts.json",
                ),
                "import_preview_ref": import_preview_ref,
                "rerun_report_ref": rerun_report_ref,
                "requested_by": requested_by,
                "created_at": _text(
                    _dict(pack.get("rerun_request")).get("created_at"), generated_at
                ),
                "updated_at": _text(
                    _dict(pack.get("rerun_request")).get("updated_at"), generated_at
                ),
                "draft_count": len(drafts),
                "accepted_for_rerun_count": accepted_for_rerun_count,
                "operator_command": (
                    "make product-workspace-requested-repair-draft-rerun "
                    f"SPECSPACE_REPAIR_RERUN_REQUEST_WORKSPACE_ID={workspace_id}"
                ),
                **_request_authority_fields(),
            }
        ],
        "summary": {
            "status": "rerun_requested",
            "workspace_id": workspace_id,
            "candidate_id": candidate_id,
            "request_count": 1,
            "active_request_count": 1,
            "accepted_for_rerun_count": accepted_for_rerun_count,
            "workspace_count": 1,
            "source": "product_workspace_repair_pack",
        },
        "consumer_boundary": _consumer_boundary(),
        "authority_boundary": {
            "rerun_request_state_is_authority": False,
            "specgraph_execution_authority": False,
            "specgraph_artifact_authority": False,
            "ontology_authority": False,
            "git_service_authority": False,
            "canonical_mutations_allowed": False,
        },
    }
    return draft_state, request_state


def build_project_local_ontology_review_decision_state(
    *,
    pack: dict[str, Any],
    review_lane: dict[str, Any],
    pack_path: Path | None,
    review_lane_path: Path,
) -> dict[str, Any]:
    _validate_pack(pack)
    _validate_project_local_lane(review_lane)
    policy = _project_local_review_policy(pack)
    context = _dict(review_lane.get("context"))
    workspace_id = _text(pack.get("workspace_id")) or _text(context.get("workspace_id"))
    candidate_id = _text(pack.get("candidate_id")) or _text(context.get("candidate_id"))
    repair_session_id = _text(pack.get("repair_session_id")) or _text(
        context.get("repair_session_id")
    )
    if not workspace_id or not candidate_id or not repair_session_id:
        raise ValueError(
            "project-local ontology decision state requires workspace, candidate, and session"
        )
    if _text(context.get("workspace_id")) and workspace_id != _text(context.get("workspace_id")):
        raise ValueError("repair pack workspace_id must match project-local ontology lane")
    if _text(context.get("candidate_id")) and candidate_id != _text(context.get("candidate_id")):
        raise ValueError("repair pack candidate_id must match project-local ontology lane")
    if _text(context.get("repair_session_id")) and repair_session_id != _text(
        context.get("repair_session_id")
    ):
        raise ValueError("repair pack repair_session_id must match project-local ontology lane")

    operator_ref = _text(policy.get("operator_ref")) or _text(
        pack.get("operator_ref"), "operator://product-demo"
    )
    generated_at = _text(policy.get("generated_at")) or _text(pack.get("generated_at"), _now_iso())
    reason = _text(
        policy.get("reason"),
        "Keep this product term project-local for the demo candidate review.",
    )
    lane_ref = _relative_ref(review_lane_path)
    pack_ref = _relative_ref(pack_path)
    decisions: list[dict[str, Any]] = []
    for term in _required_project_local_terms(review_lane):
        term_text = _text(term.get("term"))
        term_key = _text(term.get("term_key"))
        decisions.append(
            {
                "decision_id": (
                    f"specspace-project-local-ontology-decision::{workspace_id}::{term_key}"
                ),
                "workspace_id": workspace_id,
                "candidate_id": candidate_id,
                "repair_session_id": repair_session_id,
                "project_local_ontology_review_lane_ref": lane_ref,
                "term": term_text,
                "term_key": term_key,
                "review_action": "keep_project_local",
                "decision_value": {
                    "term": term_text,
                    "term_scope": "project_local",
                    "reason": reason,
                },
                "operator_ref": operator_ref,
                "created_at": generated_at,
                "updated_at": generated_at,
                "source_repair_pack_ref": pack_ref,
                **_project_local_decision_authority_fields(),
            }
        )

    return {
        "artifact_kind": PROJECT_LOCAL_DECISION_STATE_KIND,
        "schema_version": SCHEMA_VERSION,
        "state_owner": "SpecSpace",
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "source_artifacts": {
            "project_local_ontology_review_lane": lane_ref,
            "product_workspace_repair_pack": pack_ref,
        },
        "consumer_boundary": {
            "specspace_owned_state": True,
            "for_product_ontology_review": True,
            **_false_boundary(),
            "may_execute_specgraph": False,
            "may_execute_platform": False,
            "may_apply_to_specgraph": False,
            "may_apply_decisions": False,
        },
        "authority_boundary": {
            "project_local_ontology_review_decision_state_is_authority": False,
            "specgraph_artifact_authority": False,
            "ontology_authority": False,
            "git_service_authority": False,
            "canonical_mutations_allowed": False,
            "may_execute_prompt_agent": False,
            "may_execute_specgraph": False,
            "may_execute_platform": False,
            "may_apply_to_specgraph": False,
            "may_apply_decisions": False,
            "may_mutate_candidate_artifacts": False,
            "may_mutate_candidate_source_artifacts": False,
            "may_mutate_canonical_specs": False,
            "may_write_ontology_package": False,
            "may_write_ontology_lockfile": False,
            "may_accept_ontology_terms": False,
            "may_create_branch_or_commit": False,
            "may_open_pull_request": False,
            "may_publish_read_model": False,
        },
        "decisions": decisions,
        "summary": {
            "status": "project_local_ontology_decisions_recorded",
            "workspace_id": workspace_id,
            "candidate_id": candidate_id,
            "repair_session_id": repair_session_id,
            "decision_count": len(decisions),
            "review_action": "keep_project_local",
            "source": "product_workspace_repair_pack",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", type=Path, default=DEFAULT_PACK_PATH)
    parser.add_argument("--repair-session", type=Path, default=DEFAULT_REPAIR_SESSION_PATH)
    parser.add_argument(
        "--clarification-requests",
        type=Path,
        default=DEFAULT_CLARIFICATION_REQUESTS_PATH,
    )
    parser.add_argument("--drafts-output", type=Path, default=DEFAULT_DRAFTS_OUTPUT)
    parser.add_argument("--request-state-output", type=Path, default=DEFAULT_REQUESTS_OUTPUT)
    parser.add_argument("--import-preview-ref", default=DEFAULT_IMPORT_PREVIEW_REF)
    parser.add_argument("--rerun-report-ref", default=DEFAULT_RERUN_REPORT_REF)
    parser.add_argument("--project-local-ontology-review-lane", type=Path)
    parser.add_argument("--project-local-ontology-decisions-output", type=Path)
    args = parser.parse_args()

    draft_state, request_state = build_product_workspace_repair_pack_states(
        pack=load_json(args.pack),
        repair_session=load_json(args.repair_session),
        clarification_requests=load_json(args.clarification_requests),
        pack_path=args.pack,
        repair_session_path=args.repair_session,
        import_preview_ref=args.import_preview_ref,
        rerun_report_ref=args.rerun_report_ref,
    )
    write_json(draft_state, args.drafts_output)
    write_json(request_state, args.request_state_output)
    project_local_decision_state = None
    if args.project_local_ontology_review_lane and args.project_local_ontology_decisions_output:
        project_local_decision_state = build_project_local_ontology_review_decision_state(
            pack=load_json(args.pack),
            review_lane=load_json(args.project_local_ontology_review_lane),
            pack_path=args.pack,
            review_lane_path=args.project_local_ontology_review_lane,
        )
        write_json(project_local_decision_state, args.project_local_ontology_decisions_output)
    print(
        "repair_pack_states_written: "
        f"{draft_state['summary']['draft_count']} drafts -> {args.drafts_output}, "
        f"1 rerun request -> {args.request_state_output}"
        + (
            ", "
            f"{project_local_decision_state['summary']['decision_count']} "
            "project-local ontology decisions -> "
            f"{args.project_local_ontology_decisions_output}"
            if project_local_decision_state is not None
            else ""
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
