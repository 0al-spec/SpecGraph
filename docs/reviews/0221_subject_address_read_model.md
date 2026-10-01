# RFC 0221: subject-address read model preparation

## Status and scope

This is a review-only implementation design under RFC 0221. Not canonical adoption, an
implemented schema, a migration authorization, or a runtime conformance claim.
The frozen SG-SPEC-0019 remains unchanged. This design prepares the read-model
stage described in the canonical adoption review packet; implementation follows
review and adoption of the bounded canonical contract.

The existing candidate graph already has `requirements[].id`,
`acceptance_criteria[].id`, and `acceptance_criteria_refs`. Its validator resolves
references against node-local criteria. Materialization preserves those records
under `specification` and also emits legacy string-valued `acceptance`. Start
from these records rather than replacing them with content-derived search IDs.

## Proposed concrete choices

| Concern | Proposed choice | Review boundary |
| --- | --- | --- |
| Workspace scope | Persist one immutable UUID in a versioned `.specgraph/subject-identity.json` declaration; keep `project_id` as display/routing data | This declaration and its clone/fork semantics require adoption; a URL or slug cannot substitute for identity |
| Criterion storage | Versioned identified records embedded in the containing specification, separate from Requirement nodes and BDD scenarios | Moving a criterion retains identity, advances revision by one, and preserves prior containment |
| Local IDs | Preserve reviewed existing candidate IDs when unique across the workspace; new authored IDs are collision-checked and never recycled | No ordinary parser, lookup, or materialization read allocates or remints an ID |
| Revisions | Positive integers, starting at 1, with exactly one immediate same-identity predecessor for later revisions | Identity, revision, and optional digest are separate values |
| History | Explicit retained revision records and typed containment/disposition/relation events | Git history alone is not a governed revision chain; the physical history layout needs separate review |
| Compatibility | Read legacy strings and identified records; preserve current writers until consumers support the identified form | No text matching or array-position inference supplies durable identity |

UUID uniqueness is not established by its syntax alone. Validate declarations
and detect known workspace collisions when joining datasets. A checkout of the
same workspace preserves identity; an independent product fork needs an explicit
identity decision. Known independent datasets claiming the same UUID fail closed
as `ambiguous_workspace_identity` before subject selection. A declared replica
of the same workspace retains that identity; conflicting replica declarations
also fail closed. Do not silently regenerate the declaration on clone or init.

The embedded form is a storage recommendation for criterion subjects only.
It does not convert embedded candidate requirements into canonical Requirement
nodes automatically or add a new canonical node kind.

## Address values

Illustrative boundary data, not an accepted URI syntax or ready-to-use config:

```json
{
  "workspace_id": "76b9bb2c-bf76-4ed5-ae53-998da35a049e",
  "subject_kind": "acceptance_criterion",
  "subject_id": "ac.calculator-product.result-visible",
  "revision": 1
}
```

`workspace_id + subject_id` determines identity; `subject_kind` is checked
against the record, not used to allow the same local ID for two different
subjects. A revision pin selects exact governed content. A path is returned as
current or historical containment and is never part of stable identity.

The read model should expose `SubjectRef`, `SubjectRevisionRef`,
`CriterionRecord`, `SubjectRevision`, and explicit lookup result types.
JSON/YAML decoding stays at the boundary. Domain values do not read files,
allocate IDs, change dispositions, or approve records.

## Lookup contract

Separate `lookup_exact(reference, revision)` from `lookup_current(reference)`.
An exact request never falls back to current/latest, a related subject, a
canonical successor, matching text, or a criterion in another workspace.

| Result | Meaning |
| --- | --- |
| `resolved` | Exact identity/revision exists; return statement, provenance, disposition, containment and explicitly authored relations |
| `unknown_workspace` | No matching immutable workspace declaration is available |
| `ambiguous_workspace_identity` | Independent datasets claim the same immutable workspace ID, or replica declarations conflict; reject the scope before selecting a subject |
| `unknown_subject` | Workspace exists but the subject ID is not registered |
| `revision_unavailable` | Subject exists but the requested revision cannot be resolved |
| `invalid_reference` | Missing scope, invalid revision, or a subject-kind mismatch |
| `ambiguous_definition` | Duplicate or conflicting definitions prevent a trustworthy lookup |

A retired subject can return `resolved`; disposition is independent of lookup
success. A retired Requirement cannot satisfy Requirement-level dependencies,
while graph topology follows SG-SPEC-0019 independently. Absence of execution
evidence does not change lookup success and must remain an evidence state.

`decomposes_into` and `composed_from` remain separately authored directed,
same-kind relations. They do not change participant revisions, dispositions,
or canonical topology and cannot be inferred by reversing each other.

Every authored relation endpoint is returned with its full durable subject
reference (workspace identity, subject class, local ID, and explicit exact/current
revision selection) and directed role. Endpoint class alone cannot identify it.

A one-to-one containment move advances the same subject revision by one and
retains the previous revision and containment. Replacement creates successor
revision 1 and records lineage without changing dispositions; activation and
withdrawal remain separate explicit disposition transitions.

## Compatibility and migration preview

1. Inventory existing IDs with their containing node and source artifact.
   Node-local validity does not establish workspace-wide uniqueness.
2. Preserve unique IDs as proposed identity assignments. Report duplicate IDs
   or conflicting meanings for human resolution; do not silently rename them.
3. Treat unscoped candidate references as candidate-local until a reviewed
   migration binds them to the declared workspace identity.
4. Keep legacy `acceptance` strings readable without manufacturing identities.
   The preview maps each source occurrence explicitly; ordinary reads do not
   infer identity by equality of strings or list positions.
5. Key future criterion evidence by full criterion reference and pin a revision
   for wording-specific claims. Requirement references and BDD scenario IDs
   remain distinct from criterion references.

## First implementation slice after adoption

One focused PR: typed parsing, validation, and read-only current/exact lookup
over fixtures. No allocator, writer switch, migration application, split
rewrite, Hypercode binding, or telemetry collector in that slice.

Acceptance cases:

- Existing candidate records and legacy strings remain readable in their
  original authority scopes.
- Reordering or moving an identified criterion preserves its full reference.
- The same local ID in two declared workspaces resolves independently.
- A declared replica preserves workspace identity; independent forks sharing
  that identity return `ambiguous_workspace_identity` with no selected subject.
- A containment move retains identity, advances revision, and preserves exact
  lookup of both the old and new containment.
- Replacement leaves dispositions unchanged; a separate activation is required.
- Relation traversal returns the full reference and role of every endpoint.
- A wording revision retains identity and exact old-revision lookup succeeds
  only when its explicit record is available.
- Unknown IDs, unavailable revisions, duplicate definitions, missing workspace
  scope, and cross-kind relation endpoints yield explicit diagnostics.
- Retired subjects resolve without satisfying Requirement dependencies.
- Reads leave all source bytes unchanged and never allocate IDs.

## Decisions still to record

The reviewer should accept, amend, or defer the proposed embedded form,
workspace declaration and clone/fork semantics, retained-history layout, local
ID allocation policy, and legacy compatibility policy. Preparation and a
successful supervisor run do not supply this adoption decision.

## Preparation through SpecGraph

The supervisor refined a temporary `DRAFT-SPEC-0221` node in an isolated
checkout of SpecGraph. Its inputs included RFC 0221, the adoption review packet,
SG-SPEC-0019, and the candidate validator/materializer. An explicit operator
note restricted the task to preparation, with one allowed draft file.

Run `20261001T202808Z-DRAFT-SPEC-0221-68a85911` completed with executor exit 0,
`RUN_OUTCOME: done`, and proposed `specified`. The supervisor retained
`review_pending`, not approval: `classify_executor_environment` classified the
literal `migration ` in the echoed operator note and document text as a state
runtime failure. This is a reproduced diagnostic false positive, not proof
that the runtime checks were clean. No gate override or retry was performed.

The [curated supervisor candidate](0221_supervisor_candidate.yaml) remains
outside `specs/nodes`. Its `status` and original output paths describe the draft
run, not adoption or a live canonical node. The temporary target was removed
from the task checkout after curation. No existing canonical specification was
changed. The [bounded evidence summary](0221_preparation_evidence.json) records
the run, raw and curated digests, the gate, diagnostics, and curation changes;
raw executor transcripts and machine-local runtime files remain untracked.

Review corrected the candidate's conflation of retired-subject lookup with
dependency satisfaction. A retired subject remains historically resolvable;
its inability to satisfy a Requirement dependency is a separate result.
Review also made exact/current selection explicit and clarified that subject
class does not permit duplicate workspace-local IDs. These corrections are
curation of the returned draft, not changes verified by the supervisor run.

The concrete read-model recommendations above use proposed names and a proposed
UUID declaration; the supervisor candidate's examples use illustrative names.
Neither form is an accepted serialization schema. Review should reconcile the
physical schema before implementation. The candidate's embedded Requirement
inputs remain candidate records; canonical Requirement subjects continue to use
the existing node kind.

The runtime classifier issue was fixed separately in PR #746 with regressions
for ordinary migration prose and actual state-runtime failures. Replaying the
recorded stderr yields no environment issue with the fixed classifier. This
does not change the historical artifact, approve the gate, or adopt governance.

## Sources

- [RFC 0221](../proposals/0221_stable_requirement_identity_and_lineage.md)
- [Canonical adoption review packet](0221_canonical_adoption_review_packet.md)
- [Candidate reference validator](../../tools/candidate_spec_graph.py)
- [Candidate materialization](../../tools/candidate_spec_materialization.py)
