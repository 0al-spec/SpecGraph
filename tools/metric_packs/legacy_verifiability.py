"""RFC 0226 slice B: prepare and interpret existing acceptance-status facts."""

from collections import Counter
from collections.abc import Iterable, Mapping

from .context import (
    AcceptanceCoverage,
    ScoreThreshold,
    VerifiabilityContext,
    VerifiabilityResult,
)
from .score_status_spec import SCORE_STATUS_SPEC


def prepare_verifiability_context(
    entries: Iterable[object],
    status_scores: Mapping[str, object],
    minimum_score: float,
    trigger_signal: str,
) -> VerifiabilityContext:
    """Adapt legacy JSON values, retaining their existing coercion/skip semantics."""
    observations = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        coverage = entry.get("acceptance_coverage", {})
        if not isinstance(coverage, dict):
            continue
        status = str(coverage.get("status", "")).strip()
        if not status or status == "not_defined":
            continue
        raw_score = status_scores.get(status)
        try:
            score = None if raw_score is None else float(raw_score)
        except (TypeError, ValueError):
            score = None
        observations.append(AcceptanceCoverage(status, score))
    return VerifiabilityContext(tuple(observations), minimum_score, trigger_signal)


class LegacyVerifiabilityMetric:
    """Pure compatibility interpretation; this does not activate atom-level SVC."""

    def evaluate(self, context: VerifiabilityContext) -> VerifiabilityResult:
        scores = [item.score for item in context.observations if item.score is not None]
        score = round(sum(scores) / len(scores), 3) if scores else None
        status = SCORE_STATUS_SPEC.decide(ScoreThreshold(score, context.minimum_score)).value
        counts = Counter(item.status for item in context.observations)
        return VerifiabilityResult(
            score=score,
            minimum_score=context.minimum_score,
            threshold_gap=None if score is None else round(context.minimum_score - score, 3),
            status=status,
            trigger_signal=context.trigger_signal,
            relevant_spec_count=len(context.observations),
            status_counts=tuple(sorted(counts.items())),
        )
