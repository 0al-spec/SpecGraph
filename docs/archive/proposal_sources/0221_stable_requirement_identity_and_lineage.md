# Source: stable identity and lineage for individual requirements

Captured on 2026-09-29 from a project-planning discussion about preparing
SpecGraph requirements for downstream implementation and verification. The
operator judged Hypercode premature for current work, while identifying stable
addresses for individual requirements as an immediate concern.

## Problem observed

- Canonical SpecGraph nodes have stable node IDs, but acceptance criteria in
  `specs/nodes/SG-SPEC-0019.yaml` and the seed specification are plain strings.
- `docs/schema/node-format.md` currently describes `acceptance_evidence` as a
  one-to-one mapping to criteria, represented with criterion text.
- Some product specifications already use stable BDD scenario IDs. These
  scenario IDs do not give every acceptance criterion its own identity.
- `SG-SPEC-0019` defines revision and supersession lineage for canonical nodes
  and explicit edges. Its successor mapping is one-to-one and explicitly
  leaves one-to-many and many-to-one mappings for future refinement.

## Discussion outcome

The desired capability is to keep a precise reference to a normative
requirement when its containing specification changes. A requirement may move
between nodes without changing identity when its meaning is preserved. A
substantial normative change should create a successor identity. Decomposition
and combination should retire predecessor identities while recording explicit
one-to-many or many-to-one lineage; those relationships must not imply semantic
equivalence.

References to retired requirements should continue resolving to their
historical record, status, and successor relationships. Revision or content
digests identify a specific version of a requirement's content and remain
separate from its stable identity. Consumers should be able to look up this
information read-only.

For backward-compatible adoption, existing acceptance strings and existing
BDD scenario IDs should remain usable during migration. Split tooling should map
criteria by stable requirement ID, and acceptance evidence should eventually
key by that ID instead of list position or text equality.

No Hypercode syntax or integration is requested in this proposal.
