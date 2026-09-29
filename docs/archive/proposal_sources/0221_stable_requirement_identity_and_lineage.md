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
  remains one-to-one; Requirement decomposition and composition are separate
  subject relations and do not alter that canonical-node contract.

## Discussion outcome

The desired capability is to keep precise references to canonical Requirement
nodes and distinct acceptance-criterion subjects when containing specifications
change. A Requirement node and each criterion need separate stable IDs, linked
through `acceptance_criteria_refs`; evidence is keyed to the criterion. A
subject may move between nodes without changing identity when its meaning is
preserved. A substantial normative change should create a successor identity
under an explicit subject-disposition transition. Requirement and
acceptance-criterion decomposition/composition use separately authored,
directed subject relations: `decomposes_into` points from one source subject to
each resulting subject, while `composed_from` points from one resulting
subject to each contributor. Each relation's endpoints must be the same subject
class (Requirement-to-Requirement or criterion-to-criterion); cross-kind
endpoints require another separately specified relation such as
`acceptance_criteria_refs`. The two types are distinct events, not inferred
inverse records, and do not alter participants' disposition or revision chains.
Relation participants must not become revision predecessors of one another.
These relations must not imply semantic equivalence or silently change
canonical node/edge identity, lifecycle, or active-topology presence. Any
canonical node supersession remains a separate 1:1 event under frozen
SG-SPEC-0019.

Each subject ID begins at revision 1, the origin of its own revision sequence
with no same-identity predecessor. Later revisions point only to the
immediately preceding revision in that identity's 1:1 chain. A canonical node
replacement separately connects exactly one predecessor node to one successor
under SG-SPEC-0019; its cross-identity `predecessor_reference` to the prior
node's terminal revision is a supersession link, not an additional predecessor
in the successor's revision chain or a reason to erase its revision-1 origin.
Retirement or activation of a subject requires an explicit disposition
transition; decomposition and composition relations do not infer it.
Requirement identity extends the existing canonical `requirement` node kind;
the criterion representation remains a separate design decision.

Every evidence reference and lookup uses the immutable workspace identity with
the local subject ID, or explicitly binds the artifact/request to that
immutable workspace. Retired subjects continue resolving to their historical
record and all subject relations. Subject disposition is separate from
canonical node/edge lifecycle and `historical_lineage_only` topology presence;
decomposition and composition relations do not by themselves change subject
disposition, revision history, or canonical active topology. Explicit
withdrawal retires a Requirement subject, excludes it from Requirement-level
readiness and dependency satisfaction, and leaves its canonical node queryable
for historical lineage with graph topology unchanged. Graph-level traversal
continues to follow SG-SPEC-0019 node/edge presence. Any canonical node
supersession remains a separate 1:1 event under SG-SPEC-0019. Every governed
content change advances that identity's revision and records its single
immediate predecessor, while a content digest remains optional and separate
from identity.

For backward-compatible adoption, existing acceptance strings and existing
BDD scenario IDs should remain usable during migration. Split tooling should map
Requirement and criterion subjects by their separate full references, preserve
`acceptance_criteria_refs`, represent same-kind Requirement and criterion
decomposition/composition with their distinct typed relations and endpoint
roles, and key acceptance evidence by criterion reference instead of list
position, Requirement ID, or text equality. Lookup returns exact records and
all typed relation endpoints without redirecting to a related subject or
selecting one successor; reverse queries enumerate authored relations and do
not infer the other relation type by reversing an edge. Requirement-level
readiness/dependency evaluation excludes explicitly retired Requirements even
when graph-level traversal still includes their unchanged canonical nodes.

No Hypercode syntax or integration is requested in this proposal.
