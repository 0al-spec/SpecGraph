# Refinement Fan-Out Pressure and Intermediate Clustering

## Status

Draft proposal

## Problem

SpecGraph already has meaningful pressure toward:

- bounded specs
- explicit lineage
- reviewable refinement
- graph-health signals for serial ladders and bookkeeping drift

But it still lacks one useful complementary signal:

> When does a node remain locally valid while still becoming too broad because
> it accumulates too many direct children?

This matters most for root-like or intermediate coordination nodes that can
still pass normal structural checks while gradually turning into wide,
hard-to-read hubs.

The failure mode is not necessarily "too deep."

It is often:

- too many direct child edges
- too many unrelated downstream concerns hanging from one parent
- a flattening of meaningful intermediate grouping
- increased risk of duplicated terms, scattered acceptance, and reviewer
  overload

Without an explicit signal, the system can keep producing a graph that is
technically valid but semantically broader than preferred.

## Why This Matters

A node with many direct children is not automatically wrong.

Some nodes legitimately coordinate several tightly related concerns.

However, unchecked fan-out often correlates with:

- loss of semantic locality
- weaker aggregate role boundaries
- noisier review packets
- duplicated or partially overlapping child scopes
- pressure to reason about many sibling concerns at once

In those cases, the healthier move is often not further leafward splitting.

It is an intermediate regrouping step that materializes one or more cluster
nodes between the broad parent and its overly numerous direct children.

SpecGraph should be able to recognize that condition and recommend it
explicitly.

## Goals

- Define a non-blocking fan-out pressure signal for broad parent nodes.
- Distinguish healthy multi-child coordination from semantically broad hubs.
- Prefer intermediate clustering or regrouping when direct-child spread becomes
  excessive.
- Keep the signal advisory rather than a hard validity failure.
- Make the signal compatible with existing graph-health and role-legibility
  work.

## Non-Goals

- Imposing one absolute child-count threshold for every node kind
- Automatically rejecting nodes with many direct children
- Forcing cluster creation for every wide subtree
- Replacing semantic review with a single numeric heuristic
- Treating high fan-out as equivalent to deep serial decomposition

## Core Proposal

SpecGraph should introduce a derived graph-health signal for
**refinement fan-out pressure**.

The signal should answer:

> Is this node accumulating enough direct refinement breadth that an
> intermediate clustering pass should be considered?

This should begin as:

- a warning or recommendation signal
- a reason to consider regrouping
- an input into proposal framing and refactor selection

It should not begin as:

- a hard validator failure
- an automatic rewrite
- a forced child-materialization rule

## Signal Semantics

Fan-out pressure should be interpreted as a derived quality indicator rather
than a canonical fact.

The signal may consider:

- number of direct child specs
- breadth of acceptance owned or delegated by the parent
- diversity of child concern language
- evidence that the parent is acting as a loose hub rather than a coherent
  aggregate role

The exact formula need not be frozen immediately.

The important contract is that the system can distinguish between:

- healthy multi-child composition
- and broadness that suggests missing intermediate grouping

## Recommended Response

When fan-out pressure is elevated, supervisor should prefer recommendations
such as:

- `regroup_under_intermediate_cluster`
- `rebalance_direct_children`
- `introduce_semantic_cluster_parent`

before it defaults to:

- another flat child split from the same broad node
- deeper leaf slicing with no new aggregate boundary
- acceptance redistribution that preserves an already noisy sibling fan-out

The intent is to restore locality, not merely to reduce child count.

## Intermediate Clustering Principle

The preferred corrective move for fan-out pressure is often an
**intermediate clustering pass**.

That means introducing one or more nodes that each own a stronger grouped role,
so the broad parent can delegate through meaningful sub-boundaries instead of
directly owning many unrelated children.

This should only be recommended when those cluster nodes can be named as
legible roles or composed functions.

The proposal does not justify meaningless wrapper nodes.

It justifies regrouping when the missing boundary is semantically real.

## Relationship to Existing Work

### Proposal 0008

[0008_refinement_shape.md](/Users/egor/Development/GitHub/0AL/SpecGraph/docs/proposals/0008_refinement_shape.md)
focuses on serial ladders and over-atomized refinement shape.

This proposal complements it by addressing the opposite direction:

- not "too deep"
- but "too wide"

### Proposal 0017

[0017_role_first_semantic_bias_for_supervisor.md](/Users/egor/Development/GitHub/0AL/SpecGraph/docs/proposals/0017_role_first_semantic_bias_for_supervisor.md)
adds role-legibility pressure.

Fan-out pressure should work with that proposal, not separately from it.

The key combined question becomes:

- does the parent still read as a strong aggregate role?
- and if not, is breadth one of the reasons?

### Metric and Viewer Work

This proposal is also compatible with later work on:

- metric-derived graph-health inputs
- viewer overlays for graph-health pressure
- longitudinal trend reporting

Those future layers may eventually show whether the same subtree repeatedly
develops excessive breadth.

## Implementation Direction

The intended order of adoption is:

1. add a derived fan-out pressure signal to graph-health inspection
2. use it in proposal or refactor recommendation wording
3. teach supervisor to prefer regrouping actions when the signal is high
4. later expose the signal in viewer overlays and trend reports

This keeps early adoption lightweight while still making the signal useful.

## Open Questions

- Should thresholds be absolute, adaptive, or profile-specific?
- Should breadth pressure explicitly factor acceptance diversity, or only
  direct-child count at first?
- How should historically broad but already stable regions be treated?
- When should fan-out pressure recommend a proposal-first regrouping flow
  instead of direct rewrite?
