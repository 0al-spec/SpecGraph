"""Immutable facts shared by collection policies; no I/O or policy decisions."""

from dataclasses import dataclass

from traceability.criterion import CriterionEvidence, CriterionRow, JournalDeclaration

from .model import CriterionTarget, ExecutionRecord, ExpectedMeasurement, ToolPin, VerificationScope


@dataclass(frozen=True)
class CollectionContext:
    scope: VerificationScope
    provider: ToolPin
    selected_provider: ToolPin
    evidence: CriterionEvidence
    execution: ExecutionRecord


@dataclass(frozen=True)
class CollectedCriterion:
    row: CriterionRow
    target: CriterionTarget
    declared_journal: JournalDeclaration | None
    expectations: tuple[ExpectedMeasurement, ...] | None

    def __post_init__(self) -> None:
        if self.expectations is not None:
            object.__setattr__(self, "expectations", tuple(self.expectations))


def collected_criterion(
    row: CriterionRow,
    target: CriterionTarget,
    declared_journal: JournalDeclaration | None,
) -> CollectedCriterion:
    """Normalize expected JSON once; None retains malformed or ambiguous binding input."""
    expectations = None
    if len(row.bindings) == 1:
        try:
            expectations = tuple(
                ExpectedMeasurement(a.id, a.media_type, a.expected_json)
                for a in row.bindings[0].assertions
            )
        except (ValueError, TypeError):
            pass
    return CollectedCriterion(row, target, declared_journal, expectations)
