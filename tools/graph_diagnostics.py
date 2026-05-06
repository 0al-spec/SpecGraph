#!/usr/bin/env python3
"""Build a compact diagnosis from current SpecGraph run artifacts.

The tool is a shape-aware read model over generated `runs/*.json` files. It
keeps operator diagnostics out of ad hoc jq snippets and tolerates the current
artifact contracts where dashboard sections are maps, trace projection keeps an
implementation backlog object, and metric data can live in either dashboard or
metric-signal artifacts.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

DEFAULT_ARTIFACTS = {
    "dashboard": "graph_dashboard.json",
    "backlog": "graph_backlog_projection.json",
    "next_moves": "graph_next_moves.json",
    "health": "graph_health_overlay.json",
    "trace": "spec_trace_projection.json",
    "evidence": "evidence_plane_overlay.json",
    "implementation_work": "implementation_work_index.json",
    "metric_signals": "metric_signal_index.json",
    "metric_thresholds": "metric_threshold_proposals.json",
    "metric_pack_runs": "metric_pack_runs.json",
}


def as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def read_json(path: Path) -> tuple[dict[str, Any], str | None]:
    if not path.exists():
        return {}, f"missing:{path.name}"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return {}, f"invalid_json:{path.name}:{exc.lineno}:{exc.colno}"
    if not isinstance(payload, dict):
        return {}, f"invalid_shape:{path.name}:top_level_not_object"
    return payload, None


def count_by(values: list[Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        key = str(value or "")
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def first_present(*values: Any) -> Any:
    for value in values:
        if value is not None:
            return value
    return None


def card_values(dashboard: dict[str, Any]) -> dict[str, Any]:
    cards: dict[str, Any] = {}
    for card in as_list(dashboard.get("headline_cards")):
        card_obj = as_dict(card)
        card_id = card_obj.get("card_id")
        if isinstance(card_id, str) and card_id:
            cards[card_id] = card_obj.get("value")
    return cards


def dashboard_sections(dashboard: dict[str, Any]) -> dict[str, dict[str, Any]]:
    sections = dashboard.get("sections")
    if isinstance(sections, dict):
        return {str(key): as_dict(value) for key, value in sections.items()}
    # Defensive compatibility for older section-list experiments.
    result: dict[str, dict[str, Any]] = {}
    for section in as_list(sections):
        section_obj = as_dict(section)
        section_id = section_obj.get("id") or section_obj.get("section_id")
        if isinstance(section_id, str) and section_id:
            result[section_id] = section_obj
    return result


def summarize_dashboard(dashboard: dict[str, Any]) -> dict[str, Any]:
    cards = card_values(dashboard)
    sections = dashboard_sections(dashboard)
    graph = sections.get("graph", {})
    return {
        "generated_at": dashboard.get("generated_at"),
        "total_specs": first_present(cards.get("total_specs"), graph.get("total_spec_count")),
        "active_specs": first_present(cards.get("active_specs"), graph.get("active_spec_count")),
        "gated_specs": cards.get("gated_specs"),
        "structural_pressure_specs": cards.get("structural_pressure_specs"),
        "branch_rewrite_candidates": cards.get("branch_rewrite_candidates"),
        "verified_specs": cards.get("verified_specs"),
        "implementation_work_open": cards.get("implementation_work_open"),
        "complete_evidence_chains": cards.get("complete_evidence_chains"),
        "metric_packs_review_ready": cards.get("metric_packs_review_ready"),
        "metrics_below_threshold": cards.get("metrics_below_threshold"),
        "graph_backlog_open": cards.get("graph_backlog_open"),
    }


def summarize_backlog(backlog: dict[str, Any], top_limit: int) -> dict[str, Any]:
    summary = as_dict(backlog.get("summary"))
    entries = as_list(backlog.get("entries"))
    high_entries = [as_dict(entry) for entry in entries if as_dict(entry).get("priority") == "high"]
    return {
        "entry_count": summary.get("entry_count", len(entries)),
        "priority_counts": as_dict(summary.get("priority_counts")),
        "domain_counts": as_dict(summary.get("domain_counts")),
        "next_gap_counts": as_dict(summary.get("next_gap_counts")),
        "source_artifact_counts": as_dict(summary.get("source_artifact_counts")),
        "top_high_priority": [
            {
                "backlog_id": entry.get("backlog_id"),
                "domain": entry.get("domain"),
                "subject_kind": entry.get("subject_kind"),
                "subject_id": entry.get("subject_id"),
                "title": entry.get("title"),
                "status": entry.get("status"),
                "next_gap": entry.get("next_gap"),
                "source_artifact": entry.get("source_artifact"),
            }
            for entry in high_entries[:top_limit]
        ],
    }


def summarize_next_move(next_moves: dict[str, Any]) -> dict[str, Any]:
    move = as_dict(next_moves.get("recommended_next_move"))
    subject = as_dict(move.get("subject"))
    return {
        "current_scene": next_moves.get("current_scene"),
        "recommended": {
            "move_id": move.get("move_id"),
            "kind": move.get("kind"),
            "title": move.get("title"),
            "next_gap": move.get("next_gap"),
            "bounded_scope": as_list(move.get("bounded_scope")),
            "subject_id": subject.get("subject_id"),
            "subject_kind": subject.get("subject_kind"),
            "source_artifacts": as_list(move.get("source_artifacts")),
            "review_required": move.get("review_required"),
        },
        "alternative_count": len(as_list(next_moves.get("alternatives"))),
        "blocked_move_count": len(as_list(next_moves.get("blocked_moves"))),
    }


def summarize_health(health: dict[str, Any]) -> dict[str, Any]:
    entries = [as_dict(entry) for entry in as_list(health.get("entries"))]
    hotspots = [as_dict(entry) for entry in as_list(health.get("hotspot_regions"))]
    return {
        "affected_spec_count": as_dict(health.get("source")).get("affected_spec_count"),
        "entries": [
            {
                "spec_id": entry.get("spec_id"),
                "title": entry.get("title"),
                "gate_state": entry.get("gate_state"),
                "diagnostic_outcome": entry.get("diagnostic_outcome"),
                "signals": as_list(entry.get("signals")),
                "recommended_actions": as_list(entry.get("recommended_actions")),
                "problem_score": entry.get("problem_score"),
            }
            for entry in entries
        ],
        "hotspot_regions": [
            {
                "spec_id": entry.get("spec_id"),
                "title": entry.get("title"),
                "gate_state": entry.get("gate_state"),
                "diagnostic_outcome": entry.get("diagnostic_outcome"),
                "signals": as_list(entry.get("signals")),
                "recommended_actions": as_list(entry.get("recommended_actions")),
                "problem_score": entry.get("problem_score"),
                "active_subtree_size": entry.get("active_subtree_size"),
                "historical_descendant_count": entry.get("historical_descendant_count"),
            }
            for entry in hotspots
        ],
    }


def summarize_trace(trace: dict[str, Any]) -> dict[str, Any]:
    implementation_backlog = as_dict(trace.get("implementation_backlog"))
    viewer_projection = as_dict(trace.get("viewer_projection"))
    return {
        "entry_count": trace.get("entry_count"),
        "implementation_backlog_count": implementation_backlog.get("entry_count"),
        "implementation_state_counts": {
            key: len(as_list(value))
            for key, value in as_dict(viewer_projection.get("implementation_state")).items()
        },
        "freshness_counts": {
            key: len(as_list(value))
            for key, value in as_dict(viewer_projection.get("freshness")).items()
        },
        "acceptance_coverage_counts": {
            key: len(as_list(value))
            for key, value in as_dict(viewer_projection.get("acceptance_coverage")).items()
        },
        "named_filter_counts": {
            key: len(as_list(value))
            for key, value in as_dict(viewer_projection.get("named_filters")).items()
        },
        "grouped_by_next_gap_counts": {
            key: len(as_list(value))
            for key, value in as_dict(implementation_backlog.get("grouped_by_next_gap")).items()
        },
    }


def summarize_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
    evidence_backlog = as_dict(evidence.get("evidence_backlog"))
    viewer_projection = as_dict(evidence.get("viewer_projection"))
    return {
        "entry_count": evidence.get("entry_count"),
        "evidence_backlog_count": evidence_backlog.get("entry_count"),
        "chain_status_counts": {
            key: len(as_list(value))
            for key, value in as_dict(viewer_projection.get("chain_status")).items()
        },
        "artifact_stage_counts": {
            key: len(as_list(value))
            for key, value in as_dict(viewer_projection.get("artifact_stage")).items()
        },
        "named_filter_counts": {
            key: len(as_list(value))
            for key, value in as_dict(viewer_projection.get("named_filters")).items()
        },
        "grouped_by_next_gap_counts": {
            key: len(as_list(value))
            for key, value in as_dict(evidence_backlog.get("grouped_by_next_gap")).items()
        },
    }


def summarize_implementation_work(index: dict[str, Any]) -> dict[str, Any]:
    entries = [as_dict(entry) for entry in as_list(index.get("entries"))]
    return {
        "entry_count": index.get("entry_count", len(entries)),
        "readiness_counts": count_by([entry.get("readiness") for entry in entries]),
        "next_gap_counts": count_by([entry.get("next_gap") for entry in entries]),
        "blocked_by_trace_gap_count": sum(
            1 for entry in entries if entry.get("readiness") == "blocked_by_trace_gap"
        ),
        "ready_for_coding_agent_count": sum(
            1 for entry in entries if entry.get("readiness") == "ready_for_coding_agent"
        ),
    }


def metrics_from_signal_index(metric_signals: dict[str, Any]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for metric in as_list(metric_signals.get("metrics")):
        metric_obj = as_dict(metric)
        metric_id = metric_obj.get("metric_id")
        if isinstance(metric_id, str) and metric_id:
            result[metric_id] = metric_obj
    return result


def is_authoritative_threshold_metric(metric: dict[str, Any]) -> bool:
    return str(metric.get("threshold_authority_state", "")).strip() == (
        "canonical_threshold_authority"
    )


def summarize_metrics(
    dashboard: dict[str, Any],
    metric_signals: dict[str, Any],
    thresholds: dict[str, Any],
    metric_pack_runs: dict[str, Any],
) -> dict[str, Any]:
    metrics_section = dashboard_sections(dashboard).get("metrics", {})
    signal_metrics = metrics_from_signal_index(metric_signals)
    metric_scores = as_dict(metrics_section.get("metric_scores"))
    if not metric_scores:
        metric_scores = {
            metric_id: {
                "score": metric.get("score"),
                "minimum_score": metric.get("minimum_score"),
                "status": metric.get("status"),
                "threshold_gap": metric.get("threshold_gap"),
            }
            for metric_id, metric in signal_metrics.items()
        }

    authoritative_below = as_list(metrics_section.get("below_threshold_authoritative_metric_ids"))
    if not authoritative_below:
        authoritative_below = [
            metric_id
            for metric_id, metric in signal_metrics.items()
            if metric.get("status") == "below_threshold"
            and is_authoritative_threshold_metric(metric)
        ]

    threshold_entries = [as_dict(entry) for entry in as_list(thresholds.get("entries"))]
    pack_runs = [as_dict(entry) for entry in as_list(metric_pack_runs.get("entries"))]
    return {
        "metric_count": first_present(metrics_section.get("metric_count"), len(signal_metrics)),
        "metric_status_counts": first_present(
            metrics_section.get("metric_status_counts"),
            count_by([metric.get("status") for metric in signal_metrics.values()]),
        ),
        "metric_scores": metric_scores,
        "below_threshold_authoritative_metric_ids": authoritative_below,
        "threshold_proposals": [
            {
                "proposal_id": entry.get("proposal_id"),
                "metric_id": entry.get("metric_id"),
                "severity": entry.get("severity"),
                "score": entry.get("score"),
                "minimum_score": entry.get("minimum_score"),
                "threshold_gap": entry.get("threshold_gap"),
                "recommended_actions": as_list(entry.get("recommended_actions")),
            }
            for entry in threshold_entries
        ],
        "metric_pack_run_counts": {
            "entry_count": metric_pack_runs.get("entry_count", len(pack_runs)),
            "computed": sum(1 for entry in pack_runs if entry.get("run_status") == "computed"),
            "gap_entries": sum(1 for entry in pack_runs if as_list(entry.get("gaps"))),
        },
    }


def summarize_process_feedback(dashboard: dict[str, Any]) -> dict[str, Any]:
    section = dashboard_sections(dashboard).get("process_feedback", {})
    return {
        "entry_count": section.get("review_feedback_entry_count"),
        "backlog_count": section.get("review_feedback_backlog_count"),
        "status_counts": as_dict(section.get("review_feedback_status_counts")),
        "root_cause_counts": as_dict(section.get("review_feedback_root_cause_counts")),
        "prevention_counts": as_dict(section.get("review_feedback_prevention_counts")),
    }


def build_interpretation(summary: dict[str, Any]) -> list[str]:
    metrics = as_dict(summary.get("metrics"))
    health = as_dict(summary.get("health"))
    trace = as_dict(summary.get("trace"))
    evidence = as_dict(summary.get("evidence"))
    next_move = as_dict(summary.get("next_move"))
    dashboard = as_dict(summary.get("dashboard"))
    lines: list[str] = []

    recommended = as_dict(next_move.get("recommended"))
    if recommended.get("subject_id"):
        lines.append(
            f"Recommended next move targets {recommended.get('subject_id')} "
            f"with next_gap={recommended.get('next_gap')}."
        )

    hotspots = as_list(health.get("hotspot_regions"))
    if hotspots:
        top = as_dict(hotspots[0])
        lines.append(
            f"Top health hotspot is {top.get('spec_id')} with signals="
            f"{','.join(str(item) for item in as_list(top.get('signals')))}."
        )

    below = as_list(metrics.get("below_threshold_authoritative_metric_ids"))
    if below:
        rendered = ", ".join(str(item) for item in below)
        lines.append(f"Authoritative metrics below threshold: {rendered}.")

    missing_trace = as_dict(trace.get("named_filter_counts")).get("missing_trace_contract")
    missing_evidence = as_dict(evidence.get("named_filter_counts")).get("missing_evidence_contract")
    if missing_trace or missing_evidence:
        lines.append(
            f"Trace/evidence coverage is the main systemic gap: "
            f"missing_trace_contract={missing_trace}, missing_evidence_contract={missing_evidence}."
        )

    structural_pressure = dashboard.get("structural_pressure_specs")
    verified_specs = dashboard.get("verified_specs")
    if structural_pressure is not None and verified_specs is not None:
        lines.append(
            f"Structural pressure is narrow ({structural_pressure} specs), "
            f"but verified specs remain {verified_specs}."
        )

    return lines


def build_summary(runs_dir: Path, top_limit: int = 10) -> dict[str, Any]:
    artifacts: dict[str, dict[str, Any]] = {}
    warnings: list[str] = []
    for name, filename in DEFAULT_ARTIFACTS.items():
        payload, warning = read_json(runs_dir / filename)
        artifacts[name] = payload
        if warning:
            warnings.append(warning)

    summary = {
        "artifact_kind": "graph_diagnostics_summary",
        "schema_version": 1,
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "runs_dir": str(runs_dir),
        "warnings": warnings,
        "dashboard": summarize_dashboard(artifacts["dashboard"]),
        "next_move": summarize_next_move(artifacts["next_moves"]),
        "backlog": summarize_backlog(artifacts["backlog"], top_limit=top_limit),
        "health": summarize_health(artifacts["health"]),
        "trace": summarize_trace(artifacts["trace"]),
        "evidence": summarize_evidence(artifacts["evidence"]),
        "implementation_work": summarize_implementation_work(artifacts["implementation_work"]),
        "metrics": summarize_metrics(
            artifacts["dashboard"],
            artifacts["metric_signals"],
            artifacts["metric_thresholds"],
            artifacts["metric_pack_runs"],
        ),
        "process_feedback": summarize_process_feedback(artifacts["dashboard"]),
    }
    summary["interpretation"] = build_interpretation(summary)
    return summary


def render_text(summary: dict[str, Any]) -> str:
    warnings = as_list(summary.get("warnings"))
    dashboard = as_dict(summary.get("dashboard"))
    next_move = as_dict(summary.get("next_move"))
    recommended = as_dict(next_move.get("recommended"))
    backlog = as_dict(summary.get("backlog"))
    metrics = as_dict(summary.get("metrics"))
    trace = as_dict(summary.get("trace"))
    evidence = as_dict(summary.get("evidence"))
    health = as_dict(summary.get("health"))

    lines = [
        "SpecGraph Diagnostics",
    ]
    if warnings:
        lines.extend(["", "Warnings:"])
        lines.extend(f"- {warning}" for warning in warnings)

    lines.extend(
        [
            "",
            f"Specs: total={dashboard.get('total_specs')} active={dashboard.get('active_specs')} "
            f"gated={dashboard.get('gated_specs')} "
            f"structural_pressure={dashboard.get('structural_pressure_specs')}",
            f"Backlog: open={backlog.get('entry_count')} "
            f"priorities={backlog.get('priority_counts')}",
            f"Next move: {recommended.get('title')} ({recommended.get('next_gap')})",
            f"Metrics below threshold: {metrics.get('below_threshold_authoritative_metric_ids')}",
            f"Trace: {trace.get('named_filter_counts')}",
            f"Evidence: {evidence.get('named_filter_counts')}",
            "",
            "Health hotspots:",
        ]
    )
    for hotspot in as_list(health.get("hotspot_regions"))[:5]:
        hotspot_obj = as_dict(hotspot)
        lines.append(
            f"- {hotspot_obj.get('spec_id')}: gate={hotspot_obj.get('gate_state')} "
            f"score={hotspot_obj.get('problem_score')} signals={hotspot_obj.get('signals')}"
        )

    lines.extend(["", "Interpretation:"])
    for item in as_list(summary.get("interpretation")):
        lines.append(f"- {item}")

    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Summarize current SpecGraph diagnostic artifacts."
    )
    parser.add_argument(
        "--runs-dir",
        default="runs",
        help="Directory containing generated run artifacts (default: runs)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "text"],
        default="text",
        help="Output format (default: text)",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="Maximum high-priority backlog rows to include (default: 10)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    runs_dir = Path(args.runs_dir)
    summary = build_summary(runs_dir, top_limit=max(args.top, 0))
    if args.format == "json":
        print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(render_text(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
