# 0191 Event-Storming Candidate Topology Edges

Status: implemented.

## Problem

Real idea candidates produced from event-storming intake could contain useful
candidate nodes but no candidate graph edges. This made pre-SIB topology checks
report every node as orphaned even when the nodes were all derived from the same
product boundary and reviewable as a coherent candidate surface.

## Proposal

Generate conservative candidate topology edges in the ontology-bound candidate
graph seed:

```text
Product Boundary --decomposes_to--> Derived Candidate Node
```

The edge is created only between known candidate nodes already emitted by the
seed. It does not infer command ordering, causality, ownership, lifecycle state,
or domain semantics.

This is an explicit temporary anti-orphan topology layer, not the final
event-storming topology model. The `relation` value is still validated only as a
candidate graph relation string by `candidate_spec_graph.py`; it is not yet
checked against an ontology relation contract.

The candidate repair loop also treats clean pre-SIB pass-through as a ready
no-op repair loop, so generated topology does not create a new
`repair_loop_not_ready` blocker when no repair action is needed.

## Authority Boundary

This proposal only enriches review-only candidate graph topology. It does not
mutate canonical specs, write Ontology packages, accept ontology terms, approve
candidates, create Git branches, open pull requests, or publish read models.

## Acceptance Criteria

- Seeds include stable `decomposes_to` edges from product boundary to derived
  candidate nodes.
- Candidate graph building accepts those edges.
- Pre-SIB topology metrics no longer report all generated nodes as orphaned.
- Clean pre-SIB pass-through produces a ready no-op repair loop.
- The proposal text records that this is a temporary flat decomposition layer,
  not ontology-validated event-storming topology.

## Validation

- `tests/test_ontology_bound_candidate_graph_seed.py`
- `tests/test_candidate_spec_graph.py`
- `tests/test_pre_sib_coherence_report.py`
- `tests/test_candidate_repair_loop.py`
