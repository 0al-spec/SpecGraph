# Source for the graph-before-implementation rule

The operator asked SpecGraph to define the product through a coherent
specification graph before implementation. Parent specifications resolve the
abstract decisions that constrain their descendants. Every branch in the
agreed scope must reach a leaf that can be implemented and verified. Delay
implementation pilots until the graph is ready, then use requirements to
choose what technical constraints to investigate.

The operator asked to state the rule at SpecGraph's highest instruction level
and make it applicable across projects.

The operator clarified the order of implementation. Start with the leaf
specifications and use a modular, composable architecture governed by the
specifications of the particular project.
