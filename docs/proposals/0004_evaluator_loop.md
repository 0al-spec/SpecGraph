# Evaluator Loop for Metric-Guided SpecGraph Improvement

## Status

Draft proposal

## Problem

SpecGraph is moving toward a system where bounded agent runs can refine specs,
emit proposals, and eventually improve graph quality with limited human
intervention.

Today, the system already has several ingredients:

- canonical spec nodes
- a proposal lane
- supervisor-driven bounded refinement
- project-memory consultation policy
- an emerging operator request layer

What is still missing is a formal loop that decides:

- what the next bounded intervention should be
- how graph improvement is measured
- when the loop should stop
- when the loop must escalate to human review

Without this layer, the system risks becoming a collection of isolated
refinement actions rather than a controlled optimization process.

## Goals

- Define an evaluator loop that repeatedly observes graph quality, selects one
  bounded intervention, runs the supervisor, validates the result, and measures
  graph delta.
- Make metric-guided graph improvement an explicit architectural concept rather
  than an informal aspiration.
- Keep the supervisor as a bounded execution kernel rather than the owner of the
  whole optimization process.
- Support future metrics such as `pre-SIB`, `SIB`, and related graph-quality
  signals without hardcoding one specific metric family too early.
- Define mandatory stop conditions so the system does not run indefinitely or
  optimize blindly.

## Non-Goals

- Final formulas for `pre-SIB`, `SIB`, or any other future metric
- Full autonomy for direct writes to canonical `main`
- A finished orchestration implementation
- A final experiment framework for research or benchmark runs
- Replacement of human review for constitutional changes

## Proposed Loop

### 1. Observe

The evaluator gathers the current state needed to reason about graph quality.

Inputs may include:

- canonical spec graph
- proposal-lane state
- project memory such as PageIndex-backed recall
- supervisor run artifacts
- derived queues and structural signals

The evaluator should distinguish:

- canonical graph truth
- repository-tracked proposal state
- ephemeral runtime detail

### 2. Assess

The evaluator computes a bounded set of quality observations.

Early observations may be heuristic:

- oversized nodes
- weak lineage
- repeated split pressure
- stalled maturity
- proposal conflicts

Later observations may include formal metric families such as:

- `pre-SIB`
- `SIB`
- observability and verifiability related measures

The important point is that assessment should produce a machine-readable delta
target, not just a vague impression that the graph feels weak.

### 3. Select One Intervention

The evaluator chooses one bounded next step.

Examples:

- refine one spec node
- emit one split proposal
- strengthen one proposal-lane contract
- reconcile one ancestor boundary
- request one mediated clarification

The loop must not choose multiple unrelated interventions in one step.

### 4. Execute Through Supervisor

The evaluator does not mutate the graph directly. It issues one normalized run
request to the supervisor.

That request should eventually be expressible through the `OperatorRequest`
layer rather than through a large collection of CLI flags.

### 5. Validate Result

The run result must pass structural and semantic checks before it is considered
for quality comparison.

Validation should include:

- schema and YAML validity
- relation semantics
- mutation-budget compliance
- refinement acceptance classification
- proposal-lane or canonical-boundary compliance

### 6. Compare Metric Delta

The evaluator compares the post-run state to the pre-run state.

The output should answer:

- did the targeted signal improve
- did a global quality metric improve, hold, or regress
- did the run create new debt elsewhere
- was the change a no-op, oscillation, or false improvement

### 7. Decide Next State

The evaluator should then choose exactly one of:

- continue with another bounded intervention
- stop on plateau
- stop on regression
- stop on oscillation or repeated no-op
- escalate to human review
- advance a proposal toward application

## Architectural Roles

### Evaluator

Owns graph observation, metric comparison, and stop conditions.

### Supervisor

Owns bounded graph mutation, proposal emission, application paths, and
validation gates for a single requested run.

### Mediator

Owns ambiguity reduction, intent clarification, terminology alignment, and
translation from human goals into bounded requests.

### Human

Remains final authority for:

- constitutional changes
- merges into `main`
- metric definition changes
- authority-boundary changes

## Stop Conditions

The evaluator loop should not rely on a single stop rule.

Required stop conditions should include:

- plateau: the targeted metric no longer improves meaningfully
- regression: quality falls below the previous state
- oscillation: repeated changes undo one another
- repeated no-op: several runs fail to produce meaningful delta
- review checkpoint: a constitutional or governance-sensitive change appears
- budget exhaustion: run budget, token budget, or intervention budget is spent

## Human Review Checkpoints

Metric improvement alone must not be treated as authorization to merge or to
rewrite canonical governance.

Human review remains mandatory when the run:

- changes constitutional or governance semantics
- changes authority boundaries
- alters canonical ontology terms or relation contracts
- creates a proposal that affects multiple graph regions beyond the current
  bounded scope

## Relationship to Existing Work

### Proposal Lane

This loop should first optimize safely inside the proposal lane before it is
trusted with stronger canonical effects.

### SG-SPEC-0008

Project memory policy matters here because evaluator quality depends on whether
the loop can distinguish:

- local project memory
- external browsing
- recalled project constraints
- currently observed graph state

### SG-SPEC-0009

The evaluator should eventually express its selected intervention through a
normalized `OperatorRequest` contract rather than through ad hoc flags.

### Vocabulary / Ubiquitous Language

The loop will need stable, machine-readable terminology for:

- metrics
- intervention classes
- stop conditions
- regressions
- oscillation
- plateau

So the evaluator proposal and the vocabulary proposal should evolve together.

## Suggested Next Spec Slices

- `Evaluator intervention selection contract`
- `Metric delta and regression classification`
- `Plateau and oscillation stop conditions`
- `Review checkpoint semantics for autonomous loops`

## Open Questions

- What is the minimal metric interface before `pre-SIB` and `SIB` are fully
  defined?
- Should the evaluator operate only on repository-tracked state, or may it use
  runtime artifacts in assessment?
- When should proposal-lane improvement count as graph improvement if canonical
  graph state has not yet changed?
- What is the right balance between local targeted metrics and global graph
  quality metrics?
- How should the evaluator distinguish a useful temporary regression from a real
  failure?
