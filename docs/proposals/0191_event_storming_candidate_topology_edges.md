# 0191 Event-Storming Candidate Topology Edges

Status: implemented.

## Problem

Real idea candidates produced from event-storming intake could contain useful
candidate nodes but no candidate graph edges. This made pre-SIB topology checks
report every node as orphaned even when the nodes were all derived from the same
product boundary and reviewable as a coherent candidate surface.

The issue appeared during real idea smoke runs: repair answers could resolve
ontology and product/spec gaps, but the repaired candidate graph still looked
topology-empty because the ontology-bound seed emitted no edges.

## Proposal

Generate conservative candidate topology edges in the ontology-bound candidate
graph seed:

```text
Product Boundary --decomposes_to--> Derived Candidate Node
```

The edge is created only between known candidate nodes already emitted by the
seed. It does not infer command ordering, causality, ownership, lifecycle state,
or domain semantics. It only records that each derived candidate node refines
the reviewable product boundary built from the same event-storming intake.

This is an explicit temporary anti-orphan topology layer, not the final
event-storming topology model. The `relation` value is still validated only as a
candidate graph relation string by `candidate_spec_graph.py`; it is not yet
checked against an ontology relation contract. A later slice should add
ontology-backed relation validation before richer command/event/policy edges are
trusted downstream.

Because those edges can make pre-SIB pass without any repair action, the
candidate repair loop also treats a clean pre-SIB pass-through as an explicit
ready no-op repair loop. This prevents the active-candidate pipeline from
replacing the old false orphan blocker with a new `repair_loop_not_ready`
blocker when no repair is required.

## Authority Boundary

This proposal only enriches review-only candidate graph topology.

It does not:

- execute prompt agents;
- infer new product semantics with an LLM;
- mutate canonical specs;
- write Ontology packages or lockfiles;
- accept ontology terms;
- approve candidates;
- create Git branches or commits;
- open pull requests;
- publish read models.

## Acceptance Criteria

- Ontology-bound candidate graph seeds include stable `decomposes_to` edges from
  `candidate-spec.product-boundary` to each derived candidate node.
- Candidate graph building accepts those edges without changing the existing
  `id/from/to/relation` contract.
- Pre-SIB topology metrics no longer mark every generated node as orphaned when
  the candidate graph has boundary decomposition edges.
- A candidate graph with clean pre-SIB readiness and no repair actions produces
  a ready no-op repair loop instead of `repair_review_required`.
- The implementation remains conservative and avoids inferred event ordering or
  causality.
- The proposal text records that this is a temporary flat decomposition layer,
  not ontology-validated event-storming topology.

## Validation

- `tests/test_ontology_bound_candidate_graph_seed.py`
- `tests/test_candidate_spec_graph.py`
- `tests/test_pre_sib_coherence_report.py`
- `tests/test_candidate_repair_loop.py`
