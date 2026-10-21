"""Independent evidence obligations; all must be satisfied."""

from specification_core import TraceRecorder

from .context import RecordEvidenceFacts
from .contract_scope_spec import ContractOnlyScopeSpec
from .implementation_trace_spec import ImplementationTraceSpec
from .intent_disposition_spec import IntentDispositionSpec
from .specification_origin_spec import SpecificationOriginSpec

RULES = (
    ImplementationTraceSpec(),
    SpecificationOriginSpec(),
    IntentDispositionSpec(),
    ContractOnlyScopeSpec(),
)


def inspect_evidence(facts: RecordEvidenceFacts) -> tuple[list[str], list[dict[str, str]]]:
    recorder = TraceRecorder()
    failed = [
        type(rule).__name__ for rule in RULES if not rule.is_satisfied_by(facts, recorder=recorder)
    ]
    return failed, [dict(name=e.name, outcome=e.outcome.value) for e in recorder.events]
