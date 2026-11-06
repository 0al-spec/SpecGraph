"""Each criterion retains its exact binding, expectations and C2c-owned conclusion."""

from specification_core import PredicateSpec

from traceability.criterion_provider import criterion_row

from .collection_context import CollectedCriterion


def criterion_binding(context: CollectedCriterion) -> bool:
    row, target = context.row, context.target
    projected = criterion_row(
        row.source,
        row.bindings,
        list(row.findings),
        row.journal,
        row.observation,
    )
    if (row.binding_integrity, row.observed_outcome) != (
        projected.binding_integrity,
        projected.observed_outcome,
    ):
        return False
    if len(row.bindings) != 1 or row.journal is None:
        return False
    binding = row.bindings[0]
    return (
        (
            binding.pointer,
            binding.criterion_id,
            binding.contract_ref_id,
            binding.passport_binding_id,
        )
        == (
            target.source.pointer,
            target.criterion_id,
            target.contract_ref_id,
            target.passport_binding_id,
        )
        and row.journal == context.declared_journal
        and context.expectations == target.expectations
        and binding.attempt == 0
    )


COLLECTION_CRITERION_SPEC: PredicateSpec[CollectedCriterion] = PredicateSpec(
    criterion_binding,
    name="verification.collection_criterion_binding",
)
