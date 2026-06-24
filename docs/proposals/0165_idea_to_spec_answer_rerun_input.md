# 0165 Idea-To-Spec Answer Rerun Input

## Status

Implemented

## Summary

The product `idea-to-spec` path can now convert accepted clarification answers
into a deterministic rerun input overlay.

Proposal `0164` validates answer sets against stable clarification request ids,
but it deliberately does not apply answers. This slice adds the next boundary:
accepted answers become public-safe hints that a later intake or candidate
rerun can consume without mutating source artifacts, candidate graphs,
canonical specs, ontology packages, or Git state.

## Implementation

The implemented surface is:

- `tools/idea_to_spec_answer_rerun_input.py`;
- `make idea-to-spec-answer-rerun-input`;
- `runs/idea_to_spec_answer_rerun_input.json`;
- regression tests for ready overlays, unready answer reports, unsupported
  input kind, raw trace redaction, and CLI output.

The tool consumes:

```text
runs/idea_to_spec_clarification_answers.json
```

and writes:

```text
runs/idea_to_spec_answer_rerun_input.json
```

## Semantics

The rerun input artifact only uses answers with accepted statuses:

- `accepted_for_candidate`;
- `accepted_for_review`.

Accepted answers are mapped into review-only overlay buckets:

- intake active-frame hints;
- event-storming hints;
- ontology review hints for term bindings, aliases, project-local terms,
  rejected terms, and deferred terms;
- candidate review hints for acceptance criteria, graph edges, claim reviews,
  and other candidate-level decisions.

If the source answer report is not ready, or if it uses an unsupported contract,
the output remains blocked with review findings and no overlay hints are
materialized.

## Authority Boundary

This proposal does not grant write authority.

It does not:

- execute prompt agents;
- apply answers to source artifacts;
- mutate candidate source artifacts;
- mutate canonical SpecGraph specs;
- write Ontology packages or lockfiles;
- accept ontology terms;
- approve candidate graphs;
- create Git branches or commits;
- open pull requests;
- publish read models;
- add SpecSpace mutation UI.

The output is a review-only rerun input overlay. A later proposal may define how
approved overlays are consumed by a new intake or candidate generation run.

## Validation

- `tests/test_idea_to_spec_answer_rerun_input.py`
- `make idea-to-spec-answer-rerun-input`

## Follow-Ups

- Add a deterministic intake rerun step that consumes the overlay without
  granting direct mutation authority.
- Add a CLI or agent conversation wrapper that can fill answer sets from a real
  operator interview.
- Surface request, answer, and rerun input state in SpecSpace product workspace
  UX.
