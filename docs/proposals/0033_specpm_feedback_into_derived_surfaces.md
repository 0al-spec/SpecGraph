Status: Implemented

# 0033. SpecPM Feedback into Derived Surfaces

## Problem

`SpecGraph` can already:

- preview a `SpecPM` export bundle;
- emit downstream handoff packets;
- materialize a local draft bundle into the sibling `SpecPM` checkout;
- inspect inbound bundles through import preview and import-handoff artifacts;
- scaffold a reviewable downstream delivery workflow.

What is still missing is a reverse observation layer:

> once a bundle exists in `SpecPM`, how does `SpecGraph` observe downstream
> review or local adoption signals without treating that downstream state as
> canonical truth automatically?

Right now viewers can see:

- what package was exported;
- whether it was materialized locally;
- whether a downstream delivery workflow is ready or blocked.

They still cannot see:

- whether the downstream checkout has started tracking the bundle;
- whether bundle commits are now visible in downstream git history;
- whether the bundle appears to have landed on the downstream default branch;
- what next follow-up gap that downstream observation creates inside
  `SpecGraph`.

## Goals

- Add a derived feedback artifact on top of the existing `SpecPM` delivery
  workflow.
- Observe downstream review/adoption signals from the sibling checkout through
  git-visible state only.
- Link that feedback back to the originating `SpecGraph` package and source
  specs.
- Feed the result into dashboard/report surfaces without mutating canonical
  specs automatically.

## Non-Goals

- Treating downstream branch state as canonical graph truth.
- Auto-applying any downstream acceptance back into `specs/nodes/*.yaml`.
- Requiring a downstream PR integration before feedback becomes observable.
- Replacing the existing delivery workflow artifact.

## Core Proposal

Add a new derived artifact:

- `runs/specpm_feedback_index.json`

Built from:

- `runs/specpm_delivery_workflow.json`
- the current `SpecPM` sibling checkout git state
- the current `SpecPM` export preview for source-spec lineage

The feedback artifact should classify each package into a bounded observed
state such as:

- `downstream_unobserved`
- `review_activity_observed`
- `adoption_observed_locally`
- `blocked_by_delivery_gap`
- `invalid_feedback_contract`

The artifact must make two boundaries explicit:

1. downstream observation is valuable evidence;
2. downstream observation is **not** automatic canonical acceptance.

## Expected Effect

After this change:

- the delivery workflow answers “is a downstream exchange safe and reviewable?”
- the feedback index answers “what downstream review or local adoption state is
  now observable?”

That closes the first reverse observation loop for `SpecPM` without skipping
review, without silent canonical mutation, and without pretending that local
downstream acceptance is the same thing as upstream semantic truth.
