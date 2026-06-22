# 0155 Team Decision Log Active Candidate Source

Operator intent: make Team Decision Log the first real product idea-to-spec
pilot by connecting an active candidate source to existing deterministic
idea-to-spec artifacts.

Bounded scope:

- add a review-only active candidate source artifact;
- prove candidate/workspace identity for `team-decision-log`;
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
