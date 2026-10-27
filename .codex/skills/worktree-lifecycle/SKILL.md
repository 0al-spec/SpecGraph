---
name: worktree-lifecycle
description: "Create, reuse, hand off and retire Git worktrees without losing local work or leaving abandoned environments. Use when a task needs isolation, a worktree-backed PR finishes, or old worktrees need auditing."
---

# Worktree lifecycle

A worktree is a temporary execution environment. Keep the task's result and
return path durable; do not make the directory itself the only record of work.
Use the existing task, PR or coordination log rather than inventing a registry.

## Choose and record the workspace

- Inspect the repository's registered worktrees and active tasks first. Reuse
  a suitable task worktree; ordinary sequential work may use the normal checkout.
  Create isolation when parallel work or unrelated local changes justify it.
- Record the path, branch/head, task or PR and intended disposition in the task's
  existing record. On retry, find that record before allocating another tree.
- Prefer worktrees beside the primary checkout. Do not manually nest worktrees
  inside other task trees. When a producer requires nested run worktrees, retain
  parent/run relationships and retire children before their parent.
- Keep notebooks, user data, databases and services used beyond the task at a
  stable project-data location. Keep build caches at the configured build paths.
  If persistent data already lives in a worktree, migrate and verify it before
  retiring the tree; update its actual consumers and source of truth.

## Close the task, not just the PR

Before calling the work complete, give its worktree one explicit disposition:

- **Active / handed off:** a real pending task or review needs the tree. Record
  its task/PR, exact head, local data, next action and return trigger.
- **Published:** the intended changes are pushed or merged, and any remaining
  local state is accounted for. Retire the execution tree when no consumer needs it.
- **Archived:** an abandoned, failed or alternative candidate is recoverable
  elsewhere, with its disposition and any unresolved review recorded. Retire the
  tree after verifying preservation. Archival does not approve or implement it.

A merged PR does not account for uncommitted files. A dirty tree is a reason to
inspect its contents, not a reason to keep it forever. Compare the candidate
with current code/specs and classify it as already incorporated, superseded,
a pending proposal, or unknown. Preserve uncertainty rather than cherry-picking
old policy into current canonical sources.

Use the producer's existing salvage or recovery path when available. Record
the preserved patch and review action; do not rerun an executor merely to retire
its old workspace.

For squash/rebase merges, a failed ancestor check alone does not prove the work
is unmerged. Check the PR's exact reviewed head and merge commit; where useful,
compare the actual patches or syntax. A current whole-file difference also
does not prove that a particular old change is missing.

## Inspect and preserve before removal

- Inspect HEAD, staged and unstaged changes, untracked **and ignored** paths,
  nested worktrees, submodules, symlinks and any live processes or consumers.
  A clean `git status` does not cover ignored notebooks or run evidence.
- Before switching the primary checkout, check incoming tracked paths against
  local untracked/ignored files. Preserve collisions and use
  `git switch --no-overwrite-ignore`; do not silently overwrite local data.
- Preserve productive work through the normal scoped PR. For archival, retain
  the source head and a reachable Git ref or bundle, staged/unstaged patches,
  untracked and needed ignored files, and a short restoration recipe.
- Verify that the backup actually contains the selected data. For nontrivial
  recovery, compare file hashes and exercise restoration of the important
  candidate or notebook. Preserve citations, history and pending review state.
- Record unresolved semantic work in a durable follow-up with source, current
  disposition and next action. A backup with no identifiable return path is
  storage, not task closure. Keep raw notes and private recovery data local.

## Remove with the appropriate tool

- For app-managed attached worktrees, use the app's archive operation and its
  ownership checks. Preserve needed ignored files separately. Do not work around
  an ownership or shared-worktree rejection with shell deletion.
- For ordinary Git worktrees, use `git worktree remove`. When a previously
  inspected dirty tree must be removed, use force only within the user's cleanup
  authorization, after its exact contents are verified recoverable and live
  consumers are migrated. Never use recursive deletion as a failed-remove fallback.
- Run cleanup mutations sequentially. Recheck the exact target/head/status
  before removal and stop for new changes or new consumers. Do not delete
  neighboring repositories or branches merely because their names look temporary.
- Prune dead registrations only after confirming their directories are absent
  and their heads remain reachable. Verify actual removal and report retained
  exceptions with a concrete next step.
- When safe, leave the primary checkout on the current default branch. Preserve
  other active work and user edits; do not force a checkout or reset.

The closeout should state: retained worktrees and why, removed/archived paths or
their manifest, durable data location, unresolved follow-ups, and the primary
checkout state. Fit this into the task's normal handoff; do not add a separate
approval ceremony or CI gate.
