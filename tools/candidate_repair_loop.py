"""Build a review-only autonomous repair preview for candidate spec graphs."""

from __future__ import annotations

import argparse
import copy
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_ID = "0152"
SCHEMA_VERSION = 1
CONTRACT_REF = "specgraph.idea-to-spec.candidate-repair-loop.v0.1"
CANDIDATE_GRAPH_CONTRACT_REF = "specgraph.idea-to-spec.candidate-spec-graph.v0.1"
PRE_SIB_CONTRACT_REF = "specgraph.idea-to-spec.pre-sib-coherence-report.v0.1"
DEFAULT_CANDIDATE_GRAPH_PATH = (
    ROOT / "tests" / "fixtures" / "candidate_repair_loop" / "candidate_graph_repairable.json"
)
DEFAULT_PRE_SIB_REPORT_PATH = (
    ROOT / "tests" / "fixtures" / "candidate_repair_loop" / "pre_sib_repair_required.json"
)
DEFAULT_OUTPUT_PATH = ROOT / "runs" / "candidate_repair_loop_report.json"

STRONG_CLAIM_TYPES = {
    "architectural_decision",
    "constraint",
    "decision",
    "invariant",
    "product_claim",
    "runtime_behavior",
    "security_claim",
    "security_constraint",
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


def _slug(value: str, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or fallback


def _relative_ref(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


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
        "source": "candidate_repair_loop",
        "evidence": evidence or {},
    }


def _authority_boundary() -> dict[str, bool]:
    return {
        "may_execute_prompt_agent": False,
        "may_mutate_canonical_specs": False,
        "may_write_ontology_package": False,
        "may_write_ontology_lockfile": False,
        "may_mark_candidate_graph_accepted": False,
        "may_create_branch_or_commit": False,
    }


def _validate_inputs(
    candidate_graph: dict[str, Any],
    pre_sib_report: dict[str, Any],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if candidate_graph.get("artifact_kind") != "candidate_spec_graph":
        findings.append(
            _finding(
                finding_id="candidate_graph_wrong_artifact_kind",
                severity="review_required",
                message="Repair loop requires candidate_spec_graph input.",
                evidence={"artifact_kind": candidate_graph.get("artifact_kind")},
            )
        )
    if candidate_graph.get("contract_ref") != CANDIDATE_GRAPH_CONTRACT_REF:
        findings.append(
            _finding(
                finding_id="candidate_graph_contract_ref_unsupported",
                severity="review_required",
                message=(
                    f"candidate_spec_graph contract_ref must be {CANDIDATE_GRAPH_CONTRACT_REF}."
                ),
                evidence={"contract_ref": candidate_graph.get("contract_ref")},
            )
        )
    if pre_sib_report.get("artifact_kind") != "pre_sib_coherence_report":
        findings.append(
            _finding(
                finding_id="pre_sib_wrong_artifact_kind",
                severity="review_required",
                message="Repair loop requires pre_sib_coherence_report input.",
                evidence={"artifact_kind": pre_sib_report.get("artifact_kind")},
            )
        )
    if pre_sib_report.get("contract_ref") != PRE_SIB_CONTRACT_REF:
        findings.append(
            _finding(
                finding_id="pre_sib_contract_ref_unsupported",
                severity="review_required",
                message=f"pre_sib_coherence_report contract_ref must be {PRE_SIB_CONTRACT_REF}.",
                evidence={"contract_ref": pre_sib_report.get("contract_ref")},
            )
        )
    candidate_source_ref = _text(candidate_graph.get("source_ref"))
    report_candidate = _dict(pre_sib_report.get("source_candidate_graph"))
    report_candidate_source_ref = _text(report_candidate.get("source_ref"))
    if (
        candidate_source_ref
        and report_candidate_source_ref
        and candidate_source_ref != report_candidate_source_ref
    ):
        findings.append(
            _finding(
                finding_id="pre_sib_candidate_graph_mismatch",
                severity="review_required",
                message="pre-SIB report source_candidate_graph must match candidate graph input.",
                evidence={
                    "candidate_graph_source_ref": candidate_source_ref,
                    "pre_sib_source_candidate_graph_ref": report_candidate_source_ref,
                },
            )
        )
    for artifact_name, artifact in (
        ("candidate_graph", candidate_graph),
        ("pre_sib_report", pre_sib_report),
    ):
        for field in ("canonical_mutations_allowed", "tracked_artifacts_written"):
            if artifact.get(field) is not False:
                findings.append(
                    _finding(
                        finding_id="input_authority_expansion",
                        severity="review_required",
                        message=f"{artifact_name} {field} must be false.",
                        evidence={"artifact": artifact_name, field: artifact.get(field)},
                    )
                )
    return findings


def _nodes(candidate_graph: dict[str, Any]) -> list[dict[str, Any]]:
    return [node for node in _list(candidate_graph.get("nodes")) if isinstance(node, dict)]


def _edges(candidate_graph: dict[str, Any]) -> list[dict[str, Any]]:
    return [edge for edge in _list(candidate_graph.get("edges")) if isinstance(edge, dict)]


def _edge_degrees(candidate_graph: dict[str, Any]) -> dict[str, int]:
    degrees = {
        _text(node.get("id")): 0 for node in _nodes(candidate_graph) if _text(node.get("id"))
    }
    for edge in _edges(candidate_graph):
        for field in ("from", "to"):
            ref = _text(edge.get(field))
            if ref in degrees:
                degrees[ref] += 1
    return degrees


def _metric_counts(candidate_graph: dict[str, Any]) -> dict[str, Any]:
    nodes = _nodes(candidate_graph)
    edges = _edges(candidate_graph)
    requirements = [req for node in nodes for req in _list(node.get("requirements"))]
    acceptance_criteria = [ac for node in nodes for ac in _list(node.get("acceptance_criteria"))]
    claims = [
        claim for node in nodes for claim in _list(node.get("claims")) if isinstance(claim, dict)
    ]
    gaps = [gap for node in nodes for gap in _list(node.get("gaps"))]
    degrees = _edge_degrees(candidate_graph)
    node_count = len(nodes)
    connected_count = sum(1 for degree in degrees.values() if degree > 0)
    ontology_covered = sum(1 for node in nodes if _text_list(node.get("ontology_refs")))
    unsupported_strong_claims = sum(
        1
        for claim in claims
        if _is_strong_claim(claim)
        and (_claim_reliability(claim) or 0) <= 2
        and not _text_list(claim.get("evidence_refs"))
    )
    return {
        "node_count": node_count,
        "edge_count": len(edges),
        "requirement_count": len(requirements),
        "acceptance_criteria_count": len(acceptance_criteria),
        "claim_count": len(claims),
        "unsupported_strong_claim_count": unsupported_strong_claims,
        "gap_count": len(gaps),
        "orphan_node_count": sum(1 for degree in degrees.values() if degree == 0),
        "ontology_coverage_ratio": round(ontology_covered / node_count, 4) if node_count else 0.0,
        "connected_node_ratio": round(connected_count / node_count, 4) if node_count else 0.0,
    }


def _graph_finding_ids(pre_sib_report: dict[str, Any]) -> set[str]:
    findings = _list(pre_sib_report.get("findings")) + _list(pre_sib_report.get("warnings"))
    return {
        finding["finding_id"]
        for finding in findings
        if isinstance(finding, dict) and isinstance(finding.get("finding_id"), str)
    }


def _claim_reliability(claim: dict[str, Any]) -> int | None:
    value = _text(_dict(claim.get("calibration")).get("R"))
    if len(value) >= 2 and value[0] == "R" and value[1:].isdigit():
        return int(value[1:])
    return None


def _is_strong_claim(claim: dict[str, Any]) -> bool:
    claim_type = _text(claim.get("type"), "claim")
    return claim_type in STRONG_CLAIM_TYPES or _text(claim.get("strength")) == "strong"


def _action(
    *,
    action_id: str,
    kind: str,
    status: str,
    target_ref: str,
    source_findings: list[str],
    rationale: str,
    operation: dict[str, Any] | None = None,
) -> dict[str, Any]:
    action: dict[str, Any] = {
        "id": action_id,
        "kind": kind,
        "status": status,
        "target_ref": target_ref,
        "source_findings": source_findings,
        "rationale": rationale,
    }
    if operation:
        action["operation"] = operation
    return action


def _root_node_id(candidate_graph: dict[str, Any]) -> str:
    nodes = _nodes(candidate_graph)
    if not nodes:
        return ""
    for node in nodes:
        if _text(node.get("kind")) in {"product_boundary", "root", "product"}:
            return _text(node.get("id"))
    return _text(nodes[0].get("id"))


def _repair_orphans(candidate_graph: dict[str, Any]) -> list[dict[str, Any]]:
    degrees = _edge_degrees(candidate_graph)
    root_id = _root_node_id(candidate_graph)
    if not root_id:
        return []
    actions: list[dict[str, Any]] = []
    for node_id, degree in degrees.items():
        if degree > 0 or node_id == root_id:
            continue
        edge_id = f"edge.repair.{_slug(root_id, 'root')}.{_slug(node_id, 'node')}"
        actions.append(
            _action(
                action_id=f"repair.connect-orphan.{_slug(node_id, 'node')}",
                kind="add_candidate_edge",
                status="applied_to_preview",
                target_ref=node_id,
                source_findings=["pre_sib_orphan_nodes"],
                rationale="Connect orphan candidate nodes to the root product boundary for review.",
                operation={
                    "op": "append",
                    "path": "/edges",
                    "value": {
                        "id": edge_id,
                        "from": root_id,
                        "to": node_id,
                        "relation": "decomposes_to",
                        "repair_generated": True,
                    },
                },
            )
        )
    return actions


def _repair_acceptance_criteria(candidate_graph: dict[str, Any]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for node in _nodes(candidate_graph):
        node_id = _text(node.get("id"))
        existing_ac = {
            _text(ac.get("id"))
            for ac in _list(node.get("acceptance_criteria"))
            if isinstance(ac, dict)
        }
        for requirement in _list(node.get("requirements")):
            if not isinstance(requirement, dict):
                continue
            refs = _text_list(requirement.get("acceptance_criteria_refs"))
            if refs and all(ref in existing_ac for ref in refs):
                continue
            req_id = _text(requirement.get("id"), "requirement")
            ac_id = f"ac.repair.{_slug(req_id, 'requirement')}"
            actions.append(
                _action(
                    action_id=f"repair.add-ac.{_slug(req_id, 'requirement')}",
                    kind="add_acceptance_criterion",
                    status="applied_to_preview",
                    target_ref=req_id,
                    source_findings=["pre_sib_acceptance_criteria_gap"],
                    rationale=(
                        "Add a reviewable placeholder acceptance criterion for "
                        "uncovered requirement."
                    ),
                    operation={
                        "op": "add_acceptance_criterion",
                        "node_id": node_id,
                        "requirement_id": req_id,
                        "value": {
                            "id": ac_id,
                            "statement": (
                                "Review criterion needed for requirement: "
                                f"{_text(requirement.get('statement'), req_id)}"
                            ),
                            "repair_generated": True,
                        },
                    },
                )
            )
    return actions


def _repair_missing_ontology(candidate_graph: dict[str, Any]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for node in _nodes(candidate_graph):
        if _text_list(node.get("ontology_refs")):
            continue
        node_id = _text(node.get("id"), "node")
        actions.append(
            _action(
                action_id=f"repair.ontology-gap.{_slug(node_id, 'node')}",
                kind="add_ontology_gap",
                status="requires_context",
                target_ref=node_id,
                source_findings=["pre_sib_ontology_coverage_gap"],
                rationale="Ontology refs cannot be invented safely; add an explicit review gap.",
                operation={
                    "op": "append_node_gap",
                    "node_id": node_id,
                    "value": {
                        "id": f"gap.ontology-ref.{_slug(node_id, 'node')}",
                        "kind": "ontology_gap",
                        "statement": "Select or create ontology refs for this candidate node.",
                        "repair_generated": True,
                    },
                },
            )
        )
    return actions


def _repair_unsupported_claims(candidate_graph: dict[str, Any]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for node in _nodes(candidate_graph):
        for claim in _list(node.get("claims")):
            if not isinstance(claim, dict):
                continue
            if not _is_strong_claim(claim):
                continue
            if (_claim_reliability(claim) or 0) > 2 or _text_list(claim.get("evidence_refs")):
                continue
            claim_id = _text(claim.get("id"), "claim")
            actions.append(
                _action(
                    action_id=f"repair.downgrade-claim.{_slug(claim_id, 'claim')}",
                    kind="downgrade_claim",
                    status="applied_to_preview",
                    target_ref=claim_id,
                    source_findings=["pre_sib_unsupported_strong_claims"],
                    rationale="Low-reliability strong claims without evidence stay hypotheses.",
                    operation={
                        "op": "replace_claim_type",
                        "node_id": _text(node.get("id")),
                        "claim_id": claim_id,
                        "value": "hypothesis",
                    },
                )
            )
    return actions


def _build_repair_actions(
    candidate_graph: dict[str, Any], pre_sib_report: dict[str, Any]
) -> list[dict[str, Any]]:
    finding_ids = _graph_finding_ids(pre_sib_report)
    actions: list[dict[str, Any]] = []
    if "pre_sib_orphan_nodes" in finding_ids:
        actions.extend(_repair_orphans(candidate_graph))
    if "pre_sib_acceptance_criteria_gap" in finding_ids:
        actions.extend(_repair_acceptance_criteria(candidate_graph))
    if "pre_sib_ontology_coverage_gap" in finding_ids:
        actions.extend(_repair_missing_ontology(candidate_graph))
    if "pre_sib_unsupported_strong_claims" in finding_ids:
        actions.extend(_repair_unsupported_claims(candidate_graph))
    if "pre_sib_unresolved_gaps" in finding_ids:
        actions.append(
            _action(
                action_id="repair.review-unresolved-gaps",
                kind="request_context_for_gaps",
                status="requires_context",
                target_ref="candidate_graph.gaps",
                source_findings=["pre_sib_unresolved_gaps"],
                rationale=(
                    "Unresolved gaps require owner or operator context before canonical review."
                ),
            )
        )
    return actions


def _node_by_id(candidate_graph: dict[str, Any], node_id: str) -> dict[str, Any] | None:
    for node in _nodes(candidate_graph):
        if _text(node.get("id")) == node_id:
            return node
    return None


def _apply_preview_actions(
    candidate_graph: dict[str, Any],
    actions: list[dict[str, Any]],
    *,
    preview_source_ref: str,
) -> dict[str, Any]:
    preview = copy.deepcopy(candidate_graph)
    preview["source_ref"] = preview_source_ref
    preview["canonical_mutations_allowed"] = False
    preview["tracked_artifacts_written"] = False
    preview["repair_preview"] = {
        "generated_by": CONTRACT_REF,
        "applied_action_count": sum(
            1 for action in actions if action["status"] == "applied_to_preview"
        ),
    }
    for action in actions:
        if action["status"] != "applied_to_preview":
            continue
        operation = _dict(action.get("operation"))
        op = _text(operation.get("op"))
        if op == "append" and operation.get("path") == "/edges":
            preview.setdefault("edges", []).append(operation["value"])
        elif op == "add_acceptance_criterion":
            node = _node_by_id(preview, _text(operation.get("node_id")))
            if node is None:
                continue
            node.setdefault("acceptance_criteria", []).append(operation["value"])
            for requirement in _list(node.get("requirements")):
                if not isinstance(requirement, dict):
                    continue
                if _text(requirement.get("id")) == _text(operation.get("requirement_id")):
                    refs = _text_list(requirement.get("acceptance_criteria_refs"))
                    if operation["value"]["id"] not in refs:
                        refs.append(operation["value"]["id"])
                    requirement["acceptance_criteria_refs"] = refs
        elif op == "replace_claim_type":
            node = _node_by_id(preview, _text(operation.get("node_id")))
            if node is None:
                continue
            for claim in _list(node.get("claims")):
                if isinstance(claim, dict) and _text(claim.get("id")) == _text(
                    operation.get("claim_id")
                ):
                    claim["type"] = operation["value"]
                    if _text(claim.get("strength")) == "strong":
                        claim["strength"] = operation["value"]
                    claim["repair_generated_type_change"] = True
    return preview


def _preview_source_ref(output_path: Path | None) -> str:
    path = output_path or DEFAULT_OUTPUT_PATH
    return f"{_relative_ref(path)}#revised_candidate_graph_preview"


def _unhandled_pre_sib_findings(
    pre_sib_report: dict[str, Any],
    actions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    blocked_by = set(_text_list(_dict(pre_sib_report.get("readiness")).get("blocked_by")))
    if not blocked_by:
        return []
    handled = {
        finding_id for action in actions for finding_id in _text_list(action.get("source_findings"))
    }
    unhandled = blocked_by - handled
    if not unhandled:
        return []
    findings: list[dict[str, Any]] = []
    for finding in _list(pre_sib_report.get("findings")):
        finding_mapping = _dict(finding)
        finding_id = _text(finding_mapping.get("finding_id"))
        if finding_id in unhandled:
            preserved = copy.deepcopy(finding_mapping)
            preserved["source"] = "candidate_repair_loop"
            findings.append(preserved)
    for finding_id in sorted(unhandled - {finding.get("finding_id") for finding in findings}):
        findings.append(
            _finding(
                finding_id=finding_id,
                severity="review_required",
                message="pre-SIB blocking finding was not handled by the repair loop.",
            )
        )
    return findings


def _delta(before: dict[str, Any], after: dict[str, Any]) -> dict[str, Any]:
    before_metrics = _metric_counts(before)
    after_metrics = _metric_counts(after)
    return {
        "before": before_metrics,
        "after": after_metrics,
        "delta": {
            key: after_metrics[key] - before_metrics[key]
            for key in before_metrics
            if isinstance(before_metrics[key], int) and isinstance(after_metrics.get(key), int)
        },
    }


def build_candidate_repair_loop_report(
    *,
    candidate_graph: dict[str, Any],
    pre_sib_report: dict[str, Any],
    candidate_graph_path: Path | None = None,
    pre_sib_report_path: Path | None = None,
    output_path: Path | None = None,
) -> dict[str, Any]:
    input_findings = _validate_inputs(candidate_graph, pre_sib_report)
    actions = [] if input_findings else _build_repair_actions(candidate_graph, pre_sib_report)
    pre_sib_findings = (
        [] if input_findings else _unhandled_pre_sib_findings(pre_sib_report, actions)
    )
    preview = _apply_preview_actions(
        candidate_graph,
        actions,
        preview_source_ref=_preview_source_ref(output_path),
    )
    applied_count = sum(1 for action in actions if action["status"] == "applied_to_preview")
    context_required_count = sum(1 for action in actions if action["status"] == "requires_context")
    pre_sib_ready = _dict(pre_sib_report.get("readiness")).get("ready") is True
    no_op_ready = pre_sib_ready and not actions
    source_ref = _text(candidate_graph.get("source_ref"))
    if not source_ref and candidate_graph_path is not None:
        source_ref = _relative_ref(candidate_graph_path)
    pre_sib_ref = _text(pre_sib_report.get("source_ref"))
    if not pre_sib_ref and pre_sib_report_path is not None:
        pre_sib_ref = _relative_ref(pre_sib_report_path)
    findings = input_findings + pre_sib_findings
    ready = not findings and (applied_count > 0 or no_op_ready)
    status = "repair_preview_ready" if ready else "repair_review_required"
    if no_op_ready:
        preview["repair_preview"]["no_op_repair_loop"] = True
    return {
        "artifact_kind": "candidate_repair_loop_report",
        "schema_version": SCHEMA_VERSION,
        "proposal_id": PROPOSAL_ID,
        "contract_ref": CONTRACT_REF,
        "source_ref": source_ref or "operator://candidate-repair-loop-local",
        "generated_at": _now_iso(),
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "source_candidate_graph": {
            "artifact_kind": candidate_graph.get("artifact_kind"),
            "contract_ref": candidate_graph.get("contract_ref"),
            "source_ref": source_ref or "unknown",
        },
        "source_pre_sib_report": {
            "artifact_kind": pre_sib_report.get("artifact_kind"),
            "contract_ref": pre_sib_report.get("contract_ref"),
            "source_ref": pre_sib_ref or "unknown",
            "review_state": _dict(pre_sib_report.get("readiness")).get("review_state"),
        },
        "loop": {
            "mode": "deterministic_preview",
            "iteration": 1,
            "max_iterations": 1,
            "writes_candidate_graph": False,
        },
        "repair_actions": actions,
        "revised_candidate_graph_preview": preview,
        "metric_delta_projection": _delta(candidate_graph, preview),
        "readiness": {
            "ready": ready,
            "review_state": status,
            "next_artifact": "runs/idea_to_spec_workspace_bundle.json",
            "blocked_by": [finding["finding_id"] for finding in findings],
            "context_required_count": context_required_count,
        },
        "authority_boundary": _authority_boundary(),
        "privacy_boundary": {
            "raw_intent_text_published": False,
            "raw_prompt_published": False,
            "raw_model_output_published": False,
        },
        "findings": findings,
        "warnings": [
            _finding(
                finding_id="repair_context_required",
                severity="warning",
                message="Some repair actions require owner or operator context.",
                evidence={"context_required_count": context_required_count},
            )
        ]
        if context_required_count
        else [],
        "summary": {
            "status": status,
            "action_count": len(actions),
            "applied_action_count": applied_count,
            "context_required_count": context_required_count,
            "finding_count": len(findings),
            "no_op_repair_loop": no_op_ready,
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-graph", default=DEFAULT_CANDIDATE_GRAPH_PATH, type=Path)
    parser.add_argument("--pre-sib-report", default=DEFAULT_PRE_SIB_REPORT_PATH, type=Path)
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, type=Path)
    parser.add_argument("--strict", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    candidate_graph = load_json(args.candidate_graph)
    pre_sib_report = load_json(args.pre_sib_report)
    report = build_candidate_repair_loop_report(
        candidate_graph=candidate_graph,
        pre_sib_report=pre_sib_report,
        candidate_graph_path=args.candidate_graph,
        pre_sib_report_path=args.pre_sib_report,
        output_path=args.output,
    )
    write_json(report, args.output)
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.strict and not report["readiness"]["ready"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
