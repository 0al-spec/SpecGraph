# 0151 Pre-SIB Coherence Report

## Status

Implemented

## Summary

SpecGraph now has a deterministic, review-only pre-SIB/coherence report for
candidate spec graphs.

The report consumes `candidate_spec_graph` and emits:

- structural counts;
- acceptance-criteria coverage;
- ontology coverage;
- connected-node ratio and orphan-node findings;
- duplicate title warnings;
- unresolved gap warnings;
- unsupported strong-claim warnings;
- readiness for the future candidate repair loop.

The output is:

- `runs/pre_sib_coherence_report.json`.

## Implementation

This slice adds:

- `tools/pre_sib_coherence_report.py`;
- `make pre-sib-coherence`;
- ready and review-required fixtures;
- regression tests for ready reports, unready candidate graph, orphan nodes,
  ontology coverage gaps, unsupported strong claims, and CLI strict mode.

## Authority Boundary

This proposal does not grant write authority.

It does not:

- define final SIB formulas;
- execute prompt agents;
- mutate candidate graph artifacts;
- run autonomous repair loops;
- mutate canonical specs;
- write Ontology packages or lockfiles;
- accept ontology terms;
- create Git branches or commits;
- publish a SpecSpace UI surface.

## Validation

- `tests/test_pre_sib_coherence_report.py::test_pre_sib_coherence_report_builds_ready_report`
- `tests/test_pre_sib_coherence_report.py::test_pre_sib_coherence_report_blocks_unready_candidate_graph`
- `tests/test_pre_sib_coherence_report.py::test_pre_sib_coherence_report_detects_orphan_and_ontology_gaps`
- `tests/test_pre_sib_coherence_report.py::test_pre_sib_coherence_report_warns_on_unsupported_strong_claim`
- `tests/test_pre_sib_coherence_report.py::test_pre_sib_coherence_report_cli_writes_output`

## Follow-ups

- `0152` Autonomous candidate repair loop consuming this report.
- SpecSpace idea-to-spec workspace over intake, candidate graph, metrics, and
  repair history.
