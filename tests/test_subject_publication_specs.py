"""Policy contracts operate on prepared facts and have stable trace names."""

import sys
from dataclasses import replace
from pathlib import Path

import pytest
from specification_core import TraceRecorder

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

from subject_human_approval_spec import HUMAN_APPROVAL_SPEC  # noqa: E402
from subject_publication import scope_digest  # noqa: E402
from subject_publication_context import (  # noqa: E402
    HumanApprovalContext,
    ReviewedRecordContext,
    TransitionApprovalContext,
    WorkspaceAllocationContext,
)
from subject_reviewed_record_spec import REVIEWED_RECORD_SPEC  # noqa: E402
from subject_transition_approval_spec import TRANSITION_APPROVAL_SPEC  # noqa: E402
from subject_workspace_allocation_spec import WORKSPACE_ALLOCATION_SPEC  # noqa: E402


@pytest.mark.parametrize(
    "authority,outcome,expected",
    [
        ("human_project_author", "approved", True),
        ("human_project_author", "rejected", False),
        ("agent", "approved", False),
        ("", "approved", False),
    ],
)
def test_human_approval_policy(authority, outcome, expected):
    recorder = TraceRecorder()
    assert (
        HUMAN_APPROVAL_SPEC.is_satisfied_by(
            HumanApprovalContext(authority, outcome), recorder=recorder
        )
        is expected
    )
    assert recorder.events[0].name == "subject_publication.human_approval"


@pytest.mark.parametrize("requested,expected", [("same", True), ("different", False)])
def test_complete_reviewed_record_policy(requested, expected):
    recorder = TraceRecorder()
    assert (
        REVIEWED_RECORD_SPEC.is_satisfied_by(
            ReviewedRecordContext("same", requested), recorder=recorder
        )
        is expected
    )
    assert recorder.events[0].name == "subject_publication.complete_reviewed_record"


@pytest.mark.parametrize(
    "field",
    [
        "gate_type",
        "outcome",
        "decider",
        "decision_timestamp",
        "rationale",
    ],
)
def test_transition_policy_rejects_each_mismatch(field):
    context = TransitionApprovalContext(
        "review", "approved", "human:author", "human:author", "time", "time", "reason", "reason"
    )
    recorder = TraceRecorder()
    assert TRANSITION_APPROVAL_SPEC.is_satisfied_by(context, recorder=recorder)
    assert not TRANSITION_APPROVAL_SPEC.is_satisfied_by(replace(context, **{field: "different"}))
    assert recorder.events[0].name == "subject_publication.reviewed_transition"


@pytest.mark.parametrize(
    "reviewed,requested",
    [
        ({"value": True}, {"value": 1}),
        ({"value": None}, {}),
        ({"value": "1"}, {"value": 1}),
    ],
)
def test_complete_record_scope_preserves_scalar_types_and_absence(reviewed, requested):
    assert not REVIEWED_RECORD_SPEC.is_satisfied_by(
        ReviewedRecordContext(scope_digest(reviewed), scope_digest(requested))
    )


def test_complete_record_scope_ignores_mapping_key_order():
    assert REVIEWED_RECORD_SPEC.is_satisfied_by(
        ReviewedRecordContext(scope_digest({"a": 1, "b": 2}), scope_digest({"b": 2, "a": 1}))
    )


def workspace_allocation_context(**changes):
    values = {
        "allocation": {
            "workspace_identity": "workspace-a",
            "source_ref": "refs/heads/main",
            "expected_commit": "a" * 40,
            "identity_allocation_authorized": True,
            "source_ref_initialization_authorized": True,
            "declaration_sha256": "b" * 64,
        },
        "requested_workspace_identity": "workspace-a",
        "requested_source_ref": "refs/heads/main",
        "requested_expected_commit": "a" * 40,
        "requested_declaration_sha256": "b" * 64,
    }
    return WorkspaceAllocationContext(**(values | changes))


def test_workspace_allocation_policy_accepts_exact_reviewed_bootstrap():
    recorder = TraceRecorder()
    assert WORKSPACE_ALLOCATION_SPEC.is_satisfied_by(
        workspace_allocation_context(), recorder=recorder
    )
    assert recorder.events[0].name == "subject_publication.workspace_allocation"


@pytest.mark.parametrize(
    "field",
    [
        "workspace_identity",
        "source_ref",
        "expected_commit",
        "identity_allocation_authorized",
        "source_ref_initialization_authorized",
        "declaration_sha256",
    ],
)
def test_workspace_allocation_policy_rejects_each_mismatch(field):
    context = workspace_allocation_context(
        allocation={**workspace_allocation_context().allocation, field: "mismatch"}
    )
    assert not WORKSPACE_ALLOCATION_SPEC.is_satisfied_by(context)


@pytest.mark.parametrize(
    "field", ["identity_allocation_authorized", "source_ref_initialization_authorized"]
)
@pytest.mark.parametrize("value", [False, 1, 0, "true", None, []])
def test_workspace_allocation_policy_requires_literal_true(field, value):
    allocation = workspace_allocation_context().allocation
    allocation = {**allocation, field: value}
    assert not WORKSPACE_ALLOCATION_SPEC.is_satisfied_by(
        workspace_allocation_context(allocation=allocation)
    )


def test_workspace_allocation_preserves_short_circuit_before_missing_later_field():
    allocation = {
        **workspace_allocation_context().allocation,
        "workspace_identity": "another-workspace",
    }
    allocation.pop("declaration_sha256")
    assert not WORKSPACE_ALLOCATION_SPEC.is_satisfied_by(
        workspace_allocation_context(allocation=allocation)
    )
