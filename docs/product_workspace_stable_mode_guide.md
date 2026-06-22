# Product Workspace Stable Mode Guide

This guide describes the first stable client/project mode for running
SpecGraph against an external product workspace.

## Purpose

Use `product_workspace` when SpecGraph should develop a user's product graph
instead of improving SpecGraph itself.

The profile keeps the SpecGraph engine and core policies locked by default
while allowing project-local work:

- intent capture;
- project specs and proposals;
- trace and evidence surfaces;
- implementation work;
- project-local review feedback;
- project artifact publishing.

## Minimal Project Config

```yaml
artifact_kind: specgraph_project_config
schema_version: 1
project_id: swiftui-calculator
display_name: SwiftUI Calculator
governance_profile: product_workspace

engine:
  version_policy: pinned
  mutation_policy: locked
  allowed_core_updates: package_upgrade_only

workspace:
  specs_root: specs/
  proposals_root: docs/proposals/
  runs_root: runs/
  publish_root: projects/swiftui-calculator/

supervisor:
  allow_project_spec_refinement: true
  allow_project_proposals: true
  allow_project_retrospectives: true
  allow_core_policy_mutation: false
  allow_core_tooling_mutation: false
  allow_self_evolution_proposals: false
```

## Team Decision Log Pilot Config

The first public `product_idea_to_spec` pilot should use a project-local
workspace similar to:

```yaml
artifact_kind: specgraph_project_config
schema_version: 1
project_id: team-decision-log
display_name: Team Decision Log
governance_profile: product_workspace

engine:
  version_policy: pinned
  mutation_policy: locked
  allowed_core_updates: package_upgrade_only

workspace:
  specs_root: specs/
  proposals_root: docs/proposals/
  runs_root: runs/
  publish_root: projects/team-decision-log/

idea_to_spec:
  workflow_lane: product_idea_to_spec
  canonical_public_route: /team-decision-log
  source_domain: team_decision_management
  initial_scope:
    - decisions
    - considered_options
    - rationale
    - evidence
    - owners
    - review_triggers
    - supersession_and_conflicts

supervisor:
  allow_project_spec_refinement: true
  allow_project_proposals: true
  allow_project_retrospectives: true
  allow_core_policy_mutation: false
  allow_core_tooling_mutation: false
  allow_self_evolution_proposals: false
```

This config is a planning target, not a requirement to create a product repo
inside the SpecGraph bootstrap checkout. The Team Decision Log artifacts should
be published as product workspace artifacts and consumed by SpecSpace through a
workspace route such as `specgraph.space/team-decision-log`.

The deterministic local pilot chain is:

```bash
make team-decision-log-active-candidate
```

It builds event-storming intake, candidate graph, pre-SIB report, repair-loop
preview, materialization report, promotion gate, and
`runs/active_idea_to_spec_candidate.json` without canonical spec mutation.

## Operational Rules

- Do not fork SpecGraph just to create a new product workspace.
- Keep engine/tooling updates explicit and upstream.
- Keep project graph artifacts under project-owned roots.
- Treat `tools/`, `tests/`, `.github/`, `AGENTS.md`, and `CONSTITUTION.md`
  as locked core roots in product mode.
- Do not route customer project review feedback directly into SpecGraph core.
- Export upstream SpecGraph issues or proposals only by explicit human action.
- Treat Git as the canonical version substrate, but put production writes behind
  a managed graph repository boundary instead of letting UI code mutate a local
  checkout directly.
- Keep public product pilots, including Team Decision Log, in
  `product_workspace` mode with `product_spec_workspace` promotion targets.
  Do not use SpecGraph bootstrap repository roles for product pilot writes.

## Expected Supervisor Behavior

In `product_workspace`:

- `project_environment` exposes `core_locked=true`.
- `graph_next_moves` filters SpecGraph-core/self-evolution moves into
  `blocked_moves`.
- explicit supervisor targets against SpecGraph core nodes fail before executor
  launch.
- blocked moves use `blocked_by_governance_profile`.

## SpecSpace / Viewer Expectations

SpecSpace should read `runs/project_environment.json` and
`runs/graph_next_moves.json` rather than inferring mode from URLs or repository
names.

The important viewer-facing fields are:

- `viewer_projection.environment_badge`;
- `viewer_projection.enforcement_summary`;
- `graph_next_moves.source_facts.project_environment`;
- `graph_next_moves.blocked_moves[].governance_block`.

## Graph Storage And Versioning Direction

Product workspaces should eventually use a Git-backed graph repository service:

```text
candidate graph -> validation gates -> branch/commit -> review/merge -> read model
```

The repository service owns candidate workspace allocation, validation,
branch/commit creation, review policy, and artifact publication. SpecSpace
should consume the published read model and repository status rather than
writing directly into `specs/` or `runs/`.

The detailed roadmap is documented in
[`product_workspace_graph_versioning_roadmap.md`](product_workspace_graph_versioning_roadmap.md).

## Smoke Scenario

A minimal SwiftUI calculator workspace should be able to load
`governance_profile: product_workspace`, build project environment surfaces, and
reject ordinary supervisor refinement against bootstrap `SG-SPEC-*` core
targets before the executor starts.
