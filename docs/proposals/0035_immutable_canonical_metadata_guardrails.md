# Immutable Canonical Metadata Guardrails

## Status

Draft proposal

## Problem

Gate approval can currently apply candidate spec content back into canonical
`specs/nodes/*.yaml` while also accepting candidate-side lifecycle metadata.
That creates a specific governance risk:

- `created_at` can drift during an approval even though the canonical spec was
  not newly created.
- Operators may need to recover the original creation timestamp manually from
  git history, filesystem state, or old run artifacts.
- A review gate that should only decide whether candidate semantic content is
  accepted can accidentally rewrite immutable identity metadata.

This was observed during a gate backlog reconcile pass: approving
`SG-SPEC-0018` changed `created_at` to the approval time, and the original
creation timestamp had to be restored manually.

## Goals

- Preserve canonical creation metadata during gate approval and candidate sync.
- Keep `updated_at` available for real canonical mutation time.
- Make metadata drift explicit and inspectable instead of relying on manual
  operator recovery.
- Define a path from a minimal runtime guard to a reusable metadata policy.

## Non-Goals

- Freezing all metadata fields forever.
- Blocking legitimate migration tools that intentionally rewrite metadata under
  explicit authority.
- Replacing semantic review with timestamp validation.
- Adding new canonical spec nodes for this concern immediately.

## Core Proposal

SpecGraph should treat canonical identity and creation metadata as immutable
under ordinary gate approval.

At minimum, the following fields should not be overwritten from candidate
worktrees during normal approve/sync flows:

- `id`
- `created_at`

The supervisor may still update mutable lifecycle metadata such as `updated_at`
when canonical content changes.

## Phase 1: Preserve-On-Approve Runtime Guard

The first runtime slice should add a narrow guard in gate resolution:

1. Load the current canonical spec before applying an approved candidate.
2. Preserve immutable canonical metadata values.
3. Apply the accepted candidate content.
4. Restore immutable canonical metadata before writing the canonical file.
5. Update mutable lifecycle metadata according to the accepted canonical
   mutation.

This is the smallest practical fix because it protects the exact failure mode
without introducing a larger validation framework first.

Expected behavior:

- approving a candidate can change semantic spec content;
- approving a candidate must not change canonical `created_at`;
- approving a candidate can refresh `updated_at` when accepted content changes.

## Phase 2: Typed Immutable-Metadata Finding

The next layer should make candidate metadata drift visible before approval.

Validation should emit a typed finding when a candidate attempts to change an
immutable canonical metadata field:

```text
immutable_metadata_changed
```

The finding should include:

- `spec_id`
- `field`
- `canonical_value`
- `candidate_value`
- `transition_context`
- `recommended_action`

This lets the gate reviewer distinguish benign candidate timestamp churn from
actual semantic changes.

The system may choose one of two safe behaviors:

- block approval until the candidate metadata is corrected;
- allow approval only if the preserve-on-approve guard deterministically
  restores the canonical value and records the finding.

## Phase 3: Declarative Metadata Policy

The longer-term model should move metadata rules into a declarative policy
artifact instead of hard-coding field behavior only inside gate resolution.

The policy should classify fields as:

- `immutable`
- `mutable`
- `migration_only`
- `derived_only`

Initial policy examples:

- `id`: `immutable`
- `created_at`: `immutable`
- `updated_at`: `mutable`
- runtime gate fields: `mutable`
- generated projection fields: `derived_only`

That policy should be shared by:

- gate approval;
- retry/reject gate handling;
- child materialization;
- split application;
- import and handoff review flows;
- future transition validators.

## Boundary

This proposal does not say that timestamps are semantic truth. It says that
creation metadata is part of canonical artifact identity and therefore ordinary
candidate approval must not rewrite it accidentally.

Any intentional metadata migration should require explicit authority, a bounded
change surface, and an inspectable transition record.

## Acceptance Criteria

- A regression test proves that approving a candidate with a changed
  `created_at` preserves the canonical `created_at`.
- The same test proves that accepted canonical mutation can still refresh
  `updated_at`.
- Candidate drift of immutable metadata is observable through a typed finding
  or equivalent structured inspection surface.
- Future policy extraction has a clear field-classification model and does not
  require rediscovering the same invariant.

## Runtime Realization Path

The immediate follow-up should be a small supervisor-runtime PR:

- implement Phase 1 in gate resolution;
- add a targeted regression test for approved candidate metadata drift;
- rebuild relevant derived surfaces after the guard is in place.

After that, Phase 2 can turn the same invariant into a typed validation finding.
Phase 3 should only happen once more metadata-sensitive transitions need the
same rule outside gate approval.
