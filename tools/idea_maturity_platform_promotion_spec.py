"""SpecificationCore rules for platform promotion state."""

from specification_core import FirstMatch, PredicateSpec, TraceRecorder

from idea_maturity_candidate_approval_decision_spec import candidate_approval_decision_state
from idea_maturity_lifecycle_context import LifecycleStateContext, decide
from idea_maturity_promotion_execution_spec import promotion_execution_state
from idea_maturity_promotion_request_spec import promotion_request_state

_SPEC = FirstMatch.with_fallback(
    (
        (
            PredicateSpec(
                lambda c: promotion_execution_state(c) not in {"not_reached", "not_available"},
                name="platform_promotion.execution_state",
            ),
            "__execution__",
        ),
        (
            PredicateSpec(
                lambda c: promotion_request_state(c) == "requested",
                name="platform_promotion.requested",
            ),
            "requested",
        ),
        (
            PredicateSpec(
                lambda c: candidate_approval_decision_state(c) == "materialized",
                name="platform_promotion.ready",
            ),
            "ready",
        ),
    ),
    "not_reached",
    name="platform_promotion_state",
)


def platform_promotion_state(
    context: LifecycleStateContext, *, recorder: TraceRecorder | None = None
) -> str:
    value = decide(_SPEC, context, recorder)
    return (
        promotion_execution_state(context, recorder=recorder) if value == "__execution__" else value
    )
