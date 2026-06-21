# Source: Candidate Repair Loop

Operator intent: after pre-SIB/coherence metrics exist, add the first autonomous
repair-loop artifact for candidate graphs.

The loop should consume a candidate graph and its pre-SIB report, produce repair
actions, apply safe deterministic repairs to a preview graph, and report metric
delta projections. It must stay review-only: no canonical spec mutation, no
Ontology writes, no branch/commit creation, and no prompt-agent execution.
