# 0160 Generic Active Idea-To-Spec Runner

## Status

Implemented

## Summary

SpecGraph now treats the active `product_idea_to_spec` runner as a generic
pipeline from `user_idea_intake_source` to active candidate artifacts.

Before this slice, `make product-workspace-active-candidate` could build the
candidate chain, but the default entry point still started from a prepared
`idea_event_storming_seed` fixture and the active candidate config carried
product identity explicitly. That made Team Decision Log too easy to treat as
system logic instead of workspace data.

This slice changes the default active path to:

```text
user_idea_intake_source
  -> idea_event_storming_seed
  -> idea_event_storming_intake
  -> ontology_bound_candidate_graph_seed
  -> candidate_spec_graph
  -> pre-SIB/coherence report
  -> candidate_repair_loop_report
  -> candidate_spec_materialization_report
  -> idea_to_spec_promotion_gate
  -> active_idea_to_spec_candidate
```

Team Decision Log remains the default example workspace data for the product
pilot. A different product idea can replace the source JSON without adding a
product-specific tool, Make target, or active candidate config.

## Implementation

This slice adds:

- `PRODUCT_WORKSPACE_IDEA_SOURCE` as the default first input to
  `make product-workspace-active-candidate`;
- generation of `runs/idea_event_storming_seed.json` before event-storming
  intake when the target uses the default generated seed path;
- a generic active candidate config fixture that contains only artifact refs;
- Team Decision Log as a `user_idea_intake_source` data fixture rather than a
  prepared seed fixture;
- public-safe `source_intake.workspace` metadata on
  `idea_event_storming_intake`;
- active candidate metadata derivation from the generated intake artifact;
- regression coverage proving that the full target can build a non-Team
  Decision Log product candidate from `tests/fixtures/user_idea_intake/source_ready.json`.

The old seed-input path remains supported. Operators may still pass
`PRODUCT_WORKSPACE_INTAKE_SOURCE=<seed.json>` when they already have a prepared
event-storming seed.

## Semantics

The active runner now proves that the chain is generic, not that every product
idea is immediately promotable. If generated pre-SIB or promotion-gate findings
require owner context, the runner still emits
`runs/active_idea_to_spec_candidate.json` with `active_candidate_review_required`
and public-safe blockers.

This preserves the intended pre-SIB behavior:

- pipeline execution is not the same as candidate approval;
- unresolved ontology gaps remain visible instead of being auto-accepted;
- promotion readiness is granted only by the existing promotion gate.

## Authority Boundary

This proposal does not grant write authority.

It does not:

- execute prompt agents;
- infer a missing domain model with an LLM;
- mutate canonical SpecGraph specs;
- write Ontology packages or lockfiles;
- accept ontology terms;
- approve candidate graphs;
- create Git branches or commits;
- open pull requests;
- publish read models;
- add SpecSpace mutation UI.

All outputs remain review-only until the existing approval and Git Service
promotion boundaries accept them.

## Validation

- `tests/test_active_idea_to_spec_candidate_source.py::test_active_candidate_source_derives_candidate_metadata_from_intake`
- `tests/test_product_workspace_active_candidate_runner.py::test_product_workspace_active_candidate_runs_from_generic_user_idea_source`
- `make product-workspace-active-candidate`

## Follow-Ups

- Add prompt-side/event-storming capture that produces
  `user_idea_intake_source` from an operator conversation.
- Make repair suggestions more actionable for ontology gaps and promotion
  blockers.
- Continue Git Service promotion/read-model publication work after candidate
  approval.
