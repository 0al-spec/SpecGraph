# Source: SpecAuthor Generated Artifact Contract

Operator intent:

- SpecAuthorAgent should not hand free-form markdown directly to graph write
  flows.
- Before write-gate validation, the agent should emit a typed
  `generated_spec_artifact` record.
- The record should carry producer identity, active ontology/domain/context,
  target artifact metadata, draft payload, term binding/gap records, calibrated
  claims, and explicit review-only materialization intent.
- The contract must not execute prompt agents, mutate canonical specs, accept
  ontology terms, write Ontology packages, or bypass the downstream ontology
  write gate.

Bounded slice:

- add a deterministic contract validator for `generated_spec_artifact`;
- add fixtures and tests for clear and review-required artifacts;
- add a Makefile target and tool docs;
- document the relationship to the 0126 prompt contract and 0136 write gate.

Deferred:

- actual SpecAuthorAgent invocation wrapper;
- prompt execution;
- graph materialization;
- SpecSpace UI for generated artifacts;
- owner-decision import or ontology package mutation.
