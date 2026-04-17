# Non-Escalating Fallback Isolation for Supervisor Runs

## Status

Draft proposal

## Problem

When the primary git worktree path fails, supervisor may fall back to a copied
workspace path. In the current design, degraded execution can expand child
executor privileges instead of preserving or reducing them.

This is architecturally backwards.

A degraded environment may justify:

- lower throughput
- less convenience
- more operator intervention
- refusing the run

It should not justify broader write or sandbox authority.

## Goals

- Preserve the invariant that fallback execution never expands authority.
- Keep isolation behavior monotonic under failure.
- Make degraded execution explicit and reviewable.
- Prefer fail-closed behavior over privilege escalation.

## Non-Goals

- Guaranteeing that every environment can always execute a run
- Designing a full containerized runtime for all future executors
- Eliminating copied-workspace fallback entirely if it remains safe

## Core Proposal

Fallback isolation may change the implementation of isolation, but it must not
increase the effective privilege of the child executor.

## Required Invariant

If the normal execution path has authority set `A`, then every fallback path
must run with authority:

- equal to `A`
- or narrower than `A`

It must never run with authority broader than `A`.

## Allowed Fallback Outcomes

If the normal git worktree cannot be created, supervisor may:

1. use a copied isolated workspace with the same sandbox policy
2. use a copied isolated workspace with a stricter sandbox policy
3. refuse the run as blocked or retryable

It must not silently switch into a more privileged executor mode.

## Copied Workspace Boundary

If copied-workspace fallback remains supported, it should be treated as a
bounded isolation surface rather than as a privileged bypass path.

That implies:

- no hidden expansion of approvals authority
- no hidden sandbox bypass
- minimal copied content needed for the run
- explicit visibility in run artifacts that fallback isolation was used

## Related Protocol Hardening

A degraded runtime should also harden, not loosen, machine contracts.

In particular:

- executor protocol violations should resolve to protocol error or blocked state
- missing structured outcome markers should not be treated as silent success

This keeps degraded execution legible instead of permissive.

## Supervisor Implications

After this proposal:

- fallback becomes a reliability aid, not a privilege escalation path
- operators can trust that runtime degradation does not silently widen power
- security and governance properties become easier to reason about

## Open Questions

- Should copied fallback workspaces exclude `.git` entirely and run as plain
  isolated directories?
- Should degraded execution require an explicit operator note in the run log?
