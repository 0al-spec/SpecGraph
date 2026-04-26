# Temporary Implementation Work Tasks

This is a temporary parking list for the implementation-work-layer discussion.
Do not treat this file as a durable backlog source. Each item should be
converted into a proposal, policy artifact, derived runtime artifact, or viewer
contract, then removed from this list.

`tasks.md` remains deprecated. The durable direction is graph-native work
discovery through derived surfaces, not a permanent markdown task queue.

## Layer Model To Capture

- [x] Define the layered model explicitly:
  `Layer 0 Exploration -> Layer 1 Specification -> Layer 2 Implementation Work -> Layer 3 Runtime/Evidence`.
- [x] Clarify that `Exploration` contains raw intent, assumptions, hypotheses,
  and preview/mindmap surfaces, but is not canonical.
- [x] Clarify that `Specification` is canonical SpecGraph: contracts,
  invariants, acceptance criteria, lifecycle, and quality gates.
- [x] Clarify that `Implementation Work` is a reviewable bridge layer, not code
  and not canonical spec truth.
- [x] Clarify that `Runtime/Evidence` contains code changes, PRs, tests,
  telemetry/evidence, and trace links back to specs.

## Proposal Work

- [x] Add proposal `0037_implementation_work_layer.md`.
- [x] In the proposal, define when a spec is eligible to move toward
  implementation work: quality metrics satisfied, trace/evidence baseline known,
  and human/operator intent to implement is explicit.
- [x] In the proposal, define why the agent should not jump directly from
  `spec -> code`; it should first emit reviewable work packets or handoff
  artifacts.
- [x] In the proposal, define the operator action: "move this graph/spec region
  to implementation" as a request to build an implementation delta snapshot.

## Delta Snapshot

- [x] Add `tools/implementation_delta_policy.json`.
- [x] Define `runs/implementation_delta_snapshot.json`.
- [x] Define the baseline fields:
  graph version or git commit SHA, implemented specs, implementation evidence,
  trace coverage, and freshness/drift status.
- [x] Define the target fields:
  selected spec ids or graph region, target graph version, requested quality
  gates, and operator intent.
- [x] Define the delta fields:
  new specs, changed specs, changed contracts, changed acceptance criteria,
  missing traces, required tests, evidence gaps, likely affected files, and
  implementation readiness.
- [x] Ensure the snapshot is derived and review-only; it must not mutate
  canonical specs, proposal-lane nodes, or implementation files.

## Implementation Work Index

- [x] Define `runs/implementation_work_index.json`.
- [x] Convert delta entries into bounded work items with stable ids.
- [x] Include work item fields:
  affected specs, implementation reason, required tests, expected evidence,
  likely code areas, readiness, blockers, and next gap.
- [x] Define status vocabulary:
  `ready_for_planning`, `blocked_by_trace_gap`, `blocked_by_evidence_gap`,
  `blocked_by_spec_quality`, `ready_for_coding_agent`, `in_progress`,
  `implemented_pending_evidence`, `implemented`.
- [x] Keep this layer distinct from canonical specs and from actual runtime
  code changes.

## Supervisor Commands

- [x] Add `--build-implementation-delta-snapshot`.
- [x] Add a way to pass explicit target scope for single or multiple spec ids.
- [ ] Add graph-region target scope once the viewer/operator contract names a
  stable region selector vocabulary.
- [x] Add `--build-implementation-work-index`.
- [x] Make both commands standalone derived-artifact modes.
- [x] Reject combinations with ordinary refinement flags unless an explicit
  operator-request packet contract supports them.

## Viewer Contract

- [x] Add `docs/implementation_work_viewer_contract.md`.
- [x] Define ContextBuilder panels for:
  implementation delta summary, changed specs, work items, blockers, required
  tests, and evidence gaps.
- [x] Define badges for readiness and blockers.
- [x] Define links from work items back to canonical specs, trace refs, evidence
  refs, and likely code refs.
- [x] Make the viewer show that this is an implementation planning surface, not
  a canonical graph mutation.

## Later, Only If Stable

- [ ] Consider `implementation_lane/nodes/*.json` only after the derived
  artifacts prove stable.
- [ ] Define promotion from implementation work item to actual coding-agent PR
  workflow.
- [ ] Feed completed implementation evidence back into trace/evidence surfaces.
- [ ] Remove this temporary file once the proposal and derived contracts cover
  the listed work.
