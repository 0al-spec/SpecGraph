# 0177 Repaired Candidate Promotion Handoff

Status: implemented.

## Problem

Proposal `0176` lets accepted ontology and product/spec repair answers change the
review-only `idea_to_spec_rerun_materialization` candidate graph preview. This
removes resolved gaps from the nested repaired graph, but the downstream
approval surfaces still read the older active candidate and promotion gate that
were built before rerun materialization.

The result is an integration gap: a candidate can have zero remaining preview
gaps while `idea_to_spec_repair_session.summary.ready_for_candidate_approval`
stays false because the journal still sees stale active-candidate and promotion
gate blockers.

## Proposal

Add a deterministic, review-only repaired promotion handoff builder:

```text
idea_to_spec_rerun_materialization
  -> repaired_candidate_spec_graph
  -> repaired_pre_sib_coherence_report
  -> repaired_candidate_repair_loop_report
  -> repaired_candidate_spec_materialization_report
  -> repaired_idea_to_spec_promotion_gate
  -> repaired_active_idea_to_spec_candidate
  -> repaired_idea_to_spec_repair_session
  -> repaired_candidate_promotion_handoff_report
```

The builder preserves the original product-scoped `product://...` candidate
source ref for active-candidate identity checks, while recording the rerun
materialization preview source as provenance.

## Authority Boundary

The slice remains review-only:

- no prompt-agent execution;
- no mutation of canonical specs;
- no mutation of candidate source artifacts;
- no Ontology package writes;
- no ontology term acceptance;
- no candidate approval decision;
- no Git branch, commit, PR, merge, or read-model publication.

The repaired handoff may become ready for candidate approval review, but it must
not become ready for Platform promotion until a separate
`candidate_approval_decision` exists.

## Acceptance Criteria

- A ready rerun materialization with all ontology/product gaps resolved produces
  repaired active-candidate and promotion-gate surfaces.
- If the repaired graph still has pre-SIB structural issues, the normal
  candidate repair loop may repair them in preview, and the promotion gate must
  preserve `pre_sib_findings_repaired_by_preview` evidence.
- The repaired repair-session journal sets `ready_for_candidate_approval: true`
  only when the repaired active candidate, repaired promotion gate, and
  intermediate repair artifacts are ready and unresolved gap counts are zero.
- The repaired repair-session journal keeps
  `ready_for_platform_promotion: false` until a separate approval decision.
- Unresolved repaired candidate gaps keep the handoff blocked.

## Validation

- `tests/test_repaired_candidate_promotion_handoff.py`
- `make repaired-candidate-promotion-handoff`
- `make proposal-tracking-gate`
