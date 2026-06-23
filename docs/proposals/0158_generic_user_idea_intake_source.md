# 0158 Generic User Idea Intake Source

## Status

Implemented

## Summary

SpecGraph now has a deterministic generic entry point for new product ideas.
Team Decision Log remains fixture/config data; the system-level path is a
generic `user_idea_intake_source` contract.

The source captures:

- product workspace identity;
- root user intent;
- ontology/domain/context hints;
- ontology layer and model applicability defaults;
- event-storming hints: actors, domain events, commands, policies, constraints,
  risks, assumptions, and vocabulary questions.

It emits:

- `runs/idea_event_storming_seed.json`;
- a seed that the existing `idea_event_storming_intake` builder can consume;
- source findings when workspace identity or source contract metadata is
  incomplete;
- authority metadata proving that the source builder is review-only.

## Implementation

This slice adds:

- `tools/user_idea_intake_source.py`;
- `make user-idea-intake-source`;
- `make generic-idea-intake`;
- generic fixtures under `tests/fixtures/user_idea_intake/`;
- regression tests for ready seed generation, downstream intake compatibility,
  context-completion behavior, strict invalid-source handling, and raw trace
  filtering.

The default fixture uses `support-triage-log` to prove the entry point is not
hardcoded to Team Decision Log. A different product idea can replace the source
JSON without a new tool or Make target.

The downstream `idea_event_storming_intake` builder also blocks seeds whose
`source_intake.findings` contain `review_required` entries. This prevents an
invalid source contract or invalid workspace metadata from becoming
`ready_for_candidate_graph` merely because the event-storming hints are
otherwise complete.

The deterministic chain is:

```text
user_idea_intake_source
  -> idea_event_storming_seed
  -> idea_event_storming_intake
```

`generic-idea-intake` runs both steps locally.

## Authority Boundary

This proposal does not grant write authority.

It does not:

- execute prompt agents;
- infer a domain model with an LLM;
- generate a candidate spec graph;
- mutate candidate source artifacts through SpecSpace;
- mutate canonical SpecGraph specs;
- write Ontology packages or lockfiles;
- accept ontology terms;
- create Git branches or commits;
- open pull requests;
- publish read models;
- add SpecSpace mutation UI.

Raw intent text remains in the local seed for the next deterministic builder,
but the published intake artifact digests it and exposes only public-safe
summary/ref metadata. Raw prompt, model-output, and operator-note trace fields
are filtered from event-storming hints.

## Validation

- `tests/test_user_idea_intake_source.py::test_user_idea_intake_source_builds_generic_event_storming_seed`
- `tests/test_user_idea_intake_source.py::test_user_idea_intake_source_feeds_existing_intake_contract`
- `tests/test_user_idea_intake_source.py::test_user_idea_intake_source_review_required_flows_to_context_questions`
- `tests/test_user_idea_intake_source.py::test_user_idea_intake_source_strict_cli_rejects_invalid_source`
- `tests/test_user_idea_intake_source.py::test_user_idea_intake_source_findings_block_downstream_intake`
- `tests/test_user_idea_intake_source.py::test_user_idea_intake_source_cli_writes_seed`

## Follow-ups

- Candidate graph seed generation still needs a generic prompt-side or
  deterministic authoring path. This proposal only removes the product-specific
  intake-source step.
- SpecSpace can later provide an event-storming capture surface that writes the
  same `user_idea_intake_source` contract.
