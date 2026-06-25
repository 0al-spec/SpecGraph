# 0169 Ontology Decisions Rerun Overlay And Candidate Quality

## Status

Implemented

## Summary

The product `idea-to-spec` rerun input can now consume typed product ontology
gap review decisions from proposal `0168` and use them as the ontology review
source for rerun overlay hints.

This slice also adds a candidate-quality preview field to rerun preview reports
so downstream consumers can see whether ontology gap decisions resolved all,
some, or none of the candidate ontology gaps before any source artifact is
mutated.

## Implementation

The implemented surface is:

- optional `--ontology-decisions` support in
  `tools/idea_to_spec_answer_rerun_input.py`;
- `IDEA_TO_SPEC_ANSWER_RERUN_INPUT_ONTOLOGY_DECISIONS` Make variable;
- `candidate_quality_preview` in `tools/idea_to_spec_rerun_preview.py`;
- regression tests for typed decision overlay, duplicate prevention, unready
  decision blocking, CLI support, and candidate quality preview.

The extended rerun input can consume:

```text
runs/idea_to_spec_clarification_answers.json
runs/product_ontology_gap_review_decisions.json
```

and still writes:

```text
runs/idea_to_spec_answer_rerun_input.json
```

## Semantics

When `product_ontology_gap_review_decisions` is supplied, ontology-gap answers
from the generic clarification answer report are not applied directly. Instead,
the typed decision records become `ontology_review_hints`:

- `bind_existing_term` -> `term_bindings`;
- `alias_existing_term` -> `aliases`;
- `propose_project_local_term` -> `project_local_terms`;
- `reject_non_domain_term` -> `rejected_terms`;
- `defer_requires_owner` -> `deferred_terms`.

This avoids duplicate ontology hints while keeping non-ontology clarification
answers available for active-frame, event-storming, graph repair, and claim
review overlays.

`idea_to_spec_rerun_preview` now emits:

```text
rerun_preview.candidate_quality_preview
```

The quality preview reports `ontology_gap_state`, resolved/unresolved ontology
gap counts, and a `review_state` such as
`candidate_quality_partially_improved` or
`candidate_quality_blocked_by_ontology_gaps`.

## Authority Boundary

This proposal does not grant write authority.

It does not:

- execute prompt agents;
- apply decisions or answers to source artifacts;
- mutate candidate source artifacts;
- mutate canonical SpecGraph specs;
- write Ontology packages or lockfiles;
- accept ontology terms;
- approve candidate graphs;
- create Git branches or commits;
- open pull requests;
- publish read models;
- add SpecSpace mutation UI.

## Validation

- `tests/test_idea_to_spec_answer_rerun_input.py`
- `tests/test_idea_to_spec_rerun_preview.py`
- `make idea-to-spec-answer-rerun-input`
- `make idea-to-spec-rerun-preview`

## Follow-Ups

- Surface clarification requests, ontology decisions, and preview quality in
  the SpecSpace product workspace lane.
- Use candidate-quality preview state as one input to later promotion readiness
  and Git Service handoff gates.
