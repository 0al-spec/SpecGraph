# 0149 Idea Event-Storming Intake Artifact

## Status

Implemented

## Summary

SpecGraph now has a deterministic, review-only intake artifact for the
idea-to-spec workflow.

The intake converts an operator-provided product idea seed into a typed
event-storming surface:

- actors;
- domain events;
- commands;
- policies;
- external systems;
- constraints;
- risks;
- assumptions;
- vocabulary questions;
- active ontology/domain/context frame;
- context-completion questions when required inputs are missing.

The output is:

- `runs/idea_event_storming_intake.json`.

## Implementation

This slice adds:

- `tools/idea_event_storming_intake.py`;
- `make idea-event-storming-intake`;
- ready and review-required fixtures;
- regression tests for ready intake, missing frame/category findings, unknown
  relationship refs, raw trace filtering, duplicate ids, seed contract metadata,
  malformed relationship lists, singleton optional context normalization, and CLI
  strict mode.

The tool accepts a structured `idea_event_storming_seed` JSON file and emits an
`idea_event_storming_intake` artifact. It digests raw intent text and publishes
only the source ref, digest, and explicit intent summary.

## Authority Boundary

This proposal does not grant write authority.

It does not:

- execute prompt agents;
- infer missing event-storming content with an LLM;
- publish raw intent text, raw prompts, or raw model output;
- create a candidate spec graph;
- mutate canonical specs;
- write Ontology packages or lockfiles;
- accept ontology terms;
- create Git branches or commits;
- publish a SpecSpace UI surface.

## Validation

- `tests/test_idea_event_storming_intake.py::test_idea_event_storming_intake_builds_ready_artifact`
- `tests/test_idea_event_storming_intake.py::test_idea_event_storming_intake_requires_frame_and_core_categories`
- `tests/test_idea_event_storming_intake.py::test_idea_event_storming_intake_rejects_unknown_relationship_refs`
- `tests/test_idea_event_storming_intake.py::test_idea_event_storming_intake_filters_raw_entry_trace_fields`
- `tests/test_idea_event_storming_intake.py::test_idea_event_storming_intake_rejects_duplicate_entry_ids`
- `tests/test_idea_event_storming_intake.py::test_idea_event_storming_intake_validates_seed_contract_metadata`
- `tests/test_idea_event_storming_intake.py::test_idea_event_storming_intake_rejects_malformed_relationship_lists`
- `tests/test_idea_event_storming_intake.py::test_idea_event_storming_intake_preserves_singleton_optional_context`
- `tests/test_idea_event_storming_intake.py::test_idea_event_storming_intake_cli_writes_output`

## Follow-ups

- `0150` Candidate Spec Graph Contract consuming the event-storming intake.
- `0151` Pre-SIB/coherence metrics over the candidate graph.
- `0152` Autonomous candidate repair loop.
- SpecSpace idea-to-spec workspace over intake, candidate graph, metrics, and
  repair history.
