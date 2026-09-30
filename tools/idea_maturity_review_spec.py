"""SpecificationCore rules for review state."""

from specification_core import FirstMatch, PredicateSpec, TraceRecorder

from idea_maturity_lifecycle_context import LifecycleStateContext, decide
from idea_maturity_promotion_execution_spec import promotion_execution_state


def _summary_status(c):
    summary = c.summary("review_status")
    return c.text(summary.get("review_status")) or c.text(summary.get("status"))


def _artifact_state(c):
    return c.text(c.artifact("review_status").get("review_state"))


_SPEC = FirstMatch.with_fallback(
    (
        (
            PredicateSpec(
                lambda c: (
                    not c.artifact("review_status")
                    and promotion_execution_state(c) == "not_reached"
                ),
                name="review.not_reached",
            ),
            "not_reached",
        ),
        (
            PredicateSpec(lambda c: not c.artifact("review_status"), name="review.not_available"),
            "not_available",
        ),
        (
            PredicateSpec(
                lambda c: (
                    c.artifact("review_status").get("review_probe_only") is True
                    and _artifact_state(c) == "merged"
                ),
                name="review.probe_merged_unknown",
            ),
            "unknown",
        ),
        (
            PredicateSpec(
                lambda c: _artifact_state(c) in {"open", "merged"}, name="review.canonical_state"
            ),
            "__canonical__",
        ),
        (PredicateSpec(lambda c: _artifact_state(c) == "closed", name="review.closed"), "blocked"),
        (
            PredicateSpec(
                lambda c: _summary_status(c) in {"open", "merged", "blocked", "unknown"},
                name="review.summary_status",
            ),
            "__summary__",
        ),
        (
            PredicateSpec(lambda c: "merged" in _summary_status(c), name="review.merged_text"),
            "merged",
        ),
        (PredicateSpec(lambda c: "open" in _summary_status(c), name="review.open_text"), "open"),
        (
            PredicateSpec(
                lambda c: "blocked" in _summary_status(c) or "failed" in _summary_status(c),
                name="review.blocked_text",
            ),
            "blocked",
        ),
    ),
    "unknown",
    name="review_status",
)


def review_status(context: LifecycleStateContext, *, recorder: TraceRecorder | None = None) -> str:
    value = decide(_SPEC, context, recorder)
    if value == "__canonical__":
        return _artifact_state(context)
    if value == "__summary__":
        return _summary_status(context)
    return value
