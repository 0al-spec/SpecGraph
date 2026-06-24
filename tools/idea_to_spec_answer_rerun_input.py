"""Build a review-only rerun input overlay from accepted clarification answers."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_ID = "0165"
SCHEMA_VERSION = 1
CONTRACT_REF = "specgraph.idea-to-spec.answer-rerun-input.v0.1"
ANSWERS_CONTRACT_REF = "specgraph.idea-to-spec.clarification-answers.v0.1"
DEFAULT_ANSWERS_PATH = ROOT / "runs" / "idea_to_spec_clarification_answers.json"
DEFAULT_OUTPUT_PATH = ROOT / "runs" / "idea_to_spec_answer_rerun_input.json"

ACCEPTED_STATUSES = {"accepted_for_candidate", "accepted_for_review"}
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


def _text_list(value: Any) -> list[str]:
    return [item.strip() for item in _list(value) if isinstance(item, str) and item.strip()]


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
        "source": "idea_to_spec_answer_rerun_input",
        "evidence": evidence or {},
    }


def _authority_boundary() -> dict[str, bool]:
    return {
        "may_execute_prompt_agent": False,
        "may_apply_answers_to_source_artifacts": False,
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


def _validate_answers_report(answers_report: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if answers_report.get("artifact_kind") != "idea_to_spec_clarification_answers":
        findings.append(
            _finding(
                finding_id="answers_wrong_artifact_kind",
                severity="review_required",
                message="Rerun input requires idea_to_spec_clarification_answers input.",
                evidence={"artifact_kind": answers_report.get("artifact_kind")},
            )
        )
    if answers_report.get("contract_ref") != ANSWERS_CONTRACT_REF:
        findings.append(
            _finding(
                finding_id="answers_contract_ref_unsupported",
                severity="review_required",
                message=f"Answer report contract_ref must be {ANSWERS_CONTRACT_REF}.",
                evidence={"contract_ref": answers_report.get("contract_ref")},
            )
        )
    if answers_report.get("schema_version") != SCHEMA_VERSION:
        findings.append(
            _finding(
                finding_id="answers_schema_version_unsupported",
                severity="review_required",
                message="Answer report schema_version must be 1.",
                evidence={"schema_version": answers_report.get("schema_version")},
            )
        )
    readiness = _dict(answers_report.get("readiness"))
    if readiness.get("ready") is not True:
        findings.append(
            _finding(
                finding_id="answers_not_ready_for_rerun",
                severity="review_required",
                message="Answer report must resolve blocking requests before rerun input.",
                evidence={"readiness": readiness},
            )
        )
    for field in ("canonical_mutations_allowed", "tracked_artifacts_written"):
        if answers_report.get(field) is not False:
            findings.append(
                _finding(
                    finding_id="answers_authority_expanded",
                    severity="review_required",
                    message=f"Answer report {field} must be false.",
                    evidence={field: answers_report.get(field)},
                )
            )
    return findings


def _request_context(answer: dict[str, Any]) -> dict[str, str]:
    snapshot = _dict(answer.get("request_snapshot"))
    return {
        "request_id": _text(answer.get("request_id")),
        "answer_kind": _text(answer.get("answer_kind")),
        "target_artifact": _text(snapshot.get("target_artifact")),
        "target_ref": _text(snapshot.get("target_ref")),
        "request_kind": _text(snapshot.get("kind")),
    }


def _terms_from_value(value: dict[str, Any]) -> list[str]:
    terms = _text_list(value.get("terms"))
    term = _text(value.get("term"))
    if term and term not in terms:
        terms.append(term)
    return terms


def _append_project_terms(
    overlay: dict[str, Any],
    *,
    answer: dict[str, Any],
    value: dict[str, Any],
) -> None:
    context = _request_context(answer)
    terms = _terms_from_value(value)
    if not terms:
        target_ref = context["target_ref"]
        if target_ref:
            terms = [target_ref.rsplit(".", 1)[-1].replace("-", " ")]
    for term in terms:
        overlay["ontology_review_hints"]["project_local_terms"].append(
            {
                "term": term,
                "term_scope": _text(value.get("term_scope"), "project_local"),
                **context,
            }
        )


def _append_binding(
    overlay: dict[str, Any],
    *,
    answer: dict[str, Any],
    value: dict[str, Any],
) -> None:
    context = _request_context(answer)
    overlay["ontology_review_hints"]["term_bindings"].append(
        {
            "term": _text(value.get("term")),
            "ontology_ref": _text(value.get("ontology_ref")),
            **context,
        }
    )


def _append_alias(
    overlay: dict[str, Any],
    *,
    answer: dict[str, Any],
    value: dict[str, Any],
) -> None:
    context = _request_context(answer)
    overlay["ontology_review_hints"]["aliases"].append(
        {
            "term": _text(value.get("term")),
            "alias_of": _text(value.get("alias_of")),
            **context,
        }
    )


def _append_decision(
    overlay: dict[str, Any],
    *,
    answer: dict[str, Any],
    bucket: str,
) -> None:
    context = _request_context(answer)
    overlay["ontology_review_hints"][bucket].append(context)


def _append_active_frame(
    overlay: dict[str, Any],
    *,
    answer: dict[str, Any],
    value: dict[str, Any],
) -> None:
    context = _request_context(answer)
    frame = _dict(value.get("active_frame_hints") or value.get("active_frame"))
    if frame:
        overlay["intake_overlay"]["active_frame_hints"].append(
            {"value": _public_safe(frame), **context}
        )


def _append_event_storming(
    overlay: dict[str, Any],
    *,
    answer: dict[str, Any],
    value: dict[str, Any],
) -> None:
    context = _request_context(answer)
    event_storming = _dict(value.get("event_storming_hints") or value.get("event_storming"))
    if event_storming:
        overlay["intake_overlay"]["event_storming_hints"].append(
            {"value": _public_safe(event_storming), **context}
        )


def _append_candidate_review(
    overlay: dict[str, Any],
    *,
    answer: dict[str, Any],
    value: dict[str, Any],
) -> None:
    context = _request_context(answer)
    answer_kind = context["answer_kind"]
    if answer_kind in {"accept_preview_criterion", "provide_acceptance_criterion"}:
        overlay["candidate_review_hints"]["acceptance_criteria"].append(
            {"value": _public_safe(value), **context}
        )
    elif answer_kind in {"accept_preview_edge", "propose_relation"}:
        overlay["candidate_review_hints"]["graph_edges"].append(
            {"value": _public_safe(value), **context}
        )
    elif answer_kind in {"accept_downgrade", "add_evidence", "narrow_scope", "reject_claim"}:
        overlay["candidate_review_hints"]["claim_reviews"].append(
            {"value": _public_safe(value), **context}
        )
    else:
        overlay["candidate_review_hints"]["other"].append({"value": _public_safe(value), **context})


def _empty_overlay() -> dict[str, Any]:
    return {
        "intake_overlay": {
            "active_frame_hints": [],
            "event_storming_hints": [],
        },
        "ontology_review_hints": {
            "term_bindings": [],
            "aliases": [],
            "project_local_terms": [],
            "rejected_terms": [],
            "deferred_terms": [],
        },
        "candidate_review_hints": {
            "acceptance_criteria": [],
            "graph_edges": [],
            "claim_reviews": [],
            "other": [],
        },
    }


def _apply_answer_to_overlay(overlay: dict[str, Any], answer: dict[str, Any]) -> None:
    answer_kind = _text(answer.get("answer_kind"))
    value = _dict(answer.get("value"))
    if answer_kind == "propose_project_local_term":
        _append_project_terms(overlay, answer=answer, value=value)
    elif answer_kind == "bind_existing_term":
        _append_binding(overlay, answer=answer, value=value)
    elif answer_kind == "alias":
        _append_alias(overlay, answer=answer, value=value)
    elif answer_kind == "reject":
        _append_decision(overlay, answer=answer, bucket="rejected_terms")
    elif answer_kind == "defer":
        _append_decision(overlay, answer=answer, bucket="deferred_terms")
    elif answer_kind == "answer_question":
        _append_active_frame(overlay, answer=answer, value=value)
        _append_event_storming(overlay, answer=answer, value=value)
    else:
        _append_candidate_review(overlay, answer=answer, value=value)


def build_idea_to_spec_answer_rerun_input(
    *,
    answers_report: dict[str, Any],
    answers_path: Path | None = None,
) -> dict[str, Any]:
    findings = _validate_answers_report(answers_report)
    overlay = _empty_overlay()
    accepted_answers = [
        _dict(answer)
        for answer in _list(answers_report.get("answers"))
        if _text(_dict(answer).get("status")) in ACCEPTED_STATUSES
    ]
    if not findings:
        for answer in accepted_answers:
            _apply_answer_to_overlay(overlay, answer)
    source_ref = _relative_ref(answers_path) if answers_path else "inline:clarification_answers"
    ready = not findings
    return {
        "artifact_kind": "idea_to_spec_answer_rerun_input",
        "schema_version": SCHEMA_VERSION,
        "proposal_id": PROPOSAL_ID,
        "contract_ref": CONTRACT_REF,
        "generated_at": _now_iso(),
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "source_artifacts": {
            "clarification_answers": {
                "artifact_kind": answers_report.get("artifact_kind"),
                "contract_ref": answers_report.get("contract_ref"),
                "source_ref": source_ref,
                "accepted_answer_count": len(accepted_answers),
            }
        },
        "rerun_input_overlay": overlay,
        "readiness": {
            "ready": ready,
            "review_state": "rerun_input_ready" if ready else "rerun_input_review_required",
            "blocked_by": [finding["finding_id"] for finding in findings],
            "next_artifact": "runs/user_idea_intake_source.json",
        },
        "authority_boundary": _authority_boundary(),
        "privacy_boundary": {
            "raw_idea_text_published": False,
            "raw_prompt_published": False,
            "raw_model_output_published": False,
            "raw_operator_note_published": False,
        },
        "findings": findings,
        "summary": {
            "status": "rerun_input_ready" if ready else "rerun_input_review_required",
            "accepted_answer_count": len(accepted_answers),
            "project_local_term_count": len(
                overlay["ontology_review_hints"]["project_local_terms"]
            ),
            "term_binding_count": len(overlay["ontology_review_hints"]["term_bindings"]),
            "intake_overlay_count": len(overlay["intake_overlay"]["active_frame_hints"])
            + len(overlay["intake_overlay"]["event_storming_hints"]),
            "candidate_review_hint_count": sum(
                len(items) for items in overlay["candidate_review_hints"].values()
            ),
            "finding_count": len(findings),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--answers", default=DEFAULT_ANSWERS_PATH, type=Path)
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, type=Path)
    parser.add_argument("--strict", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_idea_to_spec_answer_rerun_input(
        answers_report=load_json(args.answers),
        answers_path=args.answers,
    )
    write_json(report, args.output)
    summary = _dict(report.get("summary"))
    print(
        f"{summary.get('status', 'unknown')}: "
        f"{summary.get('accepted_answer_count', 0)} accepted answers -> "
        f"{_relative_ref(args.output)}"
    )
    if args.strict and not _dict(report.get("readiness")).get("ready"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
