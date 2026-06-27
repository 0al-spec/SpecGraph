from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "repaired_candidate_promotion_handoff.py"


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def finding_ids(report: dict[str, object]) -> set[str]:
    findings = report["findings"]
    assert isinstance(findings, list)
    return {finding["finding_id"] for finding in findings if isinstance(finding, dict)}


def authority_boundary() -> dict[str, bool]:
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


def candidate_graph_preview(*, unresolved_gap: bool = False) -> dict[str, object]:
    gaps = (
        [
            {
                "id": "gap.subscription-reminder.enforcement-mechanism",
                "kind": "implementation_gap",
                "source_ref": "constraint.subscription-reminder",
                "statement": "Define reminder enforcement.",
            }
        ]
        if unresolved_gap
        else []
    )
    return {
        "active_frame": {
            "context_refs": ["context.idea_to_spec"],
            "domain_refs": ["domain.local_subscription_control"],
            "ontology_refs": ["ontology://specgraph-core"],
            "project": "LocalSubscriptionControl",
        },
        "artifact_kind": "candidate_spec_graph",
        "canonical_mutations_allowed": False,
        "contract_ref": "specgraph.idea-to-spec.candidate-spec-graph.v0.1",
        "edges": [],
        "nodes": [
            {
                "id": "candidate-spec.product-boundary",
                "kind": "product_boundary",
                "title": "Local Subscription Control",
                "description": "Track subscriptions locally.",
                "ontology_refs": ["ontology.specgraph.spec"],
                "domain_refs": ["domain.local_subscription_control"],
                "context_refs": ["context.idea_to_spec"],
                "requirements": [
                    {
                        "id": "req.product-boundary",
                        "statement": "The workspace captures local subscription control.",
                        "acceptance_criteria_refs": ["ac.product-boundary"],
                    }
                ],
                "acceptance_criteria": [
                    {
                        "id": "ac.product-boundary",
                        "statement": "A product boundary spec is present.",
                    }
                ],
                "gaps": [],
            },
            {
                "id": "candidate-spec.subscription-reminder",
                "kind": "requirement",
                "title": "Subscription Reminder",
                "description": "Show upcoming renewal reminders.",
                "ontology_refs": ["ontology.specgraph.requirement"],
                "domain_refs": ["domain.local_subscription_control"],
                "context_refs": ["context.idea_to_spec"],
                "requirements": [
                    {
                        "id": "req.subscription-reminder",
                        "statement": "The app highlights upcoming renewal dates.",
                        "acceptance_criteria_refs": ["ac.subscription-reminder"],
                    }
                ],
                "acceptance_criteria": [
                    {
                        "id": "ac.subscription-reminder",
                        "statement": "Upcoming renewals are visible before their date.",
                    }
                ],
                "gaps": gaps,
            },
        ],
        "pre_sib_readiness": {"ready": True, "review_state": "ready_for_pre_sib"},
        "schema_version": 1,
        "source_intake": {"source_ref": "product://local-subscription-control/root-intent"},
        "source_ref": "runs/test/repaired-preview#candidate_graph_preview",
        "summary": {
            "edge_count": 0,
            "finding_count": 0,
            "gap_count": len(gaps),
            "node_count": 2,
            "status": "ready_for_pre_sib",
        },
        "tracked_artifacts_written": False,
    }


def write_input_chain(run_dir: Path, *, unresolved_gap: bool = False) -> dict[str, Path]:
    paths = {
        "intake": run_dir / "idea_event_storming_intake.json",
        "clarification_requests": run_dir / "idea_to_spec_clarification_requests.json",
        "clarification_answers": run_dir / "idea_to_spec_clarification_answers.json",
        "ontology_decisions": run_dir / "product_ontology_gap_review_decisions.json",
        "rerun_input": run_dir / "idea_to_spec_answer_rerun_input.json",
        "rerun_preview": run_dir / "idea_to_spec_rerun_preview.json",
        "rerun_materialization": run_dir / "idea_to_spec_rerun_materialization.json",
    }
    write_json(
        paths["intake"],
        {
            "artifact_kind": "idea_event_storming_intake",
            "schema_version": 1,
            "contract_ref": "specgraph.idea-to-spec.event-storming-intake.v0.1",
            "canonical_mutations_allowed": False,
            "tracked_artifacts_written": False,
            "candidate_graph_readiness": {"ready": True, "review_state": "ready"},
            "source_ref": "product://local-subscription-control/root-intent",
            "source_intake": {
                "workspace": {
                    "candidate_id": "local-subscription-control",
                    "display_name": "Local Subscription Control",
                    "public_route": "/local-subscription-control",
                }
            },
            "authority_boundary": authority_boundary(),
            "summary": {"status": "ready"},
        },
    )
    write_json(
        paths["clarification_requests"],
        {
            "artifact_kind": "idea_to_spec_clarification_requests",
            "schema_version": 1,
            "proposal_id": "0163",
            "contract_ref": "specgraph.idea-to-spec.clarification-requests.v0.1",
            "canonical_mutations_allowed": False,
            "tracked_artifacts_written": False,
            "readiness": {"ready": False, "review_state": "clarification_required"},
            "authority_boundary": authority_boundary(),
            "summary": {"blocking_request_count": 1, "request_count": 1},
        },
    )
    write_json(
        paths["clarification_answers"],
        {
            "artifact_kind": "idea_to_spec_clarification_answers",
            "schema_version": 1,
            "proposal_id": "0164",
            "contract_ref": "specgraph.idea-to-spec.clarification-answers.v0.1",
            "canonical_mutations_allowed": False,
            "tracked_artifacts_written": False,
            "source_artifacts": {
                "clarification_requests": {"source_ref": rel(paths["clarification_requests"])}
            },
            "answers": [
                {
                    "request_id": "clarification.subscription-reminder",
                    "answer_kind": "answer_question",
                    "status": "accepted_for_candidate",
                    "value": "Show reminders in the local dashboard.",
                    "request_snapshot": {
                        "kind": "candidate_gap",
                        "target_ref": (
                            "candidate-spec.subscription-reminder.gaps."
                            "gap.subscription-reminder.enforcement-mechanism"
                        ),
                    },
                }
            ],
            "readiness": {"ready": True, "review_state": "answers_ready_for_rerun"},
            "authority_boundary": authority_boundary(),
            "summary": {"accepted_answer_count": 1, "unresolved_blocking_count": 0},
        },
    )
    write_json(
        paths["ontology_decisions"],
        {
            "artifact_kind": "product_ontology_gap_review_decisions",
            "schema_version": 1,
            "proposal_id": "0168",
            "contract_ref": "specgraph.product-ontology.gap-review-decisions.v0.1",
            "canonical_mutations_allowed": False,
            "tracked_artifacts_written": False,
            "source_artifacts": {
                "clarification_answers": {"source_ref": rel(paths["clarification_answers"])}
            },
            "decisions": [],
            "readiness": {"ready": True, "review_state": "ontology_gap_decisions_ready"},
            "authority_boundary": authority_boundary(),
            "summary": {"decision_count": 0},
        },
    )
    write_json(
        paths["rerun_input"],
        {
            "artifact_kind": "idea_to_spec_answer_rerun_input",
            "schema_version": 1,
            "proposal_id": "0165",
            "contract_ref": "specgraph.idea-to-spec.answer-rerun-input.v0.1",
            "canonical_mutations_allowed": False,
            "tracked_artifacts_written": False,
            "source_artifacts": {
                "clarification_answers": {"source_ref": rel(paths["clarification_answers"])},
                "product_ontology_gap_review_decisions": {
                    "source_ref": rel(paths["ontology_decisions"])
                },
            },
            "readiness": {"ready": True, "review_state": "rerun_input_ready"},
            "authority_boundary": authority_boundary(),
            "summary": {"accepted_answer_count": 1, "ontology_decision_count": 0},
        },
    )
    write_json(
        paths["rerun_preview"],
        {
            "artifact_kind": "idea_to_spec_rerun_preview",
            "schema_version": 1,
            "proposal_id": "0166",
            "contract_ref": "specgraph.idea-to-spec.rerun-preview.v0.1",
            "canonical_mutations_allowed": False,
            "tracked_artifacts_written": False,
            "source_artifacts": {"rerun_input": {"source_ref": rel(paths["rerun_input"])}},
            "readiness": {"ready": True, "review_state": "rerun_preview_ready"},
            "authority_boundary": authority_boundary(),
            "summary": {
                "candidate_quality_review_state": "candidate_quality_improved",
                "resolved_candidate_gap_count": 0 if unresolved_gap else 1,
                "resolved_ontology_gap_count": 1,
                "unresolved_candidate_gap_count": 1 if unresolved_gap else 0,
                "unresolved_ontology_gap_count": 0,
            },
        },
    )
    write_json(
        paths["rerun_materialization"],
        {
            "artifact_kind": "idea_to_spec_rerun_materialization",
            "schema_version": 1,
            "proposal_id": "0167",
            "contract_ref": "specgraph.idea-to-spec.rerun-materialization.v0.1",
            "canonical_mutations_allowed": False,
            "tracked_artifacts_written": False,
            "source_artifacts": {"rerun_preview": {"source_ref": rel(paths["rerun_preview"])}},
            "materialization_preview": {
                "candidate_graph_preview": candidate_graph_preview(unresolved_gap=unresolved_gap),
                "delta": {
                    "resolved_candidate_gap_count": 0 if unresolved_gap else 1,
                    "resolved_ontology_gap_count": 1,
                    "unresolved_candidate_gap_count": 1 if unresolved_gap else 0,
                    "unresolved_ontology_gap_count": 0,
                },
            },
            "readiness": {"ready": True, "review_state": "rerun_materialization_ready"},
            "authority_boundary": authority_boundary(),
            "summary": {
                "removed_gap_count": 1 if unresolved_gap else 2,
                "resolved_candidate_gap_count": 0 if unresolved_gap else 1,
                "resolved_ontology_gap_count": 1,
                "unresolved_candidate_gap_count": 1 if unresolved_gap else 0,
                "unresolved_ontology_gap_count": 0,
            },
        },
    )
    return paths


def output_paths(run_dir: Path) -> dict[str, Path]:
    return {
        "repaired_candidate_graph": run_dir / "repaired_candidate_spec_graph.json",
        "repaired_pre_sib": run_dir / "repaired_pre_sib_coherence_report.json",
        "repaired_repair_loop": run_dir / "repaired_candidate_repair_loop_report.json",
        "repaired_materialization_dir": run_dir / "repaired_materialized_candidate_specs",
        "repaired_materialization": run_dir / "repaired_candidate_spec_materialization_report.json",
        "repaired_promotion_gate": run_dir / "repaired_idea_to_spec_promotion_gate.json",
        "repaired_active_candidate": run_dir / "repaired_active_idea_to_spec_candidate.json",
        "repaired_repair_session": run_dir / "repaired_idea_to_spec_repair_session.json",
        "handoff": run_dir / "repaired_candidate_promotion_handoff_report.json",
    }


def run_tool(run_dir: Path, *, strict: bool = True) -> subprocess.CompletedProcess[str]:
    inputs = write_input_chain(run_dir)
    outputs = output_paths(run_dir)
    command = [
        sys.executable,
        str(TOOL_PATH),
        "--intake",
        rel(inputs["intake"]),
        "--clarification-requests",
        rel(inputs["clarification_requests"]),
        "--clarification-answers",
        rel(inputs["clarification_answers"]),
        "--ontology-decisions",
        rel(inputs["ontology_decisions"]),
        "--rerun-input",
        rel(inputs["rerun_input"]),
        "--rerun-preview",
        rel(inputs["rerun_preview"]),
        "--rerun-materialization",
        rel(inputs["rerun_materialization"]),
        "--repaired-candidate-graph-output",
        rel(outputs["repaired_candidate_graph"]),
        "--repaired-pre-sib-output",
        rel(outputs["repaired_pre_sib"]),
        "--repaired-repair-loop-output",
        rel(outputs["repaired_repair_loop"]),
        "--repaired-materialization-output-dir",
        rel(outputs["repaired_materialization_dir"]),
        "--repaired-materialization-output",
        rel(outputs["repaired_materialization"]),
        "--repaired-promotion-gate-output",
        rel(outputs["repaired_promotion_gate"]),
        "--repaired-active-candidate-output",
        rel(outputs["repaired_active_candidate"]),
        "--repaired-repair-session-output",
        rel(outputs["repaired_repair_session"]),
        "--output",
        rel(outputs["handoff"]),
    ]
    if strict:
        command.append("--strict")
    return subprocess.run(command, cwd=ROOT, check=False, capture_output=True, text=True)


def test_repaired_candidate_promotion_handoff_builds_approval_ready_chain() -> None:
    run_dir = ROOT / "runs" / "test_repaired_candidate_promotion_handoff_ready"
    if run_dir.exists():
        shutil.rmtree(run_dir)
    try:
        result = run_tool(run_dir)
        assert result.returncode == 0, result.stderr
        outputs = output_paths(run_dir)
        report = load_json(outputs["handoff"])
        assert report["readiness"]["ready"] is True
        assert report["summary"]["ready_for_candidate_approval"] is True
        assert report["summary"]["ready_for_platform_promotion"] is False

        repaired_graph = load_json(outputs["repaired_candidate_graph"])
        assert repaired_graph["source_ref"] == "product://local-subscription-control/root-intent"
        assert (
            repaired_graph["repaired_candidate_promotion_handoff"][
                "source_candidate_graph_preview_ref"
            ]
            == "runs/test/repaired-preview#candidate_graph_preview"
        )

        pre_sib = load_json(outputs["repaired_pre_sib"])
        assert pre_sib["readiness"]["ready"] is False
        assert "pre_sib_orphan_nodes" in {finding["finding_id"] for finding in pre_sib["findings"]}
        repair_loop = load_json(outputs["repaired_repair_loop"])
        assert repair_loop["readiness"]["ready"] is True
        assert repair_loop["summary"]["context_required_count"] == 0
        promotion_gate = load_json(outputs["repaired_promotion_gate"])
        assert promotion_gate["readiness"]["ready"] is True
        assert promotion_gate["warnings"][0]["finding_id"] == "pre_sib_findings_repaired_by_preview"
        active = load_json(outputs["repaired_active_candidate"])
        assert active["readiness"]["ready"] is True
        session = load_json(outputs["repaired_repair_session"])
        assert session["readiness_impact"]["ready_for_candidate_approval"] is True
        assert session["readiness_impact"]["ready_for_platform_promotion"] is False
    finally:
        if run_dir.exists():
            shutil.rmtree(run_dir)


def test_repaired_candidate_promotion_handoff_blocks_unresolved_repaired_gaps() -> None:
    run_dir = ROOT / "runs" / "test_repaired_candidate_promotion_handoff_unresolved"
    if run_dir.exists():
        shutil.rmtree(run_dir)
    try:
        write_input_chain(run_dir, unresolved_gap=True)
        inputs = {
            name: run_dir / filename
            for name, filename in {
                "intake": "idea_event_storming_intake.json",
                "clarification_requests": "idea_to_spec_clarification_requests.json",
                "clarification_answers": "idea_to_spec_clarification_answers.json",
                "ontology_decisions": "product_ontology_gap_review_decisions.json",
                "rerun_input": "idea_to_spec_answer_rerun_input.json",
                "rerun_preview": "idea_to_spec_rerun_preview.json",
                "rerun_materialization": "idea_to_spec_rerun_materialization.json",
            }.items()
        }
        outputs = output_paths(run_dir)
        command = [
            sys.executable,
            str(TOOL_PATH),
            "--intake",
            rel(inputs["intake"]),
            "--clarification-requests",
            rel(inputs["clarification_requests"]),
            "--clarification-answers",
            rel(inputs["clarification_answers"]),
            "--ontology-decisions",
            rel(inputs["ontology_decisions"]),
            "--rerun-input",
            rel(inputs["rerun_input"]),
            "--rerun-preview",
            rel(inputs["rerun_preview"]),
            "--rerun-materialization",
            rel(inputs["rerun_materialization"]),
            "--repaired-candidate-graph-output",
            rel(outputs["repaired_candidate_graph"]),
            "--repaired-pre-sib-output",
            rel(outputs["repaired_pre_sib"]),
            "--repaired-repair-loop-output",
            rel(outputs["repaired_repair_loop"]),
            "--repaired-materialization-output-dir",
            rel(outputs["repaired_materialization_dir"]),
            "--repaired-materialization-output",
            rel(outputs["repaired_materialization"]),
            "--repaired-promotion-gate-output",
            rel(outputs["repaired_promotion_gate"]),
            "--repaired-active-candidate-output",
            rel(outputs["repaired_active_candidate"]),
            "--repaired-repair-session-output",
            rel(outputs["repaired_repair_session"]),
            "--output",
            rel(outputs["handoff"]),
            "--strict",
        ]
        result = subprocess.run(command, cwd=ROOT, check=False, capture_output=True, text=True)
        assert result.returncode == 1
        report = load_json(outputs["handoff"])
        assert report["readiness"]["ready"] is False
        assert "repaired_session_not_ready_for_candidate_approval" in finding_ids(report)
        session = load_json(outputs["repaired_repair_session"])
        assert session["readiness_impact"]["unresolved_candidate_gap_count"] == 1
        assert session["readiness_impact"]["ready_for_candidate_approval"] is False
    finally:
        if run_dir.exists():
            shutil.rmtree(run_dir)
