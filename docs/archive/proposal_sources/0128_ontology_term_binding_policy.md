# Source Draft: Ontology Term Binding Policy

This source draft records the bounded follow-up to SG-RFC-0127.

## Operator Intent

The operator wants accepted Ontology entities to behave like base types or
standard-library types for spec authoring. After SG-RFC-0127 records that
process model, the next step is to make the term-binding rule machine-readable:

```text
accepted ontology term -> reuse or bind
unknown generated term -> ontology_gap
practical ontology observation -> evidence only
SpecGraph topology edge -> topology evidence, not semantic relation
```

## Requested Boundary

This slice should not introduce a hard write gate yet. It should add a
review-first policy artifact that future generated-artifact validators can
consume.

The policy must keep authority boundaries false:

- no Ontology package writes;
- no ontology lockfile writes;
- no canonical SpecGraph mutation;
- no prompt-agent execution;
- no accepted-term decision by SpecGraph alone.

## Follow-Up Direction

The next bounded slice after this policy can add a generated-artifact gate that
consumes the policy and rejects or warns on:

- new generated terms without `ontology_gap`;
- duplicate local terms when an accepted ontology entity exists;
- deprecated or rejected term reuse;
- practical ontology observations marked accepted;
- topology edges displayed as semantic ontology relations.
