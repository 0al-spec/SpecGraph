"""SpecificationCore rules for read model publication state."""

from specification_core import FirstMatch, PredicateSpec, TraceRecorder

from idea_maturity_lifecycle_context import LifecycleStateContext, decide
from idea_maturity_review_spec import review_status


def _status(c):
    return c.text(c.summary("read_model_publication").get("status"))


_SPEC = FirstMatch.with_fallback(
    (
        (
            PredicateSpec(
                lambda c: c.artifact("review_status").get("review_probe_only") is True,
                name="publication.probe_only",
            ),
            "not_reached",
        ),
        (
            PredicateSpec(
                lambda c: not c.artifact("read_model_publication") and review_status(c) != "merged",
                name="publication.not_reached",
            ),
            "not_reached",
        ),
        (
            PredicateSpec(
                lambda c: not c.artifact("read_model_publication") and review_status(c) == "merged",
                name="publication.not_available",
            ),
            "not_available",
        ),
        (
            PredicateSpec(
                lambda c: (
                    _status(c) == "published"
                    or c.summary("read_model_publication").get("published") is True
                ),
                name="publication.published",
            ),
            "published",
        ),
        (
            PredicateSpec(
                lambda c: (
                    c.artifact("read_model_publication").get("dry_run") is True
                    or _status(c) == "dry_run"
                ),
                name="publication.dry_run",
            ),
            "dry_run",
        ),
        (
            PredicateSpec(
                lambda c: (
                    c.integer(c.summary("read_model_publication").get("error_count")) > 0
                    or "failed" in _status(c)
                ),
                name="publication.failed",
            ),
            "failed",
        ),
        (PredicateSpec(lambda c: "blocked" in _status(c), name="publication.blocked"), "blocked"),
    ),
    "unknown",
    name="read_model_publication_state",
)


def read_model_publication_state(
    context: LifecycleStateContext, *, recorder: TraceRecorder | None = None
) -> str:
    return decide(_SPEC, context, recorder)
