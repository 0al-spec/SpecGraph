# Supervisor Problem Diagnosis and Recovery Planner Source Draft

## Source Context

Recent supervisor work exposed a recurring pattern: the supervisor can often
find the right semantic pressure, but the surrounding control layer still needs
operator engineering to classify failures, choose a safe recovery path, and
prevent the same failure from returning.

Concrete examples include:

- quota or provider failures that leave runtime residue in canonical spec
  metadata;
- `split_required` outcomes caused by rejected candidates rather than already
  oversized canonical content;
- split proposal application that can create false atomicity violations when a
  cluster parent already has declared member dependencies;
- newly materialized child specs that need deterministic trace and evidence
  contracts before the graph can return to steady state;
- stale proposal or backlog pressure after a canonical repair has already
  landed.

The operator intent is to make supervisor work more deterministic, autonomous,
and focused on problem detection and solving.

## Operator Intent

Add a proposal for a first-class problem diagnosis and deterministic recovery
planning layer around the supervisor.

The desired direction is:

```text
observe -> diagnose -> choose deterministic recovery or one bounded LLM run
        -> validate -> stop at PR/review boundary
```

The system should not simply run the supervisor repeatedly. It should classify
what happened, name the root cause, pick an allowed repair action when one is
safe, and stop when governance or human review is required.

## Desired Outcome

Define a proposal for:

- a typed `supervisor_problem_diagnosis` artifact;
- a small problem vocabulary for common runtime, graph, and process failures;
- a deterministic recovery planner that maps diagnosed problems to safe next
  actions;
- hard stops for ontology, policy, authority, repeated failure, or unsafe
  canonical mutation;
- a problem-solving report that records root cause, prevention, validation, and
  remaining gaps.

## Boundary

This proposal should not implement a full autonomous loop yet. It should not
grant the supervisor new governance authority, merge PRs, bypass human review,
or silently mutate canonical specs.

Runtime implementation, SpecSpace UI, and hosted factory orchestration should
come later as separate realization steps.
