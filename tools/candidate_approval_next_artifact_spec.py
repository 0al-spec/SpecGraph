"""Specification for the candidate approval next artifact."""

from __future__ import annotations

from specification_core import PredicateSpec
from tools.candidate_approval_readiness_context import ApprovalReadinessContext

_APPROVAL_READY_SPEC = PredicateSpec(
    lambda context: context.approval_ready,
    name="candidate_approval.ready_for_promotion_request",
)


def candidate_approval_next_artifact(context: ApprovalReadinessContext) -> str:
    if _APPROVAL_READY_SPEC.is_satisfied_by(context):
        return "Platform graph-repository promotion-request"
    return "operator decision or candidate repair before Git Service execution"
