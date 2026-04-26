from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def load_review_feedback_policy() -> dict[str, object]:
    return json.loads((REPO_ROOT / "tools" / "review_feedback_policy.json").read_text())


def test_review_feedback_policy_defines_learning_loop_contract() -> None:
    policy = load_review_feedback_policy()

    assert policy["artifact_kind"] == "review_feedback_policy"
    assert policy["schema_version"] == 1
    assert policy["repository_layout"] == {
        "records_artifact": "tools/review_feedback_records.json",
        "future_index_artifact": "runs/review_feedback_index.json",
    }

    contract = policy["learning_loop_contract"]
    assert isinstance(contract, dict)
    assert contract["minimum_closure_rule"] == (
        "actionable_review_threads_require_prevention_action_value"
    )
    assert contract["accepted_risk_action"] == "accepted_risk_recorded"
    required_fields = set(contract["required_closure_fields"])
    assert {
        "source_thread_url",
        "reviewer",
        "review_comment_summary",
        "fix_summary",
        "root_cause_class",
        "prevention_action",
        "verification",
        "residual_risk",
    } <= required_fields


def test_review_feedback_policy_covers_recent_review_root_causes() -> None:
    policy = load_review_feedback_policy()

    root_causes = set(policy["root_cause_classes"])
    assert {
        "scope_isolation_gap",
        "artifact_contract_validation_gap",
        "policy_runtime_drift",
        "diagnostic_wording_gap",
        "test_coverage_gap",
        "process_rule_gap",
    } <= root_causes

    prevention_actions = set(policy["prevention_actions"])
    assert {
        "regression_test_added",
        "validator_added",
        "policy_rule_added",
        "agent_instruction_added",
        "documentation_rule_added",
        "accepted_risk_recorded",
    } <= prevention_actions


def test_review_feedback_policy_has_next_gap_for_each_status() -> None:
    policy = load_review_feedback_policy()

    index_contract = policy["review_feedback_index_contract"]
    assert isinstance(index_contract, dict)
    status_values = set(index_contract["status_values"])
    next_gap_defaults = policy["next_gap_defaults"]
    assert isinstance(next_gap_defaults, dict)

    assert status_values <= set(next_gap_defaults)
    assert set(index_contract["named_filters"]) >= {
        "prevention_recorded",
        "accepted_risk_recorded",
        "policy_runtime_drift",
        "artifact_contract_validation_gap",
        "scope_isolation_gap",
    }


def test_review_feedback_records_file_matches_policy_vocabularies() -> None:
    policy = load_review_feedback_policy()
    records_path = REPO_ROOT / str(policy["repository_layout"]["records_artifact"])
    records = json.loads(records_path.read_text(encoding="utf-8"))

    assert isinstance(records, list)
    root_causes = set(policy["root_cause_classes"])
    prevention_actions = set(policy["prevention_actions"])
    verification_kinds = set(policy["verification_kinds"])
    for record in records:
        assert record["root_cause_class"] in root_causes
        assert record["prevention_action"] in prevention_actions
        assert set(record["verification"]) <= verification_kinds


def test_agents_requires_review_feedback_root_cause_loop() -> None:
    agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")

    assert "tools/review_feedback_policy.json" in agents
    assert "](/Users/" not in agents
    assert "classify the root cause" in agents
    assert "prevention action" in agents
    assert "accepted risk" in agents
