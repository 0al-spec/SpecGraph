# 0207 Depth-Driven Clarification Loop

## Status

Draft / producer-side clarification slice.

## Summary

Metrics-owned `groups.candidate_structure_depth` gives objective structural
telemetry for actors, commands, domain events, policies, constraints, workflow
edges, requirements, and acceptance criteria. Proposal `0206` turns shallow
counts into readiness explainers, but it does not ask the operator for
structured follow-up context.

This slice lets SpecGraph turn shallow structural depth observations into
ordinary idea-to-spec clarification requests. The requests reuse the existing
clarification answer and rerun overlay contracts, so accepted answers can add
event-storming hints during review-only rerun.

## Decision

`tools/idea_to_spec_clarification_requests.py` may accept
`--idea-maturity <idea_maturity_metrics_report.json>`. When the report contains
`groups.candidate_structure_depth`, zero structural counts emit
`review_required` clarification requests:

- missing actors -> `target_ref: event_storming_hints.actors`;
- missing commands -> `target_ref: event_storming_hints.commands`;
- missing domain events -> `target_ref: event_storming_hints.domain_events`;
- missing policies -> `target_ref: event_storming_hints.policies`;
- missing constraints -> `target_ref: event_storming_hints.constraints`;
- zero workflow edges with existing commands and events -> a workflow topology
  request targeting command hints.

The requests keep `suggested_actions: ["answer_question", "defer_candidate"]`
and `suggested_answer_shape: "event_storming_entry[]"` so existing answer
authoring and SpecSpace-owned answer state can validate them.

`tools/idea_to_spec_answer_rerun_input.py` should map accepted answers with
`target_ref: event_storming_hints.<category>` and `value.entries[]` into
`rerun_input_overlay.intake_overlay.event_storming_hints`.

## Authority Boundary

This slice is review-only. It does not:

- change Metrics schemas or validator semantics;
- create a composite quality score;
- turn structural depth into a promotion gate;
- approve candidates;
- mutate candidate or canonical specs;
- write Ontology packages or lockfiles;
- accept ontology terms;
- execute prompt agents;
- create Git branches, commits, or pull requests;
- publish read models.

## Acceptance Criteria

- Missing `candidate_structure_depth` does not create fake clarification
  requests.
- Zero actor/event/policy/constraint counts create `review_required` structured
  event-storming requests, not blocking gates.
- Zero workflow-edge count creates a workflow-topology request only when
  commands and domain events already exist.
- Accepted typed `entries[]` answers feed the existing review-only rerun overlay
  as event-storming hints.
- Metrics remains the objective telemetry layer; interpretation and prompts stay
  in SpecGraph/SpecSpace producer and consumer layers.
