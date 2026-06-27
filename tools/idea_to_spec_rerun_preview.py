"""Build a review-only idea-to-spec rerun preview from accepted-answer overlay."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_ID = "0166"
SCHEMA_VERSION = 1
CONTRACT_REF = "specgraph.idea-to-spec.rerun-preview.v0.1"
RERUN_INPUT_CONTRACT_REF = "specgraph.idea-to-spec.answer-rerun-input.v0.1"
INTAKE_CONTRACT_REF = "specgraph.idea-to-spec.event-storming-intake.v0.1"
CANDIDATE_GRAPH_CONTRACT_REF = "specgraph.idea-to-spec.candidate-spec-graph.v0.1"
DEFAULT_RERUN_INPUT_PATH = ROOT / "runs" / "idea_to_spec_answer_rerun_input.json"
DEFAULT_INTAKE_PATH = ROOT / "runs" / "idea_event_storming_intake.json"
DEFAULT_CANDIDATE_GRAPH_PATH = ROOT / "runs" / "candidate_spec_graph.json"
DEFAULT_OUTPUT_PATH = ROOT / "runs" / "idea_to_spec_rerun_preview.json"

ACTIVE_FRAME_LIST_FIELDS = {
    "ontology_refs",
    "domain_refs",
    "context_refs",
    "ontology_layer_refs",
    "model_applicability_refs",
}
EVENT_STORMING_CATEGORIES = (
    "actors",
    "domain_events",
    "commands",
    "policies",
    "external_systems",
    "constraints",
    "risks",
    "assumptions",
    "vocabulary_questions",
)
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
SAFE_PHRASE_SUFFIX_TOKENS = {
    "record",
    "schedule",
    "service",
    "update",
}
SAFE_TOKEN_STEMS = {
    "added": "add",
    "adding": "add",
    "canceled": "cancel",
    "cancelled": "cancel",
    "canceling": "cancel",
    "cancelling": "cancel",
    "recorded": "record",
    "recording": "record",
    "scheduled": "schedule",
    "scheduling": "schedule",
    "updated": "update",
    "updating": "update",
}
MATCH_CONFIDENCE_BY_KIND = {
    "target_ref": "explicit_target",
    "exact": "high",
    "normalized_exact": "high",
    "safe_inflection": "medium",
    "safe_phrase_match": "low",
    "aggregate_target": "aggregate_scope",
}
MATCH_KIND_PRECEDENCE = {
    "aggregate_target": 10,
    "safe_phrase_match": 20,
    "safe_inflection": 30,
    "normalized_exact": 40,
    "exact": 50,
    "target_ref": 60,
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


def _term_key(value: Any) -> str:
    text = _text(value).lower()
    return re.sub(r"[^a-z0-9]+", "", text)


def _term_tokens(value: Any) -> list[str]:
    return re.findall(r"[a-z0-9]+", _text(value).casefold())


def _safe_token_stem(token: str) -> str:
    if token in SAFE_TOKEN_STEMS:
        return SAFE_TOKEN_STEMS[token]
    if len(token) > 4 and token.endswith("s") and not token.endswith(("ss", "us", "is")):
        return token[:-1]
    return token


def _safe_term_tokens(value: Any) -> list[str]:
    return [_safe_token_stem(token) for token in _term_tokens(value)]


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
        "source": "idea_to_spec_rerun_preview",
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


def _validate_inputs(
    *,
    rerun_input: dict[str, Any],
    intake: dict[str, Any],
    candidate_graph: dict[str, Any],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    expected = (
        (
            "rerun_input",
            rerun_input,
            "idea_to_spec_answer_rerun_input",
            RERUN_INPUT_CONTRACT_REF,
        ),
        ("intake", intake, "idea_event_storming_intake", INTAKE_CONTRACT_REF),
        (
            "candidate_graph",
            candidate_graph,
            "candidate_spec_graph",
            CANDIDATE_GRAPH_CONTRACT_REF,
        ),
    )
    for name, artifact, artifact_kind, contract_ref in expected:
        if artifact.get("artifact_kind") != artifact_kind:
            findings.append(
                _finding(
                    finding_id=f"{name}_wrong_artifact_kind",
                    severity="review_required",
                    message=f"{name} must use artifact_kind {artifact_kind}.",
                    evidence={"artifact_kind": artifact.get("artifact_kind")},
                )
            )
        if artifact.get("contract_ref") != contract_ref:
            findings.append(
                _finding(
                    finding_id=f"{name}_contract_ref_unsupported",
                    severity="review_required",
                    message=f"{name} contract_ref must be {contract_ref}.",
                    evidence={"contract_ref": artifact.get("contract_ref")},
                )
            )
        if artifact.get("schema_version") != SCHEMA_VERSION:
            findings.append(
                _finding(
                    finding_id=f"{name}_schema_version_unsupported",
                    severity="review_required",
                    message=f"{name} schema_version must be 1.",
                    evidence={"schema_version": artifact.get("schema_version")},
                )
            )
        for field in ("canonical_mutations_allowed", "tracked_artifacts_written"):
            if artifact.get(field) is not False:
                findings.append(
                    _finding(
                        finding_id=f"{name}_authority_expanded",
                        severity="review_required",
                        message=f"{name} {field} must be false.",
                        evidence={field: artifact.get(field)},
                    )
                )
    readiness = _dict(rerun_input.get("readiness"))
    if readiness.get("ready") is not True:
        findings.append(
            _finding(
                finding_id="rerun_input_not_ready",
                severity="review_required",
                message="Rerun preview requires ready idea_to_spec_answer_rerun_input.",
                evidence={"readiness": readiness},
            )
        )
    return findings


def _merge_unique(existing: list[Any], additions: list[Any]) -> list[Any]:
    merged = list(existing)
    seen = {json.dumps(_public_safe(item), sort_keys=True) for item in merged}
    for item in additions:
        safe_item = _public_safe(item)
        key = json.dumps(safe_item, sort_keys=True)
        if key not in seen:
            merged.append(safe_item)
            seen.add(key)
    return merged


def _merge_active_frame(
    *,
    intake: dict[str, Any],
    overlay: dict[str, Any],
) -> dict[str, Any]:
    preview = _dict(_public_safe(_dict(intake.get("active_frame"))))
    applied_hints: list[dict[str, Any]] = []
    for raw_hint in _list(_dict(overlay.get("intake_overlay")).get("active_frame_hints")):
        hint = _dict(raw_hint)
        value = _dict(hint.get("value"))
        if not value:
            continue
        for key, item in value.items():
            if key in RAW_TRACE_FIELDS or key.startswith("raw_"):
                continue
            if key in ACTIVE_FRAME_LIST_FIELDS:
                preview[key] = _merge_unique(_list(preview.get(key)), _list(item))
            else:
                safe_item = _public_safe(item)
                if safe_item not in ("", None, [], {}):
                    preview[key] = safe_item
        applied_hints.append(
            {
                "request_id": _text(hint.get("request_id")),
                "target_ref": _text(hint.get("target_ref")),
            }
        )
    return {
        "active_frame": preview,
        "applied_hint_count": len(applied_hints),
        "applied_hints": applied_hints,
    }


def _merge_event_storming(
    *,
    intake: dict[str, Any],
    overlay: dict[str, Any],
) -> dict[str, Any]:
    preview = {
        category: _public_safe(_list(_dict(intake.get("event_storming")).get(category)))
        for category in EVENT_STORMING_CATEGORIES
    }
    applied_hints: list[dict[str, Any]] = []
    for raw_hint in _list(_dict(overlay.get("intake_overlay")).get("event_storming_hints")):
        hint = _dict(raw_hint)
        value = _dict(hint.get("value"))
        applied_categories: list[str] = []
        for category in EVENT_STORMING_CATEGORIES:
            additions = _list(value.get(category))
            if additions:
                preview[category] = _merge_unique(preview[category], additions)
                applied_categories.append(category)
        if applied_categories:
            applied_hints.append(
                {
                    "request_id": _text(hint.get("request_id")),
                    "target_ref": _text(hint.get("target_ref")),
                    "categories": applied_categories,
                }
            )
    return {
        "event_storming": preview,
        "applied_hint_count": len(applied_hints),
        "applied_hints": applied_hints,
    }


def _gap_items(candidate_graph: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for raw_node in _list(candidate_graph.get("nodes")):
        node = _dict(raw_node)
        node_id = _text(node.get("id"))
        for raw_gap in _list(node.get("gaps")):
            gap = _dict(raw_gap)
            items.append(
                {
                    "gap": gap,
                    "node_id": node_id,
                    "gap_id": _text(gap.get("id")),
                    "term": _text(gap.get("term")),
                    "source_ref": _text(gap.get("source_ref")),
                    "kind": _text(gap.get("kind")),
                    "statement": _text(gap.get("statement")),
                }
            )
    return items


def _decision_records(
    *,
    overlay: dict[str, Any],
    bucket: str,
    decision: str,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for raw_hint in _list(_dict(overlay.get("ontology_review_hints")).get(bucket)):
        hint = _dict(raw_hint)
        term = _text(hint.get("term"))
        request_id = _text(hint.get("request_id"))
        records.append(
            {
                "decision": decision,
                "decision_id": _text(hint.get("decision_id"))
                or _text(hint.get("id"))
                or request_id,
                "term": term,
                "term_key": _term_key(term),
                "request_id": request_id,
                "answer_kind": _text(hint.get("answer_kind")),
                "target_ref": _text(hint.get("target_ref")),
                "target_artifact": _text(hint.get("target_artifact")),
                "term_scope": _text(hint.get("term_scope")),
                "ontology_ref": _text(hint.get("ontology_ref")),
                "alias_of": _text(hint.get("alias_of")),
            }
        )
    return records


def _ontology_decisions(overlay: dict[str, Any]) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    records.extend(
        _decision_records(
            overlay=overlay,
            bucket="term_bindings",
            decision="bind_existing_term",
        )
    )
    records.extend(_decision_records(overlay=overlay, bucket="aliases", decision="alias"))
    records.extend(
        _decision_records(
            overlay=overlay,
            bucket="project_local_terms",
            decision="project_local_term",
        )
    )
    records.extend(_decision_records(overlay=overlay, bucket="rejected_terms", decision="reject"))
    records.extend(_decision_records(overlay=overlay, bucket="deferred_terms", decision="defer"))
    return [record for record in records if record["term_key"] or record["target_ref"]]


def _match_record(
    *,
    decision: dict[str, Any],
    gap_item: dict[str, Any],
    match_kind: str,
) -> dict[str, Any]:
    decision_term = _text(decision.get("term"))
    gap_term = _text(gap_item.get("term"))
    return {
        "gap_id": _text(gap_item.get("gap_id")),
        "node_id": _text(gap_item.get("node_id")),
        "decision_id": _text(decision.get("decision_id")) or _text(decision.get("request_id")),
        "match_kind": match_kind,
        "confidence": MATCH_CONFIDENCE_BY_KIND.get(match_kind, "unknown"),
        "gap_term": gap_term,
        "decision_term": decision_term,
        "normalized_gap_term": " ".join(_term_tokens(gap_term)),
        "normalized_decision_term": " ".join(_term_tokens(decision_term)),
    }


def _term_match_record(decision: dict[str, Any], gap_item: dict[str, Any]) -> dict[str, Any]:
    decision_term = _text(decision.get("term"))
    gap_term = _text(gap_item.get("term"))
    if not decision_term or not gap_term:
        return {}

    if decision_term.casefold() == gap_term.casefold():
        return _match_record(decision=decision, gap_item=gap_item, match_kind="exact")

    decision_key = _term_key(decision_term)
    gap_key = _term_key(gap_term)
    if decision_key and decision_key == gap_key:
        return _match_record(
            decision=decision,
            gap_item=gap_item,
            match_kind="normalized_exact",
        )

    decision_tokens = _safe_term_tokens(decision_term)
    gap_tokens = _safe_term_tokens(gap_term)
    if decision_tokens and decision_tokens == gap_tokens:
        return _match_record(
            decision=decision,
            gap_item=gap_item,
            match_kind="safe_inflection",
        )

    if len(decision_tokens) >= 2 and gap_tokens[: len(decision_tokens)] == decision_tokens:
        extra_tokens = gap_tokens[len(decision_tokens) :]
        if len(extra_tokens) == 1 and extra_tokens[0] in SAFE_PHRASE_SUFFIX_TOKENS:
            return _match_record(
                decision=decision,
                gap_item=gap_item,
                match_kind="safe_phrase_match",
            )
    return {}


def _gap_match(decision: dict[str, Any], gap_item: dict[str, Any]) -> dict[str, Any]:
    target_ref = _text(decision.get("target_ref"))
    decision_kind = _text(decision.get("decision"))
    if target_ref == "candidate_graph.gaps" and decision_kind in {"reject", "defer"}:
        return _match_record(decision=decision, gap_item=gap_item, match_kind="aggregate_target")
    node_gap_ref = f"{_text(gap_item.get('node_id'))}.gaps.{_text(gap_item.get('gap_id'))}"
    if target_ref and target_ref in {
        _text(gap_item.get("gap_id")),
        _text(gap_item.get("source_ref")),
        node_gap_ref,
    }:
        return _match_record(decision=decision, gap_item=gap_item, match_kind="target_ref")
    return _term_match_record(decision, gap_item)


def _match_precedence(match_record: dict[str, Any]) -> int:
    return MATCH_KIND_PRECEDENCE.get(_text(match_record.get("match_kind")), 0)


def _best_gap_match(
    decisions: list[dict[str, Any]],
    gap_item: dict[str, Any],
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    best_decision: dict[str, Any] | None = None
    best_evidence: dict[str, Any] = {}
    best_precedence = -1
    for decision in decisions:
        evidence = _gap_match(decision, gap_item)
        if not evidence:
            continue
        precedence = _match_precedence(evidence)
        if precedence > best_precedence:
            best_decision = decision
            best_evidence = evidence
            best_precedence = precedence
    return best_decision, best_evidence


def _matches_gap(decision: dict[str, Any], gap_item: dict[str, Any]) -> bool:
    return bool(_gap_match(decision, gap_item))


def _ontology_gap_preview(
    *,
    candidate_graph: dict[str, Any],
    overlay: dict[str, Any],
) -> dict[str, Any]:
    decisions = _ontology_decisions(overlay)
    resolved: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    for gap_item in _gap_items(candidate_graph):
        if gap_item["kind"] != "ontology_gap":
            continue
        matching_decision, matching_evidence = _best_gap_match(decisions, gap_item)
        if matching_decision:
            preview = {
                key: value
                for key, value in matching_decision.items()
                if key != "term_key" and value not in ("", None, [], {})
            }
            match_preview = _public_safe(matching_evidence)
            gap_record = {
                "gap_id": gap_item["gap_id"],
                "node_id": gap_item["node_id"],
                "term": gap_item["term"],
                "source_ref": gap_item["source_ref"],
                "decision_id": match_preview.get("decision_id"),
                "decision_term": match_preview.get("decision_term"),
                "match_kind": match_preview.get("match_kind"),
                "confidence": match_preview.get("confidence"),
                "match": match_preview,
            }
            gap_record = {
                key: value for key, value in gap_record.items() if value not in ("", None, [], {})
            }
            if _text(matching_decision.get("decision")) == "defer":
                unresolved.append(
                    {
                        **gap_record,
                        "deferral_preview": preview,
                    }
                )
                continue
            resolved.append(
                {
                    **gap_record,
                    "resolution_preview": preview,
                }
            )
        else:
            unresolved.append(
                {
                    "gap_id": gap_item["gap_id"],
                    "node_id": gap_item["node_id"],
                    "term": gap_item["term"],
                    "source_ref": gap_item["source_ref"],
                }
            )
    return {
        "decision_count": len(decisions),
        "resolved_ontology_gaps": resolved,
        "unresolved_ontology_gaps": unresolved,
        "resolved_ontology_gap_count": len(resolved),
        "unresolved_ontology_gap_count": len(unresolved),
    }


def _candidate_hint_records(overlay: dict[str, Any]) -> list[dict[str, Any]]:
    hints = _dict(overlay.get("candidate_review_hints"))
    records: list[dict[str, Any]] = []
    for bucket in ("acceptance_criteria", "graph_edges", "claim_reviews", "other"):
        for raw_hint in _list(hints.get(bucket)):
            hint = _dict(raw_hint)
            record = {
                "bucket": bucket,
                "request_id": _text(hint.get("request_id")),
                "answer_kind": _text(hint.get("answer_kind")),
                "target_artifact": _text(hint.get("target_artifact")),
                "target_ref": _text(hint.get("target_ref")),
                "request_kind": _text(hint.get("request_kind")),
                "value": _public_safe(hint.get("value")),
            }
            records.append(
                {key: value for key, value in record.items() if value not in ("", None, [], {})}
            )
    return records


def _candidate_gap_target_ref(gap_item: dict[str, Any]) -> str:
    return f"{_text(gap_item.get('node_id'))}.gaps.{_text(gap_item.get('gap_id'))}"


def _candidate_hint_matches_gap(
    hint: dict[str, Any],
    gap_item: dict[str, Any],
) -> bool:
    if _text(hint.get("request_kind")) != "candidate_gap":
        return False
    target_ref = _text(hint.get("target_ref"))
    if not target_ref:
        return False
    return target_ref == _candidate_gap_target_ref(gap_item)


def _has_substantive_public_value(value: Any) -> bool:
    safe_value = _public_safe(value)
    if isinstance(safe_value, str):
        return bool(_text(safe_value))
    if isinstance(safe_value, list):
        return any(_has_substantive_public_value(item) for item in safe_value)
    if isinstance(safe_value, dict):
        return any(_has_substantive_public_value(item) for item in safe_value.values())
    return safe_value not in (None, "", [], {})


def _candidate_hint_has_resolution_value(hint: dict[str, Any]) -> bool:
    return _has_substantive_public_value(hint.get("value"))


def _candidate_hint_is_deferred(hint: dict[str, Any]) -> bool:
    return _text(hint.get("answer_kind")) in {"defer", "defer_candidate"}


def _candidate_hint_is_rejection(hint: dict[str, Any]) -> bool:
    return _text(hint.get("answer_kind")) in {"reject", "reject_candidate"}


def _candidate_hint_rank(hint: dict[str, Any]) -> int:
    if _candidate_hint_is_deferred(hint):
        return 10
    if _candidate_hint_is_rejection(hint):
        return 30
    if _candidate_hint_has_resolution_value(hint):
        return 20
    return 0


def _candidate_resolution_kind(
    *,
    hint: dict[str, Any],
    gap_item: dict[str, Any],
) -> str:
    answer_kind = _text(hint.get("answer_kind"))
    gap_kind = _text(gap_item.get("kind"))
    gap_id = _text(gap_item.get("gap_id"))
    statement = _text(gap_item.get("statement")).casefold()
    if answer_kind in {"reject", "reject_candidate"}:
        return "gap_rejected"
    if "risk" in gap_kind or "risk" in gap_id:
        return "risk_accepted"
    if (
        "enforcement" in gap_kind
        or "enforcement" in gap_id
        or "enforcement mechanism" in statement
        or gap_kind in {"implementation_gap", "candidate_gap"}
    ):
        return "enforcement_mechanism_added"
    return "candidate_context_added"


def _candidate_match_preview(
    *,
    hint: dict[str, Any],
    gap_item: dict[str, Any],
) -> dict[str, Any]:
    return {
        "gap_id": _text(gap_item.get("gap_id")),
        "node_id": _text(gap_item.get("node_id")),
        "request_id": _text(hint.get("request_id")),
        "answer_kind": _text(hint.get("answer_kind")),
        "match_kind": "target_ref",
        "confidence": MATCH_CONFIDENCE_BY_KIND["target_ref"],
        "target_ref": _candidate_gap_target_ref(gap_item),
    }


def _candidate_gap_preview(
    *,
    candidate_graph: dict[str, Any],
    overlay: dict[str, Any],
) -> dict[str, Any]:
    hints = _candidate_hint_records(overlay)
    resolved: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    for gap_item in _gap_items(candidate_graph):
        if gap_item["kind"] == "ontology_gap":
            continue
        matching_hints = [
            hint for hint in hints if _candidate_hint_matches_gap(hint=hint, gap_item=gap_item)
        ]
        matching_hint = max(matching_hints, key=_candidate_hint_rank) if matching_hints else None
        base_record = {
            "gap_id": gap_item["gap_id"],
            "node_id": gap_item["node_id"],
            "kind": gap_item["kind"],
            "source_ref": gap_item["source_ref"],
            "statement": gap_item["statement"],
            "target_ref": _candidate_gap_target_ref(gap_item),
        }
        base_record = {
            key: value for key, value in base_record.items() if value not in ("", None, [], {})
        }
        if not matching_hint:
            unresolved.append(base_record)
            continue
        hint_preview = {
            key: value for key, value in matching_hint.items() if value not in ("", None, [], {})
        }
        match_preview = _candidate_match_preview(hint=matching_hint, gap_item=gap_item)
        if _candidate_hint_is_deferred(matching_hint):
            unresolved.append(
                {
                    **base_record,
                    "request_id": _text(matching_hint.get("request_id")),
                    "answer_kind": _text(matching_hint.get("answer_kind")),
                    "match_kind": "target_ref",
                    "confidence": MATCH_CONFIDENCE_BY_KIND["target_ref"],
                    "match": match_preview,
                    "deferral_preview": hint_preview,
                }
            )
            continue
        if not _candidate_hint_is_rejection(
            matching_hint
        ) and not _candidate_hint_has_resolution_value(matching_hint):
            unresolved.append(
                {
                    **base_record,
                    "request_id": _text(matching_hint.get("request_id")),
                    "answer_kind": _text(matching_hint.get("answer_kind")),
                    "match_kind": "target_ref",
                    "confidence": MATCH_CONFIDENCE_BY_KIND["target_ref"],
                    "match": match_preview,
                    "review_preview": hint_preview,
                }
            )
            continue
        resolved.append(
            {
                **base_record,
                "request_id": _text(matching_hint.get("request_id")),
                "answer_kind": _text(matching_hint.get("answer_kind")),
                "resolution_kind": _candidate_resolution_kind(
                    hint=matching_hint,
                    gap_item=gap_item,
                ),
                "match_kind": "target_ref",
                "confidence": MATCH_CONFIDENCE_BY_KIND["target_ref"],
                "match": match_preview,
                "resolution_preview": hint_preview,
            }
        )
    return {
        "candidate_hint_count": len(hints),
        "resolved_candidate_gaps": resolved,
        "unresolved_candidate_gaps": unresolved,
        "resolved_candidate_gap_count": len(resolved),
        "unresolved_candidate_gap_count": len(unresolved),
    }


def _candidate_review_preview(overlay: dict[str, Any]) -> dict[str, Any]:
    hints = _dict(overlay.get("candidate_review_hints"))
    return {
        "acceptance_criteria": _public_safe(_list(hints.get("acceptance_criteria"))),
        "graph_edges": _public_safe(_list(hints.get("graph_edges"))),
        "claim_reviews": _public_safe(_list(hints.get("claim_reviews"))),
        "other": _public_safe(_list(hints.get("other"))),
        "hint_count": sum(len(_list(hints.get(bucket))) for bucket in hints),
    }


def _candidate_quality_preview(
    ontology_gap_preview: dict[str, Any],
    candidate_gap_preview: dict[str, Any],
) -> dict[str, Any]:
    unresolved_ontology_count = _int(ontology_gap_preview.get("unresolved_ontology_gap_count"))
    resolved_ontology_count = _int(ontology_gap_preview.get("resolved_ontology_gap_count"))
    unresolved_candidate_count = _int(candidate_gap_preview.get("unresolved_candidate_gap_count"))
    resolved_candidate_count = _int(candidate_gap_preview.get("resolved_candidate_gap_count"))
    unresolved_count = unresolved_ontology_count + unresolved_candidate_count
    resolved_count = resolved_ontology_count + resolved_candidate_count
    if unresolved_count == 0 and resolved_count > 0:
        review_state = "candidate_quality_improved"
        ontology_gap_state = (
            "all_preview_resolved" if resolved_ontology_count > 0 else "no_ontology_gaps"
        )
        candidate_gap_state = (
            "all_preview_resolved" if resolved_candidate_count > 0 else "no_candidate_gaps"
        )
    elif resolved_count > 0:
        review_state = "candidate_quality_partially_improved"
        ontology_gap_state = (
            "partially_preview_resolved"
            if unresolved_ontology_count
            else "all_preview_resolved"
            if resolved_ontology_count
            else "no_ontology_gaps"
        )
        candidate_gap_state = (
            "partially_preview_resolved"
            if unresolved_candidate_count
            else "all_preview_resolved"
            if resolved_candidate_count
            else "no_candidate_gaps"
        )
    elif unresolved_ontology_count > 0 and unresolved_candidate_count > 0:
        review_state = "candidate_quality_blocked_by_gaps"
        ontology_gap_state = "unresolved"
        candidate_gap_state = "unresolved"
    elif unresolved_ontology_count > 0:
        review_state = "candidate_quality_blocked_by_ontology_gaps"
        ontology_gap_state = "unresolved"
        candidate_gap_state = "no_candidate_gaps"
    elif unresolved_candidate_count > 0:
        review_state = "candidate_quality_blocked_by_candidate_gaps"
        ontology_gap_state = "no_ontology_gaps"
        candidate_gap_state = "unresolved"
    else:
        review_state = "candidate_quality_unchanged"
        ontology_gap_state = "no_ontology_gaps"
        candidate_gap_state = "no_candidate_gaps"
    return {
        "review_state": review_state,
        "ontology_gap_state": ontology_gap_state,
        "candidate_gap_state": candidate_gap_state,
        "resolved_ontology_gap_count": resolved_ontology_count,
        "unresolved_ontology_gap_count": unresolved_ontology_count,
        "resolved_candidate_gap_count": resolved_candidate_count,
        "unresolved_candidate_gap_count": unresolved_candidate_count,
        "candidate_quality_metric": (
            "candidate_gap_resolution_preview"
            if resolved_candidate_count or unresolved_candidate_count
            else "ontology_gap_resolution_preview"
        ),
        "canonical_mutations_allowed": False,
    }


def build_idea_to_spec_rerun_preview(
    *,
    rerun_input: dict[str, Any],
    intake: dict[str, Any],
    candidate_graph: dict[str, Any],
    rerun_input_path: Path | None = None,
    intake_path: Path | None = None,
    candidate_graph_path: Path | None = None,
) -> dict[str, Any]:
    findings = _validate_inputs(
        rerun_input=rerun_input,
        intake=intake,
        candidate_graph=candidate_graph,
    )
    overlay = _dict(rerun_input.get("rerun_input_overlay")) if not findings else {}
    active_frame_preview = _merge_active_frame(intake=intake, overlay=overlay)
    event_storming_preview = _merge_event_storming(intake=intake, overlay=overlay)
    ontology_gap_preview = _ontology_gap_preview(
        candidate_graph=candidate_graph,
        overlay=overlay,
    )
    candidate_gap_preview = _candidate_gap_preview(
        candidate_graph=candidate_graph,
        overlay=overlay,
    )
    candidate_review_preview = _candidate_review_preview(overlay)
    candidate_quality_preview = _candidate_quality_preview(
        ontology_gap_preview,
        candidate_gap_preview,
    )
    ready = not findings
    return {
        "artifact_kind": "idea_to_spec_rerun_preview",
        "schema_version": SCHEMA_VERSION,
        "proposal_id": PROPOSAL_ID,
        "contract_ref": CONTRACT_REF,
        "generated_at": _now_iso(),
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "source_artifacts": {
            "rerun_input": {
                "artifact_kind": rerun_input.get("artifact_kind"),
                "contract_ref": rerun_input.get("contract_ref"),
                "source_ref": (
                    _relative_ref(rerun_input_path)
                    if rerun_input_path
                    else "inline:idea_to_spec_answer_rerun_input"
                ),
            },
            "intake": {
                "artifact_kind": intake.get("artifact_kind"),
                "contract_ref": intake.get("contract_ref"),
                "source_ref": (
                    _relative_ref(intake_path)
                    if intake_path
                    else "inline:idea_event_storming_intake"
                ),
            },
            "candidate_graph": {
                "artifact_kind": candidate_graph.get("artifact_kind"),
                "contract_ref": candidate_graph.get("contract_ref"),
                "source_ref": (
                    _relative_ref(candidate_graph_path)
                    if candidate_graph_path
                    else "inline:candidate_spec_graph"
                ),
            },
        },
        "rerun_preview": {
            "active_frame_preview": active_frame_preview,
            "event_storming_preview": event_storming_preview,
            "ontology_gap_preview": ontology_gap_preview,
            "candidate_gap_preview": candidate_gap_preview,
            "candidate_review_preview": candidate_review_preview,
            "candidate_quality_preview": candidate_quality_preview,
        },
        "readiness": {
            "ready": ready,
            "review_state": "rerun_preview_ready" if ready else "rerun_preview_review_required",
            "blocked_by": [finding["finding_id"] for finding in findings],
            "next_artifact": "runs/idea_event_storming_intake.json",
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
            "status": "rerun_preview_ready" if ready else "rerun_preview_review_required",
            "active_frame_hint_count": active_frame_preview["applied_hint_count"],
            "event_storming_hint_count": event_storming_preview["applied_hint_count"],
            "ontology_decision_count": ontology_gap_preview["decision_count"],
            "resolved_ontology_gap_count": ontology_gap_preview["resolved_ontology_gap_count"],
            "unresolved_ontology_gap_count": ontology_gap_preview["unresolved_ontology_gap_count"],
            "resolved_candidate_gap_count": candidate_gap_preview["resolved_candidate_gap_count"],
            "unresolved_candidate_gap_count": candidate_gap_preview[
                "unresolved_candidate_gap_count"
            ],
            "candidate_quality_review_state": candidate_quality_preview["review_state"],
            "candidate_review_hint_count": candidate_review_preview["hint_count"],
            "finding_count": len(findings),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rerun-input", default=DEFAULT_RERUN_INPUT_PATH, type=Path)
    parser.add_argument("--intake", default=DEFAULT_INTAKE_PATH, type=Path)
    parser.add_argument("--candidate-graph", default=DEFAULT_CANDIDATE_GRAPH_PATH, type=Path)
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, type=Path)
    parser.add_argument("--strict", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_idea_to_spec_rerun_preview(
        rerun_input=load_json(args.rerun_input),
        intake=load_json(args.intake),
        candidate_graph=load_json(args.candidate_graph),
        rerun_input_path=args.rerun_input,
        intake_path=args.intake,
        candidate_graph_path=args.candidate_graph,
    )
    write_json(report, args.output)
    summary = _dict(report.get("summary"))
    print(
        f"{summary.get('status', 'unknown')}: "
        f"{summary.get('resolved_ontology_gap_count', 0)} ontology gaps preview-resolved -> "
        f"{_relative_ref(args.output)}"
    )
    if args.strict and not _dict(report.get("readiness")).get("ready"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
