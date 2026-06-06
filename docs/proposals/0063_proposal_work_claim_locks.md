# Proposal Work Claim Locks

## Status

Draft proposal

## Source Material

This proposal captures the operator question about whether SpecGraph can
validate that a proposal has already been taken into work and is effectively
locked.

Source draft:

- `docs/archive/proposal_sources/0063_proposal_work_claim_locks.md`

## Context

SpecGraph already has several locking and gate concepts:

- filesystem artifact locks protect concurrent writes;
- supervisor `gate_state` protects canonical spec transitions;
- worktree paths and branches identify bounded execution context;
- proposal tracking keeps proposal documents visible as runtime follow-up work.

None of those surfaces says that proposal work itself is currently claimed by a
person, branch, or automation slice. That creates avoidable coordination risk:
two branches can start changing the same proposal area, stale work can remain
implicit, and reviewers cannot quickly distinguish active ownership from old
draft residue.

## Problem

SpecGraph lacks a reviewable, machine-readable work-claim surface for proposal
implementation.

The missing signal is not a hard global mutex. The missing signal is a bounded
coordination record that can answer:

- which proposal is being worked;
- what scope is claimed;
- who or what owns the claim;
- which branch is expected to carry the work;
- which paths are in bounds;
- when the claim expires;
- whether multiple active claims overlap.

The same coordination gap appears one step earlier: selecting a new proposal ID
must not depend on a human eyeballing the current directory. Proposal ID
allocation needs one deterministic command that inspects all proposal surfaces
and either returns the next ID or reports a conflict.

## Goals

- Add a repository-tracked proposal work claim registry.
- Add a report-only builder that normalizes claim state.
- Add a gate that fails on malformed, stale, or duplicate active claims.
- Keep claim scope explicit and path-bounded.
- Make stale ownership visible without blocking unrelated proposal work.
- Provide a deterministic proposal ID allocator for new proposal authoring.
- Preserve existing proposal tracking, supervisor gates, and artifact locks.

## Non-Goals

- Implementing a distributed lock service.
- Preventing Git branches from being created.
- Requiring every proposal PR to have a claim on day one.
- Replacing reviewer judgment, CODEOWNERS, or GitHub branch protection.
- Granting authority to mutate canonical specs.
- Locking runtime artifacts at filesystem level.
- Solving cross-repository scheduling.
- Creating proposal markdown files automatically.

## Core Proposal

Introduce a **Proposal Work Claim** registry:

```text
tools/proposal_work_claims.json
```

Each active claim is a small ownership record:

```json
{
  "claim_id": "claim-0063-contract-20260606",
  "proposal_id": "0063",
  "scope": "contract-and-gate",
  "owner": "codex",
  "branch": "codex/proposal-agent-passport-lock-contract",
  "claimed_at": "2026-06-06T00:00:00Z",
  "expires_at": "2026-06-13T00:00:00Z",
  "allowed_paths": [
    "docs/proposals/0063_proposal_work_claim_locks.md",
    "tools/proposal_work_claims.json",
    "tools/supervisor.py"
  ],
  "related_pr": ""
}
```

The default status is `active`. Completed work should either remove the claim or
mark it as `released`. Expired claims remain visible in the report and block the
gate until they are refreshed, released, or removed.

## Runtime Artifacts

This proposal introduces:

```text
tools/proposal_work_claim_policy.json
tools/proposal_work_claims.json
runs/proposal_work_claim_report.json
make proposal-work-claims
make proposal-work-claims-gate
make proposal-id
```

The report is derived and read-only:

```json
{
  "artifact_kind": "proposal_work_claim_report",
  "schema_version": 1,
  "claim_count": 0,
  "entries": [],
  "blocking_findings": [],
  "canonical_mutations_allowed": false,
  "tracked_artifacts_written": false
}
```

The gate fails only on claim health problems:

- missing `claim_id`;
- invalid four-digit `proposal_id`;
- missing `scope`;
- active claim without `branch`;
- active claim without `allowed_paths`;
- active claim without `expires_at`;
- invalid `expires_at`;
- expired active claim;
- duplicate active claim for the same `(proposal_id, scope)`.

The gate does not fail because a proposal has no claim. That stricter policy can
be added later after the workflow proves useful.

## Proposal ID Allocation

New proposal authors should use:

```bash
make proposal-id
```

The allocator inspects:

- `docs/proposals/*.md`;
- `docs/archive/proposal_sources/*.md`;
- `docs/proposals_drafts/*.md`;
- `tools/proposal_runtime_registry.json`;
- `tools/proposal_promotion_registry.json`;
- `tools/proposal_work_claims.json`.

It returns the next four-digit ID after the highest used or reserved ID across
those sources. It fails instead of allocating when it finds conflicting markdown
slugs for the same proposal ID inside active proposal/draft namespaces or
malformed registry IDs. Historical archive-source slug collisions remain visible
as warnings so old draft naming does not block new allocation.

The allocator is read-only. It chooses an ID; it does not create proposal files,
edit registries, or claim ownership.

## Relationship To Existing Surfaces

- Proposal tracking answers "is this proposal represented by runtime,
  promotion, spec-trace, or no-runtime classification?"
- Proposal work claims answer "is this proposal scope currently owned by an
  active work branch?"
- Supervisor `gate_state` answers "may this spec transition continue?"
- Artifact locks answer "may this process write this file safely right now?"

Those concerns should remain separate.

## Acceptance Criteria

- `tools/proposal_work_claims.json` exists and is valid JSON.
- `tools/proposal_work_claim_policy.json` documents the blocking findings and
  claim contract.
- `tools/supervisor.py` can build `runs/proposal_work_claim_report.json`.
- `make proposal-work-claims-gate` passes for an empty registry.
- Duplicate or expired active claims fail the gate.
- `make proposal-id` reports the next deterministic proposal ID from proposal
  docs, source drafts, registries, and work claims.
- The proposal runtime and promotion registries track this proposal.

## Risks and Mitigations

- **False sense of safety**: a claim does not prevent Git edits. Mitigation:
  document this as coordination, not enforcement.
- **Stale claims**: active claims can outlive real work. Mitigation:
  `expires_at` is required and stale active claims block the gate.
- **Overhead**: mandatory claims for every PR may slow small edits. Mitigation:
  start with optional claims and only validate claims that exist.
- **Scope drift**: claimed paths can become too broad. Mitigation: reviewers
  inspect `allowed_paths` and may require narrower scope before merge.
