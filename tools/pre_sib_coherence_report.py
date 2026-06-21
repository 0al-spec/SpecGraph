"""Build a review-only pre-SIB/coherence report for candidate spec graphs."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_ID = "0151"
SCHEMA_VERSION = 1
CONTRACT_REF = "specgraph.idea-to-spec.pre-sib-coherence-report.v0.1"
CANDIDATE_GRAPH_CONTRACT_REF = "specgraph.idea-to-spec.candidate-spec-graph.v0.1"
DEFAULT_CANDIDATE_GRAPH_PATH = (
    ROOT / "tests" / "fixtures" / "pre_sib_coherence" / "candidate_spec_graph_ready.json"
)
DEFAULT_OUTPUT_PATH = ROOT / "runs" / "pre_sib_coherence_report.json"

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
        "source": "pre_sib_coherence_report",
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


def _is_strong_claim(claim: dict[str, Any]) -> bool:
    claim_type = _text(claim.get("type"), "claim")
    return claim_type in STRONG_CLAIM_TYPES or _text(claim.get("strength")) == "strong"


def _reliability_value(claim: dict[str, Any]) -> int | None:
    value = _text(_dict(claim.get("calibration")).get("R"))
    if len(value) >= 2 and value[0] == "R" and value[1:].isdigit():
        return int(value[1:])
    return None


def _validate_candidate_root(candidate_graph: dict[str, Any]) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if candidate_graph.get("artifact_kind") != "candidate_spec_graph":
        findings.append(
            _finding(
                finding_id="candidate_graph_wrong_artifact_kind",
                severity="review_required",
                message="pre-SIB report requires candidate_spec_graph input.",
                evidence={"artifact_kind": candidate_graph.get("artifact_kind")},
            )
        )
    if candidate_graph.get("schema_version") != SCHEMA_VERSION:
        findings.append(
            _finding(
                finding_id="candidate_graph_schema_version_unsupported",
                severity="review_required",
                message="candidate_spec_graph schema_version must be 1.",
                evidence={"schema_version": candidate_graph.get("schema_version")},
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
    if _dict(candidate_graph.get("pre_sib_readiness")).get("ready") is not True:
        findings.append(
            _finding(
                finding_id="candidate_graph_not_ready",
                severity="review_required",
                message="Candidate graph must pass its contract before pre-SIB scoring.",
                evidence={
                    "review_state": _dict(candidate_graph.get("pre_sib_readiness")).get(
                        "review_state"
                    )
                },
            )
        )
    for field in ("canonical_mutations_allowed", "tracked_artifacts_written"):
        if candidate_graph.get(field) is not False:
            findings.append(
                _finding(
                    finding_id="candidate_graph_authority_expansion",
                    severity="review_required",
                    message=f"Candidate graph {field} must be false.",
                    evidence={field: candidate_graph.get(field)},
                )
            )
    return findings


def _edge_degrees(nodes: list[dict[str, Any]], edges: list[dict[str, Any]]) -> dict[str, int]:
    degrees = {node["id"]: 0 for node in nodes if _text(node.get("id"))}
    for edge in edges:
        for field in ("from", "to"):
            ref = _text(edge.get(field))
            if ref in degrees:
                degrees[ref] += 1
    return degrees


def _metric_counts(candidate_graph: dict[str, Any]) -> dict[str, Any]:
    nodes = [_dict(node) for node in _list(candidate_graph.get("nodes")) if isinstance(node, dict)]
    edges = [_dict(edge) for edge in _list(candidate_graph.get("edges")) if isinstance(edge, dict)]
    requirements = [req for node in nodes for req in _list(node.get("requirements"))]
    acceptance_criteria = [ac for node in nodes for ac in _list(node.get("acceptance_criteria"))]
    claims = [
        _dict(claim)
        for node in nodes
        for claim in _list(node.get("claims"))
        if isinstance(claim, dict)
    ]
    gaps = [gap for node in nodes for gap in _list(node.get("gaps"))]
    degrees = _edge_degrees(nodes, edges)
    connected_node_count = sum(1 for degree in degrees.values() if degree > 0)
    node_count = len(nodes)
    ac_coverage_ratio = len(acceptance_criteria) / len(requirements) if requirements else 0.0
    ontology_covered_nodes = sum(1 for node in nodes if _text_list(node.get("ontology_refs")))
    ontology_coverage_ratio = ontology_covered_nodes / node_count if node_count else 0.0
    connected_ratio = connected_node_count / node_count if node_count else 0.0
    title_counts: dict[str, int] = {}
    for node in nodes:
        title = _text(node.get("title")).lower()
        if title:
            title_counts[title] = title_counts.get(title, 0) + 1
    duplicate_titles = [title for title, count in title_counts.items() if count > 1]
    unsupported_claims = [
        claim
        for claim in claims
        if _is_strong_claim(claim)
        and (_reliability_value(claim) or 0) <= 2
        and not _text_list(claim.get("evidence_refs"))
    ]
    return {
        "node_count": node_count,
        "edge_count": len(edges),
        "requirement_count": len(requirements),
        "acceptance_criteria_count": len(acceptance_criteria),
        "claim_count": len(claims),
        "gap_count": len(gaps),
        "orphan_node_count": sum(1 for degree in degrees.values() if degree == 0),
        "ontology_covered_node_count": ontology_covered_nodes,
        "acceptance_criteria_coverage_ratio": round(ac_coverage_ratio, 4),
        "ontology_coverage_ratio": round(ontology_coverage_ratio, 4),
        "connected_node_ratio": round(connected_ratio, 4),
        "duplicate_node_titles": duplicate_titles,
        "unsupported_strong_claim_count": len(unsupported_claims),
    }


def _metric_findings(metrics: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    if metrics["node_count"] == 0:
        findings.append(
            _finding(
                finding_id="pre_sib_nodes_missing",
                severity="review_required",
                message="pre-SIB report requires at least one candidate node.",
            )
        )
    if metrics["orphan_node_count"]:
        findings.append(
            _finding(
                finding_id="pre_sib_orphan_nodes",
                severity="review_required",
                message="Candidate graph contains nodes with no candidate edges.",
                evidence={"orphan_node_count": metrics["orphan_node_count"]},
            )
        )
    if metrics["acceptance_criteria_coverage_ratio"] < 1.0:
        findings.append(
            _finding(
                finding_id="pre_sib_acceptance_criteria_gap",
                severity="review_required",
                message="Every requirement should have acceptance criteria coverage.",
                evidence={
                    "acceptance_criteria_coverage_ratio": metrics[
                        "acceptance_criteria_coverage_ratio"
                    ]
                },
            )
        )
    if metrics["ontology_coverage_ratio"] < 1.0:
        findings.append(
            _finding(
                finding_id="pre_sib_ontology_coverage_gap",
                severity="review_required",
                message="Every candidate node should carry ontology refs.",
                evidence={"ontology_coverage_ratio": metrics["ontology_coverage_ratio"]},
            )
        )
    if metrics["duplicate_node_titles"]:
        warnings.append(
            _finding(
                finding_id="pre_sib_duplicate_node_titles",
                severity="warning",
                message="Candidate graph contains duplicate node titles.",
                evidence={"duplicate_node_titles": metrics["duplicate_node_titles"]},
            )
        )
    if metrics["gap_count"]:
        warnings.append(
            _finding(
                finding_id="pre_sib_unresolved_gaps",
                severity="warning",
                message="Candidate graph still contains unresolved gaps.",
                evidence={"gap_count": metrics["gap_count"]},
            )
        )
    if metrics["unsupported_strong_claim_count"]:
        warnings.append(
            _finding(
                finding_id="pre_sib_unsupported_strong_claims",
                severity="warning",
                message="Some strong claims have low reliability and no evidence refs.",
                evidence={
                    "unsupported_strong_claim_count": metrics["unsupported_strong_claim_count"]
                },
            )
        )
    return findings, warnings


def build_pre_sib_coherence_report(
    candidate_graph: dict[str, Any],
    *,
    candidate_graph_path: Path | None = None,
) -> dict[str, Any]:
    root_findings = _validate_candidate_root(candidate_graph)
    metrics = _metric_counts(candidate_graph)
    metric_findings, warnings = _metric_findings(metrics)
    findings = root_findings + metric_findings
    ok = not findings
    source_ref = _text(candidate_graph.get("source_ref"))
    if not source_ref and candidate_graph_path is not None:
        source_ref = _relative_ref(candidate_graph_path)
    return {
        "artifact_kind": "pre_sib_coherence_report",
        "schema_version": SCHEMA_VERSION,
        "proposal_id": PROPOSAL_ID,
        "contract_ref": CONTRACT_REF,
        "source_ref": source_ref or "operator://pre-sib-coherence-local",
        "generated_at": _now_iso(),
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "source_candidate_graph": {
            "artifact_kind": candidate_graph.get("artifact_kind"),
            "contract_ref": candidate_graph.get("contract_ref"),
            "source_ref": source_ref or "unknown",
            "pre_sib_readiness": _dict(candidate_graph.get("pre_sib_readiness")).get(
                "review_state"
            ),
        },
        "metrics": metrics,
        "readiness": {
            "ready": ok,
            "review_state": "ready_for_repair_loop" if ok else "pre_sib_review_required",
            "next_artifact": "runs/candidate_repair_loop_report.json",
            "blocked_by": [finding["finding_id"] for finding in findings],
        },
        "authority_boundary": _authority_boundary(),
        "privacy_boundary": {
            "raw_intent_text_published": False,
            "raw_prompt_published": False,
            "raw_model_output_published": False,
        },
        "findings": findings,
        "warnings": warnings,
        "summary": {
            "status": "ready_for_repair_loop" if ok else "pre_sib_review_required",
            "finding_count": len(findings),
            "warning_count": len(warnings),
            "node_count": metrics["node_count"],
            "edge_count": metrics["edge_count"],
            "gap_count": metrics["gap_count"],
        },
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-graph", default=DEFAULT_CANDIDATE_GRAPH_PATH, type=Path)
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH, type=Path)
    parser.add_argument("--strict", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    candidate_graph = load_json(args.candidate_graph)
    report = build_pre_sib_coherence_report(
        candidate_graph,
        candidate_graph_path=args.candidate_graph,
    )
    write_json(report, args.output)
    print(json.dumps(report, indent=2, sort_keys=True))
    if args.strict and not report["readiness"]["ready"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
