from specification_core import Specification

from .context import DecisionReviewFacts


class UnresolvedDecisionReviewSpec(Specification[DecisionReviewFacts]):
    def _evaluate(self, candidate, recorder):
        return candidate.unresolved
