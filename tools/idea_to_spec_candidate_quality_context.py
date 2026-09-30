"""Typed inputs for candidate-quality preview decisions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CandidateQualityContext:
    resolved_ontology_count: int
    unresolved_ontology_count: int
    resolved_candidate_count: int
    unresolved_candidate_count: int

    @property
    def resolved_count(self) -> int:
        return self.resolved_ontology_count + self.resolved_candidate_count

    @property
    def unresolved_count(self) -> int:
        return self.unresolved_ontology_count + self.unresolved_candidate_count


@dataclass(frozen=True)
class GapResolutionContext:
    resolved_count: int
    unresolved_count: int
    aggregate_resolved_count: int
    no_gaps_state: str
