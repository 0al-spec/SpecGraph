# Product Workspace Initialization

## Status

Draft proposal

## Source Material

This proposal captures the operator decision to give external product projects
a first-class SpecGraph entrypoint instead of requiring hand-written workspace
boilerplate.

Source draft:

- `docs/archive/proposal_sources/0054_product_workspace_initialization.md`

## Context

SpecGraph now distinguishes between:

```text
self_hosted_bootstrap
  SpecGraph improves SpecGraph itself.

product_workspace
  SpecGraph acts as a stable engine for an external product graph.
```

Product workspace governance defines the mode. Stable-mode enforcement blocks
ordinary core/self-evolution work in that mode. The missing piece is how a new
project gets into that mode safely.

Without a dedicated initialization entrypoint, a user must manually infer:

- where to create the workspace;
- which folders are required;
- how to write `specgraph.project.yaml`;
- how to seed the first intent or proposal;
- how to connect SpecSpace to the new artifact root;
- how to keep SpecPM imports review-first;
- how to avoid accidentally cloning SpecGraph core specs into the product
  graph.

## Problem

Product workspace setup is currently a documentation exercise rather than a
contracted SpecGraph capability.

That creates operational risk:

- project configuration can drift from the governance policy;
- different projects can invent incompatible folder layouts;
- SpecSpace has no stable initialization report to display;
- Platform can list workspaces but cannot yet call a SpecGraph-owned setup
  contract;
- new users may fork or copy SpecGraph when they only need an empty product
  workspace;
- package imports can be confused with initial canonical graph materialization.

The missing capability is a reviewable initialization flow that creates a
minimal project folder document without mutating SpecGraph core.

## Goals

- Define a first-class Product Workspace Initialization contract.
- Generate or validate a minimal product workspace layout.
- Create `specgraph.project.yaml` with `governance_profile: product_workspace`
  by default.
- Support an optional root intent capture without requiring immediate canonical
  spec materialization.
- Emit a derived initialization report for SpecSpace and Platform.
- Make initialization idempotent and safe to rerun.
- Keep SpecPM private-registry imports review-first and outside the initial
  canonical mutation step.
- Keep product workspace setup separate from SpecGraph self-evolution.

## Non-Goals

- Building a hosted account system.
- Implementing Docker or server deployment.
- Implementing SpecSpace project switching.
- Implementing SpecPM package import materialization.
- Auto-importing reusable specs from SpecPM.
- Copying SpecGraph `SG-SPEC-*` nodes into a product graph.
- Allowing the product workspace initialization flow to mutate SpecGraph core
  tools, policies, tests, or specifications.

## Core Proposal

SpecGraph should expose a bounded initialization capability for external
product workspaces.

Candidate command shape:

```bash
python3 tools/supervisor.py \
  --init-product-workspace \
  --project-id swiftui-calculator \
  --display-name "SwiftUI Calculator" \
  --workspace-root /path/to/SwiftUICalculator \
  --root-intent "Build a SwiftUI calculator for iOS and macOS."
```

The exact CLI can change during implementation, but the contract should remain:

```text
inputs
  project identity, workspace root, optional root intent, optional catalog hint

outputs
  folder layout, project config, initialization report, no core mutation
```

## Generated Workspace Layout

The initialized folder should be a document-like project workspace:

```text
SwiftUICalculator/
  specgraph.project.yaml
  specs/
  docs/proposals/
  runs/
  .specgraph/
```

Minimal `specgraph.project.yaml`:

```yaml
artifact_kind: specgraph_project_config
schema_version: 1
project_id: swiftui-calculator
display_name: SwiftUI Calculator
governance_profile: product_workspace
workspace:
  specs_root: specs/
  proposals_root: docs/proposals/
  runs_root: runs/
  publish_root: projects/swiftui-calculator/
supervisor:
  allow_core_policy_mutation: false
  allow_core_tooling_mutation: false
  allow_self_evolution_proposals: false
```

## Initialization Report

The flow should write a reviewable derived artifact, for example:

```text
runs/product_workspace_initialization.json
```

Suggested shape:

```json
{
  "artifact_kind": "product_workspace_initialization",
  "schema_version": 1,
  "canonical_mutations_allowed": false,
  "tracked_artifacts_written": false,
  "project": {
    "project_id": "swiftui-calculator",
    "display_name": "SwiftUI Calculator",
    "governance_profile": "product_workspace"
  },
  "workspace": {
    "root": "<repo-or-platform-relative-path>",
    "created_paths": [
      "specgraph.project.yaml",
      "specs/",
      "docs/proposals/",
      "runs/",
      ".specgraph/"
    ]
  },
  "root_intent": {
    "status": "captured|not_provided",
    "next_gap": "review_before_canonical_materialization"
  },
  "review_state": "ready_for_review",
  "next_gap": "review_before_first_spec_materialization"
}
```

The report is not a canonical spec mutation. It is a setup receipt and
operator-review surface.

## Platform Boundary

Platform may orchestrate workspace creation and catalog registration, but
SpecGraph owns the semantics of a valid product workspace.

Suggested division:

- Platform owns `workspaces.yaml`, service topology, and launch profiles.
- SpecGraph owns `specgraph.project.yaml` validity and initialization report.
- SpecSpace reads Platform catalog and SpecGraph reports to show workspace
  status.
- SpecPM remains a package source, not an automatic initializer.

## SpecSpace Boundary

SpecSpace should be able to display:

- initialized/not initialized;
- active governance profile;
- project id and display name;
- workspace root/provider;
- root intent captured or missing;
- next safe action;
- whether imports are review-only.

SpecSpace should not infer initialization success from directory presence alone.
It should prefer the SpecGraph initialization report when available.

## SpecPM Boundary

Private SpecPM registry integration belongs after initialization.

Initialization may record registry hints such as:

```yaml
registry:
  specpm_registry_id: local-private
  import_policy: review_first
```

But it must not automatically materialize package contents into canonical
product specs. The first package step should remain:

```text
discover -> import preview -> handoff/proposal -> human approve -> materialize
```

## Safety Rules

- Product initialization must not mutate SpecGraph core.
- Existing non-empty workspace paths must fail safe or require explicit
  operator confirmation.
- Absolute local paths must not be written into shared artifacts unless marked
  local-only.
- Re-running initialization should be idempotent when files match the expected
  content.
- Conflicting existing config should produce a repairable report, not partial
  overwrite.
- Root intent capture should not bypass human review into canonical spec
  materialization.

## Acceptance Criteria

- The proposal defines Product Workspace Initialization as a SpecGraph-owned
  capability.
- The proposal separates SpecGraph initialization semantics from Platform
  orchestration.
- The proposal defines generated layout, project config, initialization report,
  and no-core-mutation safety.
- SpecSpace and SpecPM responsibilities are named without implementing them.
- Auto-import and hosted platform behavior are explicitly out of scope.
- The proposal has a bounded source draft in `docs/archive/proposal_sources/`.
