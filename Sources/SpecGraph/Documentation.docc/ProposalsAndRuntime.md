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

## RFC 0221 subject-address preparation

RFC 0221 remains review-only, not canonical adoption. Its subject-address read
model preparation builds on existing candidate Requirement and criterion IDs
and `acceptance_criteria_refs`. It proposes immutable workspace scope,
identified criterion records, separate identity/revision/containment,
`lookup_exact` and `lookup_current`, and explicit unresolved outcomes.

Reads must not allocate IDs or silently match legacy strings to identities.
Candidate-local references require reviewed workspace binding before becoming
durable subject references. Migration, runtime implementation and Hypercode
integration remain separate stages. The preparation and supervisor evidence
are documented in `docs/reviews/0221_subject_address_read_model.md` and the
RFC 0221 canonical adoption review packet. A successful draft refinement does
not adopt the proposal or change frozen SG-SPEC-0019.

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

### Curated contract completeness

When curating a supervisor candidate from an RFC, compare every transition and
lookup result with the source contract: preserve revision advancement, separate
lineage from disposition, identify every relation endpoint, and define failure
outcomes for ambiguous identity scopes. Update the curated artifact digest and
record corrections as curation, not as evidence verified by the original run.

## RFC 0221 canonical contract review

SG-SPEC-0068 is the outlined RFC 0221 child candidate, pending human approval.
The approval packet is `docs/reviews/0221_canonical_contract_approval.md`.
It proposes workspace-scoped subject identity, revisions, transitions and exact
lookup while preserving frozen SG-SPEC-0019 and its one-to-one canonical
supersession contract. Preparation and passed checks are not adoption.

Review must record explicit human approval of the exact bounded contract before
merge. Storage, allocator, physical history and source migration remain deferred.
Read-model implementation follows separately; no runtime conformance is claimed.
