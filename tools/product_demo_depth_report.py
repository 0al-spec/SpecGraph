"""Validate the semantic depth baseline for product demo candidate runs."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_ID = "0204"
SCHEMA_VERSION = 1
CONTRACT_REF = "specgraph.idea-to-spec.product-demo-depth-report.v0.1"

WORKFLOW_RELATIONS = {
    "actor_triggers_command",
    "command_emits_event",
    "event_informs_policy",
    "event_informs_constraint",
    "constraint_applies_to_command",
    "policy_applies_to_command",
}


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


def _relative_ref(path: Path) -> str:
    repo_path = _repo_path(path)
    try:
        return repo_path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return f"external:{repo_path.name or 'artifact'}"


def load_optional(path: Path) -> dict[str, Any]:
    repo_path = _repo_path(path)
    if not repo_path.exists():
        return {}
    payload = json.loads(repo_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def write_json(payload: dict[str, Any], path: Path) -> None:
    output_path = _repo_path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _authority_boundary() -> dict[str, bool]:
    return {
        "may_execute_prompt_agent": False,
        "may_execute_specgraph": False,
        "may_execute_platform": False,
        "may_mutate_candidate_artifacts": False,
        "may_mutate_canonical_specs": False,
        "may_write_ontology_package": False,
        "may_accept_ontology_terms": False,
        "may_approve_candidate": False,
        "may_create_branch_or_commit": False,
        "may_open_pull_request": False,
        "may_publish_read_model": False,
    }


def _privacy_boundary() -> dict[str, bool]:
    return {
        "raw_idea_text_published": False,
        "raw_prompt_published": False,
        "raw_model_output_published": False,
        "private_operator_state_published": False,
    }


def _event_storming_counts(intake: dict[str, Any]) -> dict[str, int]:
    event_storming = _dict(intake.get("event_storming"))
    return {
        "actor_count": len(_list(event_storming.get("actors"))),
        "command_count": len(_list(event_storming.get("commands"))),
        "domain_event_count": len(_list(event_storming.get("domain_events"))),
        "policy_count": len(_list(event_storming.get("policies"))),
        "constraint_count": len(_list(event_storming.get("constraints"))),
    }


def _candidate_graph_counts(candidate_graph: dict[str, Any]) -> dict[str, Any]:
    nodes = [node for node in _list(candidate_graph.get("nodes")) if isinstance(node, dict)]
    edges = [edge for edge in _list(candidate_graph.get("edges")) if isinstance(edge, dict)]
    relation_counts = Counter(_text(edge.get("relation"), "unknown") for edge in edges)
    workflow_edge_count = sum(relation_counts.get(relation, 0) for relation in WORKFLOW_RELATIONS)
    return {
        "node_count": len(nodes),
        "topology_edge_count": len(edges),
        "workflow_edge_count": workflow_edge_count,
        "requirement_count": sum(len(_list(node.get("requirements"))) for node in nodes),
        "acceptance_criteria_count": sum(
            len(_list(node.get("acceptance_criteria"))) for node in nodes
        ),
        "topology_relation_counts": dict(sorted(relation_counts.items())),
    }


def _overview_counts(candidate_overview: dict[str, Any]) -> dict[str, Any]:
    summary = _dict(candidate_overview.get("summary"))
    sections = _dict(candidate_overview.get("sections"))
    event_storming = _dict(sections.get("event_storming"))
    topology = _dict(sections.get("topology"))
    return {
        "candidate_overview_present": bool(candidate_overview),
        "candidate_overview_status": _text(
            summary.get("status"), _text(candidate_overview.get("status"))
        ),
        "overview_actor_count": _int(_dict(event_storming.get("actors")).get("count")),
        "overview_domain_event_count": _int(
            _dict(event_storming.get("domain_events")).get("count")
        ),
        "overview_workflow_edge_count": _int(topology.get("workflow_edge_count")),
    }


def _maturity_counts(idea_maturity: dict[str, Any]) -> dict[str, Any]:
    summary = _dict(idea_maturity.get("summary"))
    return {
        "idea_maturity_present": bool(idea_maturity),
        "idea_maturity_status": _text(idea_maturity.get("status"), _text(summary.get("status"))),
        "idea_maturity_lifecycle_state": _text(summary.get("lifecycle_state")),
        "idea_maturity_blocker_count": _int(summary.get("blocker_count")),
    }


def _blocking_findings(depth: dict[str, Any]) -> list[dict[str, Any]]:
    checks = [
        ("actor_count", "Product demo requires at least one actor."),
        ("command_count", "Product demo requires at least one command."),
        ("domain_event_count", "Product demo requires at least one domain event."),
        ("policy_count", "Product demo requires at least one policy."),
        ("constraint_count", "Product demo requires at least one constraint."),
        ("workflow_edge_count", "Product demo requires at least one workflow topology edge."),
        ("node_count", "Product demo requires at least one candidate node."),
        ("requirement_count", "Product demo requires candidate requirements."),
        ("acceptance_criteria_count", "Product demo requires acceptance criteria."),
    ]
    findings: list[dict[str, Any]] = []
    for field, message in checks:
        if _int(depth.get(field)) <= 0:
            findings.append(
                {
                    "finding_id": f"product_demo_depth_{field}_missing",
                    "severity": "blocking",
                    "message": message,
                    "source": "product_demo_depth_report",
                    "evidence": {"field": field, "value": depth.get(field)},
                }
            )
    if not depth.get("candidate_overview_present"):
        findings.append(
            {
                "finding_id": "product_demo_depth_candidate_overview_missing",
                "severity": "blocking",
                "message": "Product demo requires candidate_overview.json.",
                "source": "product_demo_depth_report",
                "evidence": {"candidate_overview_present": False},
            }
        )
    if not depth.get("idea_maturity_present"):
        findings.append(
            {
                "finding_id": "product_demo_depth_idea_maturity_missing",
                "severity": "blocking",
                "message": "Product demo requires idea_maturity_metrics_report.json.",
                "source": "product_demo_depth_report",
                "evidence": {"idea_maturity_present": False},
            }
        )
    elif depth.get("idea_maturity_status") in {"", "missing"}:
        findings.append(
            {
                "finding_id": "product_demo_depth_idea_maturity_status_missing",
                "severity": "blocking",
                "message": "Product demo Idea Maturity status must be available.",
                "source": "product_demo_depth_report",
                "evidence": {"idea_maturity_status": depth.get("idea_maturity_status")},
            }
        )
    return findings


def build_depth_report(
    *,
    run_dir: Path,
    intake_path: Path,
    candidate_graph_path: Path,
    candidate_overview_path: Path,
    idea_maturity_path: Path,
) -> dict[str, Any]:
    intake = load_optional(intake_path)
    candidate_graph = load_optional(candidate_graph_path)
    candidate_overview = load_optional(candidate_overview_path)
    idea_maturity = load_optional(idea_maturity_path)
    depth = {
        **_event_storming_counts(intake),
        **_candidate_graph_counts(candidate_graph),
        **_overview_counts(candidate_overview),
        **_maturity_counts(idea_maturity),
    }
    findings = _blocking_findings(depth)
    status = "depth_baseline_met" if not findings else "depth_baseline_failed"
    return {
        "artifact_kind": "product_demo_depth_report",
        "schema_version": SCHEMA_VERSION,
        "contract_ref": CONTRACT_REF,
        "proposal_id": PROPOSAL_ID,
        "generated_at": _now_iso(),
        "status": status,
        "run_dir": _relative_ref(run_dir),
        "summary": {
            "status": status,
            "blocking_count": len(findings),
            "actor_count": depth["actor_count"],
            "domain_event_count": depth["domain_event_count"],
            "workflow_edge_count": depth["workflow_edge_count"],
            "idea_maturity_status": depth["idea_maturity_status"],
            "candidate_overview_status": depth["candidate_overview_status"],
        },
        "depth": depth,
        "findings": findings,
        "source_refs": {
            "intake": _relative_ref(intake_path),
            "candidate_graph": _relative_ref(candidate_graph_path),
            "candidate_overview": _relative_ref(candidate_overview_path),
            "idea_maturity": _relative_ref(idea_maturity_path),
        },
        "authority_boundary": _authority_boundary(),
        "privacy_boundary": _privacy_boundary(),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--intake", type=Path, required=True)
    parser.add_argument("--candidate-graph", type=Path, required=True)
    parser.add_argument("--candidate-overview", type=Path, required=True)
    parser.add_argument("--idea-maturity", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--strict", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = build_depth_report(
        run_dir=args.run_dir,
        intake_path=args.intake,
        candidate_graph_path=args.candidate_graph,
        candidate_overview_path=args.candidate_overview,
        idea_maturity_path=args.idea_maturity,
    )
    write_json(report, args.output)
    print(f"{report['status']} -> {_relative_ref(args.output)}")
    if args.strict and report["status"] != "depth_baseline_met":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
