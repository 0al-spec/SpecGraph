# 0142 Layer-Aware Ontology Gap and Diff Review

## Status

Implemented

## Source

- `docs/archive/proposal_sources/0142_layer_aware_ontology_gap_diff_review.md`

## Summary

Ontology gap and compatibility diff surfaces now expose layer-aware review
metadata. Gaps and diffs can carry explicit layer assignments when they are
available from fixture bindings or Ontology compiler diff hints. When the layer
is not known, the surfaces mark the item as `unassigned` and preserve the review
route instead of flattening the concern into an unqualified missing term or
change.

## Motivation

After `0141`, SpecGraph can import and summarize first-class ontology layer
metadata from normalized IR. The next missing surface is review: an operator
should be able to tell whether a missing concept or compatibility change belongs
to:

- `objective`: product/domain intent and goals;
- `mechanics`: deterministic graph/model structure;
- `execution`: runtime behavior, commands, checks, and enforcement;
- `meta`: specification, governance, and process concepts;
- `multi_agent`: agent collaboration and invocation semantics.

Without this layer review metadata, downstream dashboards and SpecAuthor gates
would still see gaps and diffs as flat lists.

## Implementation

This slice updates `tools/ontology_imports.py`:

- gap entries include `layer_review`;
- `ontology_import_gap_index.summary` includes layer review counts;
- compatibility diff previews include `layer_review`;
- compatibility diff summaries include layered/unassigned change counts;
- optional `fixture.binding.layerHints` or `fixture.binding.layer_hints` can
  assign layers to unresolved refs;
- optional `compatibility_report.changes.layerHints` can assign layers to diff
  refs;
- normalized IR layer metadata remains the source for already-known refs.

The implementation remains additive: existing consumers can ignore the new
`layer_review` fields.

## Authority Boundary

This proposal does not make SpecGraph an ontology authority.

It does not:

- infer layers for legacy specs;
- write ontology packages;
- update ontology lockfiles;
- mutate canonical specs;
- accept or reject ontology terms;
- import owner decisions;
- execute prompt agents;
- close semantic gates.

## Validation

- Current SpecGraph Core import tests verify that unresolved gaps and added
  diff refs with no layer are marked `unassigned`.
- A new regression test verifies that fixture/report layer hints are grouped
  into the expected layer and reflected in summary counts.
- `make ontology-imports` continues to emit the declared read-only surfaces.

## Follow-ups

- Add a SpecSpace ontology layer lens over package, gap, and diff surfaces.
- Extend SpecAuthorAgent write gates so strong ontology-bound claims declare the
  active layer context.
- Add owner-decision import metadata once Ontology compiler reports accepted or
  rejected layer decisions.
