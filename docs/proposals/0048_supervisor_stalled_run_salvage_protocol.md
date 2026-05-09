# Supervisor Stalled Run Salvage Protocol

## Status

Draft proposal

## Source Material

This proposal is based on a live supervisor incident observed during the stacked
PR run that started from `SG-SPEC-0033`.

The incident is treated as process evidence, not as canonical runtime truth by
itself:

- `python3 tools/supervisor.py --target-spec SG-SPEC-0033 --execution-profile standard`
  created a child worktree and produced a bounded spec diff.
- The parent supervisor process did not write a new run artifact or update
  `runs/latest-summary.md`.
- The run left a dirty child worktree at
  `.worktrees/sg-spec-0033-20260509T185012Z-c6a92bf1`.
- Manual inspection showed that the only changed file was
  `specs/nodes/SG-SPEC-0033.yaml`.
- The diff was later recovered manually, validated, and promoted through PR
  review as a bounded graph change.

## Context

SpecGraph already has the governance loop:

```text
observe -> propose -> improve tools -> observe again
```

It also treats PR review comments as process evidence through the review
feedback learning loop. That covers external review feedback, but it does not
yet cover supervisor runtime incidents that happen before a PR exists.

The observed failure mode is narrower than general runtime failure:

```text
child executor mutates isolated worktree
  -> parent supervisor stalls before sync
  -> no latest summary records the failure
  -> useful bounded diff can be lost or manually adopted without protocol
```

This is not a spec-quality blocker. It is a supervisor runtime lifecycle gap.

## Problem

When a targeted supervisor run stalls after the child worktree has changed, the
system currently has no governed way to distinguish:

- no work happened;
- work happened and failed validation;
- work happened, validation never ran, and manual salvage is required;
- work happened and was abandoned intentionally.

The worst property is silence. If `runs/latest-summary.md` remains old, a user
or agent may believe the run did nothing. In reality, a dirty worktree may hold
the only copy of a bounded candidate change.

Without a salvage protocol, recovery becomes ad hoc:

- the operator manually finds the worktree;
- the operator decides whether the diff is bounded;
- the operator copies the diff into the main branch;
- the PR description records this only informally.

That loses root-cause classification, prevention intent, and repeatable
verification.

## Goals

- Define a recoverable supervisor stall as a first-class runtime incident.
- Require explicit artifact evidence when a run stalls after child worktree
  mutation.
- Preserve useful bounded diffs without silently accepting them.
- Require human review before adopting a salvaged diff.
- Make `runs/latest-summary.md` reflect the stall instead of leaving stale
  success state visible.
- Provide a later materialization path for watchdog, salvage artifacts,
  recovery commands, tests, and viewer/dashboard surfacing.

## Non-Goals

- Implementing the watchdog in this proposal.
- Automatically applying dirty worktree diffs.
- Treating salvaged diffs as canonical truth.
- Committing raw `.worktrees/` contents.
- Replacing ordinary supervisor validation or PR review.
- Defining a general incident-management system for all runtime failures.

## Core Proposal

SpecGraph should define a narrow `stalled_run_salvage` protocol.

A supervisor run enters this protocol when all of the following are true:

- the parent supervisor started a targeted child execution;
- the child worktree exists;
- the child worktree has tracked file changes;
- the parent supervisor cannot complete normal sync, validation, and summary
  writing within the configured run lifecycle;
- the changed paths remain within the original bounded target scope.

The protocol must produce reviewable evidence, not canonical mutation.

## Required Runtime Behavior

When the supervisor detects a stalled dirty worktree, it should terminate the
run explicitly and write a recoverable failure record.

The structured run-log payload (`runs/<run_id>.json`) should keep the existing
`outcome` vocabulary stable and add salvage-specific recovery fields instead of
overloading `runs/latest-summary.md` as JSON:

```json
{
  "completion_status": "failed",
  "outcome": "blocked",
  "recovery_status": "stalled_run_salvage_required",
  "required_human_action": "review_salvaged_worktree_diff",
  "executor_environment": {
    "primary_failure": true,
    "primary_failure_reason": "child_worktree_stalled_after_mutation"
  },
  "salvage": {
    "artifact_path": "runs/<run_id>-salvage.json",
    "patch_artifact_path": "runs/<run_id>-salvage.patch"
  }
}
```

`stalled_run_salvage_required` is therefore not a replacement for the current
`outcome` values (`done`, `retry`, `split_required`, `blocked`, `escalate`). It
is a recovery status used under a failed or blocked run outcome.

`runs/latest-summary.md` should render the same facts as Markdown, including:

- completion status: `failed`;
- outcome: `blocked`;
- recovery status: `stalled_run_salvage_required`;
- executor environment primary failure: `yes`;
- required human action: `review_salvaged_worktree_diff`;
- salvage artifact path and patch artifact path.

The supervisor must not leave `runs/latest-summary.md` pointing at an unrelated
older successful run when it knows that a newer targeted run stalled after
worktree mutation.

## Salvage Artifact

The salvage artifact should be stable enough for review and small enough to
avoid committing raw worktree state.

Minimum shape:

```json
{
  "artifact_kind": "supervisor_stalled_run_salvage",
  "schema_version": 1,
  "run_id": "20260509T185012Z-SG-SPEC-0033-c6a92bf1",
  "spec_id": "SG-SPEC-0033",
  "target_scope": {
    "target_spec": "SG-SPEC-0033",
    "allowed_paths": ["specs/nodes/SG-SPEC-0033.yaml"]
  },
  "stalled_phase": "post_child_mutation_pre_sync",
  "worktree": {
    "path": ".worktrees/sg-spec-0033-20260509T185012Z-c6a92bf1",
    "dirty": true,
    "changed_files": ["specs/nodes/SG-SPEC-0033.yaml"]
  },
  "diff": {
    "diff_stat": "specs/nodes/SG-SPEC-0033.yaml | 19 +++++++++++++++----",
    "patch_artifact_path": "runs/20260509T185012Z-SG-SPEC-0033-c6a92bf1-salvage.patch",
    "patch_sha256": "sha256:example",
    "bounded_to_allowed_paths": true,
    "patch_truncated": false
  },
  "recovery": {
    "automatic_adoption_allowed": false,
    "required_human_action": "review_salvaged_worktree_diff",
    "recovery_hint": "inspect diff, apply only if bounded, rerun validation"
  }
}
```

The artifact must preserve the diff in a reviewable durable form. It may do so
by embedding a small bounded patch inline or, preferably, by recording a
relative `patch_artifact_path` plus `patch_sha256` for a retained run artifact.
Diff stat and changed file list alone are insufficient because the child
worktree may later be cleaned up or become unavailable.

The artifact should not commit raw `.worktrees/` contents. Large patches may be
truncated only when `patch_truncated: true` is set and a follow-up recovery gap
explains how to recover or intentionally reject the incomplete salvage.

## Recovery Semantics

Salvage recovery should be explicit and review-first:

- `review_salvaged_worktree_diff`: operator or reviewer inspects the worktree
  diff.
- `adopt_salvaged_diff`: a later command may copy the bounded diff into the
  active branch only after review.
- `reject_salvaged_diff`: a later command may mark the salvage artifact as
  rejected and leave the worktree for cleanup.
- `cleanup_salvaged_worktree`: cleanup is allowed only after adoption,
  rejection, or accepted risk is recorded.

Adoption must rerun normal validation. A salvaged diff never skips format,
lint, graph validation, tests, or PR review.

## Graph Integration

The first materialized graph node should be small and runtime-facing:

- It should belong under the supervisor runtime or runtime-hardening branch.
- It should define the lifecycle contract for stalled child worktree recovery.
- It should reference review feedback learning-loop vocabulary for root cause,
  prevention action, and verification.
- It should not redefine broader incident management.

The expected process classification for this incident is:

- root cause class: `process_rule_gap` or `policy_runtime_drift`;
- prevention action: `policy_rule_added` plus `regression_test_added`;
- verification: targeted supervisor lifecycle test plus full supervisor suite.

## Materialization Plan

1. Materialize one spec node from this proposal:
   `Supervisor Stalled Run Salvage Protocol`.
2. Add runtime policy vocabulary for:
   `stalled_run_salvage_required`,
   `review_salvaged_worktree_diff`, and
   `supervisor_stalled_run_salvage`.
3. Add watchdog or timeout handling around the child execution phase.
4. Write `runs/<run_id>-salvage.json` when dirty worktree mutation exists but
   normal sync/summary cannot complete.
5. Update `runs/latest-summary.md` for the failed stalled run.
6. Add regression tests with a fake executor that mutates the child worktree and
   never returns a normal successful result.
7. Add optional viewer/dashboard surfacing after the artifact exists.

## Acceptance Criteria

- A stalled dirty child worktree cannot leave `latest-summary` pointing only at
  an older run.
- A salvage artifact records worktree path, changed files, bounded-path status,
  diff summary, durable patch reference or bounded inline patch, phase, and
  recovery hint.
- The supervisor marks the run as failed/recoverable instead of silently
  hanging.
- Automatic canonical mutation remains disabled for salvaged diffs.
- A regression test covers mutation-before-stall and verifies summary plus
  salvage metadata.
- Manual adoption remains possible, but it is recorded as review-driven
  recovery, not as normal supervisor success.

## Risks

- Too much artifact detail could leak local paths or noisy diffs into review.
  The first artifact should keep compact metadata and relative paths.
- Too aggressive a watchdog could abort slow but healthy runs. The timeout
  should be configurable and scoped to missing progress after child mutation.
- Salvage recovery could become a bypass if adoption is automated too early.
  Initial adoption must remain human-reviewed.

## Open Questions

- Should the salvage artifact live only in `runs/`, or should accepted salvage
  decisions also create a curated evidence packet?
- Should `review_feedback_records.json` be extended to accept runtime incidents
  directly, or should runtime incidents get a separate policy artifact?
- Should `--recover-run <run_id>` be implemented in the first runtime PR or
  deferred until after watchdog behavior is proven?
