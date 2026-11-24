# Build the specification graph before implementation

## Status

Proposed constitutional amendment. Human approval is required for adoption.

## Change

Add an operating principle to [CONSTITUTION.md](../../CONSTITUTION.md) that
requires specification coverage across the agreed product scope before product
implementation and implementation pilots. A leaf needs explicit behavior and
acceptance criteria. An upstream decision that could change the leaf keeps it
in draft. The graph supplies the requirements that scope pilot verification and
technical investigation.

Once the graph is ready, implement from the leaves upward. Use the module
boundaries, interfaces, and dependencies defined by that project's
specifications to compose the behavior required by parent specifications.

This amendment establishes a human-reviewed engineering rule. Its initial
realization is documentary and uses the existing review process.
[Source](../archive/proposal_sources/0236_graph_before_implementation.md)
and [draft obligation](0236_graph_before_implementation.intent.yaml)
record the rationale and proposed decision.
