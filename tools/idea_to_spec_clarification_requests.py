"""Build a unified clarification-request surface for idea-to-spec flows."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_ID = "0163"
DEPTH_DRIVEN_PROPOSAL_ID = "0207"
SCHEMA_VERSION = 1
CONTRACT_REF = "specgraph.idea-to-spec.clarification-requests.v0.1"
USER_IDEA_INTAKE_SESSION_CONTRACT_REF = "specgraph.idea-to-spec.user-idea-intake-session.v0.1"
EVENT_STORMING_INTAKE_CONTRACT_REF = "specgraph.idea-to-spec.event-storming-intake.v0.1"
CANDIDATE_GRAPH_CONTRACT_REF = "specgraph.idea-to-spec.candidate-spec-graph.v0.1"
PRE_SIB_CONTRACT_REF = "specgraph.idea-to-spec.pre-sib-coherence-report.v0.1"
REPAIR_LOOP_CONTRACT_REF = "specgraph.idea-to-spec.candidate-repair-loop.v0.1"
ONTOLOGY_GAP_REVIEW_KIND = "ontology_gap_review_workflow"
IDEA_MATURITY_KIND = "idea_maturity_metrics_report"
IDEA_MATURITY_CONTRACT_REF = "specgraph.idea-to-spec.maturity-metrics-report.v0.1"

DEFAULT_SESSION_PATH = ROOT / "runs" / "user_idea_intake_session.json"
DEFAULT_INTAKE_PATH = ROOT / "runs" / "idea_event_storming_intake.json"
DEFAULT_CANDIDATE_GRAPH_PATH = ROOT / "runs" / "candidate_spec_graph.json"
DEFAULT_PRE_SIB_PATH = ROOT / "runs" / "pre_sib_coherence_report.json"
DEFAULT_REPAIR_LOOP_PATH = ROOT / "runs" / "candidate_repair_loop_report.json"
DEFAULT_IDEA_MATURITY_PATH = ROOT / "runs" / "idea_maturity_metrics_report.json"
DEFAULT_OUTPUT_PATH = ROOT / "runs" / "idea_to_spec_clarification_requests.json"

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

REPAIR_ACTION_KINDS = {
    "add_candidate_edge": {
        "kind": "graph_repair",
        "answer_shape": "accept_preview_edge | reject_preview_edge | propose_relation",
        "actions": ["accept_preview_edge", "reject_preview_edge", "propose_relation"],
    },
    "add_acceptance_criterion": {
        "kind": "missing_acceptance_criteria",
        "answer_shape": "accept_preview_criterion | provide_acceptance_criterion | reject",
        "actions": [
            "accept_preview_criterion",
            "provide_acceptance_criterion",
            "reject",
        ],
    },
    "add_ontology_gap": {
        "kind": "ontology_gap",
        "answer_shape": "bind_existing_term | alias | propose_project_local_term | reject | defer",
        "actions": [
            "bind_existing_term",
            "alias",
            "propose_project_local_term",
            "reject",
            "defer",
        ],
    },
    "downgrade_claim": {
        "kind": "weak_claim",
        "answer_shape": "accept_downgrade | add_evidence | narrow_scope | reject_claim",
        "actions": ["accept_downgrade", "add_evidence", "narrow_scope", "reject_claim"],
    },
    "request_context_for_gaps": {
        "kind": "ontology_gap",
        "answer_shape": "bind_existing_term | alias | propose_project_local_term | reject | defer",
        "actions": [
            "bind_existing_term",
            "alias",
            "propose_project_local_term",
            "reject",
            "defer",
        ],
    },
}

PRE_SIB_FINDING_KINDS = {
    "pre_sib_orphan_nodes": {
        "kind": "graph_repair",
        "answer_shape": "accept_preview_edge | reject_preview_edge | propose_relation",
    },
    "pre_sib_acceptance_criteria_gap": {
        "kind": "missing_acceptance_criteria",
        "answer_shape": "accept_preview_criterion | provide_acceptance_criterion | reject",
    },
    "pre_sib_ontology_coverage_gap": {
        "kind": "ontology_gap",
        "answer_shape": "bind_existing_term | alias | propose_project_local_term | reject | defer",
    },
    "pre_sib_unresolved_gaps": {
        "kind": "ontology_gap",
        "answer_shape": "bind_existing_term | alias | propose_project_local_term | reject | defer",
    },
    "pre_sib_unsupported_strong_claims": {
        "kind": "weak_claim",
        "answer_shape": "accept_downgrade | add_evidence | narrow_scope | reject_claim",
    },
    "pre_sib_duplicate_node_titles": {
        "kind": "contradiction",
        "answer_shape": "rename_node | merge_duplicate | accept_duplicate",
    },
}

ACTIVE_FRAME_ANSWER_SHAPES = {
    "project": "text",
    "subsystem": "text",
    "lifecycle_phase": "text",
    "ontology_refs": "ontology_ref[]",
    "ontology_layer_refs": "ontology_layer_ref[]",
    "domain_refs": "domain_ref[]",
    "context_refs": "context_ref[]",
    "model_applicability_refs": "model_applicability_ref[]",
}

ONTOLOGY_GAP_ANSWER_SHAPE = (
    "bind_existing_term | alias | propose_project_local_term | reject | defer"
)
ONTOLOGY_GAP_ACTIONS = [
    "bind_existing_term",
    "alias",
    "propose_project_local_term",
    "reject",
    "defer",
]
CANDIDATE_GAP_ANSWER_SHAPE = "answer_question | provide_candidate_context | reject | defer"
CANDIDATE_GAP_ACTIONS = ["answer_question", "provide_candidate_context", "reject", "defer"]

EVENT_STORMING_DEPTH_CATEGORIES = {
    "actors": {
        "metric": "actor_count",
        "question": "Which actors should participate in this product workflow?",
        "block": "candidate_structure_depth.actor_count",
    },
    "commands": {
        "metric": "command_count",
        "question": "Which user or system commands should drive this product workflow?",
        "block": "candidate_structure_depth.command_count",
    },
    "domain_events": {
        "metric": "domain_event_count",
        "question": "Which domain events should be recorded when this workflow changes state?",
        "block": "candidate_structure_depth.domain_event_count",
    },
    "policies": {
        "metric": "policy_count",
        "question": "Which policies should react to domain events or constrain commands?",
        "block": "candidate_structure_depth.policy_count",
    },
    "constraints": {
        "metric": "constraint_count",
        "question": "Which product constraints should bound this workflow?",
        "block": "candidate_structure_depth.constraint_count",
    },
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


def _slug(value: str, fallback: str = "request") -> str:
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


def _load_optional(path: Path | None) -> tuple[dict[str, Any] | None, str]:
    if path is None:
        return None, "not_configured"
    if not path.exists():
        return None, "missing"
    return load_json(path), "present"


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
        "source": "idea_to_spec_clarification_requests",
        "evidence": evidence or {},
    }


def _source_artifact(
    *,
    name: str,
    path: Path | None,
    status: str,
    artifact: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "name": name,
        "path": _relative_ref(path) if path else None,
        "status": status,
        "artifact_kind": artifact.get("artifact_kind") if artifact else None,
        "contract_ref": artifact.get("contract_ref") if artifact else None,
        "review_state": _dict(artifact.get("readiness")).get("review_state")
        if artifact
        else artifact.get("review_state")
        if artifact
        else None,
    }


def _source_finding(
    finding: dict[str, Any],
    *,
    source_artifact: str,
) -> dict[str, Any]:
    return {
        "source_artifact": source_artifact,
        "finding_id": finding.get("finding_id"),
        "severity": finding.get("severity"),
        "message": finding.get("message"),
        "evidence": _public_safe(_dict(finding.get("evidence"))),
    }


def _finding_refs(finding_ids: list[str], *, source_artifact: str) -> list[dict[str, Any]]:
    return [
        {
            "source_artifact": source_artifact,
            "finding_id": finding_id,
        }
        for finding_id in finding_ids
    ]


def _request(
    *,
    request_id: str,
    kind: str,
    severity: str,
    question: str,
    target_artifact: str,
    target_ref: str,
    blocks: list[str],
    suggested_answer_shape: str,
    source_findings: list[dict[str, Any]],
    suggested_actions: list[str] | None = None,
    status: str = "open",
) -> dict[str, Any]:
    return {
        "id": request_id,
        "kind": kind,
        "severity": severity,
        "question": question,
        "target_artifact": target_artifact,
        "target_ref": target_ref,
        "blocks": blocks,
        "suggested_answer_shape": suggested_answer_shape,
        "suggested_actions": suggested_actions or [],
        "source_findings": source_findings,
        "status": status,
    }


def _append_request(
    requests: list[dict[str, Any]],
    request: dict[str, Any],
    used_ids: set[str],
) -> None:
    base_id = _text(request.get("id"), "clarification.request")
    request_id = base_id
    counter = 2
    while request_id in used_ids:
        request_id = f"{base_id}.{counter}"
        counter += 1
    request["id"] = request_id
    used_ids.add(request_id)
    requests.append(request)


def _field_from_block(block: str) -> str:
    return block.rsplit(".", 1)[-1]


def _fields_for_question(question: dict[str, Any]) -> set[str]:
    fields = {_field_from_block(block) for block in _text_list(question.get("blocks"))}
    question_id = _text(question.get("id"))
    if question_id.startswith("context-question."):
        fields.add(question_id.rsplit(".", 1)[-1])
    return {field for field in fields if field}


def _question_answer_shape(question: dict[str, Any]) -> str:
    fields = _fields_for_question(question)
    active_frame_fields = fields & set(ACTIVE_FRAME_ANSWER_SHAPES)
    if active_frame_fields:
        if len(active_frame_fields) == 1:
            return ACTIVE_FRAME_ANSWER_SHAPES[next(iter(active_frame_fields))]
        return "active_frame_patch"
    if fields:
        return "event_storming_entry[]"
    return "text | structured_context"


def _matching_findings_for_question(
    question: dict[str, Any],
    findings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    fields = {_field_from_block(block) for block in _text_list(question.get("blocks"))}
    matched: list[dict[str, Any]] = []
    for finding in findings:
        finding_id = _text(finding.get("finding_id"))
        evidence = _dict(finding.get("evidence"))
        missing_fields = set(_text_list(evidence.get("missing")))
        if _text(evidence.get("field")) in fields or _text(evidence.get("category")) in fields:
            matched.append(finding)
            continue
        if fields & missing_fields:
            matched.append(finding)
            continue
        if any(field and field in finding_id for field in fields):
            matched.append(finding)
    return matched


def _source_output_target_artifact(session: dict[str, Any], fallback: str) -> str:
    source_output = _dict(session.get("source_output"))
    return _text(source_output.get("path"), fallback)


def _question_blocks(question: dict[str, Any]) -> list[str]:
    blocks = _text_list(question.get("blocks"))
    if blocks:
        return blocks
    question_id = _text(question.get("id"))
    if question_id.startswith("context-question."):
        field = question_id.rsplit(".", 1)[-1]
        kind = _text(question.get("kind"))
        prefix = "active_frame" if kind == "active_frame" else "event_storming"
        return [f"{prefix}.{field}"]
    return [question_id] if question_id else []


def _requests_from_session(
    session: dict[str, Any],
    *,
    target_artifact: str,
) -> list[dict[str, Any]]:
    questions = [_dict(item) for item in _list(session.get("clarification_questions"))]
    findings = [_dict(item) for item in _list(session.get("findings"))]
    requests: list[dict[str, Any]] = []
    source_target_artifact = _source_output_target_artifact(session, target_artifact)
    for question in questions:
        question_id = _text(question.get("id"), "question")
        matching_findings = _matching_findings_for_question(question, findings)
        blocks = _question_blocks(question)
        requests.append(
            _request(
                request_id=f"clarification.intake.{_slug(question_id)}",
                kind="missing_context"
                if _text(question.get("kind")) == "active_frame"
                else "missing_event_storming_context",
                severity="blocking",
                question=_text(question.get("question"), "Clarify the missing idea context."),
                target_artifact=source_target_artifact,
                target_ref=blocks[0] if blocks else question_id,
                blocks=blocks or ["user_idea_intake_source"],
                suggested_answer_shape=_question_answer_shape(question),
                suggested_actions=["answer_question", "defer_candidate"],
                source_findings=[
                    _source_finding(finding, source_artifact="user_idea_intake_session")
                    for finding in matching_findings
                ],
            )
        )
    return requests


def _requests_from_intake(intake: dict[str, Any], *, target_artifact: str) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = []
    findings = [_dict(item) for item in _list(intake.get("findings"))]
    for raw_question in _list(intake.get("context_completion_questions")):
        question = _dict(raw_question)
        question_id = _text(question.get("id"), "context-question")
        question_kind = _text(question.get("kind"))
        if question_kind == "active_frame":
            kind = "missing_context"
        else:
            kind = "missing_event_storming_context"
        blocks = _question_blocks(question)
        matching_findings = _matching_findings_for_question(question, findings)
        requests.append(
            _request(
                request_id=f"clarification.event-storming.{_slug(question_id)}",
                kind=kind,
                severity="blocking",
                question=_text(question.get("question"), "Complete event-storming context."),
                target_artifact=target_artifact,
                target_ref=question_id,
                blocks=blocks or [question_id],
                suggested_answer_shape=_question_answer_shape(question),
                suggested_actions=["answer_question", "defer_candidate"],
                source_findings=[
                    _source_finding(finding, source_artifact="idea_event_storming_intake")
                    for finding in matching_findings
                ],
            )
        )
    if requests:
        return requests
    for finding in findings:
        finding_id = _text(finding.get("finding_id"), "event_storming_finding")
        requests.append(
            _request(
                request_id=f"clarification.event-storming.{_slug(finding_id)}",
                kind="missing_event_storming_context",
                severity="blocking",
                question=_text(
                    finding.get("message"),
                    "Resolve event-storming intake before candidate graph generation.",
                ),
                target_artifact=target_artifact,
                target_ref=finding_id,
                blocks=[finding_id],
                suggested_answer_shape="event_storming_entry[] | active_frame_ref[]",
                suggested_actions=["answer_question", "defer_candidate"],
                source_findings=[
                    _source_finding(finding, source_artifact="idea_event_storming_intake")
                ],
            )
        )
    return requests


def _repair_coverage(repair_loop: dict[str, Any] | None) -> dict[str, set[str]]:
    coverage: dict[str, set[str]] = {}
    if repair_loop is None:
        return coverage
    for raw_action in _list(repair_loop.get("repair_actions")):
        action = _dict(raw_action)
        status = _text(action.get("status"), "unknown")
        for finding_id in _text_list(action.get("source_findings")):
            coverage.setdefault(finding_id, set()).add(status)
    return coverage


def _covered_pre_sib_state(
    finding_id: str,
    coverage: dict[str, set[str]],
    default_severity: str,
) -> tuple[str, str]:
    statuses = coverage.get(finding_id, set())
    if "applied_to_preview" in statuses:
        return "advisory", "covered_by_repair_preview"
    if "requires_context" in statuses:
        return "review_required", "covered_by_repair_context"
    return default_severity, "open"


def _requests_from_pre_sib(
    pre_sib: dict[str, Any],
    repair_coverage: dict[str, set[str]] | None = None,
    *,
    target_artifact: str,
) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = []
    coverage = repair_coverage or {}
    entries = [
        (_dict(item), "blocking")
        for item in _list(pre_sib.get("findings"))
        if isinstance(item, dict)
    ] + [
        (_dict(item), "review_required")
        for item in _list(pre_sib.get("warnings"))
        if isinstance(item, dict)
    ]
    for finding, severity in entries:
        finding_id = _text(finding.get("finding_id"), "pre_sib_finding")
        request_severity, request_status = _covered_pre_sib_state(
            finding_id,
            coverage,
            severity,
        )
        kind_info = PRE_SIB_FINDING_KINDS.get(
            finding_id,
            {
                "kind": "repair_action",
                "answer_shape": "accept_risk | provide_context | reject_candidate",
            },
        )
        requests.append(
            _request(
                request_id=f"clarification.pre-sib.{_slug(finding_id)}",
                kind=kind_info["kind"],
                severity=request_severity,
                question=_text(
                    finding.get("message"),
                    "Resolve the pre-SIB finding before promotion.",
                ),
                target_artifact=target_artifact,
                target_ref=finding_id,
                blocks=[finding_id],
                suggested_answer_shape=kind_info["answer_shape"],
                suggested_actions=["inspect_repair_preview", "provide_context", "defer"],
                source_findings=[
                    _source_finding(finding, source_artifact="pre_sib_coherence_report")
                ],
                status=request_status,
            )
        )
    return requests


def _repair_question(action: dict[str, Any], kind: str) -> str:
    target = _text(action.get("target_ref"), "the candidate item")
    rationale = _text(action.get("rationale"))
    if kind == "ontology_gap":
        return f"How should ontology context be resolved for {target}?"
    if kind == "weak_claim":
        return f"Should the low-reliability claim {target} be downgraded, evidenced, or rejected?"
    if kind == "missing_acceptance_criteria":
        return f"Which acceptance criterion should cover {target}?"
    if kind == "graph_repair":
        return f"Should the preview graph repair for {target} be accepted?"
    return rationale or f"Review repair action for {target}."


def _requests_from_repair_loop(
    repair_loop: dict[str, Any],
    *,
    target_artifact: str,
) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = []
    for raw_action in _list(repair_loop.get("repair_actions")):
        action = _dict(raw_action)
        action_id = _text(action.get("id"), "repair_action")
        action_kind = _text(action.get("kind"), "repair_action")
        kind_info = REPAIR_ACTION_KINDS.get(
            action_kind,
            {
                "kind": "repair_action",
                "answer_shape": "accept_preview | provide_context | reject",
                "actions": ["accept_preview", "provide_context", "reject"],
            },
        )
        status = _text(action.get("status"))
        severity = "blocking" if status == "requires_context" else "advisory"
        request_status = "open" if status == "requires_context" else "preview_applied"
        requests.append(
            _request(
                request_id=f"clarification.repair.{_slug(action_id)}",
                kind=kind_info["kind"],
                severity=severity,
                question=_repair_question(action, kind_info["kind"]),
                target_artifact=target_artifact,
                target_ref=_text(action.get("target_ref"), action_id),
                blocks=_text_list(action.get("source_findings")) or [action_id],
                suggested_answer_shape=kind_info["answer_shape"],
                suggested_actions=kind_info["actions"],
                source_findings=_finding_refs(
                    _text_list(action.get("source_findings")),
                    source_artifact="candidate_repair_loop_report",
                ),
                status=request_status,
            )
        )
    return requests


def _requests_from_candidate_graph(
    candidate_graph: dict[str, Any],
    *,
    target_artifact: str,
) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = []
    for raw_node in _list(candidate_graph.get("nodes")):
        node = _dict(raw_node)
        node_id = _text(node.get("id"), "candidate_node")
        for raw_gap in _list(node.get("gaps")):
            gap = _dict(raw_gap)
            gap_id = _text(gap.get("id"), f"gap.{node_id}")
            target_ref = f"{node_id}.gaps.{gap_id}"
            gap_kind = _text(gap.get("kind"))
            is_ontology_gap = gap_kind == "ontology_gap"
            requests.append(
                _request(
                    request_id=f"clarification.candidate-gap.{_slug(target_ref)}",
                    kind="ontology_gap" if is_ontology_gap else "candidate_gap",
                    severity="review_required",
                    question=_text(
                        gap.get("statement"),
                        f"Resolve candidate gap {gap_id}.",
                    ),
                    target_artifact=target_artifact,
                    target_ref=target_ref,
                    blocks=[target_ref],
                    suggested_answer_shape=(
                        ONTOLOGY_GAP_ANSWER_SHAPE if is_ontology_gap else CANDIDATE_GAP_ANSWER_SHAPE
                    ),
                    suggested_actions=(
                        ONTOLOGY_GAP_ACTIONS if is_ontology_gap else CANDIDATE_GAP_ACTIONS
                    ),
                    source_findings=[
                        {
                            "source_artifact": "candidate_spec_graph",
                            "finding_id": target_ref,
                            "severity": "review_required",
                            "evidence": {
                                "node_id": node_id,
                                "gap_id": gap_id,
                                "gap_kind": gap_kind,
                            },
                        }
                    ],
                )
            )
    return requests


def _non_negative_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _candidate_structure_depth(idea_maturity_report: dict[str, Any] | None) -> dict[str, Any]:
    if idea_maturity_report is None:
        return {}
    groups = _dict(idea_maturity_report.get("groups"))
    depth = _dict(groups.get("candidate_structure_depth"))
    if not depth:
        metrics = _dict(idea_maturity_report.get("metrics"))
        depth = _dict(metrics.get("candidate_structure_depth"))
    return depth


def _has_loaded_maturity_intake_source(idea_maturity_report: dict[str, Any]) -> bool:
    source_refs = _list(idea_maturity_report.get("source_artifacts"))
    if any(
        isinstance(source_ref, str) and source_ref.endswith("idea_event_storming_intake.json")
        for source_ref in source_refs
    ):
        return True
    source_details = _dict(idea_maturity_report.get("source_artifact_details"))
    intake_source = _dict(
        source_details.get("intake") or source_details.get("event_storming_intake")
    )
    return intake_source.get("status") == "loaded"


def _depth_source_findings(
    *,
    metric: str,
    idea_maturity_target: str,
) -> list[dict[str, Any]]:
    return [
        {
            "source_artifact": "idea_maturity_metrics_report",
            "finding_id": f"candidate_structure_depth.{metric}",
            "severity": "review_required",
            "message": "Candidate structure depth is shallow for this observation.",
            "evidence": {
                "proposal_id": DEPTH_DRIVEN_PROPOSAL_ID,
                "source_ref": f"{idea_maturity_target}#groups.candidate_structure_depth.{metric}",
            },
        }
    ]


def _requests_from_structure_depth(
    idea_maturity_report: dict[str, Any] | None,
    *,
    idea_maturity_target: str,
    intake_target: str,
) -> list[dict[str, Any]]:
    if idea_maturity_report is None:
        return []
    if (
        idea_maturity_report.get("artifact_kind") != IDEA_MATURITY_KIND
        or idea_maturity_report.get("contract_ref") != IDEA_MATURITY_CONTRACT_REF
    ):
        return []
    if idea_maturity_report.get("status") == "invalid":
        return []
    has_intake = _has_loaded_maturity_intake_source(idea_maturity_report)
    depth = _candidate_structure_depth(idea_maturity_report)
    if not depth:
        return []

    requests: list[dict[str, Any]] = []
    if has_intake:
        for category, spec in EVENT_STORMING_DEPTH_CATEGORIES.items():
            metric = spec["metric"]
            count = _non_negative_int(depth.get(metric))
            if count != 0:
                continue
            target_ref = f"event_storming_hints.{category}"
            requests.append(
                _request(
                    request_id=f"clarification.depth.{category}",
                    kind="event_storming_gap",
                    severity="review_required",
                    question=spec["question"],
                    target_artifact=intake_target,
                    target_ref=target_ref,
                    blocks=[spec["block"]],
                    suggested_answer_shape="event_storming_entry[]",
                    suggested_actions=["answer_question", "defer_candidate"],
                    source_findings=_depth_source_findings(
                        metric=metric,
                        idea_maturity_target=idea_maturity_target,
                    ),
                )
            )
    return requests


def _gap_label(group: dict[str, Any]) -> str:
    return (
        _text(group.get("proposed_term"))
        or _text(group.get("proposed_relation"))
        or _text(group.get("missing_ref"))
        or _text(group.get("gap_key"), "ontology gap")
    )


def _requests_from_ontology_gap_review(
    gap_review: dict[str, Any],
    *,
    target_artifact: str,
) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = []
    for raw_group in _list(gap_review.get("gap_groups")):
        group = _dict(raw_group)
        group_id = _text(group.get("group_id"), "ontology-gap")
        label = _gap_label(group)
        source_findings = [
            {
                "source_artifact": _text(item.get("source_artifact"), "ontology_gap_review"),
                "finding_id": item.get("finding_id") or item.get("gap_ref"),
                "severity": item.get("severity") or "review_required",
                "classification": item.get("classification"),
            }
            for item in _list(group.get("source_findings"))
            if isinstance(item, dict)
        ]
        requests.append(
            _request(
                request_id=f"clarification.ontology-gap.{_slug(group_id)}",
                kind="ontology_gap",
                severity="review_required",
                question=(
                    f"Review ontology gap '{label}': bind it, alias it, propose a "
                    "project-local term, reject it, or defer it."
                ),
                target_artifact=target_artifact,
                target_ref=group_id,
                blocks=[group_id],
                suggested_answer_shape=ONTOLOGY_GAP_ANSWER_SHAPE,
                suggested_actions=ONTOLOGY_GAP_ACTIONS,
                source_findings=source_findings,
            )
        )
    return requests


def _authority_boundary() -> dict[str, bool]:
    return {
        "may_execute_prompt_agent": False,
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
    user_idea_intake_session: dict[str, Any] | None,
    idea_event_storming_intake: dict[str, Any] | None,
    candidate_graph: dict[str, Any] | None,
    pre_sib_report: dict[str, Any] | None,
    repair_loop: dict[str, Any] | None,
    ontology_gap_review: dict[str, Any] | None,
    idea_maturity_report: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    checks = (
        (
            "user_idea_intake_session",
            user_idea_intake_session,
            "user_idea_intake_session",
            USER_IDEA_INTAKE_SESSION_CONTRACT_REF,
        ),
        (
            "idea_event_storming_intake",
            idea_event_storming_intake,
            "idea_event_storming_intake",
            EVENT_STORMING_INTAKE_CONTRACT_REF,
        ),
        ("candidate_graph", candidate_graph, "candidate_spec_graph", CANDIDATE_GRAPH_CONTRACT_REF),
        ("pre_sib_report", pre_sib_report, "pre_sib_coherence_report", PRE_SIB_CONTRACT_REF),
        ("repair_loop", repair_loop, "candidate_repair_loop_report", REPAIR_LOOP_CONTRACT_REF),
    )
    findings: list[dict[str, Any]] = []
    if (
        not any(artifact for _, artifact, _, _ in checks)
        and ontology_gap_review is None
        and idea_maturity_report is None
    ):
        findings.append(
            _finding(
                finding_id="clarification_sources_missing",
                severity="review_required",
                message="Clarification request builder requires at least one source artifact.",
            )
        )
    for name, artifact, expected_kind, expected_contract in checks:
        if artifact is None:
            continue
        invalid: list[str] = []
        if artifact.get("artifact_kind") != expected_kind:
            invalid.append("artifact_kind")
        if artifact.get("contract_ref") != expected_contract:
            invalid.append("contract_ref")
        if invalid:
            findings.append(
                _finding(
                    finding_id=f"{name}_contract_invalid",
                    severity="review_required",
                    message=f"{name} must use a supported clarification source contract.",
                    evidence={
                        "invalid_fields": invalid,
                        "expected_artifact_kind": expected_kind,
                        "expected_contract_ref": expected_contract,
                        "actual_artifact_kind": artifact.get("artifact_kind"),
                        "actual_contract_ref": artifact.get("contract_ref"),
                    },
                )
            )
    if ontology_gap_review is not None and ontology_gap_review.get("artifact_kind") != (
        ONTOLOGY_GAP_REVIEW_KIND
    ):
        findings.append(
            _finding(
                finding_id="ontology_gap_review_contract_invalid",
                severity="review_required",
                message="ontology_gap_review must be an ontology_gap_review_workflow artifact.",
                evidence={"artifact_kind": ontology_gap_review.get("artifact_kind")},
            )
        )
    if idea_maturity_report is not None:
        invalid: list[str] = []
        if idea_maturity_report.get("artifact_kind") != IDEA_MATURITY_KIND:
            invalid.append("artifact_kind")
        if idea_maturity_report.get("contract_ref") != IDEA_MATURITY_CONTRACT_REF:
            invalid.append("contract_ref")
        if invalid:
            findings.append(
                _finding(
                    finding_id="idea_maturity_contract_invalid",
                    severity="review_required",
                    message="idea_maturity_report must use a supported maturity metrics contract.",
                    evidence={
                        "invalid_fields": invalid,
                        "expected_artifact_kind": IDEA_MATURITY_KIND,
                        "expected_contract_ref": IDEA_MATURITY_CONTRACT_REF,
                        "actual_artifact_kind": idea_maturity_report.get("artifact_kind"),
                        "actual_contract_ref": idea_maturity_report.get("contract_ref"),
                    },
                )
            )
    return findings


def build_idea_to_spec_clarification_requests(
    *,
    user_idea_intake_session: dict[str, Any] | None = None,
    idea_event_storming_intake: dict[str, Any] | None = None,
    candidate_graph: dict[str, Any] | None = None,
    pre_sib_report: dict[str, Any] | None = None,
    repair_loop: dict[str, Any] | None = None,
    ontology_gap_review: dict[str, Any] | None = None,
    idea_maturity_report: dict[str, Any] | None = None,
    source_artifacts: list[dict[str, Any]] | None = None,
    user_idea_intake_source_target: str = "runs/user_idea_intake_source.json",
    idea_event_storming_intake_target: str = "runs/idea_event_storming_intake.json",
    candidate_graph_target: str = "runs/candidate_spec_graph.json",
    pre_sib_report_target: str = "runs/pre_sib_coherence_report.json",
    repair_loop_target: str = "runs/candidate_repair_loop_report.json",
    ontology_gap_review_target: str = "runs/ontology_gap_review_workflow.json",
    idea_maturity_target: str = "runs/idea_maturity_metrics_report.json",
) -> dict[str, Any]:
    findings = _validate_inputs(
        user_idea_intake_session=user_idea_intake_session,
        idea_event_storming_intake=idea_event_storming_intake,
        candidate_graph=candidate_graph,
        pre_sib_report=pre_sib_report,
        repair_loop=repair_loop,
        ontology_gap_review=ontology_gap_review,
        idea_maturity_report=idea_maturity_report,
    )
    requests: list[dict[str, Any]] = []
    used_ids: set[str] = set()
    if user_idea_intake_session:
        for request in _requests_from_session(
            user_idea_intake_session,
            target_artifact=user_idea_intake_source_target,
        ):
            _append_request(requests, request, used_ids)
    if idea_event_storming_intake:
        for request in _requests_from_intake(
            idea_event_storming_intake,
            target_artifact=idea_event_storming_intake_target,
        ):
            _append_request(requests, request, used_ids)
    coverage = _repair_coverage(repair_loop)
    if candidate_graph:
        for request in _requests_from_candidate_graph(
            candidate_graph,
            target_artifact=candidate_graph_target,
        ):
            _append_request(requests, request, used_ids)
    if pre_sib_report:
        for request in _requests_from_pre_sib(
            pre_sib_report,
            repair_coverage=coverage,
            target_artifact=pre_sib_report_target,
        ):
            _append_request(requests, request, used_ids)
    if repair_loop:
        for request in _requests_from_repair_loop(
            repair_loop,
            target_artifact=repair_loop_target,
        ):
            _append_request(requests, request, used_ids)
    if ontology_gap_review:
        for request in _requests_from_ontology_gap_review(
            ontology_gap_review,
            target_artifact=ontology_gap_review_target,
        ):
            _append_request(requests, request, used_ids)
    if idea_maturity_report:
        for request in _requests_from_structure_depth(
            idea_maturity_report,
            idea_maturity_target=idea_maturity_target,
            intake_target=idea_event_storming_intake_target,
        ):
            _append_request(requests, request, used_ids)

    severity_counts: dict[str, int] = {}
    kind_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    for request in requests:
        severity = _text(request.get("severity"), "unknown")
        kind = _text(request.get("kind"), "unknown")
        status = _text(request.get("status"), "unknown")
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
        kind_counts[kind] = kind_counts.get(kind, 0) + 1
        status_counts[status] = status_counts.get(status, 0) + 1

    open_requests = [request for request in requests if request.get("status") == "open"]
    blocking_requests = [
        request for request in open_requests if request.get("severity") == "blocking"
    ]
    review_required_requests = [
        request for request in open_requests if request.get("severity") == "review_required"
    ]
    blocking_count = len(blocking_requests)
    review_required_count = len(review_required_requests)
    ready = not findings and blocking_count == 0 and review_required_count == 0
    review_state = "clarification_clear"
    if not ready:
        review_state = (
            "clarification_required"
            if blocking_count or findings
            else "clarification_review_required"
        )
    return {
        "artifact_kind": "idea_to_spec_clarification_requests",
        "schema_version": SCHEMA_VERSION,
        "proposal_id": PROPOSAL_ID,
        "contract_ref": CONTRACT_REF,
        "generated_at": _now_iso(),
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "source_artifacts": source_artifacts or [],
        "request_counts": {
            "total": len(requests),
            "by_severity": severity_counts,
            "by_kind": kind_counts,
            "by_status": status_counts,
        },
        "clarification_requests": requests,
        "readiness": {
            "ready": ready,
            "review_state": review_state,
            "blocked_by": [request["id"] for request in blocking_requests]
            + [finding["finding_id"] for finding in findings],
            "review_required_by": [request["id"] for request in review_required_requests],
            "next_artifact": "runs/idea_to_spec_clarification_answers.json",
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
            "status": review_state,
            "request_count": len(requests),
            "blocking_request_count": blocking_count,
            "review_required_request_count": review_required_count,
            "finding_count": len(findings),
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session", default=DEFAULT_SESSION_PATH, type=Path)
    parser.add_argument("--no-session", action="store_true")
    parser.add_argument("--intake", default=DEFAULT_INTAKE_PATH, type=Path)
    parser.add_argument("--no-intake", action="store_true")
    parser.add_argument("--candidate-graph", default=DEFAULT_CANDIDATE_GRAPH_PATH, type=Path)
    parser.add_argument("--no-candidate-graph", action="store_true")
    parser.add_argument("--pre-sib", default=DEFAULT_PRE_SIB_PATH, type=Path)
    parser.add_argument("--no-pre-sib", action="store_true")
    parser.add_argument("--repair-loop", default=DEFAULT_REPAIR_LOOP_PATH, type=Path)
    parser.add_argument("--no-repair-loop", action="store_true")
    parser.add_argument("--ontology-gap-review", default=None, type=Path)
    parser.add_argument("--idea-maturity", default=None, type=Path)
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, type=Path)
    parser.add_argument("--strict", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    input_specs = (
        ("user_idea_intake_session", None if args.no_session else args.session),
        ("idea_event_storming_intake", None if args.no_intake else args.intake),
        ("candidate_graph", None if args.no_candidate_graph else args.candidate_graph),
        ("pre_sib_report", None if args.no_pre_sib else args.pre_sib),
        ("repair_loop", None if args.no_repair_loop else args.repair_loop),
        ("ontology_gap_review", args.ontology_gap_review),
        ("idea_maturity_report", args.idea_maturity),
    )
    loaded: dict[str, dict[str, Any] | None] = {}
    source_artifacts: list[dict[str, Any]] = []
    for name, path in input_specs:
        artifact, status = _load_optional(path)
        loaded[name] = artifact
        source_artifacts.append(
            _source_artifact(name=name, path=path, status=status, artifact=artifact)
        )
    report = build_idea_to_spec_clarification_requests(
        user_idea_intake_session=loaded["user_idea_intake_session"],
        idea_event_storming_intake=loaded["idea_event_storming_intake"],
        candidate_graph=loaded["candidate_graph"],
        pre_sib_report=loaded["pre_sib_report"],
        repair_loop=loaded["repair_loop"],
        ontology_gap_review=loaded["ontology_gap_review"],
        idea_maturity_report=loaded["idea_maturity_report"],
        source_artifacts=source_artifacts,
        user_idea_intake_source_target=_source_output_target_artifact(
            loaded["user_idea_intake_session"] or {},
            "runs/user_idea_intake_source.json",
        ),
        idea_event_storming_intake_target=_relative_ref(args.intake),
        candidate_graph_target=_relative_ref(args.candidate_graph),
        pre_sib_report_target=_relative_ref(args.pre_sib),
        repair_loop_target=_relative_ref(args.repair_loop),
        ontology_gap_review_target=(
            _relative_ref(args.ontology_gap_review)
            if args.ontology_gap_review
            else "runs/ontology_gap_review_workflow.json"
        ),
        idea_maturity_target=(
            _relative_ref(args.idea_maturity)
            if args.idea_maturity
            else "runs/idea_maturity_metrics_report.json"
        ),
    )
    write_json(report, args.output)
    summary = _dict(report.get("summary"))
    print(
        f"{summary.get('status', 'unknown')}: "
        f"{summary.get('request_count', 0)} requests, "
        f"{summary.get('blocking_request_count', 0)} blocking -> "
        f"{_relative_ref(args.output)}"
    )
    if args.strict and not _dict(report.get("readiness")).get("ready"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
