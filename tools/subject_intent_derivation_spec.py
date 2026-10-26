"""Only explicit same-workspace Requirement revisions derive from stored Intent."""

from specification_core import PredicateSpec

from subject_intent_graph_context import IntentDerivationContext

INTENT_DERIVATION_SPEC: PredicateSpec[IntentDerivationContext] = PredicateSpec(
    lambda context: (
        context.source_class == "Requirement"
        and context.source_mode == "exact"
        and context.source_workspace == context.target_workspace
        and context.source_revision_resolved
        and context.target_revision_resolved
    ),
    name="subject_intent_graph.exact_requirement_to_intent",
)
