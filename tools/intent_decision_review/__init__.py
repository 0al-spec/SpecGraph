"""Coverage policy; structural evidence never constitutes semantic approval."""

from specification_core import FirstMatch, TraceRecorder

from .context import DecisionReviewFacts
from .invalid_spec import InvalidDecisionReviewSpec
from .not_required_spec import DecisionReviewNotRequiredSpec
from .unresolved_spec import UnresolvedDecisionReviewSpec

CONTRACT = "specgraph.intent-decision-review/v1"
DECISION = FirstMatch.with_fallback(
    (
        (InvalidDecisionReviewSpec(), "invalid"),
        (UnresolvedDecisionReviewSpec(), "needs_review"),
        (DecisionReviewNotRequiredSpec(), "not_required"),
    ),
    fallback="covered",
    name=CONTRACT,
)


def decide(facts: DecisionReviewFacts) -> tuple[str, list[dict[str, str]]]:
    recorder = TraceRecorder()
    status = DECISION.decide(facts, recorder=recorder).value
    return status, [dict(name=e.name, outcome=e.outcome.value) for e in recorder.events]
