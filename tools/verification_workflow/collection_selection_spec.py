"""The collection must preserve the selected passport, source and whole inventory."""

from specification_core import PredicateSpec

from .collection_context import CollectionContext


def selected_scope(context: CollectionContext) -> bool:
    scope, evidence = context.scope, context.evidence
    selection, plan = evidence.selection, context.execution.binding_plan
    return (
        context.provider == context.selected_provider
        and evidence.passport == scope.passport.identity
        and (selection.workspace, selection.spec, selection.passport)
        == (scope.workspace, scope.spec, scope.passport.artifact)
        and plan is not None
        and selection.plan == plan.file
        and not evidence.findings
        and not evidence.unmatched_bindings
        and tuple(row.source for row in evidence.rows) == tuple(t.source for t in scope.criteria)
    )


COLLECTION_SELECTION_SPEC: PredicateSpec[CollectionContext] = PredicateSpec(
    selected_scope,
    name="verification.collection_selected_scope",
)
