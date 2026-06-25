"""Preview SpecSpace-owned repair draft import without applying mutations."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_ID = "0172"
SCHEMA_VERSION = 1
CONTRACT_REF = "specgraph.idea-to-spec.specspace-repair-draft-import-preview.v0.1"
REPAIR_DRAFT_STATE_KIND = "specspace_idea_to_spec_repair_draft_state"
REPAIR_SESSION_KIND = "idea_to_spec_repair_session_journal"
REPAIR_SESSION_CONTRACT_REF = "specgraph.idea-to-spec.repair-session-journal.v0.1"
CLARIFICATION_REQUESTS_KIND = "idea_to_spec_clarification_requests"
CLARIFICATION_REQUESTS_CONTRACT_REF = "specgraph.idea-to-spec.clarification-requests.v0.1"

DEFAULT_DRAFTS_PATH = ROOT / "runs" / "idea_to_spec_repair_drafts.json"
DEFAULT_REPAIR_SESSION_PATH = ROOT / "runs" / "idea_to_spec_repair_session.json"
DEFAULT_CLARIFICATION_REQUESTS_PATH = ROOT / "runs" / "idea_to_spec_clarification_requests.json"
DEFAULT_OUTPUT_PATH = ROOT / "runs" / "specspace_repair_draft_import_preview.json"

TOP_LEVEL_FALSE_FIELDS = (
    "canonical_mutations_allowed",
    "tracked_artifacts_written",
)
CONSUMER_FALSE_FIELDS = (
    "may_execute_prompt_agent",
    "may_apply_to_specgraph",
    "may_apply_answers",
    "may_apply_decisions",
    "may_mutate_candidate_source_artifacts",
    "may_mutate_canonical_specs",
    "may_write_ontology_package",
    "may_accept_ontology_terms",
    "may_create_branch_or_commit",
    "may_open_pull_request",
)
AUTHORITY_FALSE_FIELDS = (
    "repair_draft_state_is_authority",
    "specgraph_artifact_authority",
    "ontology_authority",
    "git_service_authority",
    "canonical_mutations_allowed",
)
REPAIR_SESSION_AUTHORITY_FALSE_FIELDS = (
    "may_execute_prompt_agent",
    "may_apply_answers_to_source_artifacts",
    "may_apply_decisions_to_source_artifacts",
    "may_mutate_candidate_source_artifacts",
    "may_mutate_canonical_specs",
    "may_write_ontology_package",
    "may_accept_ontology_terms",
    "may_create_branch_or_commit",
)
CLARIFICATION_AUTHORITY_FALSE_FIELDS = (
    "may_execute_prompt_agent",
    "may_apply_answers_to_source_artifacts",
    "may_mutate_candidate_source_artifacts",
    "may_mutate_canonical_specs",
    "may_write_ontology_package",
    "may_accept_ontology_terms",
    "may_create_branch_or_commit",
)
DRAFT_FALSE_FIELDS = (
    "canonical_mutations_allowed",
    "tracked_artifacts_written",
    "applies_to_specgraph",
    "applies_to_candidate_artifacts",
    "mutates_canonical_specs",
    "writes_ontology_package",
    "accepts_ontology_terms",
    "creates_branch_or_commit",
    "opens_pull_request",
)
RAW_TRACE_FIELDS = {
    "operator_note",
    "operator_notes",
    "private_note",
    "raw_intent",
    "raw_intent_text",
    "raw_model_output",
    "raw_operator_note",
    "raw_prompt",
    "raw_response",
    "raw_text",
}
ONTOLOGY_ACTION_TO_DECISION = {
    "bind_existing_term": "bind_existing_term",
    "alias": "alias_existing_term",
    "propose_project_local_term": "propose_project_local_term",
    "reject": "reject_non_domain_term",
    "defer": "defer_requires_owner",
}


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any, default: str = "") -> str:
    return value.strip() if isinstance(value, str) and value.strip() else default


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _slug(value: str, fallback: str = "draft") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or fallback


def _relative_ref(path: Path | None) -> str:
    if path is None:
        return "inline:unknown"
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _public_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: _public_safe(item)
            for key, item in value.items()
            if isinstance(key, str) and key not in RAW_TRACE_FIELDS and not key.startswith("raw_")
        }
    if isinstance(value, list):
        return [_public_safe(item) for item in value]
    return value


def _sha256(path: Path | None) -> str | None:
    if path is None or not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _finding(
    *,
    finding_id: str,
    severity: str,
    message: str,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "finding_id": finding_id,
        "severity": severity,
        "message": message,
        "source": "specspace_repair_draft_import_preview",
        "evidence": evidence or {},
    }


def _warning(
    *,
    warning_id: str,
    message: str,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "warning_id": warning_id,
        "severity": "warning",
        "message": message,
        "source": "specspace_repair_draft_import_preview",
        "evidence": evidence or {},
    }


def _authority_boundary() -> dict[str, bool]:
    return {
        "may_execute_prompt_agent": False,
        "may_import_into_specgraph": False,
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


def _first_true(value: Any, fields: tuple[str, ...]) -> str | None:
    if not isinstance(value, dict):
        return None
    return next((field for field in fields if value.get(field) is True), None)


def _validate_root_artifacts(
    *,
    draft_state: dict[str, Any],
    repair_session: dict[str, Any],
    clarification_requests: dict[str, Any],
    repair_session_path: Path | None,
    clarification_requests_path: Path | None,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if draft_state.get("artifact_kind") != REPAIR_DRAFT_STATE_KIND:
        findings.append(
            _finding(
                finding_id="repair_draft_state_wrong_artifact_kind",
                severity="review_required",
                message=f"SpecSpace draft state must use artifact_kind {REPAIR_DRAFT_STATE_KIND}.",
                evidence={"artifact_kind": draft_state.get("artifact_kind")},
            )
        )
    if draft_state.get("schema_version") != SCHEMA_VERSION:
        findings.append(
            _finding(
                finding_id="repair_draft_state_schema_version_unsupported",
                severity="review_required",
                message="SpecSpace draft state schema_version must be 1.",
                evidence={"schema_version": draft_state.get("schema_version")},
            )
        )
    if draft_state.get("state_owner") != "SpecSpace":
        findings.append(
            _finding(
                finding_id="repair_draft_state_owner_unsupported",
                severity="review_required",
                message="SpecSpace repair draft import requires state_owner: SpecSpace.",
                evidence={"state_owner": draft_state.get("state_owner")},
            )
        )
    for field in TOP_LEVEL_FALSE_FIELDS:
        if draft_state.get(field) is not False:
            findings.append(
                _finding(
                    finding_id="repair_draft_state_authority_expanded",
                    severity="review_required",
                    message=f"SpecSpace draft state {field} must be false.",
                    evidence={field: draft_state.get(field)},
                )
            )
    consumer_boundary = _dict(draft_state.get("consumer_boundary"))
    for field in ("specspace_owned_state", "for_product_repair_workflow"):
        if consumer_boundary.get(field) is not True:
            findings.append(
                _finding(
                    finding_id=f"repair_draft_consumer_boundary_{field}_missing",
                    severity="review_required",
                    message=f"SpecSpace draft state consumer_boundary.{field} must be true.",
                    evidence={field: consumer_boundary.get(field)},
                )
            )
    for name, value in (
        (
            "repair_draft_consumer_boundary",
            _first_true(consumer_boundary, CONSUMER_FALSE_FIELDS),
        ),
        (
            "repair_draft_authority_boundary",
            _first_true(draft_state.get("authority_boundary"), AUTHORITY_FALSE_FIELDS),
        ),
    ):
        if value:
            findings.append(
                _finding(
                    finding_id=f"{name}_authority_expanded",
                    severity="review_required",
                    message=f"{name} must not claim {value}.",
                    evidence={value: True},
                )
            )

    if repair_session.get("artifact_kind") != REPAIR_SESSION_KIND:
        findings.append(
            _finding(
                finding_id="repair_session_wrong_artifact_kind",
                severity="review_required",
                message=f"Repair session must use artifact_kind {REPAIR_SESSION_KIND}.",
                evidence={"artifact_kind": repair_session.get("artifact_kind")},
            )
        )
    if repair_session.get("contract_ref") != REPAIR_SESSION_CONTRACT_REF:
        findings.append(
            _finding(
                finding_id="repair_session_contract_ref_unsupported",
                severity="review_required",
                message=f"Repair session contract_ref must be {REPAIR_SESSION_CONTRACT_REF}.",
                evidence={"contract_ref": repair_session.get("contract_ref")},
            )
        )
    if repair_session.get("schema_version") != SCHEMA_VERSION:
        findings.append(
            _finding(
                finding_id="repair_session_schema_version_unsupported",
                severity="review_required",
                message="Repair session schema_version must be 1.",
                evidence={"schema_version": repair_session.get("schema_version")},
            )
        )
    if _dict(repair_session.get("readiness")).get("ready") is not True:
        findings.append(
            _finding(
                finding_id="repair_session_not_ready_for_draft_import",
                severity="review_required",
                message="SpecSpace repair draft import requires a ready repair session journal.",
                evidence={"readiness": _dict(repair_session.get("readiness"))},
            )
        )
    for field in ("canonical_mutations_allowed", "tracked_artifacts_written"):
        if repair_session.get(field) is not False:
            findings.append(
                _finding(
                    finding_id="repair_session_authority_expanded",
                    severity="review_required",
                    message=f"Repair session {field} must be false.",
                    evidence={field: repair_session.get(field)},
                )
            )
    repair_session_boundary_expansion = _first_true(
        repair_session.get("authority_boundary"),
        REPAIR_SESSION_AUTHORITY_FALSE_FIELDS,
    )
    if repair_session_boundary_expansion:
        findings.append(
            _finding(
                finding_id="repair_session_authority_boundary_expanded",
                severity="review_required",
                message=f"Repair session must not claim {repair_session_boundary_expansion}.",
                evidence={repair_session_boundary_expansion: True},
            )
        )

    if clarification_requests.get("artifact_kind") != CLARIFICATION_REQUESTS_KIND:
        findings.append(
            _finding(
                finding_id="clarification_requests_wrong_artifact_kind",
                severity="review_required",
                message=(
                    f"Clarification requests must use artifact_kind {CLARIFICATION_REQUESTS_KIND}."
                ),
                evidence={"artifact_kind": clarification_requests.get("artifact_kind")},
            )
        )
    if clarification_requests.get("contract_ref") != CLARIFICATION_REQUESTS_CONTRACT_REF:
        findings.append(
            _finding(
                finding_id="clarification_requests_contract_ref_unsupported",
                severity="review_required",
                message=(
                    "Clarification requests contract_ref must be "
                    f"{CLARIFICATION_REQUESTS_CONTRACT_REF}."
                ),
                evidence={"contract_ref": clarification_requests.get("contract_ref")},
            )
        )
    if clarification_requests.get("schema_version") != SCHEMA_VERSION:
        findings.append(
            _finding(
                finding_id="clarification_requests_schema_version_unsupported",
                severity="review_required",
                message="Clarification requests schema_version must be 1.",
                evidence={"schema_version": clarification_requests.get("schema_version")},
            )
        )
    for field in ("canonical_mutations_allowed", "tracked_artifacts_written"):
        if clarification_requests.get(field) is not False:
            findings.append(
                _finding(
                    finding_id="clarification_requests_authority_expanded",
                    severity="review_required",
                    message=f"Clarification requests {field} must be false.",
                    evidence={field: clarification_requests.get(field)},
                )
            )
    clarification_boundary_expansion = _first_true(
        clarification_requests.get("authority_boundary"),
        CLARIFICATION_AUTHORITY_FALSE_FIELDS,
    )
    if clarification_boundary_expansion:
        findings.append(
            _finding(
                finding_id="clarification_requests_authority_boundary_expanded",
                severity="review_required",
                message=(
                    f"Clarification requests must not claim {clarification_boundary_expansion}."
                ),
                evidence={clarification_boundary_expansion: True},
            )
        )

    draft_session_ref = _text(
        _dict(draft_state.get("source_artifacts")).get("idea_to_spec_repair_session")
    )
    expected_session_ref = _relative_ref(repair_session_path)
    if draft_session_ref and draft_session_ref != expected_session_ref:
        findings.append(
            _finding(
                finding_id="repair_draft_state_repair_session_source_ref_mismatch",
                severity="review_required",
                message="SpecSpace draft state must reference the imported repair session path.",
                evidence={"actual": draft_session_ref, "expected": expected_session_ref},
            )
        )

    session_requests_ref = _text(
        _dict(_dict(repair_session.get("source_artifacts")).get("clarification_requests")).get(
            "source_ref"
        )
    )
    expected_requests_ref = _relative_ref(clarification_requests_path)
    if session_requests_ref and session_requests_ref != expected_requests_ref:
        findings.append(
            _finding(
                finding_id="repair_session_clarification_requests_source_ref_mismatch",
                severity="review_required",
                message="Repair session clarification_requests source_ref must match input path.",
                evidence={"actual": session_requests_ref, "expected": expected_requests_ref},
            )
        )
    return findings


def _request_index(clarification_requests: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for raw_request in _list(clarification_requests.get("clarification_requests")):
        request = _dict(raw_request)
        request_id = _text(request.get("id"))
        if request_id:
            index[request_id] = request
    return index


def _selected_workspace(
    *,
    workspace_id: str | None,
    repair_session: dict[str, Any],
    draft_state: dict[str, Any],
) -> str:
    if workspace_id:
        return workspace_id
    session = _dict(repair_session.get("session"))
    candidate_id = _text(session.get("candidate_id"))
    if candidate_id:
        return candidate_id
    selected = _text(draft_state.get("selected_workspace_id"))
    return selected or "default"


def _draft_sort_key(draft: dict[str, Any]) -> tuple[str, str, str]:
    return (
        _text(draft.get("updated_at")),
        _text(draft.get("created_at")),
        _text(draft.get("draft_id")),
    )


def _candidate_term_from_request(request: dict[str, Any]) -> str:
    target_ref = _text(request.get("target_ref"))
    if "ontology-gap." in target_ref:
        return target_ref.split("ontology-gap.", 1)[1].replace("-", " ").strip()
    request_id = _text(request.get("id"), "term")
    return request_id.rsplit(".", 1)[-1].replace("-", " ").strip() or "term"


def _answer_candidate(
    *,
    draft: dict[str, Any],
    request: dict[str, Any],
    status: str,
) -> dict[str, Any]:
    return _public_safe(
        {
            "request_id": draft.get("request_id"),
            "answer_kind": draft.get("allowed_action"),
            "status": status,
            "authority": "operator_approved",
            "operator_ref": draft.get("operator_ref"),
            "value": draft.get("answer_value"),
            "request_snapshot": {
                "kind": request.get("kind"),
                "severity": request.get("severity"),
                "target_artifact": request.get("target_artifact"),
                "target_ref": request.get("target_ref"),
                "suggested_answer_shape": request.get("suggested_answer_shape"),
            },
            "source_draft_id": draft.get("draft_id"),
        }
    )


def _ontology_decision_candidates(
    *,
    draft: dict[str, Any],
    request: dict[str, Any],
) -> list[dict[str, Any]]:
    action = _text(draft.get("allowed_action"))
    if _text(request.get("kind")) != "ontology_gap" or action not in ONTOLOGY_ACTION_TO_DECISION:
        return []
    value = _dict(draft.get("answer_value"))
    decision_type = ONTOLOGY_ACTION_TO_DECISION[action]
    context = {
        "request_id": draft.get("request_id"),
        "request_kind": request.get("kind"),
        "target_artifact": request.get("target_artifact"),
        "target_ref": request.get("target_ref"),
        "source_answer_kind": action,
        "source_answer_status": "accepted_for_candidate",
        "authority": "operator_approved",
        "source_draft_id": draft.get("draft_id"),
    }
    base_id = f"specspace-draft-ontology-decision.{_slug(_text(draft.get('request_id')))}"
    if action == "propose_project_local_term":
        terms = [
            item.strip()
            for item in _list(value.get("terms"))
            if isinstance(item, str) and item.strip()
        ]
        term = _text(value.get("term"))
        if term and term not in terms:
            terms.append(term)
        return [
            _public_safe(
                {
                    "id": f"{base_id}.{index}",
                    "decision_type": decision_type,
                    "status": "accepted_for_candidate_preview",
                    "materialization_intent": "rerun_overlay_only",
                    "canonical_mutations_allowed": False,
                    "writes_ontology_package": False,
                    "accepts_ontology_term": False,
                    "term": term_value,
                    "term_scope": _text(value.get("term_scope"), "project_local"),
                    "source_value": value,
                    **context,
                }
            )
            for index, term_value in enumerate(terms)
        ]
    if action == "bind_existing_term":
        term = _text(value.get("term"), _candidate_term_from_request(request))
        return [
            _public_safe(
                {
                    "id": f"{base_id}.0",
                    "decision_type": decision_type,
                    "status": "accepted_for_candidate_preview",
                    "materialization_intent": "rerun_overlay_only",
                    "canonical_mutations_allowed": False,
                    "writes_ontology_package": False,
                    "accepts_ontology_term": False,
                    "term": term,
                    "ontology_ref": value.get("ontology_ref"),
                    "source_value": value,
                    **context,
                }
            )
        ]
    if action == "alias":
        term = _text(value.get("term"), _candidate_term_from_request(request))
        return [
            _public_safe(
                {
                    "id": f"{base_id}.0",
                    "decision_type": decision_type,
                    "status": "accepted_for_candidate_preview",
                    "materialization_intent": "rerun_overlay_only",
                    "canonical_mutations_allowed": False,
                    "writes_ontology_package": False,
                    "accepts_ontology_term": False,
                    "term": term,
                    "alias_of": value.get("alias_of"),
                    "source_value": value,
                    **context,
                }
            )
        ]
    return [
        _public_safe(
            {
                "id": f"{base_id}.0",
                "decision_type": decision_type,
                "status": "accepted_for_candidate_preview",
                "materialization_intent": "rerun_overlay_only",
                "canonical_mutations_allowed": False,
                "writes_ontology_package": False,
                "accepts_ontology_term": False,
                "reason": value.get("reason"),
                "source_value": value,
                **context,
            }
        )
    ]


def _draft_record_findings(
    *,
    draft: dict[str, Any],
    request: dict[str, Any] | None,
    selected_workspace_id: str,
    session: dict[str, Any],
    repair_session_path: Path | None,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    request_id = _text(draft.get("request_id"))
    action = _text(draft.get("allowed_action"))
    if not request_id:
        findings.append(
            _finding(
                finding_id="draft_request_id_missing",
                severity="review_required",
                message="SpecSpace repair draft requires request_id.",
                evidence={"draft_id": draft.get("draft_id")},
            )
        )
    if request is None and request_id:
        findings.append(
            _finding(
                finding_id="draft_request_unknown",
                severity="review_required",
                message="SpecSpace repair draft must reference an existing clarification request.",
                evidence={"request_id": request_id, "draft_id": draft.get("draft_id")},
            )
        )
    if not action:
        findings.append(
            _finding(
                finding_id="draft_allowed_action_missing",
                severity="review_required",
                message="SpecSpace repair draft requires allowed_action.",
                evidence={"request_id": request_id, "draft_id": draft.get("draft_id")},
            )
        )
    allowed_actions = [
        item.strip()
        for item in _list(_dict(request or {}).get("suggested_actions"))
        if isinstance(item, str) and item.strip()
    ]
    if request is not None and action and action not in allowed_actions:
        findings.append(
            _finding(
                finding_id="draft_allowed_action_unsupported",
                severity="review_required",
                message="SpecSpace repair draft action must match request.suggested_actions.",
                evidence={
                    "request_id": request_id,
                    "allowed_action": action,
                    "suggested_actions": allowed_actions,
                },
            )
        )
    mutation_field = _first_true(draft, DRAFT_FALSE_FIELDS)
    if mutation_field:
        findings.append(
            _finding(
                finding_id="draft_authority_expanded",
                severity="review_required",
                message=f"SpecSpace repair draft must not claim {mutation_field}.",
                evidence={"request_id": request_id, mutation_field: True},
            )
        )
    if _text(draft.get("workspace_id")) != selected_workspace_id:
        findings.append(
            _finding(
                finding_id="draft_workspace_mismatch",
                severity="review_required",
                message="SpecSpace repair draft workspace_id must match selected workspace.",
                evidence={
                    "request_id": request_id,
                    "actual": draft.get("workspace_id"),
                    "expected": selected_workspace_id,
                },
            )
        )
    candidate_id = _text(session.get("candidate_id"))
    if candidate_id and _text(draft.get("candidate_id")) != candidate_id:
        findings.append(
            _finding(
                finding_id="draft_candidate_mismatch",
                severity="review_required",
                message=(
                    "SpecSpace repair draft candidate_id must match repair session candidate_id."
                ),
                evidence={
                    "request_id": request_id,
                    "actual": draft.get("candidate_id"),
                    "expected": candidate_id,
                },
            )
        )
    expected_session_id = _text(session.get("session_id"))
    if expected_session_id and _text(draft.get("repair_session_id")) != expected_session_id:
        findings.append(
            _finding(
                finding_id="draft_repair_session_id_mismatch",
                severity="review_required",
                message="SpecSpace repair draft repair_session_id must match the journal session.",
                evidence={
                    "request_id": request_id,
                    "actual": draft.get("repair_session_id"),
                    "expected": expected_session_id,
                },
            )
        )
    expected_session_ref = _relative_ref(repair_session_path)
    draft_refs = [
        ("repair_session_ref", _text(draft.get("repair_session_ref"))),
        ("source_artifact", _text(draft.get("source_artifact"))),
    ]
    for field, actual_ref in draft_refs:
        if actual_ref and actual_ref != expected_session_ref:
            findings.append(
                _finding(
                    finding_id=f"draft_{field}_mismatch",
                    severity="review_required",
                    message=f"SpecSpace repair draft {field} must match imported repair session.",
                    evidence={
                        "request_id": request_id,
                        "actual": actual_ref,
                        "expected": expected_session_ref,
                    },
                )
            )
    if request is not None:
        request_target_ref = _text(request.get("target_ref"))
        draft_target_ref = _text(draft.get("target_ref"))
        if draft_target_ref and request_target_ref and draft_target_ref != request_target_ref:
            findings.append(
                _finding(
                    finding_id="draft_target_ref_mismatch",
                    severity="review_required",
                    message="SpecSpace repair draft target_ref must match clarification request.",
                    evidence={
                        "request_id": request_id,
                        "actual": draft_target_ref,
                        "expected": request_target_ref,
                    },
                )
            )
        request_target_artifact = _text(request.get("target_artifact"))
        draft_target_artifact = _text(draft.get("target_artifact"))
        if (
            draft_target_artifact
            and request_target_artifact
            and draft_target_artifact != request_target_artifact
        ):
            findings.append(
                _finding(
                    finding_id="draft_target_artifact_mismatch",
                    severity="review_required",
                    message=(
                        "SpecSpace repair draft target_artifact must match clarification request."
                    ),
                    evidence={
                        "request_id": request_id,
                        "actual": draft_target_artifact,
                        "expected": request_target_artifact,
                    },
                )
            )
    if not _text(draft.get("operator_ref")):
        findings.append(
            _finding(
                finding_id="draft_operator_ref_missing",
                severity="review_required",
                message="SpecSpace repair draft requires operator_ref.",
                evidence={"request_id": request_id, "draft_id": draft.get("draft_id")},
            )
        )
    return findings


def _validate_answer_value(
    *,
    draft: dict[str, Any],
    request: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    action = _text(draft.get("allowed_action"))
    value = _dict(draft.get("answer_value"))
    request_id = _text(draft.get("request_id"))
    findings: list[dict[str, Any]] = []
    if action == "bind_existing_term" and not _text(value.get("ontology_ref")):
        findings.append(
            _finding(
                finding_id="draft_bind_existing_term_value_missing",
                severity="review_required",
                message="bind_existing_term draft requires answer_value.ontology_ref.",
                evidence={"request_id": request_id},
            )
        )
    elif action == "alias" and not _text(value.get("alias_of")):
        findings.append(
            _finding(
                finding_id="draft_alias_value_missing",
                severity="review_required",
                message="alias draft requires answer_value.alias_of.",
                evidence={"request_id": request_id},
            )
        )
    elif action == "propose_project_local_term":
        terms = [
            item.strip()
            for item in _list(value.get("terms"))
            if isinstance(item, str) and item.strip()
        ]
        if not terms and not _text(value.get("term")):
            findings.append(
                _finding(
                    finding_id="draft_project_local_term_value_missing",
                    severity="review_required",
                    message="propose_project_local_term draft requires terms or term.",
                    evidence={"request_id": request_id},
                )
            )
    elif action in {"reject", "defer"} and not _text(value.get("reason")):
        findings.append(
            _finding(
                finding_id=f"draft_{action}_reason_missing",
                severity="review_required",
                message=f"{action} draft requires answer_value.reason.",
                evidence={"request_id": request_id},
            )
        )
    elif request is not None and not value:
        findings.append(
            _finding(
                finding_id="draft_answer_value_missing",
                severity="review_required",
                message="SpecSpace repair draft requires non-empty answer_value.",
                evidence={"request_id": request_id},
            )
        )
    return findings


def _deduplicate_drafts(
    drafts: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for draft in drafts:
        key = (_text(draft.get("workspace_id")), _text(draft.get("request_id")))
        by_key.setdefault(key, []).append(draft)
    selected: list[dict[str, Any]] = []
    superseded: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    for key, group in sorted(by_key.items()):
        ordered = sorted(group, key=_draft_sort_key)
        winner = ordered[-1]
        selected.append(winner)
        for item in ordered[:-1]:
            superseded.append(
                {
                    "workspace_id": item.get("workspace_id"),
                    "request_id": item.get("request_id"),
                    "draft_id": item.get("draft_id"),
                    "superseded_by": winner.get("draft_id"),
                    "updated_at": item.get("updated_at"),
                }
            )
        if len(group) > 1:
            warnings.append(
                _warning(
                    warning_id="duplicate_repair_draft_resolved",
                    message="Duplicate SpecSpace repair drafts were resolved by latest updated_at.",
                    evidence={
                        "workspace_id": key[0],
                        "request_id": key[1],
                        "selected_draft_id": winner.get("draft_id"),
                        "superseded_count": len(group) - 1,
                    },
                )
            )
    return selected, superseded, warnings


def build_specspace_repair_draft_import_preview(
    *,
    draft_state: dict[str, Any],
    repair_session: dict[str, Any],
    clarification_requests: dict[str, Any],
    draft_state_path: Path | None = None,
    repair_session_path: Path | None = None,
    clarification_requests_path: Path | None = None,
    workspace_id: str | None = None,
) -> dict[str, Any]:
    findings = _validate_root_artifacts(
        draft_state=draft_state,
        repair_session=repair_session,
        clarification_requests=clarification_requests,
        repair_session_path=repair_session_path,
        clarification_requests_path=clarification_requests_path,
    )
    request_by_id = _request_index(clarification_requests)
    session = _dict(repair_session.get("session"))
    selected_workspace_id = _selected_workspace(
        workspace_id=workspace_id,
        repair_session=repair_session,
        draft_state=draft_state,
    )
    all_drafts = [_dict(item) for item in _list(draft_state.get("drafts"))]
    workspace_drafts = [
        draft for draft in all_drafts if _text(draft.get("workspace_id")) == selected_workspace_id
    ]
    ignored_workspace_count = len(all_drafts) - len(workspace_drafts)
    selected_drafts, superseded_drafts, duplicate_warnings = _deduplicate_drafts(workspace_drafts)
    warnings = duplicate_warnings

    valid_imports: list[dict[str, Any]] = []
    invalid_drafts: list[dict[str, Any]] = []
    deferred_drafts: list[dict[str, Any]] = []
    answer_candidates: list[dict[str, Any]] = []
    ontology_decision_candidates: list[dict[str, Any]] = []
    would_resolve_blocking_requests: list[str] = []
    for draft in selected_drafts:
        request_id = _text(draft.get("request_id"))
        request = request_by_id.get(request_id)
        draft_findings = _draft_record_findings(
            draft=draft,
            request=request,
            selected_workspace_id=selected_workspace_id,
            session=session,
            repair_session_path=repair_session_path,
        )
        draft_findings.extend(_validate_answer_value(draft=draft, request=request))
        if draft_findings:
            invalid_drafts.append(
                _public_safe(
                    {
                        "draft_id": draft.get("draft_id"),
                        "workspace_id": draft.get("workspace_id"),
                        "request_id": draft.get("request_id"),
                        "finding_ids": [finding["finding_id"] for finding in draft_findings],
                    }
                )
            )
            findings.extend(draft_findings)
            continue
        assert request is not None
        if _text(draft.get("allowed_action")) == "defer":
            deferred_drafts.append(
                _public_safe(
                    {
                        "draft_id": draft.get("draft_id"),
                        "request_id": request_id,
                        "target_ref": draft.get("target_ref") or request.get("target_ref"),
                        "reason": _dict(draft.get("answer_value")).get("reason"),
                    }
                )
            )
            answer_candidates.append(
                _answer_candidate(draft=draft, request=request, status="deferred")
            )
            continue
        answer_candidate = _answer_candidate(
            draft=draft,
            request=request,
            status="accepted_for_candidate",
        )
        decisions = _ontology_decision_candidates(draft=draft, request=request)
        answer_candidates.append(answer_candidate)
        ontology_decision_candidates.extend(decisions)
        valid_imports.append(
            _public_safe(
                {
                    "draft_id": draft.get("draft_id"),
                    "request_id": request_id,
                    "answer_kind": draft.get("allowed_action"),
                    "request_kind": request.get("kind"),
                    "target_artifact": request.get("target_artifact"),
                    "target_ref": request.get("target_ref"),
                    "operator_ref": draft.get("operator_ref"),
                    "answer_candidate_index": len(answer_candidates) - 1,
                    "ontology_decision_candidate_count": len(decisions),
                }
            )
        )
        if _text(request.get("severity")) == "blocking":
            would_resolve_blocking_requests.append(request_id)

    readiness_impact = _dict(repair_session.get("readiness_impact"))
    unresolved_gaps_before = _int(readiness_impact.get("unresolved_ontology_gap_count"), 0)
    resolving_ontology_request_ids = {
        _text(candidate.get("request_id"))
        for candidate in ontology_decision_candidates
        if _text(candidate.get("decision_type")) != "defer_requires_owner"
    }
    would_leave_unresolved_gaps = max(
        unresolved_gaps_before - len({item for item in resolving_ontology_request_ids if item}),
        0,
    )
    ready = not findings
    return {
        "artifact_kind": "specspace_repair_draft_import_preview",
        "schema_version": SCHEMA_VERSION,
        "proposal_id": PROPOSAL_ID,
        "contract_ref": CONTRACT_REF,
        "generated_at": _now_iso(),
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "session": {
            "session_id": session.get("session_id"),
            "candidate_id": session.get("candidate_id"),
            "workspace_id": selected_workspace_id,
            "workflow_lane": session.get("workflow_lane"),
            "governance_profile": session.get("governance_profile"),
            "target_repository_role": session.get("target_repository_role"),
        },
        "source_artifacts": {
            "specspace_repair_drafts": {
                "artifact_kind": draft_state.get("artifact_kind"),
                "schema_version": draft_state.get("schema_version"),
                "source_ref": _relative_ref(draft_state_path),
                "sha256": _sha256(draft_state_path),
                "draft_count": len(all_drafts),
                "selected_workspace_draft_count": len(workspace_drafts),
            },
            "idea_to_spec_repair_session": {
                "artifact_kind": repair_session.get("artifact_kind"),
                "contract_ref": repair_session.get("contract_ref"),
                "source_ref": _relative_ref(repair_session_path),
                "sha256": _sha256(repair_session_path),
                "readiness": _public_safe(_dict(repair_session.get("readiness"))),
            },
            "idea_to_spec_clarification_requests": {
                "artifact_kind": clarification_requests.get("artifact_kind"),
                "contract_ref": clarification_requests.get("contract_ref"),
                "source_ref": _relative_ref(clarification_requests_path),
                "sha256": _sha256(clarification_requests_path),
                "request_count": len(request_by_id),
            },
        },
        "import_preview": {
            "valid_imports": valid_imports,
            "clarification_answer_candidates": answer_candidates,
            "ontology_decision_candidates": ontology_decision_candidates,
            "deferred_drafts": deferred_drafts,
            "invalid_drafts": invalid_drafts,
            "superseded_drafts": superseded_drafts,
            "would_resolve_blocking_requests": sorted(set(would_resolve_blocking_requests)),
            "would_leave_unresolved_gaps": would_leave_unresolved_gaps,
        },
        "readiness": {
            "ready": ready,
            "review_state": (
                "repair_draft_import_preview_ready"
                if ready
                else "repair_draft_import_preview_review_required"
            ),
            "blocked_by": [finding["finding_id"] for finding in findings],
            "next_artifact": (
                "runs/idea_to_spec_clarification_answers.json"
                if ready
                else "repair invalid SpecSpace repair drafts"
            ),
        },
        "authority_boundary": _authority_boundary(),
        "privacy_boundary": {
            "redaction_enforced_by": "recursive_public_safe_field_filter",
            "raw_idea_text_published": False,
            "raw_prompt_published": False,
            "raw_model_output_published": False,
            "raw_operator_note_published": False,
        },
        "findings": findings,
        "warnings": warnings,
        "summary": {
            "status": (
                "repair_draft_import_preview_ready"
                if ready
                else "repair_draft_import_preview_review_required"
            ),
            "workspace_id": selected_workspace_id,
            "candidate_id": session.get("candidate_id"),
            "draft_count": len(all_drafts),
            "selected_workspace_draft_count": len(workspace_drafts),
            "ignored_workspace_draft_count": ignored_workspace_count,
            "accepted_for_rerun_count": len(valid_imports),
            "deferred_count": len(deferred_drafts),
            "invalid_draft_count": len(invalid_drafts),
            "superseded_draft_count": len(superseded_drafts),
            "clarification_answer_candidate_count": len(answer_candidates),
            "ontology_decision_candidate_count": len(ontology_decision_candidates),
            "would_resolve_blocking_request_count": len(set(would_resolve_blocking_requests)),
            "would_leave_unresolved_gap_count": would_leave_unresolved_gaps,
            "finding_count": len(findings),
            "warning_count": len(warnings),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--drafts", default=DEFAULT_DRAFTS_PATH, type=Path)
    parser.add_argument("--repair-session", default=DEFAULT_REPAIR_SESSION_PATH, type=Path)
    parser.add_argument(
        "--clarification-requests",
        default=DEFAULT_CLARIFICATION_REQUESTS_PATH,
        type=Path,
    )
    parser.add_argument("--workspace-id")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, type=Path)
    parser.add_argument("--strict", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_specspace_repair_draft_import_preview(
        draft_state=load_json(args.drafts),
        repair_session=load_json(args.repair_session),
        clarification_requests=load_json(args.clarification_requests),
        draft_state_path=args.drafts,
        repair_session_path=args.repair_session,
        clarification_requests_path=args.clarification_requests,
        workspace_id=args.workspace_id,
    )
    write_json(report, args.output)
    summary = _dict(report.get("summary"))
    print(
        f"{summary.get('status', 'unknown')}: "
        f"{summary.get('accepted_for_rerun_count', 0)} accepted, "
        f"{summary.get('deferred_count', 0)} deferred, "
        f"{summary.get('invalid_draft_count', 0)} invalid -> "
        f"{_relative_ref(args.output)}"
    )
    if args.strict and not _dict(report.get("readiness")).get("ready"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
