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
  supersession, and historical-presence semantics; its frozen 1:1 canonical
  node and explicit-edge successor mapping remains unchanged by this proposal
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

1. Every subject ID begins at revision 1, which is the origin of that identity's
   revision sequence and has no same-identity revision predecessor. Each later
   governed content revision MUST identify exactly one immediately preceding
   revision in that same identity's chain. If a canonical node at revision 1
   succeeds another node, its SG-SPEC-0019 supersession event separately
   preserves exactly one cross-identity `predecessor_reference` to the prior
   node's terminal revision. That canonical supersession link does not erase
   the new identity's revision-1 origin or become an additional predecessor in
   its per-identity revision chain. This separation preserves both facts
   without changing frozen SG-SPEC-0019. Editorial wording changes retain the
   subject ID. Decomposition and composition relations MUST NOT add revision
   predecessors or join revision chains of distinct subject IDs. Producing a
   content digest is optional.
2. A one-to-one move between specification nodes retains the requirement ID
   when the normative meaning is unchanged. The move is recorded as a
   containment change with provenance; it does not create an identity alias.
3. A substantial normative change creates a new subject ID. An explicit
   disposition transition retires the predecessor subject and activates the
   successor subject, preserving change scope and provenance. These subject
   dispositions do not by themselves set canonical node/edge presence. If the
   subjects are canonical nodes, any topology replacement is a separate
   SG-SPEC-0019 supersession event with exactly one predecessor and one
   successor; only that event places the superseded node in
   `historical_lineage_only` and the successor in active topology.
4. Requirement and acceptance-criterion decomposition and composition are
   represented by separate, explicitly authored, typed subject relations,
   distinct from canonical `supersedes` relations. `decomposes_into` is
   directed from one source subject to each of two or more resulting subjects;
   `composed_from` is directed from one resulting subject to each of two or
   more contributing subjects. For either relation type, every endpoint MUST
   have the same subject class: Requirement-to-Requirement or
   criterion-to-criterion. A cross-kind Requirement/criterion endpoint is
   invalid for these relation types; the existing `acceptance_criteria_refs`
   relation remains the separately specified owner/reference relation, and any
   other cross-kind relation requires its own specification. The two relation
   kinds describe distinct events; neither is inferred by reversing or
   mirroring the other. These relations establish subject lineage, not
   equivalence: no related subject may be substituted for another as though it
   had identical meaning. They do not constitute 1:N or N:1 canonical-node
   successor mappings, do not create or rewrite canonical `supersedes` edges,
   and do not change any participant's subject disposition, revision chain,
   canonical node or edge identity, lifecycle, active-topology presence, or
   dependency role. Retirement or activation requires a separate explicit
   subject disposition transition; canonical node or edge presence changes
   only under SG-SPEC-0019's independent 1:1 rules.
5. Withdrawal or loss of applicability retires the subject without a successor.
   A retired Requirement subject is excluded from Requirement-level readiness
   evaluation and MUST NOT satisfy another Requirement's dependency. This
   subject disposition does not change canonical node lifecycle or topology,
   and does not set canonical presence to `historical_lineage_only`:
   the canonical Requirement node remains queryable for historical lineage and
   graph-level traversal follows its unchanged presence under SG-SPEC-0019.
   Only a separate SG-SPEC-0019-compliant 1:1 node transition can change that
   topology presence. Canonical node `status` continues to use the lifecycle
   vocabulary governed by SG-SPEC-0001. Retired IDs remain resolvable;
   retirement never deletes or recycles an ID.
6. A same-identity editorial revision or one-to-one containment move advances
   the subject revision and preserves its subject identity and single
   immediately preceding revision. A decomposition or composition relation
   preserves its participants and relation history but does not itself update
   their subject-level disposition or revisions. Any subject retirement or
   activation is a separate explicit disposition transition. Canonical
   node/edge presence is independent and may change only through a separately
   governed canonical transition. No transition may infer presence solely from
   lifecycle status or a subject relation.
7. A subject's historical record MUST preserve its identity, revisions,
   lifecycle disposition, workspace scope, and every incoming and outgoing
   subject relation. Lookup MUST return that record and its lineage; it MUST
   NOT silently redirect to a related subject, an active canonical successor,
   or an unpinned `latest` revision.

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
   or current revision, containment history, lifecycle disposition, canonical
   node/edge presence when applicable, and explicitly typed subject relations.
   Relation traversal MUST return all endpoints and their subject classes for
   the requested relation kind; reverse queries MUST enumerate all matching
   authored relations and preserve endpoint roles, without inferring the other
   relation kind by reversing an edge. Cross-kind endpoints are invalid for
   decomposition/composition. Graph-level traversal uses canonical node/edge
   presence under SG-SPEC-0019; Requirement-level readiness and dependency
   evaluation excludes retired Requirement subjects, and a retired subject
   cannot satisfy a dependency even when its canonical node remains traversable.
   Results MUST label subject relations separately from canonical supersession,
   MUST NOT select a single related subject as a replacement, and MUST NOT
   infer disposition changes. Unknown IDs or unavailable revisions are
   unresolved, not replaced by another record.
3. A split consumer MUST map Requirement and criterion subjects by their full
   references, preserve the `acceptance_criteria_refs` relation, and classify
   each source as retained, moved, decomposed, composed, or retired. It MUST
   represent decomposition and composition with their respective explicit
   subject relations; it MUST NOT encode them as multi-successor or
   multi-predecessor `supersedes` mappings. It MUST NOT infer identity
   continuity from text similarity or array order.

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
- Explicit successor lineage for substantial change and distinct same-kind
  subject relations for Requirement and acceptance-criterion
  decomposition/composition and retirement
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
requires exactly one successor for each canonical supersession event in its
frozen scope. This proposal preserves that 1:1 rule without exception or
reinterpretation. Requirement `decomposes_into` and `composed_from` relations
are a separate subject-lineage relation class: they do not assert canonical
node replacement, do not create `supersedes` edges, and do not change active
canonical node/edge topology. If a canonical node is separately superseded,
that event still has exactly one successor and follows SG-SPEC-0019. Subject
disposition and relation history are distinct from canonical node lifecycle
and `historical_lineage_only` presence. Decomposition and composition relations
neither change participant disposition nor link revision chains; either effect
requires its own explicit transition within the applicable contract. The model
preserves append-only history, provenance, source identities, every related
subject, and explicit workspace scope.

For queries, callers address a subject by immutable workspace identity plus
local ID and optionally pin a revision. A direct lookup returns that exact
subject record and its revision/containment history. Relation traversal returns
all endpoints with their directed roles for the requested relation kind:
`decomposes_into` from source to results and `composed_from` from result to
contributors. Reverse queries enumerate every matching authored relation and
preserve endpoint roles; they do not infer one relation kind by reversing the
other. Neither direct nor relation lookup redirects to a related identity, and
relation results never stand in for canonical `supersedes` traversal.

### Observable Examples

```gherkin
Scenario: A canonical successor begins its own revision sequence
  Given a canonical Requirement node with terminal revision 4
  When one successor Requirement node replaces it under SG-SPEC-0019
  Then the successor identity begins at revision 1 as its own sequence origin
  And the supersession event separately points to the predecessor's revision 4
  And the cross-identity link is not an additional predecessor in the successor's revision chain

Scenario: Acceptance-criterion decomposition preserves endpoint types
  Given one acceptance-criterion subject with a workspace-scoped ID
  When it has decomposes_into relations to two criterion subjects
  Then both targets are returned as acceptance-criterion subjects
  And no Requirement subject is an endpoint of that relation
  And the relation does not change participant disposition or revision chains

Scenario: Acceptance-criterion composition returns every typed contributor
  Given one resulting acceptance-criterion subject and two contributing criterion subjects
  When the result has composed_from relations to each contributor
  Then lookup returns both criterion contributors with their endpoint roles
  And the relation has no Requirement subject endpoint
  And it does not change participant disposition or revision chains

Scenario: A retired Requirement is excluded from Requirement-level evaluation
  Given a canonical Requirement node whose subject disposition is explicitly retired
  When graph-level traversal and Requirement-level dependency evaluation run
  Then graph traversal follows the node's unchanged canonical presence
  And the retired Requirement is not readiness-evaluated
  And the retired Requirement cannot satisfy another Requirement's dependency
  And historical lineage lookup still resolves the canonical node
```

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
- Every governed content change advances that identity's revision and records
  its single immediate predecessor; decomposition/composition relations never
  add revision predecessors. An optional digest identifies exact content.
- A successor identity begins revision 1 as its own sequence origin; a canonical
  1:1 SG-SPEC-0019 supersession link separately identifies its predecessor's
  terminal revision.
- Editorial wording changes and one-to-one containment moves preserve identity
  when normative meaning is unchanged.
- A substantial change receives a new ID and a historical lookup returns the
  old record, status and revision, optional digest, and successor without
  silent redirection.
- Decomposition and composition examples preserve every participant ID and
  endpoint role. `decomposes_into` points from source to each result;
  `composed_from` points from result to each contributor. The separately
  authored relations apply to Requirement-to-Requirement or
  criterion-to-criterion subjects only, do not imply equivalence, change
  disposition/revision chains, or alter canonical active topology. Cross-kind
  endpoints fail validation unless another relation type is separately specified.
- Withdrawing a Requirement explicitly retires its Requirement subject and
  excludes it from Requirement-level readiness and dependency satisfaction;
  graph-level traversal and canonical historical lookup continue to follow the
  unchanged node/edge presence under SG-SPEC-0019.
- After decomposition or composition, lookup by any participant's full
  reference returns that subject and its complete relation history; traversal
  returns every related subject and never selects one or performs silent
  substitution.
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
