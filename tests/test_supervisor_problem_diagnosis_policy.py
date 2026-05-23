from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = REPO_ROOT / "tools" / "supervisor_problem_diagnosis_policy.json"
CONTRACT_DOC_PATH = REPO_ROOT / "docs" / "supervisor_problem_diagnosis_viewer_contract.md"
PROPOSAL_PATH = (
    REPO_ROOT / "docs" / "proposals" / "0055_supervisor_problem_diagnosis_and_recovery_planner.md"
)


def load_policy() -> dict[str, object]:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def test_policy_has_top_level_identity_and_layout() -> None:
    policy = load_policy()

    assert policy["artifact_kind"] == "supervisor_problem_diagnosis_policy"
    assert policy["schema_version"] == 1
    assert policy["proposal_source"] == (
        "docs/proposals/0055_supervisor_problem_diagnosis_and_recovery_planner.md"
    )
    assert policy["repository_layout"] == {
        "diagnosis_artifact": "runs/supervisor_problem_diagnosis.json"
    }


def test_policy_defines_read_only_diagnosis_contract() -> None:
    policy = load_policy()

    contract = policy["diagnosis_contract"]
    assert contract["artifact_kind"] == "supervisor_problem_diagnosis"
    assert contract["schema_version"] == 1
    assert contract["canonical_mutations_allowed"] is False
    assert contract["tracked_artifacts_written"] is False

    required = set(contract["required_sections"])
    assert {
        "target",
        "diagnosis",
        "detected_problems",
        "safe_next_actions",
        "blocked_actions",
        "validation_plan",
        "policy_reference",
    } <= required

    overall_statuses = set(contract["overall_statuses"])
    assert {"clean", "actionable", "hard_stop", "insufficient_evidence"} <= overall_statuses


def test_policy_lists_initial_problem_vocabulary() -> None:
    policy = load_policy()

    problem_ids = {problem["id"] for problem in policy["problem_classes"]}
    expected = {
        "runtime_residue",
        "quota_or_provider_failure",
        "split_required_candidate_without_proposal_path",
        "false_dependency_atomicity",
        "missing_trace_contract",
        "missing_evidence_contract",
        "stale_queue_pressure",
        "malformed_or_stale_artifact",
        "repeated_same_failure",
    }
    assert expected == problem_ids


def test_each_problem_class_has_required_fields_and_known_severity() -> None:
    policy = load_policy()
    severities = set(policy["severity_levels"])
    safe_actions = set(policy["safe_action_vocabulary"])
    hard_stop_reasons = set(policy["hard_stop_reasons"])

    for problem in policy["problem_classes"]:
        assert problem["id"]
        assert problem["summary"]
        assert problem["default_severity"] in severities
        assert problem["safe_actions"], problem["id"]
        assert problem["hard_stop_when"], problem["id"]
        for action in problem["safe_actions"]:
            assert action in safe_actions, (problem["id"], action)
        for stop in problem["hard_stop_when"]:
            assert stop in hard_stop_reasons, (problem["id"], stop)


def test_planner_contract_is_advisory_and_safe() -> None:
    policy = load_policy()

    planner = policy["planner_contract"]
    assert planner["advisory_only"] is True
    assert planner["one_recommendation_at_a_time"] is True
    assert planner["prefer_smallest_deterministic_action"] is True
    assert planner["must_not_loop_indefinitely"] is True
    assert planner["must_not_mutate_canonical_specs"] is True
    assert planner["must_not_approve_gates"] is True
    assert planner["must_not_merge_prs"] is True


def test_hard_stop_reasons_cover_governance_boundary() -> None:
    policy = load_policy()

    reasons = set(policy["hard_stop_reasons"])
    assert {
        "would_change_ontology",
        "would_change_policy",
        "would_expand_supervisor_authority",
        "would_approve_review_gate",
        "would_merge_pr",
        "repeated_same_failure_after_prior_recovery",
    } <= reasons


def test_viewer_contract_doc_exists_and_references_policy() -> None:
    assert CONTRACT_DOC_PATH.exists()
    text = CONTRACT_DOC_PATH.read_text(encoding="utf-8")
    assert "runs/supervisor_problem_diagnosis.json" in text
    assert "tools/supervisor_problem_diagnosis_policy.json" in text
    assert "0055_supervisor_problem_diagnosis_and_recovery_planner.md" in text


def test_policy_references_viewer_contract() -> None:
    policy = load_policy()
    assert policy["viewer_contract_reference"] == (
        "docs/supervisor_problem_diagnosis_viewer_contract.md"
    )


def test_proposal_lists_first_three_recognizer_classes() -> None:
    text = PROPOSAL_PATH.read_text(encoding="utf-8")
    for required in (
        "runtime_residue",
        "quota_or_provider_failure",
        "split_required_candidate_without_proposal_path",
    ):
        assert required in text
