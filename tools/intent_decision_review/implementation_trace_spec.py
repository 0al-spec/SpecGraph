from specification_core import Specification

from .context import RecordEvidenceFacts


class ImplementationTraceSpec(Specification[RecordEvidenceFacts]):
    def _evaluate(self, candidate, recorder):
        return (
            candidate.disposition not in {"new_specification", "reuse_specification", "mechanics"}
            or candidate.implementation_count > 0
        )
