"""Selected journals must identify the execution outputs, producer run and revisions."""

from specification_core import PredicateSpec

from .collection_context import CollectionContext


def journal_provenance(context: CollectionContext) -> bool:
    evidence, execution, scope = context.evidence, context.execution, context.scope
    journals = {a.artifact_id: a.file for a in execution.journals}
    selected = evidence.selection.journals
    if dict(selected) != journals or len(selected) != len(journals):
        return False
    if len(evidence.declared_journals) != len(journals):
        return False
    declarations = {j.artifact_id: j for j in evidence.declared_journals}
    if set(declarations) != set(journals):
        return False
    return all(
        (j.sha256, j.run_id, j.test_source_revision, j.execution_source_revision)
        == (
            journals[j.artifact_id].sha256,
            execution.producer_run_id,
            scope.test_revision,
            scope.execution_revision,
        )
        for j in declarations.values()
    )


COLLECTION_JOURNAL_SPEC: PredicateSpec[CollectionContext] = PredicateSpec(
    journal_provenance,
    name="verification.collection_journal_provenance",
)
