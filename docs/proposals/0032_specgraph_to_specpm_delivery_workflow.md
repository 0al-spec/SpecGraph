# 0032. SpecGraph-to-SpecPM Delivery Workflow

## Status

Implemented

## Context

`SpecGraph` already knows how to:

- build a reviewable `SpecPM` export preview,
- emit downstream `SpecPM` handoff packets,
- materialize a local draft bundle into the sibling `SpecPM` checkout, and
- inspect that bundle again through import preview and import-handoff artifacts.

What is still missing is a reviewable workflow layer between local
materialization and actual downstream delivery. Right now a bundle can exist
inside `SpecPM/.specgraph_exports/<package_id>/`, but there is no declared
artifact that says:

- whether the sibling checkout is ready for downstream exchange,
- whether unrelated checkout changes would contaminate delivery review,
- which branch/commit/PR scaffold should be used, and
- what the next human review step is before a real downstream PR exists.

Without that workflow artifact, `.specgraph_exports/` remains a local-only draft
inbox rather than a visible cross-repo delivery lane.

## Decision

Add a reviewable delivery-workflow artifact on top of
`runs/specpm_materialization_report.json`.

The new layer will:

- inspect the real git state of the sibling `SpecPM` checkout,
- classify delivery readiness for each materialized package,
- surface unrelated checkout dirt as an explicit blocker,
- emit suggested branch/commit/PR scaffolding for downstream review, and
- remain review-first only.

The layer must not:

- auto-commit into `SpecPM`,
- auto-push a delivery branch,
- auto-open a downstream PR,
- treat local bundle presence as downstream acceptance.

## Artifact

Introduce:

- `runs/specpm_delivery_workflow.json`

with one entry per materialized package.

Each entry records:

- `delivery_status`
- `review_state`
- `next_gap`
- `delivery_root`
- `bundle_root`
- `delivery_paths`
- `repo_snapshot`
- `delivery_scaffold`

Status vocabulary:

- `ready_for_delivery_review`
- `draft_delivery_only`
- `blocked_by_materialization_gap`
- `blocked_by_checkout_gap`
- `blocked_by_repo_state`
- `invalid_materialization_contract`

## Readiness Semantics

`ready_for_delivery_review` means:

- the package was materialized for review,
- the sibling checkout is available and identity-verified,
- the checkout is a git repository, and
- there are no unrelated dirty paths that would mix downstream review scope.

`draft_delivery_only` means the same workflow is visible, but the underlying
materialization is still draft-only rather than fully review-ready.

`blocked_by_repo_state` is used when the sibling checkout exists but its git
state makes downstream review ambiguous, for example because unrelated changed
paths would be bundled together with `.specgraph_exports/<package_id>/`.

## Workflow Scaffold

The artifact should suggest, but not execute:

- a downstream branch name,
- a commit subject,
- a PR title,
- the exact delivery paths that belong to the package,
- a small ordered list of review steps.

This keeps the cross-repo workflow visible and reproducible before any future
automation or PR creation exists.

## Runtime Surfaces

- `tools/specpm_delivery_policy.json`
- `tools/supervisor.py`
- `tests/test_supervisor.py`
- `runs/specpm_delivery_workflow.json`

## Observation Loop

This slice closes a specific bootstrap gap:

- `specpm_materialization_report` answers “was a draft bundle written locally?”
- `specpm_delivery_workflow` answers “is that draft bundle now safe and scoped
  enough for real downstream review work?”

Later work may build actual cross-repo delivery actions on top of this
artifact, but this slice keeps the workflow review-first and derived.
