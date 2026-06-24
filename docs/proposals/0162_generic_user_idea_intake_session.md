# 0162 Generic User Idea Intake Session

## Status

Implemented

## Summary

The `product_idea_to_spec` path now has a deterministic intake-session layer
before the prepared `user_idea_intake_source` contract.

Earlier slices made the active product workspace runner generic, but the normal
input still had to be a fully prepared `user_idea_intake_source` JSON document.
That was useful for fixtures, but it was too polished for the first user-facing
step. A user or CLI agent needs a smaller boundary: start from a raw idea plus
whatever context is already known, then either emit a valid intake source or
return concrete clarification questions.

This slice adds `user_idea_intake_session` as that boundary.

## Implementation

The implemented surface is:

- `tools/user_idea_intake_session.py`;
- `make user-idea-intake-session`;
- `make generic-idea-intake-session`;
- `runs/user_idea_intake_session.json`;
- `runs/user_idea_intake_source.json` when the session is ready;
- `make product-workspace-active-candidate`, which now runs the intake-session
  step before the existing `user_idea_intake_source` builder in generated mode.

The session input contract is
`specgraph.idea-to-spec.user-idea-raw-input.v0.1`. It may contain raw idea text,
workspace hints, active ontology/domain/context/layer/applicability hints, and
event-storming hints. The builder is deterministic and does not call a prompt
agent.

When the input has enough context, the session emits a prepared
`user_idea_intake_source` that can feed the existing chain:

```text
user_idea_raw_input
  -> user_idea_intake_session
  -> user_idea_intake_source
  -> idea_event_storming_seed
  -> idea_event_storming_intake
```

When context is missing, the session stays in `needs_clarification` and emits
public-safe `clarification_questions` instead of writing a source artifact.

## Semantics

The session requires explicit enough context for raw inputs:

- intent text or summary;
- stable workspace identity or a derivable display name;
- ontology refs;
- ontology layer refs;
- domain refs;
- context refs;
- model applicability refs;
- core event-storming categories: actors, domain events, commands, and
  constraints.

Missing values become review findings and clarification questions. The builder
may show deterministic preview defaults for domain/context refs, but those
defaults do not make a raw session ready without explicit confirmation.

Prepared `user_idea_intake_source` inputs remain accepted for compatibility.
That preserves the proposal `0158` path and old fixtures while making raw
intake sessions the normal generated product-workspace path.

## Authority Boundary

This proposal does not grant write authority.

It does not:

- execute prompt agents;
- infer missing product semantics with an LLM;
- mutate candidate source artifacts through SpecSpace;
- mutate canonical SpecGraph specs;
- write Ontology packages or lockfiles;
- accept ontology terms;
- approve candidate graphs;
- create Git branches or commits;
- open pull requests;
- publish read models;
- add SpecSpace mutation UI.

The output remains a review-only handoff into the existing idea-to-spec artifact
chain.

## Validation

- `tests/test_user_idea_intake_session.py`
- `tests/test_user_idea_intake_source.py`
- `tests/test_product_workspace_active_candidate_runner.py`
- `make user-idea-intake-session`
- `make product-workspace-active-candidate`

## Follow-Ups

- Add an actual CLI or agent conversation wrapper that fills
  `user_idea_raw_input` from an operator interview.
- Make ontology-gap repair suggestions actionable from the generated candidate
  graph and pre-SIB reports.
- Surface intake-session readiness and clarification questions in SpecSpace.
