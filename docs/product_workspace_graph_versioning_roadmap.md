# Product Workspace Graph Versioning Roadmap

## Purpose

This roadmap defines how product workspaces should version and publish
SpecGraph graph state in production.

Git is the preferred canonical version substrate for product graphs, but the
application must not behave as a direct UI over an arbitrary local folder with
`git init`. Product graph writes need a managed repository boundary that can
validate candidate state, create branches and commits, and publish read models
for SpecSpace.

## Target Shape

```text
SpecSpace UI
  -> Graph Repository Service
  -> Git-backed canonical store
  -> validated specs/nodes, docs/proposals, runs
  -> public-safe read model / artifact bundle
```

The write path and read path stay separate:

- canonical graph history lives in Git;
- draft and generated graph content lives in candidate workspaces until gates
  pass;
- SpecSpace reads published artifacts and read models;
- writes go through a service or CLI contract that owns validation, branch
  creation, commit creation, review, merge, and publication.

## First Product Pilot

The first real `product_idea_to_spec` pilot is `Team Decision Log`.

It is deliberately small, but it should not be treated as a mock or fixture. The
pilot domain includes decisions, considered options, rationale, evidence,
owners, review triggers, consequences, and supersession/conflict relations. That
shape exercises the core product workflow without reusing SpecGraph's
bootstrap/self-evolution domain as the test case.

`Team Decision Log` is product data, not a system-mode name. SpecGraph scripts,
Make targets, promotion gates, and SpecSpace consumers should stay generic for
`product_idea_to_spec`; the pilot may supply the active candidate source and
artifact payloads, but tomorrow's product idea should not require a new
product-specific flow.

The public deployment intent is:

```text
specgraph.space/
  -> SpecGraph bootstrap/showcase workspace

specgraph.space/team-decision-log
  -> Team Decision Log product_idea_to_spec pilot workspace
```

SpecGraph should publish separate product workspace artifacts for the pilot
instead of treating it as a core SpecGraph graph. The pilot must keep
`canonical_mutations_allowed: false` until the Graph Repository Service accepts
a validated promotion request for a `product_spec_workspace` repository role.

## Authority Boundary

The Graph Repository Service may prepare canonical changes, but it must not
silently mutate canonical graph truth.

Allowed first:

- create a candidate workspace;
- materialize a candidate graph;
- run ontology, SpecAuthor, pre-SIB, and structural consistency checks;
- create a branch or PR with validated changes;
- publish read-only artifacts for SpecSpace.

Not allowed in the MVP:

- browser-to-filesystem direct writes into `specs/nodes/*.yaml`;
- direct writes from SpecSpace into Ontology packages;
- direct writes from generated artifacts into canonical specs;
- merge to `main` without a repository policy decision;
- treating candidate graph state as accepted specification truth.

## Roadmap

### 1. Event-Storming Intake Artifact

Status: implemented in proposal `0149`.

Capture raw product intent as structured pre-canonical input:

- actors;
- domain events;
- commands;
- policies;
- external systems;
- constraints;
- vocabulary questions;
- open risks and assumptions.

This artifact should feed the existing SpecAuthor authoring flow and ontology
context resolution without creating canonical specs.

### 2. Candidate Spec Graph Contract

Status: implemented in proposal `0150`.

Define a full candidate graph artifact that can contain proposed specs, edges,
requirements, acceptance criteria, claims, ontology refs, and unresolved gaps.

The candidate graph must declare:

- `canonical_mutations_allowed: false`;
- source intent refs and digests;
- active ontology/domain/context frame;
- ontology layer refs and model applicability refs when available;
- generated node and edge provenance;
- materialization intent limited to review or branch preparation.

### 3. Pre-SIB And Coherence Metrics

Status: implemented in proposal `0151`.

Add a pre-implementation metric layer that scores whether the candidate graph is
ready for canonical review.

Initial signals:

- missing ontology/domain/context refs;
- unsupported strong claims;
- low-reliability decisions;
- orphan nodes;
- unresolved dependencies;
- contradictory requirements;
- duplicated or ambiguous terms;
- acceptance criteria coverage;
- implementation-readiness warnings.

The metrics are review and repair inputs, not product-quality guarantees.

### 4. Autonomous Candidate Repair Loop

Status: implemented in proposal `0152`.

Let the agent repair candidate graph state before human review:

```text
candidate graph
  -> validation reports
  -> repair plan
  -> revised candidate graph
  -> metric delta
```

The loop may update candidate artifacts, but it must not update canonical specs
or Ontology packages directly.

### 5. Graph Repository Service Contract

Status: Platform contract and report-only promotion request handoff are
implemented; SpecGraph materialized candidate spec previews are implemented in
proposal `0153`, and the final idea-to-spec promotion gate is implemented in
proposal `0154`.

Define the first service/CLI boundary over Git:

- `create_workspace`;
- `create_candidate_workspace`;
- `validate_candidate_graph`;
- `prepare_branch`;
- `create_commit`;
- `open_review`;
- `publish_read_model`.

The first implementation can be local and CLI-backed. Production deployments can
later replace the storage backend with a hosted Git provider, object storage,
queue-backed workers, or a workspace manager without changing the authority
model.

SpecGraph owns the candidate materialization preview before Platform creates a
branch. `0153` writes review-only YAML previews under
`runs/materialized_candidate_specs/` plus
`runs/candidate_spec_materialization_report.json`; Platform consumes the
reported paths through `graph-repository promotion-request` before any executor
step creates a branch, commit, or pull request.

`0154` adds `runs/idea_to_spec_promotion_gate.json` as the final read-only
handoff check. It aggregates pre-SIB metrics, repair-loop context requirements,
materialization readiness, and promotion paths so the autonomous idea-to-spec
flow has one explicit go/no-go surface before Platform promotion.

### 6. SpecSpace Review And Publish Surface

Status: partially implemented. SpecSpace now has separate workspace routes and
can show the Team Decision Log candidate graph, pre-SIB report, repair loop,
promotion gate, Platform promotion request, and Git Service execution report
without leaking SpecGraph bootstrap artifacts into the product workspace.

The next UI slice is a derived workflow lane over those artifacts, not another
raw JSON panel. It should show stage status and the next operator handoff across
the same read-only chain.

SpecSpace should show:

- active workspace and graph version;
- candidate graph preview;
- pre-SIB/coherence status;
- validation findings;
- repair loop history;
- branch/PR/review status;
- published read model status.

SpecSpace remains a consumer of the repository service contract. It should not
mount a writable checkout and commit files itself.

### 7. Active Idea-To-Spec Candidate Source

Status: implemented in proposal `0155` for the first Team Decision Log pilot.
The remaining work is to keep the source shape generic enough that Team
Decision Log stays data instead of leaking into system-level logic.

Public handoff artifacts can intentionally publish `no_active_candidate`
placeholders when no active source exists. The generic product workspace active
candidate target replaces those placeholders only when a validated active
candidate source exists and proves:

- `candidate_id` and product workspace identity are stable;
- source mode is `active_candidate`, not fixture/demo leakage;
- active ontology/domain/context frame is present;
- event-storming intake, candidate graph, pre-SIB report, repair-loop state,
  materialization report, and promotion gate refs are consistent;
- public artifacts contain sanitized refs, digests, statuses, and findings
  rather than raw prompt text, private operator notes, or local paths;
- promotion requests target `product_spec_workspace` and never
  `specgraph_bootstrap`.

This slice should remain review-only. It may prepare materialized candidate
spec previews and Git Service handoff reports, but it must not mutate canonical
SpecGraph specs or write ontology packages directly.

The implemented surface is:

- `tools/active_idea_to_spec_candidate_source.py`;
- `make product-workspace-active-candidate`;
- `runs/active_idea_to_spec_candidate.json`;
- static artifact publishing guardrails that preserve real handoff surfaces
  only when that active source is ready.

### 8. CLI Candidate Approval Flow

Status: contract proposed in proposal `0156`; first deterministic artifact
implemented in proposal `0157`.

The CLI and agent-mediated product workflow needs an explicit operator decision
between a review-ready candidate and any Git Service promotion attempt. The
agent may recommend the next transition, but it must not approve the candidate
on the user's behalf.

The proposed approval surface is:

- `runs/candidate_approval_decision.json`;
- public-safe refs and digests for the active candidate, promotion gate,
  pre-SIB/coherence report, repair-loop report, and materialization report;
- explicit decision states such as `approved`, `rejected`, `needs_context`, and
  `superseded`;
- authority metadata proving that approval does not create a branch, commit,
  pull request, merge, read model, canonical spec mutation, or Ontology write.

This keeps the states separate:

```text
agent recommends
  -> operator approves promotion request attempt
  -> Git Service executes controlled branch/commit/review steps
  -> repository review accepts or rejects canonical changes
  -> read model publishes only after merged review
```

The implemented `make candidate-approval-decision` target reads the active
candidate source and promotion gate, defaults to `needs_context`, and emits
`approved` only when the operator explicitly requests approval and all upstream
readiness checks pass. The artifact stays review-only and carries
`canonical_mutations_allowed: false`.

### 9. Git Service Post-Review And Read-Model Closure

Status: Platform has the local Git Service executor for `prepare-worktree`,
`commit-worktree`, and `open-review`, while `review-status` and
`publish-read-model` exist as separate Platform operations.

The next service slice should make post-review state explicit in the product
workspace handoff:

- record review status as a Git Service operation result;
- publish the read model only after a merged review status;
- emit public-safe report refs for both steps;
- keep SpecSpace read-only and inspect/acknowledge-only;
- keep bootstrap/internal deployment profiles separate from product workspace
  promotion profiles.

This is still a service boundary, not a SpecSpace write feature.

### 10. Generic User Idea Intake Source

Status: implemented in proposal `0158`.

The product UX now has a generic entry point where a user idea can become
structured intake data before candidate graph generation. The source artifact is
`user_idea_intake_source`; it captures:

- product workspace identity;
- product goal and excluded scope through root intent text/summary;
- actors and external systems;
- domain events and commands;
- policies, constraints, risks, and assumptions;
- vocabulary questions and context-completion questions;
- active ontology/domain/context hints;
- ontology layer and model applicability defaults.

The implemented surface is:

- `tools/user_idea_intake_source.py`;
- `make user-idea-intake-source`;
- `make generic-idea-intake`;
- `runs/idea_event_storming_seed.json`;
- the existing downstream `runs/idea_event_storming_intake.json`.

The deterministic chain is:

```text
user_idea_intake_source
  -> idea_event_storming_seed
  -> idea_event_storming_intake
```

Team Decision Log remains data. A new product idea can replace it at the intake
source boundary without adding product-specific scripts or Make targets.
Proposal `0158` intentionally stops before candidate spec graph authoring,
prompt-agent execution, Git Service calls, canonical spec mutation, or Ontology
writes.

### 11. Ontology-Bound Candidate Graph Seed

Status: implemented in proposal `0159`.

The candidate graph seed is now generated generically from approved
event-storming intake and the project-local SpecGraph core ontology IR.

This step makes Ontology foundational for the product idea-to-spec path:

- active ontology/domain/context refs are required;
- ontology layer refs are required;
- model applicability refs are required;
- generated structural nodes bind to core ontology classes such as `Spec`,
  `Node`, `Requirement`, `AcceptanceCriterion`, and `Constraint`;
- product-domain terms are emitted as ontology gaps rather than silently
  accepted into the ontology.

The implemented surface is:

- `tools/ontology_bound_candidate_graph_seed.py`;
- `make ontology-bound-candidate-graph-seed`;
- `runs/candidate_spec_graph_seed.json`;
- `make product-workspace-active-candidate`, which now generates the seed before
  building `runs/candidate_spec_graph.json`.

The deterministic chain is:

```text
user_idea_intake_source
  -> idea_event_storming_seed
  -> idea_event_storming_intake
  -> ontology_bound_candidate_graph_seed
  -> candidate_spec_graph
```

The downstream `candidate_spec_graph` builder blocks seeds whose
`source_generation.findings` require review. This prevents missing ontology
frame, missing ontology layer/applicability refs, or missing required core
ontology classes from passing into pre-SIB readiness.

### 12. Generic Active Idea-To-Spec Runner

Status: implemented in proposal `0160`.

The full active product workspace target now starts from generic user idea data,
not a prepared Team Decision Log seed.

The implemented surface is:

- `PRODUCT_WORKSPACE_IDEA_SOURCE`;
- generated `runs/idea_event_storming_seed.json` inside
  `make product-workspace-active-candidate`;
- public-safe `source_intake.workspace` metadata on
  `runs/idea_event_storming_intake.json`;
- a generic active candidate config fixture with artifact refs only;
- active candidate metadata derivation from the intake artifact.

The deterministic chain is now:

```text
user_idea_intake_source
  -> idea_event_storming_seed
  -> idea_event_storming_intake
  -> ontology_bound_candidate_graph_seed
  -> candidate_spec_graph
  -> pre-SIB/coherence report
  -> candidate_repair_loop_report
  -> candidate_spec_materialization_report
  -> idea_to_spec_promotion_gate
  -> active_idea_to_spec_candidate
```

Team Decision Log remains the default example workspace data for the product
pilot. A new product idea can replace it by passing a different
`PRODUCT_WORKSPACE_IDEA_SOURCE`, without adding a new tool, Make target, or
product-specific active candidate config. The old prepared seed path remains
available through `PRODUCT_WORKSPACE_INTAKE_SOURCE=<seed.json>`, but a prepared
seed without `source_intake.workspace` needs an explicit active candidate config
because the generic artifact-refs-only config has no product identity to derive.
In artifact-refs-only mode, governance fields use the standard active product
workspace defaults: `product_idea_to_spec`, `product_workspace`,
`product_spec_workspace`, and `workspace_owner_controlled`.

The runner may still emit `active_candidate_review_required` when pre-SIB,
repair-loop, ontology-gap, or promotion-gate checks require owner context. That
blocked state is the expected pre-SIB control behavior, not a runner failure.

### 13. Artifact-Derived Active Candidate Source Defaults

Status: implemented in proposal `0161`.

The active candidate source no longer requires a config fixture in the standard
generated flow. The builder now reads the standard artifact chain directly:

```text
runs/idea_event_storming_intake.json
  -> runs/candidate_spec_graph.json
  -> runs/pre_sib_coherence_report.json
  -> runs/candidate_repair_loop_report.json
  -> runs/candidate_spec_materialization_report.json
  -> runs/idea_to_spec_promotion_gate.json
  -> runs/active_idea_to_spec_candidate.json
```

`runs/active_idea_to_spec_candidate.json` records `config_source.required=false`
and a `source_derivation` block that shows whether identity came from
`intake.source_intake.workspace`, whether artifact paths came from defaults or
an explicit override, and which standard artifact refs were used.

Config remains supported for nonstandard artifact paths, tests, and legacy
prepared-seed compatibility. It is not part of the normal product
`product_idea_to_spec` happy path.

### 14. Generic User Idea Intake Session

Status: implemented in proposal `0162`.

The normal product-workspace runner now starts from a raw idea intake session
before it creates a prepared `user_idea_intake_source`.

The implemented surface is:

- `tools/user_idea_intake_session.py`;
- `make user-idea-intake-session`;
- `make generic-idea-intake-session`;
- `runs/user_idea_intake_session.json`;
- `runs/user_idea_intake_source.json` when the session is ready;
- `make product-workspace-active-candidate`, which runs the session step before
  the existing `user_idea_intake_source` builder in generated mode.

The deterministic chain is now:

```text
user_idea_raw_input
  -> user_idea_intake_session
  -> user_idea_intake_source
  -> idea_event_storming_seed
  -> idea_event_storming_intake
  -> ontology_bound_candidate_graph_seed
  -> candidate_spec_graph
  -> pre-SIB/coherence report
  -> candidate_repair_loop_report
  -> candidate_spec_materialization_report
  -> idea_to_spec_promotion_gate
  -> active_idea_to_spec_candidate
```

If the raw idea lacks ontology refs, ontology layer refs, domain refs, context
refs, model applicability refs, actors, domain events, commands, or constraints,
the session emits `needs_clarification` with public-safe
`clarification_questions` and does not write a prepared source artifact. This
keeps the first user-facing step generic while preventing under-specified ideas
from entering the candidate graph path as if they were ready.

Prepared `user_idea_intake_source` inputs remain supported for compatibility
and tests, but they are no longer the only normal entry point.

### 15. Idea-To-Spec Clarification Requests

Status: implemented in proposal `0163`.

The product-workspace flow now writes a unified clarification request artifact:

```text
runs/idea_to_spec_clarification_requests.json
```

It can be refreshed directly with:

```bash
make idea-to-spec-clarification-requests
```

The artifact turns scattered intake questions, pre-SIB findings, repair-loop
actions, candidate graph gaps, and ontology gap review groups into stable typed
requests. Each request carries an id, kind, severity, target artifact, target
ref, blocking source findings, suggested answer shape, and suggested actions.

This keeps the next user/agent step explicit:

```text
missing_context -> answer active ontology/domain/context frame
ontology_gap -> bind, alias, propose project-local term, reject, or defer
weak_claim -> accept downgrade, add evidence, narrow scope, or reject
missing_acceptance_criteria -> accept preview criterion or provide one
graph_repair -> accept preview edge, reject it, or propose another relation
```

The artifact remains review-only. It does not accept answers, write ontology
packages, mutate canonical specs, approve candidates, or create Git branches.
Proposal `0164` implements the answer validation surface.

### 16. Idea-To-Spec Clarification Answers

Status: implemented in proposal `0164`.

Clarification requests now have a typed answer validation surface:

```bash
make idea-to-spec-clarification-answers
```

The output is:

```text
runs/idea_to_spec_clarification_answers.json
```

The report validates an `idea_to_spec_clarification_answer_set` against the
request ids emitted by proposal `0163`. Each answer must reference an existing
request, use one of the request's `suggested_actions`, and declare authority
such as `operator_approved` or `owner_approved`.

Blocking requests are resolved only by accepted answers:

```text
accepted_for_candidate
accepted_for_review
```

`proposed`, `rejected`, and `deferred` answers remain visible records, but they
do not make the candidate ready for rerun. This keeps answer collection explicit
without silently mutating intake artifacts, candidate graphs, specs, or ontology
packages.

### 17. Idea-To-Spec Answer Rerun Input

Status: implemented in proposal `0165`.

Accepted clarification answers can now be converted into a deterministic rerun
input overlay:

```bash
make idea-to-spec-answer-rerun-input
```

The output is:

```text
runs/idea_to_spec_answer_rerun_input.json
```

The overlay maps accepted answers into explicit review-only hints:

```text
intake active-frame hints
event-storming hints
ontology term bindings, aliases, project-local terms, rejected terms, deferred terms
candidate acceptance criteria, graph edges, claim reviews
```

The tool consumes the validated `idea_to_spec_clarification_answers` report
from proposal `0164`. If that report is not ready, the rerun input remains
blocked and emits review findings instead of materializing hints. The artifact
does not apply answers, write ontology packages, mutate canonical specs, approve
candidates, or create Git branches.

### 18. Idea-To-Spec Rerun Preview

Status: implemented in proposal `0166`.

Accepted-answer overlays can now be previewed against the current intake and
candidate graph:

```bash
make idea-to-spec-rerun-preview
```

The output is:

```text
runs/idea_to_spec_rerun_preview.json
```

The preview shows:

```text
active-frame merge preview
event-storming hint preview
preview-resolved ontology gaps
still-unresolved ontology gaps
candidate review hints
```

This is still not an application step. Matching `bind_existing_term`, `alias`,
`propose_project_local_term`, `reject`, or `defer` answers can close an
ontology gap in preview state, but the tool does not accept ontology terms,
write ontology packages, mutate candidate graphs, approve candidates, or create
Git branches.

### 19. Idea-To-Spec Rerun Materialization

Status: implemented in proposal `0167`.

Ready rerun previews can now produce a materialized candidate graph preview:

```bash
make idea-to-spec-rerun-materialization
```

The output is:

```text
runs/idea_to_spec_rerun_materialization.json
```

The report contains:

```text
candidate graph preview
removed ontology gap ids
still-unresolved ontology gap ids
per-node ontology_gap_resolutions
review delta summary
```

The materialized candidate graph remains nested inside the report. The tool does
not rewrite `runs/candidate_spec_graph.json`, accept ontology terms, write
ontology packages, approve candidates, mutate canonical specs, or create Git
branches.

### 20. Product Ontology Gap Review Decisions

Status: implemented in proposal `0168`.

Accepted ontology-gap answers can now become typed product ontology review
decisions:

```bash
make product-ontology-gap-review-decisions
```

The output is:

```text
runs/product_ontology_gap_review_decisions.json
```

Supported decision types:

```text
bind_existing_term
alias_existing_term
propose_project_local_term
reject_non_domain_term
defer_requires_owner
```

The decision artifact is product-scoped review evidence for later rerun overlay
and candidate-quality surfaces. It does not import Ontology owner decisions,
accept ontology terms, write ontology packages, mutate candidate artifacts,
approve candidates, or create Git branches.

### 21. Ontology Decisions Into Rerun Overlay And Candidate Quality

Status: implemented in proposal `0169`.

Rerun input can now consume the typed product ontology decision artifact:

```bash
make idea-to-spec-answer-rerun-input \
  IDEA_TO_SPEC_ANSWER_RERUN_INPUT_ONTOLOGY_DECISIONS=runs/product_ontology_gap_review_decisions.json
```

When supplied, `product_ontology_gap_review_decisions` becomes the ontology
review source for rerun overlay hints. This prevents duplicate ontology hints
from raw clarification answers while preserving non-ontology answers for active
frame, event-storming, graph repair, and claim review overlays.

`idea_to_spec_rerun_preview` now emits
`rerun_preview.candidate_quality_preview`, reporting whether ontology gap
decisions resolve all, some, or none of the candidate ontology gaps. The signal
is still review-only and does not mutate candidate artifacts, accept ontology
terms, write Ontology packages, approve candidates, or create Git branches.

## Success Criteria

- A user can start with a product idea and receive a coherent candidate graph.
- The candidate graph reaches configured pre-SIB/coherence thresholds without a
  human reviewing every generated node.
- Canonical graph writes happen only through branch/commit/review boundaries.
- SpecSpace can show both the latest canonical graph version and candidate
  graph state without confusing them.
- Published read models remain reproducible from a Git commit and validated
  artifact bundle.
- The Team Decision Log pilot appears as a product workspace, not as part of the
  SpecGraph bootstrap workspace.
- A new product idea can replace Team Decision Log as data without adding
  product-specific scripts, Make targets, or active-candidate config fixtures.
- A raw product idea can produce a reviewable intake session that either writes
  a prepared intake source or asks concrete clarification questions.
- Blocking intake, ontology, pre-SIB, and repair issues become stable
  clarification request ids that a future answer contract and SpecSpace product
  workspace lane can reference.
- User or agent answers can be validated against clarification request ids
  without applying candidate or ontology mutations.
- Accepted clarification answers can be transformed into a review-only rerun
  input overlay without applying source, candidate, ontology, spec, or Git
  mutations.
- Accepted-answer overlays can be previewed against current intake and
  candidate graph state, including ontology gap resolution effects, without
  applying mutations.
- Ready rerun previews can materialize a review-only candidate graph preview
  and explicit delta without rewriting candidate source artifacts or granting
  promotion authority.

## Current Execution Order

The active stack after production workspace isolation is:

1. Controlled candidate rerun source selection from a ready
   `idea_to_spec_rerun_materialization` report emitted by proposal `0167`.
2. CLI or agent conversation wrapper that fills `user_idea_raw_input` from a
   real operator interview and can consume clarification requests.
3. Prompt-side enrichment that can propose richer product-domain graph nodes
   while preserving ontology gaps for unaccepted terms.
4. SpecSpace workflow lane refinement for active candidate blockers, repair
   suggestions, and approval state.
5. Platform Git Service post-review status and read-model publication
   orchestration.
6. Ontology applicability and layer-aware review refinement as compiler support
   matures.

## Related Documents

- `docs/product_workspace_stable_mode_guide.md`
- `docs/product_workspace_initialization_viewer_contract.md`
- `docs/proposals/0062_proto_graph_recursive_refinement.md`
- `docs/proposals/0146_specauthor_prompt_side_authoring_flow.md`
- `docs/ontology_spec_validation_roadmap.md`
