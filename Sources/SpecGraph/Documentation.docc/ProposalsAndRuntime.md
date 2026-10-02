# Proposals and Runtime Evidence

SpecGraph treats proposal records and runtime evidence as connected surfaces.

## Proposal Records

Proposal markdown under `docs/proposals/` describes bounded changes and their
intended relationship to canonical specifications. Changes that affect proposal
documents should include matching tracking material or an explicit
documentation-only classification.

Before assigning a proposal ID, update the checkout that `make proposal-id`
will scan. Fetching alone is not sufficient: `git fetch origin --prune` updates
remote-tracking refs, but a stale local branch can still allocate an ID that
already exists on `origin/main`.

Use `make proposal-id` only after updating `main` with `git pull --ff-only`, or
after rebasing or merging the task branch onto `origin/main`. Then check the
candidate ID across local files, remote refs, local worktrees, and open GitHub
PRs. The open-PR check should inspect PR metadata, changed proposal/source
paths, and diffs for PRs that touch proposal registries; metadata alone is not
enough because a PR can claim an ID only through files or registry content.

If any branch, worktree, proposal file, registry entry, or open PR already uses
the candidate ID, do not reuse it. Synchronize with `main`, coordinate with the
active PR owner if needed, and allocate the next deterministic ID.

## Runtime Evidence

Runtime evidence lives in generated registries, viewer-facing JSON, and local
run artifacts. Evidence should support claims about realized behavior without
turning local runtime artifacts into canonical documentation by accident.

## Validation Gate

Use the proposal tracking gate when proposal documentation changes:

```bash
make proposal-tracking-gate
```

## RFC 0221 subject-address preparation

The historical RFC 0221 subject-address preparation was review-only. Its read
model design builds on existing candidate Requirement and criterion IDs
and `acceptance_criteria_refs`. It proposes immutable workspace scope,
identified criterion records, separate identity/revision/containment,
`lookup_exact` and `lookup_current`, and explicit unresolved outcomes.

Reads must not allocate IDs or silently match legacy strings to identities.
Candidate-local references require reviewed workspace binding before becoming
durable subject references. Migration, runtime implementation and Hypercode
integration remain separate stages. The preparation and supervisor evidence
are documented in `docs/reviews/0221_subject_address_read_model.md` and the
RFC 0221 canonical adoption review packet. A successful draft refinement does
not adopt the proposal or change frozen SG-SPEC-0019.

## Readiness policy refactors

Trace current producer guarantees before extracting a fallback into a
specification. The repaired handoff no-op fallback was redundant because the
repair-loop producer already handled clean no-op readiness. Artificial input
tests alone did not establish reachability through that production chain.

Candidate repair readiness now consumes source facts and returns a typed
outcome from one boolean specification. `no_op_repair_loop` remains independent
of `ready`: findings can block a ready pre-SIB graph with no actions while the
no-op observation stays true. Preserve those projections and test optional
decision traces. Evaluate confirmed redundant decisions and restored policy
boundaries alongside complexity measurements.

## Executor transcript diagnostics

Nested executor stderr can include operator notes, specification text, and
diffs alongside runtime logs. Migration vocabulary alone is not evidence of a
runtime failure. Require explicit state failure diagnostics such as
`failed to open state db`, `failed to initialize state runtime`, or
`state db discrepancy`; keep ordinary migration plans and successful migration
logs out of environment findings. Test both the classifier and the supervisor
run artifact so narrative text cannot contaminate the executor-environment gate.
Historical run artifacts and pending human review remain historical evidence;
a classifier fix does not approve a previously retained candidate.

### Curated contract completeness

When curating a supervisor candidate from an RFC, compare every transition and
lookup result with the source contract: preserve revision advancement, separate
lineage from disposition, identify every relation endpoint, and define failure
outcomes for ambiguous identity scopes. Update the curated artifact digest and
record corrections as curation, not as evidence verified by the original run.

## RFC 0221 canonical contract review

SG-SPEC-0068 was pending human approval; the human approved its bounded semantic
contract on 2026-10-02. It is now specified and human_approved; PR #747 merged
the semantic contract as `ed8a00c7d34ab5df5f3c8c29460a8d9231a10311`.
The approval packet is `docs/reviews/0221_canonical_contract_approval.md`.
It proposes workspace-scoped subject identity, revisions, transitions and exact
lookup while preserving frozen SG-SPEC-0019 and its one-to-one canonical
supersession contract. Preparation and passed checks alone are not adoption; the actual human approval
source and reviewed commit are recorded in the packet and node.

Human approval and merge are recorded separately.
Storage, allocator, physical history and source migration remain deferred.
The first separately authorized implementation provides partial read-model
evidence; full runtime conformance is not established.

## Subject read model implementation

`tools/subject_read_model_io.py` accepts an explicit `subject_read_snapshot`
(schema version 1, YAML or JSON) and returns a JSON `subject_lookup_result`.
Select exactly one of `--revision N` or `--current`, together with `--snapshot`,
`--workspace-identity`, `--subject-class` and `--subject-id`. Exit codes are
0 for resolved with complete supplied-scope relations, 1 for unresolved lookup
or incomplete relations, and 2 for invalid input/arguments.

Identity combines workspace and local subject ID; class validates the record.
`dataset_identity` declares replicas, without establishing trust. Independent
sources or conflicting replicas sharing a workspace fail closed before lookup.
Exact lookup never falls back to current or reconstructs missing history.
Results expose `current_subject_disposition` with provenance separately from
exact content, and `retained_containment_history` without invented revisions.
Authored relations preserve full endpoints and roles in both query directions.
Every returned relation retains `source.workspace_identity` and
`source.dataset_identity`; the stable relation key combines source workspace and
local relation ID. `relation_resolution` exposes `complete`/`incomplete` and the
conflicting sources within `supplied_snapshots`. Resolved subject content does
not establish complete lineage. Unrelated source conflicts do not taint a query.
One dataset declaring multiple workspaces makes every affected scope ambiguous.
Unordered reference/endpoint collections are normalized for replica comparison.
`retained_disposition_transitions` preserves supplied activation/withdrawal
events and provenance. Duplicate event references and a retained basis event
contradicting the current projection are rejected. Presentation order never
selects the current state or asserts event chronology/as-of history.

Each Requirement revision preserves its own `acceptance_criteria_refs` collection
with exact criterion pins. Link membership or pin changes require a new governed
Requirement revision. Exact lookup never substitutes current links; a criterion
move does not rewrite ownership automatically. Historical collections remain
readable after the affected Requirements acquire new revision-specific links.

`subject_legacy_reads.parse_compatibility_document` inventories candidate-local
records and unassigned legacy acceptance strings. It preserves source scopes,
IDs, text and occurrence locators; diagnostics expose missing/duplicate IDs.
It never promotes those records to workspace-bound canonical subjects.

The snapshot is an experimental exchange/fixture format. Construction and lookup
perform no writes or allocation; existing writers are unchanged. Dependency
evaluation, disposition/replacement writers, source migration, historical as-of
queries and Hypercode remain separate work. See `docs/subject_read_model.md`
and the fixture at `tests/fixtures/subject_read_model/snapshot.json`.

### Subject refactoring binding pilot

`tools/subject_refactoring_pilot.py` exercises RFC 0221 against SpecGraph PRs
743 and 744. The explicit plan maps four existing proposal statements to exact
pilot criterion references, pinned implementation symbols and test executions.
`--execute --output-dir <new-directory>` runs four selected tests at each of
three historical checkpoints in disposable archives, then collects a direct
policy trace for `candidate_repair.preview_ready`. Missing old code anchors and
unavailable criterion revisions remain unresolved.

The pilot declaration is separate from canonical workspace identity. Criterion
revision 1 was authored for the experiment, not reconstructed from Git history.
`canonical_requirement` remains unassigned and `canonical_readiness` is
`not_evaluated`; passing tests do not adopt the mapping. Source-only runs remain
incomplete, and existing output directories are rejected to prevent reuse of
stale test evidence. See `docs/reviews/0221_refactoring_binding_pilot.md` and its
curated JSON report. The result is experimental evidence for this bounded family.

### Repaired-candidate Requirement mapping review

`docs/reviews/0221_requirement_mapping_review.md` and its JSON packet prepare
two standalone Requirement candidates: review readiness owns three exact pilot
criteria, while separate Platform promotion approval owns one. This 3 + 1
partition keeps readiness and authorization distinct. The packet is
`review_pending`, with `canonical_readiness: not_evaluated`; merging preparation
does not adopt the mapping or authorize materialization.

The proposed namespace mapping retains the original pilot references. A different
workspace creates a distinct identity, even when the local ID and statement are
preserved. Destination revision 1 starts at actual adoption, with no same-identity
predecessor. Historical test executions and policy events retain their source
references; destination evidence applicability requires an explicit authored link.

At that packet's preparation, physical workspace declaration, standalone
Requirement and criterion storage, and a validating canonical-source
writer/adapter were deferred decisions under SG-SPEC-0068. Proposed canonical
files remain absent. The attempted Sol 6.1 Medium supervisor
run failed because the local CLI rejected the model and the initial input lacked
aligned acceptance evidence. The corrected agent-authored packet passed separate
structural checks; this is not successful supervisor refinement or canonical
runtime readiness. See `0221_requirement_mapping_evidence.json` for those distinct
statuses.

### Standalone subject storage preparation

SG-SPEC-0069 is a pending child of SG-SPEC-0068 proposing the physical YAML
format: `specs/workspace_identity.yaml`, one Requirement node per file in
`specs/requirements/`, and separate criterion records in `specs/criteria/`.
Append-only `revisions` retain statement, containment, node metadata and exact
acceptance references. Top-level metadata is a validated current projection;
disposition events remain independent. No new criterion seed node kind is added.

Seven `subject_storage_candidate` envelopes in `docs/reviews/0221_subject_storage/`
prepare the workspace declaration, two Requirements and four criteria with the
same 3 + 1 partition. `gate_state: review_pending`,
`canonical_readiness: not_evaluated` and `ready_for_materialization: false` keep
preparation distinct from canonical adoption. Origin provenance and disposition
are deliberately null. The workspace UUID is still an unreserved review token.

The canonical-source adapter and validating writer are `not_implemented`.
Schema approval, reviewed namespace mapping and SG-SPEC-0051 materialization
decisions precede publication. Historical pilot references and evidence remain
unchanged; candidate validation does not transfer them or prove runtime
conformance. See `docs/reviews/0221_subject_storage_preparation.md` and the
candidate manifest for the concrete review choices and remaining decisions.

### Canonical approval gates and lookup projections

A canonical contract awaiting human approval must use `gate_state: review_pending`
so operational queues cannot classify it as ready. Resolve that state only with
recorded human decision provenance, and keep promotion/runtime scope descriptions
aligned with the approved slice. An exact content revision does not select an
as-of disposition when activation/withdrawal are independent events: label the
current disposition explicitly and keep historical as-of claims separate.

### Read-model construction invariants

Validate reference resolvability at the shared typed-index boundary so Python
callers cannot bypass CLI checks. Frozen dataclasses need immutable nested
collections as well. Test cross-workspace incoming relations, declared replica
coalescing and retained history explicitly; a successful selected lookup alone
does not prove those projections are complete.

When querying across namespaces, carry the source binding of relationship
records as well as endpoint identities. Distinguish incomplete enumeration from
an empty complete result. Define which references belong to a content revision
before describing lookup as historical; test changing those links independently
of the statement. These are contract invariants, not presentation details.
