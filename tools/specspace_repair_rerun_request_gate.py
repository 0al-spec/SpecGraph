"""Validate SpecSpace repair rerun requests before replaying draft repairs."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PROPOSAL_ID = "0174"
SCHEMA_VERSION = 1
ARTIFACT_KIND = "specspace_repair_rerun_request_gate"
CONTRACT_REF = "specgraph.idea-to-spec.specspace-repair-rerun-request-gate.v0.1"
REQUEST_STATE_KIND = "specspace_idea_to_spec_repair_rerun_request_state"
REQUESTED_ACTION = "prepare_repair_draft_rerun"
IMPORT_PREVIEW_KIND = "specspace_repair_draft_import_preview"
IMPORT_PREVIEW_CONTRACT_REF = "specgraph.idea-to-spec.specspace-repair-draft-import-preview.v0.1"
REPAIR_SESSION_KIND = "idea_to_spec_repair_session_journal"
REPAIR_SESSION_CONTRACT_REF = "specgraph.idea-to-spec.repair-session-journal.v0.1"

DEFAULT_REQUEST_STATE_PATH = ROOT / "runs" / "idea_to_spec_repair_rerun_requests.json"
DEFAULT_IMPORT_PREVIEW_PATH = ROOT / "runs" / "specspace_repair_draft_import_preview.json"
DEFAULT_REPAIR_SESSION_PATH = ROOT / "runs" / "idea_to_spec_repair_session.json"
DEFAULT_OUTPUT_PATH = ROOT / "runs" / "specspace_repair_rerun_request_gate.json"

TOP_LEVEL_FALSE_FIELDS = (
    "canonical_mutations_allowed",
    "tracked_artifacts_written",
)
CONSUMER_FALSE_FIELDS = (
    "may_execute_specgraph",
    "may_run_make_target",
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
    "may_execute_git_service_operation",
)
AUTHORITY_FALSE_FIELDS = (
    "rerun_request_state_is_authority",
    "specgraph_execution_authority",
    "specgraph_artifact_authority",
    "ontology_authority",
    "git_service_authority",
    "canonical_mutations_allowed",
)
REQUEST_FALSE_FIELDS = (
    "may_execute_specgraph",
    "may_run_make_target",
    "may_execute_prompt_agent",
    "may_apply_to_specgraph",
    "may_apply_answers",
    "may_apply_decisions",
    "may_apply_drafts_to_source_artifacts",
    "may_apply_answers_to_source_artifacts",
    "may_apply_decisions_to_source_artifacts",
    "may_mutate_candidate_source_artifacts",
    "may_mutate_canonical_specs",
    "may_write_ontology_package",
    "may_write_ontology_lockfile",
    "may_accept_ontology_terms",
    "may_mark_candidate_graph_accepted",
    "may_create_branch_or_commit",
    "may_open_pull_request",
    "may_publish_read_model",
    "may_execute_git_service_operation",
    "canonical_mutations_allowed",
    "tracked_artifacts_written",
)
REVIEW_ONLY_AUTHORITY_FIELDS = (
    "may_execute_prompt_agent",
    "may_apply_to_specgraph",
    "may_apply_answers",
    "may_apply_decisions",
    "may_apply_answers_to_source_artifacts",
    "may_apply_decisions_to_source_artifacts",
    "may_mutate_candidate_source_artifacts",
    "may_mutate_canonical_specs",
    "may_write_ontology_package",
    "may_write_ontology_lockfile",
    "may_accept_ontology_terms",
    "may_mark_candidate_graph_accepted",
    "may_create_branch_or_commit",
    "may_open_pull_request",
    "may_publish_read_model",
)
RAW_TRACE_FIELDS = {
    "operator_note",
    "operator_notes",
    "private_note",
    "raw_answer",
    "raw_draft",
    "raw_idea_text",
    "raw_model_output",
    "raw_operator_note",
    "raw_prompt",
}


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any, default: str = "") -> str:
    return value.strip() if isinstance(value, str) and value.strip() else default


def _number(value: Any) -> int:
    return int(value) if isinstance(value, int | float) else 0


def _relative_ref(path: Path | None) -> str:
    if path is None:
        return "inline:unknown"
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _sha256(path: Path | None) -> str | None:
    if path is None or not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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
        "source": "specspace_repair_rerun_request_gate",
        "evidence": evidence or {},
    }


def _first_true(value: Any, fields: tuple[str, ...]) -> str | None:
    record = _dict(value)
    for field in fields:
        if record.get(field) is True:
            return field
    return None


def _authority_boundary() -> dict[str, bool]:
    return {
        "may_execute_prompt_agent": False,
        "may_execute_specgraph_from_request": False,
        "may_run_make_target_from_request": False,
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


def _safe_artifact_ref(ref: str) -> str | None:
    if not ref:
        return None
    if "://" in ref:
        return None
    path = Path(ref)
    if any(part in ("", ".", "..") for part in path.parts):
        return None
    return path.as_posix()


def _safe_draft_state_ref(ref: str) -> str | None:
    if not ref:
        return None
    prefix = "specspace-state://"
    if ref.startswith(prefix):
        state_name = ref.removeprefix(prefix)
        if not state_name or "/" in state_name or "\\" in state_name or state_name in (".", ".."):
            return None
        return ref
    return _safe_artifact_ref(ref)


def _refs_match_operator_draft_state(*, request_ref: str, preview_source_ref: str) -> bool:
    if request_ref == preview_source_ref:
        return True
    prefix = "specspace-state://"
    if request_ref.startswith(prefix):
        return Path(preview_source_ref).name == request_ref.removeprefix(prefix)
    return False


def _validate_request_state_shape(request_state: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if request_state.get("artifact_kind") != REQUEST_STATE_KIND:
        findings.append(
            _finding(
                finding_id="request_state_wrong_artifact_kind",
                severity="review_required",
                message=f"Request state must use artifact_kind {REQUEST_STATE_KIND}.",
                evidence={"artifact_kind": request_state.get("artifact_kind")},
            )
        )
    if request_state.get("schema_version") != SCHEMA_VERSION:
        findings.append(
            _finding(
                finding_id="request_state_schema_version_unsupported",
                severity="review_required",
                message="Request state schema_version must be 1.",
                evidence={"schema_version": request_state.get("schema_version")},
            )
        )
    if request_state.get("state_owner") != "SpecSpace":
        findings.append(
            _finding(
                finding_id="request_state_owner_not_specspace",
                severity="review_required",
                message="Repair rerun request state must be owned by SpecSpace.",
                evidence={"state_owner": request_state.get("state_owner")},
            )
        )
    for field in TOP_LEVEL_FALSE_FIELDS:
        if request_state.get(field) is not False:
            findings.append(
                _finding(
                    finding_id="request_state_authority_expanded",
                    severity="review_required",
                    message=f"Request state {field} must be false.",
                    evidence={field: request_state.get(field)},
                )
            )
    field = _first_true(request_state.get("consumer_boundary"), CONSUMER_FALSE_FIELDS)
    if field:
        findings.append(
            _finding(
                finding_id="request_state_consumer_boundary_expanded",
                severity="review_required",
                message="Request state consumer boundary must remain review-only.",
                evidence={field: True},
            )
        )
    field = _first_true(request_state.get("authority_boundary"), AUTHORITY_FALSE_FIELDS)
    if field:
        findings.append(
            _finding(
                finding_id="request_state_authority_boundary_expanded",
                severity="review_required",
                message="Request state authority boundary must remain non-authoritative.",
                evidence={field: True},
            )
        )
    return findings


def _select_active_request(
    request_state: dict[str, Any],
    *,
    workspace_id: str | None,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], int]:
    findings: list[dict[str, Any]] = []
    request_rows = [_dict(item) for item in _list(request_state.get("requests"))]
    active_requests: list[dict[str, Any]] = []
    for request in request_rows:
        if workspace_id and _text(request.get("workspace_id")) != workspace_id:
            continue
        field = _first_true(request, REQUEST_FALSE_FIELDS)
        if field:
            findings.append(
                _finding(
                    finding_id="request_record_authority_expanded",
                    severity="review_required",
                    message=(
                        "Repair rerun request records cannot grant execution or mutation authority."
                    ),
                    evidence={
                        "request_id": request.get("id"),
                        field: True,
                    },
                )
            )
            continue
        if _text(request.get("status")) != "requested":
            continue
        if _text(request.get("requested_action")) != REQUESTED_ACTION:
            findings.append(
                _finding(
                    finding_id="request_record_action_unsupported",
                    severity="review_required",
                    message=f"Requested action must be {REQUESTED_ACTION}.",
                    evidence={
                        "request_id": request.get("id"),
                        "requested_action": request.get("requested_action"),
                    },
                )
            )
            continue
        active_requests.append(request)

    if not active_requests:
        findings.append(
            _finding(
                finding_id="requested_repair_rerun_missing",
                severity="review_required",
                message="No active SpecSpace repair rerun request was found.",
                evidence={"workspace_id": workspace_id},
            )
        )
        return None, findings, 0
    if len(active_requests) > 1:
        findings.append(
            _finding(
                finding_id="requested_repair_rerun_ambiguous",
                severity="review_required",
                message="Exactly one active SpecSpace repair rerun request is required.",
                evidence={
                    "request_ids": [_text(request.get("id")) for request in active_requests],
                },
            )
        )
        return None, findings, len(active_requests)
    return active_requests[0], findings, 1


def _validate_selected_request(
    request: dict[str, Any] | None,
    *,
    repair_session: dict[str, Any],
    import_preview: dict[str, Any],
    request_state_path: Path,
    import_preview_path: Path,
    repair_session_path: Path,
) -> list[dict[str, Any]]:
    if request is None:
        return []
    findings: list[dict[str, Any]] = []
    required_fields = (
        "id",
        "workspace_id",
        "candidate_id",
        "repair_session_id",
        "repair_session_ref",
        "draft_state_ref",
        "import_preview_ref",
    )
    for field in required_fields:
        if not _text(request.get(field)):
            findings.append(
                _finding(
                    finding_id=f"request_record_{field}_missing",
                    severity="review_required",
                    message=f"Repair rerun request field {field} is required.",
                    evidence={"request_id": request.get("id")},
                )
            )

    import_preview_ref = _text(request.get("import_preview_ref"))
    repair_session_ref = _text(request.get("repair_session_ref"))
    draft_state_ref = _text(request.get("draft_state_ref"))
    if _safe_artifact_ref(import_preview_ref) is None:
        findings.append(
            _finding(
                finding_id="request_import_preview_ref_unsafe",
                severity="review_required",
                message="Request import_preview_ref must be an explicit artifact path.",
                evidence={"import_preview_ref": import_preview_ref},
            )
        )
    if repair_session_ref and _safe_artifact_ref(repair_session_ref) is None:
        findings.append(
            _finding(
                finding_id="request_repair_session_ref_unsafe",
                severity="review_required",
                message="Request repair_session_ref must be an explicit artifact path.",
                evidence={"repair_session_ref": repair_session_ref},
            )
        )
    if draft_state_ref and _safe_draft_state_ref(draft_state_ref) is None:
        findings.append(
            _finding(
                finding_id="request_draft_state_ref_unsafe",
                severity="review_required",
                message=(
                    "Request draft_state_ref must be a safe SpecSpace state URI or artifact path."
                ),
                evidence={"draft_state_ref": draft_state_ref},
            )
        )

    expected_import_preview_ref = _relative_ref(import_preview_path)
    if import_preview_ref != expected_import_preview_ref:
        findings.append(
            _finding(
                finding_id="request_import_preview_ref_mismatch",
                severity="review_required",
                message="Request import_preview_ref must match the selected import preview input.",
                evidence={
                    "actual": import_preview_ref,
                    "expected": expected_import_preview_ref,
                },
            )
        )

    expected_repair_session_ref = _relative_ref(repair_session_path)
    if repair_session_ref and repair_session_ref != expected_repair_session_ref:
        findings.append(
            _finding(
                finding_id="request_repair_session_ref_mismatch",
                severity="review_required",
                message="Request repair_session_ref must match the selected repair session input.",
                evidence={
                    "actual": repair_session_ref,
                    "expected": expected_repair_session_ref,
                },
            )
        )

    session = _dict(repair_session.get("session"))
    preview_session = _dict(import_preview.get("session"))
    preview_sources = _dict(import_preview.get("source_artifacts"))
    request_workspace_id = _text(request.get("workspace_id"))
    request_candidate_id = _text(request.get("candidate_id"))
    request_repair_session_id = _text(request.get("repair_session_id"))
    if request_candidate_id != _text(session.get("candidate_id")):
        findings.append(
            _finding(
                finding_id="request_candidate_id_mismatch",
                severity="review_required",
                message="Request candidate_id must match the repair session candidate.",
                evidence={
                    "actual": request_candidate_id,
                    "expected": session.get("candidate_id"),
                },
            )
        )
    if request_repair_session_id != _text(session.get("session_id")):
        findings.append(
            _finding(
                finding_id="request_repair_session_id_mismatch",
                severity="review_required",
                message="Request repair_session_id must match the selected repair session.",
                evidence={
                    "actual": request_repair_session_id,
                    "expected": session.get("session_id"),
                },
            )
        )
    if request_repair_session_id != _text(preview_session.get("session_id")):
        findings.append(
            _finding(
                finding_id="request_import_preview_repair_session_id_mismatch",
                severity="review_required",
                message="Request repair_session_id must match the import preview session.",
                evidence={
                    "actual": request_repair_session_id,
                    "expected": preview_session.get("session_id"),
                },
            )
        )
    if request_candidate_id != _text(preview_session.get("candidate_id")):
        findings.append(
            _finding(
                finding_id="request_import_preview_candidate_id_mismatch",
                severity="review_required",
                message="Request candidate_id must match the import preview candidate.",
                evidence={
                    "actual": request_candidate_id,
                    "expected": preview_session.get("candidate_id"),
                },
            )
        )
    preview_workspace_id = _text(preview_session.get("workspace_id"))
    if preview_workspace_id and request_workspace_id != preview_workspace_id:
        findings.append(
            _finding(
                finding_id="request_import_preview_workspace_id_mismatch",
                severity="review_required",
                message="Request workspace_id must match the import preview workspace.",
                evidence={
                    "actual": request_workspace_id,
                    "expected": preview_workspace_id,
                },
            )
        )
    session_workspace_id = _text(session.get("workspace_id"))
    if session_workspace_id and request_workspace_id != session_workspace_id:
        findings.append(
            _finding(
                finding_id="request_repair_session_workspace_id_mismatch",
                severity="review_required",
                message="Request workspace_id must match the repair session workspace.",
                evidence={
                    "actual": request_workspace_id,
                    "expected": session_workspace_id,
                },
            )
        )
    for field in ("workflow_lane", "governance_profile", "target_repository_role"):
        actual = _text(preview_session.get(field))
        expected = _text(session.get(field))
        if actual != expected:
            findings.append(
                _finding(
                    finding_id=f"import_preview_session_{field}_mismatch",
                    severity="review_required",
                    message=f"Import preview session {field} must match the repair session.",
                    evidence={"actual": actual, "expected": expected},
                )
            )
    if request_workspace_id and not request_candidate_id:
        findings.append(
            _finding(
                finding_id="request_workspace_without_candidate",
                severity="review_required",
                message="Request workspace_id cannot be evaluated without candidate_id.",
                evidence={"workspace_id": request_workspace_id},
            )
        )
    preview_repair_session_ref = _text(
        _dict(preview_sources.get("idea_to_spec_repair_session")).get("source_ref")
    )
    if preview_repair_session_ref != expected_repair_session_ref:
        findings.append(
            _finding(
                finding_id="import_preview_idea_to_spec_repair_session_source_ref_mismatch",
                severity="review_required",
                message=(
                    "Import preview repair-session source_ref must match the selected repair "
                    "session input."
                ),
                evidence={
                    "actual": preview_repair_session_ref,
                    "expected": expected_repair_session_ref,
                },
            )
        )
    preview_draft_state_ref = _text(
        _dict(preview_sources.get("specspace_repair_drafts")).get("source_ref")
    )
    if (
        draft_state_ref
        and preview_draft_state_ref
        and not _refs_match_operator_draft_state(
            request_ref=draft_state_ref,
            preview_source_ref=preview_draft_state_ref,
        )
    ):
        findings.append(
            _finding(
                finding_id="request_draft_state_ref_mismatch",
                severity="review_required",
                message="Request draft_state_ref must match the import preview draft-state source.",
                evidence={
                    "actual": draft_state_ref,
                    "expected": preview_draft_state_ref,
                },
            )
        )
    if draft_state_ref == _relative_ref(request_state_path):
        findings.append(
            _finding(
                finding_id="request_draft_state_ref_points_to_request_state",
                severity="review_required",
                message="Request draft_state_ref must not point back to the request artifact.",
                evidence={"draft_state_ref": request.get("draft_state_ref")},
            )
        )
    return findings


def _validate_import_preview(import_preview: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if import_preview.get("artifact_kind") != IMPORT_PREVIEW_KIND:
        findings.append(
            _finding(
                finding_id="import_preview_wrong_artifact_kind",
                severity="review_required",
                message=f"Import preview must use artifact_kind {IMPORT_PREVIEW_KIND}.",
                evidence={"artifact_kind": import_preview.get("artifact_kind")},
            )
        )
    if import_preview.get("contract_ref") != IMPORT_PREVIEW_CONTRACT_REF:
        findings.append(
            _finding(
                finding_id="import_preview_contract_ref_unsupported",
                severity="review_required",
                message=f"Import preview contract_ref must be {IMPORT_PREVIEW_CONTRACT_REF}.",
                evidence={"contract_ref": import_preview.get("contract_ref")},
            )
        )
    if import_preview.get("schema_version") != SCHEMA_VERSION:
        findings.append(
            _finding(
                finding_id="import_preview_schema_version_unsupported",
                severity="review_required",
                message="Import preview schema_version must be 1.",
                evidence={"schema_version": import_preview.get("schema_version")},
            )
        )
    for field in TOP_LEVEL_FALSE_FIELDS:
        if import_preview.get(field) is not False:
            findings.append(
                _finding(
                    finding_id="import_preview_authority_expanded",
                    severity="review_required",
                    message=f"Import preview {field} must be false.",
                    evidence={field: import_preview.get(field)},
                )
            )
    field = _first_true(import_preview.get("authority_boundary"), REVIEW_ONLY_AUTHORITY_FIELDS)
    if field:
        findings.append(
            _finding(
                finding_id="import_preview_authority_boundary_expanded",
                severity="review_required",
                message="Import preview authority boundary must remain review-only.",
                evidence={field: True},
            )
        )
    readiness = _dict(import_preview.get("readiness"))
    if readiness.get("ready") is not True:
        findings.append(
            _finding(
                finding_id="import_preview_not_ready_for_requested_rerun",
                severity="review_required",
                message="Requested rerun requires a ready SpecSpace repair draft import preview.",
                evidence={"readiness": readiness},
            )
        )
    if _number(_dict(import_preview.get("summary")).get("accepted_for_rerun_count")) <= 0:
        findings.append(
            _finding(
                finding_id="import_preview_accepted_for_rerun_missing",
                severity="review_required",
                message="Requested rerun requires at least one accepted draft import.",
                evidence={"summary": _dict(import_preview.get("summary"))},
            )
        )
    return findings


def _validate_repair_session(repair_session: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
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
    readiness = _dict(repair_session.get("readiness"))
    if readiness.get("ready") is not True:
        findings.append(
            _finding(
                finding_id="repair_session_not_ready_for_requested_rerun",
                severity="review_required",
                message="Requested rerun requires a ready repair session journal.",
                evidence={"readiness": readiness},
            )
        )
    field = _first_true(repair_session.get("authority_boundary"), REVIEW_ONLY_AUTHORITY_FIELDS)
    if field:
        findings.append(
            _finding(
                finding_id="repair_session_authority_boundary_expanded",
                severity="review_required",
                message="Repair session authority boundary must remain review-only.",
                evidence={field: True},
            )
        )
    return findings


def _source_record(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_kind": payload.get("artifact_kind"),
        "contract_ref": payload.get("contract_ref"),
        "source_ref": _relative_ref(path),
        "sha256": _sha256(path),
    }


def _recommended_invocation(
    *,
    request_state_path: Path,
    import_preview_path: Path,
    repair_session_path: Path,
    workspace_id: str,
) -> dict[str, Any]:
    variables = {
        "SPECSPACE_REPAIR_RERUN_REQUEST_STATE": _relative_ref(request_state_path),
        "SPECSPACE_REPAIR_RERUN_REQUEST_IMPORT_PREVIEW": _relative_ref(import_preview_path),
        "SPECSPACE_REPAIR_RERUN_REQUEST_REPAIR_SESSION": _relative_ref(repair_session_path),
    }
    if workspace_id:
        variables["SPECSPACE_REPAIR_RERUN_REQUEST_WORKSPACE_ID"] = workspace_id
    parts = ["make product-workspace-requested-repair-draft-rerun"]
    parts.extend(f'{key}="{value}"' for key, value in variables.items())
    return {
        "make_target": "product-workspace-requested-repair-draft-rerun",
        "make_variables": variables,
        "operator_command": " ".join(parts),
    }


def build_specspace_repair_rerun_request_gate(
    *,
    request_state: dict[str, Any],
    import_preview: dict[str, Any],
    repair_session: dict[str, Any],
    request_state_path: Path,
    import_preview_path: Path,
    repair_session_path: Path,
    workspace_id: str | None = None,
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    findings.extend(_validate_request_state_shape(request_state))
    selected_request, request_findings, active_request_count = _select_active_request(
        request_state,
        workspace_id=workspace_id,
    )
    findings.extend(request_findings)
    findings.extend(_validate_repair_session(repair_session))
    findings.extend(_validate_import_preview(import_preview))
    findings.extend(
        _validate_selected_request(
            selected_request,
            repair_session=repair_session,
            import_preview=import_preview,
            request_state_path=request_state_path,
            import_preview_path=import_preview_path,
            repair_session_path=repair_session_path,
        )
    )
    ready = not findings
    request_workspace_id = _text(
        _dict(selected_request).get("workspace_id"),
        workspace_id or "",
    )
    invocation = _recommended_invocation(
        request_state_path=request_state_path,
        import_preview_path=import_preview_path,
        repair_session_path=repair_session_path,
        workspace_id=request_workspace_id,
    )
    return {
        "artifact_kind": ARTIFACT_KIND,
        "schema_version": SCHEMA_VERSION,
        "proposal_id": PROPOSAL_ID,
        "contract_ref": CONTRACT_REF,
        "generated_at": _now_iso(),
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "source_artifacts": {
            "specspace_repair_rerun_request_state": _source_record(
                request_state_path,
                request_state,
            ),
            "specspace_repair_draft_import_preview": _source_record(
                import_preview_path,
                import_preview,
            ),
            "idea_to_spec_repair_session": _source_record(
                repair_session_path,
                repair_session,
            ),
        },
        "selected_request": _public_safe(selected_request) if selected_request else None,
        "resolved_inputs": {
            "workspace_id": request_workspace_id,
            "candidate_id": _text(_dict(selected_request).get("candidate_id")),
            "repair_session_ref": _relative_ref(repair_session_path),
            "import_preview_ref": _relative_ref(import_preview_path),
        },
        "recommended_invocation": invocation,
        "readiness": {
            "ready": ready,
            "review_state": (
                "specspace_repair_rerun_request_ready"
                if ready
                else "specspace_repair_rerun_request_review_required"
            ),
            "blocked_by": [
                _text(finding.get("finding_id"))
                for finding in findings
                if _text(finding.get("finding_id"))
            ],
            "next_artifact": (
                "runs/specspace_repair_draft_rerun_report.json"
                if ready
                else "repair SpecSpace rerun request/import preview handoff"
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
        "summary": {
            "status": (
                "specspace_repair_rerun_request_ready"
                if ready
                else "specspace_repair_rerun_request_review_required"
            ),
            "selected_request_id": _text(_dict(selected_request).get("id")),
            "workspace_id": request_workspace_id,
            "candidate_id": _text(_dict(selected_request).get("candidate_id")),
            "active_request_count": active_request_count,
            "accepted_for_rerun_count": _dict(import_preview.get("summary")).get(
                "accepted_for_rerun_count",
                0,
            ),
            "finding_count": len(findings),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request-state", default=DEFAULT_REQUEST_STATE_PATH, type=Path)
    parser.add_argument("--import-preview", default=DEFAULT_IMPORT_PREVIEW_PATH, type=Path)
    parser.add_argument("--repair-session", default=DEFAULT_REPAIR_SESSION_PATH, type=Path)
    parser.add_argument("--workspace-id")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, type=Path)
    parser.add_argument("--strict", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_specspace_repair_rerun_request_gate(
        request_state=load_json(args.request_state),
        import_preview=load_json(args.import_preview),
        repair_session=load_json(args.repair_session),
        request_state_path=args.request_state,
        import_preview_path=args.import_preview,
        repair_session_path=args.repair_session,
        workspace_id=args.workspace_id,
    )
    write_json(report, args.output)
    summary = _dict(report.get("summary"))
    print(
        f"{summary.get('status', 'unknown')}: "
        f"{summary.get('selected_request_id') or 'no-request'} -> "
        f"{_relative_ref(args.output)}"
    )
    if args.strict and not _dict(report.get("readiness")).get("ready"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
