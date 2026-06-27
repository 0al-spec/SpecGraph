from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANSWERS_TOOL_PATH = ROOT / "tools" / "idea_to_spec_clarification_answers.py"
RERUN_INPUT_TOOL_PATH = ROOT / "tools" / "idea_to_spec_answer_rerun_input.py"
PREVIEW_TOOL_PATH = ROOT / "tools" / "idea_to_spec_rerun_preview.py"
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "idea_to_spec_clarification_answers"
REQUESTS_FIXTURE = FIXTURE_DIR / "clarification_requests_blocking.json"
ANSWERS_READY_FIXTURE = FIXTURE_DIR / "answers_ready.json"


def load_module(path: Path, name: str) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def finding_ids(report: dict[str, object]) -> set[str]:
    findings = report["findings"]
    assert isinstance(findings, list)
    return {finding["finding_id"] for finding in findings if isinstance(finding, dict)}


def intake_artifact() -> dict[str, object]:
    return {
        "artifact_kind": "idea_event_storming_intake",
        "schema_version": 1,
        "contract_ref": "specgraph.idea-to-spec.event-storming-intake.v0.1",
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "active_frame": {
            "project": "TeamDecisionLog",
            "ontology_refs": ["ontology://specgraph-core"],
            "domain_refs": ["domain.team_decision_log"],
            "context_refs": ["context.idea_to_spec"],
        },
        "event_storming": {
            "actors": [],
            "domain_events": [],
            "commands": [],
            "policies": [],
            "external_systems": [],
            "constraints": [],
            "risks": [],
            "assumptions": [],
            "vocabulary_questions": [],
        },
    }


def candidate_graph_artifact() -> dict[str, object]:
    return {
        "artifact_kind": "candidate_spec_graph",
        "schema_version": 1,
        "contract_ref": "specgraph.idea-to-spec.candidate-spec-graph.v0.1",
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "nodes": [
            {
                "id": "candidate-spec.product-boundary",
                "gaps": [
                    {
                        "id": "ontology-gap.decision-owner",
                        "kind": "ontology_gap",
                        "source_ref": "actor.decision-owner",
                        "term": "Decision Owner",
                    },
                    {
                        "id": "ontology-gap.record-decision",
                        "kind": "ontology_gap",
                        "source_ref": "command.record-decision",
                        "term": "Record Decision",
                    },
                ],
            }
        ],
        "edges": [],
    }


def ready_rerun_input() -> dict[str, object]:
    answers_module = load_module(
        ANSWERS_TOOL_PATH,
        "idea_to_spec_clarification_answers_for_preview_test",
    )
    rerun_module = load_module(
        RERUN_INPUT_TOOL_PATH,
        "idea_to_spec_answer_rerun_input_for_preview_test",
    )
    answer_report = answers_module.build_idea_to_spec_clarification_answers(
        clarification_requests=load_json(REQUESTS_FIXTURE),
        answer_set=load_json(ANSWERS_READY_FIXTURE),
        requests_path=REQUESTS_FIXTURE,
        answer_set_path=ANSWERS_READY_FIXTURE,
    )
    return rerun_module.build_idea_to_spec_answer_rerun_input(
        answers_report=answer_report,
    )


def test_rerun_preview_resolves_matching_ontology_gap() -> None:
    module = load_module(
        PREVIEW_TOOL_PATH,
        "idea_to_spec_rerun_preview_under_test",
    )

    report = module.build_idea_to_spec_rerun_preview(
        rerun_input=ready_rerun_input(),
        intake=intake_artifact(),
        candidate_graph=candidate_graph_artifact(),
    )

    assert report["artifact_kind"] == "idea_to_spec_rerun_preview"
    assert report["proposal_id"] == "0166"
    assert report["canonical_mutations_allowed"] is False
    assert report["tracked_artifacts_written"] is False
    assert report["readiness"]["ready"] is True
    assert report["readiness"]["review_state"] == "rerun_preview_ready"

    gap_preview = report["rerun_preview"]["ontology_gap_preview"]
    assert gap_preview["resolved_ontology_gap_count"] == 1
    assert gap_preview["unresolved_ontology_gap_count"] == 1
    resolved = gap_preview["resolved_ontology_gaps"][0]
    assert resolved["gap_id"] == "ontology-gap.decision-owner"
    assert resolved["decision_id"] == "clarification.repair.repair-review-unresolved-gaps"
    assert resolved["decision_term"] == "Decision Owner"
    assert resolved["match_kind"] == "exact"
    assert resolved["confidence"] == "high"
    assert resolved["match"]["gap_term"] == "Decision Owner"
    assert resolved["resolution_preview"]["decision"] == "project_local_term"
    assert resolved["resolution_preview"]["term"] == "Decision Owner"
    quality = report["rerun_preview"]["candidate_quality_preview"]
    assert quality["candidate_quality_metric"] == "ontology_gap_resolution_preview"
    assert quality["review_state"] == "candidate_quality_partially_improved"
    assert quality["resolved_ontology_gap_count"] == 1
    assert quality["unresolved_ontology_gap_count"] == 1


def test_rerun_preview_blocks_unready_rerun_input() -> None:
    module = load_module(
        PREVIEW_TOOL_PATH,
        "idea_to_spec_rerun_preview_unready_test",
    )
    rerun_input = copy.deepcopy(ready_rerun_input())
    rerun_input["readiness"]["ready"] = False
    rerun_input["rerun_input_overlay"]["ontology_review_hints"]["project_local_terms"] = [
        {
            "term": "Record Decision",
            "answer_kind": "propose_project_local_term",
            "request_id": "clarification.test",
            "target_ref": "candidate_graph.gaps",
        }
    ]

    report = module.build_idea_to_spec_rerun_preview(
        rerun_input=rerun_input,
        intake=intake_artifact(),
        candidate_graph=candidate_graph_artifact(),
    )

    assert report["readiness"]["ready"] is False
    assert "rerun_input_not_ready" in finding_ids(report)
    gap_preview = report["rerun_preview"]["ontology_gap_preview"]
    assert gap_preview["decision_count"] == 0
    assert gap_preview["resolved_ontology_gap_count"] == 0


def test_rerun_preview_matches_aggregate_reject_to_ontology_gaps() -> None:
    module = load_module(
        PREVIEW_TOOL_PATH,
        "idea_to_spec_rerun_preview_aggregate_reject_test",
    )
    rerun_input = copy.deepcopy(ready_rerun_input())
    ontology_hints = rerun_input["rerun_input_overlay"]["ontology_review_hints"]
    ontology_hints["project_local_terms"] = []
    ontology_hints["rejected_terms"] = [
        {
            "answer_kind": "reject",
            "request_id": "clarification.repair.review-unresolved-gaps",
            "target_ref": "candidate_graph.gaps",
        }
    ]

    report = module.build_idea_to_spec_rerun_preview(
        rerun_input=rerun_input,
        intake=intake_artifact(),
        candidate_graph=candidate_graph_artifact(),
    )

    gap_preview = report["rerun_preview"]["ontology_gap_preview"]
    assert gap_preview["decision_count"] == 1
    assert gap_preview["resolved_ontology_gap_count"] == 2
    assert {
        item["resolution_preview"]["decision"] for item in gap_preview["resolved_ontology_gaps"]
    } == {"reject"}
    assert {item["match_kind"] for item in gap_preview["resolved_ontology_gaps"]} == {
        "aggregate_target"
    }
    assert {item["confidence"] for item in gap_preview["resolved_ontology_gaps"]} == {
        "aggregate_scope"
    }


def test_rerun_preview_keeps_deferred_ontology_gaps_unresolved() -> None:
    module = load_module(
        PREVIEW_TOOL_PATH,
        "idea_to_spec_rerun_preview_deferred_gap_test",
    )
    rerun_input = copy.deepcopy(ready_rerun_input())
    ontology_hints = rerun_input["rerun_input_overlay"]["ontology_review_hints"]
    ontology_hints["project_local_terms"] = []
    ontology_hints["deferred_terms"] = [
        {
            "answer_kind": "defer",
            "request_id": "clarification.repair.review-unresolved-gaps",
            "target_ref": "candidate_graph.gaps",
            "reason": "Needs ontology owner decision.",
        }
    ]

    report = module.build_idea_to_spec_rerun_preview(
        rerun_input=rerun_input,
        intake=intake_artifact(),
        candidate_graph=candidate_graph_artifact(),
    )

    gap_preview = report["rerun_preview"]["ontology_gap_preview"]
    assert gap_preview["decision_count"] == 1
    assert gap_preview["resolved_ontology_gap_count"] == 0
    assert gap_preview["unresolved_ontology_gap_count"] == 2
    assert {
        item["deferral_preview"]["decision"] for item in gap_preview["unresolved_ontology_gaps"]
    } == {"defer"}
    assert {item["match_kind"] for item in gap_preview["unresolved_ontology_gaps"]} == {
        "aggregate_target"
    }
    assert {item["confidence"] for item in gap_preview["unresolved_ontology_gaps"]} == {
        "aggregate_scope"
    }
    quality = report["rerun_preview"]["candidate_quality_preview"]
    assert quality["review_state"] == "candidate_quality_blocked_by_ontology_gaps"
    assert quality["ontology_gap_state"] == "unresolved"


def test_rerun_preview_uses_safe_normalized_matching_without_broad_single_word_matches() -> None:
    module = load_module(
        PREVIEW_TOOL_PATH,
        "idea_to_spec_rerun_preview_safe_matching_test",
    )
    rerun_input = copy.deepcopy(ready_rerun_input())
    ontology_hints = rerun_input["rerun_input_overlay"]["ontology_review_hints"]
    for bucket in (
        "term_bindings",
        "aliases",
        "project_local_terms",
        "rejected_terms",
        "deferred_terms",
    ):
        ontology_hints[bucket] = []
    ontology_hints["project_local_terms"] = [
        {
            "term": "Payment Record",
            "request_id": "clarification.payment-record",
            "target_ref": "candidate_graph.gaps",
        },
        {
            "term": "Local Notification",
            "request_id": "clarification.local-notification",
            "target_ref": "candidate_graph.gaps",
        },
        {
            "term": "Renewal Date",
            "request_id": "clarification.renewal-date",
            "target_ref": "candidate_graph.gaps",
        },
        {
            "term": "Subscription",
            "request_id": "clarification.subscription",
            "target_ref": "candidate_graph.gaps",
        },
    ]
    candidate_graph = candidate_graph_artifact()
    candidate_graph["nodes"][0]["gaps"] = [
        {
            "id": "ontology-gap.payment-recorded",
            "kind": "ontology_gap",
            "source_ref": "domain-event.payment-recorded",
            "term": "Payment Recorded",
        },
        {
            "id": "ontology-gap.local-notification-service",
            "kind": "ontology_gap",
            "source_ref": "external-system.local-notification-service",
            "term": "Local Notification Service",
        },
        {
            "id": "ontology-gap.local-notification-service-update",
            "kind": "ontology_gap",
            "source_ref": "domain-event.local-notification-service-update",
            "term": "Local Notification Service Update",
        },
        {
            "id": "ontology-gap.renewal-date-updated",
            "kind": "ontology_gap",
            "source_ref": "domain-event.renewal-date-updated",
            "term": "Renewal Date Updated",
        },
        {
            "id": "ontology-gap.subscription-added",
            "kind": "ontology_gap",
            "source_ref": "domain-event.subscription-added",
            "term": "Subscription Added",
        },
        {
            "id": "ontology-gap.subscription-cancelled",
            "kind": "ontology_gap",
            "source_ref": "domain-event.subscription-cancelled",
            "term": "Subscription Cancelled",
        },
    ]

    report = module.build_idea_to_spec_rerun_preview(
        rerun_input=rerun_input,
        intake=intake_artifact(),
        candidate_graph=candidate_graph,
    )

    gap_preview = report["rerun_preview"]["ontology_gap_preview"]
    resolved = {item["term"]: item for item in gap_preview["resolved_ontology_gaps"]}
    unresolved_terms = {item["term"] for item in gap_preview["unresolved_ontology_gaps"]}
    assert gap_preview["resolved_ontology_gap_count"] == 3
    assert resolved["Payment Recorded"]["match_kind"] == "safe_inflection"
    assert resolved["Payment Recorded"]["confidence"] == "medium"
    assert resolved["Payment Recorded"]["decision_term"] == "Payment Record"
    assert resolved["Local Notification Service"]["match_kind"] == "safe_phrase_match"
    assert resolved["Local Notification Service"]["confidence"] == "low"
    assert resolved["Renewal Date Updated"]["match_kind"] == "safe_phrase_match"
    assert resolved["Renewal Date Updated"]["confidence"] == "low"
    assert unresolved_terms == {
        "Local Notification Service Update",
        "Subscription Added",
        "Subscription Cancelled",
    }


def test_rerun_preview_prefers_stronger_match_over_first_match() -> None:
    module = load_module(
        PREVIEW_TOOL_PATH,
        "idea_to_spec_rerun_preview_match_precedence_test",
    )
    rerun_input = copy.deepcopy(ready_rerun_input())
    ontology_hints = rerun_input["rerun_input_overlay"]["ontology_review_hints"]
    for bucket in (
        "term_bindings",
        "aliases",
        "project_local_terms",
        "rejected_terms",
        "deferred_terms",
    ):
        ontology_hints[bucket] = []
    ontology_hints["project_local_terms"] = [
        {
            "term": "Local Notification",
            "request_id": "clarification.local-notification",
            "target_ref": "candidate_graph.gaps",
        },
        {
            "term": "Local Notification Service",
            "request_id": "clarification.local-notification-service",
            "target_ref": "candidate_graph.gaps",
        },
    ]
    candidate_graph = candidate_graph_artifact()
    candidate_graph["nodes"][0]["gaps"] = [
        {
            "id": "ontology-gap.local-notification-service",
            "kind": "ontology_gap",
            "source_ref": "external-system.local-notification-service",
            "term": "Local Notification Service",
        }
    ]

    report = module.build_idea_to_spec_rerun_preview(
        rerun_input=rerun_input,
        intake=intake_artifact(),
        candidate_graph=candidate_graph,
    )

    resolved = report["rerun_preview"]["ontology_gap_preview"]["resolved_ontology_gaps"]
    assert len(resolved) == 1
    assert resolved[0]["match_kind"] == "exact"
    assert resolved[0]["decision_term"] == "Local Notification Service"
    assert resolved[0]["decision_id"] == "clarification.local-notification-service"


def test_rerun_preview_merges_active_frame_and_strips_raw_trace() -> None:
    module = load_module(
        PREVIEW_TOOL_PATH,
        "idea_to_spec_rerun_preview_active_frame_test",
    )
    rerun_input = copy.deepcopy(ready_rerun_input())
    rerun_input["rerun_input_overlay"]["intake_overlay"]["active_frame_hints"] = [
        {
            "request_id": "clarification.context",
            "target_ref": "active_frame",
            "value": {
                "domain_refs": ["domain.team_decision_log", "domain.audit"],
                "context_refs": ["context.idea_to_spec", "context.review"],
                "raw_prompt": "private prompt trace",
            },
        }
    ]

    report = module.build_idea_to_spec_rerun_preview(
        rerun_input=rerun_input,
        intake=intake_artifact(),
        candidate_graph=candidate_graph_artifact(),
    )

    frame = report["rerun_preview"]["active_frame_preview"]["active_frame"]
    assert frame["domain_refs"] == ["domain.team_decision_log", "domain.audit"]
    assert frame["context_refs"] == ["context.idea_to_spec", "context.review"]
    dumped = json.dumps(report)
    assert "private prompt trace" not in dumped


def test_rerun_preview_sanitizes_base_event_storming_entries() -> None:
    module = load_module(
        PREVIEW_TOOL_PATH,
        "idea_to_spec_rerun_preview_base_event_sanitized_test",
    )
    intake = intake_artifact()
    intake["event_storming"]["actors"] = [
        {
            "id": "actor.owner",
            "name": "Owner",
            "raw_prompt": "private prompt trace",
        }
    ]

    report = module.build_idea_to_spec_rerun_preview(
        rerun_input=ready_rerun_input(),
        intake=intake,
        candidate_graph=candidate_graph_artifact(),
    )

    actors = report["rerun_preview"]["event_storming_preview"]["event_storming"]["actors"]
    assert actors == [{"id": "actor.owner", "name": "Owner"}]
    assert "private prompt trace" not in json.dumps(report)


def test_rerun_preview_cli_writes_output(tmp_path: Path) -> None:
    rerun_input_path = tmp_path / "idea_to_spec_answer_rerun_input.json"
    intake_path = tmp_path / "idea_event_storming_intake.json"
    candidate_graph_path = tmp_path / "candidate_spec_graph.json"
    output = tmp_path / "idea_to_spec_rerun_preview.json"
    write_json(rerun_input_path, ready_rerun_input())
    write_json(intake_path, intake_artifact())
    write_json(candidate_graph_path, candidate_graph_artifact())

    result = subprocess.run(
        [
            sys.executable,
            str(PREVIEW_TOOL_PATH),
            "--rerun-input",
            str(rerun_input_path),
            "--intake",
            str(intake_path),
            "--candidate-graph",
            str(candidate_graph_path),
            "--output",
            str(output),
            "--strict",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    report = load_json(output)
    assert report["artifact_kind"] == "idea_to_spec_rerun_preview"
    assert report["readiness"]["ready"] is True
    assert "rerun_preview_ready" in result.stdout
