"""Summarize project-local ontology decisions as review-only maturity evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_ID = "0199"
SCHEMA_VERSION = 1
CONTRACT_REF = "specgraph.product-ontology.project-local-decision-effect.v0.1"

LANE_KIND = "project_local_ontology_review_lane"
IMPORT_PREVIEW_KIND = "specspace_project_local_ontology_decision_import_preview"

DEFAULT_REVIEW_LANE_PATH = ROOT / "runs" / "project_local_ontology_review_lane.json"
DEFAULT_IMPORT_PREVIEW_PATH = (
    ROOT / "runs" / "specspace_project_local_ontology_decision_import_preview.json"
)
DEFAULT_OUTPUT_PATH = ROOT / "runs" / "project_local_ontology_decision_effect_report.json"

REVIEW_ACTIONS = (
    "keep_project_local",
    "bind_existing",
    "alias",
    "reject",
    "request_workspace_promotion",
    "defer",
)

FALSE_AUTHORITY_FIELDS = (
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

PRIVATE_PATH_MARKERS = ("/Users/", "/home/", "/private/", "/tmp/")
PRIVATE_VALUE_MARKERS = ("-----BEGIN", "api-key", "apikey", "api_key", "bearer ", "token=")


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any, default: str = "") -> str:
    return value.strip() if isinstance(value, str) and value.strip() else default


def _id_part(value: Any) -> str:
    text = _text(value, "unknown").lower()
    normalized = "".join(char if char.isalnum() else "-" for char in text)
    return "-".join(part for part in normalized.split("-") if part) or "unknown"


def _int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _repo_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def _relative_ref(path: Path | None) -> str | None:
    if path is None:
        return None
    repo_path = _repo_path(path)
    try:
        return repo_path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return f"external:{repo_path.name or 'artifact'}"


def _sha256(path: Path | None) -> str | None:
    if path is None:
        return None
    repo_path = _repo_path(path)
    if not repo_path.exists():
        return None
    digest = hashlib.sha256()
    with repo_path.open("rb") as file_obj:
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
    payload = json.loads(_repo_path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def write_json(payload: dict[str, Any], path: Path) -> None:
    output_path = _repo_path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_optional(path: Path | None) -> tuple[dict[str, Any], Path | None, str | None]:
    if path is None or not _repo_path(path).exists():
        return {}, None, None
    try:
        return load_json(path), path, None
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {}, path, str(exc)


def _source_artifact(
    key: str, payload: dict[str, Any], path: Path | None, error: str | None
) -> dict[str, Any]:
    status = "malformed" if error else ("present" if payload else "missing")
    result = {
        "artifact_key": key,
        "artifact_kind": payload.get("artifact_kind") if payload else None,
        "contract_ref": payload.get("contract_ref") if payload else None,
        "schema_version": payload.get("schema_version") if payload else None,
        "source_ref": _relative_ref(path),
        "sha256": _sha256(path),
        "status": status,
    }
    if error:
        result["error"] = error
    if payload:
        result["summary"] = _public_safe(_dict(payload.get("summary")))
        result["readiness"] = _public_safe(_dict(payload.get("readiness")))
    return result


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
        "source": "project_local_ontology_decision_effect_report",
        "message": message,
        "evidence": _public_safe(evidence or {}),
    }


def _authority_boundary() -> dict[str, bool]:
    return {key: False for key in FALSE_AUTHORITY_FIELDS}


def _privacy_boundary() -> dict[str, bool]:
    return {
        "raw_idea_text_published": False,
        "raw_prompt_published": False,
        "raw_model_output_published": False,
        "raw_operator_note_published": False,
        "private_operator_state_published": False,
    }


def _true_authority_fields(payload: dict[str, Any], *, prefix: str = "") -> list[str]:
    fields: list[str] = []
    for field in FALSE_AUTHORITY_FIELDS:
        if payload.get(field) is True:
            fields.append(f"{prefix}{field}")
    boundary = _dict(payload.get("authority_boundary"))
    for field in FALSE_AUTHORITY_FIELDS:
        if boundary.get(field) is True:
            fields.append(f"{prefix}authority_boundary.{field}")
    return fields


def _count_actions(decisions: list[dict[str, Any]]) -> dict[str, int]:
    counts = {action: 0 for action in REVIEW_ACTIONS}
    for decision in decisions:
        action = _text(decision.get("review_action"))
        if action in counts:
            counts[action] += 1
    return counts


def _decision_effects(decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    effects: list[dict[str, Any]] = []
    for decision in decisions:
        action = _text(decision.get("review_action"), "unknown")
        effects.append(
            {
                "id": _text(decision.get("id")),
                "source_decision_id": _text(decision.get("source_decision_id")),
                "term": _text(decision.get("term")),
                "term_key": _text(decision.get("term_key")),
                "review_action": action,
                "decision_type": _text(decision.get("decision_type")),
                "status": _text(decision.get("status")),
                "effect_kind": (
                    "project_local_review_evidence"
                    if action in {"keep_project_local", "bind_existing", "alias", "reject"}
                    else "project_local_promotion_follow_up"
                    if action == "request_workspace_promotion"
                    else "non_resolving"
                ),
                "maturity_effect": (
                    "resolves_project_local_review"
                    if action in {"keep_project_local", "bind_existing", "alias", "reject"}
                    else "records_follow_up_without_blocking_current_candidate"
                    if action == "request_workspace_promotion"
                    else "requires_owner_follow_up"
                ),
                "evidence_refs": [
                    ref
                    for ref in (
                        _text(decision.get("source_artifact")),
                        _text(decision.get("target_ref")),
                    )
                    if ref
                ],
                "gap_refs": _public_safe(_list(decision.get("gap_refs"))),
                "writes_ontology_package": False,
                "accepts_ontology_terms": False,
                "canonical_mutations_allowed": False,
            }
        )
    return effects


def build_project_local_ontology_decision_effect_report(
    *,
    review_lane: dict[str, Any] | None,
    import_preview: dict[str, Any] | None,
    review_lane_path: Path | None = None,
    import_preview_path: Path | None = None,
    review_lane_error: str | None = None,
    import_preview_error: str | None = None,
) -> dict[str, Any]:
    lane = _dict(review_lane)
    preview = _dict(import_preview)
    findings: list[dict[str, Any]] = []

    if not lane:
        findings.append(
            _finding(
                finding_id="project_local_ontology_review_lane_missing",
                severity="review_required",
                message="Project-local ontology review lane is not available.",
            )
        )
    elif lane.get("artifact_kind") != LANE_KIND:
        findings.append(
            _finding(
                finding_id="project_local_ontology_review_lane_kind_mismatch",
                severity="blocking",
                message="Project-local ontology review lane has unexpected artifact_kind.",
                evidence={"artifact_kind": lane.get("artifact_kind")},
            )
        )
    if not preview:
        findings.append(
            _finding(
                finding_id="project_local_ontology_import_preview_missing",
                severity="review_required",
                message=(
                    "SpecSpace project-local ontology decision import preview is not available."
                ),
            )
        )
    elif preview.get("artifact_kind") != IMPORT_PREVIEW_KIND:
        findings.append(
            _finding(
                finding_id="project_local_ontology_import_preview_kind_mismatch",
                severity="blocking",
                message=(
                    "Project-local ontology decision import preview has unexpected artifact_kind."
                ),
                evidence={"artifact_kind": preview.get("artifact_kind")},
            )
        )

    for field in _true_authority_fields(lane, prefix="review_lane."):
        findings.append(
            _finding(
                finding_id="project_local_ontology_review_lane_authority_expanded",
                severity="blocking",
                message="Project-local ontology review lane cannot claim mutation authority.",
                evidence={"field": field},
            )
        )
    for field in _true_authority_fields(preview, prefix="import_preview."):
        findings.append(
            _finding(
                finding_id="project_local_ontology_import_preview_authority_expanded",
                severity="blocking",
                message=(
                    "Project-local ontology decision import preview cannot claim "
                    "mutation authority."
                ),
                evidence={"field": field},
            )
        )

    context = _dict(preview.get("context")) or _dict(lane.get("context"))
    accepted = [
        item
        for item in _list(_dict(preview.get("import_preview")).get("accepted_decisions"))
        if isinstance(item, dict)
    ]
    non_resolving = [
        item
        for item in _list(_dict(preview.get("import_preview")).get("non_resolving_decisions"))
        if isinstance(item, dict)
    ]
    invalid = [
        item
        for item in _list(_dict(preview.get("import_preview")).get("invalid_decisions"))
        if isinstance(item, dict)
    ]
    missing = [
        item
        for item in _list(_dict(preview.get("import_preview")).get("missing_decisions"))
        if isinstance(item, dict)
    ]

    action_counts = _count_actions(accepted)
    non_resolving_action_counts = _count_actions(non_resolving)
    effects = _decision_effects(accepted)
    effects.extend(_decision_effects(non_resolving))

    for item in invalid:
        decision_ref = _id_part(item.get("decision_id") or item.get("term_key"))
        findings.append(
            _finding(
                finding_id=f"project_local_ontology_decision_invalid_{decision_ref}",
                severity="blocking",
                message="Invalid project-local ontology decision blocks maturity evidence.",
                evidence=item,
            )
        )
    for item in missing:
        term_ref = _id_part(item.get("term_key"))
        findings.append(
            _finding(
                finding_id=f"project_local_ontology_decision_missing_{term_ref}",
                severity="blocking",
                message="Missing project-local ontology decision blocks maturity evidence.",
                evidence=item,
            )
        )
    for item in non_resolving:
        term_ref = _id_part(item.get("term_key"))
        findings.append(
            _finding(
                finding_id=f"project_local_ontology_decision_non_resolving_{term_ref}",
                severity="review_required",
                message="Non-resolving project-local ontology decision needs follow-up.",
                evidence={
                    "term_key": item.get("term_key"),
                    "review_action": item.get("review_action"),
                    "source_decision_id": item.get("source_decision_id"),
                },
            )
        )

    blocking = [item for item in findings if _text(item.get("severity")) == "blocking"]
    ready = bool(preview) and bool(lane) and not blocking and not non_resolving
    status = (
        "project_local_ontology_decision_effect_ready"
        if ready
        else "project_local_ontology_decision_effect_review_required"
    )

    accepted_count = len(accepted)
    missing_count = len(missing)
    invalid_count = len(invalid)
    non_resolving_count = len(non_resolving)
    request_promotion_count = action_counts["request_workspace_promotion"]
    summary = {
        "status": status,
        "workspace_id": _text(context.get("workspace_id")),
        "candidate_id": _text(context.get("candidate_id")),
        "repair_session_id": _text(context.get("repair_session_id")),
        "review_status": status,
        "accepted_decision_count": accepted_count,
        "maturity_evidence_decision_count": accepted_count,
        "keep_project_local_count": action_counts["keep_project_local"],
        "bind_existing_count": action_counts["bind_existing"],
        "alias_count": action_counts["alias"],
        "request_promotion_count": request_promotion_count,
        "reject_count": action_counts["reject"],
        "deferred_count": non_resolving_action_counts["defer"],
        "non_resolving_decision_count": non_resolving_count,
        "invalid_decision_count": invalid_count,
        "missing_decision_count": missing_count,
        "blocking_decision_count": invalid_count + missing_count,
        "follow_up_decision_count": request_promotion_count + non_resolving_count,
        "effect_count": len(effects),
        "ready_for_maturity": ready,
    }

    return {
        "artifact_kind": "project_local_ontology_decision_effect_report",
        "schema_version": SCHEMA_VERSION,
        "proposal_id": PROPOSAL_ID,
        "contract_ref": CONTRACT_REF,
        "generated_at": _now_iso(),
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
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
            "project_local_ontology_review_lane": _source_artifact(
                "project_local_ontology_review_lane",
                lane,
                review_lane_path,
                review_lane_error,
            ),
            "specspace_project_local_ontology_decision_import_preview": _source_artifact(
                "specspace_project_local_ontology_decision_import_preview",
                preview,
                import_preview_path,
                import_preview_error,
            ),
        },
        "decision_effects": effects,
        "project_local_ontology_review": {
            **summary,
            "evidence_refs": sorted(
                {
                    ref
                    for effect in effects
                    for ref in _list(effect.get("evidence_refs"))
                    if isinstance(ref, str) and ref
                }
            ),
        },
        "findings": findings,
        "readiness": {
            "ready": ready,
            "review_state": status,
            "blocked_by": [item["finding_id"] for item in blocking],
            "next_artifact": (
                "idea_maturity_metrics_report"
                if ready
                else "SpecSpace project-local ontology review decisions"
            ),
        },
        "authority_boundary": _authority_boundary(),
        "privacy_boundary": _privacy_boundary(),
        "summary": summary,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review-lane", type=Path, default=DEFAULT_REVIEW_LANE_PATH)
    parser.add_argument("--import-preview", type=Path, default=DEFAULT_IMPORT_PREVIEW_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    lane, lane_path, lane_error = _load_optional(args.review_lane)
    preview, preview_path, preview_error = _load_optional(args.import_preview)
    report = build_project_local_ontology_decision_effect_report(
        review_lane=lane,
        import_preview=preview,
        review_lane_path=lane_path,
        import_preview_path=preview_path,
        review_lane_error=lane_error,
        import_preview_error=preview_error,
    )
    write_json(report, args.output)
    if args.strict and not report["readiness"]["ready"]:
        print(
            f"project-local ontology decision effect not ready; wrote {_relative_ref(args.output)}",
            flush=True,
        )
        return 1
    print(
        f"wrote {_relative_ref(args.output)} status={report['summary']['status']} "
        f"accepted={report['summary']['accepted_decision_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
