from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "idea_maturity_metrics_report.py"


def load_module() -> object:
    spec = importlib.util.spec_from_file_location(
        "idea_maturity_metrics_report_under_test", TOOL_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def ref(path: Path) -> str:
    return path.as_posix()


def authority_boundary() -> dict[str, bool]:
    return {
        "may_mutate_canonical_specs": False,
        "may_write_ontology_package": False,
        "may_accept_ontology_terms": False,
        "may_create_branch_or_commit": False,
        "may_open_pull_request": False,
        "may_merge_pull_request": False,
        "may_publish_read_model": False,
        "may_execute_prompt_agent": False,
    }


def base_paths(run_dir: Path) -> dict[str, Path]:
    return {
        "intake": run_dir / "idea_event_storming_intake.json",
        "candidate_graph": run_dir / "candidate_spec_graph.json",
        "clarification_requests": run_dir / "idea_to_spec_clarification_requests.json",
        "clarification_answers": run_dir / "idea_to_spec_clarification_answers.json",
        "ontology_decisions": run_dir / "product_ontology_gap_review_decisions.json",
        "rerun_input": run_dir / "idea_to_spec_answer_rerun_input.json",
        "rerun_preview": run_dir / "idea_to_spec_rerun_preview.json",
        "rerun_materialization": run_dir / "idea_to_spec_rerun_materialization.json",
        "repaired_handoff": run_dir / "repaired_candidate_promotion_handoff_report.json",
        "repaired_candidate_graph": run_dir / "repaired_candidate_spec_graph.json",
        "repaired_active_candidate": run_dir / "repaired_active_idea_to_spec_candidate.json",
        "repaired_promotion_gate": run_dir / "repaired_idea_to_spec_promotion_gate.json",
        "repaired_repair_session": run_dir / "repaired_idea_to_spec_repair_session.json",
        "specspace_draft_import_preview": run_dir / "specspace_repair_draft_import_preview.json",
        "specspace_rerun_request": run_dir / "idea_to_spec_repair_rerun_requests.json",
        "approval_intent": run_dir / "idea_to_spec_candidate_approval_intents.json",
        "repair_rerun_execution": run_dir / "platform_product_repair_rerun_execution_report.json",
        "repair_rerun_publication": run_dir
        / "platform_product_repair_rerun_publication_report.json",
        "approval_execution": run_dir / "platform_candidate_approval_execution_report.json",
        "promotion_request": run_dir / "graph_repository_promotion_request.json",
        "promotion_execution": run_dir / "product_candidate_promotion_execution_report.json",
        "review_status": run_dir / "product_candidate_promotion_review_status_report.json",
        "read_model_publication": run_dir
        / "product_candidate_promotion_read_model_publication_report.json",
    }


def write_ready_chain(run_dir: Path, *, stale_rerun_ref: bool = False) -> dict[str, Path]:
    paths = base_paths(run_dir)
    write_json(
        paths["intake"],
        {
            "artifact_kind": "idea_event_storming_intake",
            "contract_ref": "specgraph.idea-to-spec.event-storming-intake.v0.1",
            "schema_version": 1,
            "generated_at": "2026-06-28T10:00:00+00:00",
            "source_intake": {
                "workspace": {
                    "candidate_id": "local-subscription-control",
                    "display_name": "Local Subscription Control",
                    "public_route": "/local-subscription-control",
                }
            },
            "summary": {"status": "ready_for_candidate_graph"},
            "authority_boundary": authority_boundary(),
        },
    )
    write_json(
        paths["candidate_graph"],
        {
            "artifact_kind": "candidate_spec_graph",
            "contract_ref": "specgraph.idea-to-spec.candidate-spec-graph.v0.1",
            "schema_version": 1,
            "generated_at": "2026-06-28T10:01:00+00:00",
            "nodes": [
                {
                    "id": "candidate-spec.product-boundary",
                    "gaps": [
                        {"id": "ontology-gap.subscription", "kind": "ontology_gap"},
                        {"id": "gap.local-risk", "kind": "risk_requires_review"},
                    ],
                }
            ],
            "summary": {"node_count": 1, "gap_count": 2, "status": "ready_for_pre_sib"},
            "authority_boundary": authority_boundary(),
        },
    )
    write_json(
        paths["clarification_requests"],
        {
            "artifact_kind": "idea_to_spec_clarification_requests",
            "contract_ref": "specgraph.idea-to-spec.clarification-requests.v0.1",
            "schema_version": 1,
            "summary": {
                "request_count": 2,
                "blocking_request_count": 1,
                "review_required_request_count": 1,
                "status": "clarification_required",
            },
            "readiness": {
                "ready": False,
                "review_state": "clarification_required",
                "blocked_by": ["clarification.repair"],
            },
            "authority_boundary": authority_boundary(),
        },
    )
    write_json(
        paths["clarification_answers"],
        {
            "artifact_kind": "idea_to_spec_clarification_answers",
            "contract_ref": "specgraph.idea-to-spec.clarification-answers.v0.1",
            "schema_version": 1,
            "source_artifacts": {
                "clarification_requests": {"source_ref": ref(paths["clarification_requests"])}
            },
            "answers": [
                {
                    "request_id": "clarification.ontology",
                    "answer_kind": "propose_project_local_term",
                    "status": "accepted_for_candidate",
                },
                {
                    "request_id": "clarification.candidate-risk",
                    "answer_kind": "provide_candidate_context",
                    "status": "accepted_for_candidate",
                },
            ],
            "summary": {
                "answer_count": 2,
                "accepted_answer_count": 2,
                "status": "answers_ready_for_rerun",
            },
            "readiness": {"ready": True, "review_state": "answers_ready_for_rerun"},
            "authority_boundary": authority_boundary(),
        },
    )
    write_json(
        paths["ontology_decisions"],
        {
            "artifact_kind": "product_ontology_gap_review_decisions",
            "contract_ref": "specgraph.product-ontology.gap-review-decisions.v0.1",
            "schema_version": 1,
            "source_artifacts": {
                "clarification_answers": {"source_ref": ref(paths["clarification_answers"])}
            },
            "decisions": [
                {
                    "id": "decision.subscription",
                    "decision_type": "propose_project_local_term",
                    "status": "accepted_for_candidate_preview",
                    "term": "Subscription",
                }
            ],
            "summary": {
                "decision_count": 1,
                "decision_counts": {"propose_project_local_term": 1},
                "status": "ontology_gap_decisions_ready",
            },
            "readiness": {"ready": True, "review_state": "ontology_gap_decisions_ready"},
            "authority_boundary": authority_boundary(),
        },
    )
    write_json(
        paths["rerun_input"],
        {
            "artifact_kind": "idea_to_spec_answer_rerun_input",
            "contract_ref": "specgraph.idea-to-spec.answer-rerun-input.v0.1",
            "schema_version": 1,
            "source_artifacts": {
                "clarification_answers": {"source_ref": ref(paths["clarification_answers"])},
                "product_ontology_gap_review_decisions": {
                    "source_ref": ref(paths["ontology_decisions"])
                },
            },
            "summary": {
                "accepted_answer_count": 2,
                "candidate_review_hint_count": 1,
                "ontology_decision_count": 1,
                "project_local_term_count": 1,
                "status": "rerun_input_ready",
            },
            "readiness": {"ready": True, "review_state": "rerun_input_ready"},
            "authority_boundary": authority_boundary(),
        },
    )
    write_json(
        paths["rerun_preview"],
        {
            "artifact_kind": "idea_to_spec_rerun_preview",
            "contract_ref": "specgraph.idea-to-spec.rerun-preview.v0.1",
            "schema_version": 1,
            "source_artifacts": {"rerun_input": {"source_ref": ref(paths["rerun_input"])}},
            "summary": {
                "candidate_quality_review_state": "candidate_quality_improved",
                "resolved_candidate_gap_count": 1,
                "resolved_ontology_gap_count": 1,
                "unresolved_candidate_gap_count": 0,
                "unresolved_ontology_gap_count": 0,
                "status": "rerun_preview_ready",
            },
            "readiness": {"ready": True, "review_state": "rerun_preview_ready"},
            "authority_boundary": authority_boundary(),
        },
    )
    write_json(
        paths["rerun_materialization"],
        {
            "artifact_kind": "idea_to_spec_rerun_materialization",
            "contract_ref": "specgraph.idea-to-spec.rerun-materialization.v0.1",
            "schema_version": 1,
            "generated_at": "2026-06-28T10:05:00+00:00",
            "source_artifacts": {
                "rerun_preview": {
                    "source_ref": "runs/stale_rerun_preview.json"
                    if stale_rerun_ref
                    else ref(paths["rerun_preview"])
                }
            },
            "materialization_preview": {
                "delta": {
                    "ontology_resolution_records": [
                        {
                            "gap_id": "ontology-gap.subscription",
                            "request_id": "clarification.ontology",
                            "decision_id": "decision.subscription",
                            "match_kind": "exact",
                        }
                    ],
                    "candidate_resolution_records": [
                        {
                            "gap_id": "gap.local-risk",
                            "request_id": "clarification.candidate-risk",
                            "resolution_kind": "risk_accepted",
                            "match_kind": "target_ref",
                        }
                    ],
                },
                "candidate_graph_preview": {
                    "artifact_kind": "candidate_spec_graph",
                    "nodes": [{"id": "candidate-spec.product-boundary", "gaps": []}],
                    "summary": {"node_count": 1, "gap_count": 0},
                },
            },
            "summary": {
                "removed_gap_count": 2,
                "resolved_candidate_gap_count": 1,
                "resolved_ontology_gap_count": 1,
                "unresolved_candidate_gap_count": 0,
                "unresolved_ontology_gap_count": 0,
                "status": "rerun_materialization_ready",
            },
            "readiness": {"ready": True, "review_state": "rerun_materialization_ready"},
            "authority_boundary": authority_boundary(),
        },
    )
    write_json(
        paths["repaired_candidate_graph"],
        {
            "artifact_kind": "candidate_spec_graph",
            "contract_ref": "specgraph.idea-to-spec.candidate-spec-graph.v0.1",
            "schema_version": 1,
            "nodes": [{"id": "candidate-spec.product-boundary", "gaps": []}],
            "summary": {"node_count": 1, "gap_count": 0, "status": "ready_for_pre_sib"},
        },
    )
    write_json(
        paths["repaired_active_candidate"],
        {
            "artifact_kind": "active_idea_to_spec_candidate",
            "contract_ref": "specgraph.idea-to-spec.active-candidate-source.v0.1",
            "schema_version": 1,
            "candidate": {
                "candidate_id": "local-subscription-control",
                "display_name": "Local Subscription Control",
                "public_route": "/local-subscription-control",
                "workflow_lane": "product_idea_to_spec",
                "governance_profile": "product_workspace",
                "target_repository_role": "product_spec_workspace",
            },
            "summary": {
                "candidate_id": "local-subscription-control",
                "promotion_path_count": 1,
                "status": "active_candidate_ready",
            },
            "readiness": {"ready": True, "review_state": "active_candidate_ready"},
            "authority_boundary": authority_boundary(),
        },
    )
    write_json(
        paths["repaired_promotion_gate"],
        {
            "artifact_kind": "idea_to_spec_promotion_gate",
            "contract_ref": "specgraph.idea-to-spec.promotion-gate.v0.1",
            "schema_version": 1,
            "summary": {
                "promotion_path_count": 1,
                "status": "ready_for_platform_promotion_request",
            },
            "readiness": {
                "ready": True,
                "review_state": "ready_for_platform_promotion_request",
            },
            "authority_boundary": authority_boundary(),
        },
    )
    write_json(
        paths["repaired_repair_session"],
        {
            "artifact_kind": "idea_to_spec_repair_session_journal",
            "contract_ref": "specgraph.idea-to-spec.repair-session-journal.v0.1",
            "schema_version": 1,
            "generated_at": "2026-06-28T10:06:00+00:00",
            "session": {
                "candidate_id": "local-subscription-control",
                "workspace_route": "/local-subscription-control",
                "workflow_lane": "product_idea_to_spec",
                "governance_profile": "product_workspace",
                "target_repository_role": "product_spec_workspace",
            },
            "source_artifacts": {
                "active_candidate": {"source_ref": ref(paths["repaired_active_candidate"])},
                "promotion_gate": {"source_ref": ref(paths["repaired_promotion_gate"])},
                "rerun_materialization": {"source_ref": ref(paths["rerun_materialization"])},
            },
            "readiness_impact": {
                "ready_for_candidate_approval": True,
                "ready_for_platform_promotion": False,
                "blocked_by": [],
                "promotion_path_count": 1,
                "unresolved_candidate_gap_count": 0,
                "unresolved_ontology_gap_count": 0,
            },
            "summary": {
                "accepted_answer_count": 2,
                "candidate_id": "local-subscription-control",
                "ready_for_candidate_approval": True,
                "ready_for_platform_promotion": False,
                "resolved_candidate_gap_count": 1,
                "resolved_ontology_gap_count": 1,
                "unresolved_candidate_gap_count": 0,
                "unresolved_ontology_gap_count": 0,
                "status": "repair_session_journal_ready",
            },
            "readiness": {"ready": True, "review_state": "repair_session_journal_ready"},
            "authority_boundary": authority_boundary(),
        },
    )
    write_json(
        paths["repaired_handoff"],
        {
            "artifact_kind": "repaired_candidate_promotion_handoff_report",
            "contract_ref": "specgraph.idea-to-spec.repaired-candidate-promotion-handoff.v0.1",
            "schema_version": 1,
            "source_artifacts": {
                "rerun_materialization": {"source_ref": ref(paths["rerun_materialization"])}
            },
            "summary": {
                "ready_for_candidate_approval": True,
                "ready_for_platform_promotion": False,
                "removed_gap_count": 2,
                "resolved_candidate_gap_count": 1,
                "resolved_ontology_gap_count": 1,
                "unresolved_candidate_gap_count": 0,
                "unresolved_ontology_gap_count": 0,
                "status": "repaired_candidate_promotion_handoff_ready",
            },
            "readiness": {
                "ready": True,
                "review_state": "repaired_candidate_promotion_handoff_ready",
            },
            "authority_boundary": authority_boundary(),
        },
    )
    return paths


def build_report(paths: dict[str, Path]) -> dict[str, object]:
    module = load_module()
    return module.build_idea_maturity_metrics_report(paths=paths)


def test_idea_maturity_metrics_report_builds_approval_ready_metrics(tmp_path: Path) -> None:
    paths = write_ready_chain(tmp_path / "ready")

    report = build_report(paths)

    assert report["artifact_kind"] == "idea_maturity_metrics_report"
    assert report["proposal_id"] == "0178"
    assert report["contract_ref"] == "specgraph.idea-to-spec.maturity-metrics-report.v0.1"
    assert report["metric_pack_id"] == "idea_to_spec_maturity"
    assert report["status"] == "ready"
    assert report["derived_state"]["lifecycle_state"] == "approval_ready"
    metrics = report["metrics"]
    assert metrics["clarification_question_count"] == 2
    assert metrics["accepted_answer_count"] == 2
    assert metrics["materialized_answer_count"] == 2
    assert metrics["answer_materialization_rate"] == 1.0
    assert metrics["ontology_gap_count_initial"] == 1
    assert metrics["ontology_gap_resolved_count"] == 1
    assert metrics["ontology_match_kind_counts"]["exact"] == 1
    assert metrics["candidate_gap_count_initial"] == 1
    assert metrics["candidate_gap_resolved_count"] == 1
    assert metrics["candidate_resolution_kind_counts"]["risk_accepted"] == 1
    assert metrics["candidate_approval_state"] == "ready"
    assert metrics["platform_promotion_state"] == "not_reached"
    assert metrics["promotion_path_count"] == 1
    assert report["authority_boundary"] == authority_boundary()
    assert report["privacy_boundary"]["join_to_identity_allowed"] is False


def test_idea_maturity_metrics_report_preserves_zero_denominator_rates(
    tmp_path: Path,
) -> None:
    paths = write_ready_chain(tmp_path / "zero")
    candidate_graph = load_json(paths["candidate_graph"])
    candidate_graph["nodes"][0]["gaps"] = []
    write_json(paths["candidate_graph"], candidate_graph)
    answers = load_json(paths["clarification_answers"])
    answers["answers"] = []
    answers["summary"]["answer_count"] = 0
    answers["summary"]["accepted_answer_count"] = 0
    write_json(paths["clarification_answers"], answers)
    materialization = load_json(paths["rerun_materialization"])
    materialization["materialization_preview"]["delta"] = {
        "ontology_resolution_records": [],
        "candidate_resolution_records": [],
    }
    materialization["summary"].update(
        {
            "resolved_candidate_gap_count": 0,
            "resolved_ontology_gap_count": 0,
            "unresolved_candidate_gap_count": 0,
            "unresolved_ontology_gap_count": 0,
        }
    )
    write_json(paths["rerun_materialization"], materialization)
    handoff = load_json(paths["repaired_handoff"])
    handoff["summary"].update(
        {
            "resolved_candidate_gap_count": 0,
            "resolved_ontology_gap_count": 0,
            "unresolved_candidate_gap_count": 0,
            "unresolved_ontology_gap_count": 0,
        }
    )
    write_json(paths["repaired_handoff"], handoff)

    report = build_report(paths)

    metrics = report["metrics"]
    assert metrics["answer_materialization_rate"] is None
    assert metrics["ontology_gap_resolution_rate"] is None
    assert metrics["candidate_gap_closure_rate"] is None


def test_idea_maturity_metrics_report_flags_stale_source_refs_as_blocked(
    tmp_path: Path,
) -> None:
    paths = write_ready_chain(tmp_path / "stale", stale_rerun_ref=True)

    report = build_report(paths)

    assert report["status"] == "blocked"
    assert report["metrics"]["stale_ref_count"] == 1
    assert "rerun_materialization_rerun_preview_source_ref_stale" in {
        finding["finding_id"] for finding in report["policy_findings"]
    }


def test_idea_maturity_metrics_report_strict_fails_on_invariant_violation(
    tmp_path: Path,
) -> None:
    paths = write_ready_chain(tmp_path / "invalid")
    materialization = load_json(paths["rerun_materialization"])
    materialization["summary"]["resolved_candidate_gap_count"] = 2
    write_json(paths["rerun_materialization"], materialization)
    handoff = load_json(paths["repaired_handoff"])
    handoff["summary"]["resolved_candidate_gap_count"] = 2
    write_json(paths["repaired_handoff"], handoff)
    output = tmp_path / "idea_maturity_metrics_report.json"

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--intake",
            str(paths["intake"]),
            "--candidate-graph",
            str(paths["candidate_graph"]),
            "--clarification-requests",
            str(paths["clarification_requests"]),
            "--clarification-answers",
            str(paths["clarification_answers"]),
            "--ontology-decisions",
            str(paths["ontology_decisions"]),
            "--rerun-input",
            str(paths["rerun_input"]),
            "--rerun-preview",
            str(paths["rerun_preview"]),
            "--rerun-materialization",
            str(paths["rerun_materialization"]),
            "--repaired-handoff",
            str(paths["repaired_handoff"]),
            "--repaired-candidate-graph",
            str(paths["repaired_candidate_graph"]),
            "--repaired-active-candidate",
            str(paths["repaired_active_candidate"]),
            "--repaired-promotion-gate",
            str(paths["repaired_promotion_gate"]),
            "--repaired-repair-session",
            str(paths["repaired_repair_session"]),
            "--output",
            str(output),
            "--strict",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    report = load_json(output)
    assert report["status"] == "blocked"
    assert "invariant_candidate_gap_resolved_bounds" in {
        finding["finding_id"] for finding in report["invariant_findings"]
    }


def test_idea_maturity_metrics_make_target_threads_paths(tmp_path: Path) -> None:
    paths = write_ready_chain(tmp_path / "make")
    output = tmp_path / "make" / "idea_maturity_metrics_report.json"
    make_args = [
        "make",
        "idea-maturity-metrics",
        f"IDEA_MATURITY_METRICS_INTAKE={paths['intake']}",
        f"IDEA_MATURITY_METRICS_CANDIDATE_GRAPH={paths['candidate_graph']}",
        f"IDEA_MATURITY_METRICS_CLARIFICATION_REQUESTS={paths['clarification_requests']}",
        f"IDEA_MATURITY_METRICS_CLARIFICATION_ANSWERS={paths['clarification_answers']}",
        f"IDEA_MATURITY_METRICS_ONTOLOGY_DECISIONS={paths['ontology_decisions']}",
        f"IDEA_MATURITY_METRICS_RERUN_INPUT={paths['rerun_input']}",
        f"IDEA_MATURITY_METRICS_RERUN_PREVIEW={paths['rerun_preview']}",
        f"IDEA_MATURITY_METRICS_RERUN_MATERIALIZATION={paths['rerun_materialization']}",
        f"IDEA_MATURITY_METRICS_REPAIRED_HANDOFF={paths['repaired_handoff']}",
        f"IDEA_MATURITY_METRICS_REPAIRED_CANDIDATE_GRAPH={paths['repaired_candidate_graph']}",
        f"IDEA_MATURITY_METRICS_REPAIRED_ACTIVE_CANDIDATE={paths['repaired_active_candidate']}",
        f"IDEA_MATURITY_METRICS_REPAIRED_PROMOTION_GATE={paths['repaired_promotion_gate']}",
        f"IDEA_MATURITY_METRICS_REPAIRED_REPAIR_SESSION={paths['repaired_repair_session']}",
        f"IDEA_MATURITY_METRICS_OUTPUT={output}",
    ]

    result = subprocess.run(
        make_args,
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    report = load_json(output)
    assert report["status"] == "ready"
    assert report["source_artifacts"]["candidate_graph"]["source_ref"] == str(
        paths["candidate_graph"]
    )
