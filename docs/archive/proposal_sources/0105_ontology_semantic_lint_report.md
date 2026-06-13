# Ontology Semantic Lint Report

## Source Intent

The Ontology-SpecGraph-SpecSpace line now has a semantic policy and a typed
context pack. The next useful slice is a deterministic lint report that converts
that context into review findings, so supervisor gates and SpecSpace review
surfaces can distinguish accepted vocabulary from aliases, unknown terms,
deprecated terms, and relation conflicts.

## Requested Work

- Build `ontology_semantic_lint_report` from the `0104` semantic context pack.
- Include findings, blocking findings, review-required findings, candidate
  ontology delta terms, and recommended actions.
- Preserve authority boundaries: the lint report is evidence for review, not
  canonical ontology authority and not permission to mutate specs or write
  Ontology deltas.
- Keep the output deterministic and local under `runs/`.

## Follow-Up Shape

The following bounded slice should transform lint-report candidate terms into
an explicit ontology delta candidate review packet, still without writing
Ontology packages or SpecGraph canonical specs automatically.
