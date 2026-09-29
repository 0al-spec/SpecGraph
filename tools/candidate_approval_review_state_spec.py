"""Specification for the candidate approval review state."""

from __future__ import annotations

from specification_core import PredicateSpec
from tools.candidate_approval_readiness_context import ApprovalReadinessContext

REVIEW_STATE_BY_DECISION = {
    "approved": "promotion_request_approved",
    "rejected": "candidate_promotion_rejected",
    "needs_context": "candidate_approval_needs_context",
    "superseded": "candidate_superseded",
}

_HAS_FINDINGS_SPEC = PredicateSpec(
    lambda context: context.has_findings,
    name="candidate_approval.has_findings",
)


def candidate_approval_review_state(context: ApprovalReadinessContext) -> str:
    if _HAS_FINDINGS_SPEC.is_satisfied_by(context):
        return "candidate_approval_blocked"
    return REVIEW_STATE_BY_DECISION[context.effective_state]
