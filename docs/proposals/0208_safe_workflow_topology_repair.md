# 0208 Safe Workflow Topology Repair

## Status

Draft / producer-side topology repair slice.

## Summary

Proposal `0207` lets shallow `candidate_structure_depth` observations ask for
missing event-storming entries, but it intentionally leaves
`workflow_edge_count = 0` diagnostic-only because the rerun overlay only
appended entries.

This slice adds a bounded, typed relation overlay for workflow topology repair.
It lets accepted clarification answers connect already-published
event-storming entries through review-only relations such as actor-command,
command-event, event-policy, event-constraint, policy-command, and
constraint-command links.

## Decision

When `groups.candidate_structure_depth.workflow_edge_count = 0` and the
maturity report has a loaded event-storming intake source with enough existing
entries to link, `tools/idea_to_spec_clarification_requests.py` may emit:

- `kind: workflow_topology_gap`;
- `target_ref: event_storming_hints.workflow_relations`;
- `suggested_answer_shape: event_storming_relation[]`;
- `suggested_actions: ["answer_question", "defer_candidate"]`.

Accepted answers feed `tools/idea_to_spec_answer_rerun_input.py` as:

```json
{
  "intake_overlay": {
    "event_storming_hints": [
      {
        "target_ref": "event_storming_hints.workflow_relations",
        "value": {
          "workflow_relations": [
            {
              "relation": "command_emits_event",
              "source_ref": "command.record-item",
              "target_ref": "event.item-recorded"
            }
          ]
        }
      }
    ]
  }
}
```

`tools/idea_to_spec_rerun_preview.py` validates every relation against the
current event-storming preview before applying it:

- `actor_triggers_command`: actor -> command;
- `command_emits_event`: command -> domain event;
- `event_informs_policy`: domain event -> policy;
- `event_informs_constraint`: domain event -> constraint;
- `constraint_applies_to_command`: constraint -> command;
- `policy_applies_to_command`: policy -> command.

Unknown, missing, stale, or wrong-kind refs become `review_required` findings.
Valid relation hints patch only event-storming relation fields
(`actor_refs`, `produces_event_refs`, `trigger_event_refs`, `command_refs`) and
emit `workflow_topology_preview.workflow_edges`.

`tools/idea_to_spec_rerun_materialization.py` may copy validated workflow edges
into the review-only `candidate_graph_preview` when every edge has
`review_only: true` and `materialization_dependency: false`.

## Authority Boundary

This slice is review-only. It does not:

- change Metrics schemas or validator semantics;
- create a structural-depth score;
- turn workflow topology into a promotion, approval, or Pre-SIB gate;
- infer fuzzy topology links;
- mutate event-storming intake source artifacts;
- mutate candidate or canonical specs;
- write Ontology packages or lockfiles;
- accept ontology terms;
- execute prompt agents;
- create Git branches, commits, or pull requests;
- publish read models.

Workflow topology edges are product-review evidence. They must not become YAML
`depends_on` or implementation dependencies.

## Acceptance Criteria

- Zero workflow-edge count can create one review-required topology
  clarification request only when existing entries can be linked.
- Accepted `relations[]` answers are preserved in the rerun input overlay.
- Rerun preview rejects unknown relations, missing refs, and wrong source/target
  kinds.
- Rerun preview patches relation fields only after validation.
- Rerun preview emits review-only workflow topology edges.
- Rerun materialization copies only review-only, non-dependency workflow edges
  into the candidate graph preview.
- Metrics remains objective telemetry; topology repair is producer/consumer
  behavior.
