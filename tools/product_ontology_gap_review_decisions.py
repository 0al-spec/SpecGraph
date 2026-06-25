"""Build product-scoped ontology gap review decisions for idea-to-spec flows."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_ID = "0168"
SCHEMA_VERSION = 1
CONTRACT_REF = "specgraph.product-ontology.gap-review-decisions.v0.1"
ANSWERS_CONTRACT_REF = "specgraph.idea-to-spec.clarification-answers.v0.1"
DEFAULT_ANSWERS_PATH = ROOT / "runs" / "idea_to_spec_clarification_answers.json"
DEFAULT_OUTPUT_PATH = ROOT / "runs" / "product_ontology_gap_review_decisions.json"

ACCEPTED_STATUSES = {"accepted_for_candidate", "accepted_for_review"}
SUPPORTED_ONTOLOGY_ACTIONS = {
    "bind_existing_term",
    "alias",
    "propose_project_local_term",
    "reject",
    "defer",
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


def _text_list(value: Any) -> list[str]:
    return [item.strip() for item in _list(value) if isinstance(item, str) and item.strip()]


def _slug(value: str, fallback: str = "decision") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or fallback


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
        "source": "product_ontology_gap_review_decisions",
        "evidence": evidence or {},
    }


def _authority_boundary() -> dict[str, bool]:
    return {
        "may_execute_prompt_agent": False,
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


def _validate_answers_report(answers_report: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if answers_report.get("artifact_kind") != "idea_to_spec_clarification_answers":
        findings.append(
            _finding(
                finding_id="answers_wrong_artifact_kind",
                severity="review_required",
                message=(
                    "Product ontology decisions require idea_to_spec_clarification_answers input."
                ),
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
    readiness = _dict(answers_report.get("readiness"))
    if readiness.get("ready") is not True:
        findings.append(
            _finding(
                finding_id="answers_not_ready_for_ontology_decisions",
                severity="review_required",
                message="Product ontology decisions require a ready clarification answer report.",
                evidence={"readiness": readiness},
            )
        )
    return findings


def _request_context(answer: dict[str, Any]) -> dict[str, str]:
    snapshot = _dict(answer.get("request_snapshot"))
    return {
        "request_id": _text(answer.get("request_id")),
        "request_kind": _text(snapshot.get("kind")),
        "target_artifact": _text(snapshot.get("target_artifact")),
        "target_ref": _text(snapshot.get("target_ref")),
        "source_answer_kind": _text(answer.get("answer_kind")),
        "source_answer_status": _text(answer.get("status")),
        "authority": _text(answer.get("authority")),
    }


def _terms_from_value(value: Any) -> list[str]:
    if isinstance(value, str):
        term = _text(value)
        return [term] if term else []
    if isinstance(value, list):
        return _text_list(value)
    value_dict = _dict(value)
    terms = _text_list(value_dict.get("terms"))
    term = _text(value_dict.get("term"))
    if term and term not in terms:
        terms.append(term)
    return terms


def _base_decision(context: dict[str, str], *, index: int, decision_type: str) -> dict[str, Any]:
    return {
        "id": f"product-ontology-decision.{_slug(context['request_id'])}.{index}",
        "decision_type": decision_type,
        "status": "accepted_for_candidate_preview",
        "materialization_intent": "rerun_overlay_only",
        "canonical_mutations_allowed": False,
        "writes_ontology_package": False,
        "accepts_ontology_term": False,
        **context,
    }


def _project_local_decisions(
    *,
    answer: dict[str, Any],
    context: dict[str, str],
    value: Any,
    index: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    terms = _terms_from_value(value)
    value_dict = _dict(value)
    if not terms:
        return [], [
            _finding(
                finding_id="project_local_term_value_missing",
                severity="review_required",
                message="Project-local ontology decisions require explicit term or terms.",
                evidence={"request_id": context["request_id"], "target_ref": context["target_ref"]},
            )
        ]
    decisions: list[dict[str, Any]] = []
    for offset, term in enumerate(terms):
        decision = _base_decision(
            context,
            index=index + offset,
            decision_type="propose_project_local_term",
        )
        decision.update(
            {
                "term": term,
                "term_scope": _text(value_dict.get("term_scope"), "project_local"),
                "source_value": _public_safe(answer.get("value")),
            }
        )
        decisions.append(decision)
    return decisions, []


def _binding_decision(
    *,
    answer: dict[str, Any],
    context: dict[str, str],
    value: dict[str, Any],
    index: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    term = _text(value.get("term"))
    ontology_ref = _text(value.get("ontology_ref"))
    if not term or not ontology_ref:
        return [], [
            _finding(
                finding_id="term_binding_value_incomplete",
                severity="review_required",
                message="bind_existing_term decisions require term and ontology_ref.",
                evidence={
                    "request_id": context["request_id"],
                    "term": term,
                    "ontology_ref": ontology_ref,
                },
            )
        ]
    decision = _base_decision(
        context,
        index=index,
        decision_type="bind_existing_term",
    )
    decision.update(
        {
            "term": term,
            "ontology_ref": ontology_ref,
            "source_value": _public_safe(value),
        }
    )
    return [decision], []


def _alias_decision(
    *,
    answer: dict[str, Any],
    context: dict[str, str],
    value: dict[str, Any],
    index: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    term = _text(value.get("term"))
    alias_of = _text(value.get("alias_of"))
    if not term or not alias_of:
        return [], [
            _finding(
                finding_id="alias_value_incomplete",
                severity="review_required",
                message="alias decisions require term and alias_of.",
                evidence={"request_id": context["request_id"], "term": term, "alias_of": alias_of},
            )
        ]
    decision = _base_decision(context, index=index, decision_type="alias_existing_term")
    decision.update({"term": term, "alias_of": alias_of, "source_value": _public_safe(value)})
    return [decision], []


def _simple_decision(
    *,
    context: dict[str, str],
    value: Any,
    index: int,
    decision_type: str,
) -> list[dict[str, Any]]:
    decision = _base_decision(context, index=index, decision_type=decision_type)
    value_dict = _dict(value)
    term = _text(value_dict.get("term"))
    reason = _text(value_dict.get("reason"))
    if term:
        decision["term"] = term
    if reason:
        decision["reason"] = reason
    if value not in ({}, [], "", None):
        decision["source_value"] = _public_safe(value)
    return [decision]


def _decisions_from_answer(
    answer: dict[str, Any],
    *,
    index: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    context = _request_context(answer)
    answer_kind = context["source_answer_kind"]
    value = answer.get("value")
    if context["request_kind"] != "ontology_gap":
        return [], []
    if context["source_answer_status"] not in ACCEPTED_STATUSES:
        return [], []
    if answer_kind not in SUPPORTED_ONTOLOGY_ACTIONS:
        return [], [
            _finding(
                finding_id="ontology_answer_kind_unsupported",
                severity="review_required",
                message="Ontology gap answer kind is not supported by product ontology decisions.",
                evidence={"request_id": context["request_id"], "answer_kind": answer_kind},
            )
        ]
    if answer_kind == "propose_project_local_term":
        return _project_local_decisions(answer=answer, context=context, value=value, index=index)
    if answer_kind == "bind_existing_term":
        return _binding_decision(answer=answer, context=context, value=_dict(value), index=index)
    if answer_kind == "alias":
        return _alias_decision(answer=answer, context=context, value=_dict(value), index=index)
    if answer_kind == "reject":
        return _simple_decision(
            context=context,
            value=value,
            index=index,
            decision_type="reject_non_domain_term",
        ), []
    return _simple_decision(
        context=context,
        value=value,
        index=index,
        decision_type="defer_requires_owner",
    ), []


def _decision_counts(decisions: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for decision in decisions:
        decision_type = _text(decision.get("decision_type"), "unknown")
        counts[decision_type] = counts.get(decision_type, 0) + 1
    return counts


def build_product_ontology_gap_review_decisions(
    *,
    answers_report: dict[str, Any],
    answers_path: Path | None = None,
) -> dict[str, Any]:
    findings = _validate_answers_report(answers_report)
    decisions: list[dict[str, Any]] = []
    ontology_answer_count = 0
    if not findings:
        answers = [_dict(item) for item in _list(answers_report.get("answers"))]
        for index, answer in enumerate(answers):
            context = _request_context(answer)
            if context["request_kind"] == "ontology_gap":
                ontology_answer_count += 1
            answer_decisions, answer_findings = _decisions_from_answer(answer, index=index)
            decisions.extend(answer_decisions)
            findings.extend(answer_findings)
    ready = not findings
    source_ref = _relative_ref(answers_path) if answers_path else "inline:clarification_answers"
    return {
        "artifact_kind": "product_ontology_gap_review_decisions",
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
                "answer_count": len(_list(answers_report.get("answers"))),
                "ontology_answer_count": ontology_answer_count,
            }
        },
        "decisions": decisions,
        "readiness": {
            "ready": ready,
            "review_state": (
                "ontology_gap_decisions_ready"
                if ready
                else "ontology_gap_decisions_review_required"
            ),
            "blocked_by": [finding["finding_id"] for finding in findings],
            "next_artifact": "runs/idea_to_spec_answer_rerun_input.json",
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
            "status": (
                "ontology_gap_decisions_ready"
                if ready
                else "ontology_gap_decisions_review_required"
            ),
            "decision_count": len(decisions),
            "ontology_answer_count": ontology_answer_count,
            "decision_counts": _decision_counts(decisions),
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
    report = build_product_ontology_gap_review_decisions(
        answers_report=load_json(args.answers),
        answers_path=args.answers,
    )
    write_json(report, args.output)
    summary = _dict(report.get("summary"))
    print(
        f"{summary.get('status', 'unknown')}: "
        f"{summary.get('decision_count', 0)} product ontology decisions -> "
        f"{_relative_ref(args.output)}"
    )
    if args.strict and not _dict(report.get("readiness")).get("ready"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
