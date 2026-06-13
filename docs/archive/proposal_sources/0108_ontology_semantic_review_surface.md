# Ontology Semantic Review Surface

## Source Intent

SpecGraph now has a bounded Ontology semantic chain:

- `0104` emits a semantic context pack;
- `0105` emits a semantic lint report with blocking and review-required
  findings;
- `0106` emits a delta candidate review packet for Ontology owner review.

SpecSpace and supervisor gate flows still need one stable review surface that
combines those artifacts without forcing consumers to understand each internal
report shape independently.

## Requested Work

- Build `ontology_semantic_review_surface` from the `0104` context pack, `0105`
  lint report, and `0106` delta candidate review packet.
- Include grounding summary, blocking findings, review-required findings,
  delta candidates, unified review items, and non-mutating review actions.
- Preserve review-only authority: the surface may inform supervisor gate
  evidence and SpecSpace presentation, but it cannot accept ontology terms,
  write Ontology packages, update lockfiles, mutate canonical specs, or invoke
  prompt agents.
- Keep the output deterministic and local under `runs/`.

## Follow-Up Shape

The following slice should let SpecSpace consume the review surface as a typed
derived artifact/API. It should still avoid mutation UI until Ontology package
drafting and governance handoff boundaries are explicit.
