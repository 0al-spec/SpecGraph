# 0221 Stable Identity and Lineage for Individual Requirements

RFC: SG-RFC-0221
Version: 0.1.0

## Status

Draft proposal. This document proposes an identity and lineage contract for
canonical Requirement nodes and distinct acceptance-criterion subjects. It does
not amend canonical specifications, implement an ID registry or consumer, or
approve a new ontology contract.

## Source Material

- [Discussion and inspection evidence](../archive/proposal_sources/0221_stable_requirement_identity_and_lineage.md)
- [SG-SPEC-0001](../../specs/nodes/SG-SPEC-0001.yaml): canonical node and
  specification boundaries
- [SG-SPEC-0019](../../specs/nodes/SG-SPEC-0019.yaml): canonical revision,
  supersession, and historical-presence semantics; its current 1:1 successor
  mapping is narrower than the relationship proposed here
- [Canonical Node format](../schema/node-format.md): current acceptance and
  `acceptance_evidence` representation

## Problem

SpecGraph gives specification and Requirement nodes stable IDs, but the
individual acceptance criteria inside many specs are plain strings. A
criterion's text or position cannot serve as a durable address: wording may be
clarified, criteria may move between nodes, and decomposition or consolidation
can change their number. A Requirement and an acceptance criterion are distinct
canonical subjects: a Requirement may reference one or more criteria through
`acceptance_criteria_refs`, and each criterion has its own identity. Existing
BDD scenario IDs identify scenarios, not every normative subject those
scenarios may exercise.

Without durable criterion identities and workspace-scoped references, split
tools and evidence consumers must rely on text or list positions. Historical
references can then become ambiguous after edits, moves, splits, or merges. A
content digest alone does not solve this problem because any content change
changes the digest, even when a subject remains the same after an editorial
revision.

## Proposed Contract

### Identity scope

1. Every requirement and every acceptance criterion MUST be a separately
   addressable canonical subject with its own immutable local ID, unique within
   its workspace. The full reference for either subject is the pair of the
   immutable, globally unique workspace identity and that subject's local ID.
   References MUST remain distinct across workspaces even when local IDs match.
   A local ID MUST be independent of containing node, file path, list position,
   title, and wording.
2. A canonical Requirement node uses the existing `requirement` node kind and
   its stable node `id`; this proposal extends that identity with revision and
   lineage semantics and does not introduce a second embedded Requirement
   representation. The Requirement-to-criterion relationship is expressed
   through `acceptance_criteria_refs`. Acceptance criteria retain separate
   subject identities; their concrete representation is a separate design
   decision and MUST preserve the existing distinction and reference relation.
3. The local ID format and allocator are workspace policy. A local ID MAY use
   a namespace and sequence or opaque token, for example `ZEU-REQ-0001`; this
   example is illustrative and reserves no identifier. The human-readable
   workspace slug or display name is separate from immutable workspace
   identity. Renaming that slug MUST NOT change full references; a slug alias
   MAY be used only when it resolves unambiguously to one immutable workspace
   identity. Allocation MUST detect collisions within the workspace and MUST
   NOT reuse a retired ID.
4. A subject record MUST keep stable identity separate from revision identity
   and content digest. A digest identifies exact content for a specific
   revision; it MUST NOT be used as the subject's identity. Current containment
   MUST be discoverable without making containment part of subject identity.

### Revision, movement, and retirement

1. Every governed content change MUST advance that subject's revision and
   identify the immediately preceding governed revision. The first revision is
   explicitly marked as the lineage origin and has no predecessor. This applies
   to editorial wording changes even when normative meaning is unchanged; such
   changes retain the subject ID. A replacement, split, or merge transition
   MUST link each new successor revision to the terminal revision of every
   predecessor it replaces; that transition is not a lineage origin. Producing
   a content digest is optional.
2. A one-to-one move between specification nodes retains the requirement ID
   when the normative meaning is unchanged. The move is recorded as a
   containment change with provenance; it does not create an identity alias.
3. A substantial normative change creates a new subject ID. The predecessor
   enters retired lifecycle disposition and `historical_lineage_only` presence;
   the successor has its own identity and is active in current topology. An
   explicit successor relationship preserves the change scope and provenance.
4. Splitting one subject retires its predecessor and records an explicit 1:N
   decomposition mapping. Merging subjects retires every predecessor and
   records an explicit N:1 composition mapping. In both cases predecessors
   become `historical_lineage_only`, while new successors are active. These
   mappings establish lineage, not equivalence: no successor may be
   substituted for a predecessor as though it had identical meaning.
5. Withdrawal or loss of applicability retires the subject without a successor
   and moves its presence to `historical_lineage_only`. The canonical node
   `status` continues to use the lifecycle vocabulary governed by SG-SPEC-0001;
   identity retirement is a separate lifecycle disposition, and presence is
   topology state. These concepts are separate, and retired IDs remain
   resolvable. Retirement never deletes or recycles an ID.
6. A same-identity editorial revision or one-to-one containment move advances
   revision, retains active identity disposition and active presence, and
   preserves the predecessor revision. Replacement, split, and merge retire
   predecessor identities and mark them `historical_lineage_only`; withdrawal
   does the same without successors. No transition may infer presence solely
   from lifecycle status.
7. A subject's historical record MUST preserve its identity, revisions,
   lifecycle disposition, topology presence, and all successor relationships.
   Lookup MUST return that record and its lineage; it MUST NOT silently
   redirect to an active successor or an unpinned `latest` revision.

### Evidence and read-only lookup

1. Every evidence artifact MUST either carry the immutable workspace identity
   with each local subject ID it references, or declare an immutable workspace
   binding that scopes every reference in that artifact. Acceptance evidence is
   keyed to the full acceptance-criterion reference, not to the Requirement ID;
   a criterion's owning Requirement is reached through `acceptance_criteria_refs`.
   Evidence bound to a particular wording MUST also pin that criterion revision;
   a content digest MAY additionally be recorded.
2. Every lookup request MUST either supply the immutable workspace identity
   alongside the local subject ID or explicitly target a workspace by its
   immutable identity. Local IDs or mutable workspace slugs alone are never
   sufficient. Lookup MUST resolve the subject to its identity record, requested
   or current revision, containment history, lifecycle disposition, topology
   presence, and explicit successor lineage. Unknown IDs or unavailable
   revisions are unresolved, not replaced by another record.
3. A split consumer MUST map requirement and criterion subjects by their full
   references, preserve the `acceptance_criteria_refs` relation, and classify
   each source as retained, moved, decomposed, merged, or retired. It MUST NOT
   infer identity continuity from text similarity or array order.

### Backward-compatible migration

1. Existing Requirement nodes retain their canonical `requirement` kind and
   node IDs. Existing string-valued `acceptance` criteria remain readable during
   migration as legacy, unassigned criterion subjects; readers MUST NOT
   conflate them with Requirement nodes or invent IDs during ordinary reads.
2. Migration assigns a distinct ID to each criterion through a reviewed,
   source-controlled change. It preserves criterion text and records the
   mapping from the prior containing node and criterion occurrence to the new
   full criterion reference. Reordering or formatting alone must not reassign
   migrated IDs.
3. Writers and readers transition in stages: consumers first accept both
   legacy strings and identified Requirement and criterion references;
   producers then emit IDs; legacy support is removed only through a separately
   reviewed compatibility decision. During the dual-read period, duplicate IDs,
   conflicting definitions, and ambiguous evidence mappings fail validation
   rather than falling back to text matching.
4. Existing BDD scenario IDs remain stable scenario identities. Migration does
   not convert them into requirement IDs or presume one-to-one correspondence.
   A scenario may explicitly reference one or more requirement IDs when that
   relation is authored and reviewable.
5. `acceptance_evidence` transitions from positional/text matching to entries
   keyed by full acceptance-criterion reference while preserving a compatibility
   reader for current criterion/evidence pairs. Evidence with no resolvable
   criterion reference remains legacy evidence and is not upgraded by guessing.

The relationship and criterion-keyed evidence can be represented conceptually
as:

```yaml
requirement_node:
  workspace_identity: immutable-workspace-id
  kind: requirement
  id: ZEU-REQ-0001
  acceptance_criteria_refs:
    - workspace_identity: immutable-workspace-id
      criterion_id: ZEU-AC-0001
evidence_artifact:
  workspace_identity: immutable-workspace-id
  acceptance_evidence:
    - criterion_id: ZEU-AC-0001
      criterion_revision: 2
      evidence: A policy test rejects writes to the accepted-facts store.
```

The Requirement's `id` and the evidence artifact's criterion ID are each bound
to the immutable workspace identity. Its `acceptance_criteria_refs` points to
a separately identified criterion, and evidence uses that same criterion
reference. The `requirement_node` and `evidence_artifact` roots are illustrative
separate records, not proposed canonical fields. This example does not prescribe
the criterion's representation or a serialized format.

This shape is illustrative. The proposal does not choose a canonical YAML
encoding or prescribe a database, registry service, URI scheme, or storage
backend.

## Scope Boundaries

In scope:

- Identity and lifecycle semantics for canonical Requirement nodes and
  distinct acceptance-criterion subjects
- Identity preservation across editorial revision and one-to-one moves
- Successor lineage for substantial change, split, merge, and retirement
- Historical resolution and digest-versus-identity boundaries
- Backward-compatible migration and expected consumer behavior for split
  mapping, criterion-keyed evidence, and workspace-scoped read-only lookup

Out of scope:

- Changing canonical SG-SPEC nodes or adopting this proposal
- A concrete canonical file schema, ID service, URI format, or database
- Implementing allocators, migration tools, lookup APIs, splitters, or evidence
  consumers
- Hypercode syntax, adapters, or integration
- Defining code-level conformance proofs or changing BDD scenario semantics

## Relationship to Existing Lineage

SG-SPEC-0019 governs canonical node and explicit-edge revision lineage and
currently requires one-to-one successor mapping in its bounded scope. This
proposal applies that canonical Requirement-node identity model and its
revision/predecessor discipline, while proposing requirement/criterion lineage
that can be 1:N or N:1. If adopted, those mappings require an explicit
refinement or extension of SG-SPEC-0019; they are not implied by its current
1:1 contract. Lifecycle retirement remains distinct from the
`historical_lineage_only` topology-presence state. The model preserves
append-only history, provenance, and inspectable predecessors.

## Open Questions

- What canonical representation should acceptance-criterion subjects use
  while preserving their distinct identity and the `acceptance_criteria_refs`
  relation to Requirement nodes?
- Should workspace uniqueness use a namespace plus monotonic allocator, opaque
  random identifiers with collision checks, or another governed scheme?
- What revision encoding and predecessor representation should canonical
  Requirement and criterion records use? A digest is optional and does not
  replace revision history.
- During migration, where should identified acceptance-criterion subjects be
  represented while legacy strings remain readable?

## Proposed Success Criteria

- Two workspaces can use the same local ID while workspace-scoped references
  remain distinct; evidence and lookup cannot collide across workspaces.
- A Requirement node and its acceptance criteria have distinct IDs, with
  criteria linked through `acceptance_criteria_refs` and evidence keyed by
  criterion reference.
- Every governed content change advances revision and records its predecessor;
  an optional digest identifies exact content.
- Editorial wording changes and one-to-one containment moves preserve identity
  when normative meaning is unchanged.
- A substantial change receives a new ID and a historical lookup returns the
  old record, status and revision, optional digest, and successor without
  silent redirection.
- Split and merge examples preserve all predecessor IDs and explicitly encode
  1:N and N:1 lineage without asserting equivalence.
- After a split, lookup by the predecessor's full reference returns its
  historical record and every successor; it never silently selects one child.
- Legacy string criteria and current BDD scenario IDs remain readable during a
  staged migration; no read path fabricates IDs.
- Split mapping and evidence address subjects by full workspace-scoped ID, and
  read-only lookup resolves historical records reproducibly.

## Proposal Validation

- A proposal tracking gate passes with the source draft and tracking entries
  present.
- Markdown structure and relative source links validate.
- `git diff --check` reports no whitespace errors.
- Validation does not mutate canonical specifications or execute runtime
  behavior.

## Implementation Follow-up

After canonical review and adoption, a separate bounded implementation plan
should update the requirement representation, migration tooling, split
consumer, evidence validator, and read-only lookup. It should first preserve
the existing string criterion and BDD scenario behavior, then introduce
ID-keyed evidence and historical resolution with explicit fixtures for moves,
revision, split, merge, retirement, and unknown IDs. This proposal-authoring
change implements none of those behaviors.
