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
        "pre_sib": run_dir / "pre_sib_coherence_report.json",
        "clarification_requests": run_dir / "idea_to_spec_clarification_requests.json",
        "clarification_answers": run_dir / "idea_to_spec_clarification_answers.json",
        "ontology_decisions": run_dir / "product_ontology_gap_review_decisions.json",
        "rerun_input": run_dir / "idea_to_spec_answer_rerun_input.json",
        "rerun_preview": run_dir / "idea_to_spec_rerun_preview.json",
        "rerun_materialization": run_dir / "idea_to_spec_rerun_materialization.json",
        "promotion_gate": run_dir / "idea_to_spec_promotion_gate.json",
        "repair_session": run_dir / "idea_to_spec_repair_session.json",
        "repaired_handoff": run_dir / "repaired_candidate_promotion_handoff_report.json",
        "repaired_candidate_graph": run_dir / "repaired_candidate_spec_graph.json",
        "repaired_pre_sib": run_dir / "repaired_pre_sib_coherence_report.json",
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
        "candidate_approval_decision": run_dir / "candidate_approval_decision.json",
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
        paths["pre_sib"],
        {
            "artifact_kind": "pre_sib_coherence_report",
            "contract_ref": "specgraph.idea-to-spec.pre-sib-coherence-report.v0.1",
            "schema_version": 1,
            "generated_at": "2026-06-28T10:01:30+00:00",
            "metrics": {
                "node_count": 1,
                "gap_count": 2,
            },
            "findings": [],
            "warnings": [],
            "readiness": {"ready": True, "review_state": "pre_sib_ready"},
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
        paths["repaired_pre_sib"],
        {
            "artifact_kind": "pre_sib_coherence_report",
            "contract_ref": "specgraph.idea-to-spec.pre-sib-coherence-report.v0.1",
            "schema_version": 1,
            "generated_at": "2026-06-28T10:05:30+00:00",
            "metrics": {
                "node_count": 1,
                "gap_count": 0,
            },
            "findings": [],
            "warnings": [],
            "readiness": {"ready": True, "review_state": "pre_sib_ready"},
            "authority_boundary": authority_boundary(),
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


def tool_args(paths: dict[str, Path], output: Path, *, strict: bool = False) -> list[str]:
    args = [
        sys.executable,
        str(TOOL_PATH),
        "--intake",
        str(paths["intake"]),
        "--candidate-graph",
        str(paths["candidate_graph"]),
        "--pre-sib",
        str(paths["pre_sib"]),
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
        "--promotion-gate",
        str(paths["promotion_gate"]),
        "--repair-session",
        str(paths["repair_session"]),
        "--repaired-handoff",
        str(paths["repaired_handoff"]),
        "--repaired-candidate-graph",
        str(paths["repaired_candidate_graph"]),
        "--repaired-pre-sib",
        str(paths["repaired_pre_sib"]),
        "--repaired-active-candidate",
        str(paths["repaired_active_candidate"]),
        "--repaired-promotion-gate",
        str(paths["repaired_promotion_gate"]),
        "--repaired-repair-session",
        str(paths["repaired_repair_session"]),
        "--candidate-approval-decision",
        str(paths["candidate_approval_decision"]),
        "--output",
        str(output),
    ]
    if strict:
        args.append("--strict")
    return args


def test_idea_maturity_metrics_report_builds_approval_ready_metrics(tmp_path: Path) -> None:
    paths = write_ready_chain(tmp_path / "ready")

    report = build_report(paths)

    assert report["artifact_kind"] == "idea_maturity_metrics_report"
    assert report["proposal_id"] == "0178"
    assert report["contract_ref"] == "specgraph.idea-to-spec.maturity-metrics-report.v0.1"
    assert report["contract"] == {
        "schema_version": 1,
        "schema_ref": "schemas/idea_maturity_metrics_report.schema.json",
        "validation_report_schema_ref": (
            "schemas/idea_maturity_metrics_validation_report.schema.json"
        ),
        "validator_id": "metrics.idea_maturity_metrics.validator.v0.1",
        "validator_version": "0.1.0",
        "compatibility_policy": "additive_v1",
        "compatibility_policy_ref": "VALIDATOR_CONTRACT.md#compatibility-policy",
        "metrics_rfc_ref": "Metrics/IDEA_MATURITY_METRICS.md",
        "proposal_id": "0181",
    }
    assert report["metric_pack_id"] == "idea_to_spec_maturity"
    assert report["authority_state"] == "draft_reference"
    assert report["status"] == "ready"
    assert report["derived_state"]["lifecycle_state"] == "approval_ready"
    assert report["summary"]["lifecycle_state"] == "approval_ready"
    assert "candidate_id" not in report["summary"]
    assert "status" not in report["summary"]
    assert "display_name" not in report["candidate"]
    metrics = report["metrics"]
    assert metrics["clarification_question_count"] == 2
    assert metrics["accepted_answer_count"] == 2
    assert metrics["materialized_answer_count"] == 2
    assert metrics["answer_materialization_rate"] == 1.0
    assert metrics["ontology_gap_count_initial"] == 1
    assert metrics["ontology_gap_resolved_count"] == 1
    assert metrics["ontology_match_kind_counts"]["exact"] == 1
    assert report["groups"]["ontology_grounding"]["ontology_match_kind_counts"]["exact"] == 1
    assert metrics["candidate_gap_count_initial"] == 1
    assert metrics["candidate_gap_resolved_count"] == 1
    assert metrics["candidate_resolution_kind_counts"]["risk_accepted"] == 1
    assert (
        report["groups"]["candidate_repair"]["candidate_resolution_kind_counts"]["risk_accepted"]
        == 1
    )
    assert metrics["candidate_approval_state"] == "ready"
    assert metrics["platform_promotion_state"] == "not_reached"
    assert metrics["promotion_path_count"] == 1
    assert report["authority_boundary"] == authority_boundary()
    assert report["privacy_boundary"]["join_to_identity_allowed"] is False
    assert isinstance(report["source_artifacts"], list)
    assert "source_artifact_details" in report
    assert report["readiness_explainers"] == []
    assert report["specgraph_summary"]["readiness_explainer_count"] == 0


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
    assert any(
        explainer["kind"] == "stale_ref"
        and "candidate_approval" in explainer["blocks"]
        and explainer["next_action"]
        for explainer in report["readiness_explainers"]
    )


def test_idea_maturity_metrics_report_emits_pre_sib_readiness_explainers(
    tmp_path: Path,
) -> None:
    paths = write_ready_chain(tmp_path / "pre-sib-blocked")
    paths["repaired_pre_sib"].unlink()
    pre_sib = load_json(paths["pre_sib"])
    pre_sib["findings"] = [
        {
            "finding_id": "pre_sib_ontology_coverage_gap",
            "severity": "high",
            "message": "Ontology coverage is incomplete for the candidate graph.",
        }
    ]
    pre_sib["readiness"] = {
        "ready": False,
        "review_state": "pre_sib_review_required",
        "blocked_by": ["pre_sib_ontology_coverage_gap"],
    }
    write_json(paths["pre_sib"], pre_sib)

    report = build_report(paths)

    explainers = report["readiness_explainers"]
    pre_sib_explainer = next(item for item in explainers if item["kind"] == "pre_sib_finding")
    assert pre_sib_explainer["source"] == "pre_sib"
    assert pre_sib_explainer["severity"] == "high"
    assert "candidate_approval" in pre_sib_explainer["blocks"]
    assert pre_sib_explainer["next_action"].startswith("Inspect Pre-SIB")
    assert pre_sib_explainer["evidence_refs"] == [
        f"{paths['pre_sib'].as_posix()}#findings.pre-sib-ontology-coverage-gap"
    ]


def test_idea_maturity_metrics_report_normalizes_readiness_explainer_severity(
    tmp_path: Path,
) -> None:
    paths = write_ready_chain(tmp_path / "severity-normalization")
    paths["repaired_pre_sib"].unlink()
    pre_sib = load_json(paths["pre_sib"])
    pre_sib["findings"] = [
        {
            "finding_id": "pre_sib_warning_gap",
            "severity": "warning",
            "message": "Warning severity comes from a source report.",
        }
    ]
    pre_sib["readiness"] = {
        "ready": False,
        "review_state": "pre_sib_review_required",
        "blocked_by": ["pre_sib_warning_gap"],
    }
    write_json(paths["pre_sib"], pre_sib)

    report = build_report(paths)

    severities = {item["id"]: item["severity"] for item in report["readiness_explainers"]}
    assert set(severities.values()) <= {"low", "medium", "high"}
    assert severities["readiness-explainer.pre-sib-pre-sib-warning-gap"] == "medium"
    assert severities["readiness-explainer.pre-sib-blocker-pre-sib-warning-gap"] == "high"


def test_idea_maturity_metrics_report_uses_repaired_pre_sib_as_current_surface(
    tmp_path: Path,
) -> None:
    paths = write_ready_chain(tmp_path / "repaired-pre-sib")
    pre_sib = load_json(paths["pre_sib"])
    pre_sib["findings"] = [
        {
            "finding_id": "pre_sib_old_gap",
            "severity": "high",
            "message": "Old Pre-SIB gap was present before repair.",
        }
    ]
    pre_sib["readiness"] = {
        "ready": False,
        "review_state": "pre_sib_review_required",
        "blocked_by": ["pre_sib_old_gap"],
    }
    write_json(paths["pre_sib"], pre_sib)

    report = build_report(paths)

    assert report["status"] == "ready"
    assert report["metrics"]["failed_gate_count"] == 0
    assert report["readiness_explainers"] == []


def test_idea_maturity_metrics_report_emits_repair_and_promotion_explainers(
    tmp_path: Path,
) -> None:
    paths = write_ready_chain(tmp_path / "repair-promotion-blocked")
    repair_session = load_json(paths["repaired_repair_session"])
    repair_session["readiness_impact"]["ready_for_candidate_approval"] = False
    repair_session["readiness_impact"]["blocked_by"] = ["repair_context_required"]
    repair_session["readiness_impact"]["platform_promotion_blocked_by"] = [
        "candidate_approval_decision_missing"
    ]
    repair_session["summary"]["ready_for_candidate_approval"] = False
    write_json(paths["repaired_repair_session"], repair_session)
    promotion_gate = load_json(paths["repaired_promotion_gate"])
    promotion_gate["readiness"] = {
        "ready": False,
        "review_state": "promotion_gate_blocked",
        "blocked_by": ["promotion_path_missing"],
    }
    promotion_gate["summary"]["status"] = "promotion_gate_blocked"
    write_json(paths["repaired_promotion_gate"], promotion_gate)

    report = build_report(paths)

    explainers = report["readiness_explainers"]
    assert any(
        item["kind"] == "repair_session_blocker"
        and item["source"] == "repaired_repair_session"
        and item["blocks"] == ["candidate_approval"]
        for item in explainers
    )
    assert any(
        item["kind"] == "platform_promotion_blocker" and item["blocks"] == ["platform_promotion"]
        for item in explainers
    )
    assert any(
        item["kind"] == "promotion_gate_blocker" and item["source"] == "repaired_promotion_gate"
        for item in explainers
    )


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
        tool_args(paths, output, strict=True),
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
    absent = tmp_path / "make" / "absent"
    make_args = [
        "make",
        "idea-maturity-metrics",
        f"IDEA_MATURITY_METRICS_INTAKE={paths['intake']}",
        f"IDEA_MATURITY_METRICS_CANDIDATE_GRAPH={paths['candidate_graph']}",
        f"IDEA_MATURITY_METRICS_PRE_SIB={paths['pre_sib']}",
        f"IDEA_MATURITY_METRICS_CLARIFICATION_REQUESTS={paths['clarification_requests']}",
        f"IDEA_MATURITY_METRICS_CLARIFICATION_ANSWERS={paths['clarification_answers']}",
        f"IDEA_MATURITY_METRICS_ONTOLOGY_DECISIONS={paths['ontology_decisions']}",
        f"IDEA_MATURITY_METRICS_RERUN_INPUT={paths['rerun_input']}",
        f"IDEA_MATURITY_METRICS_RERUN_PREVIEW={paths['rerun_preview']}",
        f"IDEA_MATURITY_METRICS_RERUN_MATERIALIZATION={paths['rerun_materialization']}",
        f"IDEA_MATURITY_METRICS_PROMOTION_GATE={paths['promotion_gate']}",
        f"IDEA_MATURITY_METRICS_REPAIR_SESSION={paths['repair_session']}",
        f"IDEA_MATURITY_METRICS_REPAIRED_HANDOFF={paths['repaired_handoff']}",
        f"IDEA_MATURITY_METRICS_REPAIRED_CANDIDATE_GRAPH={paths['repaired_candidate_graph']}",
        f"IDEA_MATURITY_METRICS_REPAIRED_PRE_SIB={paths['repaired_pre_sib']}",
        f"IDEA_MATURITY_METRICS_REPAIRED_ACTIVE_CANDIDATE={paths['repaired_active_candidate']}",
        f"IDEA_MATURITY_METRICS_REPAIRED_PROMOTION_GATE={paths['repaired_promotion_gate']}",
        f"IDEA_MATURITY_METRICS_REPAIRED_REPAIR_SESSION={paths['repaired_repair_session']}",
        (
            "IDEA_MATURITY_METRICS_SPECSPACE_DRAFT_IMPORT_PREVIEW="
            f"{absent / 'specspace_repair_draft_import_preview.json'}"
        ),
        (
            "IDEA_MATURITY_METRICS_SPECSPACE_RERUN_REQUEST="
            f"{absent / 'idea_to_spec_repair_rerun_requests.json'}"
        ),
        (
            "IDEA_MATURITY_METRICS_APPROVAL_INTENT="
            f"{absent / 'idea_to_spec_candidate_approval_intents.json'}"
        ),
        (
            "IDEA_MATURITY_METRICS_REPAIR_RERUN_EXECUTION="
            f"{absent / 'platform_product_repair_rerun_execution_report.json'}"
        ),
        (
            "IDEA_MATURITY_METRICS_REPAIR_RERUN_PUBLICATION="
            f"{absent / 'platform_product_repair_rerun_publication_report.json'}"
        ),
        (
            "IDEA_MATURITY_METRICS_APPROVAL_EXECUTION="
            f"{absent / 'platform_candidate_approval_execution_report.json'}"
        ),
        f"IDEA_MATURITY_METRICS_CANDIDATE_APPROVAL_DECISION={paths['candidate_approval_decision']}",
        (
            "IDEA_MATURITY_METRICS_PROMOTION_REQUEST="
            f"{absent / 'graph_repository_promotion_request.json'}"
        ),
        (
            "IDEA_MATURITY_METRICS_PROMOTION_EXECUTION="
            f"{absent / 'product_candidate_promotion_execution_report.json'}"
        ),
        (
            "IDEA_MATURITY_METRICS_REVIEW_STATUS="
            f"{absent / 'product_candidate_promotion_review_status_report.json'}"
        ),
        (
            "IDEA_MATURITY_METRICS_READ_MODEL_PUBLICATION="
            f"{absent / 'product_candidate_promotion_read_model_publication_report.json'}"
        ),
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
    assert report["source_artifact_details"]["candidate_graph"]["source_ref"] == str(
        paths["candidate_graph"]
    )


def test_idea_maturity_metrics_validate_make_target_invokes_metrics_cli(
    tmp_path: Path,
) -> None:
    paths = write_ready_chain(tmp_path / "validate")
    report_output = tmp_path / "validate" / "idea_maturity_metrics_report.json"
    validation_output = tmp_path / "validate" / "idea_maturity_metrics_validation_report.json"
    fake_cli = tmp_path / "fake_metrics_cli.py"
    trace = tmp_path / "fake_metrics_cli_args.json"
    fake_cli.write_text(
        "\n".join(
            [
                "import json",
                "import sys",
                "from pathlib import Path",
                f"Path({str(trace)!r}).write_text(json.dumps(sys.argv[1:]), encoding='utf-8')",
                "args = sys.argv[1:]",
                "output = Path(args[args.index('--output') + 1])",
                "output.parent.mkdir(parents=True, exist_ok=True)",
                "output.write_text(json.dumps({",
                "  'artifact_kind': 'idea_maturity_metrics_validation_report',",
                "  'metric_pack_id': 'idea_to_spec_maturity',",
                "  'summary': {",
                "    'status': 'ok',",
                "    'report_count': 1,",
                "    'valid_count': 1,",
                "    'invalid_count': 0,",
                "  },",
                "  'reports': [{'path': args[2], 'status': 'ok', 'diagnostics': []}],",
                "}), encoding='utf-8')",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    build_result = subprocess.run(
        tool_args(paths, report_output),
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert build_result.returncode == 0, build_result.stderr

    result = subprocess.run(
        [
            "make",
            "idea-maturity-metrics-validate",
            f"IDEA_MATURITY_METRICS_OUTPUT={report_output}",
            f"IDEA_MATURITY_METRICS_VALIDATION_OUTPUT={validation_output}",
            f"METRICS_CLI={sys.executable} {fake_cli}",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    args = json.loads(trace.read_text(encoding="utf-8"))
    assert args == [
        "validate",
        "idea-maturity",
        str(report_output),
        "--output",
        str(validation_output),
    ]
    validation = load_json(validation_output)
    assert validation["artifact_kind"] == "idea_maturity_metrics_validation_report"
    assert validation["summary"]["status"] == "ok"


def _make_dry_run_target(target: str) -> str:
    result = subprocess.run(
        ["make", "-n", target],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return result.stdout


def _write_fake_metrics_cli(path: Path, trace: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "import json",
                "import sys",
                "from pathlib import Path",
                f"Path({str(trace)!r}).write_text(json.dumps(sys.argv[1:]), encoding='utf-8')",
                "args = sys.argv[1:]",
                "output = Path(args[args.index('--output') + 1])",
                "output.parent.mkdir(parents=True, exist_ok=True)",
                "output.write_text(json.dumps({",
                "  'artifact_kind': 'idea_maturity_metrics_validation_report',",
                "  'metric_pack_id': 'idea_to_spec_maturity',",
                "  'summary': {",
                "    'status': 'ok',",
                "    'report_count': 1,",
                "    'valid_count': 1,",
                "    'invalid_count': 0,",
                "  },",
                "  'reports': [{'path': args[2], 'status': 'ok', 'diagnostics': []}],",
                "}), encoding='utf-8')",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def test_product_workspace_idea_maturity_target_builds_and_validates_report() -> None:
    output = _make_dry_run_target("product-workspace-idea-maturity")

    metrics_index = output.index("tools/idea_maturity_metrics_report.py")
    validation_index = output.index("validate idea-maturity")
    assert metrics_index < validation_index
    assert "runs/idea_maturity_metrics_report.json" in output
    assert "runs/idea_maturity_metrics_validation_report.json" in output


def test_real_idea_smoke_idea_maturity_target_isolates_run_dir_optional_artifacts() -> None:
    output = _make_dry_run_target("real-idea-smoke-idea-maturity")

    assert "runs/real_idea_smoke/idea_event_storming_intake.json" in output
    assert "runs/real_idea_smoke/idea_maturity_metrics_report.json" in output
    assert "runs/real_idea_smoke/idea_maturity_metrics_validation_report.json" in output
    assert "runs/real_idea_smoke/specspace_repair_draft_import_preview.json" in output
    assert "runs/real_idea_smoke/idea_to_spec_repair_rerun_requests.json" in output
    assert "runs/real_idea_smoke/absent-post-approval/candidate_approval_decision.json" in output
    assert "shutil.rmtree(absent, ignore_errors=True)" in output
    assert '--candidate-approval-decision "runs/candidate_approval_decision.json"' not in output
    assert '--promotion-request "runs/graph_repository_promotion_request.json"' not in output


def test_real_idea_smoke_idea_maturity_clears_stale_absent_dir(
    tmp_path: Path,
) -> None:
    run_dir = tmp_path / "smoke"
    absent_dir = run_dir / "absent-post-approval"
    paths = write_ready_chain(run_dir)
    stale_decision = absent_dir / "candidate_approval_decision.json"
    write_json(
        stale_decision,
        {
            "artifact_kind": "candidate_approval_decision",
            "summary": {"status": "candidate_approved", "effective_state": "approved"},
            "decision": {"state": "approved"},
            "readiness": {"ready": True},
            "authority_boundary": authority_boundary(),
        },
    )
    fake_cli = tmp_path / "fake_metrics_cli.py"
    trace = tmp_path / "fake_metrics_cli_args.json"
    _write_fake_metrics_cli(fake_cli, trace)

    result = subprocess.run(
        [
            "make",
            "real-idea-smoke-idea-maturity",
            f"REAL_IDEA_SMOKE_RUN_DIR={run_dir}",
            f"METRICS_CLI={sys.executable} {fake_cli}",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert not stale_decision.exists()
    report = load_json(paths["approval_intent"].parent / "idea_maturity_metrics_report.json")
    assert report["metrics"]["candidate_approval_state"] == "ready"
    assert report["metrics"]["candidate_approval_decision_state"] == "not_reached"
    assert report["derived_state"]["lifecycle_state"] == "approval_ready"


def test_decision_backed_repair_chain_emits_validated_idea_maturity() -> None:
    output = _make_dry_run_target("product-workspace-decision-backed-repair-chain")

    session_index = output.index("idea_to_spec_repair_session_journal.py")
    metrics_index = output.index("tools/idea_maturity_metrics_report.py")
    validation_index = output.index("validate idea-maturity")
    assert session_index < metrics_index < validation_index


def test_repaired_promotion_handoff_emits_validated_idea_maturity() -> None:
    output = _make_dry_run_target("product-workspace-repaired-promotion-handoff")

    handoff_index = output.index("tools/repaired_candidate_promotion_handoff.py")
    metrics_index = output.index("tools/idea_maturity_metrics_report.py")
    validation_index = output.index("validate idea-maturity")
    assert handoff_index < metrics_index < validation_index


def test_idea_maturity_metrics_report_counts_materialized_request_once(
    tmp_path: Path,
) -> None:
    paths = write_ready_chain(tmp_path / "combined")
    answers = load_json(paths["clarification_answers"])
    answers["answers"] = [
        {
            "request_id": "clarification.combined",
            "answer_kind": "provide_candidate_context",
            "status": "accepted_for_candidate",
        }
    ]
    answers["summary"]["answer_count"] = 1
    answers["summary"]["accepted_answer_count"] = 1
    write_json(paths["clarification_answers"], answers)
    materialization = load_json(paths["rerun_materialization"])
    delta = materialization["materialization_preview"]["delta"]
    delta["ontology_resolution_records"][0]["request_id"] = "clarification.combined"
    delta["candidate_resolution_records"][0]["request_id"] = "clarification.combined"
    write_json(paths["rerun_materialization"], materialization)

    report = build_report(paths)

    assert report["metrics"]["accepted_answer_count"] == 1
    assert report["metrics"]["materialized_answer_count"] == 1
    assert report["summary"]["materialized_answer_count"] == 1
    assert report["summary"]["answer_materialization_rate"] == 1.0


def test_idea_maturity_metrics_report_accounts_aggregate_answer_closure(
    tmp_path: Path,
) -> None:
    paths = write_ready_chain(tmp_path / "aggregate-answer")
    answers = load_json(paths["clarification_answers"])
    answers["answers"].append(
        {
            "request_id": "clarification.active-frame",
            "answer_kind": "answer_question",
            "status": "accepted_for_candidate",
            "request_snapshot": {
                "kind": "active_frame",
                "target_artifact": "idea_event_storming_intake",
                "target_ref": "active_frame.domain",
            },
        }
    )
    answers["summary"]["answer_count"] = 3
    answers["summary"]["accepted_answer_count"] = 3
    write_json(paths["clarification_answers"], answers)
    rerun_input = load_json(paths["rerun_input"])
    rerun_input["rerun_input_overlay"] = {
        "intake_overlay": {
            "active_frame_hints": [
                {
                    "request_id": "clarification.active-frame",
                    "answer_kind": "answer_question",
                    "request_kind": "active_frame",
                    "target_artifact": "idea_event_storming_intake",
                    "target_ref": "active_frame.domain",
                    "value": {"domain": "cash_flow_control"},
                }
            ],
            "event_storming_hints": [],
        },
        "ontology_review_hints": {
            "term_bindings": [],
            "aliases": [],
            "project_local_terms": [],
            "rejected_terms": [],
            "deferred_terms": [],
        },
        "candidate_review_hints": {
            "acceptance_criteria": [],
            "graph_edges": [],
            "claim_reviews": [],
            "other": [],
        },
    }
    rerun_input["summary"]["accepted_answer_count"] = 3
    rerun_input["summary"]["intake_overlay_count"] = 1
    write_json(paths["rerun_input"], rerun_input)

    report = build_report(paths)
    metrics = report["metrics"]
    group = report["groups"]["answer_materialization"]

    assert metrics["accepted_answer_count"] == 3
    assert metrics["per_gap_materialized_answer_count"] == 2
    assert metrics["aggregate_answer_count"] == 1
    assert metrics["closure_evidence_answer_count"] == 3
    assert metrics["unmaterialized_answer_count"] == 0
    assert metrics["answer_materialization_rate"] == 1.0
    assert group["ordinary_unmaterialized_answer_count"] == 0
    assert group["answer_accounting"]["aggregate_answer_request_ids"] == [
        "clarification.active-frame"
    ]


def test_idea_maturity_metrics_rate_does_not_exceed_one_on_summary_mismatch(
    tmp_path: Path,
) -> None:
    paths = write_ready_chain(tmp_path / "summary-mismatch")
    answers = load_json(paths["clarification_answers"])
    answers["summary"]["accepted_answer_count"] = 1
    write_json(paths["clarification_answers"], answers)

    report = build_report(paths)
    metrics = report["metrics"]

    assert metrics["accepted_answer_count"] == 2
    assert metrics["closure_evidence_answer_count"] == 2
    assert metrics["answer_materialization_rate"] == 1.0
    assert metrics["answer_accounting"]["accepted_answer_count"] == metrics["accepted_answer_count"]


def test_idea_maturity_metrics_keeps_unconfirmed_reject_as_answer_debt(
    tmp_path: Path,
) -> None:
    paths = write_ready_chain(tmp_path / "unconfirmed-dismissed-answer")
    answers = load_json(paths["clarification_answers"])
    answers["answers"].append(
        {
            "request_id": "clarification.reject-local-risk",
            "answer_kind": "reject",
            "status": "accepted_for_candidate",
            "request_snapshot": {
                "kind": "candidate_gap",
                "target_ref": "candidate-spec.product-boundary#gap.local-risk",
            },
        }
    )
    answers["summary"]["answer_count"] = 3
    answers["summary"]["accepted_answer_count"] = 3
    write_json(paths["clarification_answers"], answers)
    rerun_input = load_json(paths["rerun_input"])
    rerun_input["rerun_input_overlay"] = {
        "intake_overlay": {
            "active_frame_hints": [],
            "event_storming_hints": [],
        },
        "ontology_review_hints": {
            "term_bindings": [],
            "aliases": [],
            "project_local_terms": [],
            "rejected_terms": [],
            "deferred_terms": [],
        },
        "candidate_review_hints": {
            "acceptance_criteria": [],
            "graph_edges": [],
            "claim_reviews": [],
            "other": [
                {
                    "request_id": "clarification.reject-local-risk",
                    "answer_kind": "reject",
                    "request_kind": "candidate_gap",
                    "target_ref": "candidate-spec.product-boundary#gap.local-risk",
                }
            ],
        },
    }
    write_json(paths["rerun_input"], rerun_input)

    report = build_report(paths)
    metrics = report["metrics"]

    assert metrics["dismissed_answer_count"] == 0
    assert metrics["closure_evidence_answer_count"] == 2
    assert metrics["answer_materialization_rate"] == 0.666667
    assert metrics["ordinary_unmaterialized_answer_count"] == 1
    assert metrics["answer_accounting"]["dismissed_answer_request_ids"] == []


def test_idea_maturity_metrics_counts_confirmed_reject_as_dismissed_not_closure(
    tmp_path: Path,
) -> None:
    paths = write_ready_chain(tmp_path / "confirmed-dismissed-answer")
    answers = load_json(paths["clarification_answers"])
    answers["answers"].append(
        {
            "request_id": "clarification.reject-local-risk",
            "answer_kind": "reject",
            "status": "accepted_for_candidate",
            "request_snapshot": {
                "kind": "candidate_gap",
                "target_ref": "candidate-spec.product-boundary#gap.local-risk",
            },
        }
    )
    answers["summary"]["answer_count"] = 3
    answers["summary"]["accepted_answer_count"] = 3
    write_json(paths["clarification_answers"], answers)
    rerun_input = load_json(paths["rerun_input"])
    rerun_input["rerun_input_overlay"] = {
        "intake_overlay": {
            "active_frame_hints": [],
            "event_storming_hints": [],
        },
        "ontology_review_hints": {
            "term_bindings": [],
            "aliases": [],
            "project_local_terms": [],
            "rejected_terms": [],
            "deferred_terms": [],
        },
        "candidate_review_hints": {
            "acceptance_criteria": [],
            "graph_edges": [],
            "claim_reviews": [],
            "other": [
                {
                    "request_id": "clarification.reject-local-risk",
                    "answer_kind": "reject",
                    "request_kind": "candidate_gap",
                    "target_ref": "candidate-spec.product-boundary#gap.local-risk",
                }
            ],
        },
    }
    write_json(paths["rerun_input"], rerun_input)
    materialization = load_json(paths["rerun_materialization"])
    materialization["materialization_preview"]["delta"]["candidate_resolution_records"].append(
        {
            "gap_id": "gap.local-risk",
            "match_kind": "target_ref",
            "request_id": "clarification.reject-local-risk",
            "resolution_kind": "rejected",
        }
    )
    write_json(paths["rerun_materialization"], materialization)

    report = build_report(paths)
    metrics = report["metrics"]

    assert metrics["dismissed_answer_count"] == 1
    assert metrics["closure_evidence_answer_count"] == 2
    assert metrics["answer_materialization_rate"] == 0.666667
    assert metrics["ordinary_unmaterialized_answer_count"] == 0
    assert metrics["answer_accounting"]["dismissed_answer_request_ids"] == [
        "clarification.reject-local-risk"
    ]


def test_idea_maturity_metrics_treats_aggregate_gap_target_as_closure(
    tmp_path: Path,
) -> None:
    paths = write_ready_chain(tmp_path / "aggregate-gap-target")
    answers = load_json(paths["clarification_answers"])
    answers["answers"].append(
        {
            "request_id": "clarification.all-ontology-gaps",
            "answer_kind": "propose_project_local_term",
            "status": "accepted_for_candidate",
            "request_snapshot": {
                "kind": "ontology_gap",
                "target_ref": "candidate_graph.gaps",
            },
        }
    )
    answers["summary"]["answer_count"] = 3
    answers["summary"]["accepted_answer_count"] = 3
    write_json(paths["clarification_answers"], answers)
    rerun_input = load_json(paths["rerun_input"])
    rerun_input["rerun_input_overlay"] = {
        "intake_overlay": {
            "active_frame_hints": [],
            "event_storming_hints": [],
        },
        "ontology_review_hints": {
            "term_bindings": [],
            "aliases": [],
            "project_local_terms": [
                {
                    "request_id": "clarification.all-ontology-gaps",
                    "answer_kind": "propose_project_local_term",
                    "request_kind": "ontology_gap",
                    "target_ref": "candidate_graph.gaps",
                }
            ],
            "rejected_terms": [],
            "deferred_terms": [],
        },
        "candidate_review_hints": {
            "acceptance_criteria": [],
            "graph_edges": [],
            "claim_reviews": [],
            "other": [],
        },
    }
    write_json(paths["rerun_input"], rerun_input)

    report = build_report(paths)
    metrics = report["metrics"]

    assert metrics["aggregate_answer_count"] == 1
    assert metrics["closure_evidence_answer_count"] == 3
    assert metrics["ordinary_unmaterialized_answer_count"] == 0


def test_idea_maturity_metrics_does_not_treat_deferral_as_closure(
    tmp_path: Path,
) -> None:
    paths = write_ready_chain(tmp_path / "deferred-answer")
    answers = load_json(paths["clarification_answers"])
    answers["answers"].append(
        {
            "request_id": "clarification.defer-risk",
            "answer_kind": "defer",
            "status": "accepted_for_candidate",
            "request_snapshot": {
                "kind": "candidate_gap",
                "target_ref": "candidate-spec.product-boundary#gap.local-risk",
            },
        }
    )
    answers["summary"]["answer_count"] = 3
    answers["summary"]["accepted_answer_count"] = 3
    write_json(paths["clarification_answers"], answers)
    rerun_input = load_json(paths["rerun_input"])
    rerun_input["rerun_input_overlay"] = {
        "intake_overlay": {
            "active_frame_hints": [],
            "event_storming_hints": [],
        },
        "ontology_review_hints": {
            "term_bindings": [],
            "aliases": [],
            "project_local_terms": [],
            "rejected_terms": [],
            "deferred_terms": [],
        },
        "candidate_review_hints": {
            "acceptance_criteria": [],
            "graph_edges": [],
            "claim_reviews": [],
            "other": [
                {
                    "request_id": "clarification.defer-risk",
                    "answer_kind": "defer",
                    "request_kind": "candidate_gap",
                    "target_ref": "candidate-spec.product-boundary#gap.local-risk",
                }
            ],
        },
    }
    write_json(paths["rerun_input"], rerun_input)

    report = build_report(paths)
    metrics = report["metrics"]

    assert metrics["aggregate_answer_count"] == 0
    assert metrics["closure_evidence_answer_count"] == 2
    assert metrics["ordinary_unmaterialized_answer_count"] == 1


def test_idea_maturity_metrics_preserves_summary_only_materialization_counts(
    tmp_path: Path,
) -> None:
    paths = write_ready_chain(tmp_path / "summary-only-materialization")
    answers = load_json(paths["clarification_answers"])
    answers["answers"] = []
    answers["summary"]["answer_count"] = 2
    answers["summary"]["accepted_answer_count"] = 2
    write_json(paths["clarification_answers"], answers)

    report = build_report(paths)
    metrics = report["metrics"]

    assert metrics["accepted_answer_count"] == 2
    assert metrics["materialized_answer_count"] == 2
    assert metrics["closure_evidence_answer_count"] == 2
    assert metrics["answer_materialization_rate"] == 1.0


def test_idea_maturity_metrics_report_uses_structured_stale_findings_only(
    tmp_path: Path,
) -> None:
    paths = write_ready_chain(tmp_path / "structured-stale")
    answers = load_json(paths["clarification_answers"])
    answers["findings"] = [
        {
            "finding_id": "informational_note",
            "severity": "low",
            "message": "no stale refs detected in this section",
        },
        {
            "code": "stale_answer_ref",
            "severity": "medium",
            "message": "answer was superseded",
        },
    ]
    write_json(paths["clarification_answers"], answers)

    report = build_report(paths)

    assert report["metrics"]["stale_ref_count"] == 0
    assert report["metrics"]["stale_answer_count"] == 1


def test_idea_maturity_metrics_report_computes_stalled_phase(tmp_path: Path) -> None:
    paths = base_paths(tmp_path / "stalled")
    old = "2026-06-20T10:00:00+00:00"
    write_json(
        paths["intake"],
        {
            "artifact_kind": "idea_event_storming_intake",
            "generated_at": old,
            "source_intake": {
                "workspace": {
                    "candidate_id": "local-subscription-control",
                    "public_route": "/local-subscription-control",
                }
            },
            "summary": {"status": "ready_for_candidate_graph"},
        },
    )
    write_json(
        paths["candidate_graph"],
        {
            "artifact_kind": "candidate_spec_graph",
            "generated_at": old,
            "nodes": [
                {
                    "id": "candidate-spec.product-boundary",
                    "gaps": [{"id": "gap.local-risk", "kind": "risk_requires_review"}],
                }
            ],
            "summary": {"node_count": 1, "gap_count": 1},
        },
    )
    write_json(
        paths["clarification_requests"],
        {
            "artifact_kind": "idea_to_spec_clarification_requests",
            "generated_at": old,
            "summary": {
                "request_count": 1,
                "blocking_request_count": 1,
                "review_required_request_count": 0,
            },
            "readiness": {"ready": False, "blocked_by": ["gap.local-risk"]},
        },
    )

    report = build_report(paths)

    assert report["status"] == "blocked"
    assert report["summary"]["stalled_phase"] == "repair_required"
    assert report["groups"]["temporal_progress"]["phase_dwell_seconds"]["repair_required"] >= 86_400


def test_idea_maturity_metrics_report_preserves_blocked_promotion_execution(
    tmp_path: Path,
) -> None:
    paths = write_ready_chain(tmp_path / "blocked-promotion")
    write_json(
        paths["promotion_execution"],
        {
            "artifact_kind": "product_candidate_promotion_execution_report",
            "summary": {"status": "promotion_blocked"},
            "readiness": {"ready": False, "blocked_by": ["promotion_request_blocked"]},
        },
    )

    report = build_report(paths)

    assert report["status"] == "blocked"
    assert report["metrics"]["promotion_execution_state"] == "blocked"
    assert report["metrics"]["platform_promotion_state"] == "blocked"
    assert report["metrics"]["failed_gate_count"] == 1


def test_idea_maturity_metrics_report_counts_platform_error_inputs_by_key(
    tmp_path: Path,
) -> None:
    paths = write_ready_chain(tmp_path / "platform-error")
    write_json(
        paths["repair_rerun_execution"],
        {
            "artifact_kind": "platform_product_repair_rerun_execution_report",
            "summary": {"status": "execution_completed", "error_count": 1},
        },
    )

    report = build_report(paths)

    assert report["status"] == "blocked"
    assert report["metrics"]["failed_gate_count"] == 1


def test_idea_maturity_metrics_report_reads_candidate_approval_decision(
    tmp_path: Path,
) -> None:
    paths = write_ready_chain(tmp_path / "approval-decision")
    write_json(
        paths["candidate_approval_decision"],
        {
            "artifact_kind": "candidate_approval_decision",
            "contract_ref": "specgraph.idea-to-spec.candidate-approval-decision.v0.1",
            "decision": {"state": "approved"},
            "readiness": {"ready": True, "review_state": "promotion_request_approved"},
            "summary": {
                "effective_state": "approved",
                "promotion_path_count": 1,
                "status": "promotion_request_approved",
            },
        },
    )

    report = build_report(paths)

    assert report["metrics"]["candidate_approval_decision_state"] == "materialized"
    assert report["metrics"]["platform_promotion_state"] == "ready"
    assert report["summary"]["lifecycle_state"] == "approval_materialized"


def test_idea_maturity_metrics_report_requires_core_candidate_evidence(
    tmp_path: Path,
) -> None:
    paths = base_paths(tmp_path / "intake-only")
    write_json(
        paths["intake"],
        {
            "artifact_kind": "idea_event_storming_intake",
            "generated_at": "2026-06-28T10:00:00+00:00",
            "source_intake": {
                "workspace": {
                    "candidate_id": "local-subscription-control",
                    "public_route": "/local-subscription-control",
                }
            },
            "summary": {"status": "ready_for_candidate_graph"},
        },
    )

    report = build_report(paths)

    assert report["status"] == "partial"
    assert report["summary"]["lifecycle_state"] == "intake_ready"
    assert report["metrics"]["candidate_node_count"] == 0


def test_idea_maturity_metrics_strict_fails_on_blocked_report(tmp_path: Path) -> None:
    paths = write_ready_chain(tmp_path / "strict-blocked", stale_rerun_ref=True)
    output = tmp_path / "strict-blocked" / "idea_maturity_metrics_report.json"

    result = subprocess.run(
        tool_args(paths, output, strict=True),
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    report = load_json(output)
    assert report["status"] == "blocked"
    assert report["metrics"]["stale_ref_count"] == 1
