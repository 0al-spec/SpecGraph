# Product Workspace Governance Profile Source Draft

## Operator Intent

SpecGraph needs a deployable mode for customer or external project workspaces
where the engine is stable and the graph evolves around the customer's product,
not around SpecGraph itself.

The operator wants to separate:

- self-hosted bootstrap mode, where SpecGraph improves its own specs, tooling,
  policies, and runtime behavior;
- product workspace mode, where SpecGraph is used as a stable engine to capture
  product intents, grow project specs, build implementation work, and publish
  viewer artifacts.

## Working Assumptions

- The current repository mixes engine/tooling and SpecGraph's own self-hosted
  graph state because SpecGraph is bootstrapping itself.
- Customer deployments should not inherit that self-evolution authority by
  default.
- Project-level diagnostics, evidence, implementation work, and retrospective
  review are still useful and should remain enabled.
- Core SpecGraph policy and tooling changes should arrive through engine
  upgrades, not through a customer's project graph run.

## Desired Boundary

Product workspace mode should permit:

- creating and refining customer product intents and specs;
- emitting project-scoped proposals;
- building trace, evidence, implementation work, dashboard, backlog, and next
  move artifacts for the customer graph;
- publishing those artifacts to a project-scoped static or API-backed surface.

Product workspace mode should prohibit:

- modifying SpecGraph core tooling or tests;
- modifying core governance policies;
- creating self-evolution proposals about SpecGraph's own supervisor/runtime;
- treating review feedback about SpecGraph internals as customer graph work;
- running self-improvement marathons over canonical SpecGraph `SG-SPEC-*`
  bootstrap nodes.

## Candidate Shape

```yaml
project_id: swiftui-calculator
governance_profile: product_workspace

core:
  mutation_policy: locked
  allowed_core_updates: package_upgrade_only

workspace:
  specs_root: specs/
  proposals_root: docs/proposals/
  runs_root: runs/

supervisor:
  allow_project_spec_refinement: true
  allow_project_proposals: true
  allow_core_policy_mutation: false
  allow_core_tooling_mutation: false
  allow_self_evolution_proposals: false
```

## Boundary

The profile should disable SpecGraph core self-evolution authority, not all
reflection. Customer project retrospectives, implementation evidence, and
quality diagnostics remain part of the product development loop.
