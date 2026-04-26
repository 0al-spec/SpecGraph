# Implementation Work Layer

Status: Draft proposal

## Problem

SpecGraph now has a credible path from raw intent into canonical
specifications, and a growing set of derived surfaces that explain graph
quality, trace state, evidence state, proposal readiness, and downstream
handoffs.

The next gap is the handoff between a sufficiently mature specification and
actual implementation work.

If an agent jumps directly from `spec -> code`, the system loses the reviewable
middle step that answers:

- what has already been implemented;
- what changed in the current graph version;
- what still needs to be implemented;
- which tests and evidence are required;
- which code areas are likely affected;
- whether the request is ready for a coding agent.

That middle step should become a first-class layer.

## Layer Model

SpecGraph should distinguish four layers:

```text
Layer 0: Exploration
Layer 1: Specification
Layer 2: Implementation Work
Layer 3: Runtime / Evidence
```

### Layer 0: Exploration

Exploration contains raw intent, assumptions, hypotheses, and mindmap-style
preview surfaces.

It is not canonical.

Examples:

- `runs/exploration_preview.json`
- raw operator intent
- assumption clusters
- hypothesis clusters
- pre-promotion preview nodes

### Layer 1: Specification

Specification is canonical SpecGraph.

It contains:

- contracts;
- invariants;
- acceptance criteria;
- lifecycle and authority rules;
- quality gates;
- graph structure and relationships.

Canonical specs live in:

- `specs/nodes/*.yaml`

### Layer 2: Implementation Work

Implementation Work is a reviewable bridge layer between canonical
specification and code.

It is not code.

It is not canonical spec truth.

It should answer:

- what implementation delta exists relative to an implemented baseline;
- which specs or contract changes must be implemented now;
- what tests are required;
- what evidence must be collected;
- which code areas are likely affected;
- whether work is ready for a coding agent or blocked by trace/evidence/spec
  quality gaps.

Initial artifacts should be derived-only:

- `runs/implementation_delta_snapshot.json`
- `runs/implementation_work_index.json`

### Layer 3: Runtime / Evidence

Runtime / Evidence contains the actual implementation result:

- code changes;
- PRs;
- tests;
- telemetry/evidence;
- trace links back to specs;
- adoption or runtime observation.

This layer should feed back into trace and evidence surfaces, not silently
rewrite canonical specifications.

## Core Proposal

When an operator asks to move a spec or graph region toward implementation, the
supervisor should not immediately write code.

It should first emit an implementation delta snapshot:

```text
implemented baseline + current target graph state -> implementation delta
```

The delta snapshot is then converted into implementation work items that can be
reviewed, filtered, and handed to a coding agent.

This preserves reviewability at the most important boundary:

```text
meaning -> implementation
```

## Implementation Delta Snapshot

Add a derived artifact:

```text
runs/implementation_delta_snapshot.json
```

It should compare:

- an implemented baseline, backed by trace/evidence/git state;
- a target spec state, chosen by explicit operator scope;
- the current canonical graph version.

The snapshot should include:

- baseline graph version or git commit SHA;
- target graph version or git commit SHA;
- selected target specs or graph region;
- already implemented specs;
- new specs;
- changed specs;
- changed contracts;
- changed acceptance criteria;
- missing trace links;
- required tests;
- evidence gaps;
- likely affected files when known;
- readiness and blockers.

The artifact is derived and review-only. It must not mutate canonical specs,
proposal-lane nodes, implementation files, or downstream repositories.

## Implementation Work Index

Add a second derived artifact:

```text
runs/implementation_work_index.json
```

This artifact turns the delta snapshot into bounded work items.

Each work item should include:

- `work_item_id`
- `affected_spec_ids`
- `implementation_reason`
- `delta_refs`
- `required_tests`
- `expected_evidence`
- `likely_code_refs`
- `readiness`
- `blockers`
- `next_gap`

Initial readiness vocabulary:

- `ready_for_planning`
- `blocked_by_trace_gap`
- `blocked_by_evidence_gap`
- `blocked_by_spec_quality`
- `ready_for_coding_agent`
- `in_progress`
- `implemented_pending_evidence`
- `implemented`

The work index is still not a coding task runner. It is the reviewable work
planning surface that a coding agent can consume after human approval or an
explicit operator request.

## Eligibility

A spec or region becomes eligible for Implementation Work when:

- the operator explicitly asks to implement it;
- the relevant canonical specs are mature enough for handoff;
- graph quality and metric gates do not report active blocking issues;
- trace/evidence baseline can distinguish already implemented work from new
  work;
- any authority or policy change still routes through proposal review.

Eligibility does not mean automatic coding. It means the system may emit a
reviewable implementation delta and work index.

## Relationship To Existing Surfaces

The implementation work layer builds on:

- `runs/spec_trace_index.json`
- `runs/spec_trace_projection.json`
- `runs/evidence_plane_index.json`
- `runs/evidence_plane_overlay.json`
- `runs/graph_health_overlay.json`
- `runs/graph_dashboard.json`
- proposal-lane and promotion surfaces
- TechSpec handoff concepts

It should not replace those surfaces. It should join them into a bounded
implementation-planning read model.

## Viewer Contract

Viewer integration should show:

- the selected target scope;
- implemented baseline summary;
- delta summary;
- work item cards;
- required tests;
- evidence gaps;
- blockers;
- readiness to hand off to a coding agent.

The viewer should explicitly label this as:

```text
Implementation planning, not canonical graph mutation.
```

## Boundaries

This proposal does not add:

- automatic code generation;
- automatic PR creation;
- automatic canonical spec updates;
- automatic proposal promotion;
- `implementation_lane/nodes/*.json`;
- a new permanent markdown task queue.

`tasks.md` remains deprecated. Durable work discovery should come from
graph-native derived surfaces.

## Runtime Realization Path

Phase 1:

- Add this proposal.
- Add a declarative `tools/implementation_delta_policy.json` skeleton.
- Add a viewer-facing contract for the planned artifacts.

Phase 2:

- Implement `--build-implementation-delta-snapshot`.
- Generate `runs/implementation_delta_snapshot.json`.
- Add tests for source-artifact availability, selected target scope, and
  derived-only boundaries.

Phase 3:

- Implement `--build-implementation-work-index`.
- Generate bounded implementation work items from the delta snapshot.
- Feed headline counts into dashboard/backlog projection.

Phase 4:

- Add ContextBuilder viewer support for implementation delta and work item
  panels.
- Consider tracked `implementation_lane/nodes/*.json` only if the derived
  artifacts prove stable.

## Acceptance Criteria

- The four-layer model is documented.
- The system has a proposal-level definition of Implementation Work as a
  reviewable bridge layer.
- The first implementation delta and work-index artifact contracts are
  declared.
- The proposal explicitly prevents direct `spec -> code` jumps from becoming
  the default supervisor behavior.
- Later runtime work can implement snapshot/index builders without redefining
  the architecture.
