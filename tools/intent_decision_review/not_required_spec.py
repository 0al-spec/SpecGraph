from specification_core import Specification

from .context import DecisionReviewFacts


class DecisionReviewNotRequiredSpec(Specification[DecisionReviewFacts]):
    def _evaluate(self, candidate, recorder):
        return candidate.changed_atoms == 0
