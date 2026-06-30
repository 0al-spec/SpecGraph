"""Apply accepted intake clarification answers to a real-idea intake session."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import idea_to_spec_clarification_answers as answer_validator
import user_idea_intake_interview as interview_tool

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_ID = "0186"
SCHEMA_VERSION = 1
RERUN_INPUT_CONTRACT_REF = "specgraph.idea-to-spec.intake-answer-rerun-input.v0.1"
RERUN_REPORT_CONTRACT_REF = "specgraph.idea-to-spec.intake-clarification-rerun.v0.1"

DEFAULT_RAW_INPUT_PATH = ROOT / "runs" / "local_operator_user_idea_raw_input.json"
DEFAULT_REQUESTS_PATH = ROOT / "runs" / "idea_intake_clarification_requests.json"
DEFAULT_ANSWER_SET_PATH = (
    ROOT / "tests" / "fixtures" / "idea_intake_clarification" / "answers_ready.json"
)
DEFAULT_VALIDATED_ANSWERS_OUTPUT_PATH = ROOT / "runs" / "idea_intake_clarification_answers.json"
DEFAULT_RERUN_INPUT_OUTPUT_PATH = ROOT / "runs" / "idea_intake_answer_rerun_input.json"
DEFAULT_CLARIFIED_RAW_OUTPUT_PATH = (
    ROOT / "runs" / "local_operator_clarified_user_idea_raw_input.json"
)
DEFAULT_CLARIFIED_SESSION_OUTPUT_PATH = ROOT / "runs" / "clarified_user_idea_intake_session.json"
DEFAULT_CLARIFIED_SOURCE_OUTPUT_PATH = ROOT / "runs" / "clarified_user_idea_intake_source.json"
DEFAULT_REPORT_OUTPUT_PATH = ROOT / "runs" / "idea_intake_clarification_rerun_report.json"

APPLY_ANSWER_KINDS = {"answer_question", "provide_candidate_context"}
ACCEPTED_STATUSES = {"accepted_for_candidate", "accepted_for_review"}


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
        digest = hashlib.sha256(path.resolve().as_posix().encode("utf-8")).hexdigest()[:16]
        return f"external:{digest}:{path.name}"


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
        "source": "idea_intake_clarification_rerun",
        "evidence": evidence or {},
    }


def _authority_boundary() -> dict[str, bool]:
    return {
        "may_execute_prompt_agent": False,
        "may_infer_domain_model": False,
        "may_apply_clarification_answers": False,
        "may_mutate_user_intent": False,
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


def _request_index(clarification_requests: dict[str, Any]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for raw_request in _list(clarification_requests.get("clarification_requests")):
        request = _dict(raw_request)
        request_id = _text(request.get("id"))
        if request_id:
            index[request_id] = request
    return index


def _accepted_answer_targets(
    validated_answers: dict[str, Any],
    clarification_requests: dict[str, Any],
) -> list[dict[str, Any]]:
    requests = _request_index(clarification_requests)
    targets: list[dict[str, Any]] = []
    for answer in [_dict(item) for item in _list(validated_answers.get("answers"))]:
        if _text(answer.get("status")) not in ACCEPTED_STATUSES:
            continue
        if _text(answer.get("answer_kind")) not in APPLY_ANSWER_KINDS:
            continue
        request_id = _text(answer.get("request_id"))
        request = requests.get(request_id, {})
        targets.append(
            {
                "request_id": request_id,
                "answer_kind": answer.get("answer_kind"),
                "target_artifact": request.get("target_artifact"),
                "target_ref": request.get("target_ref"),
                "value_type": type(answer.get("value")).__name__,
                "value_digest": hashlib.sha256(
                    json.dumps(
                        answer.get("value"),
                        sort_keys=True,
                        separators=(",", ":"),
                    ).encode("utf-8")
                ).hexdigest()
                if answer.get("value") is not None
                else None,
            }
        )
    return targets


def build_intake_answer_rerun_input(
    *,
    raw_input_path: Path,
    clarification_requests: dict[str, Any],
    clarification_requests_path: Path,
    answer_set: dict[str, Any],
    answer_set_path: Path,
    validated_answers: dict[str, Any],
    validated_answers_path: Path,
) -> dict[str, Any]:
    answer_findings = [_dict(item) for item in _list(validated_answers.get("findings"))]
    readiness = _dict(validated_answers.get("readiness"))
    accepted_targets = _accepted_answer_targets(validated_answers, clarification_requests)
    findings = list(answer_findings)
    if readiness.get("ready") is not True:
        findings.append(
            _finding(
                finding_id="idea_intake_answer_rerun_answers_not_ready",
                severity="review_required",
                message="Intake clarification answers must be ready before rerun.",
                evidence={"review_state": readiness.get("review_state")},
            )
        )
    if not accepted_targets:
        findings.append(
            _finding(
                finding_id="idea_intake_answer_rerun_no_applicable_answers",
                severity="review_required",
                message="Intake clarification rerun requires accepted answers with target refs.",
            )
        )
    ready = not findings
    return {
        "artifact_kind": "idea_intake_answer_rerun_input",
        "schema_version": SCHEMA_VERSION,
        "proposal_id": PROPOSAL_ID,
        "contract_ref": RERUN_INPUT_CONTRACT_REF,
        "generated_at": _now_iso(),
        "source_refs": {
            "raw_input": _relative_ref(raw_input_path),
            "clarification_requests": _relative_ref(clarification_requests_path),
            "answer_set": _relative_ref(answer_set_path),
            "validated_answers": _relative_ref(validated_answers_path),
        },
        "input_contracts": {
            "clarification_requests": clarification_requests.get("contract_ref"),
            "answer_set": answer_set.get("contract_ref"),
            "validated_answers": validated_answers.get("contract_ref"),
        },
        "accepted_answer_targets": accepted_targets,
        "readiness": {
            "ready": ready,
            "review_state": "intake_answer_rerun_ready"
            if ready
            else "intake_answer_rerun_review_required",
            "blocked_by": [finding["finding_id"] for finding in findings],
            "next_artifact": "runs/clarified_user_idea_intake_session.json",
        },
        "authority_boundary": _authority_boundary(),
        "privacy_boundary": _privacy_boundary(),
        "findings": findings,
        "summary": {
            "status": "intake_answer_rerun_ready"
            if ready
            else "intake_answer_rerun_review_required",
            "accepted_answer_count": _dict(validated_answers.get("summary")).get(
                "accepted_answer_count", 0
            ),
            "accepted_target_count": len(accepted_targets),
            "finding_count": len(findings),
        },
    }


def build_intake_clarification_rerun(
    *,
    raw_input: dict[str, Any],
    raw_input_path: Path,
    clarification_requests: dict[str, Any],
    clarification_requests_path: Path,
    answer_set: dict[str, Any],
    answer_set_path: Path,
    validated_answers_path: Path,
    rerun_input_path: Path,
    clarified_raw_output_path: Path,
    clarified_session_output_path: Path,
    clarified_source_output_path: Path,
) -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    dict[str, Any] | None,
    dict[str, Any],
]:
    validated_answers = answer_validator.build_idea_to_spec_clarification_answers(
        clarification_requests=clarification_requests,
        answer_set=answer_set,
        requests_path=clarification_requests_path,
        answer_set_path=answer_set_path,
    )
    rerun_input = build_intake_answer_rerun_input(
        raw_input_path=raw_input_path,
        clarification_requests=clarification_requests,
        clarification_requests_path=clarification_requests_path,
        answer_set=answer_set,
        answer_set_path=answer_set_path,
        validated_answers=validated_answers,
        validated_answers_path=validated_answers_path,
    )
    clarified_raw, clarified_session, interview_report, clarified_source = (
        interview_tool.build_interview(
            base_input=raw_input,
            base_input_path=raw_input_path,
            idea_text="",
            idea_summary="",
            candidate_id="",
            display_name="",
            public_route="",
            project="",
            subsystem="",
            lifecycle_phase="",
            ontology_refs=[],
            ontology_layer_refs=[],
            domain_refs=[],
            context_refs=[],
            model_applicability_refs=[],
            event_entries={},
            clarification_requests=clarification_requests,
            clarification_requests_path=clarification_requests_path,
            clarification_answers=answer_set,
            clarification_answers_path=answer_set_path,
            raw_output_path=clarified_raw_output_path,
            session_output_path=clarified_session_output_path,
            source_output_path=clarified_source_output_path,
        )
    )
    rerun_ready = _dict(rerun_input.get("readiness")).get("ready") is True
    session_ready = _dict(clarified_session.get("readiness")).get("ready") is True
    report_findings = [
        *_list(rerun_input.get("findings")),
        *_list(interview_report.get("findings")),
    ]
    if not rerun_ready:
        report_findings.append(
            _finding(
                finding_id="idea_intake_clarification_rerun_input_not_ready",
                severity="review_required",
                message="Intake clarification rerun input is not ready.",
            )
        )
    if not session_ready:
        report_findings.append(
            _finding(
                finding_id="idea_intake_clarification_rerun_session_not_ready",
                severity="review_required",
                message="Clarified intake session still needs clarification.",
                evidence={
                    "review_state": _dict(clarified_session.get("readiness")).get("review_state")
                },
            )
        )
    ready = rerun_ready and session_ready and clarified_source is not None and not report_findings
    report = {
        "artifact_kind": "idea_intake_clarification_rerun_report",
        "schema_version": SCHEMA_VERSION,
        "proposal_id": PROPOSAL_ID,
        "contract_ref": RERUN_REPORT_CONTRACT_REF,
        "generated_at": _now_iso(),
        "source_refs": {
            "raw_input": _relative_ref(raw_input_path),
            "clarification_requests": _relative_ref(clarification_requests_path),
            "answer_set": _relative_ref(answer_set_path),
            "validated_answers": _relative_ref(validated_answers_path),
            "rerun_input": _relative_ref(rerun_input_path),
        },
        "output_refs": {
            "clarified_raw_input": _relative_ref(clarified_raw_output_path),
            "clarified_intake_session": _relative_ref(clarified_session_output_path),
            "clarified_intake_source": _relative_ref(clarified_source_output_path)
            if clarified_source is not None
            else None,
        },
        "clarification_answer_application": interview_report.get(
            "clarification_answer_application", {}
        ),
        "intake_session": {
            "artifact_kind": clarified_session.get("artifact_kind"),
            "contract_ref": clarified_session.get("contract_ref"),
            "digest": _digest(clarified_session),
            "review_state": _dict(clarified_session.get("readiness")).get("review_state"),
            "ready": session_ready,
            "clarification_question_count": len(
                _list(clarified_session.get("clarification_questions"))
            ),
        },
        "readiness": {
            "ready": ready,
            "review_state": "intake_clarification_rerun_ready"
            if ready
            else "intake_clarification_rerun_review_required",
            "blocked_by": [finding["finding_id"] for finding in report_findings],
            "next_artifact": "runs/user_idea_intake_source.json"
            if ready
            else "runs/clarified_user_idea_intake_session.json",
        },
        "authority_boundary": _authority_boundary(),
        "privacy_boundary": {
            **_privacy_boundary(),
            "raw_idea_text_published_in_report": False,
            "raw_idea_text_published_in_clarified_session": False,
        },
        "findings": report_findings,
        "summary": {
            "status": "intake_clarification_rerun_ready"
            if ready
            else "intake_clarification_rerun_review_required",
            "ready_for_candidate_source": ready,
            "source_written": clarified_source is not None,
            "accepted_target_count": len(_list(rerun_input.get("accepted_answer_targets"))),
            "finding_count": len(report_findings),
        },
    }
    return (
        validated_answers,
        rerun_input,
        clarified_raw,
        clarified_session,
        clarified_source,
        report,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-input", default=DEFAULT_RAW_INPUT_PATH, type=Path)
    parser.add_argument("--clarification-requests", default=DEFAULT_REQUESTS_PATH, type=Path)
    parser.add_argument("--answers", default=DEFAULT_ANSWER_SET_PATH, type=Path)
    parser.add_argument(
        "--validated-answers-output",
        default=DEFAULT_VALIDATED_ANSWERS_OUTPUT_PATH,
        type=Path,
    )
    parser.add_argument("--rerun-input-output", default=DEFAULT_RERUN_INPUT_OUTPUT_PATH, type=Path)
    parser.add_argument(
        "--clarified-raw-output",
        default=DEFAULT_CLARIFIED_RAW_OUTPUT_PATH,
        type=Path,
    )
    parser.add_argument(
        "--clarified-session-output",
        default=DEFAULT_CLARIFIED_SESSION_OUTPUT_PATH,
        type=Path,
    )
    parser.add_argument(
        "--clarified-source-output",
        default=DEFAULT_CLARIFIED_SOURCE_OUTPUT_PATH,
        type=Path,
    )
    parser.add_argument("--report-output", default=DEFAULT_REPORT_OUTPUT_PATH, type=Path)
    parser.add_argument("--strict", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    raw_input = load_json(args.raw_input)
    clarification_requests = load_json(args.clarification_requests)
    answer_set = load_json(args.answers)
    (
        validated_answers,
        rerun_input,
        clarified_raw,
        clarified_session,
        clarified_source,
        report,
    ) = build_intake_clarification_rerun(
        raw_input=raw_input,
        raw_input_path=args.raw_input,
        clarification_requests=clarification_requests,
        clarification_requests_path=args.clarification_requests,
        answer_set=answer_set,
        answer_set_path=args.answers,
        validated_answers_path=args.validated_answers_output,
        rerun_input_path=args.rerun_input_output,
        clarified_raw_output_path=args.clarified_raw_output,
        clarified_session_output_path=args.clarified_session_output,
        clarified_source_output_path=args.clarified_source_output,
    )
    write_json(validated_answers, args.validated_answers_output)
    write_json(rerun_input, args.rerun_input_output)
    write_json(clarified_raw, args.clarified_raw_output)
    write_json(clarified_session, args.clarified_session_output)
    write_json(report, args.report_output)
    if clarified_source is not None:
        write_json(clarified_source, args.clarified_source_output)
    elif args.clarified_source_output.exists():
        args.clarified_source_output.unlink()
    summary = _dict(report.get("summary"))
    print(
        f"{summary.get('status', 'unknown')}: "
        f"{summary.get('accepted_target_count', 0)} accepted targets -> "
        f"{_relative_ref(args.report_output)}"
    )
    if args.strict and not summary.get("ready_for_candidate_source"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
