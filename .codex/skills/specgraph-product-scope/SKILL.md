---
name: specgraph-product-scope
description: Develop or review a product specification graph, or choose the next implementation slice, with attention to user outcomes and proportionality. Use for product-level SpecGraph work; use specialized ontology or evidence skills for their respective workflows.
---

# Keep product specifications proportional

Start with the owner's intent, the current product stage, the actual user
journey, and the relevant existing specifications and decisions. Inspect the
project's current sources and use its pinned SpecGraph tools where applicable.
Separate what the owner selected from the agent's interpretation, a proposed
scenario, and behavior actually observed in the product.

When refining a requirement, evaluating a gap, or choosing what to implement,
identify the user, the concrete situation, the outcome they need, and the
evidence that the issue matters. Favor work that makes a selected core journey
usable or fixes a reported or reproducible problem. Adjust the depth of the
specification and verification to the product's stage, consequences, and
available evidence. Explicit user requirements and applicable constraints still
apply, including when a product is early or has few users.

Do not turn every possible failure, missing evidence entry, or theoretical
ambiguity into a mandatory requirement, separate screen, test matrix, or new
graph node. An example can clarify an actual requirement without becoming a
new obligation. If a detail is not needed for the current outcome, leave it
open or defer it; do not fabricate a product decision. If an existing node
appears disproportionate, identify its source, impact and proposed change;
preserve user decisions and the project's review and change process.

Before writing a test or changing behavior, read the relevant current
requirement and applicable decisions. Test the behavior that matters, including
important risks when justified; do not optimize for test count, number of
nodes, an evidence badge, or a calculated completion percentage. A passing
check or a synthetic fixture does not alone establish real usage or product
readiness.

Report the concrete outcome, what was verified, and any material open decision
or limitation. If the next useful work depends on a product choice, explain
its effect in user terms and request that choice; continue independent work
when possible.
