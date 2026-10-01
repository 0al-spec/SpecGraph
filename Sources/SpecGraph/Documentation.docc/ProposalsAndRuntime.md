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

## Readiness policy refactors

Trace current producer guarantees before extracting a fallback into a
specification. The repaired handoff no-op fallback was redundant because the
repair-loop producer already handled clean no-op readiness. Artificial input
tests alone did not establish reachability through that production chain.

Candidate repair readiness now consumes source facts and returns a typed
outcome from one boolean specification. `no_op_repair_loop` remains independent
of `ready`: findings can block a ready pre-SIB graph with no actions while the
no-op observation stays true. Preserve those projections and test optional
decision traces. Evaluate confirmed redundant decisions and restored policy
boundaries alongside complexity measurements.

## Executor transcript diagnostics

Nested executor stderr can include operator notes, specification text, and
diffs alongside runtime logs. Migration vocabulary alone is not evidence of a
runtime failure. Require explicit state failure diagnostics such as
`failed to open state db`, `failed to initialize state runtime`, or
`state db discrepancy`; keep ordinary migration plans and successful migration
logs out of environment findings. Test both the classifier and the supervisor
run artifact so narrative text cannot contaminate the executor-environment gate.
Historical run artifacts and pending human review remain historical evidence;
a classifier fix does not approve a previously retained candidate.
