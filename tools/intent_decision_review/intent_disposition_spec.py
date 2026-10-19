from specification_core import Specification

from .context import RecordEvidenceFacts


class IntentDispositionSpec(Specification[RecordEvidenceFacts]):
    def _evaluate(self, candidate, recorder):
        if candidate.change_kind == "removed":
            return candidate.disposition in {"retired", "needs_review"}
        return candidate.disposition != "retired"
