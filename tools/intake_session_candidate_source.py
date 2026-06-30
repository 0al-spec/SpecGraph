"""Materialize a ready intake session into a public-safe candidate source."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_ID = "0185"
SCHEMA_VERSION = 1
SESSION_CONTRACT_REF = "specgraph.idea-to-spec.user-idea-intake-session.v0.1"
SOURCE_CONTRACT_REF = "specgraph.idea-to-spec.user-idea-intake-source.v0.1"
INPUT_CONTRACT_REF = "specgraph.idea-to-spec.intake-session-candidate-source-input.v0.1"
REPORT_CONTRACT_REF = "specgraph.idea-to-spec.intake-session-candidate-source.v0.1"
DEFAULT_SESSION_PATH = ROOT / "runs" / "user_idea_intake_session.json"
DEFAULT_OUTPUT_PATH = ROOT / "runs" / "user_idea_intake_source.json"
DEFAULT_REPORT_OUTPUT_PATH = ROOT / "runs" / "intake_session_candidate_source_report.json"

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
AUTHORITY_KEYS = {
    "canonical_mutations_allowed",
    "may_accept_ontology_terms",
    "may_apply_clarification_answers",
    "may_apply_state",
    "may_create_branch_or_commit",
    "may_execute_platform",
    "may_execute_prompt_agent",
    "may_infer_domain_model",
    "may_mark_candidate_graph_accepted",
    "may_mutate_candidate_source_artifacts",
    "may_mutate_canonical_specs",
    "may_mutate_user_intent",
    "may_open_pull_request",
    "may_publish_read_model",
    "may_write_ontology_lockfile",
    "may_write_ontology_package",
    "tracked_artifacts_written",
}


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any, default: str = "") -> str:
    return value.strip() if isinstance(value, str) and value.strip() else default


def _relative_ref(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return f"external:{path.name}"


def _digest(payload: dict[str, Any]) -> str:
    data = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


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
        "source": "intake_session_candidate_source",
        "evidence": evidence or {},
    }


def _authority_boundary() -> dict[str, bool]:
    return {
        "may_execute_prompt_agent": False,
        "may_infer_domain_model": False,
        "may_mutate_user_intent": False,
        "may_apply_clarification_answers": False,
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


def _privacy_boundary() -> dict[str, bool]:
    return {
        "raw_idea_text_published": False,
        "raw_prompt_published": False,
        "raw_model_output_published": False,
        "raw_operator_note_published": False,
    }


def _authority_findings(value: Any) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    def visit(item: Any, path: str) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                if not isinstance(key, str):
                    continue
                child_path = f"{path}.{key}" if path else key
                if key in AUTHORITY_KEYS and child is not False:
                    findings.append(
                        _finding(
                            finding_id="intake_session_candidate_source_authority_expanded",
                            severity="blocked",
                            message=(
                                "Intake-session candidate source bridge cannot accept "
                                "execution or mutation authority."
                            ),
                            evidence={"field": child_path, "value": child},
                        )
                    )
                visit(child, child_path)
        elif isinstance(item, list):
            for index, child in enumerate(item):
                visit(child, f"{path}[{index}]")

    visit(value, "")
    return findings


def _raw_trace_findings(value: Any) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    def visit(item: Any, path: str) -> None:
        if isinstance(item, dict):
            for key, child in item.items():
                if not isinstance(key, str):
                    continue
                child_path = f"{path}.{key}" if path else key
                in_privacy_boundary = ".privacy_boundary." in f".{child_path}."
                if key in RAW_TRACE_FIELDS or (key.startswith("raw_") and not in_privacy_boundary):
                    findings.append(
                        _finding(
                            finding_id="intake_session_candidate_source_raw_trace_field",
                            severity="blocked",
                            message="Candidate source bridge cannot publish raw trace fields.",
                            evidence={"field": child_path},
                        )
                    )
                visit(child, child_path)
        elif isinstance(item, list):
            for index, child in enumerate(item):
                visit(child, f"{path}[{index}]")

    visit(value, "")
    return findings


def _session_contract_findings(session: dict[str, Any]) -> list[dict[str, Any]]:
    invalid: list[str] = []
    if session.get("artifact_kind") != "user_idea_intake_session":
        invalid.append("artifact_kind")
    if session.get("schema_version") != SCHEMA_VERSION:
        invalid.append("schema_version")
    if session.get("contract_ref") != SESSION_CONTRACT_REF:
        invalid.append("contract_ref")
    if not invalid:
        return []
    return [
        _finding(
            finding_id="intake_session_candidate_source_session_contract_invalid",
            severity="blocked",
            message="Candidate source bridge requires a supported intake session contract.",
            evidence={
                "invalid_fields": invalid,
                "expected": {
                    "artifact_kind": "user_idea_intake_session",
                    "schema_version": SCHEMA_VERSION,
                    "contract_ref": SESSION_CONTRACT_REF,
                },
            },
        )
    ]


def _privacy_findings(session: dict[str, Any], payload: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    session_privacy = _dict(session.get("privacy_boundary"))
    payload_privacy = _dict(payload.get("privacy_boundary"))
    required = {
        "raw_idea_text_published",
        "raw_prompt_published",
        "raw_model_output_published",
        "raw_operator_note_published",
    }
    if not session_privacy:
        findings.append(
            _finding(
                finding_id="intake_session_candidate_source_privacy_boundary_missing",
                severity="blocked",
                message="Intake session must declare a privacy boundary.",
            )
        )
    for key in sorted(required):
        session_key = f"{key}_in_session" if key == "raw_idea_text_published" else key
        session_value = session_privacy.get(session_key, session_privacy.get(key))
        payload_value = payload_privacy.get(key)
        if session_value is not False:
            findings.append(
                _finding(
                    finding_id="intake_session_candidate_source_privacy_unsafe",
                    severity="blocked",
                    message="Intake session privacy boundary is not public-safe.",
                    evidence={"field": f"privacy_boundary.{session_key}", "value": session_value},
                )
            )
        if payload_value is not False:
            findings.append(
                _finding(
                    finding_id="intake_session_candidate_source_payload_privacy_unsafe",
                    severity="blocked",
                    message="Candidate source payload privacy boundary is not public-safe.",
                    evidence={"field": f"candidate_source_input.privacy_boundary.{key}"},
                )
            )
    return findings


def _payload_contract_findings(payload: dict[str, Any]) -> list[dict[str, Any]]:
    invalid: list[str] = []
    if payload.get("artifact_kind") != "intake_session_candidate_source_input":
        invalid.append("artifact_kind")
    if payload.get("schema_version") != SCHEMA_VERSION:
        invalid.append("schema_version")
    if payload.get("contract_ref") != INPUT_CONTRACT_REF:
        invalid.append("contract_ref")
    if payload.get("available") is False:
        invalid.append("available")
    if not invalid:
        return []
    return [
        _finding(
            finding_id="intake_session_candidate_source_input_contract_invalid",
            severity="blocked",
            message="Ready intake session must carry a supported candidate source input payload.",
            evidence={"invalid_fields": invalid},
        )
    ]


def _content_findings(session: dict[str, Any], payload: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    readiness = _dict(session.get("readiness"))
    if readiness.get("ready") is not True:
        findings.append(
            _finding(
                finding_id="intake_session_candidate_source_session_not_ready",
                severity="review_required",
                message="Intake session is not ready for candidate source materialization.",
                evidence={"review_state": readiness.get("review_state")},
            )
        )
    if _list(session.get("clarification_questions")):
        findings.append(
            _finding(
                finding_id="intake_session_candidate_source_clarification_required",
                severity="review_required",
                message="Intake session still has clarification questions.",
                evidence={
                    "clarification_question_count": len(
                        _list(session.get("clarification_questions"))
                    )
                },
            )
        )
    workspace = _dict(payload.get("workspace"))
    if not _text(workspace.get("candidate_id")):
        findings.append(
            _finding(
                finding_id="intake_session_candidate_source_workspace_missing",
                severity="blocked",
                message="Candidate source payload requires workspace.candidate_id.",
            )
        )
    if not _text(workspace.get("display_name")):
        findings.append(
            _finding(
                finding_id="intake_session_candidate_source_display_name_missing",
                severity="blocked",
                message="Candidate source payload requires workspace.display_name.",
            )
        )
    if not _text(_dict(payload.get("intent")).get("summary")):
        findings.append(
            _finding(
                finding_id="intake_session_candidate_source_summary_missing",
                severity="blocked",
                message="Candidate source payload requires a normalized idea summary.",
            )
        )
    frame = _dict(payload.get("active_frame_hints"))
    for field in (
        "ontology_refs",
        "ontology_layer_refs",
        "domain_refs",
        "context_refs",
        "model_applicability_refs",
    ):
        if not _list(frame.get(field)):
            findings.append(
                _finding(
                    finding_id=f"intake_session_candidate_source_{field}_missing",
                    severity="review_required",
                    message=f"Candidate source payload requires active frame {field}.",
                )
            )
    event_storming = _dict(payload.get("event_storming_hints"))
    for field in ("actors", "domain_events", "commands", "constraints"):
        if not isinstance(event_storming.get(field), list):
            findings.append(
                _finding(
                    finding_id=f"intake_session_candidate_source_{field}_missing",
                    severity="review_required",
                    message=f"Candidate source payload requires event_storming_hints.{field}.",
                )
            )
    return findings


def _source_from_payload(
    session: dict[str, Any],
    payload: dict[str, Any],
    *,
    session_path: Path | None,
) -> dict[str, Any]:
    return {
        "artifact_kind": "user_idea_intake_source",
        "schema_version": SCHEMA_VERSION,
        "contract_ref": SOURCE_CONTRACT_REF,
        "source_ref": _text(payload.get("source_ref"), _text(session.get("source_ref"))),
        "workspace": _dict(payload.get("workspace")),
        "intent": {
            "text": "",
            "summary": _text(_dict(payload.get("intent")).get("summary")),
        },
        "active_frame_hints": _dict(payload.get("active_frame_hints")),
        "event_storming_hints": _dict(payload.get("event_storming_hints")),
        "source_session": {
            "artifact_kind": session.get("artifact_kind"),
            "contract_ref": session.get("contract_ref"),
            "proposal_id": session.get("proposal_id"),
            "bridge_proposal_id": PROPOSAL_ID,
            "source_ref": _relative_ref(session_path),
            "session_digest": _digest(session),
        },
        "source_materialization": {
            "artifact_kind": "intake_session_candidate_source_report",
            "contract_ref": REPORT_CONTRACT_REF,
            "proposal_id": PROPOSAL_ID,
            "mode": "session_embedded_public_payload",
        },
    }


def build_intake_session_candidate_source(
    session: dict[str, Any],
    *,
    session_path: Path | None = None,
    output_path: Path | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    payload = _dict(session.get("candidate_source_input"))
    findings = (
        _session_contract_findings(session)
        + _payload_contract_findings(payload)
        + _authority_findings(session)
        + _raw_trace_findings(payload)
        + _privacy_findings(session, payload)
        + _content_findings(session, payload)
    )
    source = None if findings else _source_from_payload(session, payload, session_path=session_path)
    if source is not None:
        findings.extend(_raw_trace_findings(source))
        findings.extend(_authority_findings(source))
        if findings:
            source = None
    ready = source is not None and not findings
    source_digest = _digest(source) if source is not None else None
    workspace = _dict(payload.get("workspace"))
    report = {
        "artifact_kind": "intake_session_candidate_source_report",
        "schema_version": SCHEMA_VERSION,
        "contract_ref": REPORT_CONTRACT_REF,
        "proposal_id": PROPOSAL_ID,
        "generated_at": _now_iso(),
        "source_refs": {
            "intake_session": _relative_ref(session_path),
            "embedded_payload": "candidate_source_input",
        },
        "output_refs": {
            "intake_source": _relative_ref(output_path) if source is not None else None,
        },
        "candidate_source": {
            "artifact_kind": "user_idea_intake_source",
            "contract_ref": SOURCE_CONTRACT_REF,
            "digest": source_digest,
            "workspace": {
                "candidate_id": workspace.get("candidate_id"),
                "display_name": workspace.get("display_name"),
                "public_route": workspace.get("public_route"),
            },
        },
        "readiness": {
            "ready": ready,
            "review_state": "candidate_source_ready"
            if ready
            else "candidate_source_review_required",
            "blocked_by": [finding["finding_id"] for finding in findings],
        },
        "authority_boundary": _authority_boundary(),
        "privacy_boundary": _privacy_boundary(),
        "findings": findings,
        "summary": {
            "status": "candidate_source_ready" if ready else "candidate_source_review_required",
            "workspace_id": workspace.get("candidate_id"),
            "finding_count": len(findings),
            "source_written": source is not None and output_path is not None,
        },
    }
    return source, report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intake-session", default=DEFAULT_SESSION_PATH, type=Path)
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, type=Path)
    parser.add_argument("--report", default=DEFAULT_REPORT_OUTPUT_PATH, type=Path)
    parser.add_argument("--strict", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    session = load_json(args.intake_session)
    source, report = build_intake_session_candidate_source(
        session,
        session_path=args.intake_session,
        output_path=args.output,
    )
    if source is not None:
        write_json(source, args.output)
    elif args.output.exists():
        args.output.unlink()
    write_json(report, args.report)
    print(
        f"{report['readiness']['review_state']}: "
        f"{report['summary']['finding_count']} findings -> {_relative_ref(args.report)}"
    )
    if source is not None:
        print(f"source_written -> {_relative_ref(args.output)}")
    if args.strict and source is None:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
