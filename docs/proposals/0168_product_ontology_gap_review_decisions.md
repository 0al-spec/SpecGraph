# 0168 Product Ontology Gap Review Decisions

## Status

Implemented

## Summary

The product `idea-to-spec` repair loop can now turn accepted ontology-gap
answers into typed product-scoped ontology review decisions.

Proposals `0163` through `0167` introduced clarification requests, validated
answers, rerun overlays, rerun previews, and review-only materialized candidate
previews. This slice adds an explicit decision artifact between accepted answers
and later ontology-aware rerun inputs so downstream consumers can distinguish
product ontology review decisions from generic clarification answers.

## Implementation

The implemented surface is:

- `tools/product_ontology_gap_review_decisions.py`;
- `make product-ontology-gap-review-decisions`;
- `runs/product_ontology_gap_review_decisions.json`;
- regression tests for project-local terms, existing-term bindings, aliases,
  rejection, deferral, unready answer reports, incomplete values, privacy
  redaction, and CLI output.

The tool consumes:

```text
runs/idea_to_spec_clarification_answers.json
```

and writes:

```text
runs/product_ontology_gap_review_decisions.json
```

## Semantics

Only accepted clarification answers whose request snapshot has
`kind: ontology_gap` become decisions.

Supported decision types:

- `bind_existing_term`;
- `alias_existing_term`;
- `propose_project_local_term`;
- `reject_non_domain_term`;
- `defer_requires_owner`.

The artifact preserves request ids, target refs, authority metadata, public-safe
source values, and the intended materialization boundary:

```text
materialization_intent: rerun_overlay_only
```

The decision artifact is product-scoped review evidence. It is not an Ontology
owner decision import and it is not canonical ontology state.

## Authority Boundary

This proposal does not grant write authority.

It does not:

- execute prompt agents;
- apply decisions to source artifacts;
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

- `tests/test_product_ontology_gap_review_decisions.py`
- `make product-ontology-gap-review-decisions`

## Follow-Ups

- Teach `idea_to_spec_answer_rerun_input` to consume this decision artifact as
  the typed ontology decision source for ontology review hints.
- Propagate ontology decision counts and unresolved gap state into candidate
  quality/readiness surfaces.
- Surface ontology gap decisions in SpecSpace product workspace UX.
