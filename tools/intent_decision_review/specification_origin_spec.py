from specification_core import Specification

from .context import RecordEvidenceFacts


class SpecificationOriginSpec(Specification[RecordEvidenceFacts]):
    def _evaluate(self, candidate, recorder):
        if candidate.disposition not in {"new_specification", "reuse_specification"}:
            return not candidate.specification_origins
        reuse = candidate.disposition == "reuse_specification"
        return bool(candidate.specification_origins) and all(
            recognized_head and recognized_base == reuse
            for recognized_head, recognized_base in candidate.specification_origins
        )
