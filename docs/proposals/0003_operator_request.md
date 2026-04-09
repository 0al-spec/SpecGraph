# Operator Request Contract for Supervisor Runs

## Status

Draft proposal

## Problem

The current `supervisor` runtime is growing a useful bounded execution surface,
but much of that surface is still exposed as low-level CLI flags and ad hoc
operator steering.

This creates several problems:

- the user-facing interface becomes harder to reason about as more run options
  accumulate
- external agents and GUI workflows have no stable, typed request envelope to
  target
- execution authority, mutation budgets, and stop conditions are described
  indirectly instead of being carried by one explicit request artifact
- future evaluator loops risk treating the supervisor as a bag of flags instead
  of a bounded execution kernel

Without a normalized request contract, the system remains difficult to steer
consistently from a viewer, a mediator, or a future metric-guided loop.

## Goals

- Define a single normalized `OperatorRequest` or `RunRequest` contract for
  bounded supervisor runs.
- Keep `supervisor` as an internal execution kernel rather than a primary
  user-facing interface.
- Make external callers such as GUI workflows, mediators, and evaluator loops
  target one structured request artifact instead of assembling many CLI flags.
- Carry execution authority, mutation budget, and stop conditions in a visible,
  reviewable form.
- Prepare the runtime for future orchestration without requiring immediate
  replacement of the current CLI.

## Non-Goals

- Immediate removal of the existing CLI flags
- Final wire format for every implementation environment
- A complete evaluator-loop specification
- A finished GUI or viewer integration
- Full autonomy for direct writes to canonical `main`

## Proposed Contract

The system should introduce a normalized run-scoped request object, tentatively
named `OperatorRequest`.

That request should be the primary way to express:

- requested run mode
- target spec or graph region
- bounded instruction
- authority grant
- mutation budget
- stop condition or completion expectation

The request contract should be narrow enough to support one bounded
intervention at a time rather than a whole plan of unrelated changes.

## Architectural Roles

### Supervisor as Kernel

`supervisor` should remain the bounded execution kernel that:

- performs one requested refinement, proposal emission, or application step
- validates the result
- returns structured run outcomes

It may retain a rich internal execution surface, but that surface should no
longer be treated as the primary operator interface.

### External Orchestration

Higher-level orchestration layers should construct one `OperatorRequest` and
delegate execution to the supervisor.

Likely callers include:

- a human operator through a GUI or viewer
- a mediator that reduces ambiguity before execution
- a future evaluator loop that selects the next bounded intervention

## Expected Request Fields

The exact schema is still open, but a minimal request should eventually express:

- `mode`
- `target`
- `instruction`
- `authority`
- `mutation_budget`
- `stop_condition`

Optional extensions may later include:

- execution profile
- selected node set
- context-pack reference
- provenance back to user intent or mediated intent

## Loop Relationship

The `OperatorRequest` contract should be the layer that lets a future evaluator
loop call the supervisor in a controlled way.

A long-term loop should look roughly like:

- observe graph state
- derive metrics or structural signals
- choose one bounded intervention
- issue one normalized request
- validate the result
- update graph state
- recompute metrics
- stop on plateau, oscillation, budget exhaustion, or review checkpoint

This proposal does not define that full loop. It defines the request surface
that such a loop should target.

## Safety Constraints

The request contract should not remove review boundaries.

Even with a normalized request, the system should preserve:

- human review checkpoints for constitutional changes
- bounded mutation discipline
- explicit authority grants for stronger actions
- supervisor ability to narrow or block unsafe execution

## Relationship to Existing Work

### SG-SPEC-0007

Mediated intent and ambiguity reduction should feed into `OperatorRequest`
rather than bypass it.

### SG-SPEC-0008

Project memory consultation and PageIndex-backed recall should help shape the
request context, but memory access is separate from the request contract itself.

### SG-SPEC-0009

The canonical runtime or spec-layer implementation of this proposal should live
through `SG-SPEC-0009` and its descendants.

### Evaluator Loop

A later evaluator-loop architecture should consume this request contract instead
of inventing a parallel execution interface.

## Open Questions

- What is the final typed schema for `OperatorRequest`?
- Which fields are mandatory for every run mode?
- How should request provenance link back to `UserIntent` or mediated intent
  artifacts?
- Which authority grants belong in the request versus being inferred by the
  supervisor?
- How should request objects be stored, surfaced in the viewer, and retained in
  runtime history?
