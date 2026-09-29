# RFC 0221 Canonical Adoption Review Packet

## Status

**Draft discussion aid; non-authoritative and not an adoption decision.** This
packet records recommended resolutions and a possible follow-up sequence for
review of [RFC 0221](../proposals/0221_stable_requirement_identity_and_lineage.md). It does
not amend a canonical specification, settle ontology authority, authorize
implementation, or establish that any requirement below has been accepted.
The existing RFC and its source draft remain the proposal record.

## Decision Requested

Review the four open design questions in RFC 0221, decide whether to adopt its
bounded identity and lineage contract, and authorize a separate canonical
refinement task only after that review. A decision to defer or reject remains a
valid outcome. The recommendations below are a concrete starting point for
that review, not defaults that become binding without approval.

## Recommended Resolutions for RFC 0221's Open Questions

### 1. Acceptance-criterion representation

**Recommendation:** represent each criterion as an independently addressable
record with a stable `criterion_id` and statement, referenced from its owning
Requirement through `acceptance_criteria_refs`. Keep the criterion distinct
from both the Requirement node and any BDD scenario. In the first schema
iteration, use a typed record collection associated with its owning canonical
specification; do not add a new seed node kind or prescribe a database in this
packet. The canonical refinement must decide whether these records are
embedded or separately stored, and specify their history and move semantics
before adoption.

The identity must not derive from the statement, owner, path, order, or scenario
ID. A move changes containment and provenance only. This choice preserves the
relationship proposed by RFC 0221 while leaving physical serialization open
until schema review. See [RFC 0221, Identity scope](../proposals/0221_stable_requirement_identity_and_lineage.md#identity-scope)
and [node format](../schema/node-format.md).

### 2. Workspace identity and local ID allocation

**Recommendation:** scope references by a persisted, immutable workspace
identity plus an opaque local subject ID. Give the workspace identity an
explicit source-controlled declaration with a uniqueness check; keep its
human-readable name as a mutable display value. Allocate local IDs through a
workspace-scoped monotonic sequence or equivalent collision-checked allocator,
and never recycle retired IDs. The exact token syntax is policy, not semantics.

This favors auditable allocation and durable references over deriving identity
from a repository URL or slug, either of which may change. The canonical
refinement should define the identity declaration's owner and collision gate;
this packet does not select a serialization format or reserve example IDs.

### 3. Revision and predecessor representation

**Recommendation:** use a per-subject positive integer revision, starting at
`1`, with every governed content change creating the next revision and an
explicit reference to the immediately preceding revision in that same
identity's 1:1 revision chain. Each subject ID begins at revision 1 as the
origin of that identity's sequence, with no same-identity predecessor. Keep the
stable subject ID separate from both revision and optional content digest. Use
explicit typed transition records for moves, replacements, Requirement and
criterion decomposition/composition, and withdrawals, including provenance and
subject-level effects. Relation participants do not become one another's
revision predecessors. Mark decomposition and composition as distinct directed
subject relations; neither relation is inferred by reversing or mirroring the
other. Only a separate SG-SPEC-0019-compliant canonical node/edge transition
determines canonical topology presence. Its cross-identity
`predecessor_reference` to one predecessor node's terminal revision is a
supersession link, separate from the successor identity's revision-1 origin
and per-identity revision chain. Do not infer lineage or presence from a digest
or storage history.

Integer sequencing is inspectable and does not imply semantic versioning. The
refinement must define atomicity and uniqueness for revision creation and
whether a transition record is attached to predecessor, successor, or a
separate event. A digest may pin exact bytes, but is not required to identify a
subject or establish semantic continuity.

### 4. Location and migration of identified criteria

**Recommendation:** keep existing string-valued `acceptance` and
`acceptance_evidence` readable as legacy data while introducing a versioned,
identified criterion-record form. A reviewed, source-controlled migration
should map each old criterion occurrence to exactly one stable criterion ID;
ordinary reads must not mint IDs or match by text. During dual-read, duplicate
IDs, conflicting records, or ambiguous evidence mappings must fail closed with
an actionable diagnostic. Producers should emit identified records only after
all supported consumers can read them. Removing legacy support requires its
own compatibility decision.

Keep existing BDD scenario IDs as scenario identities. A scenario may cite one
or more Requirement or criterion references only through an authored,
reviewable relation. Evidence for a criterion must be keyed by its full
workspace-scoped reference and pin a revision when it asserts wording-specific
behavior. See [RFC 0221, Backward-compatible migration](../proposals/0221_stable_requirement_identity_and_lineage.md#backward-compatible-migration).

## Compatibility with SG-SPEC-0019

[SG-SPEC-0019](../../specs/nodes/SG-SPEC-0019.yaml) is frozen and defines
one-to-one successor mapping for canonical node and explicit-edge supersession
within its scope. Its frozen boundary says further canonical change must
preserve both subject identities. The confirmed direction preserves this rule
without exception or reinterpretation. Requirement decomposition and
composition are separate explicit subject relations, named `decomposes_into`
and `composed_from` in the RFC draft. Both Requirement and acceptance-criterion
subjects may participate. `decomposes_into` points from one source subject to
each resulting subject; `composed_from` points from one resulting subject to
each contributor. Endpoints within either relation must share one subject type:
Requirement-to-Requirement or criterion-to-criterion. Cross-kind endpoints are
invalid for these relation types; `acceptance_criteria_refs` remains a distinct,
explicitly specified Requirement-to-criterion relation. Any other cross-kind
relation requires separate specification. These are distinct authored relation
types, not inverse storage assumptions. They do not encode 1:N or N:1
`supersedes` mappings, do not create canonical `supersedes` edges, and do not
silently change canonical node or edge identity, lifecycle, dependency role, or
active-topology presence. They also do not change participant dispositions or
revision chains; subject retirement/activation requires an independent explicit
disposition transition. Any canonical node/edge supersession remains its own
SG-SPEC-0019-compliant 1:1 event.

The follow-up must therefore:

1. Leave the frozen `SG-SPEC-0019` file unchanged. Do not reinterpret its
   `successor_mapping` as one-to-many or many-to-one.
2. Propose one new, narrowly scoped canonical child refinement of
   `SG-SPEC-0019` for stable Requirement and criterion subjects. Allocate its
   eventual node ID only through the repository's collision-checked workflow.
3. Define Requirement decomposition and composition as distinct directed
   subject-level relation kinds, separate from 0019's one-to-one node/edge
   `supersession_event`. Preserve every source and target identity and endpoint
   role; do not infer another relation by reversing one, or infer participant
   disposition, canonical node retirement, presence, or successor status.
4. Preserve the existing invariants: append-only history, explicit provenance,
   retired subjects remain resolvable, and subject disposition stays distinct
   from canonical lifecycle and topology presence. Historical canonical
   subjects are excluded from active topology only through a separate
   canonical transition.
5. Specify how the child refines the frozen parent without contradicting it;
   if that cannot be done under current refinement authority, stop for an
   explicit governance decision rather than editing the parent in place.

## Shape of the Canonical Child Refinement

If the proposal is adopted, the child refinement should state only the
semantics needed to make identity reviewable and usable:

- Subject classes and references: Requirement identity, criterion identity,
  immutable workspace scope, and the `acceptance_criteria_refs` relation.
- Revision contract: stable identity versus revision versus optional digest;
  origin marker; immediate predecessor; provenance for each governed change.
- Transition contract: identity-preserving editorial change and move;
  replacement; same-kind Requirement and criterion `decomposes_into` and
  `composed_from` subject relations; and withdrawal. State the independent
  subject-disposition and canonical lifecycle/presence effects for each;
  decomposition and composition do not alter participant disposition, revision
  chains, or canonical active topology. Withdrawing a Requirement explicitly
  retires its subject and excludes it from Requirement-level readiness and
  dependency satisfaction, while its canonical node remains queryable and
  graph-level topology follows the unchanged SG-SPEC-0019 presence.
- Lookup contract: resolve an exact subject/revision and its complete relation
  history; direct lookup preserves the requested identity, and relation
  traversal returns every endpoint with its directed role for the requested
  relation kind. Reverse queries enumerate all matching authored relation
  records without inferring the other relation kind by edge reversal. Unknown
  IDs and unavailable revisions remain unresolved, without fallback to a
  related subject, canonical successor, text match, or unpinned latest value.
- Migration boundary: legacy strings remain readable; IDs enter through
  reviewed migration; no ordinary read fabricates identities; BDD scenarios
  remain a separate identity class.
- Explicit exclusions: storage backend, service/API, URI format, Hypercode,
  automated ID issuance, and runtime conformance claims unless separately
  adopted.

The child should define semantic invariants and observable examples, not
prematurely prescribe an implementation. A useful BDD-style example is:

```gherkin
Scenario: Requirement decomposition preserves every subject and endpoint
  Given a workspace-scoped requirement reference with a terminal revision
  When a source requirement has decomposes_into relations to two reviewed results
  Then lookup preserves the source identity and returns both directed targets
  And neither target is treated as semantically equivalent to the source
  And neither relation changes participant disposition or revision chains
  And canonical node and edge active topology is unchanged by the relation

Scenario: Successor revision 1 has a separate canonical supersession link
  Given a canonical Requirement node with terminal revision 4
  When one successor replaces it through SG-SPEC-0019
  Then the successor's revision 1 is the origin of its own identity sequence
  And the supersession event separately references the predecessor's revision 4
  And that link does not add a predecessor to the successor's revision chain

Scenario: Criterion composition cannot link Requirement endpoints
  Given two acceptance-criterion subjects and one Requirement subject
  When a composed_from relation connects the Requirement to the criteria
  Then validation rejects the cross-kind relation endpoints
  And acceptance_criteria_refs remains a distinct relation

Scenario: Retired Requirement stays queryable but cannot satisfy dependencies
  Given a canonical Requirement node with an explicitly retired subject
  When graph-level traversal and Requirement-level dependency evaluation run
  Then graph traversal follows the unchanged canonical node presence
  And historical lineage lookup still resolves the node
  And the retired Requirement is excluded from readiness evaluation
  And it cannot satisfy another Requirement's dependency
```

Additional examples should cover an editorial wording change retaining identity,
a move retaining identity while changing containment, criterion decomposition
returning every criterion target, composition returning every contributor,
canonical 1:1 supersession, ambiguous legacy evidence failing closed, and two
workspaces using the same local ID without collision.

## Staged Implementation Assignment and Gates

Implementation begins only after the canonical child is reviewed and adopted.
Keep each stage a separate bounded task/PR; later stages depend on accepted
artifacts from earlier stages.

| Stage | Bounded deliverable | Acceptance gates |
|---|---|---|
| 0. Canonical contract | Adopt the child refinement and its explicit relationship to SG-SPEC-0019. | Human review records the decision; node ID and lineage are collision-checked; YAML format/lint and graph validation pass; no runtime claim is made. |
| 1. Read model | Add typed parsing/validation for identified Requirement and criterion records while preserving legacy reads. | Fixtures cover valid dual-read, duplicate IDs, conflicting definitions, unknown references, and legacy input; validators never allocate IDs. |
| 2. Migration preview | Produce a deterministic, read-only mapping report for existing criteria and evidence. | Repeated runs are stable; every candidate mapping is reviewable; ambiguous/unmatched items are reported, not guessed; canonical files remain unchanged. |
| 3. Reviewed migration | Apply source-controlled IDs and explicit mapping to a bounded set of canonical records. | Review confirms identity assignment; reorder/format changes do not reassign IDs; old scenario IDs remain unchanged; graph/schema gates pass. |
| 4. Evidence and split consumers | Resolve criterion evidence and split mappings by full references. | Tests prove evidence is criterion-keyed and revision-pinned; decomposition/composition preserve every participant ID and directed endpoint role without joining revision chains; text/array order is never used as identity. |
| 5. Historical lookup | Add read-only resolution of current and retired subjects and revisions. | Tests cover move, revision, replacement, split, merge, withdrawal, unknown ID, and unavailable revision; no silent successor/latest redirection. |

For each implementation PR, run the focused tests and validators for the
changed contract, relevant graph/spec-evidence checks, and
`make proposal-tracking-gate` while the work remains associated with RFC 0221.
Do not claim runtime conformance from schema fixtures or local tests alone;
report exactly which stage and evidence have passed.

## Remaining Human Decisions

- Adopt, reject, or defer RFC 0221.
- Approve a canonical representation for criteria and decide whether the
  representation is embedded or separately stored.
- Approve workspace-identity ownership and the local allocator policy.
- Approve revision numbering and transition-record placement.
- Approve migration and evidence compatibility policy before any source data
  or runtime consumer is changed.
