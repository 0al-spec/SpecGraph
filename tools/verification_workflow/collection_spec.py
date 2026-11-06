"""Compose collection policies while preserving the public RunRecords specification."""

from specification_core import PredicateSpec

from .collection_context import CollectionContext, collected_criterion
from .collection_criterion_spec import COLLECTION_CRITERION_SPEC
from .collection_journal_spec import COLLECTION_JOURNAL_SPEC
from .collection_observation_spec import COLLECTION_OBSERVATION_SPEC
from .collection_selection_spec import COLLECTION_SELECTION_SPEC
from .model import RunRecords, Stage


def collection_scope(records: RunRecords) -> bool:
    collection, execution = records.collection, records.execution
    if collection is None or execution is None or collection.evidence is None:
        return False
    evidence = collection.evidence
    request = records.owner.request
    selected = next(s for s in request.definition.steps if s.stage == Stage.COLLECT)
    adapter = next(
        o.adapter for o in request.registry.operations if o.identity == selected.operation_id
    )
    context = CollectionContext(request.scope, collection.provider, adapter, evidence, execution)
    if not (
        COLLECTION_SELECTION_SPEC.is_satisfied_by(context)
        and COLLECTION_JOURNAL_SPEC.is_satisfied_by(context)
    ):
        return False
    declarations = {j.artifact_id: j for j in evidence.declared_journals}
    for row, target in zip(evidence.rows, request.scope.criteria, strict=True):
        declaration = (
            declarations.get(row.bindings[0].artifact_id) if len(row.bindings) == 1 else None
        )
        criterion = collected_criterion(row, target, declaration)
        if not (
            COLLECTION_CRITERION_SPEC.is_satisfied_by(criterion)
            and COLLECTION_OBSERVATION_SPEC.is_satisfied_by(criterion)
        ):
            return False
    return True


COLLECTION_SCOPE_SPEC: PredicateSpec[RunRecords] = PredicateSpec(
    collection_scope,
    name="verification.collection_passport_scope",
)
