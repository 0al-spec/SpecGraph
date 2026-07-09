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


def workflow_topology_intake() -> dict[str, object]:
    intake = intake_artifact()
    intake["event_storming"] = {
        "actors": [{"id": "actor.household-member", "name": "Household member"}],
        "domain_events": [
            {"id": "event.pantry-item-recorded", "statement": "Pantry item recorded"}
        ],
        "commands": [{"id": "command.record-pantry-item", "name": "Record pantry item"}],
        "policies": [{"id": "policy.expiration-reminder", "name": "Expiration reminder"}],
        "external_systems": [],
        "constraints": [],
        "risks": [],
        "assumptions": [],
        "vocabulary_questions": [],
    }
    return intake


def workflow_topology_candidate_graph() -> dict[str, object]:
    graph = candidate_graph_artifact()
    graph["nodes"] = [
        {
            "id": "candidate-spec.product-boundary",
            "kind": "product_boundary",
            "source_event_refs": [],
            "gaps": [],
        },
        {
            "id": "candidate-spec.record-pantry-item",
            "kind": "behavior_requirement",
            "source_event_refs": ["command.record-pantry-item"],
            "gaps": [],
        },
        {
            "id": "candidate-spec.expiration-reminder",
            "kind": "policy_constraint",
            "source_event_refs": ["policy.expiration-reminder"],
            "gaps": [],
        },
    ]
    return graph


def rerun_input_with_workflow_relations(relations: list[dict[str, object]]) -> dict[str, object]:
    return {
        "artifact_kind": "idea_to_spec_answer_rerun_input",
        "schema_version": 1,
        "contract_ref": "specgraph.idea-to-spec.answer-rerun-input.v0.1",
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
        "readiness": {"ready": True, "review_state": "rerun_input_ready"},
        "rerun_input_overlay": {
            "intake_overlay": {
                "active_frame_hints": [],
                "event_storming_hints": [
                    {
                        "request_id": "clarification.depth.workflow-topology",
                        "request_kind": "workflow_topology_gap",
                        "answer_kind": "answer_question",
                        "target_artifact": "runs/idea_event_storming_intake.json",
                        "target_ref": "event_storming_hints.workflow_relations",
                        "value": {"workflow_relations": relations},
                    }
                ],
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
        },
    }


def candidate_graph_with_candidate_gaps() -> dict[str, object]:
    graph = candidate_graph_artifact()
    graph["nodes"] = [
        {
            "id": "candidate-spec.local-storage",
            "gaps": [
                {
                    "id": "gap.local-only-storage.enforcement-mechanism",
                    "kind": "implementation_gap",
                    "source_ref": "constraint.local-only-storage",
                    "statement": "Define the enforcement mechanism for local-only storage.",
                }
            ],
        },
        {
            "id": "candidate-spec.renewal-risk",
            "gaps": [
                {
                    "id": "gap.risk.stale-renewal-date",
                    "kind": "risk_requires_review",
                    "source_ref": "risk.stale-renewal-date",
                    "statement": "Clarify whether stale renewal dates are accepted risk.",
                }
            ],
        },
        {
            "id": "candidate-spec.required-fields",
            "gaps": [
                {
                    "id": "gap.required-fields.enforcement-mechanism",
                    "kind": "implementation_gap",
                    "source_ref": "constraint.required-fields",
                    "statement": "Define required fields enforcement.",
                }
            ],
        },
    ]
    return graph


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


def test_rerun_preview_resolves_targeted_candidate_gaps_without_fuzzy_matching() -> None:
    module = load_module(
        PREVIEW_TOOL_PATH,
        "idea_to_spec_rerun_preview_candidate_gap_test",
    )
    rerun_input = copy.deepcopy(ready_rerun_input())
    overlay = rerun_input["rerun_input_overlay"]
    ontology_hints = overlay["ontology_review_hints"]
    for bucket in (
        "term_bindings",
        "aliases",
        "project_local_terms",
        "rejected_terms",
        "deferred_terms",
    ):
        ontology_hints[bucket] = []
    overlay["candidate_review_hints"]["other"] = [
        {
            "answer_kind": "answer_question",
            "request_id": "clarification.local-storage",
            "request_kind": "candidate_gap",
            "target_artifact": "runs/candidate_spec_graph.json",
            "target_ref": (
                "candidate-spec.local-storage.gaps.gap.local-only-storage.enforcement-mechanism"
            ),
            "value": "Store subscription records in a local-only encrypted file.",
        },
        {
            "answer_kind": "provide_candidate_context",
            "request_id": "clarification.renewal-risk",
            "request_kind": "candidate_gap",
            "target_artifact": "runs/candidate_spec_graph.json",
            "target_ref": "candidate-spec.renewal-risk.gaps.gap.risk.stale-renewal-date",
            "value": {"risk_acceptance": "Show a stale-renewal warning before reminders."},
        },
        {
            "answer_kind": "defer_candidate",
            "request_id": "clarification.required-fields",
            "request_kind": "candidate_gap",
            "target_artifact": "runs/candidate_spec_graph.json",
            "target_ref": (
                "candidate-spec.required-fields.gaps.gap.required-fields.enforcement-mechanism"
            ),
            "value": {"reason": "Needs owner review."},
        },
    ]

    report = module.build_idea_to_spec_rerun_preview(
        rerun_input=rerun_input,
        intake=intake_artifact(),
        candidate_graph=candidate_graph_with_candidate_gaps(),
    )

    candidate_gap_preview = report["rerun_preview"]["candidate_gap_preview"]
    assert candidate_gap_preview["resolved_candidate_gap_count"] == 2
    assert candidate_gap_preview["unresolved_candidate_gap_count"] == 1
    resolved_by_gap = {
        item["gap_id"]: item for item in candidate_gap_preview["resolved_candidate_gaps"]
    }
    assert (
        resolved_by_gap["gap.local-only-storage.enforcement-mechanism"]["resolution_kind"]
        == "enforcement_mechanism_added"
    )
    assert resolved_by_gap["gap.risk.stale-renewal-date"]["resolution_kind"] == "risk_accepted"
    unresolved = candidate_gap_preview["unresolved_candidate_gaps"][0]
    assert unresolved["gap_id"] == "gap.required-fields.enforcement-mechanism"
    assert unresolved["deferral_preview"]["answer_kind"] == "defer_candidate"
    quality = report["rerun_preview"]["candidate_quality_preview"]
    assert quality["candidate_quality_metric"] == "candidate_gap_resolution_preview"
    assert quality["review_state"] == "candidate_quality_partially_improved"
    assert quality["resolved_candidate_gap_count"] == 2
    assert quality["unresolved_candidate_gap_count"] == 1
    assert report["summary"]["resolved_candidate_gap_count"] == 2
    assert report["summary"]["unresolved_candidate_gap_count"] == 1


def test_rerun_preview_resolves_explicit_candidate_reject_without_value() -> None:
    module = load_module(
        PREVIEW_TOOL_PATH,
        "idea_to_spec_rerun_preview_candidate_reject_test",
    )
    rerun_input = copy.deepcopy(ready_rerun_input())
    rerun_input["rerun_input_overlay"]["ontology_review_hints"]["project_local_terms"] = []
    rerun_input["rerun_input_overlay"]["candidate_review_hints"]["other"] = [
        {
            "answer_kind": "reject",
            "request_id": "clarification.local-storage",
            "request_kind": "candidate_gap",
            "target_ref": (
                "candidate-spec.local-storage.gaps.gap.local-only-storage.enforcement-mechanism"
            ),
            "value": {},
        }
    ]

    report = module.build_idea_to_spec_rerun_preview(
        rerun_input=rerun_input,
        intake=intake_artifact(),
        candidate_graph=candidate_graph_with_candidate_gaps(),
    )

    candidate_gap_preview = report["rerun_preview"]["candidate_gap_preview"]
    assert candidate_gap_preview["resolved_candidate_gap_count"] == 1
    resolved = candidate_gap_preview["resolved_candidate_gaps"][0]
    assert resolved["gap_id"] == "gap.local-only-storage.enforcement-mechanism"
    assert resolved["resolution_kind"] == "gap_rejected"


def test_rerun_preview_does_not_resolve_candidate_gap_from_other_hint_kind() -> None:
    module = load_module(
        PREVIEW_TOOL_PATH,
        "idea_to_spec_rerun_preview_candidate_non_candidate_hint_test",
    )
    rerun_input = copy.deepcopy(ready_rerun_input())
    rerun_input["rerun_input_overlay"]["ontology_review_hints"]["project_local_terms"] = []
    rerun_input["rerun_input_overlay"]["candidate_review_hints"]["acceptance_criteria"] = [
        {
            "answer_kind": "provide_acceptance_criterion",
            "request_id": "clarification.acceptance",
            "request_kind": "graph_repair",
            "target_ref": (
                "candidate-spec.local-storage.gaps.gap.local-only-storage.enforcement-mechanism"
            ),
            "value": "Reviewer can verify local-only persistence.",
        }
    ]

    report = module.build_idea_to_spec_rerun_preview(
        rerun_input=rerun_input,
        intake=intake_artifact(),
        candidate_graph=candidate_graph_with_candidate_gaps(),
    )

    candidate_gap_preview = report["rerun_preview"]["candidate_gap_preview"]
    assert candidate_gap_preview["resolved_candidate_gap_count"] == 0
    assert {item["gap_id"] for item in candidate_gap_preview["unresolved_candidate_gaps"]} == {
        "gap.local-only-storage.enforcement-mechanism",
        "gap.risk.stale-renewal-date",
        "gap.required-fields.enforcement-mechanism",
    }


def test_rerun_preview_matches_candidate_gap_only_by_node_scoped_gap_ref() -> None:
    module = load_module(
        PREVIEW_TOOL_PATH,
        "idea_to_spec_rerun_preview_candidate_source_ref_test",
    )
    rerun_input = copy.deepcopy(ready_rerun_input())
    rerun_input["rerun_input_overlay"]["ontology_review_hints"]["project_local_terms"] = []
    rerun_input["rerun_input_overlay"]["candidate_review_hints"]["other"] = [
        {
            "answer_kind": "answer_question",
            "request_id": "clarification.local-storage",
            "request_kind": "candidate_gap",
            "target_ref": "constraint.local-only-storage",
            "value": "Store records locally.",
        }
    ]

    report = module.build_idea_to_spec_rerun_preview(
        rerun_input=rerun_input,
        intake=intake_artifact(),
        candidate_graph=candidate_graph_with_candidate_gaps(),
    )

    candidate_gap_preview = report["rerun_preview"]["candidate_gap_preview"]
    assert candidate_gap_preview["resolved_candidate_gap_count"] == 0
    assert candidate_gap_preview["unresolved_candidate_gap_count"] == 3


def test_rerun_preview_requires_substantive_candidate_gap_answer_content() -> None:
    module = load_module(
        PREVIEW_TOOL_PATH,
        "idea_to_spec_rerun_preview_candidate_empty_value_test",
    )
    rerun_input = copy.deepcopy(ready_rerun_input())
    rerun_input["rerun_input_overlay"]["ontology_review_hints"]["project_local_terms"] = []
    rerun_input["rerun_input_overlay"]["candidate_review_hints"]["other"] = [
        {
            "answer_kind": "answer_question",
            "request_id": "clarification.local-storage",
            "request_kind": "candidate_gap",
            "target_ref": (
                "candidate-spec.local-storage.gaps.gap.local-only-storage.enforcement-mechanism"
            ),
            "value": [{"raw_prompt": "private trace"}, ""],
        }
    ]

    report = module.build_idea_to_spec_rerun_preview(
        rerun_input=rerun_input,
        intake=intake_artifact(),
        candidate_graph=candidate_graph_with_candidate_gaps(),
    )

    candidate_gap_preview = report["rerun_preview"]["candidate_gap_preview"]
    assert candidate_gap_preview["resolved_candidate_gap_count"] == 0
    unresolved = {
        item["gap_id"]: item for item in candidate_gap_preview["unresolved_candidate_gaps"]
    }
    local_storage = unresolved["gap.local-only-storage.enforcement-mechanism"]
    assert local_storage["review_preview"]["value"] == [{}, ""]


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


def test_rerun_preview_applies_typed_workflow_relation_hints() -> None:
    module = load_module(
        PREVIEW_TOOL_PATH,
        "idea_to_spec_rerun_preview_workflow_relations_test",
    )
    rerun_input = rerun_input_with_workflow_relations(
        [
            {
                "relation": "actor_triggers_command",
                "source_ref": "actor.household-member",
                "target_ref": "command.record-pantry-item",
            },
            {
                "relation": "command_emits_event",
                "source_ref": "command.record-pantry-item",
                "target_ref": "event.pantry-item-recorded",
            },
            {
                "relation": "event_informs_policy",
                "source_ref": "event.pantry-item-recorded",
                "target_ref": "policy.expiration-reminder",
            },
        ]
    )

    report = module.build_idea_to_spec_rerun_preview(
        rerun_input=rerun_input,
        intake=workflow_topology_intake(),
        candidate_graph=workflow_topology_candidate_graph(),
    )

    assert report["readiness"]["ready"] is True
    event_storming = report["rerun_preview"]["event_storming_preview"]["event_storming"]
    command = event_storming["commands"][0]
    policy = event_storming["policies"][0]
    assert command["actor_refs"] == ["actor.household-member"]
    assert command["produces_event_refs"] == ["event.pantry-item-recorded"]
    assert policy["trigger_event_refs"] == ["event.pantry-item-recorded"]
    topology = report["rerun_preview"]["workflow_topology_preview"]
    assert topology["workflow_edge_count"] == 3
    assert topology["topology_relation_counts"]["actor_triggers_command"] == 1
    assert topology["topology_relation_counts"]["command_emits_event"] == 1
    assert topology["topology_relation_counts"]["event_informs_policy"] == 1
    assert all(edge["review_only"] is True for edge in topology["workflow_edges"])
    assert report["summary"]["workflow_relation_hint_count"] == 3


def test_rerun_preview_preserves_distinct_workflow_edges_with_same_endpoints() -> None:
    module = load_module(
        PREVIEW_TOOL_PATH,
        "idea_to_spec_rerun_preview_workflow_relation_distinct_edges_test",
    )
    intake = workflow_topology_intake()
    intake["event_storming"]["actors"].append(
        {"id": "actor.shopping-planner", "name": "Shopping planner"}
    )
    rerun_input = rerun_input_with_workflow_relations(
        [
            {
                "relation": "actor_triggers_command",
                "source_ref": "actor.household-member",
                "target_ref": "command.record-pantry-item",
            },
            {
                "relation": "actor_triggers_command",
                "source_ref": "actor.shopping-planner",
                "target_ref": "command.record-pantry-item",
            },
        ]
    )

    report = module.build_idea_to_spec_rerun_preview(
        rerun_input=rerun_input,
        intake=intake,
        candidate_graph=workflow_topology_candidate_graph(),
    )

    topology = report["rerun_preview"]["workflow_topology_preview"]
    assert report["readiness"]["ready"] is True
    assert topology["workflow_edge_count"] == 2
    assert topology["topology_relation_counts"]["actor_triggers_command"] == 2
    assert {tuple(edge["source_event_refs"]) for edge in topology["workflow_edges"]} == {
        ("actor.household-member", "command.record-pantry-item"),
        ("actor.shopping-planner", "command.record-pantry-item"),
    }


def test_rerun_preview_blocks_workflow_topology_when_boundary_node_missing() -> None:
    module = load_module(
        PREVIEW_TOOL_PATH,
        "idea_to_spec_rerun_preview_workflow_relation_boundary_test",
    )
    candidate_graph = workflow_topology_candidate_graph()
    candidate_graph["nodes"] = [
        node for node in candidate_graph["nodes"] if node["id"] != "candidate-spec.product-boundary"
    ]
    rerun_input = rerun_input_with_workflow_relations(
        [
            {
                "relation": "actor_triggers_command",
                "source_ref": "actor.household-member",
                "target_ref": "command.record-pantry-item",
            }
        ]
    )

    report = module.build_idea_to_spec_rerun_preview(
        rerun_input=rerun_input,
        intake=workflow_topology_intake(),
        candidate_graph=candidate_graph,
    )

    assert report["readiness"]["ready"] is False
    assert "workflow_topology_boundary_missing" in finding_ids(report)
    topology = report["rerun_preview"]["workflow_topology_preview"]
    assert topology["workflow_edge_count"] == 0


def test_rerun_preview_reports_unmapped_workflow_relation_endpoint() -> None:
    module = load_module(
        PREVIEW_TOOL_PATH,
        "idea_to_spec_rerun_preview_workflow_relation_unmapped_test",
    )
    candidate_graph = workflow_topology_candidate_graph()
    candidate_graph["nodes"] = [
        node
        for node in candidate_graph["nodes"]
        if node["id"] != "candidate-spec.record-pantry-item"
    ]
    rerun_input = rerun_input_with_workflow_relations(
        [
            {
                "relation": "command_emits_event",
                "source_ref": "command.record-pantry-item",
                "target_ref": "event.pantry-item-recorded",
            }
        ]
    )

    report = module.build_idea_to_spec_rerun_preview(
        rerun_input=rerun_input,
        intake=workflow_topology_intake(),
        candidate_graph=candidate_graph,
    )

    assert report["readiness"]["ready"] is False
    assert "workflow_topology_endpoint_unmapped" in finding_ids(report)
    topology = report["rerun_preview"]["workflow_topology_preview"]
    assert topology["workflow_edge_count"] == 0


def test_rerun_preview_blocks_wrong_kind_workflow_relation_hint() -> None:
    module = load_module(
        PREVIEW_TOOL_PATH,
        "idea_to_spec_rerun_preview_workflow_relation_kind_test",
    )
    rerun_input = rerun_input_with_workflow_relations(
        [
            {
                "relation": "command_emits_event",
                "source_ref": "actor.household-member",
                "target_ref": "event.pantry-item-recorded",
            }
        ]
    )

    report = module.build_idea_to_spec_rerun_preview(
        rerun_input=rerun_input,
        intake=workflow_topology_intake(),
        candidate_graph=workflow_topology_candidate_graph(),
    )

    assert report["readiness"]["ready"] is False
    assert "workflow_relation_hint_kind_mismatch" in finding_ids(report)
    topology = report["rerun_preview"]["workflow_topology_preview"]
    assert topology["workflow_edge_count"] == 0


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
