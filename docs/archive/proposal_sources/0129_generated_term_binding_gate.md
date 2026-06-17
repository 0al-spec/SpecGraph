# Source Draft: Generated Term Binding Gate

This source draft records the bounded implementation follow-up to SG-RFC-0128.

## Operator Intent

After accepted Ontology entities were modeled as canonical type symbols and the
term-binding policy became machine-readable, the next step is an executable
review gate for generated graph-facing artifacts.

The gate should catch:

- new generated terms without `ontology_gap`;
- duplicate local terms when an accepted ontology entity exists;
- deprecated or rejected term reuse;
- practical ontology observations marked accepted;
- SpecGraph topology edges treated as semantic ontology relations.

## Boundary

This slice should run in review mode first. It should produce a report and
optionally fail in explicit `--strict` mode, but it should not wire itself into
ordinary supervisor writes or mutate canonical specs.

Non-goals:

- no active prompt change;
- no prompt-agent execution;
- no Ontology package write;
- no ontology lockfile write;
- no canonical SpecGraph spec mutation;
- no SpecSpace mutation UI.
