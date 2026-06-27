# 0176 Candidate Repair Answer Materialization

## Status

Implemented

## Summary

The product `idea-to-spec` repair chain now materializes targeted non-ontology
repair answers into review-only candidate graph deltas. Proposal `0176` extends
the existing answer rerun, preview, materialization, and repair-session journal
surfaces so `candidate_gap` answers can close product/spec gaps without
rewriting source candidate artifacts or granting SpecSpace mutation authority.

This covers answers such as:

```text
local-only-storage.enforcement-mechanism -> enforcement mechanism added
subscription-required-fields.enforcement-mechanism -> enforcement mechanism added
stale-renewal-date-risk -> risk accepted
```

Ontology decisions remain handled by the ontology gap review flow. This proposal
only handles product candidate gaps whose clarification request explicitly
targets a candidate graph gap.

## Motivation

After the generic `product_idea_to_spec` path started working for new product
ideas, the subscription pilot showed a remaining asymmetry: ontology answers
could resolve preview gaps, but non-ontology answers were only preserved as
`candidate_review_hints`. The user could answer questions about risks,
required-field validation, local-only storage, or reminder enforcement, yet the
materialized candidate graph preview still kept those gaps open.

That made the repair loop less useful than the operator interaction: the system
recorded the answer but did not move the candidate closer to approval readiness.

## Implementation

The implemented surface is:

- `answer_question` for `candidate_gap` now enters `candidate_review_hints`
  instead of being dropped when it is not active-frame or event-storming data;
- `idea_to_spec_rerun_preview` now emits
  `rerun_preview.candidate_gap_preview`;
- candidate gap preview resolves only explicit `target_ref` matches;
- deferred candidate answers remain unresolved;
- `idea_to_spec_rerun_materialization` removes preview-resolved candidate gaps
  from nested `candidate_graph_preview.nodes[].gaps`;
- removed candidate gaps are preserved as
  `candidate_graph_preview.nodes[].candidate_gap_resolutions`;
- `idea_to_spec_repair_session_journal` treats unresolved candidate gaps as
  candidate-approval blockers;
- focused regression tests cover rerun input routing, candidate gap preview,
  materialization, and journal readiness.

The preview records include:

```text
gap_id
node_id
kind
target_ref
request_id
answer_kind
resolution_kind
match_kind
confidence
resolution_preview
```

Supported `resolution_kind` values are intentionally small and review-oriented:

```text
enforcement_mechanism_added
risk_accepted
gap_rejected
candidate_context_added
```

Matching is deliberately stricter than ontology term matching. Candidate repair
answers close gaps only when the answer target matches the concrete candidate
gap ref, such as:

```text
candidate-spec.local-storage.gaps.gap.local-only-storage.enforcement-mechanism
```

There is no fuzzy, synonym, or phrase matching for candidate product gaps.

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

The materialized candidate graph remains nested inside
`runs/idea_to_spec_rerun_materialization.json` as preview state.

## Validation

- `tests/test_idea_to_spec_answer_rerun_input.py`
- `tests/test_idea_to_spec_rerun_preview.py`
- `tests/test_idea_to_spec_rerun_materialization.py`
- `tests/test_idea_to_spec_repair_session_journal.py`
- `make idea-to-spec-answer-rerun-input`
- `make idea-to-spec-rerun-preview`
- `make idea-to-spec-rerun-materialization`

## Follow-Ups

- Surface `candidate_gap_preview` and `candidate_gap_resolutions` in SpecSpace
  product repair lanes.
- Use candidate gap resolution counts in Platform promotion readiness
  dashboards.
- Add a prompt/event-storming intake flow that generates better first-pass
  answers before deterministic materialization.
