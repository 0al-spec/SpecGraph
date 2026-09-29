"""SpecificationCore rules for candidate approval intent state."""

from specification_core import FirstMatch, PredicateSpec, TraceRecorder

from idea_maturity_candidate_approval_spec import candidate_approval_state
from idea_maturity_lifecycle_context import LifecycleStateContext, decide

_SPEC = FirstMatch.with_fallback(
    (
        (
            PredicateSpec(
                lambda c: (
                    "approval_intent" not in c.artifacts and candidate_approval_state(c) != "ready"
                ),
                name="approval_intent.not_reached",
            ),
            "not_reached",
        ),
        (
            PredicateSpec(
                lambda c: (
                    "approval_intent" not in c.artifacts and candidate_approval_state(c) == "ready"
                ),
                name="approval_intent.unavailable_after_ready",
            ),
            "not_available",
        ),
        (
            PredicateSpec(
                lambda c: (
                    "approval_intent" in c.artifacts
                    and (
                        c.integer(c.summary("approval_intent").get("active_intent_count")) > 0
                        or "requested" in c.text(c.summary("approval_intent").get("status"))
                    )
                ),
                name="approval_intent.requested",
            ),
            "requested",
        ),
        (
            PredicateSpec(
                lambda c: (
                    "approval_intent" in c.artifacts
                    and "blocked" in c.text(c.summary("approval_intent").get("status"))
                ),
                name="approval_intent.blocked",
            ),
            "blocked",
        ),
    ),
    "unknown",
    name="candidate_approval_intent_state",
)


def candidate_approval_intent_state(
    context: LifecycleStateContext, *, recorder: TraceRecorder | None = None
) -> str:
    return decide(_SPEC, context, recorder)
