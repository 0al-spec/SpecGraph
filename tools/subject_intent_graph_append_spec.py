"""An Intent graph append adds origins and preserves every previous record."""

from specification_core import PredicateSpec

from subject_intent_graph_context import IntentGraphAppendContext

INTENT_GRAPH_APPEND_SPEC: PredicateSpec[IntentGraphAppendContext] = PredicateSpec(
    lambda context: (
        context.before_workspace == context.after_workspace
        and len(context.after_records) > len(context.before_records)
        and set(context.before_records).issubset(context.after_records)
    ),
    name="subject_intent_graph.append_preserves_origins",
)
