"""SpecificationCore policy for candidate repair-preview readiness."""

from enum import Enum

from specification_core import FirstMatch, PredicateSpec

from candidate_repair_readiness_context import CandidateRepairReadinessContext


class CandidateRepairReadiness(str, Enum):
    PREVIEW_READY = "repair_preview_ready"
    REVIEW_REQUIRED = "repair_review_required"


_SPEC = FirstMatch.with_fallback(
    (
        (
            PredicateSpec(
                lambda context: not context.has_findings and context.applied_action_count > 0,
                name="candidate_repair.applied_preview_ready",
            ),
            CandidateRepairReadiness.PREVIEW_READY,
        ),
        (
            PredicateSpec(
                lambda context: not context.has_findings and context.no_op_ready,
                name="candidate_repair.no_op_preview_ready",
            ),
            CandidateRepairReadiness.PREVIEW_READY,
        ),
    ),
    CandidateRepairReadiness.REVIEW_REQUIRED,
    name="candidate_repair_readiness",
)


def candidate_repair_readiness(
    context: CandidateRepairReadinessContext,
) -> CandidateRepairReadiness:
    decision = _SPEC.decide(context)
    assert decision.value is not None
    return decision.value
