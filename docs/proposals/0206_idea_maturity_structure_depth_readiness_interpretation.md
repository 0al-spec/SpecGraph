# 0206 Idea Maturity Structure Depth Readiness Interpretation

## Status

Draft / producer-side readiness interpretation slice.

## Summary

Proposal `0205` added Metrics-owned raw structural depth observations under
`groups.candidate_structure_depth`. Those counts are intentionally objective:
zero actors, domain events, workflow edges, requirements, or acceptance criteria
are valid observations, not Metrics-level failures.

SpecGraph still needs to help downstream product surfaces explain what shallow
structure means for a candidate narrative. That interpretation belongs in
SpecGraph's `readiness_explainers`, not in the Metrics RFC as a score, gate, or
threshold.

## Decision

SpecGraph should emit `readiness_explainers[]` derived from
`groups.candidate_structure_depth` when a current candidate graph exists and a
structural count is zero.

The explainers:

- use `proposal_id: "0206"`;
- use `source: "idea_maturity_metrics_report.groups.candidate_structure_depth"`;
- use `blocks: ["pre_sib_review"]`;
- point evidence refs at the corresponding
  `runs/idea_maturity_metrics_report.json#groups.candidate_structure_depth.*`
  metric;
- explain the operator-facing interpretation and next review step.

## Authority Boundary

This slice is interpretation-only.

It does not:

- add a new metric id;
- add a composite score;
- change Idea Maturity status calculation;
- change Pre-SIB, repair, approval, promotion, Git, or publication gates;
- approve candidates;
- mutate candidate or canonical specs;
- write Ontology packages or lockfiles;
- accept ontology terms;
- execute prompt agents;
- create Git branches, commits, or pull requests;
- publish read models.

## Metrics Boundary

Metrics remains the source of truth for the raw
`candidate_structure_depth` schema and validator. Metrics already defines the
existing non-authority `pre_sib_review` readiness block, but Metrics does not
define thresholds or next actions for the structural counts.

## Acceptance Criteria

- Shallow structural counts produce `readiness_explainers[]` with
  `proposal_id: "0206"`.
- The explainers use `pre_sib_review` plus candidate-structure `kind`/`source`,
  not approval, promotion, Git, or publication blocks.
- Shallow structural counts do not create policy findings and do not make the
  report `blocked` by themselves.
- Rich structural counts do not emit structural-depth readiness explainers.
