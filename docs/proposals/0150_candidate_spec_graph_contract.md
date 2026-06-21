# 0150 Candidate Spec Graph Contract

## Status

Implemented

## Summary

SpecGraph now has a deterministic, review-only `candidate_spec_graph` artifact
for the idea-to-spec workflow.

The artifact consumes an `idea_event_storming_intake` and structured candidate
graph seed data, then emits a pre-canonical graph containing:

- candidate nodes;
- candidate edges;
- requirements;
- acceptance criteria;
- calibrated claims;
- gaps;
- ontology/domain/context frame inherited from the intake;
- readiness for the future pre-SIB/coherence report.

The output is:

- `runs/candidate_spec_graph.json`.

## Implementation

This slice adds:

- `tools/candidate_spec_graph.py`;
- `make candidate-spec-graph`;
- ready and review-required fixtures;
- regression tests for ready graphs, unready intake, unknown refs, strong claims
  without F/G/R, requirement-to-acceptance-criteria refs, and CLI strict mode.

## Authority Boundary

This proposal does not grant write authority.

It does not:

- execute prompt agents;
- generate candidate graph content from raw intent;
- run pre-SIB/coherence scoring;
- run autonomous repair loops;
- mutate canonical specs;
- write Ontology packages or lockfiles;
- accept ontology terms;
- create Git branches or commits;
- publish a SpecSpace UI surface.

## Validation

- `tests/test_candidate_spec_graph.py::test_candidate_spec_graph_builds_ready_graph`
- `tests/test_candidate_spec_graph.py::test_candidate_spec_graph_blocks_unready_intake`
- `tests/test_candidate_spec_graph.py::test_candidate_spec_graph_rejects_unknown_refs`
- `tests/test_candidate_spec_graph.py::test_candidate_spec_graph_rejects_strong_claim_without_fgr`
- `tests/test_candidate_spec_graph.py::test_candidate_spec_graph_cli_writes_output`

## Follow-ups

- `0151` Pre-SIB/coherence metrics over the candidate graph.
- `0152` Autonomous candidate repair loop.
- SpecSpace idea-to-spec workspace over intake, candidate graph, metrics, and
  repair history.
