from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def load_graph_diagnostics_module() -> object:
    module_path = Path(__file__).resolve().parents[1] / "tools" / "graph_diagnostics.py"
    spec = importlib.util.spec_from_file_location("test_graph_diagnostics_module", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: str) -> None:
    path.write_text(payload, encoding="utf-8")


def test_build_summary_handles_current_artifact_shapes(tmp_path: Path) -> None:
    module = load_graph_diagnostics_module()
    runs = tmp_path / "runs"
    runs.mkdir()

    write_json(
        runs / "graph_dashboard.json",
        """
        {
          "artifact_kind": "graph_dashboard",
          "generated_at": "2026-05-06T00:00:00Z",
          "headline_cards": [
            {"card_id": "total_specs", "value": 57},
            {"card_id": "active_specs", "value": 53},
            {"card_id": "gated_specs", "value": 1},
            {"card_id": "structural_pressure_specs", "value": 2},
            {"card_id": "verified_specs", "value": 0},
            {"card_id": "implementation_work_open", "value": 16},
            {"card_id": "complete_evidence_chains", "value": 2},
            {"card_id": "metric_packs_review_ready", "value": 1},
            {"card_id": "metrics_below_threshold", "value": 2},
            {"card_id": "graph_backlog_open", "value": 222}
          ],
          "sections": {
            "metrics": {
              "metric_count": 2,
              "metric_status_counts": {"below_threshold": 1, "healthy": 1},
              "metric_scores": {
                "specification_verifiability": {
                  "score": 0.149,
                  "minimum_score": 0.45,
                  "status": "below_threshold"
                }
              },
              "below_threshold_authoritative_metric_ids": ["specification_verifiability"]
            },
            "process_feedback": {
              "review_feedback_entry_count": 27,
              "review_feedback_backlog_count": 1,
              "review_feedback_status_counts": {"prevention_recorded": 26},
              "review_feedback_root_cause_counts": {"artifact_contract_validation_gap": 10},
              "review_feedback_prevention_counts": {"regression_test_added": 18}
            }
          }
        }
        """,
    )
    write_json(
        runs / "graph_backlog_projection.json",
        """
        {
          "summary": {
            "entry_count": 2,
            "priority_counts": {"high": 1, "medium": 1},
            "domain_counts": {"health": 1, "metrics": 1},
            "next_gap_counts": {"resolve_split_gate": 1},
            "source_artifact_counts": {"graph_health_overlay": 1}
          },
          "entries": [
            {
              "backlog_id": "b1",
              "priority": "high",
              "domain": "health",
              "subject_kind": "spec",
              "subject_id": "SG-SPEC-0032",
              "title": "Split pressure",
              "status": "split_required",
              "next_gap": "resolve_split_gate",
              "source_artifact": "graph_health_overlay"
            }
          ]
        }
        """,
    )
    write_json(
        runs / "graph_next_moves.json",
        """
        {
          "current_scene": "high_priority_backlog",
          "recommended_next_move": {
            "move_id": "m1",
            "kind": "review_backlog_item",
            "title": "Review SG-SPEC-0032",
            "next_gap": "resolve_split_gate",
            "bounded_scope": ["SG-SPEC-0032"],
            "source_artifacts": ["runs/graph_health_overlay.json"],
            "review_required": true,
            "subject": {"subject_kind": "spec", "subject_id": "SG-SPEC-0032"}
          },
          "alternatives": [{}],
          "blocked_moves": []
        }
        """,
    )
    write_json(
        runs / "graph_health_overlay.json",
        """
        {
          "source": {"affected_spec_count": 1},
          "entries": [
            {
              "spec_id": "SG-SPEC-0032",
              "title": "Split pressure",
              "gate_state": "split_required",
              "diagnostic_outcome": "split_required",
              "signals": ["repeated_split_required_candidate"],
              "recommended_actions": ["schedule_decomposition_pass"],
              "problem_score": 3
            }
          ],
          "hotspot_regions": [
            {
              "spec_id": "SG-SPEC-0032",
              "title": "Split pressure",
              "gate_state": "split_required",
              "diagnostic_outcome": "split_required",
              "signals": ["repeated_split_required_candidate"],
              "recommended_actions": ["schedule_decomposition_pass"],
              "problem_score": 3,
              "active_subtree_size": 6,
              "historical_descendant_count": 3
            }
          ]
        }
        """,
    )
    write_json(
        runs / "spec_trace_projection.json",
        """
        {
          "entry_count": 57,
          "implementation_backlog": {
            "entry_count": 57,
            "grouped_by_next_gap": {
              "attach_trace_contract": ["SG-SPEC-0001", "SG-SPEC-0002"]
            }
          },
          "viewer_projection": {
            "implementation_state": {"unclaimed": ["SG-SPEC-0001"], "implemented": []},
            "freshness": {"not_tracked": ["SG-SPEC-0001"]},
            "acceptance_coverage": {"no_linked_evidence": ["SG-SPEC-0001"]},
            "named_filters": {"missing_trace_contract": ["SG-SPEC-0001"]}
          }
        }
        """,
    )
    write_json(
        runs / "evidence_plane_overlay.json",
        """
        {
          "entry_count": 57,
          "evidence_backlog": {
            "entry_count": 55,
            "grouped_by_next_gap": {
              "attach_evidence_contract": ["SG-SPEC-0001"]
            }
          },
          "viewer_projection": {
            "chain_status": {"untracked": ["SG-SPEC-0001"]},
            "artifact_stage": {"untracked": ["SG-SPEC-0001"]},
            "named_filters": {"missing_evidence_contract": ["SG-SPEC-0001"]}
          }
        }
        """,
    )
    write_json(
        runs / "implementation_work_index.json",
        """
        {
          "entry_count": 1,
          "entries": [
            {
              "readiness": "blocked_by_trace_gap",
              "next_gap": "attach_trace_baseline"
            }
          ]
        }
        """,
    )
    write_json(
        runs / "metric_signal_index.json",
        """
        {
          "metrics": [
            {
              "metric_id": "specification_verifiability",
              "status": "below_threshold",
              "threshold_authority_state": "canonical_threshold_authority",
              "score": 0.149,
              "minimum_score": 0.45
            }
          ]
        }
        """,
    )
    write_json(
        runs / "metric_threshold_proposals.json",
        """
        {
          "entries": [
            {
              "proposal_id": "metric-specification_verifiability-followup",
              "metric_id": "specification_verifiability",
              "severity": "high",
              "score": 0.149,
              "minimum_score": 0.45,
              "threshold_gap": 0.301,
              "recommended_actions": ["attach_trace_contract"]
            }
          ]
        }
        """,
    )
    write_json(
        runs / "metric_pack_runs.json",
        """
        {
          "entry_count": 1,
          "entries": [
            {"run_status": "computed", "gaps": []}
          ]
        }
        """,
    )

    summary = module.build_summary(runs, top_limit=1)

    assert summary["dashboard"]["total_specs"] == 57
    assert summary["canonical_mutations_allowed"] is False
    assert summary["tracked_artifacts_written"] is False
    assert summary["next_move"]["recommended"]["subject_id"] == "SG-SPEC-0032"
    assert summary["backlog"]["top_high_priority"][0]["next_gap"] == "resolve_split_gate"
    assert summary["trace"]["named_filter_counts"]["missing_trace_contract"] == 1
    assert summary["evidence"]["named_filter_counts"]["missing_evidence_contract"] == 1
    assert summary["implementation_work"]["blocked_by_trace_gap_count"] == 1
    assert summary["metrics"]["below_threshold_authoritative_metric_ids"] == [
        "specification_verifiability"
    ]
    assert any("Trace/evidence coverage" in item for item in summary["interpretation"])


def test_build_summary_reports_missing_artifacts(tmp_path: Path) -> None:
    module = load_graph_diagnostics_module()
    runs = tmp_path / "runs"
    runs.mkdir()

    summary = module.build_summary(runs)

    assert summary["artifact_kind"] == "graph_diagnostics_summary"
    assert "missing:graph_dashboard.json" in summary["warnings"]
    assert summary["dashboard"]["total_specs"] is None
    assert summary["canonical_mutations_allowed"] is False
    assert summary["tracked_artifacts_written"] is False


def test_build_summary_fallback_excludes_non_authoritative_threshold_metrics(
    tmp_path: Path,
) -> None:
    module = load_graph_diagnostics_module()
    runs = tmp_path / "runs"
    runs.mkdir()
    write_json(
        runs / "metric_signal_index.json",
        """
        {
          "metrics": [
            {
              "metric_id": "specification_verifiability",
              "status": "below_threshold",
              "threshold_authority_state": "canonical_threshold_authority"
            },
            {
              "metric_id": "economic_cost_pressure",
              "status": "below_threshold",
              "threshold_authority_state": "not_threshold_authority"
            },
            {
              "metric_id": "sib_proxy",
              "status": "below_threshold",
              "threshold_authority_state": "alias_only"
            }
          ]
        }
        """,
    )

    summary = module.build_summary(runs)

    assert summary["metrics"]["below_threshold_authoritative_metric_ids"] == [
        "specification_verifiability"
    ]


def test_main_default_text_output_includes_artifact_warnings(
    tmp_path: Path,
    capsys,
) -> None:
    module = load_graph_diagnostics_module()
    runs = tmp_path / "runs"
    runs.mkdir()

    exit_code = module.main(["--runs-dir", str(runs)])

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "SpecGraph Diagnostics" in output
    assert "Warnings:" in output
    assert "- missing:graph_dashboard.json" in output
    assert "- missing:metric_pack_runs.json" in output
