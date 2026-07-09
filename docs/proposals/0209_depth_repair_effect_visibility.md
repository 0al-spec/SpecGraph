# 0209 Depth Repair Effect Visibility

## Status

Draft / producer-side repair-effect visibility slice.

## Summary

Proposals `0205` through `0208` made structural depth observable, interpretable,
actionable through clarification requests, and repairable through safe
event-storming and workflow-topology hints. The remaining gap is visibility:
after a rerun, downstream surfaces can see final `candidate_structure_depth`
counts, but they cannot easily explain what changed because of the accepted
depth repair answers.

This slice adds a review-only `structural_depth_delta` surface to the existing
rerun preview/materialization artifacts. It records before/after structural
counts, added event-storming entries, added workflow relations, remaining
shallow dimensions, and a compact effect status.

## Decision

`tools/idea_to_spec_rerun_preview.py` emits:

```json
{
  "rerun_preview": {
    "structural_depth_delta": {
      "proposal_id": "0209",
      "status": "improved",
      "before": {
        "actor_count": 0,
        "workflow_edge_count": 0
      },
      "after": {
        "actor_count": 1,
        "workflow_edge_count": 3
      },
      "delta": {
        "actor_count": 1,
        "workflow_edge_count": 3
      },
      "added_event_storming_entry_refs": {
        "actors": ["actor.household-member"]
      },
      "added_workflow_relation_count": 3,
      "remaining_shallow_dimensions": ["constraint_count"],
      "review_only": true,
      "canonical_mutations_allowed": false,
      "materialization_dependency": false
    }
  }
}
```

`tools/idea_to_spec_rerun_materialization.py` preserves the effect in
`materialization_preview.delta.structural_depth_delta` and recomputes graph-side
after counts from the actual `candidate_graph_preview`.

Valid statuses are:

- `resolved`: previously shallow structural dimensions are now non-zero;
- `improved`: at least one structural dimension increased, but some dimensions
  may still be shallow;
- `still_shallow`: no measured improvement and at least one dimension is still
  zero;
- `unchanged`: no measured improvement and no shallow dimensions remain;
- `not_measured`: the rerun/materialization was not ready enough to produce a
  trustworthy delta.

`tools/idea_maturity_metrics_report.py` may reference this delta from
producer-side readiness explainers, but it does not add a new Metrics field,
score, status, or gate.

## Authority Boundary

This slice is report-only and review-only. It does not:

- change Metrics schemas or validator semantics;
- add a structural-depth score;
- change Idea Maturity status semantics;
- change repair, Pre-SIB, candidate approval, promotion, Git, or publication
  gates;
- mutate event-storming intake source artifacts;
- mutate candidate or canonical specs;
- write Ontology packages or lockfiles;
- accept ontology terms;
- execute prompt agents;
- create Git branches, commits, or pull requests;
- publish read models.

Workflow topology remains product-review evidence. Structural depth deltas must
not become YAML `depends_on`, implementation dependencies, or promotion
authority.

## Acceptance Criteria

- Rerun preview emits `structural_depth_delta` for event-storming and workflow
  topology repair answers.
- Rerun materialization preserves `structural_depth_delta` in its existing
  review-only delta and recomputes graph-side after counts from the materialized
  candidate graph preview.
- Failed or unready materialization reports `status: "not_measured"` instead of
  implying depth was unchanged.
- Idea Maturity readiness explainers can cite the structural depth delta as
  evidence without changing Metrics counts, status, or gate semantics.
- Downstream consumers can show what improved, what was added, and which shallow
  dimensions remain without gaining execution or mutation authority.
