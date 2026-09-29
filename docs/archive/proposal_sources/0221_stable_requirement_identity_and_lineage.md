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

The desired capability is to keep precise references to canonical Requirement
nodes and distinct acceptance-criterion subjects when containing specifications
change. A Requirement node and each criterion need separate stable IDs, linked
through `acceptance_criteria_refs`; evidence is keyed to the criterion. A
subject may move between nodes without changing identity when its meaning is
preserved. A substantial normative change should create a successor identity.
Decomposition and combination should retire predecessor identities while
recording explicit one-to-many or many-to-one lineage; those relationships must
not imply semantic equivalence. Requirement identity extends the existing
canonical `requirement` node kind; the criterion representation remains a
separate design decision.

Every evidence reference and lookup uses the immutable workspace identity with
the local subject ID, or explicitly binds the artifact/request to that
immutable workspace. Retired subjects continue resolving to their historical
record and successor relationships. Lifecycle retirement is separate from
`historical_lineage_only` topology presence: replacement, split, merge, and
withdrawal retire their predecessors, mark them historical in topology, and
keep them resolvable; only the first three have successor mappings. Every
governed content change advances revision and records its predecessor, while a
content digest remains optional and separate from identity.

For backward-compatible adoption, existing acceptance strings and existing
BDD scenario IDs should remain usable during migration. Split tooling should map
Requirement and criterion subjects by their separate full references, preserve
`acceptance_criteria_refs`, and key acceptance evidence by criterion reference
instead of list position, Requirement ID, or text equality.

No Hypercode syntax or integration is requested in this proposal.
