"""SpecificationCore decision for an individual gap-family state."""

from specification_core import FirstMatch, PredicateSpec
from tools.idea_to_spec_candidate_quality_context import GapResolutionContext

_GAP_RESOLUTION_SPEC = FirstMatch.with_fallback(
    (
        (
            PredicateSpec(
                lambda context: (
                    context.unresolved_count > 0 and context.aggregate_resolved_count > 0
                ),
                name="gap_resolution.partially_resolved",
            ),
            "partially_preview_resolved",
        ),
        (
            PredicateSpec(
                lambda context: context.resolved_count > 0,
                name="gap_resolution.all_resolved",
            ),
            "all_preview_resolved",
        ),
        (
            PredicateSpec(
                lambda context: context.unresolved_count > 0,
                name="gap_resolution.unresolved",
            ),
            "unresolved",
        ),
    ),
    None,
    name="gap_resolution_state",
)


def gap_resolution_state(context: GapResolutionContext) -> str:
    decision = _GAP_RESOLUTION_SPEC.decide(context)
    if decision.value is not None:
        return decision.value
    return context.no_gaps_state
