# Product Workspace Governance Profile

## Status

Implemented

## Source Material

This proposal captures the operator request to deliver SpecGraph as a stable
runtime for external projects rather than always running it in self-hosted
bootstrap mode.

Source draft:

- `docs/archive/proposal_sources/0052_product_workspace_governance_profile.md`

## Context

SpecGraph is currently grown through a self-hosted workflow:

```text
SpecGraph specs
  -> supervisor runs
  -> proposals
  -> tooling/policy improvements
  -> more SpecGraph specs
```

That loop is useful while bootstrapping SpecGraph itself. It lets review
feedback, run failures, metric drift, and graph diagnostics improve the
supervisor, policies, validators, and viewer surfaces.

External product use is different. A customer or another project should be able
to use SpecGraph to develop their own software without accidentally granting the
supervisor authority to evolve SpecGraph core.

## Problem

The repository currently conflates two concerns:

```text
SpecGraph engine/tooling
  supervisor, policies, validators, artifact builders

Project graph workspace
  specs, proposals, runs, deploy target, project configuration
```

For SpecGraph's own bootstrap, that coupling is acceptable. For customer
deployments, it is unsafe and confusing:

- a product graph could inherit self-evolution behavior meant only for
  SpecGraph bootstrap;
- review feedback about customer product specs could be misclassified as
  feedback about SpecGraph core;
- supervisor "next moves" could steer work toward core runtime/tooling
  improvements instead of the customer's product;
- deployments for multiple projects need separate graph state, artifact
  storage, secrets, and viewer data sources.

The missing contract is a governance profile that explicitly locks SpecGraph
core and scopes supervisor authority to the product workspace.

## Goals

- Define a **Product Workspace Governance Profile** for external/customer
  projects.
- Separate stable SpecGraph engine authority from project graph authority.
- Disable SpecGraph core self-evolution in product workspaces.
- Preserve project-level reflection, diagnostics, evidence, implementation
  work, backlog, dashboard, and next-move surfaces.
- Make the active governance profile visible to operators and viewers.
- Support multi-project deployment without requiring forks for every project.

## Non-Goals

- Removing self-hosted bootstrap mode from SpecGraph development.
- Implementing the full project workspace runtime in this proposal.
- Finalizing Docker, server, or static hosting topology.
- Defining every multi-tenant auth, billing, or account-management rule.
- Preventing project-level retrospectives or quality diagnostics.
- Allowing product workspaces to mutate SpecGraph core policies or tooling.

## Core Proposal

SpecGraph should support at least two governance profiles:

```text
self_hosted_bootstrap
  SpecGraph is allowed to improve its own graph, policies, and runtime through
  proposal-first governance and human review.

product_workspace
  SpecGraph engine is locked; supervisor authority is scoped to the customer's
  project graph.
```

The profile is not just UI metadata. It is an authority boundary that affects
which mutations, proposals, next moves, and diagnostics are allowed.

## Product Workspace Boundary

Product workspace mode should allow:

- root intent capture for the project;
- project spec creation and refinement;
- project-scoped proposals;
- trace, evidence, implementation work, backlog, dashboard, and activity
  surfaces;
- project-local retrospectives and review feedback analysis;
- static artifact publishing for the project workspace;
- SpecSpace/ContextBuilder data-source binding to the project artifact root.

Product workspace mode should prohibit:

- modifying `tools/` as part of ordinary product graph development;
- modifying `tests/` for SpecGraph core as part of ordinary product graph
  development;
- mutating core policy artifacts such as supervisor, evidence, metric, proposal,
  or deploy policies;
- creating proposals whose subject is "improve SpecGraph core";
- running self-evolution marathons over SpecGraph bootstrap `SG-SPEC-*` nodes;
- converting customer review feedback into SpecGraph core runtime work unless a
  human explicitly exports it as an upstream SpecGraph issue/proposal.

## Candidate Project Configuration

Runtime implementation may introduce a project manifest such as:

```yaml
artifact_kind: specgraph_project_config
schema_version: 1
project_id: swiftui-calculator
governance_profile: product_workspace

engine:
  version: "pinned"
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

The exact file name is intentionally open. Candidate names:

- `specgraph.project.yaml`;
- `.specgraph/project.yaml`;
- `specgraph.workspace.yaml`.

## Engine And Workspace Layout

A product deployment should be able to run with a read-only engine and a
writable workspace:

```text
/opt/specgraph-engine       read-only
/workspace/specs            read-write
/workspace/docs/proposals   read-write
/workspace/runs             read-write
/workspace/config           read-write
```

This keeps engine upgrades explicit and project graph changes isolated.

Forking the SpecGraph repository should be optional. Forks are appropriate for
changing SpecGraph itself. Product use should prefer separate project
workspaces.

## Multi-Project Artifact Deployment

Published artifacts should be project-scoped:

```text
https://specgraph.tech/projects/specgraph/specs/
https://specgraph.tech/projects/specgraph/runs/

https://specgraph.tech/projects/swiftui-calculator/specs/
https://specgraph.tech/projects/swiftui-calculator/runs/
```

Each project should have separate:

- project id;
- workspace root;
- spec/proposal/run storage;
- publish target;
- deploy credentials;
- SpecSpace data source.

## Runtime Guardrails

Runtime implementation should enforce the profile at several layers:

- allowed path checks reject core mutations in product workspace mode;
- proposal classification rejects self-evolution proposal targets unless
  explicitly exported upstream;
- next-move generation filters out SpecGraph-core work for product workspaces;
- review-feedback classification records customer-project feedback separately
  from SpecGraph-core feedback;
- publish bundle metadata includes `project_id` and `governance_profile`;
- SpecSpace displays the active profile and whether core is locked.

## Viewer Contract

SpecSpace/ContextBuilder should be able to render a compact environment banner:

```text
Mode: Product Workspace
Project: swiftui-calculator
Core: locked
Self-evolution: disabled
Project graph: writable
```

The viewer should not infer this from URL shape or repository name. It should
read it from a derived artifact or manifest field.

## Relationship To Existing Architecture

This proposal extends the multi-service factory architecture:

```text
SpecPM
  stores and exchanges spec packages

SpecGraph
  owns graph governance and supervisor execution

SpecSpace / ContextBuilder
  visualizes graph state and exposes operator controls
```

`product_workspace` mode defines how those services behave when the graph is a
customer product graph rather than SpecGraph's own bootstrap graph.

It also complements:

- Supervisor Prompt Overlay Profiles, which tune project behavior without
  replacing hard invariants;
- Evidence-Backed Build Protocol, which turns mature specs into implementation
  work;
- Multi-Service SpecGraph Factory Architecture, which defines service
  boundaries.

## Runtime Scope

The first runtime slice materializes the profile as a read-only project
environment surface:

- `specgraph.project.yaml`;
- `tools/project_environment_policy.json`;
- `runs/project_environment.json`;
- `make project-environment`;
- `docs/project_environment_viewer_contract.md`.

This establishes observable profile identity and viewer contract. Deeper
enforcement hooks for next-move filtering, allowed path checks, and upstream
export flows remain future runtime follow-ups.

## Acceptance Criteria

- The proposal distinguishes `self_hosted_bootstrap` from `product_workspace`.
- Product workspace mode locks SpecGraph core tooling and policy by default.
- Product workspace mode still permits project-level specs, proposals,
  diagnostics, evidence, implementation work, and retrospectives.
- Multi-project deployment requires separate project identity, workspace roots,
  artifact roots, and viewer data sources.
- Runtime follow-up is explicitly proposal-first and starts with a read-only
  environment artifact before deeper enforcement hooks.
