# Product Workspace Pilots

SpecGraph can run in `product_workspace` mode when it should develop a user's
product graph instead of improving SpecGraph itself.

## First Pilot

The first real `product_idea_to_spec` pilot is Team Decision Log. It is a
small product domain, but it is not a mock or fixture: teams record decisions,
considered options, rationale, evidence, owners, review triggers,
consequences, and supersession or conflict relations.

Team Decision Log is product data, not a system-mode name. SpecGraph scripts,
Make targets, promotion gates, and SpecSpace consumers should stay generic for
`product_idea_to_spec`; a later product idea should be able to replace the
pilot payload without adding a product-specific flow.

The intended public route layout keeps one SpecSpace deployment with separate
workspaces:

```text
specgraph.space/
  -> SpecGraph bootstrap/showcase workspace

specgraph.space/team-decision-log
  -> Team Decision Log product_idea_to_spec pilot workspace
```

The Team Decision Log route should use product workspace artifacts and should
not expose SpecGraph bootstrap/self-evolution surfaces as product-domain state.

## Active Candidate Source

The next implementation slice should connect a validated Active Candidate
Source for Team Decision Log. Current public handoff artifacts can publish
`no_active_candidate` placeholders; those placeholders should become real
candidate materialization and promotion-gate artifacts only when the source is
an `active_candidate`, not fixture or demo leakage.

A valid pilot source should provide stable candidate and workspace identity,
active ontology/domain/context frame, consistent event-storming intake,
candidate graph, pre-SIB report, repair-loop state, materialization report, and
promotion gate refs.

Proposal `0155` implements the first deterministic local chain through the
generic product workspace target:

```bash
make product-workspace-active-candidate
```

The target writes `runs/active_idea_to_spec_candidate.json` after building the
Team Decision Log event-storming intake, candidate graph, pre-SIB report,
repair-loop preview, candidate materialization report, and promotion gate.
Static artifact publishing keeps `no_active_candidate` placeholders unless that
active candidate source is ready. Team Decision Log is the default fixture data
for the target, not a separate system-level flow.

## CLI Candidate Approval Flow

Proposal `0156` defines the next approval boundary for CLI and agent-mediated
product workspace operation. A ready candidate may be recommended by the agent,
but it should not move toward Git Service promotion without an explicit
operator decision.

The proposed approval surface is `runs/candidate_approval_decision.json`. It
should record public-safe refs, digests, decision state, and authority metadata
for the transition from `candidate_review_requested` to
`promotion_request_approved`. It must not create branches, commits, pull
requests, merges, read models, canonical spec mutations, or Ontology writes.

Proposal `0157` implements the first deterministic local approval artifact:

```bash
make candidate-approval-decision
```

The target writes `runs/candidate_approval_decision.json`. Its default decision
state is `needs_context`; approval requires an explicit
`CANDIDATE_APPROVAL_DECISION_STATE=approved` and ready upstream candidate/gate
artifacts.

## Review And Promotion Chain

SpecSpace can now route the product workspace separately from the SpecGraph
showcase and read the candidate graph, pre-SIB report, repair loop, promotion
gate, Platform promotion request, and Git Service execution report without
granting write authority.

Proposal `0158` adds the generic idea intake entry point. A
`user_idea_intake_source` now becomes `runs/idea_event_storming_seed.json` and
then the existing `runs/idea_event_storming_intake.json` through
`make generic-idea-intake`. Team Decision Log stays data; another product idea
can replace it at the intake-source boundary without new product-specific
scripts.

Proposal `0159` adds generic ontology-bound candidate graph seed generation
from approved intake data:

```bash
make ontology-bound-candidate-graph-seed
```

The `ontology_bound_candidate_graph_seed` generator reads the normalized
project-local SpecGraph core ontology IR and writes
`runs/candidate_spec_graph_seed.json`. It requires active ontology/domain/context
refs, ontology layer refs, and model applicability refs. Generated structural
candidate nodes bind to ontology classes such as `Spec`, `Node`, `Requirement`,
`AcceptanceCriterion`, and `Constraint`, while product-domain terms remain
ontology gaps until an owner explicitly accepts, rejects, or aliases them.

`make product-workspace-active-candidate` now runs the ontology-bound seed step
before building `runs/candidate_spec_graph.json`. Git Service post-review status
and read-model publication remain service operations outside SpecSpace write
authority.

Proposal `0160` makes the full active runner generic:

```bash
make product-workspace-active-candidate
```

The target now starts from `PRODUCT_WORKSPACE_IDEA_SOURCE`, writes
`runs/idea_event_storming_seed.json`, and carries public-safe workspace identity
through `runs/idea_event_storming_intake.json` into
`runs/active_idea_to_spec_candidate.json`. The active candidate config can now
contain only artifact refs; candidate id, display name, and route derive from
the generated intake, while governance fields use the standard active product
workspace defaults. Team Decision Log is the default
`PRODUCT_WORKSPACE_IDEA_SOURCE` fixture for the product pilot, not a separate
system flow. Passing `PRODUCT_WORKSPACE_INTAKE_SOURCE=<seed.json>` keeps the old
prepared-seed input mode for backcompat; prepared seeds without
`source_intake.workspace` need an explicit active candidate config.

Proposal `0161` makes the active candidate source artifact-derived by default.
The standard `make product-workspace-active-candidate` flow no longer needs an
active candidate config fixture: `runs/active_idea_to_spec_candidate.json`
reads the generated intake, candidate graph, pre-SIB report, repair loop,
materialization report, and promotion gate from their standard `runs/*` paths.
The artifact records `config_source.required=false` and `source_derivation` so
downstream consumers can see whether artifact paths came from defaults or from
an explicit compatibility/debug override.

Proposal `0162` adds `user_idea_intake_session` as the first deterministic
raw/session intake boundary:

```bash
make user-idea-intake-session
make generic-idea-intake-session
```

The session writes `runs/user_idea_intake_session.json` and, when it has enough
ontology/domain/context/layer/applicability and event-storming context,
`runs/user_idea_intake_source.json`. Missing context becomes public-safe
clarification questions instead of silently entering the candidate graph path.
`make product-workspace-active-candidate` now runs this session step before the
existing intake-source builder in generated mode. Prepared
`user_idea_intake_source` inputs remain supported for compatibility and tests.

Proposal `0184` adds the first operator-facing real-intake CLI wrapper:

```bash
make real-idea-intake
```

The wrapper writes a local-only
`runs/local_operator_user_idea_raw_input.json`, runs the existing
`user_idea_intake_session` gate, and writes a public-safe
`runs/user_idea_intake_interview_report.json`. It can accept explicit
ontology/domain/context/layer/applicability refs, event-storming hints, and
accepted clarification answers. It does not execute a prompt agent or infer
missing product semantics; under-specified input remains
`needs_clarification`.

Proposal `0185` adds a review-only bridge from a ready intake session to the
standard candidate-source artifact:

```bash
make intake-session-candidate-source
```

The bridge reads `runs/user_idea_intake_session.json`, validates that its
embedded `candidate_source_input` is public-safe and ready, and writes
`runs/user_idea_intake_source.json` plus
`runs/intake_session_candidate_source_report.json`. It rewrites source
provenance to the intake session instead of the local raw-input artifact, so raw
idea text remains local-only while the existing generic intake chain can start
from a real intake session.

Proposal `0186` adds the real-intake clarification loop for under-specified
ideas:

```bash
make real-idea-intake-clarification-requests
make real-idea-intake-clarification-answers
make real-idea-intake-clarification-rerun
make real-idea-intake-ready-candidate-source
```

The loop writes intake-specific clarification request/answer/rerun artifacts,
including `runs/idea_intake_answer_rerun_input.json`,
`runs/clarified_user_idea_intake_session.json`, and
`runs/idea_intake_clarification_rerun_report.json`. It applies accepted answers
through the same review-only intake wrapper, then the candidate-source bridge
prefers the clarified session when present. It does not execute prompt agents,
infer missing semantics with an LLM, mutate specs, write Ontology packages, or
publish raw idea text.

Proposal `0187` adds the active-candidate convenience flow for ready real-intake
sessions:

```bash
make real-idea-intake-active-candidate
```

The target sequences the missing bridge explicitly:

```text
ready or clarified user_idea_intake_session
  -> user_idea_intake_source
  -> idea_event_storming_seed
  -> product-workspace-active-candidate
```

It preserves the existing contract boundary: `product-workspace-active-candidate`
still consumes an event-storming seed, not a raw `user_idea_intake_source`. A
direct intake-source input now fails with an actionable operator message instead
of a later seed-contract mismatch.

Proposal `0188` hardens the staged real-intake clarification workflow. The
`real-idea-intake-clarification-requests` target now preserves an existing
`USER_IDEA_INTAKE_SESSION_OUTPUT` artifact and emits clarification requests from
that session by default. It only rebuilds intake when the session is missing or
when the operator passes `REAL_IDEA_INTAKE_REFRESH=1`. This keeps isolated
real-idea smoke runs from accidentally replacing a product-scoped intake session
with a generic fallback session.

Proposal `0189` keeps real-idea active frames aligned with active-candidate
validation by appending the candidate-local domain ref derived from
`candidate_id` while preserving broader product domain refs. A renovation idea
can therefore carry both `domain.home_renovation_project_management` and
`domain.apartment_renovation_assistant` instead of failing later with
`active_candidate_domain_mismatch`. Auto-appended domain refs carry
`domain_ref_derivations` metadata and are not marked owner-confirmed.

Proposal `0190` adds a run-directory wrapper for live real-idea smoke runs:
`make real-idea-smoke REAL_IDEA_SMOKE_RUN_DIR=runs/<id>`. The target routes the
existing real-intake active-candidate chain into the selected directory and
writes a compact `real_idea_smoke_summary.json` without publishing raw idea
text. The wrapper normalizes repository-local absolute run dirs, rejects
external absolute paths, clears ambient active-candidate config, and writes the
summary even when intake gates block. Upstream artifact summaries are whitelisted
before inclusion so raw idea text cannot leak through smoke telemetry.

Proposal `0191` adds conservative topology edges to ontology-bound candidate
graph seeds. Each generated candidate node is linked from
`candidate-spec.product-boundary` with `decomposes_to`, so pre-SIB topology
metrics no longer treat a real idea candidate as entirely orphaned. The edge
generation does not infer domain causality or event ordering; it is a temporary
flat anti-orphan topology layer, not an ontology-validated event-storming
relation model. A clean pre-SIB pass-through also yields a ready no-op repair
loop instead of a false `repair_loop_not_ready` blocker.

Proposal `0192` makes repeated real-idea smoke runs safer. By default,
`make real-idea-smoke` clears wrapper-owned derived outputs inside
`REAL_IDEA_SMOKE_RUN_DIR` before rebuilding, so a second run cannot silently
reuse an older `user_idea_intake_session.json`. Operator-authored answer input
files are preserved, but generated answer/rerun/repair/maturity outputs and the
default `absent-post-approval` directory are cleared. `REAL_IDEA_SMOKE_REFRESH=0`
keeps the old reuse behavior when that is intentional. The companion
`make real-idea-smoke-idea-maturity` target builds Idea Maturity from the same
run directory and sends optional post-approval Platform/Git inputs to
`REAL_IDEA_SMOKE_MATURITY_ABSENT_DIR`, preventing stale canonical `runs/*.json`
artifacts from overstating custom smoke lifecycle state.

Proposal `0163` adds `idea_to_spec_clarification_requests` as the unified
read-only question/action surface:

```bash
make idea-to-spec-clarification-requests
```

The standard product-workspace runner writes
`runs/idea_to_spec_clarification_requests.json` after the repair loop. Intake
questions, pre-SIB findings, repair-loop context requirements, candidate graph
gaps, and ontology gap groups become stable request ids with suggested answer
shapes such as `bind_existing_term`, `alias`, `propose_project_local_term`,
`reject`, or `defer`. The artifact does not accept answers, mutate canonical
specs, write ontology packages, approve candidates, or create Git branches.
Proposal `0164` adds `idea_to_spec_clarification_answers`:

```bash
make idea-to-spec-clarification-answers
```

The answer report validates an `idea_to_spec_clarification_answer_set` against
the request ids from proposal `0163`. Accepted answers can make blocking
requests ready for a future deterministic rerun, while `proposed`, `rejected`,
and `deferred` records remain review evidence. The report does not apply
answers to intake artifacts, mutate candidate graphs, write ontology packages,
approve candidates, or create Git branches.

Proposal `0165` adds `idea_to_spec_answer_rerun_input`:

```bash
make idea-to-spec-answer-rerun-input
```

The rerun input report converts accepted clarification answers into explicit
review-only overlay hints for the next deterministic run: active frame updates,
event-storming hints, ontology term bindings, aliases, project-local terms,
candidate acceptance criteria, graph edges, and claim reviews. If the answer
report is not ready, the overlay remains blocked with findings. The report does
not apply answers to source artifacts, mutate candidate graphs, write ontology
packages, approve candidates, create Git branches, or publish read models.

Proposal `0166` adds `idea_to_spec_rerun_preview`:

```bash
make idea-to-spec-rerun-preview
```

The preview report evaluates the accepted-answer overlay against the current
event-storming intake and candidate graph. It shows active-frame merge effects,
event-storming additions, preview-resolved ontology gaps, still-unresolved
ontology gaps, and candidate review hints. A project-local term, binding, alias,
rejection, or deferral can resolve the preview state for a gap, but the report
does not apply answers to source artifacts, mutate candidate graphs, accept
ontology terms, write ontology packages, approve candidates, create Git
branches, or publish read models.

Proposal `0167` adds `idea_to_spec_rerun_materialization`:

```bash
make idea-to-spec-rerun-materialization
```

The materialization report consumes a ready rerun preview and current candidate
graph, then nests a materialized candidate graph preview inside
`runs/idea_to_spec_rerun_materialization.json`. Preview-resolved ontology gaps
are removed from node `gaps` and preserved as explicit
`ontology_gap_resolutions`; unresolved ontology gaps remain visible. The report
does not rewrite `runs/candidate_spec_graph.json`, accept ontology terms, write
ontology packages, approve candidates, mutate canonical specs, create Git
branches, or publish read models.

Proposal `0168` adds `product_ontology_gap_review_decisions`:

```bash
make product-ontology-gap-review-decisions
```

The decision report consumes ready `idea_to_spec_clarification_answers` and
extracts accepted ontology-gap answers into
`runs/product_ontology_gap_review_decisions.json`. Product ontology decisions
can bind an existing term, alias a term, propose a project-local term, reject a
non-domain term, or defer to owner review. The report remains review-only: it
does not import Ontology owner decisions, accept ontology terms, write ontology
packages, mutate candidate artifacts, approve candidates, create Git branches,
or publish read models.

Proposal `0169` lets `idea_to_spec_answer_rerun_input` consume those product
ontology decisions:

```bash
make idea-to-spec-answer-rerun-input \
  IDEA_TO_SPEC_ANSWER_RERUN_INPUT_ONTOLOGY_DECISIONS=runs/product_ontology_gap_review_decisions.json
```

When the decision artifact is supplied, it becomes the ontology review source
for rerun overlay hints. The rerun preview also exposes
`candidate_quality_preview`, a read-only signal showing whether ontology gap
decisions resolved all, some, or none of the candidate ontology gaps. This does
not apply answers to source artifacts, mutate candidate artifacts, accept
ontology terms, write ontology packages, approve candidates, create Git
branches, or publish read models.

Proposal `0175` adds conservative ontology gap matching normalization to the
same review-only preview chain. Resolved ontology gaps now include
`match_kind`, `safe_phrase_match`, `confidence`, `decision_id`, `gap_term`,
and `decision_term` evidence, and the materialized candidate graph preview
preserves that evidence inside `ontology_gap_resolutions`. Safe variants such as
`Payment Record -> Payment Recorded`,
`Local Notification -> Local Notification Service`, and
`Renewal Date -> Renewal Date Updated` can resolve in preview state, while
broad single-word terms such as `Subscription` do not automatically resolve
event/action gaps such as `Subscription Added` or `Subscription Cancelled`.
If several decisions match one gap, the preview chooses the strongest
`match_kind` before falling back to source order for ties. `confidence` is a
triage signal: exact matches are `high`, safe inflections are `medium`,
directed phrase matches are `low`, explicit target refs are `explicit_target`,
and aggregate gap actions are `aggregate_scope`. `safe_phrase_match` is
directional, so the decision term must be the prefix and the gap term may only
add one safe suffix.
This remains review-only: no ontology terms are accepted and no candidate or
canonical artifacts are mutated.

Proposal `0176` adds candidate repair answer materialization to the same
review-only chain. Accepted `candidate_gap` answers now produce
`candidate_gap_preview` records, and targeted answers can remove product/spec
gaps from the nested materialized candidate graph preview while preserving
evidence in `candidate_gap_resolutions`. Deferred candidate answers stay
unresolved, and matching is by explicit `target_ref` only, not fuzzy text
similarity. The repair session journal treats unresolved candidate gaps as
candidate-approval blockers alongside unresolved ontology gaps.

Proposal `0177` adds the repaired candidate promotion handoff. After
`idea_to_spec_rerun_materialization` removes repaired gaps, run:

```bash
make repaired-candidate-promotion-handoff
```

The target writes separate `repaired_*` artifacts for the repaired candidate
graph, pre-SIB report, repair loop preview, candidate materialization,
promotion gate, active candidate, repair session journal, and handoff report.
The default active-candidate and handoff outputs are
`runs/repaired_active_idea_to_spec_candidate.json` and
`runs/repaired_candidate_promotion_handoff_report.json`.
It preserves the product-scoped `product://...` source ref for active candidate
identity checks and records the rerun materialization preview as provenance.
If only structural pre-SIB findings remain, the normal repair preview can carry
them and the promotion gate records `pre_sib_findings_repaired_by_preview`.
The repaired journal can become ready for candidate approval review, but
Platform promotion stays false until a separate `candidate_approval_decision`.

Proposal `0178` adds a Metrics RFC adapter for the product lifecycle:

```bash
make idea-maturity-metrics
make idea-maturity-metrics-validate
```

The default output is `runs/idea_maturity_metrics_report.json`. The report uses
`metric_pack_id: idea_to_spec_maturity` and preserves the RFC state semantics
for `not_reached`, `not_available`, `blocked`, `ready`, `dry_run`, and related
states. It counts clarification load, answer materialization, ontology
grounding, candidate gap closure, workflow friction, promotion readiness, and
optional downstream review/publication state when Platform artifacts are
present. It remains observability-only: no canonical spec mutation, no Ontology
write, no ontology term acceptance, no prompt-agent execution, no Git action,
and no read-model publication.

Proposal `0180` adds typed `readiness_explainers` to the same report. These
explainers identify concrete lifecycle blockers such as Pre-SIB findings,
repair-session blockers, promotion-gate blockers, stale refs, policy failures,
and invariant failures. Each explainer carries `kind`, affected lifecycle
`blocks`, `next_action`, and public-safe `evidence_refs` so SpecSpace and
Platform can explain readiness without inventing a score or becoming approval
authorities.

The validation target writes
`runs/idea_maturity_metrics_validation_report.json` by invoking the sibling
Metrics CLI. SpecGraph produces telemetry, but Metrics owns the RFC/schema
validator. Public bundle refresh publishes both artifacts so SpecSpace can show
the metrics surface and whether it passed the Metrics contract.

SpecSpace now consumes those artifacts in the Product Workspace `Idea maturity`
section. Proposal `0179` adds product-lane wiring so the dashboard-ready product
review targets also produce the maturity surfaces by default:

```bash
make product-workspace-idea-maturity
make product-workspace-decision-backed-repair-chain
make product-workspace-repaired-promotion-handoff
```

The first target builds and validates the maturity report. The decision-backed
repair chain and repaired promotion handoff targets run it after their normal
review-only outputs. `make product-workspace-active-candidate` stays narrow and
does not run metrics validation.

The next slices are Platform awareness and a `local-subscription-control` demo
pass. Platform may use the report as an explanatory preflight signal before
promotion, but not as promotion authority. Concrete handoff artifacts and
existing gates remain the source of branch/commit/PR readiness.

Proposal `0181` adds explicit Metrics contract metadata to the maturity report:
schema refs, validation-report schema refs, validator id/version, and
compatibility-policy refs. This lets SpecSpace and Platform show which
Metrics-owned contract was used while SpecGraph remains only the producer of the
report and validation evidence.

Proposal `0170` adds a single convenience target for smoke and CI runs that
need the complete decision-backed review chain:

```bash
make product-workspace-decision-backed-repair-chain
```

The wrapper runs the normal product workspace candidate pipeline, validates
clarification answers, derives `product_ontology_gap_review_decisions`, passes
those decisions into `idea_to_spec_answer_rerun_input`, and then builds rerun
preview plus rerun materialization. It also forwards custom output paths across
the chained targets, so tests can keep artifacts isolated without manually
repeating the ontology-decision variable. The target only orchestrates existing
review-only tools and does not grant write authority.

Proposal `0171` adds the durable repair-session journal:

```bash
make idea-to-spec-repair-session-journal
```

The default output is `runs/idea_to_spec_repair_session.json`. It aggregates
the active candidate, clarification requests and answers, product ontology
decisions, rerun overlay input, rerun preview, rerun materialization, and
promotion gate into one read-only session artifact. The journal records source
refs and digests, ordered repair stages, accepted answers, ontology decisions,
resolved and unresolved ontology gap counts, and whether the candidate can move
to approval or Platform promotion. `make product-workspace-decision-backed-repair-chain`
writes the journal as its final step.

The journal remains audit/read-model state only. It does not apply answers,
accept ontology terms, mutate candidate artifacts, write canonical specs,
create branches, open pull requests, or publish read models.

Proposal `0172` adds a review-only import preview for SpecSpace-owned repair
draft state:

```bash
make specspace-repair-draft-import-preview
```

The default output is `runs/specspace_repair_draft_import_preview.json`. It
reads `runs/idea_to_spec_repair_drafts.json`,
`runs/idea_to_spec_repair_session.json`, and
`runs/idea_to_spec_clarification_requests.json`, then validates that the draft
state is owned by SpecSpace, keeps read-only authority flags, references the
current repair session, and targets existing clarification requests with
allowed actions. Valid drafts become sanitized clarification answer candidates
and product ontology decision candidates; deferred drafts and duplicate
superseded drafts remain visible as review evidence.
The draft-state input can be overridden with
`SPECSPACE_REPAIR_DRAFT_IMPORT_DRAFTS` for tests or local exports.

The import preview does not apply drafts, accept ontology terms, mutate
candidate artifacts, write canonical specs, create branches, open pull
requests, or publish read models.

Proposal `0173` converts a ready repair draft import preview into the standard
review-only rerun artifacts:

```bash
make product-workspace-repair-draft-rerun
```

The target refreshes `runs/specspace_repair_draft_import_preview.json`, then
writes `runs/specspace_repair_draft_rerun_report.json` plus the standard
`idea_to_spec_clarification_answers`,
`product_ontology_gap_review_decisions`, `idea_to_spec_answer_rerun_input`,
`idea_to_spec_rerun_preview`, `idea_to_spec_rerun_materialization`, and
`idea_to_spec_repair_session` artifacts. It reuses the existing review-only
builders, so ready SpecSpace drafts can be replayed into the durable repair
session without making draft state authoritative.

The draft rerun bridge does not apply drafts, accept ontology terms, mutate
candidate artifacts, write canonical specs, create branches, open pull
requests, or publish read models.
Use `SPECSPACE_REPAIR_DRAFT_RERUN_IMPORT_PREVIEW` when a smoke test or local
operator needs to replay a non-default import preview path.
If the preview is not ready, the bridge writes only
`runs/specspace_repair_draft_rerun_report.json` and leaves existing shared
rerun artifacts untouched. Ready reports include draft provenance back to
SpecSpace draft ids.

Proposal `0174` adds a SpecSpace repair rerun request gate:

```bash
make specspace-repair-rerun-request-gate
make product-workspace-requested-repair-draft-rerun
```

The default gate report is
`runs/specspace_repair_rerun_request_gate.json`. It reads
`runs/idea_to_spec_repair_rerun_requests.json`, a ready
`runs/specspace_repair_draft_import_preview.json`, and
`runs/idea_to_spec_repair_session.json`. The request must be SpecSpace-owned,
must contain exactly one active `prepare_repair_draft_rerun` request for the
selected workspace, and must keep `may_execute_specgraph`,
`may_run_make_target`, canonical mutation, ontology write, Git, and promotion
authority false.

`make product-workspace-requested-repair-draft-rerun` refreshes the import
preview, validates the request in strict mode, and then runs the proposal
`0173` rerun builder. If the request is invalid, the target stops before
writing shared rerun artifacts. The request remains explicit operator intent;
SpecGraph does not trust `operator_command` from SpecSpace as execution
authority. Use `SPECSPACE_REPAIR_RERUN_REQUEST_STATE`,
`SPECSPACE_REPAIR_RERUN_REQUEST_IMPORT_PREVIEW`,
`SPECSPACE_REPAIR_RERUN_REQUEST_REPAIR_SESSION`,
`SPECSPACE_REPAIR_RERUN_REQUEST_WORKSPACE_ID`, and
`SPECSPACE_REPAIR_RERUN_REQUEST_OUTPUT` to thread non-default handoff paths.

Proposal `0182` adds a generic product workspace repair-pack materializer plus a
curated Team Decision Log happy-path pack:

```bash
make product-workspace-repair-pack-state
make product-workspace-happy-path-repair-pack
```

The materializer reads a `product_workspace_repair_pack` fixture and the current
repair-session/clarification-request artifacts, then writes standard
SpecSpace-owned `runs/idea_to_spec_repair_drafts.json` and
`runs/idea_to_spec_repair_rerun_requests.json`. The generic happy-path target
then reuses the same import preview, rerun request gate, repair-draft rerun,
repaired promotion handoff, and Idea Maturity validation flow. The default
fixture is the Team Decision Log pack, but product identity stays in pack data
and `PRODUCT_WORKSPACE_REPAIR_PACK_WORKSPACE_ID`, not in the generic flow. The
expected happy-path result has zero unresolved ontology gaps, zero unresolved
candidate gaps, `ready_for_candidate_approval: true`, and Idea Maturity
`lifecycle_state: approval_ready`.

`make product-workspace-team-decision-log-happy-path-repair-pack` remains only
as a documented demo alias for the default Team Decision Log fixture.

The final maturity refresh intentionally treats approval and promotion artifacts
as absent for the repair-pack demo so stale local Platform state cannot leak
into the repair-pack readiness surface. Candidate approval, promotion request,
Git execution, review status, and read-model publication remain separate
Platform/Git Service flows.

Proposal `0183` publishes the Team Decision Log demo as a separate product
workspace artifact bundle. The static publish workflow builds the ordinary
bootstrap bundle first, then runs the Team Decision Log happy-path repair pack
and writes a second manifest under:

```text
workspaces/team-decision-log/artifact_manifest.json
```

SpecSpace production routes should consume that workspace-specific manifest for
`/team-decision-log` instead of the bootstrap root manifest.

## Authority Boundary

Team Decision Log remains non-canonical until a repository service accepts a
validated promotion request. The pilot must keep
`canonical_mutations_allowed: false` and route promotion only to
`product_spec_workspace` repository roles.

The product pilot must not:

- mutate canonical SpecGraph specs;
- write ontology packages directly;
- publish raw prompts, private operator notes, or local paths;
- use `specgraph_bootstrap` repository roles for product writes.

## Current Execution Order

1. Product workspace repair-pack materialization from
   `product_workspace_repair_pack` when running the happy-path demo.
2. Review-only import preview for SpecSpace-owned repair drafts from
   `specspace_repair_draft_import_preview`.
3. Request-gated repair draft rerun intent through
   `specspace_repair_rerun_request_gate`.
4. Review-only rerun artifacts from a ready SpecSpace repair draft import
   preview through `specspace_repair_draft_rerun_report`.
5. Controlled candidate rerun source selection from
   `idea_to_spec_rerun_materialization`.
6. Real idea intake CLI wrapper through `real-idea-intake`.
7. Intake-session candidate source bridge through
   `intake_session_candidate_source_report`.
8. SpecSpace intake UI or agent conversation wrapper for the same
   raw-input/interview contract.
9. Prompt-side enrichment for richer candidate graph authoring under the same
   ontology-bound seed contract.
10. SpecSpace workflow lane refinement for clearer active candidate blockers and
   repair suggestions.
11. Extend Platform Git Service orchestration through review status and
   read-model publication.
12. Refine product workspace workflow lane metrics and blocker copy.
13. Refine ontology applicability and layer-aware review as compiler support
   matures.

## Canonical Sources

The full planning contracts remain in repository Markdown:

- `docs/product_workspace_graph_versioning_roadmap.md`
- `docs/product_workspace_stable_mode_guide.md`
