# SpecGraph-to-TechSpec Handoff Boundary

## Status

Draft proposal

## Problem

SpecGraph is intended to remain a graph of bounded concepts, relationships,
+governance rules, and structural decomposition.

It is not intended to absorb unlimited implementation detail.

In practice, a subtree may keep decomposing cleanly while becoming less useful
as a graph of meaning.

Typical symptoms:

- repeated one-child refinement chains
- nodes that are locally valid but increasingly execution-facing
- shrinking semantic novelty between parent and child
- growing attention on payload shape, edge sequencing, runtime gating, or
  implementation-order semantics rather than graph topology
- a subtree that feels more like a technical design packet than a concept map

This creates ambiguity:

- Is the graph still refining one more legitimate SpecGraph concept?
- Or has the subtree reached the lower boundary of the graph layer and started
  expressing future Tech Specs instead?

Without a formal boundary, supervisor may keep pushing detail downward inside
canonical graph specs, creating serialized ladders that are valid but
cognitively expensive.

That weakens the role of the graph as a navigable map of grouped meaning.

## Goals

- Define a lower boundary for canonical SpecGraph specs.
- Distinguish graph-layer decomposition from implementation-facing Tech Spec
  decomposition.
- Introduce a derived handoff signal when a subtree appears to have reached the
  Tech Spec boundary.
- Make this handoff a Definition-of-Done consideration for graph refinement.
- Preserve SpecGraph as a readable knowledge graph rather than an infinitely
  deep technical outline.
- Keep handoff reviewable and explicit rather than implicit drift.

## Non-Goals

- A final schema for Tech Specs
- A full task or implementation management system
- Immediate support for code-generation artifacts
- Automatic conversion of graph specs into implementation plans
- A claim that every deep subtree must become a Tech Spec

## Core Proposal

SpecGraph should recognize that canonical graph specs have a natural lower
boundary.

Below that boundary, further useful detail no longer improves the graph as a
graph.

Instead, it starts specifying:

- execution behavior
- implementation sequencing
- field-level technical contracts
- runtime payload details
- task-facing design decisions

When that happens, the correct next move is not always another child spec in
the same graph layer.

The correct next move may be:

- stop graph-layer refinement
- mark the subtree as handoff-ready
- emit a Tech Spec or implementation-facing artifact in another layer

## Layer Distinction

### Canonical SpecGraph Layer

This layer should own:

- bounded concepts
- topology
- refinement lineage
- governance boundaries
- proposal-vs-canonical separation
- role assignment between nodes
- aggregate decomposition at the concept-map level

### Tech Spec Layer

This layer should own:

- implementation-facing field contracts
- concrete execution sequencing
- runtime interaction surfaces
- component or service design constraints
- handoff-ready technical decisions needed for tasks or code

### Task / Implementation Layer

This layer should own:

- concrete work items
- code changes
- execution plans
- tests
- rollout and validation steps

## Handoff Signal

SpecGraph should introduce a derived signal family for lower-boundary detection.

Representative signals:

- `techspec_handoff_candidate`
- `implementation_layer_boundary_reached`
- `graph_layer_exhausted_for_subtree`

These signals should remain derived observations, not canonical fields on spec
nodes.

## When the Signal Should Fire

The handoff signal should be considered when several of the following hold:

- local atomicity continues to improve, but subtree readability gets worse
- a region becomes a serial refinement ladder
- new child nodes mostly define technical execution contracts rather than new
  graph concepts
- sibling grouping stops emerging
- further decomposition mostly narrows implementation detail rather than
  conceptual structure
- the subtree is increasingly useful as a technical packet but less useful as a
  graph overview

This proposal does not require one exact threshold, but it does require the
project to treat these as recognizable conditions rather than incidental drift.

## Definition of Done Implication

Graph refinement for one subtree should be considered complete enough when:

- the subtree has reached a stable concept-map shape
- the remaining unresolved detail is predominantly implementation-facing
- additional graph-layer decomposition would mainly create serial technical
  ladders
- the next best artifact is a Tech Spec rather than another canonical graph
  child

In other words:

one valid Definition of Done for graph refinement is not "all detail captured
in graph specs," but "the graph has captured all graph-native structure, and
the remainder should hand off to the next layer."

## Evaluator Behavior

When the handoff signal fires, evaluator should prefer:

1. stop further ordinary graph-layer refinement on the same subtree
2. emit a Tech Spec handoff proposal
3. mark the subtree as graph-complete enough for its current scope
4. avoid penalizing the graph for not absorbing implementation detail that
   belongs elsewhere

This should reduce wasted refinement cycles on already-exhausted graph nodes.

## Supervisor Behavior

Supervisor should not automatically create Tech Specs in canonical graph space.

Instead, when the subtree appears to have reached the lower boundary of the
graph layer, supervisor should:

- reduce preference for another graph child under the same node
- favor proposal-first handoff
- surface the handoff signal in run artifacts
- treat further deepening as suspicious unless the new child clearly introduces
  a new graph-native aggregate concern

## Viewer Implication

The viewer should eventually be able to show that a region is:

- still graph-native and actively decomposing
- over-serialized and likely needing rebalance
- ready for Tech Spec handoff

This helps users understand whether a deep subtree is a problem in graph shape
or a sign that the graph has already done its job.

## Why This Is Different From Shape-Quality Signals

Proposal `0008_refinement_shape.md` addresses subtree shape quality:

- too much depth
- too little breadth
- too many one-child ladders

This proposal addresses layer boundary:

- when a subtree should stop decomposing inside canonical graph specs at all

The two are related but not identical.

A subtree can be:

- badly shaped and still graph-native
- well shaped and still ready for Tech Spec handoff
- badly shaped because the system is forcing implementation detail into the
  wrong layer

## Recommended Initial Rule

The project should start with a conservative rule:

If a subtree repeatedly triggers both:

- shape-quality warnings such as `serial_refinement_ladder`
- and semantic signs that new children are predominantly execution-facing

then evaluator should emit a handoff-oriented proposal before permitting
further deep canonical decomposition.

## Relationship to Existing Proposals

### Proposal 0004

`0004_evaluator_loop.md` defines how evaluator chooses the next bounded
intervention. Handoff detection should become one of the stop-or-redirect
conditions.

### Proposal 0007

`0007_supervisor_performance.md` defines performance and graph-impact
measurement. Handoff readiness should be treated as graph-impact interpretation,
not runtime performance.

### Proposal 0008

`0008_refinement_shape.md` defines subtree shape smells. Those smells are one
important input to handoff detection, but not the whole decision.

## Open Questions

- What is the minimal artifact contract for a Tech Spec in this repository?
- Should Tech Specs live inside the graph as a different node kind or outside
  it as a neighboring tracked layer?
- Should handoff-ready subtrees become `frozen`, `reviewed`, or some new state
  at the graph layer?
- How much execution-facing detail is still acceptable inside canonical graph
  specs before handoff becomes mandatory?

## Proposed Next Step

After this proposal, the next bounded step should be:

- define a derived handoff signal contract for evaluator and supervisor
- specify how handoff readiness participates in graph-level Definition of Done
- decide whether Tech Specs live as a new tracked layer, proposal subtype, or
  external-but-linked artifact class
