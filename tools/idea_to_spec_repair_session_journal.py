"""Build a durable review-only journal for an idea-to-spec repair session."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_ID = "0171"
SCHEMA_VERSION = 1
CONTRACT_REF = "specgraph.idea-to-spec.repair-session-journal.v0.1"

DEFAULT_ACTIVE_CANDIDATE_PATH = ROOT / "runs" / "active_idea_to_spec_candidate.json"
DEFAULT_CLARIFICATION_REQUESTS_PATH = ROOT / "runs" / "idea_to_spec_clarification_requests.json"
DEFAULT_CLARIFICATION_ANSWERS_PATH = ROOT / "runs" / "idea_to_spec_clarification_answers.json"
DEFAULT_ONTOLOGY_DECISIONS_PATH = ROOT / "runs" / "product_ontology_gap_review_decisions.json"
DEFAULT_RERUN_INPUT_PATH = ROOT / "runs" / "idea_to_spec_answer_rerun_input.json"
DEFAULT_RERUN_PREVIEW_PATH = ROOT / "runs" / "idea_to_spec_rerun_preview.json"
DEFAULT_RERUN_MATERIALIZATION_PATH = ROOT / "runs" / "idea_to_spec_rerun_materialization.json"
DEFAULT_PROMOTION_GATE_PATH = ROOT / "runs" / "idea_to_spec_promotion_gate.json"
DEFAULT_OUTPUT_PATH = ROOT / "runs" / "idea_to_spec_repair_session.json"

EXPECTED_ARTIFACTS = {
    "active_candidate": (
        "active_idea_to_spec_candidate",
        "specgraph.idea-to-spec.active-candidate-source.v0.1",
    ),
    "clarification_requests": (
        "idea_to_spec_clarification_requests",
        "specgraph.idea-to-spec.clarification-requests.v0.1",
    ),
    "clarification_answers": (
        "idea_to_spec_clarification_answers",
        "specgraph.idea-to-spec.clarification-answers.v0.1",
    ),
    "ontology_decisions": (
        "product_ontology_gap_review_decisions",
        "specgraph.product-ontology.gap-review-decisions.v0.1",
    ),
    "rerun_input": (
        "idea_to_spec_answer_rerun_input",
        "specgraph.idea-to-spec.answer-rerun-input.v0.1",
    ),
    "rerun_preview": (
        "idea_to_spec_rerun_preview",
        "specgraph.idea-to-spec.rerun-preview.v0.1",
    ),
    "rerun_materialization": (
        "idea_to_spec_rerun_materialization",
        "specgraph.idea-to-spec.rerun-materialization.v0.1",
    ),
    "promotion_gate": (
        "idea_to_spec_promotion_gate",
        "specgraph.idea-to-spec.promotion-gate.v0.1",
    ),
}

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


def _relative_ref(path: Path) -> str:
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
        "source": "idea_to_spec_repair_session_journal",
        "evidence": evidence or {},
    }


def _authority_boundary() -> dict[str, bool]:
    return {
        "may_execute_prompt_agent": False,
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


def _source_artifact(
    *,
    key: str,
    artifact: dict[str, Any],
    path: Path | None,
) -> dict[str, Any]:
    readiness = _dict(artifact.get("readiness"))
    summary = _dict(artifact.get("summary"))
    return {
        "artifact_key": key,
        "artifact_kind": artifact.get("artifact_kind"),
        "contract_ref": artifact.get("contract_ref"),
        "proposal_id": artifact.get("proposal_id"),
        "schema_version": artifact.get("schema_version"),
        "source_ref": _relative_ref(path) if path else f"inline:{key}",
        "sha256": _sha256(path),
        "readiness": _public_safe(readiness),
        "summary": _public_safe(summary),
        "status": summary.get("status") or readiness.get("review_state"),
    }


def _validate_artifact(
    *,
    key: str,
    artifact: dict[str, Any],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    expected_kind, expected_contract = EXPECTED_ARTIFACTS[key]
    if artifact.get("artifact_kind") != expected_kind:
        findings.append(
            _finding(
                finding_id=f"{key}_wrong_artifact_kind",
                severity="review_required",
                message=f"{key} must use artifact_kind {expected_kind}.",
                evidence={"artifact_kind": artifact.get("artifact_kind")},
            )
        )
    if artifact.get("contract_ref") != expected_contract:
        findings.append(
            _finding(
                finding_id=f"{key}_contract_ref_unsupported",
                severity="review_required",
                message=f"{key} contract_ref must be {expected_contract}.",
                evidence={"contract_ref": artifact.get("contract_ref")},
            )
        )
    if artifact.get("schema_version") != SCHEMA_VERSION:
        findings.append(
            _finding(
                finding_id=f"{key}_schema_version_unsupported",
                severity="review_required",
                message=f"{key} schema_version must be 1.",
                evidence={"schema_version": artifact.get("schema_version")},
            )
        )
    for field in ("canonical_mutations_allowed", "tracked_artifacts_written"):
        if artifact.get(field) is not False:
            findings.append(
                _finding(
                    finding_id=f"{key}_authority_expanded",
                    severity="review_required",
                    message=f"{key} {field} must be false.",
                    evidence={field: artifact.get(field)},
                )
            )
    boundary = artifact.get("authority_boundary")
    if not isinstance(boundary, dict) or not boundary:
        findings.append(
            _finding(
                finding_id=f"{key}_authority_boundary_missing",
                severity="review_required",
                message=f"{key} must declare an explicit review-only authority_boundary.",
                evidence={"authority_boundary": boundary},
            )
        )
        boundary = {}
    for boundary_field, value in boundary.items():
        if value is True:
            findings.append(
                _finding(
                    finding_id=f"{key}_authority_boundary_expanded",
                    severity="review_required",
                    message=f"{key} authority boundary must remain review-only.",
                    evidence={boundary_field: value},
                )
            )
    return findings


def _source_ref_mismatch_findings(
    *,
    artifacts: dict[str, dict[str, Any]],
    paths: dict[str, Path],
) -> list[dict[str, Any]]:
    expected_refs = {key: _relative_ref(path) for key, path in paths.items()}
    checks = (
        (
            "active_candidate",
            ("source_artifacts", "promotion_gate", "source_ref"),
            "promotion_gate",
        ),
        (
            "active_candidate",
            ("platform_handoff_surfaces", "idea_to_spec_promotion_gate.json", "source_ref"),
            "promotion_gate",
        ),
        (
            "clarification_answers",
            ("source_artifacts", "clarification_requests", "source_ref"),
            "clarification_requests",
        ),
        (
            "ontology_decisions",
            ("source_artifacts", "clarification_answers", "source_ref"),
            "clarification_answers",
        ),
        (
            "rerun_input",
            ("source_artifacts", "clarification_answers", "source_ref"),
            "clarification_answers",
        ),
        (
            "rerun_input",
            ("source_artifacts", "product_ontology_gap_review_decisions", "source_ref"),
            "ontology_decisions",
        ),
        (
            "rerun_preview",
            ("source_artifacts", "rerun_input", "source_ref"),
            "rerun_input",
        ),
        (
            "rerun_materialization",
            ("source_artifacts", "rerun_preview", "source_ref"),
            "rerun_preview",
        ),
    )
    findings: list[dict[str, Any]] = []
    for artifact_key, field_path, expected_key in checks:
        cursor: Any = artifacts.get(artifact_key, {})
        for field in field_path:
            cursor = _dict(cursor).get(field)
        actual_ref = _text(cursor)
        expected_ref = expected_refs.get(expected_key)
        if expected_ref and not actual_ref:
            findings.append(
                _finding(
                    finding_id=f"{artifact_key}_{expected_key}_source_ref_missing",
                    severity="review_required",
                    message=(
                        f"{artifact_key} must declare a source ref for {expected_key} "
                        "so the journal can prove the repair chain."
                    ),
                    evidence={"expected": expected_ref},
                )
            )
        elif actual_ref and expected_ref and actual_ref != expected_ref:
            findings.append(
                _finding(
                    finding_id=f"{artifact_key}_{expected_key}_source_ref_mismatch",
                    severity="review_required",
                    message=(
                        f"{artifact_key} source ref for {expected_key} must match "
                        "the journal input path."
                    ),
                    evidence={"actual": actual_ref, "expected": expected_ref},
                )
            )
    return findings


def _accepted_answers(answers: dict[str, Any]) -> list[dict[str, Any]]:
    accepted_statuses = {"accepted_for_candidate", "accepted_for_review"}
    rows: list[dict[str, Any]] = []
    for raw_answer in _list(answers.get("answers")):
        answer = _dict(raw_answer)
        if _text(answer.get("status")) in accepted_statuses:
            rows.append(
                _public_safe(
                    {
                        "request_id": answer.get("request_id"),
                        "answer_kind": answer.get("answer_kind"),
                        "status": answer.get("status"),
                        "target_artifact": _dict(answer.get("request_snapshot")).get(
                            "target_artifact"
                        ),
                        "target_ref": _dict(answer.get("request_snapshot")).get("target_ref"),
                        "request_kind": _dict(answer.get("request_snapshot")).get("kind"),
                        "value": answer.get("value"),
                    }
                )
            )
    return rows


def _ontology_decisions(decisions_report: dict[str, Any]) -> list[dict[str, Any]]:
    return [_public_safe(_dict(decision)) for decision in _list(decisions_report.get("decisions"))]


def _stage_records(source_artifacts: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    order = (
        "active_candidate",
        "clarification_requests",
        "clarification_answers",
        "ontology_decisions",
        "rerun_input",
        "rerun_preview",
        "rerun_materialization",
        "promotion_gate",
    )
    stages: list[dict[str, Any]] = []
    for index, key in enumerate(order, start=1):
        source = source_artifacts[key]
        readiness = _dict(source.get("readiness"))
        summary = _dict(source.get("summary"))
        stages.append(
            {
                "index": index,
                "stage": key,
                "artifact_kind": source.get("artifact_kind"),
                "source_ref": source.get("source_ref"),
                "ready": readiness.get("ready"),
                "review_state": readiness.get("review_state"),
                "blocked_by": _list(readiness.get("blocked_by")),
                "status": summary.get("status") or readiness.get("review_state"),
                "next_artifact": readiness.get("next_artifact"),
            }
        )
    return stages


def _readiness_impact(
    *,
    active_candidate: dict[str, Any],
    clarification_requests: dict[str, Any],
    clarification_answers: dict[str, Any],
    ontology_decisions: dict[str, Any],
    rerun_input: dict[str, Any],
    rerun_preview: dict[str, Any],
    rerun_materialization: dict[str, Any],
    promotion_gate: dict[str, Any],
) -> dict[str, Any]:
    active_readiness = _dict(active_candidate.get("readiness"))
    answers_readiness = _dict(clarification_answers.get("readiness"))
    ontology_readiness = _dict(ontology_decisions.get("readiness"))
    rerun_input_readiness = _dict(rerun_input.get("readiness"))
    preview_readiness = _dict(rerun_preview.get("readiness"))
    materialization_readiness = _dict(rerun_materialization.get("readiness"))
    promotion_readiness = _dict(promotion_gate.get("readiness"))
    requests_summary = _dict(clarification_requests.get("summary"))
    answers_summary = _dict(clarification_answers.get("summary"))
    ontology_summary = _dict(ontology_decisions.get("summary"))
    preview_summary = _dict(rerun_preview.get("summary"))
    materialization_summary = _dict(rerun_materialization.get("summary"))

    unresolved_ontology_gap_count = _int(
        materialization_summary.get(
            "unresolved_ontology_gap_count",
            preview_summary.get("unresolved_ontology_gap_count", 0),
        )
        or 0
    )
    resolved_ontology_gap_count = _int(
        materialization_summary.get(
            "resolved_ontology_gap_count",
            preview_summary.get("resolved_ontology_gap_count", 0),
        )
        or 0
    )
    blocking_request_count = _int(requests_summary.get("blocking_request_count") or 0)
    unresolved_blocking_count = _int(answers_summary.get("unresolved_blocking_count") or 0)

    blockers: list[str] = []
    blockers.extend(str(item) for item in _list(active_readiness.get("blocked_by")))
    blockers.extend(str(item) for item in _list(promotion_readiness.get("blocked_by")))
    intermediate_readiness = {
        "clarification_answers": answers_readiness,
        "ontology_decisions": ontology_readiness,
        "rerun_input": rerun_input_readiness,
        "rerun_preview": preview_readiness,
        "rerun_materialization": materialization_readiness,
    }
    for artifact_key, readiness in intermediate_readiness.items():
        if readiness.get("ready") is not True:
            blockers.append(f"{artifact_key}_not_ready")
            blockers.extend(str(item) for item in _list(readiness.get("blocked_by")))
    if unresolved_ontology_gap_count:
        blockers.append("unresolved_ontology_gaps")
    if unresolved_blocking_count:
        blockers.append("unresolved_clarification_answers")
    blockers = sorted({item for item in blockers if item})

    intermediate_artifacts_ready = all(
        readiness.get("ready") is True for readiness in intermediate_readiness.values()
    )
    ready_for_candidate_approval = (
        active_readiness.get("ready") is True
        and promotion_readiness.get("ready") is True
        and intermediate_artifacts_ready
        and unresolved_ontology_gap_count == 0
        and unresolved_blocking_count == 0
    )
    platform_promotion_blockers = (
        ["candidate_approval_decision_missing"]
        if ready_for_candidate_approval
        else ["candidate_not_ready_for_approval"]
    )
    return {
        "ready_for_candidate_approval": ready_for_candidate_approval,
        "ready_for_platform_promotion": False,
        "platform_promotion_blocked_by": platform_promotion_blockers,
        "intermediate_artifacts_ready": intermediate_artifacts_ready,
        "blocked_by": blockers,
        "active_candidate_review_state": active_readiness.get("review_state"),
        "promotion_gate_review_state": promotion_readiness.get("review_state"),
        "clarification_request_count": requests_summary.get("request_count", 0),
        "blocking_request_count": blocking_request_count,
        "accepted_answer_count": answers_summary.get("accepted_answer_count", 0),
        "unresolved_blocking_count": unresolved_blocking_count,
        "ontology_decision_count": ontology_summary.get("decision_count", 0),
        "resolved_ontology_gap_count": resolved_ontology_gap_count,
        "unresolved_ontology_gap_count": unresolved_ontology_gap_count,
        "rerun_removed_gap_count": materialization_summary.get("removed_gap_count", 0),
        "candidate_quality_review_state": preview_summary.get("candidate_quality_review_state"),
        "promotion_path_count": _dict(promotion_gate.get("summary")).get("promotion_path_count", 0),
    }


def build_idea_to_spec_repair_session_journal(
    *,
    active_candidate: dict[str, Any],
    clarification_requests: dict[str, Any],
    clarification_answers: dict[str, Any],
    ontology_decisions: dict[str, Any],
    rerun_input: dict[str, Any],
    rerun_preview: dict[str, Any],
    rerun_materialization: dict[str, Any],
    promotion_gate: dict[str, Any],
    active_candidate_path: Path | None = None,
    clarification_requests_path: Path | None = None,
    clarification_answers_path: Path | None = None,
    ontology_decisions_path: Path | None = None,
    rerun_input_path: Path | None = None,
    rerun_preview_path: Path | None = None,
    rerun_materialization_path: Path | None = None,
    promotion_gate_path: Path | None = None,
    session_id: str | None = None,
    operator_ref: str = "local_operator:unattributed",
) -> dict[str, Any]:
    artifacts = {
        "active_candidate": active_candidate,
        "clarification_requests": clarification_requests,
        "clarification_answers": clarification_answers,
        "ontology_decisions": ontology_decisions,
        "rerun_input": rerun_input,
        "rerun_preview": rerun_preview,
        "rerun_materialization": rerun_materialization,
        "promotion_gate": promotion_gate,
    }
    paths = {
        "active_candidate": active_candidate_path,
        "clarification_requests": clarification_requests_path,
        "clarification_answers": clarification_answers_path,
        "ontology_decisions": ontology_decisions_path,
        "rerun_input": rerun_input_path,
        "rerun_preview": rerun_preview_path,
        "rerun_materialization": rerun_materialization_path,
        "promotion_gate": promotion_gate_path,
    }

    findings: list[dict[str, Any]] = []
    for key, artifact in artifacts.items():
        findings.extend(_validate_artifact(key=key, artifact=artifact))
    findings.extend(
        _source_ref_mismatch_findings(
            artifacts=artifacts,
            paths={key: path for key, path in paths.items() if path is not None},
        )
    )

    source_artifacts = {
        key: _source_artifact(key=key, artifact=artifact, path=paths[key])
        for key, artifact in artifacts.items()
    }
    candidate = _dict(active_candidate.get("candidate"))
    candidate_id = _text(candidate.get("candidate_id"), "unknown-candidate")
    effective_session_id = _text(session_id, f"repair-session.{candidate_id}")
    accepted_answers = _accepted_answers(clarification_answers)
    decisions = _ontology_decisions(ontology_decisions)
    readiness_impact = _readiness_impact(
        active_candidate=active_candidate,
        clarification_requests=clarification_requests,
        clarification_answers=clarification_answers,
        ontology_decisions=ontology_decisions,
        rerun_input=rerun_input,
        rerun_preview=rerun_preview,
        rerun_materialization=rerun_materialization,
        promotion_gate=promotion_gate,
    )
    ready = not findings
    return {
        "artifact_kind": "idea_to_spec_repair_session_journal",
        "schema_version": SCHEMA_VERSION,
        "proposal_id": PROPOSAL_ID,
        "contract_ref": CONTRACT_REF,
        "generated_at": _now_iso(),
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "session": {
            "session_id": effective_session_id,
            "candidate_id": candidate_id,
            "workspace_route": candidate.get("public_route"),
            "workflow_lane": candidate.get("workflow_lane"),
            "governance_profile": candidate.get("governance_profile"),
            "target_repository_role": candidate.get("target_repository_role"),
            "operator_ref": _text(operator_ref, "local_operator:unattributed"),
        },
        "source_artifacts": source_artifacts,
        "workflow_journal": {
            "stages": _stage_records(source_artifacts),
            "accepted_answers": accepted_answers,
            "ontology_decisions": decisions,
            "rerun_overlay_refs": {
                "source_ref": source_artifacts["rerun_input"]["source_ref"],
                "summary": source_artifacts["rerun_input"]["summary"],
            },
            "preview_refs": {
                "rerun_preview": {
                    "source_ref": source_artifacts["rerun_preview"]["source_ref"],
                    "summary": source_artifacts["rerun_preview"]["summary"],
                },
                "rerun_materialization": {
                    "source_ref": source_artifacts["rerun_materialization"]["source_ref"],
                    "summary": source_artifacts["rerun_materialization"]["summary"],
                },
            },
        },
        "readiness_impact": readiness_impact,
        "readiness": {
            "ready": ready,
            "review_state": (
                "repair_session_journal_ready"
                if ready
                else "repair_session_journal_review_required"
            ),
            "blocked_by": [finding["finding_id"] for finding in findings],
            "next_artifact": (
                "SpecSpace product repair workspace"
                if ready
                else "repair invalid repair-session journal inputs"
            ),
        },
        "authority_boundary": _authority_boundary(),
        "privacy_boundary": {
            "redaction_enforced_by": "recursive_public_safe_field_filter",
            "static_flags_are_asserted_invariants": True,
            "raw_idea_text_published": False,
            "raw_prompt_published": False,
            "raw_model_output_published": False,
            "raw_operator_note_published": False,
        },
        "findings": findings,
        "summary": {
            "status": (
                "repair_session_journal_ready"
                if ready
                else "repair_session_journal_review_required"
            ),
            "candidate_id": candidate_id,
            "workflow_lane": candidate.get("workflow_lane"),
            "source_artifact_count": len(source_artifacts),
            "accepted_answer_count": len(accepted_answers),
            "ontology_decision_count": len(decisions),
            "resolved_ontology_gap_count": readiness_impact["resolved_ontology_gap_count"],
            "unresolved_ontology_gap_count": readiness_impact["unresolved_ontology_gap_count"],
            "ready_for_candidate_approval": readiness_impact["ready_for_candidate_approval"],
            "finding_count": len(findings),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--active-candidate", default=DEFAULT_ACTIVE_CANDIDATE_PATH, type=Path)
    parser.add_argument(
        "--clarification-requests",
        default=DEFAULT_CLARIFICATION_REQUESTS_PATH,
        type=Path,
    )
    parser.add_argument(
        "--clarification-answers",
        default=DEFAULT_CLARIFICATION_ANSWERS_PATH,
        type=Path,
    )
    parser.add_argument("--ontology-decisions", default=DEFAULT_ONTOLOGY_DECISIONS_PATH, type=Path)
    parser.add_argument("--rerun-input", default=DEFAULT_RERUN_INPUT_PATH, type=Path)
    parser.add_argument("--rerun-preview", default=DEFAULT_RERUN_PREVIEW_PATH, type=Path)
    parser.add_argument(
        "--rerun-materialization",
        default=DEFAULT_RERUN_MATERIALIZATION_PATH,
        type=Path,
    )
    parser.add_argument("--promotion-gate", default=DEFAULT_PROMOTION_GATE_PATH, type=Path)
    parser.add_argument("--session-id")
    parser.add_argument("--operator-ref", default="local_operator:unattributed")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, type=Path)
    parser.add_argument("--strict", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_idea_to_spec_repair_session_journal(
        active_candidate=load_json(args.active_candidate),
        clarification_requests=load_json(args.clarification_requests),
        clarification_answers=load_json(args.clarification_answers),
        ontology_decisions=load_json(args.ontology_decisions),
        rerun_input=load_json(args.rerun_input),
        rerun_preview=load_json(args.rerun_preview),
        rerun_materialization=load_json(args.rerun_materialization),
        promotion_gate=load_json(args.promotion_gate),
        active_candidate_path=args.active_candidate,
        clarification_requests_path=args.clarification_requests,
        clarification_answers_path=args.clarification_answers,
        ontology_decisions_path=args.ontology_decisions,
        rerun_input_path=args.rerun_input,
        rerun_preview_path=args.rerun_preview,
        rerun_materialization_path=args.rerun_materialization,
        promotion_gate_path=args.promotion_gate,
        session_id=args.session_id,
        operator_ref=args.operator_ref,
    )
    write_json(report, args.output)
    summary = _dict(report.get("summary"))
    print(
        f"{summary.get('status', 'unknown')}: "
        f"{summary.get('source_artifact_count', 0)} artifacts, "
        f"{summary.get('ontology_decision_count', 0)} ontology decisions, "
        f"{summary.get('unresolved_ontology_gap_count', 0)} unresolved ontology gaps -> "
        f"{_relative_ref(args.output)}"
    )
    if args.strict and not _dict(report.get("readiness")).get("ready"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
