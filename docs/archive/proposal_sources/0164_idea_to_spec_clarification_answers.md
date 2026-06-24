# 0164 Idea-To-Spec Clarification Answers

## Status

Implemented

## Summary

The product `idea-to-spec` path now has a typed answer contract for
clarification requests.

Proposal `0163` made blockers and review work explicit through
`idea_to_spec_clarification_requests`. This slice adds the next boundary:
answers can be validated against those request ids without mutating the
candidate graph, canonical specs, or ontology packages.

## Implementation

The implemented surface is:

- `tools/idea_to_spec_clarification_answers.py`;
- `make idea-to-spec-clarification-answers`;
- `runs/idea_to_spec_clarification_answers.json`;
- fixture answer sets for contract validation;
- regression tests for ready answers, unknown requests, disallowed answer kinds,
  unsupported authority, and CLI output.

The input answer set uses:

```json
{
  "artifact_kind": "idea_to_spec_clarification_answer_set",
  "schema_version": 1,
  "contract_ref": "specgraph.idea-to-spec.clarification-answer-set.v0.1",
  "answers": []
}
```

Each answer must reference an existing clarification request and use an
`answer_kind` that is allowed by that request's `suggested_actions`.

## Semantics

The report validates:

- request id exists;
- answer kind is allowed for the request;
- authority is explicit and supported;
- duplicate answers for one request are rejected;
- blocking requests are considered resolved only by accepted answers.

Accepted answer statuses are:

- `accepted_for_candidate`;
- `accepted_for_review`.

Other statuses such as `proposed`, `rejected`, and `deferred` are allowed as
records, but they do not resolve blocking requests.

The output includes:

- normalized public-safe answers;
- request snapshots for review;
- unresolved blocking request list;
- readiness for a future deterministic candidate rerun.

## Authority Boundary

This proposal does not grant write authority.

It does not:

- execute prompt agents;
- infer missing product semantics with an LLM;
- apply answers to intake artifacts;
- mutate candidate source artifacts through SpecSpace;
- mutate canonical SpecGraph specs;
- write Ontology packages or lockfiles;
- accept ontology terms;
- approve candidate graphs;
- create Git branches or commits;
- open pull requests;
- publish read models;
- add SpecSpace mutation UI.

The output is a review-only contract report that prepares a later rerun slice.

## Validation

- `tests/test_idea_to_spec_clarification_answers.py`
- `make idea-to-spec-clarification-answers`

## Follow-Ups

- Feed accepted answers into a deterministic intake/candidate rerun input.
- Add ontology gap review decision actions over clarification answers.
- Surface request/answer state in SpecSpace product workspace UX.
