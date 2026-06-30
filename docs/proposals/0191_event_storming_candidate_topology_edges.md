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
- The implementation remains conservative and avoids inferred event ordering or
  causality.

## Validation

- `tests/test_ontology_bound_candidate_graph_seed.py`
- `tests/test_candidate_spec_graph.py`
- `tests/test_pre_sib_coherence_report.py`
