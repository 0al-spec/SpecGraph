# Proposals and Runtime Evidence

SpecGraph treats proposal records and runtime evidence as connected surfaces.

## Proposal Records

Proposal markdown under `docs/proposals/` describes bounded changes and their
intended relationship to canonical specifications. Changes that affect proposal
documents should include matching tracking material or an explicit
documentation-only classification.

Before assigning a proposal ID, update the checkout that `make proposal-id`
will scan. Fetching alone is not sufficient: `git fetch origin --prune` updates
remote-tracking refs, but a stale local branch can still allocate an ID that
already exists on `origin/main`.

Use `make proposal-id` only after updating `main` with `git pull --ff-only`, or
after rebasing or merging the task branch onto `origin/main`. Then check the
candidate ID across local files, remote refs, local worktrees, and open GitHub
PRs. The open-PR check should inspect PR metadata, changed proposal/source
paths, and diffs for PRs that touch proposal registries; metadata alone is not
enough because a PR can claim an ID only through files or registry content.

If any branch, worktree, proposal file, registry entry, or open PR already uses
the candidate ID, do not reuse it. Synchronize with `main`, coordinate with the
active PR owner if needed, and allocate the next deterministic ID.

## Runtime Evidence

Runtime evidence lives in generated registries, viewer-facing JSON, and local
run artifacts. Evidence should support claims about realized behavior without
turning local runtime artifacts into canonical documentation by accident.

## Validation Gate

Use the proposal tracking gate when proposal documentation changes:

```bash
make proposal-tracking-gate
```
