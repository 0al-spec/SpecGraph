# 0155 Product Workspace Active Candidate Source

Operator intent: make the product idea-to-spec active candidate source generic
so Team Decision Log remains the first pilot carried by data, not a
pilot-specific system flow.

Bounded scope:

- add a review-only active candidate source artifact;
- prove candidate/workspace identity from the active candidate config;
- require `product_workspace` governance and `product_spec_workspace` target
  repository role;
- link event-storming intake, candidate graph, pre-SIB report, repair loop,
  materialization, and promotion gate;
- keep public placeholders when no valid active source exists;
- prevent fixture/demo placeholder handoff leakage.

Out of scope:

- prompt-agent execution;
- SpecSpace mutation UI;
- canonical SpecGraph spec mutation;
- ontology package writes;
- Git branch, commit, PR, merge, or read-model publishing.
