# 0157 Candidate Approval Decision Artifact

## Status

Implemented

## Summary

SpecGraph now has a deterministic, review-only artifact for explicit
idea-to-spec candidate approval decisions.

The builder consumes:

- `runs/active_idea_to_spec_candidate.json`;
- `runs/idea_to_spec_promotion_gate.json`;
- an explicit CLI decision state: `approved`, `rejected`, `needs_context`, or
  `superseded`;
- a public-safe operator reference and short rationale.

It emits:

- `runs/candidate_approval_decision.json`;
- source refs and digests for the active candidate, promotion gate, and linked
  evidence chain;
- effective decision state, with unsafe approvals downgraded to
  `needs_context`;
- promotion paths only when the decision is `approved` and all upstream
  readiness, digest, path, and public-ref checks pass.

This implements the first runtime slice from proposal `0156`.

## Implementation

This slice adds:

- `tools/candidate_approval_decision.py`;
- `make candidate-approval-decision`;
- regression tests for approved, rejected, unsafe, and default non-approval
  paths;
- static publishing guards that skip stale approval artifacts when the active
  candidate source is absent, unpublishable, or no longer matches recorded
  source digests;
- documentation and registry tracking for proposal/runtime provenance.

The default CLI state is intentionally non-approving:

```bash
make candidate-approval-decision
```

writes `needs_context`. To approve, the operator must pass an explicit state:

```bash
make candidate-approval-decision \
  CANDIDATE_APPROVAL_DECISION_STATE=approved \
  CANDIDATE_APPROVAL_OPERATOR_REF=local_operator:egor \
  CANDIDATE_APPROVAL_REASON="Candidate is ready for promotion request creation."
```

## Authority Boundary

This proposal does not grant write authority.

It does not:

- execute prompt agents;
- mutate candidate graph artifacts;
- mutate canonical SpecGraph specs;
- write Ontology packages or lockfiles;
- accept ontology terms;
- create Git branches or commits;
- open pull requests;
- merge reviews;
- publish read models;
- let SpecSpace write into a checkout.

The approval artifact authorizes only the next controlled handoff: Platform may
create or validate a promotion request. Git Service execution, repository
review, merge, and read-model publication remain separate downstream
authorities.

## Validation

- `tests/test_candidate_approval_decision.py::test_candidate_approval_decision_approves_ready_handoff`
- `tests/test_candidate_approval_decision.py::test_candidate_approval_decision_downgrades_unready_approval`
- `tests/test_candidate_approval_decision.py::test_candidate_approval_decision_records_explicit_rejection`
- `tests/test_candidate_approval_decision.py::test_candidate_approval_decision_rejects_private_operator_text`
- `tests/test_candidate_approval_decision.py::test_candidate_approval_decision_cli_strict_fails_without_approval`
- `tests/test_candidate_approval_decision.py::test_candidate_approval_decision_rejects_stale_promotion_gate_digest`
- `tests/test_candidate_approval_decision.py::test_candidate_approval_decision_rejects_unsafe_promotion_paths`
- `tests/test_static_artifact_bundle.py::test_build_public_bundle_skips_candidate_approval_with_stale_digest`
- `tests/test_static_artifact_bundle.py::test_build_public_bundle_skips_candidate_approval_without_publishable_active_candidate`

## Follow-ups

- Platform should require or consume `candidate_approval_decision` before Git
  Service promotion execution.
- SpecSpace should display approval state in the product workspace workflow
  lane as read-only evidence.
- A later post-review slice should add explicit `review_merged` and
  `read_model_publish_approved` closure artifacts.
