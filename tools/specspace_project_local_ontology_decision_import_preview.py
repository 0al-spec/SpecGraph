"""Preview SpecSpace-owned project-local ontology decisions without applying them."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_ID = "0198"
SCHEMA_VERSION = 1
CONTRACT_REF = "specgraph.product-ontology.specspace-project-local-decision-import-preview.v0.1"

DECISION_STATE_KIND = "specspace_project_local_ontology_review_decision_state"
LANE_KIND = "project_local_ontology_review_lane"

DEFAULT_DECISIONS_PATH = ROOT / "runs" / "project_local_ontology_review_decisions.json"
DEFAULT_LANE_PATH = ROOT / "runs" / "project_local_ontology_review_lane.json"
DEFAULT_OUTPUT_PATH = (
    ROOT / "runs" / "specspace_project_local_ontology_decision_import_preview.json"
)

SUPPORTED_ACTIONS = {
    "keep_project_local",
    "bind_existing",
    "alias",
    "reject",
    "request_workspace_promotion",
    "defer",
}
ACTION_TO_DECISION_TYPE = {
    "keep_project_local": "propose_project_local_term",
    "bind_existing": "bind_existing_term",
    "alias": "alias_existing_term",
    "reject": "reject_non_domain_term",
    "request_workspace_promotion": "request_workspace_promotion",
    "defer": "defer_requires_owner",
}
NON_RESOLVING_ACTIONS = {"defer"}

TOP_LEVEL_FALSE_FIELDS = (
    "canonical_mutations_allowed",
    "tracked_artifacts_written",
)
CONSUMER_FALSE_FIELDS = (
    "may_execute_prompt_agent",
    "may_execute_specgraph",
    "may_execute_platform",
    "may_apply_to_specgraph",
    "may_apply_decisions",
    "may_mutate_candidate_artifacts",
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
AUTHORITY_FALSE_FIELDS = (
    "project_local_ontology_review_decision_state_is_authority",
    "specgraph_artifact_authority",
    "ontology_authority",
    "git_service_authority",
    "canonical_mutations_allowed",
    "may_execute_prompt_agent",
    "may_execute_specgraph",
    "may_execute_platform",
    "may_apply_to_specgraph",
    "may_apply_decisions",
    "may_mutate_candidate_artifacts",
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
DECISION_FALSE_FIELDS = (
    "canonical_mutations_allowed",
    "tracked_artifacts_written",
    "applies_to_specgraph",
    "applies_to_candidate_artifacts",
    "mutates_canonical_specs",
    "writes_ontology_package",
    "updates_ontology_lockfile",
    "accepts_ontology_terms",
    "may_mark_candidate_graph_accepted",
    "creates_branch_or_commit",
    "opens_pull_request",
    "may_publish_read_model",
    "may_execute_prompt_agent",
    "may_execute_specgraph",
    "may_execute_platform",
    "may_apply_to_specgraph",
    "may_apply_decisions",
    "may_mutate_candidate_artifacts",
    "may_mutate_canonical_specs",
    "may_write_ontology_package",
    "may_write_ontology_lockfile",
    "may_accept_ontology_terms",
    "may_mark_candidate_graph_accepted",
    "may_create_branch_or_commit",
    "may_open_pull_request",
    "may_publish_read_model",
)
LANE_AUTHORITY_FALSE_FIELDS = (
    "may_execute_prompt_agent",
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
    "private_notes",
    "raw_answer",
    "raw_intent",
    "raw_intent_text",
    "raw_model_output",
    "raw_operator_note",
    "raw_prompt",
    "raw_response",
    "raw_text",
}

PRIVATE_PATH_MARKERS = (
    "/Users/",
    "/home/",
    "/private/",
    "/tmp/",
)
PRIVATE_VALUE_MARKERS = (
    "-----BEGIN",
    "api-key",
    "apikey",
    "api_key",
    "bearer ",
    "token=",
)


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any, default: str = "") -> str:
    return value.strip() if isinstance(value, str) and value.strip() else default


def _slug(value: str, fallback: str = "decision") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or fallback


def _term_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def _relative_ref(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return f"external:{path.name or 'artifact'}"


def _accepted_review_lane_refs(path: Path | None) -> set[str]:
    lane_ref = _relative_ref(path)
    if not lane_ref:
        return set()
    refs = {lane_ref}
    if (
        path is not None
        and path.name == "project_local_ontology_review_lane.json"
        and lane_ref.startswith("runs/")
        and lane_ref != "runs/project_local_ontology_review_lane.json"
    ):
        refs.add("runs/project_local_ontology_review_lane.json")
    return refs


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
    if isinstance(value, str):
        lowered = value.lower()
        if any(marker.lower() in lowered for marker in PRIVATE_PATH_MARKERS):
            return "[redacted-private-text]"
        if any(marker.lower() in lowered for marker in PRIVATE_VALUE_MARKERS):
            return "[redacted-private-text]"
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
        "source": "specspace_project_local_ontology_decision_import_preview",
        "evidence": evidence or {},
    }


def _authority_boundary() -> dict[str, bool]:
    return {
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
    }


def _privacy_boundary() -> dict[str, bool]:
    return {
        "raw_idea_text_published": False,
        "raw_prompt_published": False,
        "raw_model_output_published": False,
        "raw_operator_note_published": False,
        "private_operator_state_published": False,
    }


def _source_artifact(
    key: str,
    payload: dict[str, Any],
    path: Path | None,
    *,
    required: bool = True,
) -> dict[str, Any]:
    status = "present" if payload else ("missing_required" if required else "missing_optional")
    return {
        "artifact_key": key,
        "artifact_kind": payload.get("artifact_kind") if payload else None,
        "contract_ref": payload.get("contract_ref") if payload else None,
        "schema_version": payload.get("schema_version") if payload else None,
        "source_ref": _relative_ref(path),
        "sha256": _sha256(path),
        "status": status,
        "summary": _public_safe(payload.get("summary")) if payload else {},
    }


def _first_true(value: Any, fields: tuple[str, ...]) -> str | None:
    if not isinstance(value, dict):
        return None
    for field in fields:
        if value.get(field) is True:
            return field
    return None


def _validate_contracts(
    *,
    decision_state: dict[str, Any],
    lane: dict[str, Any],
    findings: list[dict[str, Any]],
) -> None:
    if not decision_state:
        findings.append(
            _finding(
                finding_id="project_local_decision_state_missing",
                severity="blocking",
                message="SpecSpace project-local ontology decision state is missing.",
            )
        )
        return
    if decision_state.get("artifact_kind") != DECISION_STATE_KIND:
        findings.append(
            _finding(
                finding_id="project_local_decision_state_kind_invalid",
                severity="blocking",
                message=(
                    "SpecSpace project-local ontology decision state has unexpected artifact_kind."
                ),
                evidence={"artifact_kind": decision_state.get("artifact_kind")},
            )
        )
    if decision_state.get("state_owner") != "SpecSpace":
        findings.append(
            _finding(
                finding_id="project_local_decision_state_owner_invalid",
                severity="blocking",
                message="Project-local ontology decision state must be owned by SpecSpace.",
                evidence={"state_owner": decision_state.get("state_owner")},
            )
        )
    field = _first_true(decision_state, TOP_LEVEL_FALSE_FIELDS)
    if field is not None:
        findings.append(
            _finding(
                finding_id="project_local_decision_state_authority_expanded",
                severity="blocking",
                message=f"Project-local ontology decision state cannot claim {field}.",
                evidence={"field": field},
            )
        )
    for boundary_name, fields in (
        ("consumer_boundary", CONSUMER_FALSE_FIELDS),
        ("authority_boundary", AUTHORITY_FALSE_FIELDS),
    ):
        field = _first_true(_dict(decision_state.get(boundary_name)), fields)
        if field is not None:
            findings.append(
                _finding(
                    finding_id=f"project_local_decision_state_{boundary_name}_expanded",
                    severity="blocking",
                    message=(
                        f"Project-local ontology decision {boundary_name}.{field} must not be true."
                    ),
                    evidence={"boundary": boundary_name, "field": field},
                )
            )

    if not lane:
        findings.append(
            _finding(
                finding_id="project_local_review_lane_missing",
                severity="blocking",
                message="Project-local ontology review lane artifact is missing.",
            )
        )
        return
    if lane.get("artifact_kind") != LANE_KIND:
        findings.append(
            _finding(
                finding_id="project_local_review_lane_kind_invalid",
                severity="blocking",
                message="Project-local ontology review lane has unexpected artifact_kind.",
                evidence={"artifact_kind": lane.get("artifact_kind")},
            )
        )
    if lane.get("canonical_mutations_allowed") is not False:
        findings.append(
            _finding(
                finding_id="project_local_review_lane_canonical_mutation_claim",
                severity="blocking",
                message="Project-local ontology review lane must not allow canonical mutations.",
            )
        )
    if lane.get("tracked_artifacts_written") is not False:
        findings.append(
            _finding(
                finding_id="project_local_review_lane_write_claim",
                severity="blocking",
                message="Project-local ontology review lane must be review-only.",
            )
        )
    field = _first_true(
        _dict(lane.get("authority_boundary")),
        LANE_AUTHORITY_FALSE_FIELDS,
    )
    if field is not None:
        findings.append(
            _finding(
                finding_id="project_local_review_lane_authority_expanded",
                severity="blocking",
                message=(
                    "Project-local ontology review lane authority_boundary."
                    f"{field} must not be true."
                ),
                evidence={"field": field},
            )
        )
    privacy = _dict(lane.get("privacy_boundary"))
    for key, flag in privacy.items():
        if (
            isinstance(key, str)
            and key.startswith("raw_")
            and key.endswith("_published")
            and flag is True
        ):
            findings.append(
                _finding(
                    finding_id="project_local_review_lane_raw_trace_published",
                    severity="blocking",
                    message=(
                        "Project-local ontology review lane must not publish raw/private traces."
                    ),
                    evidence={"field": key},
                )
            )


def _decision_value(
    *,
    action: str,
    raw_value: Any,
    term: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    value = _dict(raw_value)
    field = _first_true(value, DECISION_FALSE_FIELDS + CONSUMER_FALSE_FIELDS)
    if field is not None:
        return {}, {
            "reason": "decision_value_authority_expanded",
            "field": field,
        }
    explicit_term = _text(value.get("term"))
    if explicit_term and _term_key(explicit_term) != _text(term.get("term_key")):
        return {}, {
            "reason": "decision_term_mismatch",
            "expected_term_key": _text(term.get("term_key")),
            "actual_term_key": _term_key(explicit_term),
        }
    term_text = _text(value.get("term")) or _text(term.get("term"))
    if action == "keep_project_local":
        result = {"term": term_text, "term_scope": "project_local"}
        reason = _text(value.get("reason") or value.get("text"))
        if reason:
            result["reason"] = reason
        return result, None
    if action == "bind_existing":
        ontology_ref = _text(value.get("ontology_ref") or value.get("text"))
        if not ontology_ref:
            return {}, {"reason": "bind_existing_requires_ontology_ref"}
        return {"term": term_text, "ontology_ref": ontology_ref}, None
    if action == "alias":
        alias_of = _text(value.get("alias_of") or value.get("text"))
        if not alias_of:
            return {}, {"reason": "alias_requires_alias_of"}
        return {"term": term_text, "alias_of": alias_of}, None
    if action in {"reject", "request_workspace_promotion", "defer"}:
        reason = _text(value.get("reason") or value.get("text"))
        if not reason:
            return {}, {"reason": f"{action}_requires_reason"}
        result = {"term": term_text, "reason": reason}
        if action == "request_workspace_promotion":
            result["promotion_scope"] = _text(value.get("promotion_scope")) or "workspace"
        if action == "defer":
            follow_up = _text(value.get("follow_up"))
            if follow_up:
                result["follow_up"] = follow_up
        return result, None
    return {}, {"reason": "unsupported_action"}


def _lane_terms(lane: dict[str, Any]) -> dict[str, dict[str, Any]]:
    terms: dict[str, dict[str, Any]] = {}
    for item in _list(lane.get("terms")):
        term = _dict(item)
        term_key = _text(term.get("term_key"))
        if term_key:
            terms[term_key] = term
    return terms


def _required_term_keys(lane_terms: dict[str, dict[str, Any]]) -> set[str]:
    required: set[str] = set()
    for term_key, term in lane_terms.items():
        status = _text(term.get("status"), "unreviewed")
        if status in {"unreviewed", "deferred"}:
            required.add(term_key)
    return required


def _candidate_from_decision(
    *,
    decision: dict[str, Any],
    action: str,
    value: dict[str, Any],
    term: dict[str, Any],
    source_ref: str | None,
) -> dict[str, Any]:
    term_key = _text(decision.get("term_key"))
    target_ref = _text(decision.get("target_ref")) or _text(
        _dict((_list(term.get("gap_refs")) or [{}])[0]).get("target_ref")
    )
    decision_type = ACTION_TO_DECISION_TYPE[action]
    status = (
        "deferred_requires_owner"
        if action in NON_RESOLVING_ACTIONS
        else "accepted_for_project_local_preview"
    )
    return {
        "id": f"specspace-project-local-ontology-import.{_slug(term_key)}.{_slug(action)}",
        "source_decision_id": _text(decision.get("decision_id")),
        "source_artifact": source_ref,
        "decision_type": decision_type,
        "review_action": action,
        "status": status,
        "materialization_intent": (
            "non_resolving_review_note"
            if action in NON_RESOLVING_ACTIONS
            else "review_overlay_only"
        ),
        "term": _text(value.get("term")) or _text(term.get("term")),
        "term_key": term_key,
        "decision_value": _public_safe(value),
        "target_ref": target_ref,
        "gap_refs": _public_safe(_list(term.get("gap_refs"))),
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "writes_ontology_package": False,
        "updates_ontology_lockfile": False,
        "accepts_ontology_terms": False,
        "applies_to_specgraph": False,
        "creates_branch_or_commit": False,
        "opens_pull_request": False,
    }


def build_specspace_project_local_ontology_decision_import_preview(
    *,
    decision_state: dict[str, Any] | None,
    review_lane: dict[str, Any] | None,
    decision_state_path: Path | None = None,
    review_lane_path: Path | None = None,
    workspace_id: str | None = None,
) -> dict[str, Any]:
    state = _dict(decision_state)
    lane = _dict(review_lane)
    findings: list[dict[str, Any]] = []
    _validate_contracts(decision_state=state, lane=lane, findings=findings)

    context = _dict(lane.get("context"))
    lane_terms = _lane_terms(lane)
    required_terms = _required_term_keys(lane_terms)
    lane_ref = _relative_ref(review_lane_path)
    accepted_lane_refs = _accepted_review_lane_refs(review_lane_path)
    state_ref = _relative_ref(decision_state_path)
    supported_actions = set(
        _list(_dict(lane.get("review_decision_schema")).get("supported_actions"))
    )
    if not supported_actions:
        supported_actions = SUPPORTED_ACTIONS

    accepted_decisions: list[dict[str, Any]] = []
    non_resolving_decisions: list[dict[str, Any]] = []
    invalid_decisions: list[dict[str, Any]] = []
    seen_terms: set[str] = set()
    invalid_terms: set[str] = set()
    processed_terms: set[str] = set()

    for raw_decision in _list(state.get("decisions")):
        decision = _dict(raw_decision)
        decision_id = _text(decision.get("decision_id"), "unknown_decision")
        field = _first_true(decision, DECISION_FALSE_FIELDS)
        if field is not None:
            invalid_decisions.append(
                {
                    "decision_id": decision_id,
                    "reason": "decision_authority_expanded",
                    "field": field,
                }
            )
            continue
        decision_workspace = _text(decision.get("workspace_id"))
        if workspace_id and decision_workspace != workspace_id:
            if _text(decision.get("term_key")) in required_terms:
                invalid_terms.add(_text(decision.get("term_key")))
            invalid_decisions.append(
                {
                    "decision_id": decision_id,
                    "reason": "workspace_mismatch",
                    "expected": workspace_id,
                    "actual": decision_workspace,
                }
            )
            continue
        context_workspace = _text(context.get("workspace_id"))
        if context_workspace and not decision_workspace:
            if _text(decision.get("term_key")) in required_terms:
                invalid_terms.add(_text(decision.get("term_key")))
            invalid_decisions.append(
                {
                    "decision_id": decision_id,
                    "reason": "workspace_missing",
                    "expected": context_workspace,
                }
            )
            continue
        if context_workspace and decision_workspace != context_workspace:
            if _text(decision.get("term_key")) in required_terms:
                invalid_terms.add(_text(decision.get("term_key")))
            invalid_decisions.append(
                {
                    "decision_id": decision_id,
                    "reason": "lane_workspace_mismatch",
                    "expected": context_workspace,
                    "actual": decision_workspace,
                }
            )
            continue
        candidate_id = _text(decision.get("candidate_id"))
        context_candidate = _text(context.get("candidate_id"))
        if context_candidate and not candidate_id:
            if _text(decision.get("term_key")) in required_terms:
                invalid_terms.add(_text(decision.get("term_key")))
            invalid_decisions.append(
                {
                    "decision_id": decision_id,
                    "reason": "candidate_missing",
                    "expected": context_candidate,
                }
            )
            continue
        if context_candidate and candidate_id != context_candidate:
            if _text(decision.get("term_key")) in required_terms:
                invalid_terms.add(_text(decision.get("term_key")))
            invalid_decisions.append(
                {
                    "decision_id": decision_id,
                    "reason": "candidate_mismatch",
                    "expected": context_candidate,
                    "actual": candidate_id,
                }
            )
            continue
        repair_session_id = _text(decision.get("repair_session_id"))
        context_session = _text(context.get("repair_session_id"))
        if context_session and not repair_session_id:
            if _text(decision.get("term_key")) in required_terms:
                invalid_terms.add(_text(decision.get("term_key")))
            invalid_decisions.append(
                {
                    "decision_id": decision_id,
                    "reason": "repair_session_missing",
                    "expected": context_session,
                }
            )
            continue
        if context_session and repair_session_id != context_session:
            if _text(decision.get("term_key")) in required_terms:
                invalid_terms.add(_text(decision.get("term_key")))
            invalid_decisions.append(
                {
                    "decision_id": decision_id,
                    "reason": "repair_session_mismatch",
                    "expected": context_session,
                    "actual": repair_session_id,
                }
            )
            continue
        decision_lane_ref = _text(decision.get("project_local_ontology_review_lane_ref"))
        if accepted_lane_refs and not decision_lane_ref:
            if _text(decision.get("term_key")) in required_terms:
                invalid_terms.add(_text(decision.get("term_key")))
            invalid_decisions.append(
                {
                    "decision_id": decision_id,
                    "reason": "review_lane_ref_missing",
                    "expected": lane_ref,
                }
            )
            continue
        if accepted_lane_refs and decision_lane_ref not in accepted_lane_refs:
            if _text(decision.get("term_key")) in required_terms:
                invalid_terms.add(_text(decision.get("term_key")))
            invalid_decisions.append(
                {
                    "decision_id": decision_id,
                    "reason": "review_lane_ref_stale",
                    "expected": lane_ref,
                    "actual": decision_lane_ref,
                }
            )
            continue
        term_key = _text(decision.get("term_key"))
        term = lane_terms.get(term_key)
        if term is None:
            invalid_decisions.append(
                {
                    "decision_id": decision_id,
                    "reason": "unknown_project_local_term",
                    "term_key": term_key,
                }
            )
            continue
        if term_key in processed_terms:
            invalid_terms.add(term_key)
            invalid_decisions.append(
                {
                    "decision_id": decision_id,
                    "reason": "duplicate_project_local_term_decision",
                    "term_key": term_key,
                }
            )
            continue
        processed_terms.add(term_key)
        action = _text(decision.get("review_action"))
        allowed_actions = set(_list(term.get("suggested_actions"))) or supported_actions
        if (
            action not in SUPPORTED_ACTIONS
            or action not in supported_actions
            or action not in allowed_actions
        ):
            invalid_decisions.append(
                {
                    "decision_id": decision_id,
                    "reason": "unsupported_or_disallowed_action",
                    "term_key": term_key,
                    "action": action,
                    "allowed_actions": sorted(allowed_actions),
                }
            )
            if term_key in required_terms:
                invalid_terms.add(term_key)
            continue
        value, value_error = _decision_value(
            action=action,
            raw_value=decision.get("decision_value"),
            term=term,
        )
        if value_error is not None:
            invalid_decisions.append(
                {
                    "decision_id": decision_id,
                    "term_key": term_key,
                    "action": action,
                    **value_error,
                }
            )
            if term_key in required_terms:
                invalid_terms.add(term_key)
            continue
        candidate = _candidate_from_decision(
            decision=decision,
            action=action,
            value=value,
            term=term,
            source_ref=state_ref,
        )
        seen_terms.add(term_key)
        if action in NON_RESOLVING_ACTIONS:
            non_resolving_decisions.append(candidate)
        else:
            accepted_decisions.append(candidate)

    missing_decisions = [
        {
            "term_key": term_key,
            "term": _text(lane_terms[term_key].get("term")),
            "status": _text(lane_terms[term_key].get("status"), "unreviewed"),
            "reason": "required_project_local_ontology_decision_missing",
        }
        for term_key in sorted(required_terms - seen_terms - invalid_terms)
    ]

    for invalid in invalid_decisions:
        invalid_key = _text(
            invalid.get("decision_id"),
            _text(invalid.get("term_key"), "unknown"),
        )
        findings.append(
            _finding(
                finding_id=f"project_local_decision_invalid_{_slug(invalid_key)}",
                severity="blocking",
                message="Project-local ontology decision failed import validation.",
                evidence=invalid,
            )
        )
    for missing in missing_decisions:
        missing_key = _text(missing.get("term_key"), "unknown")
        findings.append(
            _finding(
                finding_id=f"project_local_decision_missing_{_slug(missing_key)}",
                severity="blocking",
                message=(
                    "Project-local ontology review requires an operator decision for this term."
                ),
                evidence=missing,
            )
        )
    for decision in non_resolving_decisions:
        deferred_key = _text(decision.get("term_key"), "unknown")
        findings.append(
            _finding(
                finding_id=f"project_local_decision_deferred_{_slug(deferred_key)}",
                severity="review_required",
                message=(
                    "Deferred project-local ontology decision is recorded but does "
                    "not resolve the review lane."
                ),
                evidence={
                    "term_key": decision.get("term_key"),
                    "source_decision_id": decision.get("source_decision_id"),
                },
            )
        )

    blocking_findings = [item for item in findings if _text(item.get("severity")) == "blocking"]
    ready = not blocking_findings and not non_resolving_decisions and bool(state) and bool(lane)
    status = (
        "project_local_ontology_decision_import_ready"
        if ready
        else "project_local_ontology_decision_import_review_required"
    )
    blocked_by = [item["finding_id"] for item in blocking_findings]
    if non_resolving_decisions:
        blocked_by.append("project_local_ontology_decisions_deferred")

    return {
        "artifact_kind": "specspace_project_local_ontology_decision_import_preview",
        "schema_version": SCHEMA_VERSION,
        "proposal_id": PROPOSAL_ID,
        "contract_ref": CONTRACT_REF,
        "generated_at": _now_iso(),
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "readiness": {
            "ready": ready,
            "review_state": status,
            "blocked_by": blocked_by,
            "next_artifact": (
                "project_local_ontology_decisions_for_repair"
                if ready
                else "SpecSpace project-local ontology review decisions"
            ),
        },
        "context": {
            "workspace_id": _text(context.get("workspace_id")),
            "candidate_id": _text(context.get("candidate_id")),
            "repair_session_id": _text(context.get("repair_session_id")),
            "workflow_lane": _text(context.get("workflow_lane")),
            "domain_refs": _list(context.get("domain_refs")),
            "context_refs": _list(context.get("context_refs")),
            "ontology_refs": _list(context.get("ontology_refs")),
        },
        "source_artifacts": {
            "decision_state": _source_artifact("decision_state", state, decision_state_path),
            "project_local_ontology_review_lane": _source_artifact(
                "project_local_ontology_review_lane",
                lane,
                review_lane_path,
            ),
        },
        "import_preview": {
            "accepted_decisions": accepted_decisions,
            "non_resolving_decisions": non_resolving_decisions,
            "invalid_decisions": invalid_decisions,
            "missing_decisions": missing_decisions,
        },
        "decision_candidates": accepted_decisions,
        "authority_boundary": _authority_boundary(),
        "privacy_boundary": _privacy_boundary(),
        "findings": findings,
        "summary": {
            "status": status,
            "workspace_id": _text(context.get("workspace_id")),
            "candidate_id": _text(context.get("candidate_id")),
            "decision_count": len(_list(state.get("decisions"))),
            "accepted_decision_count": len(accepted_decisions),
            "non_resolving_decision_count": len(non_resolving_decisions),
            "invalid_decision_count": len(invalid_decisions),
            "missing_decision_count": len(missing_decisions),
            "finding_count": len(findings),
            "ready": ready,
        },
    }


def _load_optional(path: Path) -> tuple[dict[str, Any], Path | None]:
    if not path.exists():
        return {}, path
    return load_json(path), path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Preview SpecSpace project-local ontology decision import."
    )
    parser.add_argument("--decisions", type=Path, default=DEFAULT_DECISIONS_PATH)
    parser.add_argument("--review-lane", type=Path, default=DEFAULT_LANE_PATH)
    parser.add_argument("--workspace-id")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    decision_state, decision_path = _load_optional(args.decisions)
    review_lane, lane_path = _load_optional(args.review_lane)
    report = build_specspace_project_local_ontology_decision_import_preview(
        decision_state=decision_state,
        review_lane=review_lane,
        decision_state_path=decision_path,
        review_lane_path=lane_path,
        workspace_id=args.workspace_id,
    )
    write_json(report, args.output)
    if args.strict and report["readiness"]["ready"] is not True:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
