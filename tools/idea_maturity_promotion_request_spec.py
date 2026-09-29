"""SpecificationCore rules for promotion request state."""

from specification_core import FirstMatch, PredicateSpec, TraceRecorder

from idea_maturity_candidate_approval_decision_spec import candidate_approval_decision_state
from idea_maturity_lifecycle_context import LifecycleStateContext, decide

_SPEC = FirstMatch.with_fallback(
    (
        (
            PredicateSpec(
                lambda c: (
                    not c.artifact("promotion_request")
                    and candidate_approval_decision_state(c) == "materialized"
                ),
                name="promotion_request.unavailable_after_approval",
            ),
            "not_available",
        ),
        (
            PredicateSpec(
                lambda c: (
                    c.artifact("promotion_request").get("ok") is True
                    or c.summary("promotion_request").get("promotion_ready") is True
                ),
                name="promotion_request.requested",
            ),
            "requested",
        ),
        (
            PredicateSpec(
                lambda c: c.integer(c.summary("promotion_request").get("error_count")) > 0,
                name="promotion_request.blocked",
            ),
            "blocked",
        ),
        (
            PredicateSpec(
                lambda c: bool(c.artifact("promotion_request")), name="promotion_request.unknown"
            ),
            "unknown",
        ),
    ),
    "not_reached",
    name="promotion_request_state",
)


def promotion_request_state(
    context: LifecycleStateContext, *, recorder: TraceRecorder | None = None
) -> str:
    return decide(_SPEC, context, recorder)
