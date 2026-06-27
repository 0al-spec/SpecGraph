# 0175 Ontology Gap Matching Normalization

## Status

Implemented

## Summary

The product `idea-to-spec` repair chain can now resolve ontology gaps with a
small, explicit normalization policy instead of relying only on literal term
keys. Proposal `0175` extends `idea_to_spec_rerun_preview` and
`idea_to_spec_rerun_materialization` so typed product ontology decisions can
match safe inflection and phrase variants while preserving machine-readable
match provenance.

This improves cases like:

```text
Payment Record -> Payment Recorded
Local Notification -> Local Notification Service
Renewal Date -> Renewal Date Updated
```

without making broad single-word terms authoritative over event/action variants.
For example, `Subscription` does not automatically resolve `Subscription Added`
or `Subscription Cancelled`.

## Motivation

Proposal `0169` lets rerun input consume typed product ontology decisions, but
preview matching still treated many safe term variants as unrelated gaps. During
the subscription tracker pilot, project-local terms such as `Payment Record` and
`Local Notification` did not resolve closely related candidate graph gaps,
leaving the repair loop noisier than the operator intent.

The fix should not become fuzzy matching. Product ontology review remains
review-only and conservative: a decision may close a gap only when the match is
explicitly explainable and safe to inspect.

## Implementation

The implemented surface is:

- normalized ontology gap matching in `tools/idea_to_spec_rerun_preview.py`;
- match provenance threaded into
  `rerun_preview.ontology_gap_preview.resolved_ontology_gaps`;
- match provenance preserved in materialized
  `candidate_graph_preview.nodes[].ontology_gap_resolutions`;
- focused regression tests in `tests/test_idea_to_spec_rerun_preview.py` and
  `tests/test_idea_to_spec_rerun_materialization.py`;
- roadmap, DocC, and registry tracking for proposal `0175`.

The preview records include:

```text
gap_id
decision_id
gap_term
decision_term
match_kind
confidence
match
```

Supported `match_kind` values are:

```text
exact
normalized_exact
safe_inflection
safe_phrase_match
target_ref
aggregate_target
```

`confidence` is a triage signal, not an ontology acceptance claim:

```text
target_ref -> explicit_target
exact / normalized_exact -> high
safe_inflection -> medium
safe_phrase_match -> low
aggregate_target -> aggregate_scope
```

If more than one decision matches a gap, the preview chooses the strongest
`match_kind` by precedence before preserving source order for ties. This keeps a
later `exact` match from being displaced by an earlier `safe_phrase_match`.

`safe_phrase_match` is deliberately narrow and directional. It requires a
multi-token decision term, treats the decision term as the prefix of the gap
term, and only accepts exactly one suffix stem from a short allowlist such as
`record`, `schedule`, `service`, and `update`. It is not a bidirectional synonym
rule and does not let event-like terms rewrite the base project vocabulary.

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

- `tests/test_idea_to_spec_rerun_preview.py`
- `tests/test_idea_to_spec_rerun_materialization.py`
- `make idea-to-spec-rerun-preview`
- `make idea-to-spec-rerun-materialization`

## Follow-Ups

- Surface `match_kind` and `confidence` in SpecSpace product repair lanes.
- Use match provenance in later candidate-quality and promotion-review
  dashboards without treating it as ontology acceptance.
