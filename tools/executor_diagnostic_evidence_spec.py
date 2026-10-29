"""SG-SPEC-0003 / proposal 0056: admission of executor diagnostic evidence."""

from dataclasses import dataclass

from specification_core import PredicateSpec


@dataclass(frozen=True)
class ExecutorDiagnosticEvidenceContext:
    """Origin and kind supplied by the event adapter, never inferred from text."""

    origin: str
    event_kind: str


EXECUTOR_DIAGNOSTIC_EVIDENCE_SPEC: PredicateSpec[ExecutorDiagnosticEvidenceContext] = PredicateSpec(
    lambda context: (
        context.origin == "codex_native_event" and context.event_kind in ("error", "turn.failed")
    ),
    name="executor.diagnostic_evidence_admitted",
)
