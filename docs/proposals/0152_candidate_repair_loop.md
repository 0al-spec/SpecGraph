# 0152 Candidate Repair Loop

## Status

Implemented

## Summary

SpecGraph now has a deterministic, review-only candidate repair loop preview for
the idea-to-spec workflow.

The report consumes:

- `candidate_spec_graph`;
- `pre_sib_coherence_report`.

It emits:

- repair actions;
- a revised candidate graph preview;
- metric delta projection;
- context-required repair warnings;
- readiness for the future SpecSpace idea-to-spec workspace bundle.

The output is:

- `runs/candidate_repair_loop_report.json`.

## Implementation

This slice adds:

- `tools/candidate_repair_loop.py`;
- `make candidate-repair-loop`;
- repairable and invalid-input fixtures;
- regression tests for repair action generation, preview application, metric
  delta projection, mismatched pre-SIB report rejection, unhandled blocker
  preservation, output-scoped preview refs, input-contract rejection, and CLI
  strict mode.

The deterministic repair preview can:

- connect orphan candidate nodes to the product/root node;
- add placeholder acceptance criteria for uncovered requirements;
- downgrade unsupported low-reliability strong claims to hypotheses;
- record ontology-selection and unresolved-gap work as context-required actions.

## Authority Boundary

This proposal does not grant write authority.

It does not:

- execute prompt agents;
- mutate the source candidate graph artifact;
- mutate canonical specs;
- write Ontology packages or lockfiles;
- accept ontology terms;
- create Git branches or commits;
- publish a SpecSpace UI surface.

## Validation

- `tests/test_candidate_repair_loop.py::test_candidate_repair_loop_builds_repair_preview`
- `tests/test_candidate_repair_loop.py::test_candidate_repair_loop_preview_applies_safe_repairs`
- `tests/test_candidate_repair_loop.py::test_candidate_repair_loop_downgrades_strength_marker`
- `tests/test_candidate_repair_loop.py::test_candidate_repair_loop_projects_metric_delta`
- `tests/test_candidate_repair_loop.py::test_candidate_repair_loop_rejects_mismatched_pre_sib_report`
- `tests/test_candidate_repair_loop.py::test_candidate_repair_loop_preserves_unhandled_pre_sib_blockers`
- `tests/test_candidate_repair_loop.py::test_candidate_repair_loop_rejects_wrong_pre_sib_contract`
- `tests/test_candidate_repair_loop.py::test_candidate_repair_loop_preview_ref_uses_output_path`
- `tests/test_candidate_repair_loop.py::test_candidate_repair_loop_cli_writes_output`

## Follow-ups

- SpecSpace idea-to-spec workspace over intake, candidate graph, pre-SIB report,
  and repair loop history.
- Graph Repository Service / materialization gate after review-ready candidate
  graph state exists.
