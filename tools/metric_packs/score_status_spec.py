"""SG-SPEC-0021: preserve the shared score/threshold status decision."""

from specification_core import FirstMatch, PredicateSpec

from .context import ScoreThreshold

SCORE_STATUS_SPEC: FirstMatch[ScoreThreshold, str] = FirstMatch.with_fallback(
    (
        (
            PredicateSpec(lambda c: c.score is None, name="metrics.score_absent"),
            "not_applicable",
        ),
        (
            PredicateSpec(
                lambda c: c.score is not None and c.score >= c.minimum_score,
                name="metrics.score_meets_threshold",
            ),
            "healthy",
        ),
    ),
    "below_threshold",
    name="metrics.score_status",
)
