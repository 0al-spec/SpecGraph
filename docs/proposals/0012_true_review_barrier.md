# True Review Barrier for Canonical Mutation

## Status

Draft proposal

## Problem

`supervisor` currently uses `review_pending` as a human gate for status and
maturity promotion, but not as a true gate for canonical content.

In the current model, a successful refinement can sync files from the isolated
worktree back into the canonical tree before human approval is resolved. This
creates a semantic mismatch:

- `review_pending` sounds like canonical truth is still pending
- the canonical tree may already contain the candidate content
- non-approve gate decisions do not necessarily remove that content

This weakens the governance model in two ways.

### 1. Canonical truth is mutated before approval

The system appears to promise pre-merge review semantics while behaving closer
to post-write review semantics.

### 2. Derived state can be based on unaccepted candidate content

Proposal queues, refactor queues, summaries, and follow-on decisions can drift
toward candidate worktree state rather than accepted canonical state.

## Goals

- Make review gates protect canonical truth, not only lifecycle promotion.
- Preserve bounded human review over one candidate refinement at a time.
- Keep approval resolution explicit, inspectable, and freshness-checked.
- Ensure derived artifacts that represent current graph truth are based on
  accepted canonical state only.

## Non-Goals

- Replacing the split-proposal lane
- Defining the final storage format for every possible candidate artifact
- Removing all derived artifacts from supervisor runs
- Eliminating draft worktree inspection during review

## Core Proposal

`review_pending` should become a true pre-merge barrier for canonical mutation.

### Candidate Stage

When a refinement succeeds but requires human approval:

- do not sync candidate content into the canonical root
- preserve the candidate in a staged review artifact
- record the exact candidate file set, digests, and source worktree reference
- attach proposed status and maturity without promoting them yet

This keeps candidate truth reviewable without presenting it as canonical.

### Approval Stage

When the operator approves the review gate:

- re-validate freshness between the staged candidate and current canonical base
- sync only the approved candidate paths into canonical root
- apply status or maturity promotion
- clear staged review metadata

### Non-Approve Stage

When the operator resolves the gate as retry, split, block, redirect, or
escalate:

- do not sync candidate content into canonical root
- clear or archive the staged candidate state
- preserve the decision trail and run metadata

### Accepted-Only Derivation

Derived artifacts that describe the current graph state should be rebuilt from:

- accepted canonical content
- or explicit first-class proposal artifacts

They should not treat unapproved candidate worktree content as current truth.

## Minimum Artifact Contract

The proposal does not force one exact representation, but it does require a
staged review contract with at least:

- `pending_sync_paths`
- `pending_worktree_path` or equivalent staged source
- `pending_base_digests`
- `pending_candidate_digests`
- `pending_run_id`

This is the minimum needed to keep approval deterministic and freshness-aware.

## Naming Consequence

If SpecGraph intentionally wants post-write review instead, it should rename the
semantics honestly.

But the preferred direction of this proposal is not renaming. It is restoring
`review_pending` as a real pre-merge review barrier.

## Supervisor Implications

After this proposal:

- canonical content changes require either auto-approve or explicit approval
- `review_pending` becomes a statement about truth, not only promotion
- queue updates that represent canonical graph health should run after accepted
  sync, not before
- proposal artifacts remain valid as first-class non-canonical outputs

## Open Questions

- Should staged candidate artifacts live in node metadata, a dedicated
  review-state file, or both?
- Which derived artifacts may still be generated from candidate state if they
  are explicitly marked non-canonical?
