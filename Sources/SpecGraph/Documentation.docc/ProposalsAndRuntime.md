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
Append-only `revisions` retain statement, containment, node metadata, authored
`revision_scope` and exact acceptance references. Requirement `provenance` uses
the SG-SPEC-0024 node envelope in each revision's `node_fields.provenance` and
the validated current projection. That envelope is separate from the governed
decision reference in `revision.provenance`. Disposition events remain independent
and use `activation`/`withdrawal`. No new criterion seed node kind is added.

Exact case-sensitive IDs remain distinct. Portable allocation and whole-tree
validation reject workspace-wide ASCII case collisions such as `REQ.A`/`req.a`,
across subject classes, grouping directories and retired records. Lowercase ASCII
grouping components do not create additional identity scopes.

Seven `subject_storage_candidate` envelopes in `docs/reviews/0221_subject_storage/`
prepare the workspace declaration, two Requirements and four criteria with the
same 3 + 1 partition. `gate_state: review_pending`,
`canonical_readiness: not_evaluated` and `ready_for_materialization: false` keep
preparation distinct from canonical adoption. Origin decision provenance and
disposition are deliberately null. Requirement node actor, timestamp and inferred
confidence are also null in current and retained envelopes, with explicit pending
field paths. Authored scopes describe proposed origins rather than past adoption.
The workspace UUID is still an unreserved review token.

The canonical-source adapter and validating writer are `not_implemented`.
Schema approval, reviewed namespace mapping and SG-SPEC-0051 materialization
decisions precede publication. Historical pilot references and evidence remain
unchanged; candidate validation does not transfer them or prove runtime
conformance. See `docs/reviews/0221_subject_storage_preparation.md` and the
candidate manifest for the concrete review choices and remaining decisions.
`docs/reviews/0221_subject_storage_review_resolution.md` records the PR #751
contract corrections and fixture-level prevention checks; writer enforcement
remains deferred.

### Physical schema and mapping approval packet

`docs/reviews/0221_subject_storage_approval.md` and its YAML packet select the
SG-SPEC-0069 version-1 physical schema merged in PR #751. `reviewed_commit` and
ten reviewed-file digests bind the unchanged contract, preparation manifest,
original mapping and seven candidates. `approval_scope_sha256` binds the complete
review scope; it is a content digest, not a signature or proof of authorization.

The packet names three decisions: physical schema, future workspace/ID plan and
exact 3 + 1 Requirement membership with four cross-workspace mappings. It also
requests bounded implementation authorization for the source adapter and writer.
Decision templates remain null. `gate_state: review_pending`,
`canonical_adoption: false` and `ready_for_materialization: false` retain the
human decision boundary. Approval must cite the delivered scope, actual reviewer,
authority, timestamp, outcome, rationale, provenance and source quote; changed
reviewed content needs another explicit decision.

Implementation permission does not authorize canonical subject publication.
SG-SPEC-0051 materialization after a verified writer, source migration and evidence
applicability retain separate authorization. Historical pilot identities and
executions are unchanged. Record a genuine decision separately after human
approval, preserving the prepared packet and original mapping as historical
preparation. Only then resolve the appropriate review gate.

`docs/reviews/0221_subject_storage_approval_evidence.json` records read-only native
checks and the operational gate. Its diagnostic `done` does not establish approval,
adoption, readiness or writer conformance. The first implementation slice after
approval is the read-only canonical-source adapter.

### Canonical approval gates and lookup projections

A canonical contract awaiting human approval must use `gate_state: review_pending`
so operational queues cannot classify it as ready. Resolve that state only with
recorded human decision provenance, and keep promotion/runtime scope descriptions
aligned with the approved slice. An exact content revision does not select an
as-of disposition when activation/withdrawal are independent events: label the
current disposition explicitly and keep historical as-of claims separate.

When defining a closed physical schema, inventory the inherited governance
fields, including node provenance and bounded revision scope. Preserve them in
historical records and current projections, check filename portability separately
from logical identity, and test against the governing contracts rather than only
the new draft's own field list.

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

## Recorded RFC 0221 physical-schema approval

The actual human reply “Одобряю пакет PR #752” approves the delivered physical
schema and mapping packet. `docs/reviews/0221_subject_storage_decision.json`
records the quote, reviewer authority, delivered head, `approval_scope_sha256`
and a review for each of the four exact mappings. The prior packet's
`review_pending` state remains a historical preparation snapshot.

SG-SPEC-0069 is now `human_approved` and `status: specified`; its native review
gate is resolved after attribution is recorded. The workspace/ID plan remains
unallocated. Bounded adapter/writer implementation is authorized, while
`ready_for_materialization: false` and canonical subject adoption remain false.
Runtime conformance is still `not_implemented` in this decision slice.
SG-SPEC-0051 canonical transitions, source migration, destination evidence
applicability and trusted runtime remain separate boundaries.

See `docs/reviews/0221_subject_storage_decision.md`. Byte-exact reviewed snapshots
keep prior schema/test hashes verifiable without rewriting prepared candidates,
pending decision templates or the original pilot evidence.

## Read-only RFC 0221 canonical-source adapter

`tools/subject_canonical_source.py` implements `read_canonical_source` against
the approved SG-SPEC-0069 physical schema. Its explicit source root and selected
topology/evidence binding produce an immutable index and source digest audit.
Strict checks cover the complete revision chain, node provenance, authored
`revision_scope`, exact criterion pins, current projections, portable collisions
and containment paths. Reads allocate nothing and never publish source files.

Snapshot exchange v1 optionally retains `node_fields`/`revision_scope` and
`retained_disposition_order`. Exact lookup preserves historical metadata, while
disposition is current and its authored event order remains available. Optional
provenance and nested trace values survive export/reparse; legacy output remains
unchanged. Canonical presence comes from the selected topology independently of
file presence or disposition. `caller_selected_not_attested` labels its evidence
boundary; external subject relations remain outside this supplied storage slice.

See `docs/subject_canonical_source.md`. This is
`partial_canonical_source_adapter` evidence, with
`canonical_readiness: not_evaluated`, `ready_for_materialization: false` and
`canonical_mutations_allowed: false`. Prior digest conflict enforcement, origin
allocation and atomic publication belong to the bounded writer slice below. Canonical
materialization, migration and destination evidence applicability remain separate.

## Bounded RFC 0221 subject-source Git writer

SG-SPEC-0069 now has a validating origin/content-revision writer in
`tools/subject_source_write.py`, with Git I/O in `tools/subject_source_git.py`.
The `git_commit_compare_and_swap_v1` backend selects an existing direct ref under
`refs/specgraph/subject-storage/`. The request binds an expected commit and the
complete prior source SHA256 map. New origins require an unused identity;
revisions retain all prior content and disposition history unchanged.

All changed records are prepared together outside the canonical source and
validated through the strict reader. A private Git index produces one commit;
the actual parent, changed paths and committed source bytes are checked before
publication. An expected-old-value ref update publishes the entire source tree
atomically and rejects concurrent winners. The operator checkout, index and
ordinary branches are untouched. This is Git-ref atomicity, not an atomic
multi-file filesystem checkout.

Publication requires an explicit authorization bound to `request_sha256` and
the exact transition decision references. `operator_supplied_not_attested`
labels that evidence; schema approval does not supply materialization authority.
Preview reports `source_ref_updated: false`; successful publication reports true.
Both retain `canonical_readiness: not_evaluated`, `ready_for_materialization: false`
and `trusted_runtime_receipt: false`.

See `docs/subject_source_write.md` and `tests/test_subject_source_write.py`.
Temporary fixture origins prove bounded writer behavior, including late CAS
conflicts and failure before publication. Production workspace/subject origins
remain unallocated. Containment moves, disposition changes, relations, topology,
migration and destination evidence applicability are separate slices.

Writer diagnostics distinguish malformed expected commit IDs (`invalid_input`,
exit 2) from deleted selected refs (`source_conflict`, exit 3), including deletion
at the CAS boundary. PR #758 regression fixtures prevent both classification gaps;
see the review prevention section in `docs/subject_source_write.md`.

## RFC 0221 canonical materialization review packet

`docs/reviews/0221_canonical_materialization_packet.json` is a digest-bound,
review-only `rfc0221_canonical_materialization_packet` with
`gate_state: review_pending`. It maps two Requirement
and four criterion SpecDraft candidates to six proposed canonical origins and
lists the twelve required `proposal -> spec_draft` and
`spec_draft -> canonical_artifact` review transitions under SG-SPEC-0051.
Every decision field remains pending; the packet is not a writer request or
publication authorization. `canonical_mutations_allowed: false` and
`ready_for_materialization: false` remain in force. The workspace declaration,
source-ref initialization, identity allocation and destination evidence links
also need their own genuine provenance. See
`docs/reviews/0221_canonical_materialization_packet.md` for the decision sequence.

Its exact `approval_scope_sha256` is
`29bb79bae19e096671aab6ababe34ff32c37002b9e3255b283d2001398c97fa6`.
After approval keep the packet immutable and store actual decisions in a
separate artifact binding packet path, raw-file digest, scope digest and reviewed
head; a changed scope requires a new packet version and new approval.
Intent lineage remains unresolved for all six ingresses and explicitly blocks
SG-SPEC-0051 advancement. Dataset/topology selection and origin, activation and
declaration provenance also need actual decisions covering those effects.

`make materialization-packet-check` checks all seven candidate inputs, proposal
and prior-decision bytes, pinned historical contract bytes, exact revision-1
targets, the 3 + 1 membership and twelve pending transition templates. CI runs
it with mutation regressions. Success proves a consistent pending snapshot only.
At this packet's preparation time the writer reported `operator_supplied_not_attested`
and its decision-to-request gate was absent. Those historical blockers are
retained in the immutable packet. The gate implementation below does not
approve its missing Intent lineage or pending decisions. Merge, digest
consistency and valid storage do not supply permission to publish.

## Governed subject publication

`tools/subject_publication.py` supplies a mandatory decision gate before writer
candidate creation and ref publication. `subject_publication_evidence` selects
an explicit repository, immutable evidence commit and decision artifact. The
gate resolves packet bytes at their reviewed head and scope-bound recorded
human decisions. `subject_publication_decisions` must cover paired ingress and
canonical transitions, reviewed Intent lineage, exact subject revisions,
workspace allocation, activation, topology and the exact writer request.

Publication requires `--governance`; missing or inconsistent evidence produces
`governance_blocked` with exit code 4 and no ref update. Preview remains
preparation. The result is
`scope_bound_recorded_decisions_verified_not_attested` with
`reviewer_identity_attested: false`: recorded attribution is verified against
selected sources, while identity/signature attestation is outside version 1.
Schema approval cannot authorize origins. Tests use synthetic decisions in
temporary repositories. The old materialization packet still lacks Intent
lineage and approval; see `docs/subject_publication.md` for the artifact
contract, trust boundary and compatibility change.


The gate binds the complete reviewed subject record and workspace declaration.
Version 1 permits no post-review substitutions, including status, authority,
provenance or containment changes. New candidates require a new reviewed packet.
Malformed or unreadable governance selections also yield `governance_blocked`/4;
malformed request input remains `invalid_input`/2.

Three policies have separate modules and immutable typed contexts:
`subject_publication.complete_reviewed_record` (reused for declarations),
`subject_publication.human_approval` and `subject_publication.reviewed_transition`.
Policy tests verify their stable trace names. Parsing, Git I/O and publication
remain outside specifications. New decision-heavy tooling requires this
SpecificationCore policy review beyond refactoring pilots; deliberate
non-extraction belongs in the PR rationale.

The workspace allocation policy is also a separate specification:
`subject_publication.workspace_allocation`. It compares the reviewed effect with
the request's workspace identity, source ref, expected commit, both literal-true
permission flags and exact declaration digest. The writer keeps its conditional
bootstrap dispatch and governance failure message. Its dedicated context is
immutable and its predicate test covers each mismatch.


## Publication policy diagnostics

The proposed `publication_policy_classification` v1 manifest binds 75 guard and
dispatch sites in the publication gate to categories, stable IDs, AST predicate
hashes and architectural locations. The initial PR #762 snapshot reported 49
inline policies. The workspace-allocation extraction moves stable site
`publication.site.069` to its named specification. The complete current
classification should report 48 inline policies, no duplicate definitions and
no selected boundary violations. Four specifications now implement five sites
through reuse. These are proposed classifications, not human approval or
whole-project semantic discovery.

Initial scoped diagnostics counted **Inline policies (49)**, **Duplicate policy
definitions (0)** and **Policy boundary violations (0)**. The measured
post-extraction classification reports **Inline policies (48)**, **Duplicate
policy definitions (0)** and **Policy boundary violations (0)**. Its stable-ID
diff removes `inline:publication.site.069` with no added violation.

The diagnostic labels are Inline policies, Duplicate policy definitions and
Policy boundary violations; their complete-scope counts remain 48, 0 and 0.

Run `make publication-policy-diagnostics`. Changed, missing or unclassified
sites produce `counts: null`; an absent historical classification makes the
diff unavailable. Diffs enumerate new/removed violation IDs, so a net zero cannot
hide a new violation. The versioned classification and source hashes identify
the interpretation used by each snapshot. Classification changes require review.

Python CI uploads the run-local `publication-policy-diagnostics` JSON artifact.
The diagnostic has `merge_gate_enabled: false`; it does not block merge.
See `docs/publication_policy_diagnostics.md` for scope and interpretation.


Collector tests use an independent syntax corpus, avoiding a blocking threshold
on live project totals or classification completeness for this informational report.


## Registered Specification rule reuse

The separate Python CI `registered-rule-reuse` job invokes `check-rule-reuse`
with `tools/rule_reuse_catalog.toml` for the reviewed workspace allocation rule.
It uses the PR base catalog and a pinned SpecificationMetrics commit. First-time
activation is explicitly **bootstrap** and report-only; after the catalog lands
in the base, mode **enforcing** blocks `new_reimplementations > 0`, incomplete
parsing and stale canonical digests. Report readiness and exact base/head revisions
are checked even in bootstrap. Deleting the head catalog fails. Catalog
migrations need explicit review. Existing publication diagnostics retain
`merge_gate_enabled: false`; their informational classification is unchanged.

Only changed scoped Python predicates in if/elif/while/assert/require and lambda
bodies are covered; this is not project-wide semantic equivalence. Near matches
remain review-only. Static Specification call recognition is not runtime proof.
The real workspace allocation pilot reports procedural copies **1 → 0**, one
static spec use and four changed scoped files.

Run-local evidence contains JSON, catalogs, mode and `history.sqlite`, whose
`rule_reuse_snapshots` table stays separate from primary S/U history. Actions
retention bounds its availability; this is not a permanent cross-run database.
Jev semantic review is opt-in, makes no CI calls and never authorizes a blocking
match. Branch-protection requirements are separate GitHub settings. See
`docs/registered_rule_reuse.md` for authority, coverage and rollout details.
