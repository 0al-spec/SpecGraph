# Reflective Co-Evolution of Proposals and Runtime Realization

## Status

Draft proposal

## Problem

SpecGraph is already building several valuable layers in parallel:

- canonical graph semantics
- proposal documents
- backlog tasks
- supervisor runtime behavior
- derived run artifacts and graph-health inspection

But these layers still tend to move at different speeds.

In practice, one recurring failure mode is:

- proposals accumulate on one side
- runtime scripts lag behind
- backlog grows as a separate planning surface
- reflection remains descriptive rather than operational

This weakens the central bootstrap promise of SpecGraph:

> the system should improve itself through reflective observation, bounded
> intervention, and renewed observation

Without a stronger co-evolution rule, the project risks producing:

- a design archive that the runtime does not embody
- script behavior that is not yet anchored to the active proposal set
- a backlog that grows faster than reflective closure
- self-observation that notices gaps without turning them into synchronized
  improvements

## Why This Matters

SpecGraph is not intended to be only:

- a graph of ideas
- a supervisor runtime
- a pile of backlog items

It is intended to be a self-improving governed system.

That means proposal processing should not be treated as a purely documentary
lane.

It should be part of a closed reflective loop:

1. observe a gap or pathology
2. normalize it into a proposal
3. materialize bounded runtime or tooling changes where appropriate
4. add validation and observation hooks
5. re-observe the resulting behavior

This is how SpecGraph remains alive rather than merely well-documented.

## Goals

- Define proposal processing as part of a reflective self-improvement loop.
- Require synchronous consideration of runtime or tooling realization when a
  proposal affects active supervisor behavior.
- Keep proposals, scripts, tests, and observation artifacts in tighter
  alignment.
- Reduce drift between accepted design direction and current operational
  behavior.
- Make backlog growth a derived result of reflective work rather than a
  separate planning universe.

## Non-Goals

- Requiring every proposal to be fully implemented before it can be written
- Forcing immediate runtime changes for purely exploratory or distant proposals
- Eliminating backlog documents entirely
- Replacing bounded implementation sequencing with one giant continuous branch
- Allowing runtime code to self-authorize constitutional changes

## Core Proposal

SpecGraph should adopt a **reflective co-evolution rule**:

> Proposals that materially affect active runtime behavior should be processed
> together with bounded runtime-realization and observation work, not as a
> disconnected documentation stream.

This does not mean every proposal must be implemented immediately.

It means every relevant proposal should explicitly answer:

- what runtime or tooling surface it touches
- whether a bounded implementation slice is feasible now
- what validation or observation artifact should accompany that slice
- how the system will re-observe the result

## Proposal Processing Packet

When a proposal is considered implementation-relevant, its processing should
carry a minimal co-evolution packet.

That packet should identify at least:

- affected runtime surface
  - for example `tools/supervisor.py`, validators, viewers, reports
- implementation posture
  - `document_only`
  - `bounded_runtime_followup`
  - `synchronous_runtime_slice`
  - `deferred_until_canonicalized`
- required validation surface
  - tests, lint, deterministic checks, replay runs, inspection outputs
- expected observation surface
  - graph-health signals, trace artifacts, performance metrics, decision
    inspection, or other derived evidence

The important rule is not one final schema.

The important rule is that proposal processing must stop being blind to runtime
realization.

## Co-Evolution Modes

This proposal recognizes several legitimate modes.

### 1. Document-Only

Appropriate when the idea is still exploratory or when the relevant runtime
surface does not yet exist.

### 2. Bounded Runtime Follow-Up

Appropriate when the proposal is stable enough that it should immediately
produce backlog tasks or a next implementation slice, but not necessarily in
the same commit.

### 3. Synchronous Runtime Slice

Appropriate when the proposal addresses an already active runtime surface and a
small direct improvement can be implemented now in:

- `tools/`
- `tests/`
- or adjacent derived tooling

This is the mode most aligned with bootstrap self-improvement.

### 4. Deferred Until Canonicalized

Appropriate when a proposal first needs acceptance into canonical graph
semantics before runtime changes would be legitimate.

## Required Reflective Closure

When a proposal enters either:

- `bounded_runtime_followup`
- or `synchronous_runtime_slice`

the system should aim to close a minimal reflective loop:

1. proposal normalized
2. bounded runtime or tooling change made
3. validation added or updated
4. observable artifact emitted or inspected
5. residual gap recorded if the loop is not yet complete

This keeps self-improvement concrete.

It also prevents the common failure mode where reflection produces only more
text and more backlog.

## Relationship to Existing Work

### Constitution

[CONSTITUTION.md](/Users/egor/Development/GitHub/0AL/SpecGraph/CONSTITUTION.md)
already states that drift must be corrected both ways:

- runtime behavior must be anchored in specs
- governing behavior must have an operational realization path

This proposal strengthens that principle by making proposal processing itself a
place where the loop must be considered explicitly.

### Proposal 0004

[0004_evaluator_loop.md](/Users/egor/Development/GitHub/0AL/SpecGraph/docs/proposals/0004_evaluator_loop.md)
defines the high-level reflective loop.

This proposal makes that loop more operational by stating that proposal work
and runtime/tooling work should co-evolve whenever the proposal affects active
execution surfaces.

### Proposal 0007

[0007_supervisor_performance.md](/Users/egor/Development/GitHub/0AL/SpecGraph/docs/proposals/0007_supervisor_performance.md)
adds measurement of runtime yield.

This proposal depends on that spirit:

- runtime slices should be observed
- not merely merged

### Proposal 0019

[0019_spec_to_code_trace_plane.md](/Users/egor/Development/GitHub/0AL/SpecGraph/docs/proposals/0019_spec_to_code_trace_plane.md)
provides a path to inspect how much proposal meaning is actually embodied in
code and tests.

That trace plane is one of the future places where co-evolution status should
become visible.

### Proposal 0021

[0021_deterministic_transition_checks_and_validator_profiles.md](/Users/egor/Development/GitHub/0AL/SpecGraph/docs/proposals/0021_deterministic_transition_checks_and_validator_profiles.md)
helps formalize the transition side.

This proposal complements it by focusing on synchronized realization and
re-observation, not only transition legality.

## Backlog Implication

Backlog should increasingly be treated as a projection of the reflective loop,
not as an unrelated planning list.

That means tasks should increasingly capture:

- proposal normalization
- runtime realization
- validation hardening
- observation and trace closure

as one connected chain.

## Implementation Direction

The intended order of adoption is:

1. tag proposals with implementation posture
2. reflect that posture in backlog generation
3. start pairing proposal-processing work with bounded `tools/` and `tests/`
   slices by default where appropriate
4. expose realization and observation status through trace or inspection
   artifacts

## Open Questions

- Should co-evolution posture live in proposal metadata, a sidecar artifact, or
  a derived index?
- How should purely constitutional proposals be distinguished from proposals
  that should immediately drive runtime-tooling work?
- When should a proposal be blocked on missing runtime realization, and when is
  backlog generation sufficient?
