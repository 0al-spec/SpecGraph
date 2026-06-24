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
available through `PRODUCT_WORKSPACE_INTAKE_SOURCE=<seed.json>`.

The runner may still emit `active_candidate_review_required` when pre-SIB,
repair-loop, ontology-gap, or promotion-gate checks require owner context. That
blocked state is the expected pre-SIB control behavior, not a runner failure.

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
  product-specific scripts or Make targets.

## Current Execution Order

The active stack after production workspace isolation is:

1. Prompt-side enrichment that can propose richer product-domain graph nodes
   while preserving ontology gaps for unaccepted terms.
2. SpecSpace workflow lane refinement for active candidate blockers, repair
   suggestions, and approval state.
3. Platform Git Service post-review status and read-model publication
   orchestration.
4. Ontology applicability and layer-aware review refinement as compiler support
   matures.

## Related Documents

- `docs/product_workspace_stable_mode_guide.md`
- `docs/product_workspace_initialization_viewer_contract.md`
- `docs/proposals/0062_proto_graph_recursive_refinement.md`
- `docs/proposals/0146_specauthor_prompt_side_authoring_flow.md`
- `docs/ontology_spec_validation_roadmap.md`
