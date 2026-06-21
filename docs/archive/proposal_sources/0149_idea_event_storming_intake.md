# Source: Idea Event-Storming Intake Artifact

Operator intent: start the autonomous idea-to-spec loop with a structured,
review-only event-storming intake.

The product goal is to let a user clarify a raw product idea with an agent, then
let SpecGraph generate a full candidate specification graph under ontology and
pre-SIB/coherence metrics without requiring human review on every generated
node.

This first slice is deliberately deterministic. It normalizes raw intent refs
and structured event-storming seed data into a typed intake artifact containing
actors, domain events, commands, policies, external systems, constraints, and
vocabulary questions. It does not infer missing concepts with an LLM, execute a
prompt agent, create a candidate graph, write canonical specs, write Ontology
packages, create Git branches, or publish raw intent text.
