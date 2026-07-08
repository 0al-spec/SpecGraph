# 0205 Idea Maturity Structural Depth Observations

## Status

Draft / maturity telemetry contract slice.

## Summary

Idea Maturity already reports lifecycle readiness, repair closure, ontology
grounding, promotion readiness, and publication state. Product demo depth also
proved that UI-started demos need actors, domain events, workflow topology,
requirements, acceptance criteria, and candidate overview evidence before they
are convincing.

Those structural observations should not live only in a separate demo report.
They belong in the Metrics-owned Idea Maturity contract as raw observations so
SpecSpace can explain candidate depth without inventing another quality score.

## Decision

SpecGraph should emit `groups.candidate_structure_depth` in
`runs/idea_maturity_metrics_report.json`.

The group contains:

- `actor_count`;
- `command_count`;
- `domain_event_count`;
- `policy_count`;
- `constraint_count`;
- `topology_edge_count`;
- `workflow_edge_count`;
- `requirement_count`;
- `acceptance_criteria_count`.

The event-storming counts come from `idea_event_storming_intake.json`. Candidate
graph counts come from `repaired_candidate_spec_graph.json` when present,
otherwise from `candidate_spec_graph.json`.

## Authority Boundary

This slice is telemetry-only.

It does not:

- replace the product demo depth report;
- introduce a composite maturity score;
- approve candidates;
- mutate candidate or canonical specs;
- write Ontology packages or lockfiles;
- accept ontology terms;
- execute prompt agents;
- create Git branches, commits, or pull requests;
- publish read models.

## Downstream Contract

Metrics remains the source of truth for the schema and validator. SpecGraph is
only a producer of the report. SpecSpace can consume the group as a diagnostic
surface for candidate depth, and Platform may summarize it as report-only
telemetry, but existing repair, approval, and promotion gates remain
authoritative.

## Acceptance Criteria

- `idea_maturity_metrics_report.json` includes
  `groups.candidate_structure_depth`.
- The group validates against the Metrics RFC/schema.
- Repaired candidate graph depth is preferred when repaired artifacts exist.
- Missing event-storming or candidate graph structure reports zero counts
  instead of failing report generation.
- Product demo depth remains a separate strict demo diagnostic, not a promotion
  gate.
