# Product Workspace Stable Mode Enforcement

## Status

Draft proposal

## Source Material

This proposal captures the operator decision to turn product workspace identity
from a visible environment surface into an enforceable supervisor mode.

Source draft:

- `docs/archive/proposal_sources/0053_product_workspace_stable_mode_enforcement.md`

## Context

Product Workspace Governance Profile introduced the first explicit distinction
between:

```text
self_hosted_bootstrap
  SpecGraph develops SpecGraph through proposal-first self-evolution.

product_workspace
  SpecGraph serves an external project with SpecGraph core locked by default.
```

The first runtime slice made that distinction observable through
`project_environment`. That is necessary but incomplete: a badge can warn an
operator, but it does not by itself prevent the supervisor from selecting or
executing self-evolution work in the wrong workspace.

## Problem

SpecGraph currently has enough surfaces to describe a product workspace, but
not enough enforcement to make the mode operationally safe.

Without enforcement:

- `make next-move` may still recommend SpecGraph-core work in a product
  workspace;
- targeted supervisor runs may attempt to mutate locked roots;
- review feedback from a customer project can be routed into SpecGraph core
  improvement loops;
- the viewer can show `Core: locked` while runtime behavior remains advisory;
- a new project instance can accidentally inherit bootstrap marathons meant
  for SpecGraph itself.

The missing capability is a stable-mode enforcement layer that applies the
active governance profile before move selection, target execution, path writes,
and operator diagnostics.

## Goals

- Make `product_workspace` an enforced supervisor mode, not only a viewer
  surface.
- Keep `self_hosted_bootstrap` available for SpecGraph core development.
- Filter next moves by governance profile before presenting them as
  recommended operator actions.
- Reject or block targets that would mutate locked SpecGraph core surfaces in
  product mode.
- Publish readable diagnostics explaining which profile blocked a move and
  what the next allowed action is.
- Preserve project-local retrospectives, quality feedback, evidence,
  implementation work, dashboard, and activity surfaces.
- Provide stable client-instance guidance for new projects that should not
  fork SpecGraph just to use it.

## Non-Goals

- Building a hosted multi-tenant service.
- Defining billing, account management, or remote auth.
- Removing self-hosted bootstrap behavior from the SpecGraph repository.
- Replacing GitHub PR review or human merge authority.
- Allowing product workspaces to mutate SpecGraph core policies, tools, or
  validators by default.
- Automatically exporting customer feedback upstream into SpecGraph core.

## Core Proposal

SpecGraph should treat the active governance profile as a runtime authority
input.

The enforcement pipeline should be:

```text
project config
  -> project_environment
  -> governance policy
  -> next-move eligibility
  -> target/path authorization
  -> supervisor run result
  -> viewer/operator diagnostics
```

In `self_hosted_bootstrap`, SpecGraph may continue to improve its own
specifications, policies, and tooling through proposal-first governance.

In `product_workspace`, the supervisor should default to:

- allowed project graph roots;
- project-scoped specs and proposals;
- project-local implementation work;
- project-local feedback and retrospectives;
- read-only consumption of SpecGraph engine policy.

The supervisor should not silently choose or execute:

- core policy mutation;
- core tooling mutation;
- SpecGraph self-evolution proposal creation;
- bootstrap `SG-SPEC-*` marathons for the engine graph;
- review-feedback learning loops that change SpecGraph core instead of the
  product graph.

## Enforcement Slices

### 1. Policy Contract Tightening

Extend project environment policy so each governance profile exposes a stable,
machine-readable enforcement contract:

- allowed mutation roots;
- forbidden mutation roots;
- allowed target domains;
- forbidden target domains;
- self-evolution allowance;
- review-feedback routing mode;
- default next-move behavior.

### 2. Next-Move Filtering

`graph_next_moves` should evaluate candidate moves against the active
governance profile.

For product workspaces, blocked core/self-evolution moves should not appear as
ordinary recommended next moves. They should either be omitted from the primary
recommendation or surfaced as blocked diagnostics with:

- `blocked_by_governance_profile`;
- active profile id;
- blocked subject;
- allowed alternative;
- required human action if upstream export is desired.

### 3. Target And Path Enforcement

Supervisor target execution should verify the active profile before mutating
canonical artifacts.

At minimum:

- writes under forbidden roots are rejected before commit;
- direct target runs against locked core domains return a safe blocked result;
- path checks use repo-relative paths and fail closed on unknown profile;
- rejected targets produce structured artifacts instead of crashes.

### 4. Viewer-Facing Diagnostics

SpecSpace should not infer mode from repository name, URL shape, or branch.
SpecGraph should publish a viewer-facing projection with:

- active profile;
- core lock state;
- allowed domains;
- locked domains;
- blocked moves;
- next allowed action;
- whether upstream export is required.

### 5. Stable Client Instance Guide

Document the recommended setup for a new project:

- keep SpecGraph engine separate from project workspace state;
- start with a clean project graph;
- use `product_workspace`;
- bind SpecSpace to the project artifact root;
- publish project artifacts under a project-scoped path;
- export upstream SpecGraph issues explicitly instead of mutating the engine
  graph from the client workspace.

### 6. Smoke Scenario

Add a fixture or smoke scenario representing a simple external project, such
as a SwiftUI calculator.

The scenario should demonstrate:

- product workspace config is valid;
- project graph work remains allowed;
- SpecGraph core/self-evolution work is blocked or filtered;
- viewer surfaces explain the decision;
- tests can run without network or hosted deployment.

## Relationship To Product Workspace Governance Profile

This proposal is a follow-up to Product Workspace Governance Profile.

The previous proposal answered:

```text
What modes exist, and how should operators see the active mode?
```

This proposal answers:

```text
How does the active mode constrain supervisor behavior?
```

## Acceptance Criteria

- Product workspace enforcement is represented as one umbrella proposal rather
  than several disconnected proposals.
- The proposal names the required PR slices before runtime implementation.
- Next-move filtering, target/path enforcement, viewer diagnostics, and client
  instance guidance are explicitly in scope.
- Hosted multi-tenancy and automatic upstream export are explicitly out of
  scope.
- The proposal has a bounded source draft in `docs/archive/proposal_sources/`.
