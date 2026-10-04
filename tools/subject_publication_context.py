"""Immutable facts for publication policies; parsing and Git I/O stay in adapters."""

from collections.abc import Mapping
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
    allocation: Mapping[str, object]
    requested_workspace_identity: str
    requested_source_ref: str
    requested_expected_commit: str
    requested_declaration_sha256: str
