# 0153 Candidate Spec Materialization Preview

## Status

Implemented

## Summary

SpecGraph now has a deterministic, review-only candidate spec materialization
preview for the idea-to-spec workflow.

The materializer consumes:

- `candidate_spec_graph`;
- optional `candidate_repair_loop_report`.

It emits:

- local YAML preview files under `runs/materialized_candidate_specs/`;
- `runs/candidate_spec_materialization_report.json`;
- promotion request paths that Platform can pass to
  `graph-repository promotion-request`.

If a repair loop report includes `revised_candidate_graph_preview`, the
materializer uses that preview. Otherwise it uses the candidate graph directly.

## Implementation

This slice adds:

- `tools/candidate_spec_materialization.py`;
- `make candidate-spec-materialization`;
- regression tests for YAML preview generation, authority-boundary rejection,
  CLI output, and strict-mode failure.

The generated YAML preview keeps the candidate state inspectable as spec-shaped
records with requirements, acceptance criteria, claims, gaps, ontology refs, and
source provenance. It is intentionally not treated as accepted canonical graph
truth.

## Authority Boundary

This proposal does not grant write authority.

It does not:

- execute prompt agents;
- mutate candidate source artifacts;
- mutate canonical specs;
- write Ontology packages or lockfiles;
- accept ontology terms;
- create Git branches or commits;
- open pull requests;
- publish a SpecSpace mutation UI.

## Validation

- `tests/test_candidate_spec_materialization.py::test_candidate_spec_materialization_writes_review_yaml`
- `tests/test_candidate_spec_materialization.py::test_candidate_spec_materialization_rejects_authority_expansion`
- `tests/test_candidate_spec_materialization.py::test_candidate_spec_materialization_cli_writes_report_and_files`
- `tests/test_candidate_spec_materialization.py::test_candidate_spec_materialization_strict_cli_exits_nonzero`

## Follow-ups

- Platform executor orchestration that consumes a promotion request and runs the
  existing prepare-worktree, commit-worktree, and open-review steps.
- SpecSpace controlled promotion UI over materialization and promotion request
  reports.
