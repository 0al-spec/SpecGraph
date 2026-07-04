from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "idea_to_spec_repair_session_journal.py"


def load_module(path: Path, name: str) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
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


def finding_ids(report: dict[str, object]) -> set[str]:
    findings = report["findings"]
    assert isinstance(findings, list)
    return {finding["finding_id"] for finding in findings if isinstance(finding, dict)}


def valid_artifacts() -> dict[str, dict[str, object]]:
    return {
        "active_candidate": {
            "artifact_kind": "active_idea_to_spec_candidate",
            "schema_version": 1,
            "proposal_id": "0155",
            "contract_ref": "specgraph.idea-to-spec.active-candidate-source.v0.1",
            "canonical_mutations_allowed": False,
            "tracked_artifacts_written": False,
            "candidate": {
                "candidate_id": "team-decision-log",
                "display_name": "Team Decision Log",
                "workflow_lane": "product_idea_to_spec",
                "public_route": "/team-decision-log",
                "governance_profile": "product_workspace",
                "target_repository_role": "product_spec_workspace",
            },
            "readiness": {
                "ready": False,
                "review_state": "active_candidate_review_required",
                "blocked_by": ["promotion_gate_not_ready"],
            },
            "source_artifacts": {
                "promotion_gate": {"source_ref": "runs/idea_to_spec_promotion_gate.json"}
            },
            "platform_handoff_surfaces": {
                "idea_to_spec_promotion_gate.json": {
                    "source_ref": "runs/idea_to_spec_promotion_gate.json"
                }
            },
            "authority_boundary": {"may_mutate_canonical_specs": False},
            "summary": {
                "status": "active_candidate_review_required",
                "candidate_id": "team-decision-log",
            },
        },
        "clarification_requests": {
            "artifact_kind": "idea_to_spec_clarification_requests",
            "schema_version": 1,
            "proposal_id": "0163",
            "contract_ref": "specgraph.idea-to-spec.clarification-requests.v0.1",
            "canonical_mutations_allowed": False,
            "tracked_artifacts_written": False,
            "readiness": {
                "ready": False,
                "review_state": "clarification_required",
                "blocked_by": ["clarification.repair.ontology-gap"],
            },
            "authority_boundary": {"may_write_ontology_package": False},
            "summary": {
                "status": "clarification_required",
                "request_count": 3,
                "blocking_request_count": 1,
            },
        },
        "clarification_answers": {
            "artifact_kind": "idea_to_spec_clarification_answers",
            "schema_version": 1,
            "proposal_id": "0164",
            "contract_ref": "specgraph.idea-to-spec.clarification-answers.v0.1",
            "canonical_mutations_allowed": False,
            "tracked_artifacts_written": False,
            "source_artifacts": {
                "clarification_requests": {
                    "source_ref": "runs/idea_to_spec_clarification_requests.json"
                }
            },
            "answers": [
                {
                    "request_id": "clarification.repair.ontology-gap",
                    "answer_kind": "propose_project_local_term",
                    "status": "accepted_for_candidate",
                    "raw_operator_note": "private note",
                    "value": {"terms": ["Decision Owner"]},
                    "request_snapshot": {
                        "kind": "ontology_gap",
                        "target_artifact": "runs/candidate_repair_loop_report.json",
                        "target_ref": "candidate_graph.gaps",
                    },
                }
            ],
            "readiness": {
                "ready": True,
                "review_state": "answers_ready_for_rerun",
                "blocked_by": [],
            },
            "authority_boundary": {"may_accept_ontology_terms": False},
            "summary": {
                "status": "answers_ready_for_rerun",
                "accepted_answer_count": 1,
                "unresolved_blocking_count": 0,
            },
        },
        "ontology_decisions": {
            "artifact_kind": "product_ontology_gap_review_decisions",
            "schema_version": 1,
            "proposal_id": "0168",
            "contract_ref": "specgraph.product-ontology.gap-review-decisions.v0.1",
            "canonical_mutations_allowed": False,
            "tracked_artifacts_written": False,
            "source_artifacts": {
                "clarification_answers": {
                    "source_ref": "runs/idea_to_spec_clarification_answers.json"
                }
            },
            "decisions": [
                {
                    "id": "product-ontology-decision.decision-owner.0",
                    "decision_type": "propose_project_local_term",
                    "status": "accepted_for_candidate_preview",
                    "materialization_intent": "rerun_overlay_only",
                    "term": "Decision Owner",
                    "raw_prompt": "private prompt",
                }
            ],
            "readiness": {
                "ready": True,
                "review_state": "ontology_gap_decisions_ready",
                "blocked_by": [],
            },
            "authority_boundary": {"may_accept_ontology_terms": False},
            "summary": {
                "status": "ontology_gap_decisions_ready",
                "decision_count": 1,
            },
        },
        "rerun_input": {
            "artifact_kind": "idea_to_spec_answer_rerun_input",
            "schema_version": 1,
            "proposal_id": "0165",
            "contract_ref": "specgraph.idea-to-spec.answer-rerun-input.v0.1",
            "canonical_mutations_allowed": False,
            "tracked_artifacts_written": False,
            "source_artifacts": {
                "clarification_answers": {
                    "source_ref": "runs/idea_to_spec_clarification_answers.json"
                },
                "product_ontology_gap_review_decisions": {
                    "source_ref": "runs/product_ontology_gap_review_decisions.json"
                },
            },
            "readiness": {
                "ready": True,
                "review_state": "rerun_input_ready",
                "blocked_by": [],
            },
            "authority_boundary": {"may_apply_answers_to_source_artifacts": False},
            "summary": {
                "status": "rerun_input_ready",
                "accepted_answer_count": 1,
                "ontology_decision_count": 1,
            },
        },
        "rerun_preview": {
            "artifact_kind": "idea_to_spec_rerun_preview",
            "schema_version": 1,
            "proposal_id": "0166",
            "contract_ref": "specgraph.idea-to-spec.rerun-preview.v0.1",
            "canonical_mutations_allowed": False,
            "tracked_artifacts_written": False,
            "source_artifacts": {
                "rerun_input": {"source_ref": "runs/idea_to_spec_answer_rerun_input.json"}
            },
            "readiness": {
                "ready": True,
                "review_state": "rerun_preview_ready",
                "blocked_by": [],
            },
            "authority_boundary": {"may_mutate_candidate_source_artifacts": False},
            "summary": {
                "status": "rerun_preview_ready",
                "candidate_quality_review_state": "candidate_quality_partially_improved",
                "resolved_ontology_gap_count": 1,
                "unresolved_ontology_gap_count": 2,
            },
        },
        "rerun_materialization": {
            "artifact_kind": "idea_to_spec_rerun_materialization",
            "schema_version": 1,
            "proposal_id": "0167",
            "contract_ref": "specgraph.idea-to-spec.rerun-materialization.v0.1",
            "canonical_mutations_allowed": False,
            "tracked_artifacts_written": False,
            "source_artifacts": {
                "rerun_preview": {"source_ref": "runs/idea_to_spec_rerun_preview.json"}
            },
            "readiness": {
                "ready": True,
                "review_state": "rerun_materialization_ready",
                "blocked_by": [],
            },
            "authority_boundary": {"may_mutate_candidate_source_artifacts": False},
            "summary": {
                "status": "rerun_materialization_ready",
                "removed_gap_count": 1,
                "resolved_ontology_gap_count": 1,
                "unresolved_ontology_gap_count": 2,
            },
        },
        "promotion_gate": {
            "artifact_kind": "idea_to_spec_promotion_gate",
            "schema_version": 1,
            "proposal_id": "0154",
            "contract_ref": "specgraph.idea-to-spec.promotion-gate.v0.1",
            "canonical_mutations_allowed": False,
            "tracked_artifacts_written": False,
            "readiness": {
                "ready": False,
                "review_state": "idea_to_spec_promotion_blocked",
                "blocked_by": ["promotion_paths_missing"],
            },
            "authority_boundary": {"may_create_branch_or_commit": False},
            "summary": {
                "status": "idea_to_spec_promotion_blocked",
                "promotion_path_count": 0,
            },
        },
    }


def valid_paths() -> dict[str, Path]:
    return {
        "active_candidate": ROOT / "runs" / "active_idea_to_spec_candidate.json",
        "clarification_requests": ROOT / "runs" / "idea_to_spec_clarification_requests.json",
        "clarification_answers": ROOT / "runs" / "idea_to_spec_clarification_answers.json",
        "ontology_decisions": ROOT / "runs" / "product_ontology_gap_review_decisions.json",
        "rerun_input": ROOT / "runs" / "idea_to_spec_answer_rerun_input.json",
        "rerun_preview": ROOT / "runs" / "idea_to_spec_rerun_preview.json",
        "rerun_materialization": ROOT / "runs" / "idea_to_spec_rerun_materialization.json",
        "promotion_gate": ROOT / "runs" / "idea_to_spec_promotion_gate.json",
    }


def build_report(
    artifacts: dict[str, dict[str, object]],
    *,
    missing_stages: set[str] | None = None,
) -> dict[str, object]:
    module = load_module(TOOL_PATH, "idea_to_spec_repair_session_journal_under_test")
    paths = valid_paths()
    return module.build_idea_to_spec_repair_session_journal(
        active_candidate=artifacts["active_candidate"],
        clarification_requests=artifacts["clarification_requests"],
        clarification_answers=artifacts["clarification_answers"],
        ontology_decisions=artifacts["ontology_decisions"],
        rerun_input=artifacts["rerun_input"],
        rerun_preview=artifacts["rerun_preview"],
        rerun_materialization=artifacts["rerun_materialization"],
        promotion_gate=artifacts["promotion_gate"],
        active_candidate_path=paths["active_candidate"],
        clarification_requests_path=paths["clarification_requests"],
        clarification_answers_path=paths["clarification_answers"],
        ontology_decisions_path=paths["ontology_decisions"],
        rerun_input_path=paths["rerun_input"],
        rerun_preview_path=paths["rerun_preview"],
        rerun_materialization_path=paths["rerun_materialization"],
        promotion_gate_path=paths["promotion_gate"],
        operator_ref="operator:test",
        missing_stages=missing_stages,
    )


def missing_optional_artifact(key: str) -> dict[str, object]:
    module = load_module(TOOL_PATH, "idea_to_spec_repair_session_journal_missing_under_test")
    return module._missing_optional_artifact(key)  # type: ignore[attr-defined]


def test_repair_session_journal_builds_durable_review_only_summary() -> None:
    report = build_report(valid_artifacts())

    assert report["artifact_kind"] == "idea_to_spec_repair_session_journal"
    assert report["proposal_id"] == "0171"
    assert report["contract_ref"] == "specgraph.idea-to-spec.repair-session-journal.v0.1"
    assert report["canonical_mutations_allowed"] is False
    assert report["tracked_artifacts_written"] is False
    assert report["readiness"]["ready"] is True
    assert report["session"]["candidate_id"] == "team-decision-log"
    assert report["session"]["operator_ref"] == "operator:test"
    assert len(report["workflow_journal"]["stages"]) == 8
    assert report["summary"]["source_artifact_count"] == 8
    assert report["summary"]["accepted_answer_count"] == 1
    assert report["summary"]["ontology_decision_count"] == 1
    assert report["summary"]["unresolved_ontology_gap_count"] == 2
    assert report["summary"]["ready_for_candidate_approval"] is False
    boundary = report["authority_boundary"]
    assert boundary["may_write_ontology_package"] is False
    assert boundary["may_create_branch_or_commit"] is False


def test_repair_session_journal_allows_initial_session_with_missing_repair_stages() -> None:
    artifacts = valid_artifacts()
    for key in (
        "clarification_answers",
        "ontology_decisions",
        "rerun_input",
        "rerun_preview",
        "rerun_materialization",
    ):
        artifacts[key] = missing_optional_artifact(key)

    report = build_report(
        artifacts,
        missing_stages={
            "clarification_answers",
            "ontology_decisions",
            "rerun_input",
            "rerun_preview",
            "rerun_materialization",
        },
    )

    assert report["readiness"]["ready"] is True
    assert report["summary"]["ready_for_candidate_approval"] is False
    assert report["readiness_impact"]["intermediate_artifacts_ready"] is False
    assert "clarification_answers_not_ready" in report["readiness_impact"]["blocked_by"]
    stages = report["workflow_journal"]["stages"]
    assert len(stages) == 8
    missing_stages = [stage for stage in stages if stage["status"] == "artifact_missing"]
    assert len(missing_stages) == 5
    source = report["source_artifacts"]["clarification_answers"]
    assert source["schema_version"] is None
    assert source["sha256"] is None


def test_repair_session_journal_does_not_trust_loaded_missing_optional_marker() -> None:
    artifacts = valid_artifacts()
    artifacts["clarification_answers"]["missing_optional_stage"] = True

    report = build_report(artifacts)

    assert "clarification_answers_missing_optional_stage_untrusted" in finding_ids(report)
    assert report["readiness"]["ready"] is False
    source = report["source_artifacts"]["clarification_answers"]
    assert source["schema_version"] == 1
    assert source["source_ref"] == "runs/idea_to_spec_clarification_answers.json"


def test_repair_session_journal_marks_candidate_approval_possible_only_after_ready_chain() -> None:
    artifacts = valid_artifacts()
    artifacts["active_candidate"]["readiness"] = {
        "ready": True,
        "review_state": "active_candidate_ready",
        "blocked_by": [],
    }
    artifacts["promotion_gate"]["readiness"] = {
        "ready": True,
        "review_state": "idea_to_spec_promotion_ready",
        "blocked_by": [],
    }
    artifacts["promotion_gate"]["summary"]["promotion_path_count"] = 1
    artifacts["rerun_preview"]["summary"]["resolved_ontology_gap_count"] = 3
    artifacts["rerun_preview"]["summary"]["unresolved_ontology_gap_count"] = 0
    artifacts["rerun_materialization"]["summary"]["resolved_ontology_gap_count"] = 3
    artifacts["rerun_materialization"]["summary"]["unresolved_ontology_gap_count"] = 0

    report = build_report(artifacts)

    assert report["readiness_impact"]["blocked_by"] == []
    assert report["summary"]["ready_for_candidate_approval"] is True
    assert report["readiness_impact"]["ready_for_candidate_approval"] is True
    assert report["readiness_impact"]["ready_for_platform_promotion"] is False
    assert report["readiness_impact"]["platform_promotion_blocked_by"] == [
        "candidate_approval_decision_missing"
    ]


def test_repair_session_journal_blocks_candidate_approval_on_unresolved_candidate_gaps() -> None:
    artifacts = valid_artifacts()
    artifacts["active_candidate"]["readiness"] = {
        "ready": True,
        "review_state": "active_candidate_ready",
        "blocked_by": [],
    }
    artifacts["promotion_gate"]["readiness"] = {
        "ready": True,
        "review_state": "idea_to_spec_promotion_ready",
        "blocked_by": [],
    }
    artifacts["promotion_gate"]["summary"]["promotion_path_count"] = 1
    artifacts["rerun_preview"]["summary"]["unresolved_ontology_gap_count"] = 0
    artifacts["rerun_preview"]["summary"]["resolved_candidate_gap_count"] = 2
    artifacts["rerun_preview"]["summary"]["unresolved_candidate_gap_count"] = 1
    artifacts["rerun_materialization"]["summary"]["unresolved_ontology_gap_count"] = 0
    artifacts["rerun_materialization"]["summary"]["resolved_candidate_gap_count"] = 2
    artifacts["rerun_materialization"]["summary"]["unresolved_candidate_gap_count"] = 1

    report = build_report(artifacts)

    assert report["readiness_impact"]["ready_for_candidate_approval"] is False
    assert "unresolved_candidate_gaps" in report["readiness_impact"]["blocked_by"]
    assert report["summary"]["resolved_candidate_gap_count"] == 2
    assert report["summary"]["unresolved_candidate_gap_count"] == 1


def test_repair_session_journal_requires_ready_intermediate_artifacts_for_approval() -> None:
    artifacts = valid_artifacts()
    artifacts["active_candidate"]["readiness"] = {
        "ready": True,
        "review_state": "active_candidate_ready",
        "blocked_by": [],
    }
    artifacts["promotion_gate"]["readiness"] = {
        "ready": True,
        "review_state": "idea_to_spec_promotion_ready",
        "blocked_by": [],
    }
    artifacts["rerun_preview"]["readiness"] = {
        "ready": False,
        "review_state": "rerun_preview_review_required",
        "blocked_by": ["rerun_preview_failed"],
    }
    artifacts["rerun_preview"]["summary"]["unresolved_ontology_gap_count"] = 0
    artifacts["rerun_materialization"]["summary"]["unresolved_ontology_gap_count"] = 0

    report = build_report(artifacts)

    assert report["readiness_impact"]["ready_for_candidate_approval"] is False
    assert "rerun_preview_not_ready" in report["readiness_impact"]["blocked_by"]
    assert "rerun_preview_failed" in report["readiness_impact"]["blocked_by"]


def test_repair_session_journal_strips_raw_trace_fields() -> None:
    report = build_report(valid_artifacts())
    text = json.dumps(report)

    assert "private note" not in text
    assert "private prompt" not in text
    accepted_answer = report["workflow_journal"]["accepted_answers"][0]
    ontology_decision = report["workflow_journal"]["ontology_decisions"][0]
    assert "raw_operator_note" not in accepted_answer
    assert "raw_prompt" not in ontology_decision


def test_repair_session_journal_rejects_authority_expansion() -> None:
    artifacts = valid_artifacts()
    artifacts["ontology_decisions"]["authority_boundary"] = {"may_accept_ontology_terms": True}

    report = build_report(artifacts)

    assert report["readiness"]["ready"] is False
    assert "ontology_decisions_authority_boundary_expanded" in finding_ids(report)


def test_repair_session_journal_requires_explicit_authority_boundary() -> None:
    artifacts = valid_artifacts()
    artifacts["rerun_preview"].pop("authority_boundary")

    report = build_report(artifacts)

    assert report["readiness"]["ready"] is False
    assert "rerun_preview_authority_boundary_missing" in finding_ids(report)


def test_repair_session_journal_detects_stale_source_refs() -> None:
    artifacts = valid_artifacts()
    rerun_input = copy.deepcopy(artifacts["rerun_input"])
    rerun_input["source_artifacts"]["product_ontology_gap_review_decisions"]["source_ref"] = (
        "runs/stale_product_ontology_gap_review_decisions.json"
    )
    artifacts["rerun_input"] = rerun_input

    report = build_report(artifacts)

    assert report["readiness"]["ready"] is False
    assert "rerun_input_ontology_decisions_source_ref_mismatch" in finding_ids(report)


def test_repair_session_journal_detects_missing_chained_source_refs() -> None:
    artifacts = valid_artifacts()
    rerun_input = copy.deepcopy(artifacts["rerun_input"])
    rerun_input["source_artifacts"]["product_ontology_gap_review_decisions"].pop("source_ref")
    artifacts["rerun_input"] = rerun_input

    report = build_report(artifacts)

    assert report["readiness"]["ready"] is False
    assert "rerun_input_ontology_decisions_source_ref_missing" in finding_ids(report)


def test_repair_session_journal_detects_stale_active_candidate_refs() -> None:
    artifacts = valid_artifacts()
    active_candidate = copy.deepcopy(artifacts["active_candidate"])
    active_candidate["source_artifacts"]["promotion_gate"]["source_ref"] = (
        "runs/stale_idea_to_spec_promotion_gate.json"
    )
    artifacts["active_candidate"] = active_candidate

    report = build_report(artifacts)

    assert report["readiness"]["ready"] is False
    assert "active_candidate_promotion_gate_source_ref_mismatch" in finding_ids(report)


def test_repair_session_journal_cli_writes_output(tmp_path: Path) -> None:
    artifacts = valid_artifacts()
    paths = {}
    for key, artifact in artifacts.items():
        path = tmp_path / f"{key}.json"
        write_json(path, artifact)
        paths[key] = path
    output = tmp_path / "idea_to_spec_repair_session.json"

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--active-candidate",
            str(paths["active_candidate"]),
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
            "--session-id",
            "repair-session.test",
            "--operator-ref",
            "operator:cli-test",
            "--output",
            str(output),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    report = load_json(output)
    assert report["artifact_kind"] == "idea_to_spec_repair_session_journal"
    assert report["session"]["session_id"] == "repair-session.test"
    assert report["session"]["operator_ref"] == "operator:cli-test"


def test_repair_session_journal_cli_strict_returns_nonzero_for_review_required(
    tmp_path: Path,
) -> None:
    artifacts = valid_artifacts()
    artifacts["ontology_decisions"]["authority_boundary"] = {"may_accept_ontology_terms": True}
    paths = {}
    for key, artifact in artifacts.items():
        path = tmp_path / f"{key}.json"
        write_json(path, artifact)
        paths[key] = path
    output = tmp_path / "idea_to_spec_repair_session.json"

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--active-candidate",
            str(paths["active_candidate"]),
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
    assert report["readiness"]["ready"] is False
    assert "ontology_decisions_authority_boundary_expanded" in finding_ids(report)
