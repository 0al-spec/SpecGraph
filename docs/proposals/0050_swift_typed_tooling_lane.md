# Swift Typed Tooling Lane

## Status

Draft proposal

## Source Material

This proposal captures the operator discussion about using Swift as a
pragmatic second language for SpecGraph tooling.

The discussion concluded that Swift should not replace the Python supervisor.
Instead, it should be introduced as a bounded typed tooling lane for read-only
artifact clients, validators, SDKs, and future native SpecSpace integration.

Source draft:

- `docs/archive/proposal_sources/0050_swift_typed_tooling_lane.md`

## Context

SpecGraph now publishes increasingly stable neutral artifacts:

- canonical spec node YAML;
- static publish bundles;
- `artifact_manifest.json`;
- graph dashboard and backlog projections;
- proposal, trace, evidence, metric-pack, model-usage, and conversation-memory
  surfaces;
- SpecPM handoff and registry-observation artifacts.

These artifacts are language-neutral, but most runtime tooling still lives in
Python. Python remains the right place for the current supervisor because it
already owns orchestration, policy, tests, and bootstrap velocity.

At the same time, some future consumers need a stricter typed boundary:

- native macOS/iOS or SwiftUI `SpecSpace` clients;
- local CLI tools with strongly typed artifact models;
- SDKs for reading published SpecGraph bundles;
- Agent Passport and protocol tooling;
- validator experiments that should not mutate canonical graph state.

Swift is a reasonable second language for that layer because it gives a typed
model system and good ergonomics while staying close to Apple-native and
cross-platform developer tooling.

## Problem

Without an explicit boundary, "write some components in Swift" can drift into
three bad shapes:

- a broad rewrite of the Python supervisor before the runtime model is stable;
- duplicate authority where Swift and Python disagree about canonical graph
  mutation;
- ad hoc Swift experiments that cannot be validated against the same artifacts
  and fixtures as the existing tooling.

SpecGraph needs a proposal-first boundary for Swift adoption.

The key question is not "Swift or Python?" but:

```text
Which SpecGraph surfaces can be read through typed Swift tooling without
changing graph authority?
```

## Goals

- Define Swift as an optional second implementation lane for typed tooling.
- Keep Python supervisor orchestration as the canonical runtime authority.
- Start with read-only artifact consumption, not canonical mutation.
- Require fixture parity between Swift readers and Python-generated artifacts.
- Support both local paths and HTTP-backed static artifact roots.
- Prepare a future typed SDK for SpecSpace and other consumers.
- Keep the lane compatible with Agent Passport and protocol tooling later.

## Non-Goals

- Rewriting `tools/supervisor.py` in Swift.
- Making Swift a required dependency for ordinary SpecGraph operation.
- Granting Swift tooling canonical write authority in the first slice.
- Replacing ContextBuilder or SpecSpace.
- Replacing Python tests as the main supervisor regression suite.
- Choosing Swift over Rust for future low-level sandbox or enforcement code.
- Defining the final package layout for every future Swift module.

## Core Proposal

SpecGraph should define a **Swift typed tooling lane**.

This lane may implement read-only clients, validators, and SDKs over published
SpecGraph artifacts, while Python remains the graph and supervisor authority.

The initial boundary is:

```text
Python supervisor / SpecGraph repository
  -> emits JSON/YAML/Markdown artifacts
  -> Swift typed tooling reads artifacts
  -> Swift tooling validates or inspects typed contracts
  -> findings flow back through proposals, PRs, or derived artifacts
```

Swift tooling must not write canonical specs, proposal registries, runtime
policy, or supervisor state until a later proposal grants a narrower authority.

## First Candidate Component

The first Swift component should be a read-only artifact client, tentatively:

```text
tools/swift/SpecGraphKit
```

It should prove the language boundary with a small set of stable contracts:

- read `artifact_manifest.json`;
- read `runs/graph_dashboard.json`;
- read `runs/graph_backlog_projection.json`;
- read selected spec node surfaces from `specs/nodes/`;
- support a local filesystem root;
- support an HTTP static artifact root such as `https://specgraph.tech/`;
- expose one small CLI command such as `inspect`.

The component should be useful even before it understands every SpecGraph
artifact. Unknown fields should be tolerated unless the field is part of the
minimal contract being validated.

## Authority Boundary

Swift tools in this lane are initially consumers, not controllers.

Allowed in the first slice:

- parse artifacts;
- validate typed shape;
- emit local inspection output;
- fail CI for its own fixture contract;
- report missing or unsupported fields as typed gaps.

Not allowed in the first slice:

- mutate canonical `specs/`;
- mutate proposal registries;
- approve supervisor gates;
- write to `runs/` as a source of graph truth;
- publish artifacts to static hosting;
- trigger supervisor runs.

If a Swift component later needs write authority, that must be a separate
proposal with explicit authority class, target paths, and rollback strategy.

## Artifact Contract Strategy

The Swift lane should consume the same artifacts that Python already produces.

The first contract set should be intentionally small:

```text
artifact_manifest.json
runs/graph_dashboard.json
runs/graph_backlog_projection.json
specs/nodes/*.yaml or exported node JSON surface
```

The Swift side should model these as tolerant typed contracts:

- required fields for identity and routing;
- optional fields for viewer-only or future extensions;
- explicit unknown-field tolerance;
- stable error types for missing artifacts, invalid JSON/YAML, and unsupported
  schema versions.

This keeps the lane useful for external consumers without forcing every derived
surface to become a Swift schema immediately.

## Validation Strategy

The first Swift PR should include fixture parity checks:

- use Python-generated fixture artifacts from the repository or CI build;
- parse them through Swift models;
- assert stable IDs, counts, and minimal required fields;
- verify local path and HTTP-root URL normalization separately;
- avoid network dependence in normal unit tests.

The Swift lane should not be considered operational until CI can run the small
Swift test suite on the selected supported platform.

## Relationship To Existing Architecture

This proposal extends the multi-service factory model:

```text
SpecGraph
  Python supervisor and artifact producer

SpecPM
  package and registry substrate

SpecSpace / ContextBuilder
  operator cockpit and viewer

Swift typed tooling lane
  typed artifact client / SDK / validator substrate
```

The Swift lane is not a fourth authority service. It is a typed implementation
lane that may be used by SpecSpace, CLI tools, or protocol validators.

## Future Follow-Ups

After the read-only client proves useful, possible follow-ups are:

- `SpecGraphKit` package layout and CI;
- static artifact HTTP provider;
- typed dashboard/backlog SDK models;
- Agent Passport validator wrapper;
- SwiftUI/native SpecSpace consumer integration;
- signed bundle verification;
- read-only metric and evidence artifact readers;
- later proposal for narrow write authority if needed.

## Acceptance Criteria

- Swift is documented as an optional typed tooling lane, not a supervisor
  rewrite.
- The first Swift slice is constrained to read-only artifact consumption.
- The proposal names the initial artifact contracts and authority boundary.
- Future write authority requires a separate proposal.
- The promotion registry records this proposal's source draft and bounded
  scope.
