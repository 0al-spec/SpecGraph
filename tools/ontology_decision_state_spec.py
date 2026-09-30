"""Read-only counts of operator decision states; no import or approval authority."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from specification_core import PredicateSpec

ACCEPTED = PredicateSpec(lambda state: state == "accepted", name="ontology_decision.accepted")
REJECTED = PredicateSpec(lambda state: state == "rejected", name="ontology_decision.rejected")
NEEDS_CLARIFICATION = PredicateSpec(
    lambda state: state == "needs_clarification", name="ontology_decision.needs_clarification"
)


@dataclass(frozen=True)
class DecisionStateCounts:
    accepted: int
    rejected: int
    clarification: int


def count_decision_states(records: Sequence[Mapping[str, object]]) -> DecisionStateCounts:
    """Count exact state values in already prepared report rows.

    Unknown values contribute to no bucket. A missing decision_state remains a
    KeyError, as in the original report code. Keep the three traversal passes
    so this extraction preserves evaluation order as well as report counts.
    """
    return DecisionStateCounts(
        accepted=sum(1 for row in records if ACCEPTED.is_satisfied_by(row["decision_state"])),
        rejected=sum(1 for row in records if REJECTED.is_satisfied_by(row["decision_state"])),
        clarification=sum(
            1 for row in records if NEEDS_CLARIFICATION.is_satisfied_by(row["decision_state"])
        ),
    )
