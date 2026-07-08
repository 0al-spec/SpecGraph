"""Build a review-only rerun input overlay from accepted clarification answers."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_ID = "0165"
SCHEMA_VERSION = 1
CONTRACT_REF = "specgraph.idea-to-spec.answer-rerun-input.v0.1"
ANSWERS_CONTRACT_REF = "specgraph.idea-to-spec.clarification-answers.v0.1"
ONTOLOGY_DECISIONS_CONTRACT_REF = "specgraph.product-ontology.gap-review-decisions.v0.1"
DEFAULT_ANSWERS_PATH = ROOT / "runs" / "idea_to_spec_clarification_answers.json"
DEFAULT_OUTPUT_PATH = ROOT / "runs" / "idea_to_spec_answer_rerun_input.json"

ACCEPTED_STATUSES = {"accepted_for_candidate", "accepted_for_review"}
EVENT_STORMING_CATEGORIES = {
    "actors",
    "commands",
    "domain_events",
    "policies",
    "constraints",
}
ACTIVE_FRAME_FIELDS = {
    "project",
    "subsystem",
    "lifecycle_phase",
    "ontology_refs",
    "ontology_layer_refs",
    "domain_refs",
    "context_refs",
    "model_applicability_refs",
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


def _ontology_answer_fingerprint(answers_report: dict[str, Any]) -> str:
    projection: list[dict[str, Any]] = []
    for answer in [_dict(item) for item in _list(answers_report.get("answers"))]:
        context = _request_context(answer)
        if context["request_kind"] != "ontology_gap":
            continue
        projection.append(
            {
                "request_id": context["request_id"],
                "answer_kind": context["answer_kind"],
                "status": _text(answer.get("status")),
                "target_artifact": context["target_artifact"],
                "target_ref": context["target_ref"],
                "value": _public_safe(answer.get("value")),
            }
        )
    encoded = json.dumps(projection, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def _validate_ontology_decisions_report(
    decisions_report: dict[str, Any],
    *,
    answers_report: dict[str, Any],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if decisions_report.get("artifact_kind") != "product_ontology_gap_review_decisions":
        findings.append(
            _finding(
                finding_id="ontology_decisions_wrong_artifact_kind",
                severity="review_required",
                message=("Ontology decision input must be product_ontology_gap_review_decisions."),
                evidence={"artifact_kind": decisions_report.get("artifact_kind")},
            )
        )
    if decisions_report.get("contract_ref") != ONTOLOGY_DECISIONS_CONTRACT_REF:
        findings.append(
            _finding(
                finding_id="ontology_decisions_contract_ref_unsupported",
                severity="review_required",
                message=(
                    "Ontology decision input contract_ref must be "
                    f"{ONTOLOGY_DECISIONS_CONTRACT_REF}."
                ),
                evidence={"contract_ref": decisions_report.get("contract_ref")},
            )
        )
    if decisions_report.get("schema_version") != SCHEMA_VERSION:
        findings.append(
            _finding(
                finding_id="ontology_decisions_schema_version_unsupported",
                severity="review_required",
                message="Ontology decision input schema_version must be 1.",
                evidence={"schema_version": decisions_report.get("schema_version")},
            )
        )
    for field in ("canonical_mutations_allowed", "tracked_artifacts_written"):
        if decisions_report.get(field) is not False:
            findings.append(
                _finding(
                    finding_id="ontology_decisions_authority_expanded",
                    severity="review_required",
                    message=f"Ontology decision input {field} must be false.",
                    evidence={field: decisions_report.get(field)},
                )
            )
    readiness = _dict(decisions_report.get("readiness"))
    if readiness.get("ready") is not True:
        findings.append(
            _finding(
                finding_id="ontology_decisions_not_ready_for_rerun",
                severity="review_required",
                message="Ontology decisions must be ready before building rerun input.",
                evidence={"readiness": readiness},
            )
        )
    source_answers = _dict(
        _dict(decisions_report.get("source_artifacts")).get("clarification_answers")
    )
    expected_fingerprint = _ontology_answer_fingerprint(answers_report)
    actual_fingerprint = _text(source_answers.get("ontology_answer_fingerprint"))
    if not actual_fingerprint:
        findings.append(
            _finding(
                finding_id="ontology_decisions_answer_fingerprint_missing",
                severity="review_required",
                message=(
                    "Ontology decisions must declare the ontology answer "
                    "fingerprint they were derived from."
                ),
                evidence={"source_ref": source_answers.get("source_ref")},
            )
        )
    elif actual_fingerprint != expected_fingerprint:
        findings.append(
            _finding(
                finding_id="ontology_decisions_answer_fingerprint_mismatch",
                severity="review_required",
                message=(
                    "Ontology decisions must be derived from the current "
                    "clarification answers before they can suppress ontology-gap answers."
                ),
                evidence={
                    "expected": expected_fingerprint,
                    "actual": actual_fingerprint,
                    "source_ref": source_answers.get("source_ref"),
                },
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


def _decision_context(decision: dict[str, Any]) -> dict[str, str]:
    return {
        "decision_id": _text(decision.get("id")),
        "decision_type": _text(decision.get("decision_type")),
        "request_id": _text(decision.get("request_id")),
        "answer_kind": _text(
            decision.get("source_answer_kind"),
            _text(decision.get("decision_type")),
        ),
        "target_artifact": _text(decision.get("target_artifact")),
        "target_ref": _text(decision.get("target_ref")),
        "request_kind": _text(decision.get("request_kind"), "ontology_gap"),
    }


def _terms_from_value(value: Any) -> list[str]:
    if isinstance(value, str):
        term_value = _text(value)
        return [term_value] if term_value else []
    if isinstance(value, list):
        return _text_list(value)
    value_dict = _dict(value)
    terms = _text_list(value_dict.get("terms"))
    term = _text(value_dict.get("term"))
    if term and term not in terms:
        terms.append(term)
    return terms


def _append_project_terms(
    overlay: dict[str, Any],
    *,
    answer: dict[str, Any],
    value: Any,
) -> list[dict[str, Any]]:
    context = _request_context(answer)
    terms = _terms_from_value(value)
    if not terms:
        return [
            _finding(
                finding_id="project_local_term_value_missing",
                severity="review_required",
                message="Project-local term answers must provide explicit term or terms.",
                evidence={
                    "request_id": context["request_id"],
                    "target_ref": context["target_ref"],
                },
            )
        ]
    value_dict = _dict(value)
    for term in terms:
        overlay["ontology_review_hints"]["project_local_terms"].append(
            {
                "term": term,
                "term_scope": _text(value_dict.get("term_scope"), "project_local"),
                **context,
            }
        )
    return []


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


def _append_ontology_decision(
    overlay: dict[str, Any],
    *,
    decision: dict[str, Any],
) -> list[dict[str, Any]]:
    context = _decision_context(decision)
    decision_type = context["decision_type"]
    if _text(decision.get("status")) != "accepted_for_candidate_preview":
        return [
            _finding(
                finding_id="ontology_decision_status_not_preview_accepted",
                severity="review_required",
                message=(
                    "Ontology decision rows must be accepted for candidate preview "
                    "before they can enter rerun overlay hints."
                ),
                evidence={
                    "decision_id": context["decision_id"],
                    "status": decision.get("status"),
                },
            )
        ]
    if _text(decision.get("materialization_intent")) != "rerun_overlay_only":
        return [
            _finding(
                finding_id="ontology_decision_materialization_intent_unsupported",
                severity="review_required",
                message=(
                    "Ontology decision rows must use rerun_overlay_only materialization intent."
                ),
                evidence={
                    "decision_id": context["decision_id"],
                    "materialization_intent": decision.get("materialization_intent"),
                },
            )
        ]
    if decision_type == "propose_project_local_term":
        term = _text(decision.get("term"))
        if not term:
            return [
                _finding(
                    finding_id="ontology_decision_project_local_term_missing",
                    severity="review_required",
                    message="Project-local ontology decisions require term.",
                    evidence={"decision_id": context["decision_id"]},
                )
            ]
        overlay["ontology_review_hints"]["project_local_terms"].append(
            {
                "term": term,
                "term_scope": _text(decision.get("term_scope"), "project_local"),
                **context,
            }
        )
    elif decision_type == "bind_existing_term":
        term = _text(decision.get("term"))
        ontology_ref = _text(decision.get("ontology_ref"))
        if not term or not ontology_ref:
            return [
                _finding(
                    finding_id="ontology_decision_binding_incomplete",
                    severity="review_required",
                    message="Existing-term ontology decisions require term and ontology_ref.",
                    evidence={
                        "decision_id": context["decision_id"],
                        "term": term,
                        "ontology_ref": ontology_ref,
                    },
                )
            ]
        overlay["ontology_review_hints"]["term_bindings"].append(
            {"term": term, "ontology_ref": ontology_ref, **context}
        )
    elif decision_type == "alias_existing_term":
        term = _text(decision.get("term"))
        alias_of = _text(decision.get("alias_of"))
        if not term or not alias_of:
            return [
                _finding(
                    finding_id="ontology_decision_alias_incomplete",
                    severity="review_required",
                    message="Alias ontology decisions require term and alias_of.",
                    evidence={
                        "decision_id": context["decision_id"],
                        "term": term,
                        "alias_of": alias_of,
                    },
                )
            ]
        overlay["ontology_review_hints"]["aliases"].append(
            {"term": term, "alias_of": alias_of, **context}
        )
    elif decision_type == "reject_non_domain_term":
        overlay["ontology_review_hints"]["rejected_terms"].append(
            {
                **context,
                "term": _text(decision.get("term")),
                "reason": _text(decision.get("reason")),
            }
        )
    elif decision_type == "defer_requires_owner":
        overlay["ontology_review_hints"]["deferred_terms"].append(
            {
                **context,
                "term": _text(decision.get("term")),
                "reason": _text(decision.get("reason")),
            }
        )
    else:
        return [
            _finding(
                finding_id="ontology_decision_type_unsupported",
                severity="review_required",
                message="Ontology decision type is unsupported for rerun input overlay.",
                evidence={
                    "decision_id": context["decision_id"],
                    "decision_type": decision_type,
                },
            )
        ]
    return []


def _append_candidate_decision(
    overlay: dict[str, Any],
    *,
    answer: dict[str, Any],
    value: Any,
) -> None:
    context = _request_context(answer)
    overlay["candidate_review_hints"]["other"].append({"value": _public_safe(value), **context})


def _active_frame_from_value(answer: dict[str, Any], value: Any) -> dict[str, Any]:
    context = _request_context(answer)
    value_dict = _dict(value)
    nested_frame = _dict(value_dict.get("active_frame_hints") or value_dict.get("active_frame"))
    if nested_frame:
        return nested_frame
    direct_frame = {
        field: value_dict[field] for field in ACTIVE_FRAME_FIELDS if field in value_dict
    }
    if direct_frame:
        return direct_frame
    target_ref = context["target_ref"]
    field = target_ref.rsplit(".", 1)[-1]
    if field in ACTIVE_FRAME_FIELDS and value not in ({}, [], "", None):
        return {field: value}
    return {}


def _append_active_frame(
    overlay: dict[str, Any],
    *,
    answer: dict[str, Any],
    value: Any,
) -> None:
    context = _request_context(answer)
    frame = _active_frame_from_value(answer, value)
    if frame:
        overlay["intake_overlay"]["active_frame_hints"].append(
            {"value": _public_safe(frame), **context}
        )


def _append_event_storming(
    overlay: dict[str, Any],
    *,
    answer: dict[str, Any],
    value: Any,
) -> None:
    context = _request_context(answer)
    value_dict = _dict(value)
    event_storming = _dict(
        value_dict.get("event_storming_hints") or value_dict.get("event_storming")
    )
    if not event_storming:
        target_ref = context["target_ref"]
        category = target_ref.removeprefix("event_storming_hints.")
        entries = _list(value)
        if not entries:
            entries = _list(value_dict.get("entries"))
        if (
            target_ref.startswith("event_storming_hints.")
            and category in EVENT_STORMING_CATEGORIES
            and entries
        ):
            event_storming = {category: entries}
    if event_storming:
        overlay["intake_overlay"]["event_storming_hints"].append(
            {"value": _public_safe(event_storming), **context}
        )


def _append_candidate_review(
    overlay: dict[str, Any],
    *,
    answer: dict[str, Any],
    value: Any,
) -> None:
    context = _request_context(answer)
    answer_kind = context["answer_kind"]
    if answer_kind in {"accept_preview_criterion", "provide_acceptance_criterion"}:
        overlay["candidate_review_hints"]["acceptance_criteria"].append(
            {"value": _public_safe(value), **context}
        )
    elif answer_kind in {"accept_preview_edge", "reject_preview_edge", "propose_relation"}:
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


def _apply_answer_to_overlay(
    overlay: dict[str, Any], answer: dict[str, Any]
) -> list[dict[str, Any]]:
    answer_kind = _text(answer.get("answer_kind"))
    value = answer.get("value")
    context = _request_context(answer)
    if answer_kind == "propose_project_local_term":
        return _append_project_terms(overlay, answer=answer, value=value)
    elif answer_kind == "bind_existing_term":
        _append_binding(overlay, answer=answer, value=_dict(value))
    elif answer_kind == "alias":
        _append_alias(overlay, answer=answer, value=_dict(value))
    elif answer_kind == "reject":
        if context["request_kind"] == "ontology_gap":
            _append_decision(overlay, answer=answer, bucket="rejected_terms")
        else:
            _append_candidate_decision(overlay, answer=answer, value=value)
    elif answer_kind == "defer":
        if context["request_kind"] == "ontology_gap":
            _append_decision(overlay, answer=answer, bucket="deferred_terms")
        else:
            _append_candidate_decision(overlay, answer=answer, value=value)
    elif answer_kind == "answer_question":
        _append_active_frame(overlay, answer=answer, value=value)
        _append_event_storming(overlay, answer=answer, value=value)
        if context["request_kind"] == "candidate_gap":
            _append_candidate_review(overlay, answer=answer, value=value)
    else:
        _append_candidate_review(overlay, answer=answer, value=value)
    return []


def build_idea_to_spec_answer_rerun_input(
    *,
    answers_report: dict[str, Any],
    ontology_decisions_report: dict[str, Any] | None = None,
    answers_path: Path | None = None,
    ontology_decisions_path: Path | None = None,
) -> dict[str, Any]:
    answers_findings = _validate_answers_report(answers_report)
    findings = list(answers_findings)
    ontology_decision_findings: list[dict[str, Any]] = []
    if ontology_decisions_report is not None:
        ontology_decision_findings = _validate_ontology_decisions_report(
            ontology_decisions_report,
            answers_report=answers_report,
        )
        findings.extend(ontology_decision_findings)
    overlay = _empty_overlay()
    ontology_decisions_valid_for_overlay = (
        ontology_decisions_report is not None and not ontology_decision_findings
    )
    accepted_answers = [
        _dict(answer)
        for answer in _list(answers_report.get("answers"))
        if _text(_dict(answer).get("status")) in ACCEPTED_STATUSES
    ]
    if not answers_findings:
        for answer in accepted_answers:
            if (
                ontology_decisions_valid_for_overlay
                and _request_context(answer)["request_kind"] == "ontology_gap"
            ):
                continue
            findings.extend(_apply_answer_to_overlay(overlay, answer))
        if ontology_decisions_valid_for_overlay:
            decisions = [_dict(item) for item in _list(ontology_decisions_report.get("decisions"))]
            for decision in decisions:
                findings.extend(_append_ontology_decision(overlay, decision=decision))
    source_ref = _relative_ref(answers_path) if answers_path else "inline:clarification_answers"
    ontology_decisions_source_ref = (
        _relative_ref(ontology_decisions_path)
        if ontology_decisions_path
        else "inline:product_ontology_gap_review_decisions"
    )
    ready = not findings
    source_artifacts: dict[str, Any] = {
        "clarification_answers": {
            "artifact_kind": answers_report.get("artifact_kind"),
            "contract_ref": answers_report.get("contract_ref"),
            "source_ref": source_ref,
            "accepted_answer_count": len(accepted_answers),
        }
    }
    if ontology_decisions_report is not None:
        source_artifacts["product_ontology_gap_review_decisions"] = {
            "artifact_kind": ontology_decisions_report.get("artifact_kind"),
            "contract_ref": ontology_decisions_report.get("contract_ref"),
            "source_ref": ontology_decisions_source_ref,
            "decision_count": len(_list(ontology_decisions_report.get("decisions"))),
        }
    return {
        "artifact_kind": "idea_to_spec_answer_rerun_input",
        "schema_version": SCHEMA_VERSION,
        "proposal_id": PROPOSAL_ID,
        "contract_ref": CONTRACT_REF,
        "generated_at": _now_iso(),
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "source_artifacts": source_artifacts,
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
            "ontology_decision_count": (
                len(_list(ontology_decisions_report.get("decisions")))
                if ontology_decisions_report is not None
                else 0
            ),
            "ontology_decision_source": (
                "product_ontology_gap_review_decisions"
                if ontology_decisions_report is not None
                else "clarification_answers"
            ),
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
    parser.add_argument("--ontology-decisions", type=Path)
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, type=Path)
    parser.add_argument("--strict", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_idea_to_spec_answer_rerun_input(
        answers_report=load_json(args.answers),
        ontology_decisions_report=(
            load_json(args.ontology_decisions) if args.ontology_decisions else None
        ),
        answers_path=args.answers,
        ontology_decisions_path=args.ontology_decisions,
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
