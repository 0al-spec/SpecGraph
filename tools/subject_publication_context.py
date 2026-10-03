"""Immutable facts for publication policies; parsing and Git I/O stay in adapters."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ReviewedRecordContext:
    reviewed_scope_sha256: str
    requested_scope_sha256: str


@dataclass(frozen=True)
class HumanApprovalContext:
    reviewer_authority: str
    outcome: str


@dataclass(frozen=True)
class TransitionApprovalContext:
    gate_type: str
    outcome: str
    decider: str
    reviewer: str
    decision_timestamp: str
    review_timestamp: str
    rationale: str
    review_rationale: str


@dataclass(frozen=True)
class WorkspaceAllocationContext:
    allocation_workspace_identity: object
    requested_workspace_identity: str
    allocation_source_ref: object
    requested_source_ref: str
    allocation_expected_commit: object
    requested_expected_commit: str
    identity_allocation_authorized: object
    source_ref_initialization_authorized: object
    allocation_declaration_sha256: object
    requested_declaration_sha256: str
