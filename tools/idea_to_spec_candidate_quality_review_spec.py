"""SpecificationCore decision for the aggregate candidate-quality review state."""

from specification_core import FirstMatch, PredicateSpec, TraceRecorder
from tools.idea_to_spec_candidate_quality_context import CandidateQualityContext

_CANDIDATE_QUALITY_REVIEW_SPEC = FirstMatch.with_fallback(
    (
        (
            PredicateSpec(
                lambda context: context.unresolved_count == 0 and context.resolved_count > 0,
                name="candidate_quality.all_gaps_resolved",
            ),
            "candidate_quality_improved",
        ),
        (
            PredicateSpec(
                lambda context: context.resolved_count > 0,
                name="candidate_quality.some_gaps_resolved",
            ),
            "candidate_quality_partially_improved",
        ),
        (
            PredicateSpec(
                lambda context: (
                    context.unresolved_ontology_count > 0 and context.unresolved_candidate_count > 0
                ),
                name="candidate_quality.both_gap_families_unresolved",
            ),
            "candidate_quality_blocked_by_gaps",
        ),
        (
            PredicateSpec(
                lambda context: context.unresolved_ontology_count > 0,
                name="candidate_quality.ontology_gaps_unresolved",
            ),
            "candidate_quality_blocked_by_ontology_gaps",
        ),
        (
            PredicateSpec(
                lambda context: context.unresolved_candidate_count > 0,
                name="candidate_quality.candidate_gaps_unresolved",
            ),
            "candidate_quality_blocked_by_candidate_gaps",
        ),
    ),
    "candidate_quality_unchanged",
    name="candidate_quality_review_state",
)


def candidate_quality_review_state(
    context: CandidateQualityContext,
    *,
    recorder: TraceRecorder | None = None,
) -> str:
    decision = _CANDIDATE_QUALITY_REVIEW_SPEC.decide(context, recorder=recorder)
    assert decision.matched and decision.value is not None
    return decision.value
