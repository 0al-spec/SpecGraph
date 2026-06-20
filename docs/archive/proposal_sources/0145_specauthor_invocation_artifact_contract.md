# 0145 SpecAuthor Invocation Artifact Contract

Origin: follow-up to `0126`, `0136`, `0137`, `0143`, and `0144`.

## Intent

SpecAuthorAgent needs a typed invocation boundary before prompt-side behavior is
implemented. The boundary should connect:

- operator/user intent;
- active ontology, ontology layer, domain, context, and model applicability
  frame;
- generated artifact metadata;
- generated artifact contract report;
- ontology write-gate report;
- final operator decision state.

The artifact should prove what the agent would author under which semantic
frame, without executing prompts inside the supervisor and without mutating
canonical specs.

## Boundaries

This slice must not:

- execute SpecAuthorAgent;
- change active prompts;
- infer missing ontology context or model applicability;
- invoke downstream write gates automatically;
- materialize specs;
- write Ontology packages or lockfiles;
- mutate canonical specs;
- accept or reject ontology terms;
- import owner decisions;
- add SpecSpace UI.

## Acceptance

- `specauthor_invocation_artifact` has a deterministic contract validator.
- The contract requires active ontology/domain/context/layer/applicability
  frame.
- The contract requires links to generated artifact contract and write-gate
  reports.
- The contract keeps operator decisions acknowledgement-only.
- Regression tests cover ready, incomplete, and strict CLI paths.
