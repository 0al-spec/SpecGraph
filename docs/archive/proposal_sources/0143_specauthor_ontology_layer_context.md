# Source Draft: SpecAuthor Ontology Layer Context

Origin: follow-up to `0141 Layered Ontology Import Surface` and
`0142 Layer-Aware Ontology Gap and Diff Review`.

Intent:

- make SpecAuthor-generated artifacts resolve the active ontology layer context
  before write-gate review;
- require strong generated claims to declare the ontology layer they apply to;
- prevent claims from using a layer outside the active frame;
- keep the change as a typed artifact/write-gate contract extension, not a
  prompt-agent runtime implementation;
- preserve the read-only authority boundary: no ontology package writes, no
  lockfile updates, and no canonical spec mutation.

Non-goals:

- no prompt execution;
- no Agent Passport extension;
- no automatic layer inference;
- no owner-decision import;
- no ontology package mutation;
- no SpecSpace UI changes.
