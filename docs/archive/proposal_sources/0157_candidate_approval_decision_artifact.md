# 0157 Candidate Approval Decision Artifact

Operator intent: implement the first runtime slice after proposal `0156` by
producing an explicit candidate approval decision artifact for CLI-mode
idea-to-spec operation.

Bounded scope:

- read `active_idea_to_spec_candidate` and `idea_to_spec_promotion_gate`;
- accept an explicit operator decision state;
- write `runs/candidate_approval_decision.json`;
- default to `needs_context`, not approval;
- include public-safe refs, digests, decision state, findings, and authority
  metadata;
- downgrade requested approvals to `needs_context` when active candidate or
  promotion gate readiness is incomplete.
- reject out-of-repository approval input refs, stale promotion-gate digests,
  unsafe promotion paths, and approved decisions with default/non-explicit
  rationale;
- prevent static publishing from carrying a stale approval artifact when the
  active candidate is absent, unpublishable, or no longer digest-matches the
  approval evidence.

Out of scope:

- prompt-agent execution;
- SpecSpace mutation UI;
- canonical SpecGraph spec mutation;
- ontology package writes;
- Git branch, commit, PR, merge, or read-model publishing;
- treating the approval artifact as repository review acceptance.
