# Spec-to-Code Trace Plane and Implementation Overlay

## Status

Draft proposal

## Problem

SpecGraph is already becoming a stronger canonical graph of:

- bounded semantic roles
- lineage and supersession
- review gates
- proposals and refinement structure

But implementation observability still lives outside the graph.

Today, the project can see:

- canonical specs in `specs/nodes`
- proposals in `docs/proposals`
- operator backlog in `tasks.md`
- implementation in code and tests
- review state in pull requests and run artifacts

What it still cannot see clearly is:

> How implemented is this part of the graph, and how confidently is that
> implementation traced back to the governing specs?

This creates several problems:

- `tasks.md` becomes a growing external backlog rather than a projection of the
  graph
- code can materialize without a clear graph-facing trace
- a spec may be partially implemented, fully implemented, verified, stale, or
  drifting, but the graph cannot show that directly
- proposals can accumulate "to the left" while implementation and verification
  move elsewhere
- a reader cannot quickly tell whether a subtree is only semantically defined,
  actively being implemented, already covered by tests, or drifting after
  subsequent code changes

The result is that graph meaning, implementation activity, and execution
backlog feel adjacent but not formally connected.

## Why This Matters

SpecGraph becomes much more useful if a reader can inspect not only:

- what the system should mean
- and how the graph is evolving

but also:

- where that meaning is materialized in code
- how far implementation has progressed
- what evidence exists for acceptance coverage
- whether implementation has drifted since the last trusted verification

Without that layer, the project keeps relying on three weak substitutes:

- memory
- scattered PR history
- a manually maintained flat task list

That makes it harder to:

- choose the next bounded implementation move
- review whether a subtree is merely specified or actually embodied
- detect stale verification after later code changes
- distinguish "not implemented yet" from "implemented but not traced"
- show implementation coverage directly on graph nodes

In short:

the graph currently governs meaning, but it does not yet expose implementation
state as a first-class inspectable overlay.

## Goals

- Define a formal spec-to-code trace plane adjacent to canonical SpecGraph.
- Introduce a derived implementation overlay for nodes and subtrees.
- Make implementation state readable directly on the graph without polluting
  canonical spec prose.
- Link specs to code, tests, pull requests, commits, and verification records.
- Distinguish implementation progress from implementation evidence.
- Make backlog views derivable from graph-bound trace artifacts rather than
  maintained only as external flat lists.
- Support drift and freshness detection after code or tests change.
- Keep the model general enough for non-code artifacts and later Tech Spec
  handoff.

## Non-Goals

- Turning canonical spec YAML into a manual inventory of source files
- Replacing Git history, pull requests, or code review systems
- Creating a full project management platform inside SpecGraph
- Requiring immediate perfect trace coverage for every existing spec
- Auto-generating tasks or code changes without review
- Mandating one exact storage engine or viewer implementation for trace
  artifacts

## Core Proposal

SpecGraph should recognize a **spec-to-code trace plane** as a derived layer
adjacent to:

- canonical spec nodes
- proposal-lane artifacts
- evidence overlays

This plane should answer:

- where a spec is embodied
- what implementation state that embodiment is in
- what verification exists
- whether that verification is fresh or stale

The trace plane should remain **derived and inspectable**, not canonical truth
by default.

Canonical specs continue to answer:

- what the system means
- what boundaries and contracts exist
- what acceptance matters

The trace plane answers:

- where those contracts are implemented
- how complete that implementation appears
- what evidence supports that claim

## Layer Model

This proposal clarifies four adjacent layers.

### 1. Canonical Graph

This layer owns:

- semantic roles
- bounded contracts
- lineage
- gates
- canonical acceptance

### 2. Proposal Layer

This layer owns:

- suggested graph changes
- provisional structure
- reviewable mutation candidates

### 3. Implementation Trace Plane

This new layer owns:

- code and test linkage to specs
- implementation-state overlays
- verification coverage summaries
- freshness and drift indicators
- implementation-facing backlog projections

### 4. Evidence Plane

This layer, as proposed separately, owns:

- runtime observations
- telemetry correlations
- adoption and outcome evidence

The key distinction is:

- canonical graph says what should be true
- implementation trace says where that truth is embodied
- evidence says what runtime behavior was observed

## Trace Artifact Concept

SpecGraph should introduce a derived artifact family for implementation trace.

A representative trace artifact may eventually include fields such as:

- `spec_id`
- `implementation_state`
- `code_refs`
- `test_refs`
- `pr_refs`
- `commit_refs`
- `acceptance_coverage`
- `last_verified_at`
- `verification_basis`
- `drift_state`

This artifact is not required to live inside canonical spec YAML.

It may live in:

- a derived artifact store
- a generated index
- a viewer cache
- or another trace-oriented layer

The important point is that the artifact is graph-bound and spec-addressable.

## Implementation State Overlay

The project should define a small implementation-state vocabulary that can be
projected onto graph nodes.

Representative states may include:

- `unclaimed` - no implementation trace is attached yet
- `planned` - an implementation path is identified but work has not started
- `in_progress` - code or tests are actively changing for this spec
- `implemented` - code anchors exist and appear materialized
- `verified` - implementation is backed by explicit verification evidence
- `drifted` - implementation changed after the last trusted verification
- `blocked` - implementation is intentionally paused by dependency or review
  state

These states should remain derived statuses, not canonical spec statuses.

This prevents confusion between:

- refinement maturity of the spec
- and embodiment maturity of the implementation

## Code, Test, and Review Linkage

The trace plane should be able to link a spec to several embodiment surfaces.

### Code References

These indicate where the implementation appears to live.

Examples:

- source files
- generator outputs
- configuration artifacts
- integration boundaries

### Test References

These indicate how implementation claims are verified.

Examples:

- unit tests
- integration tests
- snapshot or fixture tests
- lints or structural validations

### Review References

These indicate where the implementation was reviewed or landed.

Examples:

- pull requests
- commits
- review decisions
- release or migration artifacts

Together, these let a viewer answer:

- where is this spec embodied?
- how was it verified?
- when was that verification last refreshed?

## Acceptance Coverage

Implementation trace should not stop at file linkage.

It should also support a lightweight notion of **acceptance coverage**.

The important question is not merely:

- does some code reference this spec?

but:

- how much of the spec's stated acceptance appears materially covered?

This proposal does not require one final schema yet.

But it does require the project to distinguish:

- code presence
- implementation state
- verification presence
- acceptance coverage confidence

These are different claims and should not collapse into one boolean.

## Freshness and Drift

The trace plane should treat freshness as a first-class concern.

A spec may have excellent code and test linkage while still becoming stale.

Typical causes:

- implementation files changed after the last verification snapshot
- linked tests changed or were removed
- the governing spec changed but trace coverage was not refreshed
- a later PR affected the traced code path without re-verifying the spec

The graph should be able to surface this as:

- `verified`
- `verified_but_stale`
- `drifted`

or equivalent derived labels.

This matters because "implemented once" is not the same thing as "currently
trustworthy."

## Backlog as Projection

One major consequence of this proposal is that operator backlog should
increasingly become a **projection** of the graph and trace plane.

For example, a backlog view could be generated from queries like:

- specs with no implementation trace
- specs with `planned` but no active PR
- specs with `implemented` but not `verified`
- specs with `drifted` trace state
- specs with accepted proposals but no implementation owner

This does not mean `tasks.md` must disappear immediately.

But long term, `tasks.md` should increasingly be:

- a generated or synchronized operating view
- not the only place where implementation intent is tracked

In other words:

the graph should not depend on a flat external backlog to express execution
state that could be observed directly from its own trace layer.

## Viewer Implications

This proposal gives the viewer a clear future role.

It should eventually be able to render node overlays such as:

- no implementation trace
- implementation in progress
- implemented but not verified
- verified and fresh
- verified but stale
- drift detected

It should also support filters like:

- show all unimplemented accepted specs
- show all drifted verified nodes
- show all specs touched by PR X
- show all specs whose acceptance is only partially covered

This makes the graph much more operational without changing its canonical
meaning surface.

## Supervisor and Evaluator Implications

Supervisor should not immediately mutate implementation trace as canonical
truth.

But this trace plane can eventually help it:

- choose the next bounded implementation target
- detect when proposals are piling up without implementation follow-through
- avoid selecting already-verified stable regions when drifted ones need
  attention
- emit better backlog projections

Evaluator can later use this plane to distinguish:

- graph incompleteness
- implementation incompleteness
- verification incompleteness
- drift after prior completion

That is a stronger basis for prioritization than a flat backlog alone.

## Relation to Tech Spec Handoff

This proposal fits naturally below the SpecGraph-to-TechSpec boundary.

If a subtree reaches handoff-ready state, the implementation trace plane can
link:

- the canonical graph region
- the downstream Tech Spec artifact
- the code and tests that realize that handoff

This means trace is not limited to direct source files.

It can also show that a graph subtree is embodied through an intermediate
implementation-facing artifact.

## Relation to the Telemetry Evidence Plane

This proposal is related to, but distinct from, the telemetry evidence plane.

Implementation trace answers:

- where the spec is embodied
- how it was verified
- whether that embodiment is fresh

Telemetry evidence answers:

- what runtime behavior was observed
- what outcomes or adoption followed

One is about embodiment and verification.

The other is about runtime observation and outcome evidence.

Both can appear as overlays on the same graph without being the same layer.

## Adoption Order

The natural rollout order is:

1. Define the trace-plane ontology and implementation-state vocabulary.
2. Define the minimal trace artifact schema.
3. Link specs to code, tests, and PRs in a derived store.
4. Add freshness and drift heuristics.
5. Build graph overlays and backlog projections from that trace plane.
6. Only later let supervisor or evaluator rely on trace signals for selection
   or prioritization.

This order matters because it preserves inspectability before automation.

## Why This Is Useful

The strongest value in this proposal is not "put tasks on the graph."

The strongest value is:

- making implementation observability graph-native
- reducing the gap between spec meaning and code embodiment
- giving reviewers a direct way to inspect implementation state on graph nodes
- turning backlog from a manually curated external list into a derivable view
- making drift visible instead of silently accumulating after initial
  implementation

It lets SpecGraph remain a semantic governance graph while exposing whether its
contracts are actually embodied and still trusted.

## Open Questions

- What is the minimal trace artifact schema that gives value before the system
  becomes heavy?
- Should trace be owned per node only, or should some edges and handoff regions
  also receive direct embodiment records?
- How much acceptance coverage can be derived automatically, and how much
  requires explicit human attestation?
- Should `tasks.md` eventually be generated fully, or remain a mixed manual and
  derived operator surface?
- Which layer should own PR, commit, and code-anchor ingestion?
- What heuristics are strong enough to call a node `drifted` without producing
  too much noise?
