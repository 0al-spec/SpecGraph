"""Build the explicit candidate approval decision artifact."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_ID = "0157"
SCHEMA_VERSION = 1
CONTRACT_REF = "specgraph.idea-to-spec.candidate-approval-decision.v0.1"
ACTIVE_CANDIDATE_CONTRACT_REF = "specgraph.idea-to-spec.active-candidate-source.v0.1"
PROMOTION_GATE_CONTRACT_REF = "specgraph.idea-to-spec.promotion-gate.v0.1"
DEFAULT_ACTIVE_CANDIDATE_PATH = ROOT / "runs" / "active_idea_to_spec_candidate.json"
DEFAULT_PROMOTION_GATE_PATH = ROOT / "runs" / "idea_to_spec_promotion_gate.json"
DEFAULT_OUTPUT_PATH = ROOT / "runs" / "candidate_approval_decision.json"
DECISION_STATES = ("approved", "rejected", "needs_context", "superseded")
REVIEW_STATE_BY_DECISION = {
    "approved": "promotion_request_approved",
    "rejected": "candidate_promotion_rejected",
    "needs_context": "candidate_approval_needs_context",
    "superseded": "candidate_superseded",
}
OPERATOR_REF_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:@-]{2,119}$")
PRIVATE_TEXT_MARKERS = (
    "/Users/",
    "/home/",
    "/private/",
    "/tmp/",
    "\\",
    "-----BEGIN",
    "API_KEY",
    "authorization",
    "password",
    "secret",
)


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any, default: str = "") -> str:
    return value.strip() if isinstance(value, str) and value.strip() else default


def _relative_ref(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _sha256(path: Path) -> str:
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
        "source": "candidate_approval_decision",
        "evidence": evidence or {},
    }


def _readiness_ready(artifact: dict[str, Any]) -> bool:
    return _dict(artifact.get("readiness")).get("ready") is True


def _source_artifact(artifact: dict[str, Any], path: Path) -> dict[str, Any]:
    return {
        "artifact_kind": artifact.get("artifact_kind"),
        "contract_ref": artifact.get("contract_ref"),
        "proposal_id": artifact.get("proposal_id"),
        "source_ref": _relative_ref(path),
        "sha256": _sha256(path),
        "readiness": _dict(artifact.get("readiness")),
        "summary": _dict(artifact.get("summary")),
    }


def _authority_boundary() -> dict[str, bool]:
    return {
        "agent_may_recommend": True,
        "agent_may_approve": False,
        "git_service_execution_remains_separate": True,
        "review_merge_required_for_canonical_acceptance": True,
        "read_model_publish_requires_merged_review": True,
        "may_execute_prompt_agent": False,
        "may_mutate_candidate_source_artifacts": False,
        "may_mutate_canonical_specs": False,
        "may_write_ontology_package": False,
        "may_write_ontology_lockfile": False,
        "may_mark_candidate_graph_accepted": False,
        "may_create_branch_or_commit": False,
        "may_open_pull_request": False,
        "may_merge_review": False,
        "may_publish_read_model": False,
    }


def _privacy_boundary() -> dict[str, bool]:
    return {
        "raw_intent_text_published": False,
        "raw_model_output_published": False,
        "raw_operator_note_published": False,
        "raw_prompt_published": False,
        "local_paths_published": False,
    }


def _validate_public_text(
    field: str, value: str, *, required: bool = False
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if required and not value:
        findings.append(
            _finding(
                finding_id=f"{field}_missing",
                severity="review_required",
                message=f"{field} is required for this decision state.",
            )
        )
        return findings
    if not value:
        return findings
    if "\n" in value or "\r" in value or len(value) > 240:
        findings.append(
            _finding(
                finding_id=f"{field}_not_public_safe",
                severity="review_required",
                message=f"{field} must be a single public-safe line no longer than 240 chars.",
            )
        )
    lowered = value.lower()
    if any(marker.lower() in lowered for marker in PRIVATE_TEXT_MARKERS):
        findings.append(
            _finding(
                finding_id=f"{field}_contains_private_marker",
                severity="review_required",
                message=f"{field} must not contain local paths, secrets, or private note markers.",
            )
        )
    return findings


def _validate_active_candidate(
    active_candidate: dict[str, Any],
    *,
    active_candidate_path: Path,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if active_candidate.get("artifact_kind") != "active_idea_to_spec_candidate":
        findings.append(
            _finding(
                finding_id="active_candidate_wrong_artifact_kind",
                severity="review_required",
                message="Approval requires an active_idea_to_spec_candidate artifact.",
                evidence={"artifact_kind": active_candidate.get("artifact_kind")},
            )
        )
    if active_candidate.get("contract_ref") != ACTIVE_CANDIDATE_CONTRACT_REF:
        findings.append(
            _finding(
                finding_id="active_candidate_contract_ref_unsupported",
                severity="review_required",
                message="Approval requires the active candidate source contract.",
                evidence={"contract_ref": active_candidate.get("contract_ref")},
            )
        )
    if active_candidate.get("canonical_mutations_allowed") is not False:
        findings.append(
            _finding(
                finding_id="active_candidate_authority_expanded",
                severity="review_required",
                message="Active candidate source must not allow canonical mutations.",
            )
        )
    if active_candidate.get("tracked_artifacts_written") is not False:
        findings.append(
            _finding(
                finding_id="active_candidate_tracked_write_expanded",
                severity="review_required",
                message="Active candidate source must be review-only.",
            )
        )
    if active_candidate.get("source_mode") != "active_candidate":
        findings.append(
            _finding(
                finding_id="active_candidate_source_mode_unsupported",
                severity="review_required",
                message="Approval requires a real active candidate source.",
                evidence={"source_mode": active_candidate.get("source_mode")},
            )
        )
    if not _readiness_ready(active_candidate):
        findings.append(
            _finding(
                finding_id="active_candidate_not_ready",
                severity="review_required",
                message="Active candidate source must be ready before approval.",
                evidence={"readiness": _dict(active_candidate.get("readiness"))},
            )
        )
    candidate = _dict(active_candidate.get("candidate"))
    expected = {
        "workflow_lane": "product_idea_to_spec",
        "governance_profile": "product_workspace",
        "target_repository_role": "product_spec_workspace",
    }
    for field, expected_value in expected.items():
        observed = candidate.get(field)
        if observed != expected_value:
            findings.append(
                _finding(
                    finding_id=f"active_candidate_{field}_unsupported",
                    severity="review_required",
                    message=f"Approval requires candidate {field}={expected_value!r}.",
                    evidence={"expected": expected_value, "observed": observed},
                )
            )
    if not _text(candidate.get("candidate_id")):
        findings.append(
            _finding(
                finding_id="active_candidate_candidate_id_missing",
                severity="review_required",
                message="Approval requires a stable candidate_id.",
            )
        )
    if not active_candidate_path.is_file():
        findings.append(
            _finding(
                finding_id="active_candidate_source_file_missing",
                severity="review_required",
                message="Active candidate source file is missing.",
                evidence={"path": _relative_ref(active_candidate_path)},
            )
        )
    return findings


def _validate_promotion_gate(
    promotion_gate: dict[str, Any],
    *,
    promotion_gate_path: Path,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if promotion_gate.get("artifact_kind") != "idea_to_spec_promotion_gate":
        findings.append(
            _finding(
                finding_id="promotion_gate_wrong_artifact_kind",
                severity="review_required",
                message="Approval requires an idea_to_spec_promotion_gate artifact.",
                evidence={"artifact_kind": promotion_gate.get("artifact_kind")},
            )
        )
    if promotion_gate.get("contract_ref") != PROMOTION_GATE_CONTRACT_REF:
        findings.append(
            _finding(
                finding_id="promotion_gate_contract_ref_unsupported",
                severity="review_required",
                message="Approval requires the idea-to-spec promotion gate contract.",
                evidence={"contract_ref": promotion_gate.get("contract_ref")},
            )
        )
    if promotion_gate.get("canonical_mutations_allowed") is not False:
        findings.append(
            _finding(
                finding_id="promotion_gate_authority_expanded",
                severity="review_required",
                message="Promotion gate must not allow canonical mutations.",
            )
        )
    if promotion_gate.get("tracked_artifacts_written") is not False:
        findings.append(
            _finding(
                finding_id="promotion_gate_tracked_write_expanded",
                severity="review_required",
                message="Promotion gate must be review-only.",
            )
        )
    if promotion_gate.get("source_mode") == "public_placeholder" or promotion_gate.get(
        "placeholder_reason"
    ):
        findings.append(
            _finding(
                finding_id="promotion_gate_is_public_placeholder",
                severity="review_required",
                message="Approval requires a real promotion gate, not a public placeholder.",
                evidence={
                    "source_mode": promotion_gate.get("source_mode"),
                    "placeholder_reason": promotion_gate.get("placeholder_reason"),
                },
            )
        )
    if not _readiness_ready(promotion_gate):
        findings.append(
            _finding(
                finding_id="promotion_gate_not_ready",
                severity="review_required",
                message="Promotion gate must be ready before approval.",
                evidence={"readiness": _dict(promotion_gate.get("readiness"))},
            )
        )
    paths = _list(_dict(promotion_gate.get("promotion_request")).get("paths"))
    if not paths:
        findings.append(
            _finding(
                finding_id="promotion_gate_paths_missing",
                severity="review_required",
                message="Promotion gate must expose Platform promotion paths before approval.",
            )
        )
    if not promotion_gate_path.is_file():
        findings.append(
            _finding(
                finding_id="promotion_gate_source_file_missing",
                severity="review_required",
                message="Promotion gate file is missing.",
                evidence={"path": _relative_ref(promotion_gate_path)},
            )
        )
    return findings


def _cross_artifact_findings(
    *,
    active_candidate: dict[str, Any],
    promotion_gate_path: Path,
) -> list[dict[str, Any]]:
    source_artifacts = _dict(active_candidate.get("source_artifacts"))
    promotion_ref = _dict(source_artifacts.get("promotion_gate"))
    expected_ref = _relative_ref(promotion_gate_path)
    observed_ref = promotion_ref.get("source_ref")
    if observed_ref and observed_ref != expected_ref:
        return [
            _finding(
                finding_id="promotion_gate_ref_mismatch",
                severity="review_required",
                message="Active candidate source must reference the same promotion gate artifact.",
                evidence={"expected": expected_ref, "observed": observed_ref},
            )
        ]
    return []


def _evidence_refs(
    *,
    active_candidate: dict[str, Any],
    active_candidate_path: Path,
    promotion_gate: dict[str, Any],
    promotion_gate_path: Path,
) -> list[dict[str, Any]]:
    refs = [
        _source_artifact(active_candidate, active_candidate_path),
        _source_artifact(promotion_gate, promotion_gate_path),
    ]
    for artifact_key, artifact_ref in _dict(active_candidate.get("source_artifacts")).items():
        if not isinstance(artifact_ref, dict):
            continue
        refs.append(
            {
                "artifact_key": artifact_key,
                "artifact_kind": artifact_ref.get("artifact_kind"),
                "contract_ref": artifact_ref.get("contract_ref"),
                "proposal_id": artifact_ref.get("proposal_id"),
                "source_ref": artifact_ref.get("source_ref"),
                "sha256": artifact_ref.get("sha256"),
                "readiness": _dict(artifact_ref.get("readiness")),
                "summary": _dict(artifact_ref.get("summary")),
            }
        )
    return refs


def build_candidate_approval_decision(
    *,
    active_candidate: dict[str, Any],
    promotion_gate: dict[str, Any],
    active_candidate_path: Path,
    promotion_gate_path: Path,
    requested_state: str,
    operator_ref: str,
    reason: str,
    conditions: list[str] | None = None,
) -> dict[str, Any]:
    requested = _text(requested_state)
    normalized_operator_ref = _text(operator_ref)
    normalized_reason = _text(reason)
    normalized_conditions = [
        _text(condition) for condition in (conditions or []) if _text(condition)
    ]
    findings: list[dict[str, Any]] = []
    if requested not in DECISION_STATES:
        findings.append(
            _finding(
                finding_id="decision_state_unsupported",
                severity="review_required",
                message="Decision state must be approved, rejected, needs_context, or superseded.",
                evidence={"requested_state": requested_state},
            )
        )
        requested = "needs_context"
    if not OPERATOR_REF_RE.fullmatch(normalized_operator_ref):
        findings.append(
            _finding(
                finding_id="operator_ref_not_public_safe",
                severity="review_required",
                message=(
                    "operator_ref must be a stable public-safe handle, not raw identity text "
                    "or a local path."
                ),
                evidence={"operator_ref": operator_ref},
            )
        )
    reason_required = requested in {"rejected", "needs_context", "superseded"}
    findings.extend(_validate_public_text("reason", normalized_reason, required=reason_required))
    for index, condition in enumerate(normalized_conditions):
        findings.extend(_validate_public_text(f"condition_{index}", condition))
    findings.extend(
        _validate_active_candidate(
            active_candidate,
            active_candidate_path=active_candidate_path,
        )
    )
    findings.extend(
        _validate_promotion_gate(
            promotion_gate,
            promotion_gate_path=promotion_gate_path,
        )
    )
    findings.extend(
        _cross_artifact_findings(
            active_candidate=active_candidate,
            promotion_gate_path=promotion_gate_path,
        )
    )
    effective_state = requested
    if requested == "approved" and findings:
        findings.append(
            _finding(
                finding_id="approval_requested_for_unready_handoff",
                severity="review_required",
                message=(
                    "Approved decisions require ready active candidate and promotion gate inputs."
                ),
                evidence={"finding_count_before_block": len(findings)},
            )
        )
        effective_state = "needs_context"
    approval_ready = effective_state == "approved" and not findings
    blocked_by = [finding["finding_id"] for finding in findings]
    if not approval_ready and not blocked_by:
        blocked_by = [f"decision_{effective_state}"]
    candidate = _dict(active_candidate.get("candidate"))
    promotion_paths = _list(_dict(promotion_gate.get("promotion_request")).get("paths"))
    return {
        "artifact_kind": "candidate_approval_decision",
        "schema_version": SCHEMA_VERSION,
        "proposal_id": PROPOSAL_ID,
        "contract_ref": CONTRACT_REF,
        "generated_at": _now_iso(),
        "canonical_mutations_allowed": False,
        "ontology_writes_allowed": False,
        "tracked_artifacts_written": False,
        "workspace": {
            "workspace_id": candidate.get("candidate_id"),
            "mode": candidate.get("workflow_lane"),
            "repository_role": candidate.get("target_repository_role"),
            "public_route": candidate.get("public_route"),
        },
        "candidate": {
            "candidate_id": candidate.get("candidate_id"),
            "display_name": candidate.get("display_name"),
            "active_candidate_ref": _relative_ref(active_candidate_path),
            "promotion_gate_ref": _relative_ref(promotion_gate_path),
        },
        "decision": {
            "requested_state": requested_state,
            "state": effective_state,
            "approved_transition": "candidate_review_requested -> promotion_request_approved",
            "operator_ref": normalized_operator_ref,
            "reason": normalized_reason,
            "conditions": normalized_conditions,
        },
        "readiness": {
            "ready": approval_ready,
            "review_state": REVIEW_STATE_BY_DECISION[effective_state]
            if not findings
            else "candidate_approval_blocked",
            "blocked_by": blocked_by,
            "next_artifact": "Platform graph-repository promotion-request"
            if approval_ready
            else "operator decision or candidate repair before Git Service execution",
        },
        "promotion_request": {
            "platform_artifact_kind": "platform_graph_repository_promotion_request",
            "path_argument": "--path",
            "paths": promotion_paths if approval_ready else [],
            "requires_git_service_execution": True,
        },
        "source_artifacts": {
            "active_candidate": _source_artifact(active_candidate, active_candidate_path),
            "promotion_gate": _source_artifact(promotion_gate, promotion_gate_path),
        },
        "evidence_refs": _evidence_refs(
            active_candidate=active_candidate,
            active_candidate_path=active_candidate_path,
            promotion_gate=promotion_gate,
            promotion_gate_path=promotion_gate_path,
        ),
        "authority_boundary": _authority_boundary(),
        "privacy_boundary": _privacy_boundary(),
        "findings": findings,
        "warnings": [],
        "summary": {
            "status": REVIEW_STATE_BY_DECISION[effective_state]
            if not findings
            else "candidate_approval_blocked",
            "requested_state": requested_state,
            "effective_state": effective_state,
            "candidate_id": candidate.get("candidate_id"),
            "finding_count": len(findings),
            "warning_count": 0,
            "promotion_path_count": len(promotion_paths) if approval_ready else 0,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--active-candidate", default=DEFAULT_ACTIVE_CANDIDATE_PATH, type=Path)
    parser.add_argument("--promotion-gate", default=DEFAULT_PROMOTION_GATE_PATH, type=Path)
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, type=Path)
    parser.add_argument("--decision", choices=DECISION_STATES, default="needs_context")
    parser.add_argument("--operator-ref", default="local_operator:unattributed")
    parser.add_argument("--reason", default="awaiting explicit operator approval")
    parser.add_argument("--condition", action="append", default=[])
    parser.add_argument("--strict", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    active_candidate = load_json(args.active_candidate)
    promotion_gate = load_json(args.promotion_gate)
    report = build_candidate_approval_decision(
        active_candidate=active_candidate,
        promotion_gate=promotion_gate,
        active_candidate_path=args.active_candidate,
        promotion_gate_path=args.promotion_gate,
        requested_state=args.decision,
        operator_ref=args.operator_ref,
        reason=args.reason,
        conditions=args.condition,
    )
    write_json(report, args.output)
    print(
        f"{report['readiness']['review_state']}: "
        f"{report['summary']['promotion_path_count']} promotion paths"
    )
    if args.strict and not report["readiness"]["ready"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
