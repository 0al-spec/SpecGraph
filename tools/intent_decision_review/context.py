"""Immutable observations for the engineering review gate."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DecisionReviewFacts:
    changed_atoms: int
    invalid: bool = False
    unresolved: bool = False


@dataclass(frozen=True)
class RecordEvidenceFacts:
    disposition: str
    change_kind: str
    implementation_count: int
    specification_origins: tuple[tuple[bool, bool], ...]
    production_changed: bool
