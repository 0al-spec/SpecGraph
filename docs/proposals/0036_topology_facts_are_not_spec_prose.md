# Topology Facts Are Not Spec Prose

## Status

Initial runtime slice implemented

Runtime realization:

- `tools/supervisor.py` now tells child executors that graph topology already
  lives in canonical metadata such as `depends_on`, `refines`, `inputs`, and
  `outputs`.
- `tests/test_supervisor.py` covers the prompt guardrail for ordinary
  refinement and child materialization.
- The SG-SPEC-0026 reflective/proposal branch begins a cleanup pass toward
  domain-first prose instead of topology self-description.

## Problem

SpecGraph has reached a failure mode where some valid spec nodes mostly explain
their own graph placement:

- which spec is the child of which other spec;
- which edge is direct or indirect;
- which route is delegated through another spec;
- which handoff segment exists between neighboring spec IDs.

Those facts are already present in the graph structure.

When they become the main prose of a spec, the graph starts narrating its own
decomposition mechanics instead of the system meaning it is supposed to model.

The result is especially visible when a subtree is read as a "book": a branch
such as reflective execution and proposal/split mechanics should read as a
coherent story about runtime readiness, continuation, proposals, and split
lifecycle. It should not read as a log of which spec node routes to which other
spec node.

## Goals

- Make topology facts explicit metadata, not the primary prose payload.
- Keep spec prose domain-first: capability, invariant, runtime behavior,
  review boundary, or evidence expectation.
- Discourage edge-only, gateway-segment-only, and handoff-segment-only child
  materialization.
- Prefer rewrite, merge, regrouping, or proposal/refactor pressure when a child
  would only verbalize existing topology.
- Preserve legitimate boundary specs when they define a real system-facing
  contract.

## Non-Goals

- Removing `depends_on`, `refines`, `inputs`, or `outputs`.
- Banning all boundary, gateway, or handoff specs.
- Hiding topology from reviewers or viewers.
- Rewriting the whole graph in one pass.
- Making every legacy topology-heavy node immediately invalid.

## Core Proposal

Spec prose should not primarily restate graph topology.

Canonical topology already exists in structured fields:

- `depends_on`
- `refines`
- `inputs`
- `outputs`
- lineage and supersession fields
- derived graph-health and trace artifacts

A spec may reference neighboring spec IDs when needed, but its main acceptance
criteria and specification body should explain the system-facing role that the
topology supports.

The guiding question becomes:

> If the graph edges were hidden, could a reader still understand what system
> responsibility this node defines?

If the answer is no, the node is probably topology prose rather than a useful
specification.

## Decision Rule

Before creating or preserving a child spec, supervisor and reviewers should ask:

1. Does this child introduce a distinct system-facing role, composed function,
   policy, protocol, capability, or runtime/review-observable invariant?
2. Does it explain something that cannot be recovered from `depends_on`,
   `refines`, `inputs`, `outputs`, or derived graph artifacts?
3. Would deleting or merging the child erase meaningful system behavior, or only
   collapse an edge label?

If the child only names an edge, route, gateway segment, handoff segment, or
delegation path, the preferred action is not further decomposition.

Preferred actions are:

- rewrite the parent in domain-first prose;
- merge the bookkeeping slice back into the nearest meaningful role;
- regroup sibling concerns under a clearer aggregate;
- emit proposal/refactor pressure instead of canonicalizing a new node.

## Boundary Specs Still Allowed

Boundary specs remain valid when they define a real contract, such as:

- a review gate with explicit acceptance behavior;
- a protocol transition with allowed states;
- a trust boundary with authorization or audit consequences;
- a runtime envelope that changes execution behavior;
- an evidence boundary that changes how claims are verified.

They are weak when they only say that one spec sits between two other specs.

## Supervisor Behavior

### Prompt Guidance

Child executor prompts should state that topology already lives in graph
metadata. The executor should avoid making topology self-description the main
spec prose.

### Child Materialization

Child materialization should require a separately nameable role, composed
function, or observable invariant.

If the proposed child is merely an edge or handoff segment, supervisor should
prefer rewrite/merge/regrouping or proposal pressure.

### Refactor Interpretation

When graph-health reports `role_obscured_node` or `bookkeeping_only_node`, the
first interpretation should be semantic readability loss, not simply a request
for more children.

### Book Projection

A bounded subtree should support a compact book-like projection:

- headings should read as system responsibilities;
- IDs should act as cross-references;
- topology should support the story rather than become the story.

## Relationship to Existing Work

### Proposal 0017

[0017_role_first_semantic_bias_for_supervisor.md](/Users/egor/Development/GitHub/0AL/SpecGraph/docs/proposals/0017_role_first_semantic_bias_for_supervisor.md)
defines role-first semantic bias and `bookkeeping_only_node` pressure.

This proposal sharpens that rule for the specific case where the prose mostly
verbalizes graph topology.

### SG-SPEC-0049

[SG-SPEC-0049.yaml](/Users/egor/Development/GitHub/0AL/SpecGraph/specs/nodes/SG-SPEC-0049.yaml)
already defines subtree-shape and bookkeeping-drift signals.

This proposal gives those signals a clearer operator interpretation: topology
pressure should often cause rewrite or merge, not another canonical child.

## Acceptance Criteria

- Supervisor prompts explicitly say that topology facts are already represented
  by graph metadata.
- Child materialization guidance rejects children whose main purpose is
  topology verbalization.
- The SG-SPEC-0026 reflective/proposal branch starts moving toward domain-first
  prose.
- Future graph-health or proposal surfaces can point to this proposal when
  recommending `merge_bookkeeping_slice`, `rewrite_node_role_boundary`, or
  similar actions.

## Runtime Realization Path

Phase 1:

- Add prompt guidance and tests.
- Remove the current `SG-SPEC-0057` topology-only child from the open branch.
- Refactor the nearby reflective/proposal subtree prose toward domain-first
  wording.

Phase 2:

- Make graph-health recommendations cite this proposal for topology prose
  pressure.
- Add viewer/backlog projection fields that distinguish topology facts from
  domain prose gaps.

Phase 3:

- Consider a soft validator finding for topology-prose drift after enough
  legacy cleanup has happened.
