# Source Draft: Layer-Aware Ontology Gap and Diff Review

Origin: follow-up to `0141 Layered Ontology Import Surface`.

Intent:

- make ontology gaps and compatibility diffs explicitly layer-aware;
- preserve the read-only authority boundary from the import surface;
- let reviewers distinguish missing objective, mechanics, execution, meta, and
  multi-agent concepts before any ontology package or SpecGraph spec mutation;
- support optional layer hints from fixture bindings and Ontology compiler diff
  reports when those producers can already identify the intended layer;
- make missing layer assignment visible as a review item rather than silently
  flattening the gap or diff.

Non-goals:

- no ontology package writes;
- no automatic layer inference for legacy specs;
- no lockfile updates;
- no canonical spec mutation;
- no owner-decision import;
- no SpecSpace UI changes;
- no prompt-agent invocation.
