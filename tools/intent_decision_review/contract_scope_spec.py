from specification_core import Specification

from .context import RecordEvidenceFacts


class ContractOnlyScopeSpec(Specification[RecordEvidenceFacts]):
    def _evaluate(self, candidate, recorder):
        return candidate.disposition != "contract_only" or (
            not candidate.production_changed and candidate.implementation_count == 0
        )
