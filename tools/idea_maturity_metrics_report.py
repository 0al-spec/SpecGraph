"""Build Idea-to-Spec maturity metrics from review-only lifecycle artifacts."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_ID = "0178"
READINESS_EXPLAINERS_PROPOSAL_ID = "0180"
METRICS_CONTRACT_PROPOSAL_ID = "0181"
SCHEMA_VERSION = 1
CONTRACT_REF = "specgraph.idea-to-spec.maturity-metrics-report.v0.1"
METRIC_PACK_ID = "idea_to_spec_maturity"
METRIC_PACK_REF = "metrics.idea_to_spec_maturity.v0.1"
METRICS_RFC_REF = "Metrics/IDEA_MATURITY_METRICS.md"
METRICS_SCHEMA_REF = "schemas/idea_maturity_metrics_report.schema.json"
METRICS_VALIDATION_REPORT_SCHEMA_REF = "schemas/idea_maturity_metrics_validation_report.schema.json"
METRICS_VALIDATOR_ID = "metrics.idea_maturity_metrics.validator.v0.1"
METRICS_VALIDATOR_VERSION = "0.1.0"
METRICS_COMPATIBILITY_POLICY = "additive_v1"
METRICS_COMPATIBILITY_POLICY_REF = "VALIDATOR_CONTRACT.md#compatibility-policy"
AUTHORITY_STATE = "draft_reference"
STALL_DWELL_SECONDS = 86_400

DEFAULT_PATHS = {
    "intake": ROOT / "runs" / "idea_event_storming_intake.json",
    "candidate_graph": ROOT / "runs" / "candidate_spec_graph.json",
    "pre_sib": ROOT / "runs" / "pre_sib_coherence_report.json",
    "clarification_requests": ROOT / "runs" / "idea_to_spec_clarification_requests.json",
    "clarification_answers": ROOT / "runs" / "idea_to_spec_clarification_answers.json",
    "ontology_decisions": ROOT / "runs" / "product_ontology_gap_review_decisions.json",
    "rerun_input": ROOT / "runs" / "idea_to_spec_answer_rerun_input.json",
    "rerun_preview": ROOT / "runs" / "idea_to_spec_rerun_preview.json",
    "rerun_materialization": ROOT / "runs" / "idea_to_spec_rerun_materialization.json",
    "promotion_gate": ROOT / "runs" / "idea_to_spec_promotion_gate.json",
    "repair_session": ROOT / "runs" / "idea_to_spec_repair_session.json",
    "repaired_handoff": ROOT / "runs" / "repaired_candidate_promotion_handoff_report.json",
    "repaired_candidate_graph": ROOT / "runs" / "repaired_candidate_spec_graph.json",
    "repaired_pre_sib": ROOT / "runs" / "repaired_pre_sib_coherence_report.json",
    "repaired_active_candidate": ROOT / "runs" / "repaired_active_idea_to_spec_candidate.json",
    "repaired_promotion_gate": ROOT / "runs" / "repaired_idea_to_spec_promotion_gate.json",
    "repaired_repair_session": ROOT / "runs" / "repaired_idea_to_spec_repair_session.json",
    "specspace_draft_import_preview": ROOT / "runs" / "specspace_repair_draft_import_preview.json",
    "specspace_rerun_request": ROOT / "runs" / "idea_to_spec_repair_rerun_requests.json",
    "approval_intent": ROOT / "runs" / "idea_to_spec_candidate_approval_intents.json",
    "repair_rerun_execution": ROOT / "runs" / "platform_product_repair_rerun_execution_report.json",
    "repair_rerun_publication": ROOT
    / "runs"
    / "platform_product_repair_rerun_publication_report.json",
    "approval_execution": ROOT / "runs" / "platform_candidate_approval_execution_report.json",
    "candidate_approval_decision": ROOT / "runs" / "candidate_approval_decision.json",
    "promotion_request": ROOT / "runs" / "graph_repository_promotion_request.json",
    "promotion_execution": ROOT / "runs" / "product_candidate_promotion_execution_report.json",
    "review_status": ROOT / "runs" / "product_candidate_promotion_review_status_report.json",
    "read_model_publication": ROOT
    / "runs"
    / "product_candidate_promotion_read_model_publication_report.json",
}
DEFAULT_OUTPUT_PATH = ROOT / "runs" / "idea_maturity_metrics_report.json"

AUTHORITY_BOUNDARY_KEYS = (
    "may_mutate_canonical_specs",
    "may_write_ontology_package",
    "may_accept_ontology_terms",
    "may_create_branch_or_commit",
    "may_open_pull_request",
    "may_merge_pull_request",
    "may_publish_read_model",
    "may_execute_prompt_agent",
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

ONTOLOGY_MATCH_KIND_KEYS = (
    "exact",
    "normalized_exact",
    "safe_inflection",
    "safe_phrase_match",
    "target_ref",
    "aggregate_target",
    "manual_bind",
    "manual_alias",
    "project_local_term",
    "reject",
    "defer",
    "other",
)

CANDIDATE_RESOLUTION_KIND_KEYS = (
    "risk_accepted",
    "enforcement_mechanism_added",
    "context_supplied",
    "gap_rejected",
    "other",
)

PLATFORM_REPORT_KEYS = {
    "repair_rerun_execution",
    "repair_rerun_publication",
    "approval_execution",
    "promotion_execution",
    "review_status",
    "read_model_publication",
}

SUPERSEDED_REPORT_KEYS = {
    "pre_sib": "repaired_pre_sib",
    "promotion_gate": "repaired_promotion_gate",
    "repair_session": "repaired_repair_session",
}

READINESS_EXPLAINER_LIMIT = 32
READINESS_SEVERITY_VALUES = {"low", "medium", "high"}
READINESS_SEVERITY_ALIASES = {
    "blocking": "high",
    "critical": "high",
    "error": "high",
    "review_required": "medium",
    "warning": "medium",
    "warn": "medium",
    "info": "low",
    "informational": "low",
}

SUMMARY_METRIC_KEYS = (
    "lifecycle_state",
    "clarification_question_count",
    "blocking_question_count",
    "review_required_question_count",
    "answered_question_count",
    "accepted_answer_count",
    "deferred_answer_count",
    "invalid_answer_count",
    "materialized_answer_count",
    "unmaterialized_answer_count",
    "answer_materialization_rate",
    "ontology_gap_count_initial",
    "ontology_gap_resolved_count",
    "ontology_gap_unresolved_count",
    "ontology_gap_resolution_rate",
    "candidate_gap_count_initial",
    "candidate_gap_resolved_count",
    "candidate_gap_unresolved_count",
    "candidate_gap_closure_rate",
    "candidate_node_count",
    "promotion_path_count",
    "remaining_blocker_count",
    "manual_handoff_count",
    "operator_command_count",
    "failed_gate_count",
    "stale_ref_count",
    "dry_run_count",
    "rerun_count",
    "rerun_request_count",
    "approval_attempt_count",
    "time_to_first_candidate_seconds",
    "time_to_first_materialization_seconds",
    "time_to_approval_ready_seconds",
    "last_progress_at",
    "stalled_phase",
    "candidate_approval_state",
    "candidate_approval_intent_state",
    "candidate_approval_decision_state",
    "platform_promotion_state",
    "promotion_request_state",
    "promotion_execution_state",
    "review_status",
    "review_pr_number",
    "review_merge_commit_sha",
    "read_model_publication_state",
    "published_file_count",
    "published_manifest_digest",
)

SOURCE_REF_CHECKS = (
    ("clarification_answers", "clarification_requests", "clarification_requests"),
    ("ontology_decisions", "clarification_answers", "clarification_answers"),
    ("rerun_input", "clarification_answers", "clarification_answers"),
    ("rerun_input", "product_ontology_gap_review_decisions", "ontology_decisions"),
    ("rerun_preview", "rerun_input", "rerun_input"),
    ("rerun_materialization", "rerun_preview", "rerun_preview"),
    ("repaired_handoff", "rerun_materialization", "rerun_materialization"),
    ("repaired_repair_session", "rerun_materialization", "rerun_materialization"),
    ("repaired_repair_session", "active_candidate", "repaired_active_candidate"),
    ("repaired_repair_session", "promotion_gate", "repaired_promotion_gate"),
)


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _repo_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT / path


def _relative_ref(path: Path | None) -> str | None:
    if path is None:
        return None
    repo_path = _repo_path(path)
    try:
        return repo_path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return repo_path.as_posix()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any, default: str = "") -> str:
    return value.strip() if isinstance(value, str) and value.strip() else default


def _text_list(value: Any) -> list[str]:
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:96] or "unknown"


def _tokenize(value: str) -> set[str]:
    return {token for token in re.split(r"[^a-z0-9]+", value.lower()) if token}


def _status_has_token(status: str, token: str) -> bool:
    tokens = _tokenize(status)
    if not tokens:
        return False
    if token == "blocked" and ("unblocked" in tokens or tokens == {"not", "blocked"}):
        return False
    return token in tokens


def _status_is_blocked(status: str) -> bool:
    return _status_has_token(status, "blocked")


def _status_is_failed(status: str) -> bool:
    return _status_has_token(status, "failed") or _status_has_token(status, "failure")


def _int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _rate(numerator: int, denominator: int) -> float | None:
    if denominator <= 0:
        return None
    return round(numerator / denominator, 6)


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


def _parse_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _artifact_time(artifact: dict[str, Any]) -> datetime | None:
    summary = _dict(artifact.get("summary"))
    candidates = (
        artifact.get("generated_at"),
        artifact.get("created_at"),
        artifact.get("updated_at"),
        artifact.get("completed_at"),
        summary.get("generated_at"),
        summary.get("created_at"),
        summary.get("updated_at"),
        summary.get("completed_at"),
    )
    for candidate in candidates:
        parsed = _parse_time(candidate)
        if parsed is not None:
            return parsed
    return None


def _seconds_between(start: datetime | None, end: datetime | None) -> float | None:
    if start is None or end is None:
        return None
    seconds = (end - start).total_seconds()
    if seconds < 0:
        return None
    return round(seconds, 3)


def _authority_boundary() -> dict[str, bool]:
    return {key: False for key in AUTHORITY_BOUNDARY_KEYS}


def _privacy_boundary() -> dict[str, object]:
    return {
        "contains_human_operator_identity": False,
        "join_to_identity_allowed": False,
        "minimum_aggregation_subject": "candidate_run",
        "raw_prompt_or_operator_text_included": False,
    }


def _metrics_contract_metadata() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "schema_ref": METRICS_SCHEMA_REF,
        "validation_report_schema_ref": METRICS_VALIDATION_REPORT_SCHEMA_REF,
        "validator_id": METRICS_VALIDATOR_ID,
        "validator_version": METRICS_VALIDATOR_VERSION,
        "compatibility_policy": METRICS_COMPATIBILITY_POLICY,
        "compatibility_policy_ref": METRICS_COMPATIBILITY_POLICY_REF,
        "metrics_rfc_ref": METRICS_RFC_REF,
        "proposal_id": METRICS_CONTRACT_PROPOSAL_ID,
    }


def _finding(
    *,
    finding_id: str,
    severity: str,
    message: str,
    source: str = "idea_maturity_metrics_report",
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "finding_id": finding_id,
        "severity": severity,
        "message": message,
        "source": source,
        "evidence": _public_safe(evidence or {}),
    }


def load_json(path: Path) -> dict[str, Any]:
    repo_path = _repo_path(path)
    payload = json.loads(repo_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def write_json(payload: dict[str, Any], path: Path) -> None:
    output_path = _repo_path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _source_artifact(
    key: str,
    path: Path,
    artifact: dict[str, Any] | None,
    *,
    status: str,
    error: str | None = None,
) -> dict[str, Any]:
    source: dict[str, Any] = {
        "artifact_key": key,
        "source_ref": _relative_ref(path),
        "status": status,
    }
    if error:
        source["error"] = error
    if artifact is not None:
        source.update(
            {
                "artifact_kind": artifact.get("artifact_kind"),
                "contract_ref": artifact.get("contract_ref"),
                "proposal_id": artifact.get("proposal_id"),
                "schema_version": artifact.get("schema_version"),
                "summary": _public_safe(_dict(artifact.get("summary"))),
                "readiness": _public_safe(_dict(artifact.get("readiness"))),
                "generated_at": artifact.get("generated_at"),
            }
        )
    return source


def _load_sources(paths: dict[str, Path]) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    artifacts: dict[str, dict[str, Any]] = {}
    source_artifacts: dict[str, Any] = {}
    for key, path in paths.items():
        repo_path = _repo_path(path)
        if not repo_path.is_file():
            source_artifacts[key] = _source_artifact(key, path, None, status="not_available")
            continue
        try:
            artifact = load_json(path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            source_artifacts[key] = _source_artifact(
                key,
                path,
                None,
                status="malformed",
                error=str(exc),
            )
            continue
        artifacts[key] = artifact
        source_artifacts[key] = _source_artifact(key, path, artifact, status="loaded")
    return artifacts, source_artifacts


def _summary(artifacts: dict[str, dict[str, Any]], key: str) -> dict[str, Any]:
    return _dict(_dict(artifacts.get(key)).get("summary"))


def _readiness(artifacts: dict[str, dict[str, Any]], key: str) -> dict[str, Any]:
    return _dict(_dict(artifacts.get(key)).get("readiness"))


def _summary_int(artifacts: dict[str, dict[str, Any]], key: str, field: str) -> int:
    return _int(_summary(artifacts, key).get(field))


def _nodes(artifact: dict[str, Any] | None) -> list[dict[str, Any]]:
    return [node for node in _list(_dict(artifact).get("nodes")) if isinstance(node, dict)]


def _all_gaps(candidate_graph: dict[str, Any] | None) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    for node in _nodes(candidate_graph):
        for gap in _list(node.get("gaps")):
            if isinstance(gap, dict):
                gaps.append(gap)
    return gaps


def _candidate_identity(artifacts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    active = _dict(artifacts.get("repaired_active_candidate")) or _dict(
        artifacts.get("active_candidate")
    )
    candidate = _dict(active.get("candidate"))
    if candidate:
        return _public_safe(
            {
                "candidate_id": _text(candidate.get("candidate_id"), "unknown-candidate"),
                "workspace_route": _text(candidate.get("public_route"), "/unknown"),
                "workflow_lane": candidate.get("workflow_lane"),
                "governance_profile": candidate.get("governance_profile"),
                "target_repository_role": candidate.get("target_repository_role"),
            }
        )
    session = _dict(_dict(artifacts.get("repaired_repair_session")).get("session"))
    if session:
        return _public_safe(
            {
                "candidate_id": _text(session.get("candidate_id"), "unknown-candidate"),
                "workspace_route": _text(session.get("workspace_route"), "/unknown"),
                "workflow_lane": session.get("workflow_lane"),
                "governance_profile": session.get("governance_profile"),
                "target_repository_role": session.get("target_repository_role"),
            }
        )
    intake_workspace = _dict(
        _dict(_dict(artifacts.get("intake")).get("source_intake")).get("workspace")
    )
    return _public_safe(
        {
            "candidate_id": _text(intake_workspace.get("candidate_id"), "unknown-candidate"),
            "workspace_route": _text(intake_workspace.get("public_route"), "/unknown"),
        }
    )


def _resolution_records(
    artifacts: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    materialization = _dict(artifacts.get("rerun_materialization"))
    preview = _dict(materialization.get("materialization_preview"))
    delta = _dict(preview.get("delta"))
    ontology_records = [
        record
        for record in _list(delta.get("ontology_resolution_records"))
        if isinstance(record, dict)
    ]
    candidate_records = [
        record
        for record in _list(delta.get("candidate_resolution_records"))
        if isinstance(record, dict)
    ]

    candidate_graph_preview = _dict(preview.get("candidate_graph_preview"))
    for node in _nodes(candidate_graph_preview):
        ontology_records.extend(
            record
            for record in _list(node.get("ontology_gap_resolutions"))
            if isinstance(record, dict)
        )
        candidate_records.extend(
            record
            for record in _list(node.get("candidate_gap_resolutions"))
            if isinstance(record, dict)
        )
    return _dedupe_records(ontology_records), _dedupe_records(candidate_records)


def _dedupe_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for record in records:
        key = (
            record.get("node_id") or _dict(record.get("match")).get("node_id"),
            record.get("gap_id"),
            record.get("decision_id") or record.get("request_id"),
            record.get("match_kind") or _dict(record.get("match")).get("match_kind"),
            record.get("resolution_kind"),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(record)
    return deduped


def _unique_request_ids(records: list[dict[str, Any]]) -> set[str]:
    return {
        value
        for record in records
        for value in (
            record.get("request_id"),
            _dict(record.get("match")).get("request_id"),
            _dict(record.get("resolution_preview")).get("request_id"),
        )
        if isinstance(value, str) and value.strip()
    }


def _count_unique_request_ids(records: list[dict[str, Any]]) -> int:
    return len(_unique_request_ids(records))


def _accepted_answer_ids(answers: list[dict[str, Any]]) -> set[str]:
    return {
        request_id
        for answer in answers
        if _text(answer.get("status")).startswith("accepted")
        for request_id in [_text(answer.get("request_id"))]
        if request_id
    }


def _overlay_answer_records(artifacts: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    overlay = _dict(_dict(artifacts.get("rerun_input")).get("rerun_input_overlay"))
    records: list[dict[str, str]] = []
    for group_name in ("intake_overlay", "ontology_review_hints", "candidate_review_hints"):
        group = _dict(overlay.get(group_name))
        for bucket_name, items in group.items():
            if not isinstance(bucket_name, str):
                continue
            for item in _list(items):
                item_dict = _dict(item)
                request_id = _text(item_dict.get("request_id"))
                if not request_id:
                    continue
                records.append(
                    {
                        "request_id": request_id,
                        "group": group_name,
                        "bucket": bucket_name,
                        "answer_kind": _text(item_dict.get("answer_kind")),
                        "request_kind": _text(item_dict.get("request_kind")),
                        "target_ref": _text(item_dict.get("target_ref")),
                    }
                )
    return records


def _is_nonblocking_consumed_answer(record: dict[str, str]) -> bool:
    if record["group"] == "intake_overlay":
        return True
    if _is_aggregate_gap_target(record):
        return True
    if record["request_kind"] not in {"candidate_gap", "ontology_gap"}:
        return True
    return False


def _is_aggregate_gap_target(record: dict[str, str]) -> bool:
    return (
        record["request_kind"] in {"candidate_gap", "ontology_gap"}
        and record["target_ref"] == "candidate_graph.gaps"
    )


def _is_dismissed_consumed_answer(record: dict[str, str]) -> bool:
    return record["answer_kind"] == "reject"


def _answer_accounting(
    *,
    answers: list[dict[str, Any]],
    materialized_answer_request_ids: set[str],
    artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    accepted_ids = _accepted_answer_ids(answers)
    overlay_records = _overlay_answer_records(artifacts)
    consumed_ids = {
        record["request_id"] for record in overlay_records if record["request_id"] in accepted_ids
    }
    nonblocking_consumed_ids = {
        record["request_id"]
        for record in overlay_records
        if record["request_id"] in accepted_ids and _is_nonblocking_consumed_answer(record)
    }
    dismissed_consumed_ids = {
        record["request_id"]
        for record in overlay_records
        if record["request_id"] in accepted_ids and _is_dismissed_consumed_answer(record)
    }
    materialized_ids = materialized_answer_request_ids & accepted_ids
    dismissed_ids = dismissed_consumed_ids & materialized_ids
    materialized_ids = materialized_ids - dismissed_ids
    aggregate_ids = nonblocking_consumed_ids - materialized_ids - dismissed_ids
    closure_evidence_ids = materialized_ids | aggregate_ids
    ordinary_unmaterialized_ids = accepted_ids - closure_evidence_ids - dismissed_ids
    return {
        "accepted_answer_request_ids": sorted(accepted_ids),
        "materialized_answer_request_ids": sorted(materialized_ids),
        "consumed_answer_request_ids": sorted(consumed_ids),
        "aggregate_answer_request_ids": sorted(aggregate_ids),
        "dismissed_answer_request_ids": sorted(dismissed_ids),
        "closure_evidence_answer_request_ids": sorted(closure_evidence_ids),
        "ordinary_unmaterialized_answer_request_ids": sorted(ordinary_unmaterialized_ids),
        "accepted_answer_count": len(accepted_ids),
        "materialized_answer_count": len(materialized_ids),
        "consumed_answer_count": len(consumed_ids),
        "aggregate_answer_count": len(aggregate_ids),
        "dismissed_answer_count": len(dismissed_ids),
        "closure_evidence_answer_count": len(closure_evidence_ids),
        "ordinary_unmaterialized_answer_count": len(ordinary_unmaterialized_ids),
    }


def _closed_counter(keys: tuple[str, ...], observed: Counter[str]) -> dict[str, int]:
    result = {key: 0 for key in keys}
    for key, count in observed.items():
        result[key if key in result else "other"] += count
    return result


def _ontology_decision_counts(artifacts: dict[str, dict[str, Any]]) -> dict[str, int]:
    decisions = [
        decision
        for decision in _list(_dict(artifacts.get("ontology_decisions")).get("decisions"))
        if isinstance(decision, dict)
    ]
    counter: Counter[str] = Counter()
    for decision in decisions:
        decision_type = _text(decision.get("decision_type")) or _text(decision.get("decision"))
        counter[decision_type or "other"] += 1
    summary_counts = _dict(_summary(artifacts, "ontology_decisions").get("decision_counts"))
    for key, value in summary_counts.items():
        if isinstance(key, str) and key not in counter:
            counter[key] = _int(value)
    return {
        "project_local": counter["propose_project_local_term"]
        + counter["project_local_term"]
        + counter["project_local"],
        "rejected": counter["reject"] + counter["rejected"],
        "deferred": counter["defer"] + counter["deferred"],
    }


def _metrics(artifacts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    candidate_graph = artifacts.get("candidate_graph")
    repaired_candidate_graph = artifacts.get("repaired_candidate_graph")
    initial_gaps = _all_gaps(candidate_graph)
    ontology_initial = sum(1 for gap in initial_gaps if gap.get("kind") == "ontology_gap")
    candidate_initial = sum(1 for gap in initial_gaps if gap.get("kind") != "ontology_gap")

    ontology_records, candidate_records = _resolution_records(artifacts)
    materialized_answer_request_ids = _unique_request_ids(ontology_records) | _unique_request_ids(
        candidate_records
    )

    answers = [
        answer
        for answer in _list(_dict(artifacts.get("clarification_answers")).get("answers"))
        if isinstance(answer, dict)
    ]
    answered_question_count = len(answers) or _summary_int(
        artifacts, "clarification_answers", "answer_count"
    )
    accepted_answer_count = _summary_int(
        artifacts, "clarification_answers", "accepted_answer_count"
    ) or sum(1 for answer in answers if _text(answer.get("status")).startswith("accepted"))

    draft_import_summary = _summary(artifacts, "specspace_draft_import_preview")
    deferred_answer_count = _summary_int(
        artifacts, "specspace_draft_import_preview", "deferred_count"
    ) + sum(
        1
        for answer in answers
        if _text(answer.get("answer_kind")) == "defer" or "defer" in _text(answer.get("status"))
    )
    invalid_answer_count = _summary_int(
        artifacts, "specspace_draft_import_preview", "invalid_draft_count"
    ) + sum(1 for answer in answers if "invalid" in _text(answer.get("status")))
    if not answered_question_count and draft_import_summary:
        answered_question_count = _int(draft_import_summary.get("draft_count"))

    answer_accounting = _answer_accounting(
        answers=answers,
        materialized_answer_request_ids=materialized_answer_request_ids,
        artifacts=artifacts,
    )
    if accepted_answer_count > 0 and answer_accounting["accepted_answer_count"] == 0:
        summary_materialized_ids = sorted(materialized_answer_request_ids)[:accepted_answer_count]
        summary_materialized_count = len(summary_materialized_ids)
        answer_accounting = {
            **answer_accounting,
            "accepted_answer_count": accepted_answer_count,
            "materialized_answer_request_ids": summary_materialized_ids,
            "closure_evidence_answer_request_ids": summary_materialized_ids,
            "ordinary_unmaterialized_answer_request_ids": [],
            "materialized_answer_count": summary_materialized_count,
            "closure_evidence_answer_count": summary_materialized_count,
            "ordinary_unmaterialized_answer_count": max(
                accepted_answer_count - summary_materialized_count,
                0,
            ),
        }
    else:
        accepted_answer_count = max(
            accepted_answer_count,
            answer_accounting["accepted_answer_count"],
        )
    bounded_materialized_answer_count = min(
        answer_accounting["materialized_answer_count"],
        accepted_answer_count,
    )
    closure_evidence_answer_count = min(
        answer_accounting["closure_evidence_answer_count"],
        accepted_answer_count,
    )
    unmaterialized_answer_count = min(
        answer_accounting["ordinary_unmaterialized_answer_count"],
        max(accepted_answer_count - closure_evidence_answer_count, 0),
    )
    answer_accounting = {
        **answer_accounting,
        "accepted_answer_count": accepted_answer_count,
        "materialized_answer_count": bounded_materialized_answer_count,
        "closure_evidence_answer_count": closure_evidence_answer_count,
        "ordinary_unmaterialized_answer_count": unmaterialized_answer_count,
    }
    ontology_decision_counts = _ontology_decision_counts(artifacts)

    ontology_match_counter: Counter[str] = Counter()
    for record in ontology_records:
        match_kind = _text(record.get("match_kind")) or _text(
            _dict(record.get("match")).get("match_kind")
        )
        decision = _text(_dict(record.get("resolution_preview")).get("decision"))
        ontology_match_counter[match_kind or decision or "other"] += 1

    candidate_resolution_counter: Counter[str] = Counter()
    for record in candidate_records:
        candidate_resolution_counter[_text(record.get("resolution_kind"), "other")] += 1

    repaired_session_summary = _summary(artifacts, "repaired_repair_session")
    repaired_handoff_summary = _summary(artifacts, "repaired_handoff")
    rerun_materialization_summary = _summary(artifacts, "rerun_materialization")
    final_gap_summary = (
        repaired_handoff_summary or repaired_session_summary or rerun_materialization_summary
    )

    ontology_resolved = _int(
        final_gap_summary.get(
            "resolved_ontology_gap_count",
            rerun_materialization_summary.get("resolved_ontology_gap_count", len(ontology_records)),
        )
    )
    ontology_unresolved = _int(
        final_gap_summary.get(
            "unresolved_ontology_gap_count",
            rerun_materialization_summary.get("unresolved_ontology_gap_count", ontology_initial),
        )
    )
    candidate_resolved = _int(
        final_gap_summary.get(
            "resolved_candidate_gap_count",
            rerun_materialization_summary.get(
                "resolved_candidate_gap_count", len(candidate_records)
            ),
        )
    )
    candidate_unresolved = _int(
        final_gap_summary.get(
            "unresolved_candidate_gap_count",
            rerun_materialization_summary.get("unresolved_candidate_gap_count", candidate_initial),
        )
    )

    remaining_blockers = _remaining_blocker_count(artifacts)
    stale_ref_count = _stale_ref_count(artifacts)
    failed_gate_count = _failed_gate_count(artifacts)
    dry_run_count = _dry_run_count(artifacts)
    rerun_request_count = _summary_int(
        artifacts, "specspace_rerun_request", "request_count"
    ) or _summary_int(artifacts, "specspace_rerun_request", "active_request_count")
    approval_attempt_count = _summary_int(artifacts, "approval_intent", "intent_count")

    candidate_node_count = (
        _summary_int(artifacts, "repaired_candidate_graph", "node_count")
        or _summary_int(artifacts, "candidate_graph", "node_count")
        or len(_nodes(repaired_candidate_graph or candidate_graph))
    )

    return {
        "clarification_question_count": _summary_int(
            artifacts, "clarification_requests", "request_count"
        ),
        "blocking_question_count": _summary_int(
            artifacts, "clarification_requests", "blocking_request_count"
        ),
        "review_required_question_count": _summary_int(
            artifacts, "clarification_requests", "review_required_request_count"
        ),
        "answered_question_count": answered_question_count,
        "accepted_answer_count": accepted_answer_count,
        "deferred_answer_count": deferred_answer_count,
        "invalid_answer_count": invalid_answer_count,
        "materialized_answer_count": bounded_materialized_answer_count,
        "unmaterialized_answer_count": unmaterialized_answer_count,
        "answer_materialization_rate": _rate(
            answer_accounting["closure_evidence_answer_count"],
            accepted_answer_count,
        ),
        "per_gap_materialized_answer_count": bounded_materialized_answer_count,
        "consumed_answer_count": answer_accounting["consumed_answer_count"],
        "aggregate_answer_count": answer_accounting["aggregate_answer_count"],
        "dismissed_answer_count": answer_accounting["dismissed_answer_count"],
        "closure_evidence_answer_count": closure_evidence_answer_count,
        "ordinary_unmaterialized_answer_count": unmaterialized_answer_count,
        "answer_accounting": answer_accounting,
        "candidate_review_hint_count": _summary_int(
            artifacts, "rerun_input", "candidate_review_hint_count"
        ),
        "stale_answer_count": _stale_answer_count(artifacts),
        "ontology_gap_count_initial": ontology_initial,
        "ontology_gap_resolved_count": ontology_resolved,
        "ontology_gap_unresolved_count": ontology_unresolved,
        "ontology_gap_resolution_rate": _rate(ontology_resolved, ontology_initial),
        "ontology_project_local_term_count": ontology_decision_counts["project_local"],
        "ontology_rejected_term_count": ontology_decision_counts["rejected"],
        "ontology_deferred_term_count": ontology_decision_counts["deferred"],
        "ontology_match_kind_counts": _closed_counter(
            ONTOLOGY_MATCH_KIND_KEYS,
            ontology_match_counter,
        ),
        "candidate_gap_count_initial": candidate_initial,
        "candidate_gap_resolved_count": candidate_resolved,
        "candidate_gap_unresolved_count": candidate_unresolved,
        "candidate_gap_closure_rate": _rate(candidate_resolved, candidate_initial),
        "candidate_resolution_kind_counts": _closed_counter(
            CANDIDATE_RESOLUTION_KIND_KEYS,
            candidate_resolution_counter,
        ),
        "risk_accepted_count": candidate_resolution_counter["risk_accepted"],
        "enforcement_mechanism_added_count": candidate_resolution_counter[
            "enforcement_mechanism_added"
        ],
        "context_supplied_count": candidate_resolution_counter["context_supplied"],
        "remaining_blocker_count": remaining_blockers,
        "rerun_count": _rerun_count(artifacts),
        "manual_handoff_count": _manual_handoff_count(artifacts),
        "operator_command_count": _operator_command_count(artifacts),
        "failed_gate_count": failed_gate_count,
        "stale_ref_count": stale_ref_count,
        "dry_run_count": dry_run_count,
        "rerun_request_count": rerun_request_count,
        "approval_attempt_count": approval_attempt_count,
        **_temporal_metrics(artifacts),
        "candidate_approval_state": _candidate_approval_state(artifacts),
        "candidate_approval_intent_state": _candidate_approval_intent_state(artifacts),
        "candidate_approval_decision_state": _candidate_approval_decision_state(artifacts),
        "platform_promotion_state": _platform_promotion_state(artifacts),
        "promotion_path_count": _promotion_path_count(artifacts),
        "promotion_request_state": _promotion_request_state(artifacts),
        "promotion_execution_state": _promotion_execution_state(artifacts),
        "review_status": _review_status(artifacts),
        "review_pr_number": _review_pr_number(artifacts),
        "review_merge_commit_sha": _review_merge_commit_sha(artifacts),
        "read_model_publication_state": _read_model_publication_state(artifacts),
        "published_file_count": _published_file_count(artifacts),
        "published_manifest_digest": _published_manifest_digest(artifacts),
        "candidate_node_count": candidate_node_count,
    }


def _remaining_blocker_count(artifacts: dict[str, dict[str, Any]]) -> int:
    repaired_session = _dict(artifacts.get("repaired_repair_session"))
    readiness_impact = _dict(repaired_session.get("readiness_impact"))
    if readiness_impact:
        return len(_list(readiness_impact.get("blocked_by"))) + _int(
            readiness_impact.get("unresolved_blocking_count")
        )
    blocked: set[str] = set()
    for artifact in artifacts.values():
        readiness = _dict(artifact.get("readiness"))
        for blocker in _list(readiness.get("blocked_by")):
            if isinstance(blocker, str):
                blocked.add(blocker)
    return len(blocked)


def _finding_codes(finding: dict[str, Any]) -> set[str]:
    values = {
        finding.get("finding_id"),
        finding.get("kind"),
        finding.get("code"),
        finding.get("classification"),
        finding.get("type"),
    }
    evidence = _dict(finding.get("evidence"))
    values.update(
        {
            evidence.get("finding_id"),
            evidence.get("kind"),
            evidence.get("code"),
            evidence.get("classification"),
            evidence.get("type"),
        }
    )
    return {_text(value).lower() for value in values if _text(value)}


def _finding_has_stale_ref(finding: dict[str, Any]) -> bool:
    for code in _finding_codes(finding):
        if code == "source_ref_mismatch":
            return True
        tokens = _tokenize(code)
        if "answer" in tokens:
            continue
        if "stale" in tokens and ("ref" in tokens or "source" in tokens):
            return True
    return False


def _finding_has_stale_answer(finding: dict[str, Any]) -> bool:
    for code in _finding_codes(finding):
        tokens = _tokenize(code)
        if "stale" in tokens and "answer" in tokens:
            return True
        if "superseded" in tokens and ("answer" in tokens or "draft" in tokens):
            return True
    return False


def _stale_ref_count(artifacts: dict[str, dict[str, Any]]) -> int:
    count = 0
    for artifact in artifacts.values():
        for finding in _list(artifact.get("findings")):
            if not isinstance(finding, dict):
                continue
            if _finding_has_stale_ref(finding):
                count += 1
    return count


def _stale_answer_count(artifacts: dict[str, dict[str, Any]]) -> int:
    count = 0
    for artifact in artifacts.values():
        for finding in _list(artifact.get("findings")):
            if isinstance(finding, dict) and _finding_has_stale_answer(finding):
                count += 1
    return count


def _failed_gate_count(artifacts: dict[str, dict[str, Any]]) -> int:
    failed_or_blocked_artifacts: set[str] = set()
    for key, artifact in artifacts.items():
        superseding_key = SUPERSEDED_REPORT_KEYS.get(key)
        if superseding_key and superseding_key in artifacts:
            continue
        readiness = _dict(artifact.get("readiness"))
        summary = _dict(artifact.get("summary"))
        status = (
            _text(summary.get("status"))
            or _text(readiness.get("review_state"))
            or _text(artifact.get("status"))
        )
        if (
            readiness
            and readiness.get("ready") is False
            and _list(readiness.get("blocked_by"))
            and (_status_is_failed(status) or _status_is_blocked(status))
        ):
            failed_or_blocked_artifacts.add(key)
        if _status_is_failed(status) or _status_is_blocked(status):
            failed_or_blocked_artifacts.add(key)
        if key in PLATFORM_REPORT_KEYS and _int(summary.get("error_count")) > 0:
            failed_or_blocked_artifacts.add(key)
    return len(failed_or_blocked_artifacts)


def _dry_run_count(artifacts: dict[str, dict[str, Any]]) -> int:
    count = 0
    for artifact in artifacts.values():
        summary = _dict(artifact.get("summary"))
        if artifact.get("dry_run") is True or _text(summary.get("status")) == "dry_run":
            count += 1
    return count


def _manual_handoff_count(artifacts: dict[str, dict[str, Any]]) -> int:
    handoff_keys = (
        "specspace_rerun_request",
        "approval_intent",
        "repair_rerun_execution",
        "approval_execution",
        "promotion_request",
        "promotion_execution",
    )
    return sum(1 for key in handoff_keys if key in artifacts)


def _operator_command_count(artifacts: dict[str, dict[str, Any]]) -> int:
    count = 0
    for key in (
        "repair_rerun_execution",
        "repair_rerun_publication",
        "approval_execution",
        "promotion_execution",
    ):
        artifact = _dict(artifacts.get(key))
        if artifact.get("command") or artifact.get("git_service_command"):
            count += 1
        count += len(_list(artifact.get("operations")))
    return count


def _phase_time(
    artifacts: dict[str, dict[str, Any]],
    *keys: str,
) -> datetime | None:
    for key in keys:
        artifact = _dict(artifacts.get(key))
        if not artifact:
            continue
        parsed = _artifact_time(artifact)
        if parsed is not None:
            return parsed
    return None


def _phase_timeline(artifacts: dict[str, dict[str, Any]]) -> list[tuple[str, datetime]]:
    phases = [
        ("intake_ready", _phase_time(artifacts, "intake")),
        ("repair_required", _phase_time(artifacts, "candidate_graph", "clarification_requests")),
        (
            "repair_rerun_requested",
            _phase_time(artifacts, "specspace_rerun_request", "rerun_input"),
        ),
        (
            "repaired_candidate_ready",
            _phase_time(artifacts, "repaired_repair_session", "repaired_handoff"),
        ),
        ("approval_materialized", _phase_time(artifacts, "approval_execution")),
        ("promotion_requested", _phase_time(artifacts, "promotion_request")),
        ("git_review_active", _phase_time(artifacts, "review_status", "promotion_execution")),
        ("read_model_publication_complete", _phase_time(artifacts, "read_model_publication")),
    ]
    return [(phase, timestamp) for phase, timestamp in phases if timestamp is not None]


def _phase_dwell_seconds(
    phases: list[tuple[str, datetime]],
    *,
    lifecycle_state: str,
    blocked_or_open: bool,
) -> dict[str, float]:
    if not phases:
        return {}
    dwell: dict[str, float] = {}
    for index, (phase, timestamp) in enumerate(phases):
        next_timestamp = phases[index + 1][1] if index + 1 < len(phases) else None
        seconds = _seconds_between(timestamp, next_timestamp)
        if seconds is not None:
            dwell[phase] = seconds
    last_phase, last_timestamp = phases[-1]
    if blocked_or_open or last_phase == lifecycle_state:
        now = datetime.now(tz=timezone.utc)
        seconds = _seconds_between(last_timestamp, now)
        if seconds is not None:
            dwell[last_phase] = max(dwell.get(last_phase, 0), seconds)
    return dwell


def _stalled_phase(phase_dwell: dict[str, float], lifecycle_state: str) -> str | None:
    if lifecycle_state not in phase_dwell:
        return None
    return lifecycle_state if phase_dwell[lifecycle_state] >= STALL_DWELL_SECONDS else None


def _rerun_count(artifacts: dict[str, dict[str, Any]]) -> int:
    explicit = (
        _summary_int(artifacts, "repair_rerun_execution", "rerun_count")
        or _summary_int(artifacts, "specspace_rerun_request", "request_count")
        or _summary_int(artifacts, "specspace_rerun_request", "active_request_count")
    )
    if explicit:
        return explicit
    rerun_artifact_keys = ("rerun_input", "rerun_preview", "rerun_materialization")
    return 1 if any(key in artifacts for key in rerun_artifact_keys) else 0


def _lifecycle_state_from_metrics_fragment(artifacts: dict[str, dict[str, Any]]) -> str:
    if _read_model_publication_state(artifacts) == "published":
        return "read_model_publication_complete"
    if _review_status(artifacts) in {"open", "merged"}:
        return "git_review_active"
    if _promotion_request_state(artifacts) == "requested":
        return "promotion_requested"
    if _candidate_approval_decision_state(artifacts) == "materialized":
        return "approval_materialized"
    if _candidate_approval_state(artifacts) == "ready":
        return "approval_ready"
    if artifacts.get("repaired_repair_session") or artifacts.get("repaired_handoff"):
        return "repaired_candidate_ready"
    if artifacts.get("specspace_rerun_request") or artifacts.get("rerun_input"):
        return "repair_rerun_requested"
    if artifacts.get("candidate_graph") or artifacts.get("clarification_requests"):
        return "repair_required"
    if artifacts.get("intake"):
        return "intake_ready"
    return "blocked"


def _temporal_metrics(artifacts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    times = {key: _artifact_time(artifact) for key, artifact in artifacts.items()}
    intake_time = times.get("intake")
    candidate_time = times.get("candidate_graph")
    materialization_time = times.get("rerun_materialization")
    approval_ready_time = (
        times.get("repaired_repair_session")
        if _candidate_approval_state(artifacts) == "ready"
        else None
    )
    progress_times = [
        value
        for key, value in times.items()
        if value is not None
        and key
        in {
            "candidate_graph",
            "rerun_materialization",
            "repaired_handoff",
            "repaired_repair_session",
            "approval_execution",
            "promotion_execution",
            "read_model_publication",
        }
    ]
    last_progress = max(progress_times).isoformat() if progress_times else None
    lifecycle_state = _lifecycle_state_from_metrics_fragment(artifacts)
    blocked_or_open = (
        _remaining_blocker_count(artifacts) > 0
        or _failed_gate_count(artifacts) > 0
        or lifecycle_state
        in {"repair_required", "repair_rerun_requested", "git_review_active", "blocked"}
    )
    phase_timeline = _phase_timeline(artifacts)
    phase_dwell = _phase_dwell_seconds(
        phase_timeline,
        lifecycle_state=lifecycle_state,
        blocked_or_open=blocked_or_open,
    )
    timeline = {f"{phase}_at": timestamp.isoformat() for phase, timestamp in phase_timeline}
    if last_progress:
        timeline["last_progress_at"] = last_progress
    return {
        "time_to_first_candidate_seconds": _seconds_between(intake_time, candidate_time),
        "time_to_first_materialization_seconds": _seconds_between(
            intake_time,
            materialization_time,
        ),
        "time_to_approval_ready_seconds": _seconds_between(intake_time, approval_ready_time),
        "phase_dwell_seconds": phase_dwell,
        "no_progress_rerun_count": 1
        if artifacts.get("rerun_materialization")
        and _summary_int(artifacts, "rerun_materialization", "removed_gap_count") == 0
        else 0,
        "last_progress_at": last_progress,
        "stalled_phase": _stalled_phase(phase_dwell, lifecycle_state),
        "temporal_clock_source": "artifact_generated_at_or_event_timestamp",
        "timeline": timeline,
    }


def _candidate_approval_state(artifacts: dict[str, dict[str, Any]]) -> str:
    readiness_impact = _dict(
        _dict(artifacts.get("repaired_repair_session")).get("readiness_impact")
    )
    repaired_session_summary = _summary(artifacts, "repaired_repair_session")
    handoff_summary = _summary(artifacts, "repaired_handoff")
    if (
        readiness_impact.get("ready_for_candidate_approval") is True
        or repaired_session_summary.get("ready_for_candidate_approval") is True
        or handoff_summary.get("ready_for_candidate_approval") is True
    ):
        return "ready"
    if artifacts.get("repaired_repair_session") or artifacts.get("repaired_handoff"):
        return "blocked"
    if artifacts.get("candidate_graph"):
        return "not_reached"
    return "not_available"


def _candidate_approval_intent_state(artifacts: dict[str, dict[str, Any]]) -> str:
    if "approval_intent" not in artifacts:
        return "not_reached" if _candidate_approval_state(artifacts) != "ready" else "not_available"
    summary = _summary(artifacts, "approval_intent")
    status = _text(summary.get("status"))
    if _int(summary.get("active_intent_count")) > 0 or "requested" in status:
        return "requested"
    if "blocked" in status:
        return "blocked"
    return "unknown"


def _candidate_approval_decision_state(artifacts: dict[str, dict[str, Any]]) -> str:
    execution = _dict(artifacts.get("approval_execution"))
    if execution:
        summary = _summary(artifacts, "approval_execution")
        status = _text(summary.get("status")) or _text(execution.get("status"))
        if (
            _dict(execution.get("candidate_approval_decision_ref"))
            or summary.get("decision_written") is True
        ):
            return "materialized"
        if execution.get("dry_run") is True:
            return "dry_run"
        if "failed" in status or "blocked" in status:
            return "failed" if "failed" in status else "blocked"
        return "unknown"
    decision = _dict(artifacts.get("candidate_approval_decision"))
    if decision:
        summary = _summary(artifacts, "candidate_approval_decision")
        readiness = _dict(decision.get("readiness"))
        decision_payload = _dict(decision.get("decision"))
        state = _text(summary.get("effective_state")) or _text(decision_payload.get("state"))
        status = (
            _text(summary.get("status"))
            or _text(readiness.get("review_state"))
            or _text(decision.get("status"))
        )
        if state == "approved" and readiness.get("ready") is True:
            return "materialized"
        if decision.get("dry_run") is True or status == "dry_run":
            return "dry_run"
        if _status_is_failed(status):
            return "failed"
        if _status_is_blocked(status) or state in {"rejected", "needs_context", "superseded"}:
            return "blocked"
        return "unknown"
    if _candidate_approval_intent_state(artifacts) in {"requested", "ready"}:
        return "not_available"
    return "not_reached"


def _platform_promotion_state(artifacts: dict[str, dict[str, Any]]) -> str:
    execution_state = _promotion_execution_state(artifacts)
    if execution_state not in {"not_reached", "not_available"}:
        return execution_state
    request_state = _promotion_request_state(artifacts)
    if request_state == "requested":
        return "requested"
    if _candidate_approval_decision_state(artifacts) == "materialized":
        return "ready"
    return "not_reached"


def _promotion_path_count(artifacts: dict[str, dict[str, Any]]) -> int:
    return (
        _summary_int(artifacts, "repaired_promotion_gate", "promotion_path_count")
        or _summary_int(artifacts, "repaired_active_candidate", "promotion_path_count")
        or _summary_int(artifacts, "promotion_request", "commit_path_count")
    )


def _promotion_request_state(artifacts: dict[str, dict[str, Any]]) -> str:
    request = _dict(artifacts.get("promotion_request"))
    if not request:
        return (
            "not_available"
            if _candidate_approval_decision_state(artifacts) == "materialized"
            else "not_reached"
        )
    summary = _summary(artifacts, "promotion_request")
    if request.get("ok") is True or summary.get("promotion_ready") is True:
        return "requested"
    if _int(summary.get("error_count")) > 0:
        return "blocked"
    return "unknown"


def _promotion_execution_state(artifacts: dict[str, dict[str, Any]]) -> str:
    execution = _dict(artifacts.get("promotion_execution"))
    if not execution:
        return (
            "not_available" if _promotion_request_state(artifacts) == "requested" else "not_reached"
        )
    summary = _summary(artifacts, "promotion_execution")
    status = _text(summary.get("status")) or _text(execution.get("status"))
    if execution.get("dry_run") is True or status == "dry_run":
        return "dry_run"
    if _int(summary.get("error_count")) > 0 or _status_is_failed(status):
        return "failed"
    if _status_is_blocked(status):
        return "blocked"
    if summary.get("commit_created") is True or summary.get("review_opened") is True:
        return "executed"
    return "unknown"


def _review_status(artifacts: dict[str, dict[str, Any]]) -> str:
    review = _dict(artifacts.get("review_status"))
    if not review:
        return (
            "not_reached"
            if _promotion_execution_state(artifacts) == "not_reached"
            else "not_available"
        )
    summary = _summary(artifacts, "review_status")
    status = _text(summary.get("review_status")) or _text(summary.get("status"))
    if status in {"open", "merged", "blocked", "unknown"}:
        return status
    if "merged" in status:
        return "merged"
    if "open" in status:
        return "open"
    if "blocked" in status or "failed" in status:
        return "blocked"
    return "unknown"


def _review_pr_number(artifacts: dict[str, dict[str, Any]]) -> int | None:
    review = _dict(artifacts.get("review_status"))
    summary = _summary(artifacts, "review_status")
    value = summary.get("review_pr_number") or _dict(review.get("review")).get("number")
    return _int(value) if value is not None else None


def _review_merge_commit_sha(artifacts: dict[str, dict[str, Any]]) -> str | None:
    review = _dict(artifacts.get("review_status"))
    summary = _summary(artifacts, "review_status")
    return (
        _text(summary.get("review_merge_commit_sha"))
        or _text(_dict(review.get("review")).get("merge_commit_sha"))
        or None
    )


def _read_model_publication_state(artifacts: dict[str, dict[str, Any]]) -> str:
    publication = _dict(artifacts.get("read_model_publication"))
    if not publication:
        return "not_reached" if _review_status(artifacts) != "merged" else "not_available"
    summary = _summary(artifacts, "read_model_publication")
    status = _text(summary.get("status"))
    if status == "published" or summary.get("published") is True:
        return "published"
    if publication.get("dry_run") is True or status == "dry_run":
        return "dry_run"
    if _int(summary.get("error_count")) > 0 or "failed" in status:
        return "failed"
    if "blocked" in status:
        return "blocked"
    return "unknown"


def _published_file_count(artifacts: dict[str, dict[str, Any]]) -> int:
    return _summary_int(
        artifacts, "read_model_publication", "published_file_count"
    ) or _summary_int(artifacts, "read_model_publication", "file_count")


def _published_manifest_digest(artifacts: dict[str, dict[str, Any]]) -> str | None:
    publication = _dict(artifacts.get("read_model_publication"))
    summary = _summary(artifacts, "read_model_publication")
    return (
        _text(summary.get("published_manifest_digest"))
        or _text(_dict(publication.get("manifest")).get("sha256"))
        or None
    )


def _source_ref_findings(
    artifacts: dict[str, dict[str, Any]],
    paths: dict[str, Path],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for parent_key, source_key, expected_path_key in SOURCE_REF_CHECKS:
        parent = _dict(artifacts.get(parent_key))
        if not parent or expected_path_key not in paths:
            continue
        source_artifacts = _dict(parent.get("source_artifacts"))
        source = _dict(source_artifacts.get(source_key))
        if not source:
            continue
        actual = source.get("source_ref")
        expected = _relative_ref(paths[expected_path_key])
        if actual is None:
            findings.append(
                _finding(
                    finding_id=f"{parent_key}_{source_key}_source_ref_missing",
                    severity="medium",
                    message=f"{parent_key} does not declare source_ref for {source_key}.",
                    evidence={"parent": parent_key, "source_key": source_key},
                )
            )
        elif actual != expected:
            findings.append(
                _finding(
                    finding_id=f"{parent_key}_{source_key}_source_ref_stale",
                    severity="medium",
                    message=(
                        f"{parent_key} source_ref for {source_key} does not match selected input."
                    ),
                    evidence={
                        "parent": parent_key,
                        "source_key": source_key,
                        "actual": actual,
                        "expected": expected,
                    },
                )
            )
    return findings


def _policy_findings(
    artifacts: dict[str, dict[str, Any]],
    metrics: dict[str, Any],
    source_ref_findings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    findings = list(source_ref_findings)
    if (
        metrics["read_model_publication_state"] == "published"
        and metrics["review_status"] != "merged"
    ):
        findings.append(
            _finding(
                finding_id="out_of_order_publication",
                severity="high",
                message="Read-model publication appears before merged review evidence.",
                evidence={
                    "read_model_publication_state": metrics["read_model_publication_state"],
                    "review_status": metrics["review_status"],
                },
            )
        )
    if (
        metrics["promotion_request_state"] == "requested"
        and metrics["candidate_approval_decision_state"] != "materialized"
    ):
        findings.append(
            _finding(
                finding_id="promotion_requested_without_approval_decision",
                severity="high",
                message=(
                    "Promotion request exists without materialized candidate approval decision."
                ),
                evidence={
                    "promotion_request_state": metrics["promotion_request_state"],
                    "candidate_approval_decision_state": metrics[
                        "candidate_approval_decision_state"
                    ],
                },
            )
        )
    if metrics["stale_ref_count"] > 0:
        findings.append(
            _finding(
                finding_id="stale_answer_refs",
                severity="medium",
                message="One or more source-ref or stale-answer findings are present.",
                evidence={"stale_ref_count": metrics["stale_ref_count"]},
            )
        )
    return findings


def _invariant_findings(metrics: dict[str, Any]) -> list[dict[str, Any]]:
    checks = [
        (
            "blocking_question_count_bounds",
            metrics["blocking_question_count"] <= metrics["clarification_question_count"],
            "blocking_question_count must not exceed clarification_question_count.",
        ),
        (
            "review_required_question_count_bounds",
            metrics["review_required_question_count"] <= metrics["clarification_question_count"],
            "review_required_question_count must not exceed clarification_question_count.",
        ),
        (
            "accepted_answer_count_bounds",
            metrics["accepted_answer_count"] <= metrics["answered_question_count"],
            "accepted_answer_count must not exceed answered_question_count.",
        ),
        (
            "deferred_answer_count_bounds",
            metrics["deferred_answer_count"] <= metrics["answered_question_count"],
            "deferred_answer_count must not exceed answered_question_count.",
        ),
        (
            "invalid_answer_count_bounds",
            metrics["invalid_answer_count"] <= metrics["answered_question_count"],
            "invalid_answer_count must not exceed answered_question_count.",
        ),
        (
            "answer_partition_bounds",
            metrics["accepted_answer_count"]
            + metrics["invalid_answer_count"]
            + metrics["deferred_answer_count"]
            <= metrics["answered_question_count"],
            "accepted + invalid + deferred answers must not exceed answered_question_count.",
        ),
        (
            "materialized_answer_count_bounds",
            metrics["materialized_answer_count"] <= metrics["accepted_answer_count"],
            "materialized_answer_count must not exceed accepted_answer_count.",
        ),
        (
            "unmaterialized_answer_count_bounds",
            metrics["unmaterialized_answer_count"] <= metrics["accepted_answer_count"],
            "unmaterialized_answer_count must not exceed accepted_answer_count.",
        ),
        (
            "answer_materialization_partition_bounds",
            metrics["materialized_answer_count"] + metrics["unmaterialized_answer_count"]
            <= metrics["accepted_answer_count"],
            "materialized + unmaterialized answers must not exceed accepted_answer_count.",
        ),
        (
            "ontology_gap_resolved_bounds",
            metrics["ontology_gap_resolved_count"] <= metrics["ontology_gap_count_initial"],
            "ontology_gap_resolved_count must not exceed ontology_gap_count_initial.",
        ),
        (
            "ontology_gap_unresolved_bounds",
            metrics["ontology_gap_unresolved_count"] <= metrics["ontology_gap_count_initial"],
            "ontology_gap_unresolved_count must not exceed ontology_gap_count_initial.",
        ),
        (
            "ontology_gap_partition_bounds",
            metrics["ontology_gap_resolved_count"] + metrics["ontology_gap_unresolved_count"]
            <= metrics["ontology_gap_count_initial"],
            "resolved + unresolved ontology gaps must not exceed ontology_gap_count_initial.",
        ),
        (
            "candidate_gap_resolved_bounds",
            metrics["candidate_gap_resolved_count"] <= metrics["candidate_gap_count_initial"],
            "candidate_gap_resolved_count must not exceed candidate_gap_count_initial.",
        ),
        (
            "candidate_gap_unresolved_bounds",
            metrics["candidate_gap_unresolved_count"] <= metrics["candidate_gap_count_initial"],
            "candidate_gap_unresolved_count must not exceed candidate_gap_count_initial.",
        ),
        (
            "candidate_gap_partition_bounds",
            metrics["candidate_gap_resolved_count"] + metrics["candidate_gap_unresolved_count"]
            <= metrics["candidate_gap_count_initial"],
            "resolved + unresolved candidate gaps must not exceed candidate_gap_count_initial.",
        ),
    ]
    findings: list[dict[str, Any]] = []
    for finding_id, ok, message in checks:
        if ok:
            continue
        findings.append(
            _finding(
                finding_id=f"invariant_{finding_id}",
                severity="high",
                message=message,
                source="idea_maturity_metrics_report.invariant_validator",
            )
        )
    return findings


def _path_evidence_ref(paths: dict[str, Path], key: str, fragment: str | None = None) -> str | None:
    if key not in paths:
        return None
    source_ref = _relative_ref(paths[key])
    if not source_ref:
        return None
    return f"{source_ref}#{fragment}" if fragment else source_ref


def _selected_artifact_key(
    artifacts: dict[str, dict[str, Any]],
    *,
    preferred: str,
    fallback: str,
) -> str | None:
    if artifacts.get(preferred):
        return preferred
    if artifacts.get(fallback):
        return fallback
    return None


def _readiness_explainer(
    *,
    explainer_id: str,
    kind: str,
    source: str,
    severity: str,
    blocks: list[str],
    message: str,
    next_action: str,
    evidence_refs: list[str | None] | None = None,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": f"readiness-explainer.{_slug(explainer_id)}",
        "proposal_id": READINESS_EXPLAINERS_PROPOSAL_ID,
        "kind": kind,
        "source": source,
        "severity": _readiness_severity(severity),
        "blocks": [block for block in blocks if block],
        "message": message,
        "next_action": next_action,
        "evidence_refs": [ref for ref in evidence_refs or [] if ref],
        "evidence": _public_safe(evidence or {}),
    }


def _readiness_severity(value: str) -> str:
    normalized = _slug(value).replace("-", "_")
    if normalized in READINESS_SEVERITY_VALUES:
        return normalized
    return READINESS_SEVERITY_ALIASES.get(normalized, "medium")


def _dedupe_explainers(explainers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for explainer in explainers:
        explainer_id = _text(explainer.get("id"))
        if not explainer_id or explainer_id in seen:
            continue
        seen.add(explainer_id)
        deduped.append(explainer)
        if len(deduped) >= READINESS_EXPLAINER_LIMIT:
            break
    return deduped


def _finding_fragment(finding: dict[str, Any], *, collection: str) -> str:
    finding_id = (
        _text(finding.get("finding_id"))
        or _text(finding.get("code"))
        or _text(finding.get("kind"))
        or "finding"
    )
    return f"{collection}.{_slug(finding_id)}"


def _pre_sib_readiness_explainers(
    artifacts: dict[str, dict[str, Any]],
    paths: dict[str, Path],
) -> list[dict[str, Any]]:
    selected_key = _selected_artifact_key(
        artifacts,
        preferred="repaired_pre_sib",
        fallback="pre_sib",
    )
    if selected_key is None:
        return []
    pre_sib = _dict(artifacts.get(selected_key))
    readiness = _dict(pre_sib.get("readiness"))
    findings = [
        item
        for item in [*_list(pre_sib.get("findings")), *_list(pre_sib.get("warnings"))]
        if isinstance(item, dict)
    ]
    explainers: list[dict[str, Any]] = []
    for finding in findings:
        finding_id = (
            _text(finding.get("finding_id"))
            or _text(finding.get("code"))
            or _text(finding.get("kind"))
            or "pre_sib_finding"
        )
        severity = _text(finding.get("severity"), "review_required")
        message = _text(
            finding.get("message"),
            "Pre-SIB coherence finding remains unresolved.",
        )
        explainers.append(
            _readiness_explainer(
                explainer_id=f"pre-sib-{finding_id}",
                kind="pre_sib_finding",
                source=selected_key,
                severity=severity,
                blocks=["pre_sib_review", "candidate_approval"],
                message=message,
                next_action=(
                    "Inspect Pre-SIB coherence findings and close the referenced "
                    "candidate graph condition."
                ),
                evidence_refs=[
                    _path_evidence_ref(
                        paths,
                        selected_key,
                        _finding_fragment(finding, collection="findings"),
                    )
                ],
                evidence={
                    "finding_id": finding_id,
                    "review_state": readiness.get("review_state"),
                },
            )
        )
    for blocker in _text_list(readiness.get("blocked_by")):
        explainers.append(
            _readiness_explainer(
                explainer_id=f"pre-sib-blocker-{blocker}",
                kind="pre_sib_blocker",
                source=selected_key,
                severity="blocking",
                blocks=["pre_sib_review", "candidate_approval"],
                message=f"Pre-SIB readiness is blocked by {blocker}.",
                next_action=(
                    "Review the Pre-SIB report and run the repair loop after the "
                    "blocker is resolved."
                ),
                evidence_refs=[_path_evidence_ref(paths, selected_key, "readiness.blocked_by")],
                evidence={"blocked_by": blocker, "review_state": readiness.get("review_state")},
            )
        )
    return explainers


def _repair_session_readiness_explainers(
    artifacts: dict[str, dict[str, Any]],
    paths: dict[str, Path],
) -> list[dict[str, Any]]:
    selected_key = _selected_artifact_key(
        artifacts,
        preferred="repaired_repair_session",
        fallback="repair_session",
    )
    if selected_key is None:
        return []
    session = _dict(artifacts.get(selected_key))
    readiness = _dict(session.get("readiness"))
    readiness_impact = _dict(session.get("readiness_impact"))
    explainers: list[dict[str, Any]] = []
    for blocker in _text_list(readiness_impact.get("blocked_by")) + _text_list(
        readiness.get("blocked_by")
    ):
        explainers.append(
            _readiness_explainer(
                explainer_id=f"repair-session-{blocker}",
                kind="repair_session_blocker",
                source=selected_key,
                severity="blocking",
                blocks=["candidate_approval"],
                message=f"Candidate approval is blocked by repair-session condition {blocker}.",
                next_action=(
                    "Inspect the repair session journal, answer the referenced request, "
                    "and rerun the candidate repair preview."
                ),
                evidence_refs=[
                    _path_evidence_ref(
                        paths,
                        selected_key,
                        "readiness_impact.blocked_by",
                    )
                ],
                evidence={"blocked_by": blocker},
            )
        )
    for blocker in _text_list(readiness_impact.get("platform_promotion_blocked_by")):
        explainers.append(
            _readiness_explainer(
                explainer_id=f"repair-session-platform-{blocker}",
                kind="platform_promotion_blocker",
                source=selected_key,
                severity="blocking",
                blocks=["platform_promotion"],
                message=f"Platform promotion is blocked by repair-session condition {blocker}.",
                next_action=(
                    "Complete candidate approval and Platform handoff prerequisites "
                    "before promotion."
                ),
                evidence_refs=[
                    _path_evidence_ref(
                        paths,
                        selected_key,
                        "readiness_impact.platform_promotion_blocked_by",
                    )
                ],
                evidence={"blocked_by": blocker},
            )
        )
    return explainers


def _promotion_gate_readiness_explainers(
    artifacts: dict[str, dict[str, Any]],
    paths: dict[str, Path],
) -> list[dict[str, Any]]:
    selected_key = _selected_artifact_key(
        artifacts,
        preferred="repaired_promotion_gate",
        fallback="promotion_gate",
    )
    if selected_key is None:
        return []
    gate = _dict(artifacts.get(selected_key))
    readiness = _dict(gate.get("readiness"))
    explainers: list[dict[str, Any]] = []
    for blocker in _text_list(readiness.get("blocked_by")):
        explainers.append(
            _readiness_explainer(
                explainer_id=f"promotion-gate-{blocker}",
                kind="promotion_gate_blocker",
                source=selected_key,
                severity="blocking",
                blocks=["platform_promotion"],
                message=f"Promotion gate is blocked by {blocker}.",
                next_action=(
                    "Inspect the promotion gate report and repair the selected "
                    "promotion path or source artifact."
                ),
                evidence_refs=[_path_evidence_ref(paths, selected_key, "readiness.blocked_by")],
                evidence={"blocked_by": blocker, "review_state": readiness.get("review_state")},
            )
        )
    return explainers


def _finding_readiness_explainers(
    findings: list[dict[str, Any]],
    *,
    collection: str,
) -> list[dict[str, Any]]:
    explainers: list[dict[str, Any]] = []
    for finding in findings:
        finding_id = _text(finding.get("finding_id"), "finding")
        severity = _text(finding.get("severity"), "review_required")
        if severity not in {"high", "medium", "blocking", "review_required"}:
            continue
        if finding_id.startswith("invariant_"):
            kind = "invariant_failure"
            blocks = ["metrics_validation", "candidate_approval"]
            next_action = (
                "Fix the inconsistent maturity metric inputs and rerun the Metrics "
                "validation target."
            )
        elif "stale" in _tokenize(finding_id) or "source" in _tokenize(finding_id):
            kind = "stale_ref"
            blocks = ["candidate_approval", "platform_promotion"]
            next_action = (
                "Refresh the stale source artifact chain before using maturity "
                "telemetry for review."
            )
        else:
            kind = "policy_failure"
            blocks = ["candidate_approval", "platform_promotion"]
            next_action = (
                "Inspect the policy finding evidence and complete the missing lifecycle handoff."
            )
        explainers.append(
            _readiness_explainer(
                explainer_id=f"{collection}-{finding_id}",
                kind=kind,
                source=f"idea_maturity_metrics_report.{collection}",
                severity=severity,
                blocks=blocks,
                message=_text(finding.get("message"), "Maturity report finding blocks readiness."),
                next_action=next_action,
                evidence_refs=[
                    f"runs/idea_maturity_metrics_report.json#{collection}.{_slug(finding_id)}"
                ],
                evidence=_dict(finding.get("evidence")),
            )
        )
    return explainers


def _readiness_explainers(
    artifacts: dict[str, dict[str, Any]],
    paths: dict[str, Path],
    *,
    policy_findings: list[dict[str, Any]],
    invariant_findings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    explainers = [
        *_pre_sib_readiness_explainers(artifacts, paths),
        *_repair_session_readiness_explainers(artifacts, paths),
        *_promotion_gate_readiness_explainers(artifacts, paths),
        *_finding_readiness_explainers(policy_findings, collection="policy_findings"),
        *_finding_readiness_explainers(invariant_findings, collection="invariant_findings"),
    ]
    return _dedupe_explainers(explainers)


def _derived_state(
    metrics: dict[str, Any], policy_findings: list[dict[str, Any]]
) -> dict[str, Any]:
    if metrics["read_model_publication_state"] == "published":
        lifecycle_state = "read_model_publication_complete"
    elif metrics["review_status"] in {"open", "merged"}:
        lifecycle_state = "git_review_active"
    elif metrics["promotion_request_state"] == "requested":
        lifecycle_state = "promotion_requested"
    elif metrics["candidate_approval_decision_state"] == "materialized":
        lifecycle_state = "approval_materialized"
    elif metrics["candidate_approval_state"] == "ready":
        lifecycle_state = "approval_ready"
    elif metrics["rerun_request_count"] > 0:
        lifecycle_state = "repair_rerun_requested"
    elif (
        metrics["candidate_node_count"] > 0
        and metrics["clarification_question_count"] > 0
        and metrics["candidate_gap_unresolved_count"] == 0
        and metrics["ontology_gap_unresolved_count"] == 0
    ):
        lifecycle_state = "repaired_candidate_ready"
    elif (
        metrics["candidate_gap_count_initial"] > 0
        or metrics["ontology_gap_count_initial"] > 0
        or metrics["clarification_question_count"] > 0
    ):
        lifecycle_state = "repair_required"
    elif metrics["candidate_node_count"] > 0:
        lifecycle_state = "intake_ready"
    else:
        lifecycle_state = "blocked" if policy_findings else "intake_ready"

    blockers = [
        finding["finding_id"]
        for finding in policy_findings
        if finding.get("severity") in {"high", "medium"}
    ]
    if metrics["remaining_blocker_count"] > 0 and "remaining_blockers" not in blockers:
        blockers.append("remaining_blockers")
    return {
        "lifecycle_state": "blocked"
        if blockers and lifecycle_state == "unknown"
        else lifecycle_state,
        "blockers": blockers,
        "candidate_approval_state": metrics["candidate_approval_state"],
        "platform_promotion_state": metrics["platform_promotion_state"],
        "review_status": metrics["review_status"],
        "read_model_publication_state": metrics["read_model_publication_state"],
    }


def _summary_projection(metrics: dict[str, Any], derived_state: dict[str, Any]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for key in SUMMARY_METRIC_KEYS:
        if key == "lifecycle_state":
            summary[key] = derived_state["lifecycle_state"]
        else:
            summary[key] = metrics.get(key)
    ontology_initial = _int(summary.get("ontology_gap_count_initial"))
    ontology_resolved = min(_int(summary.get("ontology_gap_resolved_count")), ontology_initial)
    ontology_unresolved = min(
        _int(summary.get("ontology_gap_unresolved_count")),
        max(ontology_initial - ontology_resolved, 0),
    )
    candidate_initial = _int(summary.get("candidate_gap_count_initial"))
    candidate_resolved = min(_int(summary.get("candidate_gap_resolved_count")), candidate_initial)
    candidate_unresolved = min(
        _int(summary.get("candidate_gap_unresolved_count")),
        max(candidate_initial - candidate_resolved, 0),
    )
    summary.update(
        {
            "ontology_gap_resolved_count": ontology_resolved,
            "ontology_gap_unresolved_count": ontology_unresolved,
            "ontology_gap_resolution_rate": _rate(ontology_resolved, ontology_initial),
            "candidate_gap_resolved_count": candidate_resolved,
            "candidate_gap_unresolved_count": candidate_unresolved,
            "candidate_gap_closure_rate": _rate(candidate_resolved, candidate_initial),
        }
    )
    return summary


def _metric_groups(metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        "clarification_load": {
            "clarification_question_count": metrics["clarification_question_count"],
            "blocking_question_count": metrics["blocking_question_count"],
            "review_required_question_count": metrics["review_required_question_count"],
        },
        "answer_materialization": {
            "answered_question_count": metrics["answered_question_count"],
            "accepted_answer_count": metrics["accepted_answer_count"],
            "deferred_answer_count": metrics["deferred_answer_count"],
            "invalid_answer_count": metrics["invalid_answer_count"],
            "materialized_answer_count": metrics["materialized_answer_count"],
            "unmaterialized_answer_count": metrics["unmaterialized_answer_count"],
            "answer_materialization_rate": metrics["answer_materialization_rate"],
            "per_gap_materialized_answer_count": metrics["per_gap_materialized_answer_count"],
            "consumed_answer_count": metrics["consumed_answer_count"],
            "aggregate_answer_count": metrics["aggregate_answer_count"],
            "dismissed_answer_count": metrics["dismissed_answer_count"],
            "closure_evidence_answer_count": metrics["closure_evidence_answer_count"],
            "ordinary_unmaterialized_answer_count": metrics["ordinary_unmaterialized_answer_count"],
            "answer_accounting": metrics["answer_accounting"],
            "stale_answer_count": metrics["stale_answer_count"],
        },
        "ontology_grounding": {
            "ontology_gap_count_initial": metrics["ontology_gap_count_initial"],
            "ontology_gap_resolved_count": metrics["ontology_gap_resolved_count"],
            "ontology_gap_unresolved_count": metrics["ontology_gap_unresolved_count"],
            "ontology_gap_resolution_rate": metrics["ontology_gap_resolution_rate"],
            "ontology_project_local_term_count": metrics["ontology_project_local_term_count"],
            "ontology_rejected_term_count": metrics["ontology_rejected_term_count"],
            "ontology_deferred_term_count": metrics["ontology_deferred_term_count"],
            "ontology_match_kind_counts": metrics["ontology_match_kind_counts"],
        },
        "candidate_repair": {
            "candidate_gap_count_initial": metrics["candidate_gap_count_initial"],
            "candidate_gap_resolved_count": metrics["candidate_gap_resolved_count"],
            "candidate_gap_unresolved_count": metrics["candidate_gap_unresolved_count"],
            "candidate_gap_closure_rate": metrics["candidate_gap_closure_rate"],
            "candidate_resolution_kind_counts": metrics["candidate_resolution_kind_counts"],
            "risk_accepted_count": metrics["risk_accepted_count"],
            "enforcement_mechanism_added_count": metrics["enforcement_mechanism_added_count"],
            "context_supplied_count": metrics["context_supplied_count"],
            "remaining_blocker_count": metrics["remaining_blocker_count"],
        },
        "workflow_friction": {
            "manual_handoff_count": metrics["manual_handoff_count"],
            "operator_command_count": metrics["operator_command_count"],
            "failed_gate_count": metrics["failed_gate_count"],
            "stale_ref_count": metrics["stale_ref_count"],
            "dry_run_count": metrics["dry_run_count"],
            "rerun_count": metrics["rerun_count"],
            "rerun_request_count": metrics["rerun_request_count"],
            "approval_attempt_count": metrics["approval_attempt_count"],
        },
        "temporal_progress": {
            "time_to_first_candidate_seconds": metrics["time_to_first_candidate_seconds"],
            "time_to_first_materialization_seconds": metrics[
                "time_to_first_materialization_seconds"
            ],
            "time_to_approval_ready_seconds": metrics["time_to_approval_ready_seconds"],
            "last_progress_at": metrics["last_progress_at"],
            "stalled_phase": metrics["stalled_phase"],
            "phase_dwell_seconds": metrics["phase_dwell_seconds"],
            "no_progress_rerun_count": metrics["no_progress_rerun_count"],
            "temporal_clock_source": metrics["temporal_clock_source"],
        },
        "promotion_readiness": {
            "candidate_approval_state": metrics["candidate_approval_state"],
            "candidate_approval_intent_state": metrics["candidate_approval_intent_state"],
            "candidate_approval_decision_state": metrics["candidate_approval_decision_state"],
            "platform_promotion_state": metrics["platform_promotion_state"],
            "promotion_path_count": metrics["promotion_path_count"],
            "promotion_request_state": metrics["promotion_request_state"],
            "promotion_execution_state": metrics["promotion_execution_state"],
        },
        "review_publication": {
            "review_status": metrics["review_status"],
            "review_pr_number": metrics["review_pr_number"],
            "review_merge_commit_sha": metrics["review_merge_commit_sha"],
            "read_model_publication_state": metrics["read_model_publication_state"],
            "published_file_count": metrics["published_file_count"],
            "published_manifest_digest": metrics["published_manifest_digest"],
        },
    }


def build_idea_maturity_metrics_report(
    *,
    paths: dict[str, Path],
) -> dict[str, Any]:
    artifacts, source_artifacts = _load_sources(paths)
    metrics = _metrics(artifacts)
    source_ref_findings = _source_ref_findings(artifacts, paths)
    metrics["stale_ref_count"] += len(source_ref_findings)
    policy_findings = _policy_findings(artifacts, metrics, source_ref_findings)
    invariant_findings = _invariant_findings(metrics)
    findings = [*policy_findings, *invariant_findings]
    readiness_explainers = _readiness_explainers(
        artifacts,
        paths,
        policy_findings=policy_findings,
        invariant_findings=invariant_findings,
    )
    loaded_required = any(
        key in artifacts
        for key in (
            "candidate_graph",
            "repaired_candidate_graph",
            "repaired_repair_session",
            "repaired_handoff",
            "candidate_approval_decision",
        )
    )
    if any(source.get("status") == "malformed" for source in source_artifacts.values()):
        status = "invalid"
    elif invariant_findings:
        status = "blocked"
    elif any(finding.get("severity") == "high" for finding in policy_findings):
        status = "blocked"
    elif (
        metrics["remaining_blocker_count"] > 0
        or metrics["failed_gate_count"] > 0
        or metrics["stale_ref_count"] > 0
    ):
        status = "blocked"
    elif not loaded_required:
        status = "partial"
    else:
        status = "ready"

    derived_state = _derived_state(metrics, policy_findings)
    source_refs = [
        source["source_ref"]
        for source in source_artifacts.values()
        if source.get("status") == "loaded" and source.get("source_ref")
    ]
    summary = _summary_projection(metrics, derived_state)
    return {
        "artifact_kind": "idea_maturity_metrics_report",
        "schema_version": SCHEMA_VERSION,
        "proposal_id": PROPOSAL_ID,
        "contract_ref": CONTRACT_REF,
        "contract": _metrics_contract_metadata(),
        "metric_pack_id": METRIC_PACK_ID,
        "metric_pack_ref": METRIC_PACK_REF,
        "metrics_rfc_ref": METRICS_RFC_REF,
        "authority_state": AUTHORITY_STATE,
        "generated_at": _now_iso(),
        "status": status,
        "candidate": _candidate_identity(artifacts),
        "source_artifacts": source_refs,
        "source_artifact_details": source_artifacts,
        "authority_boundary": _authority_boundary(),
        "privacy_boundary": _privacy_boundary(),
        "summary": summary,
        "groups": _metric_groups(metrics),
        "timeline": _dict(metrics.get("timeline")),
        "metrics": metrics,
        "derived_state": derived_state,
        "readiness_explainers": readiness_explainers,
        "policy_findings": policy_findings,
        "invariant_findings": invariant_findings,
        "findings": findings,
        "specgraph_summary": {
            "status": status,
            "finding_count": len(findings),
            "readiness_explainer_count": len(readiness_explainers),
            "policy_finding_count": len(policy_findings),
            "invariant_finding_count": len(invariant_findings),
        },
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    for key, default in DEFAULT_PATHS.items():
        parser.add_argument(f"--{key.replace('_', '-')}", type=Path, default=default)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    paths = {key: getattr(args, key) for key in DEFAULT_PATHS}
    report = build_idea_maturity_metrics_report(paths=paths)
    write_json(report, args.output)
    if args.strict and (
        report["status"] in {"blocked", "invalid"}
        or any(finding.get("severity") == "high" for finding in report["findings"])
    ):
        print(
            f"idea maturity metrics report invalid; wrote {_relative_ref(args.output)}",
            file=sys.stderr,
        )
        return 1
    print(
        f"wrote {_relative_ref(args.output)} status={report['status']} "
        f"lifecycle={report['derived_state']['lifecycle_state']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
