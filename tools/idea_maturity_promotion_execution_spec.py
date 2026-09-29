"""SpecificationCore rules for promotion execution state."""

from specification_core import FirstMatch, PredicateSpec, TraceRecorder

from idea_maturity_lifecycle_context import LifecycleStateContext, decide
from idea_maturity_promotion_request_spec import promotion_request_state


def _status(c):
    return c.text(c.summary("promotion_execution").get("status")) or c.text(
        c.artifact("promotion_execution").get("status")
    )


_SPEC = FirstMatch.with_fallback(
    (
        (
            PredicateSpec(
                lambda c: (
                    not c.artifact("promotion_execution")
                    and promotion_request_state(c) == "requested"
                ),
                name="promotion_execution.not_available_after_request",
            ),
            "not_available",
        ),
        (
            PredicateSpec(
                lambda c: (
                    c.artifact("promotion_execution").get("dry_run") is True
                    or _status(c) == "dry_run"
                ),
                name="promotion_execution.dry_run",
            ),
            "dry_run",
        ),
        (
            PredicateSpec(
                lambda c: (
                    c.integer(c.summary("promotion_execution").get("error_count")) > 0
                    or c.is_failed(_status(c))
                ),
                name="promotion_execution.failed",
            ),
            "failed",
        ),
        (
            PredicateSpec(lambda c: c.is_blocked(_status(c)), name="promotion_execution.blocked"),
            "blocked",
        ),
        (
            PredicateSpec(
                lambda c: (
                    c.summary("promotion_execution").get("commit_created") is True
                    or c.summary("promotion_execution").get("review_opened") is True
                ),
                name="promotion_execution.executed",
            ),
            "executed",
        ),
        (
            PredicateSpec(
                lambda c: bool(c.artifact("promotion_execution")),
                name="promotion_execution.unknown",
            ),
            "unknown",
        ),
    ),
    "not_reached",
    name="promotion_execution_state",
)


def promotion_execution_state(
    context: LifecycleStateContext, *, recorder: TraceRecorder | None = None
) -> str:
    return decide(_SPEC, context, recorder)
