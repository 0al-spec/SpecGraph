# Refinement-Shape Signals for Serial Ladders and Over-Atomized Subtrees

## Status

Draft proposal

## Problem

SpecGraph currently has strong pressure toward atomic bounded specs.

That pressure is useful, but it can overshoot.

In practice, a subtree can become:

- structurally valid
- canonically formatted
- locally atomic at each node
- yet still difficult for a human or agent to reason about as one coherent
  region

The recurring failure mode is not a malformed node. It is a malformed shape.

Typical symptoms:

- a long `refines` chain with very few sibling branches
- repeated one-child delegation steps
- intermediate specs whose primary role is to say "this child owns the next
  narrower slice"
- low breadth and high depth in a region that a human would expect to read as
  one grouped cluster

This produces a graph that is technically consistent but cognitively expensive.

The current graph-health model already has signals for oversized nodes, weak
linkage, and stalled maturity. It does not yet have a formal way to say:

- this subtree is too serialized
- this subtree is over-atomized
- this subtree needs a rebalance toward aggregate nodes and sibling grouping

Without such signals, supervisor runs may keep improving local atomicity while
quietly worsening global comprehensibility.

## Goals

- Define graph-shape signals that detect excessive serial refinement and
  over-atomized subtrees.
- Distinguish subtree-shape problems from ordinary local spec defects.
- Make these signals derived graph-health observations rather than canonical
  spec facts.
- Allow evaluator and supervisor policy to penalize deep one-child ladders even
  when individual nodes are valid.
- Trigger retrospective subtree rebalance proposals when the graph shape
  becomes cognitively costly.
- Preserve the atomic-spec principle without forcing every decomposition into a
  long single-child chain.

## Non-Goals

- A hard ban on deep refinement chains
- A claim that every one-child chain is bad
- Final numeric thresholds for every repository or domain
- Immediate automatic canonical rewrites whenever shape signals fire
- Viewer implementation details or final graph-layout rules

## Core Proposal

SpecGraph should add a new derived graph-health family for subtree shape.

This family should detect when a region is valid in isolation but poorly formed
as a navigable cluster.

Two primary smells should be introduced.

### 1. Serial Refinement Ladder

This smell captures a subtree that is mostly a single vertical path.

It should fire when:

- a `refines` chain grows beyond a bounded depth
- most internal nodes in that chain have only one meaningful refinement child
- breadth does not emerge as the chain deepens
- successive nodes mostly restate delegation topology rather than defining
  clearly different groups of concern

### 2. Over-Atomized Subtree

This smell captures a subtree where local atomicity has become too fine-grained
for practical comprehension.

It should fire when:

- many nodes have very small bounded payloads
- the subtree is deeper than it is broad
- intermediate nodes serve mainly as routing layers
- there is no stable aggregate node that groups a small number of sibling
  branches into a readable cluster

## Human-Cognitive Baseline

The shape target should not be "minimum depth at all costs."

The shape target should be:

- one aggregate or cluster node when a concern naturally groups
- two to four meaningful sibling children beneath that node
- leaf nodes only where concerns genuinely diverge

In other words, the preferred structure is often:

- one cluster node
- a few sibling branches
- then leaf specs

not:

- one cluster node
- one child
- one child
- one child
- one child

## Derived Metrics

The following metrics should be derivable from the canonical graph and spec
content.

### Structural Metrics

- `one_child_refines_chain_length`
- `subtree_max_depth`
- `subtree_effective_breadth`
- `single_child_internal_node_ratio`
- `aggregate_child_count`
- `depth_without_breadth_score`

### Semantic-Heuristic Metrics

- `delegation_only_node_ratio`
- `title_similarity_along_chain`
- `dependency_overlap_along_chain`
- `boundary_only_ratio`
- `aggregate_absence_score`

These metrics do not need perfect semantic understanding to be useful.
Heuristic approximations are acceptable at first.

## Primary Signals

The first shape signals should be:

- `serial_refinement_ladder`
- `over_atomized_subtree`
- `missing_aggregate_node`
- `depth_without_breadth`
- `delegation_only_chain`

These should be emitted as derived graph-health observations, not written into
canonical spec nodes.

## Composite Risk Signal

The system may later compute a composite signal:

- `serial_over_atomization_risk`

This should combine structural depth, lack of breadth, and low semantic novelty
between neighboring nodes.

This composite should remain advisory at first.

## Recommended Evaluator Behavior

When shape signals fire repeatedly in the same subtree, the evaluator should
prefer:

1. retrospective subtree rebalance
2. aggregate-node proposal
3. sibling regrouping
4. compression of purely serial delegation layers

The evaluator should prefer those actions over continuing ordinary refinement
on the same ladder node.

## Supervisor Implications

Supervisor should not immediately rewrite canonical shape because a subtree
looks over-atomized.

Instead, these signals should first drive:

- selection penalties in next-step choice
- reviewable refactor proposals
- subtree-targeted split or regrouping interventions

This keeps graph-shape correction aligned with existing proposal-first and
review-gated governance.

## Why This Is Separate From Atomicity

Atomicity answers:

- is this node too broad?

Shape-quality answers:

- is this region too serialized?
- is this region too fragmented for comprehension?
- did local decomposition improve or worsen the readability of the whole
  subtree?

Both are necessary.

A graph can fail atomicity by being too large.
A graph can fail shape-quality by being too thin.

## Relationship to Existing Proposals

### Proposal 0004

`0004_evaluator_loop.md` defines the higher-level evaluator that selects the
next bounded intervention. Shape signals should become one of the evaluator's
inputs.

### Proposal 0007

`0007_supervisor_performance.md` defines runtime, yield, and graph-impact
measurement. Shape-quality metrics belong in the graph-impact layer rather than
runtime or yield.

## Recommended Initial Thresholds

Initial thresholds should remain heuristic and reviewable.

Reasonable starting points:

- warn when `one_child_refines_chain_length >= 4`
- warn when `subtree_max_depth > subtree_effective_breadth`
- warn when `single_child_internal_node_ratio` is high across one subtree
- warn when most intermediate nodes are boundary/delegation-only nodes

These thresholds should first produce signals and proposals, not hard failures.

## Open Questions

- How much title or acceptance overlap is enough to count as low semantic
  novelty?
- Should viewer overlays show shape smells directly, or only the derived
  metrics behind them?
- Should a chain be penalized less when each level crosses a clearly different
  governance boundary?
- When should subtree compression become an automatic proposal instead of a
  manual follow-up?

## Proposed Next Step

After this proposal, the next bounded implementation step should be:

- add shape-quality signals to the derived graph-health layer
- log them in run artifacts
- add evaluator penalties for repeated one-child ladders
- emit retrospective subtree rebalance proposals when the signals persist
