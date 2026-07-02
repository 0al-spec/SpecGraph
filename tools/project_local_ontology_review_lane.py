"""Build a review-only lane for project-local product ontology terms."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_ID = "0197"
SCHEMA_VERSION = 1
CONTRACT_REF = "specgraph.product-ontology.project-local-review-lane.v0.1"

DEFAULT_CANDIDATE_GRAPH_PATH = ROOT / "runs" / "candidate_spec_graph.json"
DEFAULT_DECISIONS_PATH = ROOT / "runs" / "product_ontology_gap_review_decisions.json"
DEFAULT_RERUN_PREVIEW_PATH = ROOT / "runs" / "idea_to_spec_rerun_preview.json"
DEFAULT_ACTIVE_CANDIDATE_PATH = ROOT / "runs" / "active_idea_to_spec_candidate.json"
DEFAULT_REPAIR_SESSION_PATH = ROOT / "runs" / "idea_to_spec_repair_session.json"
DEFAULT_OUTPUT_PATH = ROOT / "runs" / "project_local_ontology_review_lane.json"

AUTHORITY_FALSE_FIELDS = (
    "may_execute_prompt_agent",
    "may_apply_decisions_to_source_artifacts",
    "may_mutate_candidate_source_artifacts",
    "may_mutate_canonical_specs",
    "may_write_ontology_package",
    "may_write_ontology_lockfile",
    "may_accept_ontology_terms",
    "may_mark_candidate_graph_accepted",
    "may_create_branch_or_commit",
    "may_open_pull_request",
    "may_publish_read_model",
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

DECISION_STATUS = {
    "bind_existing_term": "bound_existing",
    "alias_existing_term": "aliased",
    "alias": "aliased",
    "propose_project_local_term": "kept_project_local",
    "keep_project_local": "kept_project_local",
    "reject_non_domain_term": "rejected",
    "reject": "rejected",
    "request_workspace_promotion": "promotion_requested",
    "promote_to_workspace_ontology": "promotion_requested",
    "defer_requires_owner": "deferred",
    "defer": "deferred",
}

STATUS_PRECEDENCE = {
    "unreviewed": 0,
    "deferred": 1,
    "kept_project_local": 2,
    "promotion_requested": 3,
    "rejected": 4,
    "aliased": 5,
    "bound_existing": 6,
}

REVIEW_ACTIONS = (
    "keep_project_local",
    "bind_existing",
    "alias",
    "reject",
    "request_workspace_promotion",
    "defer",
)


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any, default: str = "") -> str:
    return value.strip() if isinstance(value, str) and value.strip() else default


def _slug(value: str, fallback: str = "term") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or fallback


def _term_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def _relative_ref(path: Path | None) -> str | None:
    if path is None:
        return None
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return f"external:{path.name or 'artifact'}"


def _sha256(path: Path | None) -> str | None:
    if path is None or not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
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
    return value


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _load_optional(path: Path | None) -> tuple[dict[str, Any], Path | None]:
    if path is None or not path.exists():
        return {}, None
    return load_json(path), path


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
        "source": "project_local_ontology_review_lane",
        "evidence": evidence or {},
    }


def _authority_boundary() -> dict[str, bool]:
    return {key: False for key in AUTHORITY_FALSE_FIELDS}


def _privacy_boundary() -> dict[str, bool]:
    return {
        "raw_idea_text_published": False,
        "raw_prompt_published": False,
        "raw_model_output_published": False,
        "raw_operator_note_published": False,
        "private_operator_state_published": False,
    }


def _source_artifact(
    key: str,
    payload: dict[str, Any],
    path: Path | None,
    *,
    required: bool = False,
) -> dict[str, Any]:
    status = "present" if payload else ("missing_required" if required else "missing_optional")
    return {
        "artifact_key": key,
        "artifact_kind": payload.get("artifact_kind") if payload else None,
        "contract_ref": payload.get("contract_ref") if payload else None,
        "schema_version": payload.get("schema_version") if payload else None,
        "source_ref": _relative_ref(path),
        "sha256": _sha256(path),
        "status": status,
        "summary": _public_safe(payload.get("summary")) if payload else {},
    }


def _validate_authority(
    *,
    payload: dict[str, Any],
    artifact_key: str,
    findings: list[dict[str, Any]],
) -> None:
    boundary = _dict(payload.get("authority_boundary"))
    for key in AUTHORITY_FALSE_FIELDS:
        if boundary.get(key) is True:
            findings.append(
                _finding(
                    finding_id=f"{artifact_key}_authority_expanded",
                    severity="review_required",
                    message=f"{artifact_key} authority_boundary.{key} must not be true.",
                    evidence={"artifact_key": artifact_key, "field": key},
                )
            )


def _gap_items(candidate_graph: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for raw_node in _list(candidate_graph.get("nodes")):
        node = _dict(raw_node)
        node_id = _text(node.get("id"))
        for raw_gap in _list(node.get("gaps")):
            gap = _dict(raw_gap)
            if _text(gap.get("kind")) != "ontology_gap":
                continue
            gap_id = _text(gap.get("id"))
            term = _text(gap.get("term"))
            source_ref = _text(gap.get("source_ref"))
            items.append(
                {
                    "gap_id": gap_id,
                    "node_id": node_id,
                    "term": term,
                    "term_key": _term_key(term),
                    "source_ref": source_ref,
                    "source_kind": _text(gap.get("source_kind")),
                    "statement": _text(gap.get("statement")),
                    "suggested_action": _text(gap.get("suggested_action")),
                    "target_ref": f"{node_id}.gaps.{gap_id}" if node_id and gap_id else gap_id,
                    "blocks_candidate_graph": bool(gap.get("blocks_candidate_graph")),
                }
            )
    return items


def _decision_status(decision: dict[str, Any]) -> str:
    decision_type = _text(decision.get("decision_type")) or _text(decision.get("decision"))
    return DECISION_STATUS.get(decision_type, "unreviewed")


def _decision_term_key(decision: dict[str, Any]) -> str:
    return _term_key(_text(decision.get("term")) or _text(decision.get("proposed_term")))


def _decision_matches_gap(decision: dict[str, Any], gap: dict[str, Any]) -> bool:
    target_ref = _text(decision.get("target_ref"))
    status = _decision_status(decision)
    if target_ref == "candidate_graph.gaps":
        if status in {"rejected", "deferred"}:
            return True
    elif target_ref and target_ref in {
        _text(gap.get("gap_id")),
        _text(gap.get("source_ref")),
        _text(gap.get("target_ref")),
    }:
        return True
    decision_key = _decision_term_key(decision)
    return bool(decision_key and decision_key == _text(gap.get("term_key")))


def _decision_projection(decision: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "id",
        "decision_type",
        "status",
        "materialization_intent",
        "request_id",
        "request_kind",
        "target_artifact",
        "target_ref",
        "source_answer_kind",
        "source_answer_status",
        "term",
        "term_scope",
        "ontology_ref",
        "alias_of",
        "reason",
        "scope",
        "proposed_term",
    )
    projected = {
        key: _public_safe(decision.get(key))
        for key in fields
        if decision.get(key) not in ("", None, [], {})
    }
    projected["review_status"] = _decision_status(decision)
    return projected


def _resolved_gap_index(rerun_preview: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    ontology_preview = _dict(_dict(rerun_preview.get("rerun_preview")).get("ontology_gap_preview"))
    resolved: dict[tuple[str, str], dict[str, Any]] = {}
    for raw_gap in _list(ontology_preview.get("resolved_ontology_gaps")):
        gap = _dict(raw_gap)
        key = (_text(gap.get("node_id")), _text(gap.get("gap_id")))
        if key != ("", ""):
            resolved[key] = _public_safe(gap)
    return resolved


def _term_effect(
    *,
    status: str,
    gap_refs: list[dict[str, Any]],
    resolved_gap_refs: list[dict[str, Any]],
    has_rerun_preview: bool,
) -> dict[str, Any]:
    if status == "unreviewed":
        return {
            "candidate_readiness_effect": "blocks_until_reviewed",
            "next_action": "choose_project_local_ontology_decision",
        }
    if status == "deferred":
        return {
            "candidate_readiness_effect": "blocked_by_owner_review",
            "next_action": "complete_owner_review_or_choose_non_deferred_decision",
        }
    if status in {"kept_project_local", "bound_existing", "aliased", "rejected"}:
        if resolved_gap_refs:
            return {
                "candidate_readiness_effect": "preview_resolves_ontology_gap",
                "resolved_gap_count": len(resolved_gap_refs),
                "next_action": "review_repaired_candidate_handoff",
            }
        if has_rerun_preview:
            return {
                "candidate_readiness_effect": "decision_not_reflected_in_preview",
                "next_action": "rebuild_rerun_preview_for_current_decisions",
            }
        return {
            "candidate_readiness_effect": "decision_pending_rerun_preview",
            "next_action": "build_rerun_preview_for_current_decisions",
        }
    if status == "promotion_requested":
        return {
            "candidate_readiness_effect": "workspace_promotion_requested_review_only",
            "next_action": "review_workspace_ontology_promotion_request",
        }
    if gap_refs:
        return {
            "candidate_readiness_effect": "unknown_review_state",
            "next_action": "review_project_local_ontology_term",
        }
    return {
        "candidate_readiness_effect": "no_candidate_gap",
        "next_action": "inspect_decision_evidence",
    }


def _term_records(
    *,
    candidate_graph: dict[str, Any],
    decisions_report: dict[str, Any],
    rerun_preview: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    warnings: list[dict[str, Any]] = []
    gaps = _gap_items(candidate_graph)
    decisions = [_dict(item) for item in _list(decisions_report.get("decisions"))]
    resolved_index = _resolved_gap_index(rerun_preview)
    has_rerun_preview = bool(rerun_preview)

    grouped: dict[str, dict[str, Any]] = {}
    for gap in gaps:
        key = _text(gap.get("term_key")) or _slug(_text(gap.get("gap_id")))
        record = grouped.setdefault(
            key,
            {
                "id": (
                    f"project-local-ontology-term.{_slug(_text(gap.get('term')), fallback=key)}"
                ),
                "term": _text(gap.get("term")),
                "term_key": key,
                "status": "unreviewed",
                "source_refs": [],
                "gap_refs": [],
                "resolved_gap_refs": [],
                "decisions": [],
                "suggested_actions": list(REVIEW_ACTIONS),
            },
        )
        if gap.get("source_ref") and gap.get("source_ref") not in record["source_refs"]:
            record["source_refs"].append(gap["source_ref"])
        gap_ref = {
            key_name: gap[key_name]
            for key_name in (
                "gap_id",
                "node_id",
                "target_ref",
                "source_ref",
                "source_kind",
                "statement",
                "suggested_action",
            )
            if gap.get(key_name) not in ("", None, [], {})
        }
        record["gap_refs"].append(gap_ref)
        resolved = resolved_index.get((_text(gap.get("node_id")), _text(gap.get("gap_id"))))
        if resolved:
            record["resolved_gap_refs"].append(resolved)

    for decision in decisions:
        matched = False
        for gap in gaps:
            if not _decision_matches_gap(decision, gap):
                continue
            matched = True
            key = _text(gap.get("term_key")) or _decision_term_key(decision)
            record = grouped.setdefault(
                key,
                {
                    "id": (
                        "project-local-ontology-term."
                        f"{_slug(_text(decision.get('term')), fallback=key)}"
                    ),
                    "term": _text(decision.get("term")) or _text(decision.get("proposed_term")),
                    "term_key": key,
                    "status": "unreviewed",
                    "source_refs": [],
                    "gap_refs": [],
                    "resolved_gap_refs": [],
                    "decisions": [],
                    "suggested_actions": list(REVIEW_ACTIONS),
                },
            )
            projected = _decision_projection(decision)
            if projected not in record["decisions"]:
                record["decisions"].append(projected)
            status = projected["review_status"]
            if STATUS_PRECEDENCE.get(status, 0) > STATUS_PRECEDENCE.get(record["status"], 0):
                record["status"] = status
                record["selected_decision_id"] = projected.get("id")
        if not matched:
            decision_key = _decision_term_key(decision)
            if decision_key:
                decision_term = _text(decision.get("term")) or _text(decision.get("proposed_term"))
                record = grouped.setdefault(
                    decision_key,
                    {
                        "id": (
                            "project-local-ontology-term."
                            f"{_slug(decision_term, fallback=decision_key)}"
                        ),
                        "term": decision_term,
                        "term_key": decision_key,
                        "status": _decision_status(decision),
                        "source_refs": [],
                        "gap_refs": [],
                        "resolved_gap_refs": [],
                        "decisions": [],
                        "suggested_actions": list(REVIEW_ACTIONS),
                    },
                )
                projected = _decision_projection(decision)
                if projected not in record["decisions"]:
                    record["decisions"].append(projected)
            else:
                warnings.append(
                    _finding(
                        finding_id="ontology_review_decision_unmatched",
                        severity="warning",
                        message="Ontology review decision did not match a candidate ontology gap.",
                        evidence={
                            "decision_id": _text(decision.get("id")),
                            "decision_type": _text(decision.get("decision_type")),
                            "target_ref": _text(decision.get("target_ref")),
                        },
                    )
                )

    records: list[dict[str, Any]] = []
    for record in grouped.values():
        record["effect"] = _term_effect(
            status=record["status"],
            gap_refs=record["gap_refs"],
            resolved_gap_refs=record["resolved_gap_refs"],
            has_rerun_preview=has_rerun_preview,
        )
        record["evidence_refs"] = [
            ref
            for ref in (
                "runs/candidate_spec_graph.json" if record["gap_refs"] else "",
                "runs/product_ontology_gap_review_decisions.json" if record["decisions"] else "",
                "runs/idea_to_spec_rerun_preview.json" if record["resolved_gap_refs"] else "",
            )
            if ref
        ]
        records.append(record)
    records.sort(key=lambda item: (_text(item.get("status")), _text(item.get("term")).casefold()))
    return records, warnings


def _counts(records: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {status: 0 for status in STATUS_PRECEDENCE}
    for record in records:
        status = _text(record.get("status"), "unreviewed")
        counts[status] = counts.get(status, 0) + 1
    return {key: value for key, value in counts.items() if value}


def _context(
    *,
    active_candidate: dict[str, Any],
    repair_session: dict[str, Any],
    candidate_graph: dict[str, Any],
) -> dict[str, Any]:
    candidate = _dict(active_candidate.get("candidate"))
    session = _dict(repair_session.get("session"))
    summary = _dict(repair_session.get("summary"))
    active_frame = _dict(candidate_graph.get("active_frame")) or _dict(
        active_candidate.get("active_frame")
    )
    return {
        "workspace_id": _text(candidate.get("candidate_id")) or _text(summary.get("candidate_id")),
        "candidate_id": _text(candidate.get("candidate_id")) or _text(summary.get("candidate_id")),
        "workspace_route": _text(_dict(active_candidate.get("summary")).get("workspace_route")),
        "workflow_lane": _text(candidate.get("workflow_lane"))
        or _text(summary.get("workflow_lane")),
        "repair_session_id": _text(session.get("session_id")) or _text(summary.get("session_id")),
        "domain_refs": _list(active_frame.get("domain_refs")),
        "context_refs": _list(active_frame.get("context_refs")),
        "ontology_refs": _list(active_frame.get("ontology_refs")),
    }


def build_project_local_ontology_review_lane(
    *,
    candidate_graph: dict[str, Any],
    decisions_report: dict[str, Any] | None = None,
    rerun_preview: dict[str, Any] | None = None,
    active_candidate: dict[str, Any] | None = None,
    repair_session: dict[str, Any] | None = None,
    candidate_graph_path: Path | None = None,
    decisions_path: Path | None = None,
    rerun_preview_path: Path | None = None,
    active_candidate_path: Path | None = None,
    repair_session_path: Path | None = None,
) -> dict[str, Any]:
    decisions_report = decisions_report or {}
    rerun_preview = rerun_preview or {}
    active_candidate = active_candidate or {}
    repair_session = repair_session or {}
    findings: list[dict[str, Any]] = []

    if candidate_graph.get("artifact_kind") != "candidate_spec_graph":
        findings.append(
            _finding(
                finding_id="candidate_graph_wrong_artifact_kind",
                severity="review_required",
                message="Project-local ontology review lane requires candidate_spec_graph input.",
                evidence={"artifact_kind": candidate_graph.get("artifact_kind")},
            )
        )
    _validate_authority(payload=candidate_graph, artifact_key="candidate_graph", findings=findings)
    if decisions_report:
        if decisions_report.get("artifact_kind") != "product_ontology_gap_review_decisions":
            findings.append(
                _finding(
                    finding_id="ontology_decisions_wrong_artifact_kind",
                    severity="review_required",
                    message=(
                        "Ontology review lane can only consume "
                        "product_ontology_gap_review_decisions."
                    ),
                    evidence={"artifact_kind": decisions_report.get("artifact_kind")},
                )
            )
        _validate_authority(
            payload=decisions_report,
            artifact_key="ontology_decisions",
            findings=findings,
        )
    if rerun_preview:
        if rerun_preview.get("artifact_kind") != "idea_to_spec_rerun_preview":
            findings.append(
                _finding(
                    finding_id="rerun_preview_wrong_artifact_kind",
                    severity="review_required",
                    message="Rerun preview input must be idea_to_spec_rerun_preview.",
                    evidence={"artifact_kind": rerun_preview.get("artifact_kind")},
                )
            )
        _validate_authority(payload=rerun_preview, artifact_key="rerun_preview", findings=findings)

    terms, warnings = _term_records(
        candidate_graph=candidate_graph,
        decisions_report=decisions_report,
        rerun_preview=rerun_preview,
    )
    status_counts = _counts(terms)
    unreviewed_count = status_counts.get("unreviewed", 0)
    deferred_count = status_counts.get("deferred", 0)
    blocking_count = unreviewed_count + deferred_count
    if unreviewed_count:
        findings.append(
            _finding(
                finding_id="project_local_ontology_terms_unreviewed",
                severity="review_required",
                message="Some project-local ontology terms still need operator review.",
                evidence={"unreviewed_term_count": unreviewed_count},
            )
        )
    if deferred_count:
        findings.append(
            _finding(
                finding_id="project_local_ontology_terms_deferred",
                severity="review_required",
                message="Some project-local ontology terms are deferred for owner review.",
                evidence={"deferred_term_count": deferred_count},
            )
        )
    ready = not findings
    source_artifacts = {
        "candidate_graph": _source_artifact(
            "candidate_graph",
            candidate_graph,
            candidate_graph_path,
            required=True,
        ),
        "ontology_decisions": _source_artifact(
            "ontology_decisions",
            decisions_report,
            decisions_path,
        ),
        "rerun_preview": _source_artifact("rerun_preview", rerun_preview, rerun_preview_path),
        "active_candidate": _source_artifact(
            "active_candidate",
            active_candidate,
            active_candidate_path,
        ),
        "repair_session": _source_artifact("repair_session", repair_session, repair_session_path),
    }
    return {
        "artifact_kind": "project_local_ontology_review_lane",
        "schema_version": SCHEMA_VERSION,
        "proposal_id": PROPOSAL_ID,
        "contract_ref": CONTRACT_REF,
        "generated_at": _now_iso(),
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "materialization_intent": "review_lane_only",
        "context": _context(
            active_candidate=active_candidate,
            repair_session=repair_session,
            candidate_graph=candidate_graph,
        ),
        "source_artifacts": source_artifacts,
        "terms": terms,
        "review_decision_schema": {
            "supported_actions": list(REVIEW_ACTIONS),
            "authority": "operator_intent_only",
            "request_workspace_promotion_effect": "proposal_only_no_ontology_write",
        },
        "readiness": {
            "ready": ready,
            "review_state": (
                "project_local_ontology_review_ready"
                if ready
                else "project_local_ontology_review_required"
            ),
            "blocked_by": [finding["finding_id"] for finding in findings],
            "next_artifact": (
                "runs/idea_maturity_metrics_report.json"
                if ready
                else "SpecSpace project-local ontology review lane"
            ),
        },
        "authority_boundary": _authority_boundary(),
        "privacy_boundary": _privacy_boundary(),
        "findings": findings,
        "warnings": warnings,
        "summary": {
            "status": (
                "project_local_ontology_review_ready"
                if ready
                else "project_local_ontology_review_required"
            ),
            "term_count": len(terms),
            "reviewed_term_count": len(terms) - blocking_count,
            "blocking_term_count": blocking_count,
            "unreviewed_term_count": unreviewed_count,
            "deferred_term_count": deferred_count,
            "status_counts": status_counts,
            "finding_count": len(findings),
            "warning_count": len(warnings),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-graph", default=DEFAULT_CANDIDATE_GRAPH_PATH, type=Path)
    parser.add_argument("--ontology-decisions", default=DEFAULT_DECISIONS_PATH, type=Path)
    parser.add_argument("--rerun-preview", default=DEFAULT_RERUN_PREVIEW_PATH, type=Path)
    parser.add_argument("--active-candidate", default=DEFAULT_ACTIVE_CANDIDATE_PATH, type=Path)
    parser.add_argument("--repair-session", default=DEFAULT_REPAIR_SESSION_PATH, type=Path)
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, type=Path)
    parser.add_argument("--strict", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    candidate_graph = load_json(args.candidate_graph)
    decisions_report, decisions_path = _load_optional(args.ontology_decisions)
    rerun_preview, rerun_preview_path = _load_optional(args.rerun_preview)
    active_candidate, active_candidate_path = _load_optional(args.active_candidate)
    repair_session, repair_session_path = _load_optional(args.repair_session)
    report = build_project_local_ontology_review_lane(
        candidate_graph=candidate_graph,
        decisions_report=decisions_report,
        rerun_preview=rerun_preview,
        active_candidate=active_candidate,
        repair_session=repair_session,
        candidate_graph_path=args.candidate_graph,
        decisions_path=decisions_path,
        rerun_preview_path=rerun_preview_path,
        active_candidate_path=active_candidate_path,
        repair_session_path=repair_session_path,
    )
    write_json(report, args.output)
    summary = _dict(report.get("summary"))
    print(
        f"{summary.get('status', 'unknown')}: "
        f"{summary.get('reviewed_term_count', 0)}/{summary.get('term_count', 0)} reviewed -> "
        f"{_relative_ref(args.output)}"
    )
    if args.strict and not _dict(report.get("readiness")).get("ready"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
