# Source Draft: Layered Ontology Import Surface

Origin: follow-up to Ontology `ONT-039` layered ontology model and the
Ontology-SpecGraph-SpecSpace roadmap.

Intent:

- make SpecGraph consume first-class ontology `layer` metadata from normalized IR
  when the Ontology compiler emits it;
- preserve layer metadata on resolved ontology refs so downstream SpecAuthor,
  supervisor, and SpecSpace surfaces can reason about objective/mechanics/
  execution/meta/multi-agent distinctions;
- publish a package-level layer summary in `runs/ontology_package_index.json`;
- keep the slice read-only: no ontology package writes, no lockfile updates, no
  canonical spec mutation, no accepted-term authority change.

Non-goals:

- no new ontology package authoring in SpecGraph;
- no automatic layer inference for legacy specs;
- no SpecSpace UI changes;
- no SpecAuthorAgent prompt/runtime behavior change;
- no owner-decision import or ontology governance mutation.
