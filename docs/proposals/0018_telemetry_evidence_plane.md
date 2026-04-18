# Telemetry Evidence Plane for SpecGraph

## Status

Draft proposal

## Problem

SpecGraph is growing as a canonical graph of:

- bounded semantic roles
- lineage and supersession
- review gates
- proposal and refinement structure

But it still lacks a formal answer to one important question:

> How should runtime observations relate back to canonical graph meaning?

Without a governing answer, telemetry tends to fall into one of two bad
shapes:

- it remains an external dashboard concern with weak relation to graph nodes
  and edges
- or it starts leaking raw runtime detail into canonical specs, which makes
  the graph harder to read and maintain

This leaves a gap between:

- what the graph says should matter
- what the runtime actually does
- and what evidence a reviewer or operator can inspect when evaluating system
  behavior, adoption, or policy outcomes

## Why This Matters

SpecGraph becomes much more valuable if it can be read not only as a semantic
map, but as a semantic map that can be inspected against real evidence.

That enables several future capabilities:

- graph overlays backed by live or historical evidence
- decision inspection for why a resolver, selector, or policy chose one path
- adoption and outcome attribution that can be traced back to graph meaning
- review workflows that can incorporate runtime evidence without confusing it
  with canonical truth

This is especially important for a system that increasingly wants:

- human-readable graph structure
- inspectable lineage
- policy-aware runtime behavior
- projection into downstream tech specs or implementation surfaces

In short:

the graph should not become telemetry storage, but telemetry should be able to
act as evidence for the graph.

## Goals

- Define a formal evidence-plane concept adjacent to canonical SpecGraph.
- Introduce a readable semantic chain from intent through runtime and outcome.
- Separate the roles of traces, metrics, logs, and provenance records.
- Keep runtime signals derived and inspectable rather than canonical by
  default.
- Enable graph overlays and decision inspection without forcing runtime detail
  into core spec nodes.
- Make delayed outcome or adoption attribution first-class instead of treating
  every relationship as strict parent/child execution.
- Keep the proposal stack-neutral while allowing strong implementation profiles.

## Non-Goals

- Mandating one telemetry vendor or backend
- Defining the final storage engine for evidence ingestion
- Requiring every SpecGraph deployment to adopt one observability stack
- Encoding raw telemetry payloads into canonical spec YAML
- Replacing product analytics, warehouse analytics, or incident tooling
- Allowing telemetry alone to rewrite canonical graph truth automatically

## Core Proposal

SpecGraph should recognize a **telemetry evidence plane** as a derived layer
that sits adjacent to canonical graph semantics.

The canonical graph defines:

- bounded semantic roles
- reviewable contracts
- topology and lineage
- what kinds of evidence are meaningful for a node or edge

The evidence plane holds:

- runtime traces
- aggregated metrics
- correlated logs or events
- provenance records
- outcome and adoption observations linked back to graph meaning

This keeps a clear distinction:

- canonical specs answer what the system means and how it is governed
- evidence answers what was observed in runtime behavior and how that behavior
  relates back to the graph

## Semantic Evidence Chain

The project should adopt one canonical conceptual chain for evidence
attribution:

`Intent -> SpecNode -> Artifact -> RuntimeEntity -> Outcome -> Adoption`

This chain is not necessarily a single parent/child tree in storage or traces.

It is a semantic attribution model.

The intended meaning is:

- `Intent` identifies the originating request, operation, or user/system aim
- `SpecNode` identifies the graph role or contract that the intent resolved
  through
- `Artifact` identifies the generated or selected tech-spec, config, build,
  release, or other concrete realization
- `RuntimeEntity` identifies the executing service, worker, agent, function,
  process, or other runtime surface
- `Outcome` records what happened
- `Adoption` records whether value was later realized, retained, or attributed

This gives the graph a readable bridge from semantic governance to actual
runtime evidence.

## Signal Roles

This proposal distinguishes the jobs of telemetry signals.

### Traces

Traces should primarily answer:

> What path did this concrete intent or execution follow?

Traces are the right place for:

- execution path continuity
- causal links between stages
- latency and error visibility at request or operation scope
- correlation from one runtime step to another

### Metrics

Metrics should primarily answer:

> How much, how often, how fast, and with what aggregate outcome?

Metrics are the right place for:

- request volumes
- durations
- error ratios
- coverage ratios
- adoption counts
- adoption lag distributions

Metrics should prefer low-cardinality attributes suitable for stable
aggregation.

### Logs and Events

Logs or structured events should primarily answer:

> Why did the system decide this?

They are the right place for:

- rule matches
- selector decisions
- policy allow or deny outcomes
- degradation or fallback reasons
- rich provenance context that is too verbose for span attributes

### Provenance Records

Some evidence should exist as durable correlation records rather than only as
ephemeral runtime telemetry.

These records may hold:

- correlation identifiers
- source references
- artifact digests
- causal links between earlier outcomes and later adoption

This is especially important when attribution spans long time gaps.

## Canonical vs Derived Boundary

This proposal intentionally draws a hard boundary between canonical graph truth
and observed evidence.

Canonical specs may define:

- that a node or edge is expected to emit evidence
- what evidence categories are relevant
- what correlations must be reviewable

Canonical specs should not by default store:

- raw trace payloads
- raw logs
- high-volume metrics
- backend-specific dashboard definitions

Evidence remains derived.

It may be cached, indexed, summarized, or linked for inspection, but it should
not become canonical truth just by existing.

This protects the graph from absorbing runtime noise while still making runtime
behavior inspectable.

## Delayed Adoption and Non-Tree Causality

The project should treat delayed adoption or delayed value realization as a
first-class case.

Not all meaningful relationships look like immediate parent/child execution.

Sometimes:

- an intent resolves now
- an artifact is produced now
- runtime execution happens now
- adoption or value realization happens much later

For these cases, the system should prefer **causal links** or durable
correlation records rather than forcing everything into one strict execution
tree.

This matters because:

- the runtime relationship is real
- the semantic attribution is real
- but the timing may be asynchronous or delayed

The graph should be able to express:

- immediate outcome attribution
- delayed adoption attribution
- many-to-one or one-to-many evidence relationships

without pretending they are all the same shape.

## Telemetry Schema

SpecGraph should eventually define a project-level telemetry semantic schema.

That schema should describe:

- stable evidence-oriented attribute names
- signal-specific meanings
- allowed correlation surfaces
- low-cardinality vs high-cardinality distinctions
- required or optional evidence for certain node or edge classes

The schema should remain **schema-first** and **project-owned**.

This makes it possible to generate or validate:

- runtime constants
- collector transforms
- ingestion mappings
- viewer overlays
- inspector labels

This proposal does **not** require one exact format yet.

It only establishes that the project should not scatter telemetry names and
meaning ad hoc across code and dashboards.

## Stack Neutrality and Preferred Profiles

The canonical proposal should remain stack-neutral.

SpecGraph should not require one exact telemetry vendor, collector, or storage
backend as part of graph truth.

However, the project may still define **preferred implementation profiles**.

A reasonable profile may recommend:

- OpenTelemetry for traces, metrics, and logs
- OTLP for transport
- a collector as routing and transformation plane
- compatibility shims only for legacy instrumentation paths

That recommendation can be strong without becoming a canonical validity rule
for the graph itself.

In other words:

- canonical spec defines the evidence model
- implementation profile chooses the instrumentation stack

## Viewer and Inspector Implications

This proposal gives a clean future basis for two derived surfaces.

### 1. Graph Overlay

Nodes and edges may eventually expose evidence-backed overlays such as:

- request rate
- latency bands
- error ratios
- most recent artifact or release linkage
- adoption conversion
- adoption lag

These are overlays, not canonical node fields.

### 2. Decision Inspector

Users should eventually be able to inspect:

- which rules matched
- which selector won
- which policy allowed or denied the path
- which logs, traces, and metrics support that explanation

This converts the graph from a static design map into an inspectable semantic
surface.

## Supervisor Implications

Supervisor should not treat telemetry as a substitute for canonical review.

But telemetry-aware evidence can eventually help it:

- enrich graph-health inspection
- support reviewer evidence packages
- distinguish lack of use from lack of semantic clarity
- surface adoption or runtime gaps without forcing new canonical children

If telemetry is introduced later into supervisor logic, it should remain:

- derived
- explainable
- non-self-authorizing

Telemetry may inform decisions.

It should not silently become the authority that rewrites graph truth.

## Adoption Order

The natural adoption order is:

1. Define the semantic evidence chain and evidence-plane boundary.
2. Define a project-owned telemetry schema.
3. Ingest and correlate evidence into a derived evidence plane.
4. Build overlays and a decision inspector on top of that plane.
5. Only then consider telemetry-informed review or refinement heuristics.

This order matters because it preserves meaning before optimization.

## Why This Is Useful

The strongest value in this proposal is not "use telemetry."

The strongest value is:

- making runtime evidence legible in graph terms
- preventing raw runtime detail from polluting canonical specs
- giving the project a principled way to correlate intent, execution, outcome,
  and adoption
- creating a future path for evidence-backed graph inspection

It lets SpecGraph stay a readable graph of roles and contracts while still
connecting to what actually happens in the system.

## Open Questions

- Which parts of the semantic evidence chain belong in canonical ontology, and
  which parts belong only in derived evidence artifacts?
- Should evidence expectations be owned by one meta-spec, or delegated by node
  family?
- What is the minimal schema surface needed before any runtime integration is
  worthwhile?
- When telemetry informs reviewer decisions, what protections are needed to
  keep it non-self-authorizing?
- Which future layer should own concrete implementation profiles for evidence
  transport and storage?
