# Multi-Service SpecGraph Factory Architecture

## Status

Draft proposal

## Source Material

This proposal captures the operator discussion that reframed standalone
SpecGraph deployment as a broader cybernetic AI software factory architecture.

The discussion identified three emerging services:

- `SpecPM` as the future storage, registry, and package substrate for
  specifications, adapters, protocols, and reusable boundary contracts.
- `SpecGraph` as the graph, supervisor, governance, and control core.
- `ContextBuilder` / `SpecSpace` as the graph browser, operator cockpit, and
  GUI surface for human interaction with the factory.

The discussion also clarified that human input should not mean manual approval
for every small step. The intended operating model is closer to
human-on-the-loop control: the human supplies intents, constraints, corrections,
priorities, and explicit authority escalation while the agentic factory performs
bounded autonomous work.

## Context

SpecGraph already has many factory pieces:

- conversation and exploration surfaces for raw intent;
- proposal and pre-spec layers for reviewable planning;
- canonical spec nodes and graph overlays;
- supervisor-driven refinement and split/materialization mechanics;
- implementation-work and spec-to-code trace surfaces;
- metrics, evidence, review-feedback, and graph-dashboard artifacts;
- SpecPM export, handoff, materialization, import-preview, and public-registry
  observation surfaces;
- ContextBuilder viewer surfaces that can render dashboards, backlogs,
  proposals, metrics, evidence, and import/export lifecycle state.

These pieces currently operate through local CLI runs, GitHub PR review, and
viewer-side read-only inspection. That is enough for bootstrap, but it does not
yet define how SpecGraph should run as a stable standalone factory.

The missing concept is a service-level operating model:

```text
Human / Operator
  -> ContextBuilder / SpecSpace
  -> SpecGraph
  -> SpecPM
  -> implementation targets
  -> runtime evidence
  -> SpecGraph
```

## Problem

Without a multi-service architecture, several boundaries remain ambiguous:

- whether ContextBuilder is only a viewer or also an operator surface;
- whether SpecPM is only a sibling repository or a registry/storage substrate;
- whether SpecGraph is a CLI tool, a supervisor, or the factory control plane;
- where human input enters the system;
- which actions can be autonomous and which require explicit authority;
- how standalone/pre-production deployment differs from local development;
- how services exchange state without hidden filesystem coupling;
- how operator actions, PRs, approvals, and runtime evidence are audited.

If these boundaries remain implicit, the system can drift toward one of two
bad shapes:

- an unsafe autonomous loop that silently mutates canonical graph state; or
- a manually driven toolchain that cannot become the intended AI factory.

SpecGraph needs an explicit architecture where services are separated by data
ownership and authority, not only by repository names.

## Goals

- Define SpecGraph factory as a multi-service system.
- Assign clear roles to `SpecPM`, `SpecGraph`, and `SpecSpace`.
- Treat human input as operator control signals rather than only manual gates.
- Preserve autonomous observation and bounded autonomous work.
- Require explicit authority escalation for canonical, destructive, external,
  or production-impacting changes.
- Define service handoff artifacts instead of hidden cross-service filesystem
  mutation.
- Make pre-production deployment a profile of the factory architecture, not a
  standalone Docker-only concern.
- Prepare future specs for operator actions, supervisor worker isolation,
  registry-backed package flows, and ContextBuilder action surfaces.

## Non-Goals

- Implementing Docker, VM, or server deployment in this proposal.
- Replacing GitHub PR review immediately.
- Granting the supervisor unconditional merge or production-deploy authority.
- Making ContextBuilder own graph validity or supervisor policy.
- Making SpecPM own supervisor decisions.
- Defining a complete network API for every service.
- Requiring all services to be separate processes during local development.
- Removing the existing CLI/Makefile workflow.

## Core Proposal

SpecGraph should define a **multi-service factory architecture** with three
first-class service roles:

```text
SpecPM
  package / registry / reusable contract substrate

SpecGraph
  graph / supervisor / policy / control core

ContextBuilder / SpecSpace
  operator cockpit / graph browser / human input surface
```

The same architecture should support local development, pre-production
deployment, and later hosted operation. The difference between those modes is
how services are packaged, isolated, scheduled, and authorized.

## Service Roles

### 1. SpecPM: Specification Package Registry

SpecPM owns packaged specification distribution.

It should be responsible for:

- storing reusable specification packages;
- versioning adapters, protocols, and boundary specs;
- exposing registry-visible package versions;
- supporting package capabilities and discovery;
- receiving SpecGraph handoff bundles;
- materializing packages into a registry or package workspace;
- exposing import/export contracts without making graph decisions.

SpecPM is not the supervisor. It must not decide graph next moves, mutate
canonical SpecGraph state, or interpret product intent as policy.

Useful analogy:

```text
npm / crates.io
+ schema registry
+ specification artifact store
+ package boundary contract host
```

### 2. SpecGraph: Cybernetic Control Core

SpecGraph owns graph semantics and factory control.

It should be responsible for:

- capturing and structuring intents;
- maintaining the canonical specification graph;
- producing exploration, proposal, trace, evidence, metrics, and dashboard
  surfaces;
- choosing or recommending next moves;
- running bounded supervisor actions;
- enforcing authority and review policy;
- opening implementation or specification PRs;
- observing external consumers and package registries;
- integrating runtime feedback back into graph state.

SpecGraph may prepare changes, but canonical mutation must follow the active
authority policy.

### 3. ContextBuilder / SpecSpace: Operator Cockpit

ContextBuilder, evolving toward SpecSpace, owns human interaction and visual
operation.

It should be responsible for:

- browsing graph state and derived surfaces;
- rendering dashboards, metrics, backlog, trace, evidence, and proposal state;
- capturing operator intents and corrections;
- showing next moves, risk, authority state, and required review;
- starting bounded actions only through explicit operator actions;
- displaying PRs, gates, run results, and audit trails;
- keeping UI affordances aligned with SpecGraph contracts.

SpecSpace should not be the source of graph truth. It submits operator actions
to SpecGraph and renders SpecGraph-derived state.

## Factory Control Loop

The intended high-level loop is:

```text
operator input
  -> intent capture
  -> exploration / assumption shaping
  -> proposal pressure
  -> canonical specs
  -> implementation work
  -> PR / tests / review
  -> runtime evidence and metrics
  -> graph update
  -> next operator-visible state
```

This is a cybernetic loop:

- goal signal: operator intent, priority, constraint, or correction;
- state observation: graph, metrics, evidence, backlog, PR state;
- policy constraints: authority levels, review gates, risk rules;
- bounded action: supervisor run, proposal emission, package handoff, PR;
- feedback: validation, review comments, tests, runtime telemetry;
- correction: graph refinement, proposal change, implementation follow-up.

## Human Input Model

Human input should be first-class and typed.

An operator input is not just a chat message. It is a control signal with scope
and authority.

Candidate shape:

```yaml
operator_input:
  input_id: op-input-2026-05-13-0001
  source: specspace_chat
  kind: intent | correction | priority | constraint | approval_policy | stop_signal
  target_scope: product | graph_subtree | proposal | spec_node | runtime
  authority_level: advisory | draft_allowed | pr_allowed | merge_allowed
  note: "Build a SwiftUI calculator for iOS and macOS."
  created_at: "2026-05-13T00:00:00Z"
```

The operator may remain on-the-loop for normal bounded work. Explicit
human-in-the-loop approval is required only when the active authority policy
demands escalation.

## Authority Levels

The factory should distinguish these authority levels:

| Level | Meaning | Examples |
| --- | --- | --- |
| `observe` | Read, index, summarize, diagnose. | Build dashboard, metrics, backlog, import preview. |
| `plan` | Create draft pressure, proposals, or action candidates. | Emit proposal, split suggestion, implementation plan. |
| `draft_mutate` | Mutate non-canonical or isolated draft state. | Worktree diff, draft bundle, preview artifact. |
| `pr_mutate` | Prepare canonical change only as a PR. | Spec refinement branch, tool/test change branch. |
| `merge` | Land canonical change. | Merge PR after review policy. |
| `external_publish` | Publish or update outside SpecGraph. | SpecPM package publish, production deploy. |

Default pre-production policy:

- observation may run automatically;
- planning may run automatically with bounded scope;
- draft mutation may run in isolated worktrees;
- PR mutation may require explicit operator command;
- merge requires human approval unless a later policy explicitly grants it;
- external publish requires explicit approval.

## Service Handoff Artifacts

Services should exchange explicit artifacts and API payloads rather than relying
on hidden shared-state mutation.

Initial handoff families:

```text
operator_action
  SpecSpace -> SpecGraph

factory_run
  SpecGraph internal run/audit record

spec_package_handoff
  SpecGraph -> SpecPM

specpm_import_preview
  SpecGraph observing SpecPM-bound bundles

registry_observation
  SpecGraph observing SpecPM public/static registry

implementation_work
  SpecGraph -> implementation agents / PR workflow

runtime_evidence
  implementation/runtime -> SpecGraph
```

### Operator Action

Candidate minimal shape:

```yaml
operator_action:
  artifact_kind: operator_action
  schema_version: 1
  action_id: op-action-2026-05-13-0001
  source_service: specspace
  target_service: specgraph
  kind: submit_intent | run_supervisor | approve_proposal | reject_proposal | request_export | stop_run
  target:
    spec_id: SG-SPEC-0058
  authority_level: pr_allowed
  operator_note: "Run one bounded supervisor refinement."
  created_at: "2026-05-13T00:00:00Z"
```

The response should be a factory run or refusal record, not an implicit mutation.

### Factory Run

Candidate minimal shape:

```yaml
factory_run:
  artifact_kind: factory_run
  schema_version: 1
  run_id: factory-run-2026-05-13-0001
  requested_by_action: op-action-2026-05-13-0001
  service: specgraph
  mode: supervisor_worker
  authority_level: pr_allowed
  completion_status: progressed | failed | blocked
  produced_artifacts: []
  produced_pr: 301
  next_required_human_action: review_pr
```

## Deployment Profiles

The architecture should support multiple deployment profiles.

### Local Development

Services may run from local repositories:

- SpecGraph CLI and Makefile shortcuts;
- ContextBuilder dev server;
- SpecPM local checkout or registry dev server.

This mode optimizes for iteration speed.

### Pre-Production Standalone

Services should be isolated by role:

```text
specgraph-artifact-builder
  automatic read/derive refresh

contextbuilder-specspace
  read-only operator cockpit plus action submission

specgraph-supervisor-worker
  isolated bounded mutation worker

specpm-registry
  package registry or static index
```

This mode optimizes for reproducibility, auditability, and authority control.

### Hosted Factory

Future hosted mode may add:

- authenticated operator accounts;
- persistent operator action log;
- scheduled artifact refresh;
- queue-based supervisor workers;
- package registry publishing;
- product/runtime telemetry ingestion;
- organization-level policy profiles.

Hosted mode is a downstream architecture and should not be assumed by the first
implementation.

## Pre-Production Isolation Rules

Pre-production deployment should enforce:

- ContextBuilder/SpecSpace reads graph artifacts and submits operator actions;
- artifact-builder can refresh `runs/*.json` but cannot commit or merge;
- supervisor-worker runs one bounded action per job;
- supervisor-worker writes to isolated worktrees/branches;
- PR creation is allowed only when action authority permits it;
- merge is not automatic by default;
- external publish is not automatic by default;
- secrets for GitHub, model providers, and registries are scoped per worker;
- generated artifacts have retention policy and explicit promotion rules.

## Relation to Existing Artifacts

Existing artifacts already map into the architecture:

| Existing surface | Service role |
| --- | --- |
| `runs/graph_dashboard.json` | SpecGraph observation, SpecSpace rendering |
| `runs/graph_next_moves.json` | SpecGraph planning, SpecSpace guidance |
| `runs/exploration_preview.json` | SpecGraph exploration, SpecSpace preview |
| `runs/specpm_export_preview.json` | SpecGraph package planning |
| `runs/specpm_handoff_packets.json` | SpecGraph -> SpecPM handoff |
| `runs/specpm_import_preview.json` | SpecGraph observing SpecPM-bound bundles |
| `runs/specpm_public_registry_index.json` | SpecGraph registry observation |
| `runs/implementation_work_index.json` | SpecGraph implementation layer |
| `runs/review_feedback_index.json` | SpecGraph feedback learning |

The missing first-class artifacts are operator actions and factory runs.

## Viewer / SpecSpace Implications

ContextBuilder should evolve from read-only viewer toward controlled operator
surface without becoming the graph authority.

Future UI affordances should be backed by SpecGraph contracts:

- submit raw intent;
- build exploration preview;
- request proposal generation;
- run one bounded supervisor action;
- approve/reject proposal;
- request package export or import preview;
- inspect factory run audit;
- inspect required human action;
- stop or defer an autonomous queue.

The UI should show authority state before starting any action.

Example:

```text
Next move: SG-SPEC-0058
Gap: attach_trace_contract
Suggested action: run_supervisor
Authority required: pr_allowed

[Explain] [Run one bounded PR] [Defer] [Stop this line]
```

## SpecPM Implications

SpecPM should be treated as the package substrate, not as a passive folder.

Downstream work should clarify:

- package identity lifecycle;
- package version authority;
- public/static registry authority;
- package import/export review boundaries;
- package adoption evidence back into SpecGraph;
- whether metric packs, protocols, adapters, and boundary specs share one
  package model.

## Safety Model

The architecture should prevent silent autonomous mutation.

Required safety properties:

- every mutating action has an operator action or policy-granted authority;
- every supervisor worker run has bounded scope;
- every canonical graph change is reviewable;
- every external publish is explicitly authorized;
- every service handoff is inspectable;
- every refusal or blocked run surfaces a next human action or accepted risk.

This still allows high autonomy. The factory can observe, plan, draft, validate,
open PRs, and suggest next actions continuously. It cannot silently cross
authority boundaries.

## Materialization Path

This proposal should materialize into several smaller specs rather than one
large implementation:

1. `Factory Service Roles`
   - Define SpecPM, SpecGraph, and SpecSpace role boundaries.
2. `Operator Action Protocol`
   - Define typed human/operator inputs and action authority.
3. `Factory Run Audit Artifact`
   - Define durable records for autonomous and human-triggered factory runs.
4. `Supervisor Worker Isolation`
   - Define bounded worker execution, worktree/branch behavior, secrets, and
     one-action lifecycle.
5. `Pre-Production Deployment Profile`
   - Define Docker/VM/server profile over existing service roles.
6. `SpecSpace Action Surface Contract`
   - Define viewer/operator buttons, read-only vs mutating states, and
     authority display.
7. `SpecPM Package Substrate Boundary`
   - Define package registry/storage responsibilities and handoff surfaces.

## Open Questions

- Should `operator_actions/` be a tracked canonical directory, a run artifact,
  or an external audit log?
- Should chat-originated operator input be stored before or after exploration
  reduction?
- Which authority levels can be granted by policy without per-action approval?
- Should PR creation remain a supervisor responsibility or move to a separate
  factory worker?
- How should SpecGraph represent multiple implementation target repositories?
- How should a standalone instance authenticate local vs remote operators?
- Which artifacts are retained as evidence and which remain local ephemeral
  runtime state?

## Acceptance Criteria

- The three service roles are explicit and non-overlapping.
- Human input is modeled as typed operator control, not only manual PR review.
- Autonomous observation and planning remain allowed.
- Canonical mutation, merge, and external publish authority are separated.
- Cross-service writes require explicit handoff artifacts or action protocols.
- Pre-production deploy is framed as a profile of the architecture.
- Follow-up specs can be materialized without conflating viewer, registry, and
  supervisor responsibilities.
