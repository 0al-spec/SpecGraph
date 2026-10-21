from specification_core import Specification

from .context import DecisionReviewFacts


class InvalidDecisionReviewSpec(Specification[DecisionReviewFacts]):
    def _evaluate(self, candidate, recorder):
        return candidate.invalid
