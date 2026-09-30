"""Conventional extraction control for the decision-counts experiment."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class DecisionStateCounts:
    accepted: int
    rejected: int
    clarification: int


def count_decision_states(records: Sequence[Mapping[str, object]]) -> DecisionStateCounts:
    return DecisionStateCounts(
        accepted=sum(1 for record in records if record["decision_state"] == "accepted"),
        rejected=sum(1 for record in records if record["decision_state"] == "rejected"),
        clarification=sum(
            1 for record in records if record["decision_state"] == "needs_clarification"
        ),
    )
