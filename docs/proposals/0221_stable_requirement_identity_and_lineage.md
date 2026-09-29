# 0221 Stable Identity and Lineage for Individual Requirements

RFC: SG-RFC-0221
Version: 0.1.0

## Status

Draft proposal. This document proposes an identity and lineage contract for
individual normative requirements and acceptance criteria. It does not amend
canonical specifications, implement an ID registry or consumer, or approve a
new ontology contract.

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

SpecGraph gives specification nodes stable IDs, but the individual acceptance
criteria inside many nodes are plain strings. A criterion's text or position
cannot serve as a durable address: wording may be clarified, criteria may move
between nodes, and decomposition or consolidation can change the number of
criteria. Existing BDD scenario IDs identify scenarios, not every normative
requirement those scenarios may exercise.

Without a separate requirement identity, split tools and evidence consumers
must rely on text or list positions. Historical references can then become
ambiguous after edits, moves, splits, or merges. A content digest alone does
not solve this problem because any content change changes the digest, even when
the requirement remains the same requirement after an editorial revision.

## Proposed Contract

### Identity scope

1. Each atomic normative requirement MUST have an immutable local requirement
   ID that is unique within its owning workspace. Its full identity/reference
   is the pair of the immutable, globally unique workspace identity and the
   local requirement ID. The full reference MUST remain distinct across
   workspaces, even when two workspaces use the same local sequence. The local
   requirement ID MUST be independent of the containing specification node,
   file path, list position, title, and requirement wording.
2. The local ID format and allocator are workspace policy. A local ID MAY use
   a namespace and sequence or opaque token, for example `ZEU-REQ-0001`; this
   example is illustrative and reserves no identifier. The human-readable
   workspace slug or display name is separate from immutable workspace
   identity. Renaming that slug MUST NOT change full requirement references;
   a slug alias MAY be used only when it resolves unambiguously to one
   immutable workspace identity. Allocation MUST detect local ID collisions
   within the workspace and MUST NOT reuse a retired ID.
3. A requirement record MUST keep its stable ID separate from a revision
   identifier or content digest. A digest identifies exact content for a
   specific revision; it MUST NOT be used as the requirement's identity.
4. The record or its canonical relationships MUST make current containment
   discoverable without making containment part of the requirement ID.

### Revision, movement, and retirement

1. Editorial changes that preserve normative meaning retain the requirement
   ID. Such changes MAY produce a new requirement revision and digest.
2. A one-to-one move between specification nodes retains the requirement ID
   when the normative meaning is unchanged. The move is recorded as a
   containment change with provenance; it does not create an identity alias.
3. A substantial normative change creates a new requirement ID. The previous
   ID becomes historical and links to the successor through an explicit
   successor relationship. Reviewers must be able to inspect the change scope
   and provenance that justify the successor.
4. Splitting one requirement into multiple requirements retires the
   predecessor and records an explicit one-to-many decomposition mapping to
   the successor IDs. Merging multiple requirements retires all predecessors
   and records an explicit many-to-one composition mapping to the successor.
   These mappings establish lineage, not equivalence: no successor may be
   substituted for a predecessor as though it had identical meaning.
5. Retirement without a successor is permitted when a requirement is withdrawn
   or no longer applicable. The record retains its reason, authority, and
   provenance. Retirement never deletes or recycles the ID.
6. A requirement's historical record MUST preserve its own identity, content
   revision/digest references, status, and all successor relationships. A
   historical lookup MUST return that record and its status and successors;
   it MUST NOT silently redirect to an active successor or an unpinned
   `latest` version.

### Evidence and read-only lookup

1. Acceptance evidence MUST identify the requirement ID it supports. Evidence
   bound to a particular wording or revision SHOULD also identify that exact
   requirement revision or content digest so evidence is not silently treated
   as current after a normative change.
2. A read-only lookup MUST resolve an active or retired requirement ID to its
   identity record, requested or current revision state, containment history,
   retirement status, and explicit successor lineage. An unavailable historical
   revision or unknown ID is reported as unresolved, not replaced by another
   record.
3. A split consumer MUST map criteria by requirement ID, then explicitly
   classify each source ID as retained, moved, decomposed, merged, or retired.
   It MUST NOT infer identity continuity from text similarity or array order.

### Backward-compatible migration

1. Existing string-valued `acceptance` criteria remain readable during
   migration. Consumers MUST distinguish identified criteria from legacy
   unassigned strings and MUST NOT invent stable IDs during ordinary reads.
2. Migration assigns an ID to each existing criterion through a reviewed,
   source-controlled change. It preserves the criterion text and records the
   mapping from the prior containing node and criterion occurrence to the new
   ID. Reordering or formatting alone must not reassign migrated IDs.
3. Writers and readers transition in stages: consumers first accept both
   legacy criteria and identified requirement records; producers then emit
   IDs; legacy support is removed only through a separately reviewed
   compatibility decision. During the dual-read period, duplicate IDs,
   conflicting definitions, and ambiguous evidence mappings fail validation
   rather than falling back to text matching.
4. Existing BDD scenario IDs remain stable scenario identities. Migration does
   not convert them into requirement IDs or presume one-to-one correspondence.
   A scenario may explicitly reference one or more requirement IDs when that
   relation is authored and reviewable.
5. `acceptance_evidence` transitions from positional/text matching to entries
   keyed by requirement ID while preserving a compatibility reader for current
   criterion/evidence pairs. Evidence with no resolvable requirement ID remains
   legacy evidence and is not upgraded by guessing.

An illustrative full reference could be represented conceptually as
`(workspace_identity: "immutable-workspace-id", requirement_id: "ZEU-REQ-0001")`.
This is notation only, not a proposed URI or serialized format. An identified
criterion and evidence pair could look like:

```yaml
acceptance:
  - id: ZEU-REQ-0001
    statement: The component cannot write accepted case facts.
acceptance_evidence:
  ZEU-REQ-0001:
    requirement_revision: 1
    evidence: A policy test rejects writes to the accepted-facts store.
```

This shape is illustrative. The proposal does not choose a canonical YAML
encoding or prescribe a database, registry service, URI scheme, or storage
backend.

## Scope Boundaries

In scope:

- Identity and lifecycle semantics for individual normative requirements and
  acceptance criteria
- Identity preservation across editorial revision and one-to-one moves
- Successor lineage for substantial change, split, merge, and retirement
- Historical resolution and digest-versus-identity boundaries
- Backward-compatible migration and expected consumer behavior for split
  mapping, evidence keys, and read-only lookup

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
proposal requires requirement-level one-to-many and many-to-one lineage. If
adopted, that relationship must be established as an explicit refinement or
extension of SG-SPEC-0019's boundary; it must not be represented as though the
current 1:1 contract already provides it. The requirement-level model must
preserve SG-SPEC-0019's append-only historical visibility, provenance, and
active-versus-historical distinction.

## Open Questions

- Should requirement records become first-class graph entities with explicit
  containment edges, or remain typed atoms embedded in specification nodes
  with independently addressable identities?
- Should workspace uniqueness use a namespace plus monotonic allocator, opaque
  random identifiers with collision checks, or another governed scheme?
- Which statuses are needed beyond active, retired, and historical, and how
  should applicability withdrawal differ from semantic replacement?
- What minimal digest algorithm, canonicalization rule, and revision record
  are needed for pinned historical lookup?
- During migration, should identified criteria coexist inside `acceptance`
  objects or live in a separate `requirements` collection with a derived
  acceptance projection?

## Proposed Success Criteria

- Two workspaces can use the same local sequence while their full references
  remain distinct and their local IDs remain unique within each workspace.
- Editorial wording changes and one-to-one containment moves preserve identity
  when normative meaning is unchanged.
- A substantial change receives a new ID and a historical lookup returns the
  old record, status, digest/revision, and successor without silent redirection.
- Split and merge examples preserve all predecessor IDs and explicitly encode
  1:N and N:1 lineage without asserting equivalence.
- After a split, lookup by the predecessor's full reference returns its
  historical record and every successor; it never silently selects one child.
- Legacy string criteria and current BDD scenario IDs remain readable during a
  staged migration; no read path fabricates IDs.
- Split mapping and acceptance evidence address requirements by ID, and
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
