# Role-First Semantic Bias for Supervisor Refinement

## Status

Implemented

Runtime realization:

- `tools/supervisor.py` derives role-legibility profiles for canonical
  subtrees and emits `role_obscured_node` and `bookkeeping_only_node` signals.
- Those signals are visible through graph-health overlays, refactor/proposal
  queues, decision-inspector queue rules, and the dashboard health section.
- `tests/test_supervisor.py` covers role-legibility detection, false-positive
  protection, proposal-first queue routing, prompt guidance, and dashboard
  projection.

## Problem

SpecGraph already has useful pressure toward:

- bounded atomic specs
- explicit lineage
- reviewable gates
- proposal-first restructuring

That pressure is valuable, but it can still drift into a failure mode where a
subtree remains structurally valid while becoming semantically weak.

The recurring symptom is not necessarily a malformed node.

It is a node that stops reading as a meaningful role in the system and starts
reading mainly as bookkeeping about:

- sibling spec IDs
- edge placement
- ownership handoff
- delegation routing
- slice boundaries

This creates a graph that may still be:

- valid YAML
- locally atomic
- lineage-consistent
- reviewable by machine checks

yet still difficult for a human to read as a coherent model of the system.

## Why This Matters

SpecGraph is most useful when its subtrees can be read as a semantic model of a
system, not merely as a record of refinement operations.

If a subtree can only be explained by saying:

- "this node owns the edge"
- "this child consumes the segment"
- "that sibling holds the handoff"

then the graph is beginning to describe its own decomposition mechanics more
than the system it is supposed to govern.

That weakens:

- human readability
- agent comprehension
- stability of future refinement
- confidence that a subtree could later project into a meaningful tech-spec or
  implementation-facing representation

## Design Constraint

This proposal intentionally does **not** require explicit reference to any
particular downstream language or IR.

In particular, it does not require SpecGraph to name or depend on Hypercode.

The desired bias is more general:

- a good node should read as a human-comprehensible system role or composed
  function
- that role need not be object-oriented
- that role may be structural, process-oriented, functional, policy-oriented,
  or protocol-oriented

## Goals

- Introduce a role-first semantic bias for supervisor-guided refinement.
- Prefer nodes that read as meaningful system roles or composed functions.
- Allow multiple valid role families, not just entity or component nouns.
- Reduce the chance of bookkeeping-only child materialization.
- Encourage rewrite or merge when decomposition no longer improves legibility.
- Keep the bias architecture-neutral and compatible with non-OOP styles.

## Non-Goals

- Requiring explicit Hypercode terminology in specs
- Mandating object-oriented decomposition
- Banning every boundary, edge, or handoff node categorically
- Making role legibility a hard validity error for canonical specs
- Replacing existing atomicity, gate, or lineage contracts

## Core Proposal

Supervisor should adopt a **role-first semantic bias**.

This means that refinement should prefer nodes that can be understood as a
system-facing role, function, or invariant before they are understood as a
decomposition artifact.

The guiding question should be:

> What responsibility does this node play in system meaning?

not:

> Which neighboring specs does this node own, consume, or route between?

## Acceptable Role Families

A valid node role does **not** have to be a component or object.

Supervisor should treat all of the following as first-class legitimate node
families:

- `entity` — a thing, aggregate, or bounded domain object
- `process` — a staged activity or flow of work
- `transformation` — a mapping, normalization, evaluation, or conversion
- `boundary` — a reviewable interface, handoff, or scope-limiting contract
- `policy` — a governing rule set or decision contract
- `protocol` — an interaction contract or state-transition interface
- `aggregate_role` — a grouped concern that synthesizes multiple child roles

This means a subtree may be healthy whether it reads like:

- `Calculator -> UI -> Display -> Keyboard`
- `InputParsing -> ExpressionNormalization -> OperationDispatch`
- `AdmissionBoundary -> ValidationPolicy -> ResolutionProtocol`

The criterion is not object shape.

The criterion is whether the subtree exposes meaningful semantic roles.

## Node-Role Test

A node should be considered role-legible when a human can summarize it in one
short sentence that:

- uses system-facing language
- does not require neighboring spec IDs for comprehension
- states either the node's bounded responsibility or the composed function it
  adds

Examples:

- "This node defines the gateway-entry contract for proposal/split readiness."
- "This node defines normalization of user-entered arithmetic expressions."
- "This node defines the review gate for retrospective refactor application."

Poor summaries tend to sound like:

- "This node owns the direct edge under sibling X."
- "This node holds the downstream segment while the parent keeps the rest."
- "This slice exists so the other slice can compose the next handoff."

## Composed-Function Test

For multi-child or aggregate nodes, the node should answer:

> What new function, invariant, or reviewable contract becomes true because
> these child concerns are composed here?

This protects against a common failure mode where a parent node merely restates
that children exist, but does not say what semantic value the composition adds.

If the composition does not synthesize a new readable function or contract, the
aggregate is weak.

If the child split does not introduce a separately nameable role or invariant,
the child is weak.

## Readable Semantic Projection Test

A bounded subtree should preferably admit a short human-readable projection as
an outline of system meaning.

That outline should:

- be understandable without a chain of spec IDs
- preserve the main role boundaries
- look like a small semantic map rather than a decomposition log

This does not require one exact target notation.

It simply means that a healthy subtree should be recitable as:

- a compact structured outline
- a small concept map
- or a concise role tree

If a subtree cannot be restated that way, it is a signal that the graph may be
drifting away from semantic clarity.

## Discouraged Node Shapes

The following shapes should be treated as warning signs unless the node also
states a clear distinct role or invariant.

### 1. Edge-Only Bookkeeping

A node primarily exists to say:

- one edge exists
- one adjacent node consumes another
- one route is direct while another route is indirect

without adding a distinct system-facing contract.

### 2. Segment-Only Delegation

A node mostly exists to preserve a partial path segment while nearby nodes own
the rest of the story.

### 3. Handoff-Only Serialization

A chain of nodes repeats handoff or ownership language but adds little new
semantic grouping.

### 4. Spec-ID-Dependent Meaning

A node cannot be understood without following multiple neighboring `SG-SPEC-*`
references just to recover what system role it serves.

These are not always invalid.

But they should create pressure toward:

- rewrite
- merge
- regrouping

instead of another layer of decomposition.

## Supervisor Behavior

This proposal should affect supervisor behavior in four places.

### 1. Prompt Guidance

Child-executor prompts should explicitly prefer:

- human-readable system roles
- composed functions
- separately nameable invariants

They should explicitly discourage:

- child creation whose main meaning is edge, segment, or slice bookkeeping
- decomposition that only repartitions already-readable structure

### 2. Graph-Health Interpretation

Role-legibility and bookkeeping-drift signals should be interpreted through a
broader semantic lens.

In particular:

- a valid role may be entity-like, process-like, transformation-like,
  boundary-like, policy-like, or protocol-like
- the detector should not penalize non-OOP subtrees merely for being
  process-oriented or functional in style
- the detector should penalize bookkeeping-only decomposition more strongly
  when no distinct role or composed function can be named

### 3. Recommended Actions

When role-obscuring or bookkeeping-only patterns are detected, supervisor
should prefer:

- `rewrite_node_role_boundary`
- `merge_bookkeeping_slice`
- `rebalance_subtree_shape`

before it prefers:

- further child materialization
- narrower edge slicing
- another serial handoff node

### 4. Proposal and Refactor Bias

When emitting refactor or governance proposals, supervisor should frame the
problem in semantic terms:

- restore readable role boundaries
- merge slices that do not add a distinct function
- regroup children under a stronger aggregate role

rather than only in structural terms such as chain length or node count.

## Soft Guidance, Not Hard Validity

This proposal should begin as **soft guidance** rather than hard validity.

That means:

- no immediate hard failure solely because a node is role-weak
- no automatic rejection of every edge or boundary node
- no forced rewriting of legacy specs on first detection

Instead, the bias should first shape:

- prompt language
- graph-health interpretation
- recommended actions
- proposal framing

Later governance may decide whether some aspects deserve stronger enforcement.

## Relationship to Existing Work

### Proposal 0008

[0008_refinement_shape.md](/Users/egor/Development/GitHub/0AL/SpecGraph/docs/proposals/0008_refinement_shape.md)
focuses on subtree shape pathologies such as serial ladders and
over-atomization.

This proposal complements it by adding a semantic quality test:

- not only "is the subtree too serial?"
- but also "do the nodes still read like meaningful roles?"

### SG-SPEC-0049

[SG-SPEC-0049.yaml](/Users/egor/Development/GitHub/0AL/SpecGraph/specs/nodes/SG-SPEC-0049.yaml)
already defines:

- `node_role`
- `composed_function`
- `role_obscured_node`
- `bookkeeping_only_node`

This proposal strengthens the intended interpretation of those ideas and
generalizes them beyond component-like structures.

### Proposals 0012-0016

The recent supervisor-trust proposals strengthen:

- approval semantics
- authority discipline
- fallback safety
- artifact integrity
- policy inspection

This proposal adds a complementary semantic-quality layer:

- not "may the runtime do this?"
- but "should the runtime prefer this shape of refinement?"

## Implementation Direction

The intended order of adoption is:

1. child-executor prompt guidance
2. graph-health heuristic refinement
3. proposal and refactor recommendation wording
4. decision-inspection visibility for role-first judgments

This keeps the first step low-risk and immediately useful.

## Open Questions

- Should supervisor expose an explicit `readable_semantic_projection` note in
  graph-health artifacts, or is that too prescriptive for now?
- Should some legacy nodes be allowed to remain structurally weak if they are
  already stable historical lineage?
- How strongly should boundary-like nodes be protected from false positives
  when their role is legitimate but narrow?
