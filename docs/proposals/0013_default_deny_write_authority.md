# Default-Deny Write Authority for Supervisor Refinement

## Status

Draft proposal

## Problem

The current supervisor write-authority model is too permissive by default.

In particular, empty `allowed_paths` currently behaves like unrestricted write
authority. That means a node that does not explicitly define write scope may
still allow:

- arbitrary file sync back into canonical root
- broad candidate mutation inside the worktree
- new spec file creation by implication

This is the opposite of a zero-trust default.

The current model therefore relies too heavily on prompt discipline and
post-hoc validation instead of runtime authority enforcement.

## Goals

- Make supervisor write authority default-deny.
- Ensure every refinement run has a minimal bounded implicit scope.
- Require explicit authority expansion for new canonical files and broader
  writeback regions.
- Keep child materialization narrow and explicit.

## Non-Goals

- Restricting read access needed for bounded validation or graph reconciliation
- Removing explicit child-materialization authority
- Defining a full capability language for every future executor feature

## Core Proposal

Empty `allowed_paths` should no longer mean unrestricted authority.

Instead, the default implicit scope should be:

- the selected source spec file only

In other words, the fallback interpretation of missing write policy should be:

`allowed_paths = [source_spec_path]`

## Authority Tiers

### Tier 1. Implicit Base Scope

Every targeted refinement gets one implicit writable path:

- the selected source node file

This keeps the common case simple while remaining safe.

### Tier 2. Explicit Path Expansion

If a node needs additional writable paths, it must declare them explicitly in
`allowed_paths`.

Examples:

- a bounded sibling metadata file
- an explicit proposal artifact path
- a controlled child spec path

### Tier 3. Explicit Structural Authority

New spec creation should require both:

- a path match that allows the new file
- explicit run authority such as `materialize_one_child`

This avoids treating structural mutation as an accidental side effect of broad
path patterns.

## Required Runtime Behavior

After this proposal:

- validating changed files must reject out-of-scope paths by default
- sync-back selection must not widen scope when `allowed_paths` is absent
- child materialization must be impossible unless explicitly authorized
- the same write authority rules must hold in normal and degraded execution
  modes

## Why This Matters

SpecGraph treats specifications as governed artifacts, not casual notes.

That means the write model should say:

- what may change
- why it may change
- under which explicit authority

A missing policy should therefore collapse to a minimal safe default, not to
allow-all behavior.

## Supervisor Implications

This proposal makes write authority more legible:

- the selected node remains the default unit of mutation
- broader changes become explicit and reviewable
- post-hoc validators become a second line of defense rather than the only real
  boundary

## Open Questions

- Should proposal-lane artifacts use the same `allowed_paths` model or a
  distinct proposal-authority model?
- Should supervisor refuse nodes with wildcard `allowed_paths` that exceed one
  declared role boundary?
