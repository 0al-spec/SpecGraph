"""A transition agrees with the actual human review of that action."""

from specification_core import PredicateSpec

from subject_publication_context import TransitionApprovalContext

TRANSITION_APPROVAL_SPEC: PredicateSpec[TransitionApprovalContext] = PredicateSpec(
    lambda context: (
        context.gate_type == "review"
        and context.outcome == "approved"
        and context.decider == context.reviewer
        and context.decision_timestamp == context.review_timestamp
        and context.rationale == context.review_rationale
    ),
    name="subject_publication.reviewed_transition",
)
