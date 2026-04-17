# Atomic Artifact Store and Collision-Safe Allocation for Supervisor

## Status

Draft proposal

## Problem

Supervisor already produces valuable runtime artifacts:

- run logs
- latest summaries
- proposal queues
- refactor queues
- structured proposal artifacts

But the artifact store is still too fragile for a governance runtime.

Current risks include:

- direct writes without atomic replace
- concurrent lost updates
- partial JSON files after interruption
- timestamp-based collisions in run or worktree identifiers
- sequential spec ID allocation without reservation or locking

This is acceptable in a bootstrap script. It is not acceptable in a trustworthy
governance kernel.

## Goals

- Make runtime artifacts atomic and corruption-resistant.
- Add lock discipline around shared artifact mutation.
- Prevent identifier collisions under parallel or repeated runs.
- Make spec ID allocation safe for child materialization.

## Non-Goals

- Building a distributed coordinator
- Solving every future multi-operator concurrency problem at once
- Replacing simple JSON artifacts with a database immediately

## Core Proposal

Supervisor should treat artifact persistence as a bounded transactional layer.

## Atomic Write Contract

Shared artifacts must be written using:

- temporary file creation in the same directory
- complete payload write and flush
- atomic replace into the target path

This applies at minimum to:

- run logs
- latest summary
- proposal queue
- refactor queue
- proposal artifacts

## Locking Contract

Shared mutable artifacts should use lock discipline so concurrent runs cannot
silently overwrite each other.

At minimum, there should be locks for:

- queue mutation
- latest-summary mutation
- reserved spec ID allocation

## Collision-Safe Identifiers

Run IDs, worktree names, and branch names should not rely only on
second-resolution timestamps.

They should include at least one collision-resistant element such as:

- `time_ns`
- monotonic counter under lock
- UUID suffix

## Reserved Spec ID Allocation

Sequential spec IDs should not be allocated by a naive `max + 1` scan under
possible parallel execution.

Instead, supervisor should use a reserved allocation step with:

- lock protection
- durable reservation artifact
- deterministic release or promotion semantics

## Corruption-Tolerant Reads

Artifact consumers should degrade safely when a shared artifact is malformed.

That means:

- invalid queue JSON should not crash the whole supervisor
- malformed artifacts should surface as recoverable findings
- repair or replacement should be explicit

## Supervisor Implications

After this proposal:

- shared artifacts become safer under interruption and concurrency
- queue state becomes less vulnerable to silent corruption
- child materialization can reserve IDs without accidental collision
- the runtime moves closer to a real artifact store rather than ad hoc file I/O

## Open Questions

- Should reserved spec IDs live under `runs/`, a dedicated allocator file, or a
  future proposal-lane structure?
- Which artifacts should remain best-effort local caches versus treated as
  integrity-critical state?
