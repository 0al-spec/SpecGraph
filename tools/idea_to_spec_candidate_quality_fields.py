"""Named candidate-quality report fields backed by existing specifications."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from tools.idea_to_spec_candidate_quality_context import (
    CandidateQualityContext,
    GapResolutionContext,
)
from tools.idea_to_spec_candidate_quality_review_spec import candidate_quality_review_state
from tools.idea_to_spec_decision_set import SpecField, SpecSet
from tools.idea_to_spec_gap_resolution_spec import gap_resolution_state


@dataclass(frozen=True)
class GapFamilyDecision:
    resolved_count: Callable[[CandidateQualityContext], int]
    unresolved_count: Callable[[CandidateQualityContext], int]
    no_gaps_state: str

    def __call__(self, context: CandidateQualityContext) -> str:
        return gap_resolution_state(
            GapResolutionContext(
                resolved_count=self.resolved_count(context),
                unresolved_count=self.unresolved_count(context),
                aggregate_resolved_count=context.resolved_count,
                no_gaps_state=self.no_gaps_state,
            )
        )


CANDIDATE_QUALITY_FIELDS = SpecSet[CandidateQualityContext](
    fields=(
        SpecField("review_state", candidate_quality_review_state),
        SpecField(
            "ontology_gap_state",
            GapFamilyDecision(
                resolved_count=lambda context: context.resolved_ontology_count,
                unresolved_count=lambda context: context.unresolved_ontology_count,
                no_gaps_state="no_ontology_gaps",
            ),
        ),
        SpecField(
            "candidate_gap_state",
            GapFamilyDecision(
                resolved_count=lambda context: context.resolved_candidate_count,
                unresolved_count=lambda context: context.unresolved_candidate_count,
                no_gaps_state="no_candidate_gaps",
            ),
        ),
    )
)
