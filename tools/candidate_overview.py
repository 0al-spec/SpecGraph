"""Build a public-safe narrative overview for an idea-to-spec candidate."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_ID = "0201"
SCHEMA_VERSION = 1
CONTRACT_REF = "specgraph.idea-to-spec.candidate-overview.v0.1"

DEFAULT_INTAKE_PATH = ROOT / "runs" / "idea_event_storming_intake.json"
DEFAULT_CANDIDATE_GRAPH_PATH = ROOT / "runs" / "candidate_spec_graph.json"
DEFAULT_REPAIRED_CANDIDATE_GRAPH_PATH = ROOT / "runs" / "repaired_candidate_spec_graph.json"
DEFAULT_REPAIR_SESSION_PATH = ROOT / "runs" / "idea_to_spec_repair_session.json"
DEFAULT_REPAIRED_REPAIR_SESSION_PATH = ROOT / "runs" / "repaired_idea_to_spec_repair_session.json"
DEFAULT_MATURITY_PATH = ROOT / "runs" / "idea_maturity_metrics_report.json"
DEFAULT_PROJECT_LOCAL_ONTOLOGY_LANE_PATH = ROOT / "runs" / "project_local_ontology_review_lane.json"
DEFAULT_PROJECT_LOCAL_ONTOLOGY_EFFECT_PATH = (
    ROOT / "runs" / "project_local_ontology_decision_effect_report.json"
)
DEFAULT_ONTOLOGY_PACKAGE_INDEX_PATH = ROOT / "runs" / "ontology_package_index.json"
DEFAULT_ONTOLOGY_COMPATIBILITY_DIFF_PATH = (
    ROOT / "runs" / "ontology_compatibility_diff_preview.json"
)
DEFAULT_REPAIRED_HANDOFF_PATH = ROOT / "runs" / "repaired_candidate_promotion_handoff_report.json"
DEFAULT_OUTPUT_PATH = ROOT / "runs" / "candidate_overview.json"

AUTHORITY_FALSE_FIELDS = (
    "may_execute_prompt_agent",
    "may_execute_specgraph",
    "may_execute_platform",
    "may_apply_answers_to_source_artifacts",
    "may_apply_decisions_to_source_artifacts",
    "may_mutate_candidate_artifacts",
    "may_mutate_candidate_source_artifacts",
    "may_mutate_canonical_specs",
    "may_write_ontology_package",
    "may_write_ontology_lockfile",
    "may_accept_ontology_terms",
    "may_mark_candidate_graph_accepted",
    "may_create_branch_or_commit",
    "may_open_pull_request",
    "may_merge_pull_request",
    "may_publish_read_model",
)
TOP_LEVEL_AUTHORITY_FALSE_FIELDS = (
    "canonical_mutations_allowed",
    "tracked_artifacts_written",
)
APPLICABILITY_SCOPE_FIELDS = (
    ("domains", "domains"),
    ("lifecycle_phases", "lifecyclePhases"),
    ("agent_types", "agentTypes"),
    ("subsystems", "subsystems"),
    ("runtimes", "runtimes"),
    ("platforms", "platforms"),
    ("contexts", "contexts"),
)
CLASSIFIED_CHANGE_DETAIL_FIELDS = (
    "target_kind",
    "before",
    "after",
    "compatibility",
)

EXPECTED_SOURCE_ARTIFACT_KINDS = {
    "intake": "idea_event_storming_intake",
    "candidate_graph": "candidate_spec_graph",
    "repaired_candidate_graph": "candidate_spec_graph",
    "repair_session": "idea_to_spec_repair_session_journal",
    "repaired_repair_session": "idea_to_spec_repair_session_journal",
    "idea_maturity": "idea_maturity_metrics_report",
    "project_local_ontology_lane": "project_local_ontology_review_lane",
    "project_local_ontology_effect": "project_local_ontology_decision_effect_report",
    "ontology_package_index": "ontology_package_index",
    "ontology_compatibility_diff": "ontology_compatibility_diff_preview",
    "repaired_handoff": "repaired_candidate_promotion_handoff_report",
}

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
    "root_intent_text",
}

PRIVATE_PATH_MARKERS = ("/Users/", "/home/", "/private/", "/tmp/", "/var/folders/")
PRIVATE_VALUE_MARKERS = ("-----BEGIN", "api-key", "apikey", "api_key", "bearer ", "token=")

EVENT_STORMING_GROUPS = (
    "actors",
    "commands",
    "domain_events",
    "policies",
    "constraints",
    "external_systems",
    "risks",
    "vocabulary_questions",
)

WORKFLOW_RELATIONS = (
    "actor_triggers_command",
    "command_emits_event",
    "event_informs_policy",
    "event_informs_constraint",
    "constraint_applies_to_command",
    "policy_applies_to_command",
)


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any, default: str = "") -> str:
    return value.strip() if isinstance(value, str) and value.strip() else default


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


def _safe_text(value: Any, default: str = "") -> str:
    safe = _public_safe(_text(value, default))
    return safe if isinstance(safe, str) and safe else default


def _slug(value: str, fallback: str = "item") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or fallback


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
        "source": "candidate_overview",
        "message": message,
        "evidence": _public_safe(evidence or {}),
    }


def _authority_boundary() -> dict[str, bool]:
    return {field: False for field in AUTHORITY_FALSE_FIELDS}


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
    for field in TOP_LEVEL_AUTHORITY_FALSE_FIELDS:
        if payload.get(field) is True:
            fields.append(f"{prefix}{field}")
    for field in AUTHORITY_FALSE_FIELDS:
        if payload.get(field) is True:
            fields.append(f"{prefix}{field}")
    for field, value in payload.items():
        if field.startswith("may_") and value is True:
            fields.append(f"{prefix}{field}")
    boundary = _dict(payload.get("authority_boundary"))
    for field in AUTHORITY_FALSE_FIELDS:
        if boundary.get(field) is True:
            fields.append(f"{prefix}authority_boundary.{field}")
    for field, value in boundary.items():
        if field.startswith("may_") and value is True:
            fields.append(f"{prefix}authority_boundary.{field}")
    return list(dict.fromkeys(fields))


def _source_artifact(
    key: str,
    payload: dict[str, Any],
    path: Path | None,
    error: str | None,
) -> dict[str, Any]:
    status = "malformed" if error else ("present" if payload else "missing")
    result: dict[str, Any] = {
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
        readiness = _dict(payload.get("readiness"))
        if readiness:
            result["readiness"] = _public_safe(readiness)
    return result


def _candidate_identity(
    *,
    intake: dict[str, Any],
    candidate_graph: dict[str, Any],
    maturity: dict[str, Any],
) -> dict[str, Any]:
    workspace = _dict(_dict(intake.get("source_intake")).get("workspace"))
    graph_workspace = _dict(_dict(candidate_graph.get("source_intake")).get("workspace"))
    maturity_candidate = _dict(maturity.get("candidate"))
    candidate_id = (
        _text(workspace.get("candidate_id"))
        or _text(graph_workspace.get("candidate_id"))
        or _text(maturity_candidate.get("candidate_id"))
        or "unknown-candidate"
    )
    display_name = (
        _text(workspace.get("display_name"))
        or _text(graph_workspace.get("display_name"))
        or _text(maturity_candidate.get("display_name"))
        or candidate_id.replace("-", " ").title()
    )
    public_route = _text(workspace.get("public_route")) or _text(
        graph_workspace.get("public_route")
    )
    identity = {
        "candidate_id": candidate_id,
        "display_name": display_name,
        "public_route": public_route or f"/{_slug(candidate_id, 'candidate')}",
    }
    return {key: _safe_text(value) for key, value in identity.items()}


def _payload_candidate_id(payload: dict[str, Any]) -> str:
    workspace = _dict(_dict(payload.get("source_intake")).get("workspace"))
    candidate = _dict(payload.get("candidate"))
    summary = _dict(payload.get("summary"))
    return (
        _text(workspace.get("candidate_id"))
        or _text(candidate.get("candidate_id"))
        or _text(summary.get("candidate_id"))
    )


def _root_intent_summary(intake: dict[str, Any], candidate_graph: dict[str, Any]) -> str:
    root_intent = _dict(intake.get("root_intent"))
    summary = _text(root_intent.get("summary")) or _text(root_intent.get("statement"))
    if summary:
        return _safe_text(summary, "No public intent summary available.")
    nodes = [node for node in _list(candidate_graph.get("nodes")) if isinstance(node, dict)]
    boundary = next(
        (
            node
            for node in nodes
            if _text(node.get("kind")) in {"product_spec_boundary", "product_boundary"}
        ),
        nodes[0] if nodes else {},
    )
    return _safe_text(
        _text(boundary.get("description")) or _text(boundary.get("title")),
        "No public intent summary available.",
    )


def _compact_event_entry(entry: dict[str, Any]) -> dict[str, Any]:
    return {
        key: _public_safe(value)
        for key, value in {
            "id": _text(entry.get("id")),
            "name": _text(entry.get("name")) or _text(entry.get("statement")),
            "role": _text(entry.get("role")),
            "kind": _text(entry.get("kind")),
            "actor_refs": _list(entry.get("actor_refs")),
            "command_refs": _list(entry.get("command_refs")),
            "produces_event_refs": _list(entry.get("produces_event_refs")),
            "trigger_event_refs": _list(entry.get("trigger_event_refs")),
            "source_refs": _list(entry.get("source_refs")),
        }.items()
        if value not in ("", [], {})
    }


def _event_storming_summary(intake: dict[str, Any]) -> dict[str, Any]:
    event_storming = _dict(intake.get("event_storming"))
    groups: dict[str, Any] = {}
    for group in EVENT_STORMING_GROUPS:
        entries = [entry for entry in _list(event_storming.get(group)) if isinstance(entry, dict)]
        groups[group] = {
            "count": len(entries),
            "items": [_compact_event_entry(entry) for entry in entries[:12]],
        }
    return groups


def _node_summary(candidate_graph: dict[str, Any]) -> dict[str, Any]:
    nodes = [node for node in _list(candidate_graph.get("nodes")) if isinstance(node, dict)]
    by_kind = Counter(_text(node.get("kind"), "unknown") for node in nodes)
    compact_nodes: list[dict[str, Any]] = []
    aliases: list[dict[str, str]] = []
    alias_by_node_id: dict[str, str] = {}
    for node in sorted(nodes, key=lambda item: _text(item.get("id"))):
        node_id = _text(node.get("id"))
        display_alias = _safe_text(node.get("display_alias"))
        if node_id and display_alias:
            alias_by_node_id[node_id] = display_alias
            aliases.append(
                {
                    "node_id": node_id,
                    "display_alias": display_alias,
                    "display_alias_source": _safe_text(node.get("display_alias_source")),
                    "title": _safe_text(node.get("title")),
                    "kind": _safe_text(node.get("kind")),
                }
            )
    for node in nodes[:24]:
        gaps = [gap for gap in _list(node.get("gaps")) if isinstance(gap, dict)]
        compact_nodes.append(
            {
                "id": _text(node.get("id")),
                "display_alias": _safe_text(node.get("display_alias")),
                "display_alias_source": _safe_text(node.get("display_alias_source")),
                "title": _text(node.get("title")),
                "kind": _text(node.get("kind")),
                "description": _text(node.get("description")),
                "requirement_count": len(_list(node.get("requirements"))),
                "acceptance_criteria_count": len(_list(node.get("acceptance_criteria"))),
                "gap_count": len(gaps),
                "ontology_gap_count": sum(
                    1 for gap in gaps if _text(gap.get("kind")) == "ontology_gap"
                ),
                "candidate_gap_count": sum(
                    1 for gap in gaps if _text(gap.get("kind")) != "ontology_gap"
                ),
                "source_event_refs": _list(node.get("source_event_refs"))[:16],
            }
        )
    return {
        "count": len(nodes),
        "kind_counts": dict(sorted(by_kind.items())),
        "aliases": aliases,
        "alias_count": len(aliases),
        "alias_by_node_id": alias_by_node_id,
        "items": [_public_safe(node) for node in compact_nodes],
    }


def _topology_summary(
    candidate_graph: dict[str, Any], *, alias_by_node_id: dict[str, str]
) -> dict[str, Any]:
    edges = [edge for edge in _list(candidate_graph.get("edges")) if isinstance(edge, dict)]
    relation_counts = Counter(_text(edge.get("relation"), "unknown") for edge in edges)
    workflow_edge_count = sum(relation_counts.get(relation, 0) for relation in WORKFLOW_RELATIONS)
    examples = [
        {
            "id": _text(edge.get("id")),
            "relation": _text(edge.get("relation")),
            "from": _text(edge.get("from")),
            "from_display_alias": _safe_text(alias_by_node_id.get(_text(edge.get("from")))),
            "to": _text(edge.get("to")),
            "to_display_alias": _safe_text(alias_by_node_id.get(_text(edge.get("to")))),
            "source_event_refs": _list(edge.get("source_event_refs"))[:8],
        }
        for edge in edges[:24]
    ]
    return {
        "edge_count": len(edges),
        "workflow_edge_count": workflow_edge_count,
        "relation_counts": dict(sorted(relation_counts.items())),
        "examples": _public_safe(examples),
    }


def _repair_summary(
    *,
    repair_session: dict[str, Any],
    repaired_repair_session: dict[str, Any],
    repaired_handoff: dict[str, Any],
) -> dict[str, Any]:
    selected = repaired_repair_session or repair_session
    selected_summary = _dict(selected.get("summary"))
    handoff_summary = _dict(repaired_handoff.get("summary"))
    source = (
        "repaired" if repaired_repair_session else ("standard" if repair_session else "missing")
    )

    def bool_with_handoff_fallback(field: str) -> bool:
        if field in selected_summary:
            return selected_summary.get(field) is True
        return handoff_summary.get(field) is True

    return {
        "source": source,
        "status": _text(selected_summary.get("status"), "missing"),
        "ready_for_candidate_approval": bool_with_handoff_fallback("ready_for_candidate_approval"),
        "ready_for_platform_promotion": bool_with_handoff_fallback("ready_for_platform_promotion"),
        "accepted_answer_count": _int(selected_summary.get("accepted_answer_count")),
        "resolved_ontology_gap_count": _int(
            selected_summary.get("resolved_ontology_gap_count")
            or handoff_summary.get("resolved_ontology_gap_count")
        ),
        "unresolved_ontology_gap_count": _int(
            selected_summary.get("unresolved_ontology_gap_count")
            or handoff_summary.get("unresolved_ontology_gap_count")
        ),
        "resolved_candidate_gap_count": _int(
            selected_summary.get("resolved_candidate_gap_count")
            or handoff_summary.get("resolved_candidate_gap_count")
        ),
        "unresolved_candidate_gap_count": _int(
            selected_summary.get("unresolved_candidate_gap_count")
            or handoff_summary.get("unresolved_candidate_gap_count")
        ),
        "removed_gap_count": _int(handoff_summary.get("removed_gap_count")),
    }


def _maturity_summary(maturity: dict[str, Any]) -> dict[str, Any]:
    summary = _dict(maturity.get("summary"))
    return {
        "status": _text(maturity.get("status"), "missing"),
        "lifecycle_state": _text(summary.get("lifecycle_state"), "unknown"),
        "candidate_approval_state": _text(summary.get("candidate_approval_state"), "unknown"),
        "platform_promotion_state": _text(summary.get("platform_promotion_state"), "unknown"),
        "remaining_blocker_count": _int(summary.get("remaining_blocker_count")),
        "ontology_gap_unresolved_count": _int(summary.get("ontology_gap_unresolved_count")),
        "candidate_gap_unresolved_count": _int(summary.get("candidate_gap_unresolved_count")),
        "project_local_ontology_review_status": _text(
            summary.get("project_local_ontology_review_status"), "missing"
        ),
    }


def _project_local_effect_matches_lane(
    *,
    lane: dict[str, Any],
    effect: dict[str, Any],
    source_artifacts: dict[str, dict[str, Any]],
) -> bool:
    if not lane or not effect:
        return False
    lane_source = _dict(
        _dict(effect.get("source_artifacts")).get("project_local_ontology_review_lane")
    )
    if lane_source.get("artifact_kind") != "project_local_ontology_review_lane":
        return False

    loaded_lane = _dict(source_artifacts.get("project_local_ontology_lane"))
    loaded_lane_sha = _text(loaded_lane.get("sha256"))
    source_lane_sha = _text(lane_source.get("sha256"))
    if loaded_lane_sha or source_lane_sha:
        return bool(loaded_lane_sha and source_lane_sha and loaded_lane_sha == source_lane_sha)

    lane_context = _dict(lane.get("context"))
    effect_context = _dict(effect.get("context"))
    if lane_context or effect_context:
        for field in ("workspace_id", "candidate_id", "repair_session_id", "workflow_lane"):
            if _text(lane_context.get(field)) != _text(effect_context.get(field)):
                return False

    lane_summary = _dict(lane.get("summary"))
    source_summary = _dict(lane_source.get("summary"))
    for field in ("status", "term_count", "reviewed_term_count", "unreviewed_term_count"):
        if source_summary.get(field) != lane_summary.get(field):
            return False
    return True


def _is_resolving_project_local_effect(effect: dict[str, Any]) -> bool:
    return (
        _text(effect.get("maturity_effect")) == "resolves_project_local_review"
        and _text(effect.get("status")) == "accepted_for_project_local_preview"
        and _text(effect.get("review_action"))
        in {"keep_project_local", "bind_existing", "alias", "reject"}
    )


def _project_local_ontology_summary(
    *,
    lane: dict[str, Any],
    effect: dict[str, Any],
    source_artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    lane_summary = _dict(lane.get("summary"))
    effect_summary = _dict(effect.get("summary"))
    lane_status = _text(lane_summary.get("status"), "missing")
    effect_matches_lane = _project_local_effect_matches_lane(
        lane=lane,
        effect=effect,
        source_artifacts=source_artifacts,
    )
    raw_effect_status = _text(effect_summary.get("status"), "missing")
    effect_status = raw_effect_status if effect_matches_lane else "missing"
    review_status = effect_status if effect_status != "missing" else lane_status
    effects_by_term: dict[str, dict[str, Any]] = {}
    for raw_effect in _list(effect.get("decision_effects")) if effect_matches_lane else []:
        item = _dict(raw_effect)
        term_key = _text(item.get("term_key"))
        if term_key:
            effects_by_term[term_key] = item
    terms: list[dict[str, Any]] = []
    for raw_term in _list(lane.get("terms"))[:16]:
        term = _dict(raw_term)
        term_key = _text(term.get("term_key"))
        review_effect = _dict(effects_by_term.get(term_key))
        effective_status = (
            "reviewed_by_project_local_decision"
            if review_effect and _is_resolving_project_local_effect(review_effect)
            else _text(term.get("status"), "unreviewed")
        )
        terms.append(
            _public_safe(
                {
                    **term,
                    "effective_status": effective_status,
                    "review_effect": {
                        "status": _text(review_effect.get("status")),
                        "review_action": _text(review_effect.get("review_action")),
                        "maturity_effect": _text(review_effect.get("maturity_effect")),
                        "evidence_refs": _list(review_effect.get("evidence_refs"))[:8],
                    }
                    if review_effect
                    else {},
                }
            )
        )
    return {
        "review_status": review_status,
        "lane_status": lane_status,
        "effect_status": effect_status,
        "raw_effect_status": raw_effect_status,
        "effect_matches_lane": effect_matches_lane,
        "term_count": _int(lane_summary.get("term_count")),
        "reviewed_term_count": _int(lane_summary.get("reviewed_term_count")),
        "unreviewed_term_count": _int(lane_summary.get("unreviewed_term_count")),
        "accepted_decision_count": _int(effect_summary.get("accepted_decision_count")),
        "blocking_decision_count": _int(effect_summary.get("blocking_decision_count")),
        "terms": terms,
    }


def _string_items(value: Any, *, limit: int = 16) -> list[str]:
    return [item.strip() for item in _list(value) if isinstance(item, str) and item.strip()][:limit]


def _applicability_scope(value: Any) -> dict[str, list[str]]:
    scope = _dict(value)
    return {
        output_key: values
        for output_key, input_key in APPLICABILITY_SCOPE_FIELDS
        if (values := _string_items(scope.get(input_key)))
    }


def _applicability_records(value: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for raw_record in _list(value)[:16]:
        record = _dict(raw_record)
        record_id = _text(record.get("id"))
        if not record_id:
            continue
        records.append(
            {
                "id": record_id,
                "layer": _text(record.get("layer")) or None,
                "text": _safe_text(record.get("text"), "No applicability text published."),
            }
        )
    return records


def _classified_changes(value: Any) -> list[dict[str, str]]:
    changes: list[dict[str, str]] = []
    for raw_change in _list(value)[:24]:
        change = _dict(raw_change)
        kind = _text(change.get("kind"))
        ref = _text(change.get("ref"))
        if not kind or not ref:
            continue
        projected = {"kind": kind, "ref": ref}
        for field in CLASSIFIED_CHANGE_DETAIL_FIELDS:
            detail = _text(change.get(field))
            if detail:
                projected[field] = detail
        changes.append(projected)
    return changes


def _ontology_applicability_summary(
    *,
    package_index: dict[str, Any],
    compatibility_diff: dict[str, Any],
    source_artifacts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    profiles: list[dict[str, Any]] = []
    for raw_package in _list(package_index.get("packages"))[:8]:
        package = _dict(raw_package)
        profile = _dict(package.get("model_applicability"))
        profile_summary = _dict(package.get("model_applicability_summary"))
        if not profile and _text(profile_summary.get("status")) != "declared":
            continue
        package_id = _text(package.get("package_id"), "unknown-package")
        version = _text(package.get("version"))
        lock = _dict(package.get("lock"))
        package_ref = _text(lock.get("package_ref")) or (
            f"{package_id}@{version}" if version else package_id
        )
        profiles.append(
            {
                "package_id": package_id,
                "package_ref": package_ref,
                "status": _text(profile_summary.get("status"), "declared"),
                "applies_to": _applicability_scope(profile.get("applies_to")),
                "excludes": _applicability_scope(profile.get("excludes")),
                "assumptions": _applicability_records(profile.get("assumptions")),
                "invalidation_triggers": _applicability_records(
                    profile.get("invalidation_triggers")
                ),
            }
        )

    profile_refs = {item["package_ref"] for item in profiles if _text(item.get("package_ref"))}
    diff_package_refs = [
        ref
        for key in ("package_ref", "from_ref", "to_ref")
        if (ref := _text(compatibility_diff.get(key)))
    ]
    matched_package_refs = sorted(profile_refs.intersection(diff_package_refs))
    diff_matches_profile = bool(compatibility_diff and profile_refs and matched_package_refs)
    classification = (
        _dict(compatibility_diff.get("change_classification")) if diff_matches_profile else {}
    )
    structural_changes = _classified_changes(classification.get("structural_changes"))
    annotation_changes = _classified_changes(classification.get("annotation_changes"))
    applicability_changes = _classified_changes(classification.get("applicability_changes"))
    classified_change_count = (
        len(structural_changes) + len(annotation_changes) + len(applicability_changes)
    )
    source_refs = [
        source_ref
        for key in ("ontology_package_index", "ontology_compatibility_diff")
        if (source_ref := _text(_dict(source_artifacts.get(key)).get("source_ref")))
        and _dict(source_artifacts.get(key)).get("status") == "present"
    ]
    status = "not_published"
    if profiles:
        status = "declared"
    if compatibility_diff and not diff_matches_profile:
        status = "change_evidence_stale"
    if classified_change_count:
        status = "change_review_required"
    return {
        "proposal_id": "0216",
        "status": status,
        "review_only": True,
        "profile_count": len(profiles),
        "assumption_count": sum(len(item["assumptions"]) for item in profiles),
        "invalidation_trigger_count": sum(len(item["invalidation_triggers"]) for item in profiles),
        "profiles": profiles,
        "change_classification": {
            "status": (
                "published"
                if diff_matches_profile
                else ("stale_package_mismatch" if compatibility_diff else "not_published")
            ),
            "diff_package_refs": diff_package_refs,
            "matched_package_refs": matched_package_refs,
            "structural_changes": structural_changes,
            "annotation_changes": annotation_changes,
            "applicability_changes": applicability_changes,
            "classified_change_count": classified_change_count,
        },
        "source_refs": source_refs,
        "authority_boundary": {
            "may_infer_applicability": False,
            "may_enforce_runtime_policy": False,
            "may_mutate_candidate_artifacts": False,
            "may_write_ontology_package": False,
            "may_accept_ontology_terms": False,
            "may_approve_candidate": False,
            "may_promote_candidate": False,
        },
    }


def _next_action(
    *,
    maturity: dict[str, Any],
    repair: dict[str, Any],
    project_local_ontology: dict[str, Any],
) -> dict[str, Any]:
    explainers = [
        item for item in _list(maturity.get("readiness_explainers")) if isinstance(item, dict)
    ]
    for explainer in explainers:
        action = _text(explainer.get("next_action"))
        if action:
            return {
                "action_id": _text(explainer.get("id"), "maturity_next_action"),
                "label": action,
                "source": "idea_maturity.readiness_explainers",
                "evidence_refs": _list(explainer.get("evidence_refs"))[:8],
            }
    if project_local_ontology.get("blocking_decision_count"):
        return {
            "action_id": "review_project_local_ontology_terms",
            "label": "Review remaining project-local ontology decisions.",
            "source": "project_local_ontology",
            "evidence_refs": ["runs/project_local_ontology_review_lane.json"],
        }
    if not repair.get("ready_for_candidate_approval"):
        return {
            "action_id": "continue_repair_loop",
            "label": "Answer open repair questions or run the repaired handoff preview.",
            "source": "repair_session",
            "evidence_refs": ["runs/idea_to_spec_repair_session.json"],
        }
    if repair.get("ready_for_candidate_approval") and not repair.get(
        "ready_for_platform_promotion"
    ):
        return {
            "action_id": "request_candidate_approval_intent",
            "label": "Request candidate approval for promotion review.",
            "source": "repaired_repair_session",
            "evidence_refs": ["runs/repaired_idea_to_spec_repair_session.json"],
        }
    return {
        "action_id": "inspect_candidate_overview",
        "label": "Inspect the candidate overview and continue with the next lifecycle gate.",
        "source": "candidate_overview",
        "evidence_refs": ["runs/candidate_overview.json"],
    }


def _source_findings(source_artifacts: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    required = {"intake", "candidate_graph"}
    for key, artifact in source_artifacts.items():
        if artifact["status"] == "malformed":
            findings.append(
                _finding(
                    finding_id="candidate_overview_source_malformed",
                    severity="review_required",
                    message="Candidate overview skipped a malformed source artifact.",
                    evidence={"artifact_key": key, "source_ref": artifact.get("source_ref")},
                )
            )
        expected_kind = EXPECTED_SOURCE_ARTIFACT_KINDS.get(key)
        if (
            artifact["status"] == "present"
            and expected_kind
            and artifact.get("artifact_kind") != expected_kind
        ):
            findings.append(
                _finding(
                    finding_id="candidate_overview_source_wrong_artifact_kind",
                    severity="review_required",
                    message="Candidate overview source artifact kind is unsupported.",
                    evidence={
                        "artifact_key": key,
                        "source_ref": artifact.get("source_ref"),
                        "expected_artifact_kind": expected_kind,
                        "artifact_kind": artifact.get("artifact_kind"),
                    },
                )
            )
        if key in required and artifact["status"] != "present":
            findings.append(
                _finding(
                    finding_id="candidate_overview_required_source_missing",
                    severity="review_required",
                    message="Candidate overview requires intake and candidate graph artifacts.",
                    evidence={"artifact_key": key, "source_ref": artifact.get("source_ref")},
                )
            )
    return findings


def _select_candidate_graph(
    *,
    candidate_graph: dict[str, Any],
    repaired_candidate_graph: dict[str, Any],
    identity: dict[str, Any],
) -> tuple[dict[str, Any], str, list[dict[str, Any]]]:
    if not repaired_candidate_graph:
        return candidate_graph, "candidate_graph", []
    expected_candidate_id = _text(identity.get("candidate_id"))
    repaired_candidate_id = _payload_candidate_id(repaired_candidate_graph)
    if not repaired_candidate_id:
        return (
            candidate_graph,
            "candidate_graph",
            [
                _finding(
                    finding_id="candidate_overview_repaired_graph_provenance_missing",
                    severity="review_required",
                    message=(
                        "Candidate overview did not prefer repaired candidate graph "
                        "because candidate provenance is missing."
                    ),
                    evidence={
                        "expected_candidate_id": expected_candidate_id,
                    },
                )
            ],
        )
    if repaired_candidate_id != expected_candidate_id:
        return (
            candidate_graph,
            "candidate_graph",
            [
                _finding(
                    finding_id="candidate_overview_repaired_graph_candidate_mismatch",
                    severity="review_required",
                    message=(
                        "Candidate overview did not prefer repaired candidate graph "
                        "because its candidate id differs from the selected workspace."
                    ),
                    evidence={
                        "expected_candidate_id": expected_candidate_id,
                        "repaired_candidate_id": repaired_candidate_id,
                    },
                )
            ],
        )
    return repaired_candidate_graph, "repaired_candidate_graph", []


def _authority_findings(payloads: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for key, payload in payloads.items():
        fields = _true_authority_fields(payload, prefix=f"{key}.")
        if fields:
            findings.append(
                _finding(
                    finding_id="candidate_overview_source_authority_expansion",
                    severity="review_required",
                    message=(
                        "Candidate overview source artifact claims authority outside "
                        "review-only bounds."
                    ),
                    evidence={"artifact_key": key, "fields": fields[:16]},
                )
            )
    return findings


def build_candidate_overview(
    *,
    intake: dict[str, Any],
    candidate_graph: dict[str, Any],
    repaired_candidate_graph: dict[str, Any] | None = None,
    repair_session: dict[str, Any] | None = None,
    repaired_repair_session: dict[str, Any] | None = None,
    maturity: dict[str, Any] | None = None,
    project_local_ontology_lane: dict[str, Any] | None = None,
    project_local_ontology_effect: dict[str, Any] | None = None,
    ontology_package_index: dict[str, Any] | None = None,
    ontology_compatibility_diff: dict[str, Any] | None = None,
    repaired_handoff: dict[str, Any] | None = None,
    source_artifacts: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    repaired_candidate_graph = repaired_candidate_graph or {}
    repair_session = repair_session or {}
    repaired_repair_session = repaired_repair_session or {}
    maturity = maturity or {}
    project_local_ontology_lane = project_local_ontology_lane or {}
    project_local_ontology_effect = project_local_ontology_effect or {}
    ontology_package_index = ontology_package_index or {}
    ontology_compatibility_diff = ontology_compatibility_diff or {}
    repaired_handoff = repaired_handoff or {}
    source_artifacts = source_artifacts or {}

    identity = _candidate_identity(
        intake=intake,
        candidate_graph=candidate_graph,
        maturity=maturity,
    )
    selected_graph, graph_source, graph_selection_findings = _select_candidate_graph(
        candidate_graph=candidate_graph,
        repaired_candidate_graph=repaired_candidate_graph,
        identity=identity,
    )
    event_storming = _event_storming_summary(intake)
    nodes = _node_summary(selected_graph)
    topology = _topology_summary(selected_graph, alias_by_node_id=nodes["alias_by_node_id"])
    repair = _repair_summary(
        repair_session=repair_session,
        repaired_repair_session=repaired_repair_session,
        repaired_handoff=repaired_handoff,
    )
    maturity_view = _maturity_summary(maturity)
    ontology = _project_local_ontology_summary(
        lane=project_local_ontology_lane,
        effect=project_local_ontology_effect,
        source_artifacts=source_artifacts,
    )
    ontology_applicability = _ontology_applicability_summary(
        package_index=ontology_package_index,
        compatibility_diff=ontology_compatibility_diff,
        source_artifacts=source_artifacts,
    )
    next_action = _next_action(
        maturity=maturity,
        repair=repair,
        project_local_ontology=ontology,
    )
    findings = [
        *_source_findings(source_artifacts),
        *graph_selection_findings,
        *_authority_findings(
            {
                "intake": intake,
                "candidate_graph": candidate_graph,
                "repaired_candidate_graph": repaired_candidate_graph,
                "repair_session": repair_session,
                "repaired_repair_session": repaired_repair_session,
                "maturity": maturity,
                "project_local_ontology_lane": project_local_ontology_lane,
                "project_local_ontology_effect": project_local_ontology_effect,
                "ontology_package_index": ontology_package_index,
                "ontology_compatibility_diff": ontology_compatibility_diff,
                "repaired_handoff": repaired_handoff,
            }
        ),
    ]
    ready = not any(finding.get("severity") == "review_required" for finding in findings)

    product_intent = _root_intent_summary(intake, selected_graph)
    lifecycle_state = maturity_view["lifecycle_state"]
    approval_phrase = (
        "ready for candidate approval review"
        if repair["ready_for_candidate_approval"]
        else "still in review or repair"
    )

    summary = {
        "status": "candidate_overview_ready" if ready else "candidate_overview_review_required",
        "candidate_id": identity["candidate_id"],
        "display_name": identity["display_name"],
        "graph_source": graph_source,
        "node_count": nodes["count"],
        "edge_count": topology["edge_count"],
        "workflow_edge_count": topology["workflow_edge_count"],
        "remaining_blocker_count": maturity_view["remaining_blocker_count"],
        "ready_for_candidate_approval": repair["ready_for_candidate_approval"],
        "ready_for_platform_promotion": repair["ready_for_platform_promotion"],
        "project_local_ontology_review_status": ontology["review_status"],
        "ontology_applicability_status": ontology_applicability["status"],
        "finding_count": len(findings),
    }

    return {
        "artifact_kind": "candidate_overview",
        "schema_version": SCHEMA_VERSION,
        "contract_ref": CONTRACT_REF,
        "proposal_id": PROPOSAL_ID,
        "generated_at": _now_iso(),
        "authority_boundary": _authority_boundary(),
        "privacy_boundary": _privacy_boundary(),
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "source_artifacts": _public_safe(source_artifacts),
        "summary": summary,
        "readiness": {
            "ready": ready,
            "review_state": summary["status"],
            "blocked_by": [
                finding["finding_id"]
                for finding in findings
                if finding["severity"] == "review_required"
            ],
        },
        "candidate": _public_safe(identity),
        "narrative": {
            "product_intent": _safe_text(product_intent, "No public intent summary available."),
            "understood_scope": (
                f"{identity['display_name']} currently has {nodes['count']} candidate nodes, "
                f"{event_storming['commands']['count']} commands, "
                f"{event_storming['domain_events']['count']} domain events, and "
                f"{topology['workflow_edge_count']} workflow topology edges."
            ),
            "readiness": (
                f"The candidate lifecycle is {lifecycle_state}; the repaired surface is "
                f"{approval_phrase}."
            ),
            "next_action": _safe_text(next_action["label"]),
        },
        "sections": {
            "event_storming": event_storming,
            "candidate_nodes": nodes,
            "topology": topology,
            "repair": repair,
            "idea_maturity": maturity_view,
            "project_local_ontology": ontology,
            "ontology_applicability": _public_safe(ontology_applicability),
        },
        "next_action": next_action,
        "findings": findings,
    }


def build_candidate_overview_from_paths(
    *,
    intake_path: Path,
    candidate_graph_path: Path,
    repaired_candidate_graph_path: Path | None,
    repair_session_path: Path | None,
    repaired_repair_session_path: Path | None,
    maturity_path: Path | None,
    project_local_ontology_lane_path: Path | None,
    project_local_ontology_effect_path: Path | None,
    ontology_package_index_path: Path | None,
    ontology_compatibility_diff_path: Path | None,
    repaired_handoff_path: Path | None,
) -> dict[str, Any]:
    loaded: dict[str, tuple[dict[str, Any], Path | None, str | None]] = {
        "intake": _load_optional(intake_path),
        "candidate_graph": _load_optional(candidate_graph_path),
        "repaired_candidate_graph": _load_optional(repaired_candidate_graph_path),
        "repair_session": _load_optional(repair_session_path),
        "repaired_repair_session": _load_optional(repaired_repair_session_path),
        "idea_maturity": _load_optional(maturity_path),
        "project_local_ontology_lane": _load_optional(project_local_ontology_lane_path),
        "project_local_ontology_effect": _load_optional(project_local_ontology_effect_path),
        "ontology_package_index": _load_optional(ontology_package_index_path),
        "ontology_compatibility_diff": _load_optional(ontology_compatibility_diff_path),
        "repaired_handoff": _load_optional(repaired_handoff_path),
    }
    source_artifacts = {
        key: _source_artifact(key, payload, path, error)
        for key, (payload, path, error) in loaded.items()
    }
    return build_candidate_overview(
        intake=loaded["intake"][0],
        candidate_graph=loaded["candidate_graph"][0],
        repaired_candidate_graph=loaded["repaired_candidate_graph"][0],
        repair_session=loaded["repair_session"][0],
        repaired_repair_session=loaded["repaired_repair_session"][0],
        maturity=loaded["idea_maturity"][0],
        project_local_ontology_lane=loaded["project_local_ontology_lane"][0],
        project_local_ontology_effect=loaded["project_local_ontology_effect"][0],
        ontology_package_index=loaded["ontology_package_index"][0],
        ontology_compatibility_diff=loaded["ontology_compatibility_diff"][0],
        repaired_handoff=loaded["repaired_handoff"][0],
        source_artifacts=source_artifacts,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--intake", type=Path, default=DEFAULT_INTAKE_PATH)
    parser.add_argument("--candidate-graph", type=Path, default=DEFAULT_CANDIDATE_GRAPH_PATH)
    parser.add_argument(
        "--repaired-candidate-graph",
        type=Path,
        default=DEFAULT_REPAIRED_CANDIDATE_GRAPH_PATH,
    )
    parser.add_argument("--repair-session", type=Path, default=DEFAULT_REPAIR_SESSION_PATH)
    parser.add_argument(
        "--repaired-repair-session",
        type=Path,
        default=DEFAULT_REPAIRED_REPAIR_SESSION_PATH,
    )
    parser.add_argument("--idea-maturity", type=Path, default=DEFAULT_MATURITY_PATH)
    parser.add_argument(
        "--project-local-ontology-lane",
        type=Path,
        default=DEFAULT_PROJECT_LOCAL_ONTOLOGY_LANE_PATH,
    )
    parser.add_argument(
        "--project-local-ontology-effect",
        type=Path,
        default=DEFAULT_PROJECT_LOCAL_ONTOLOGY_EFFECT_PATH,
    )
    parser.add_argument(
        "--ontology-package-index",
        type=Path,
        default=DEFAULT_ONTOLOGY_PACKAGE_INDEX_PATH,
    )
    parser.add_argument(
        "--ontology-compatibility-diff",
        type=Path,
        default=DEFAULT_ONTOLOGY_COMPATIBILITY_DIFF_PATH,
    )
    parser.add_argument("--repaired-handoff", type=Path, default=DEFAULT_REPAIRED_HANDOFF_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--strict", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    overview = build_candidate_overview_from_paths(
        intake_path=args.intake,
        candidate_graph_path=args.candidate_graph,
        repaired_candidate_graph_path=args.repaired_candidate_graph,
        repair_session_path=args.repair_session,
        repaired_repair_session_path=args.repaired_repair_session,
        maturity_path=args.idea_maturity,
        project_local_ontology_lane_path=args.project_local_ontology_lane,
        project_local_ontology_effect_path=args.project_local_ontology_effect,
        ontology_package_index_path=args.ontology_package_index,
        ontology_compatibility_diff_path=args.ontology_compatibility_diff,
        repaired_handoff_path=args.repaired_handoff,
    )
    write_json(overview, args.output)
    if args.strict and not _dict(overview.get("readiness")).get("ready"):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
