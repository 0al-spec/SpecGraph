# Supervisor External Consumer Handoff Loop

## Status

Draft proposal

## Source Material

This proposal captures the operator concern that SpecGraph work is
supervisor-centric, while SpecSpace is a neighboring product/runtime consumer
that is not itself implemented through the SpecGraph supervisor.

Source draft:

- `docs/archive/proposal_sources/0064_supervisor_external_consumer_handoff_loop.md`

## Context

SpecGraph development is increasingly organized around the supervisor:

```text
supervisor observes graph/spec state
  -> finds gaps
  -> proposes bounded follow-up work
  -> validates canonical SpecGraph artifacts
  -> closes or narrows the gap
```

That loop works well for SpecGraph-owned specs, proposals, policies, indexes,
and derived reports. It becomes less direct when the gap is real but the
implementation belongs to SpecSpace.

SpecSpace is not just a static renderer. It is a product surface that consumes
SpecGraph artifacts, shows operator state, hosts runtime utility panels, and
turns derived graph surfaces into a human workflow. It cannot be treated as
ordinary SpecGraph code, but it also should not drift outside the supervisor
discipline.

## Problem

SpecGraph can identify gaps that require SpecSpace implementation, but there is
no explicit loop that says how such work is handed off, implemented, evidenced,
and then counted as closed by the graph.

Without a formal boundary:

- SpecGraph proposals can say "SpecSpace should display this" without a stable
  consumer contract;
- SpecSpace PRs can implement UI behavior without a graph-visible evidence
  return path;
- supervisor next-move logic can keep proposing work that is already done in a
  neighboring repository;
- review can confuse proposal completion with consumer implementation;
- Platform packaging/deploy work can be triggered before the artifact contract
  is stable.

The core tension is useful and should be preserved:

```text
SpecGraph supervisor is the canonical gap finder.
SpecSpace is an external implementation consumer.
```

The solution is not to make SpecSpace a submodule of the SpecGraph supervisor.
The solution is to make SpecSpace work a typed external handoff with explicit
evidence feedback.

## Goals

- Keep SpecGraph supervisor as the center of graph gap detection and proposal
  sequencing.
- Define how supervisor-discovered gaps become SpecSpace implementation
  handoffs.
- Define the minimum artifact contract a SpecSpace handoff must contain.
- Define the evidence SpecSpace returns so SpecGraph can mark a consumer gap
  reduced or closed.
- Prevent SpecSpace from reading unstable proposal internals when stable derived
  JSON surfaces should be used instead.
- Clarify when Platform/deploy work enters the sequence.
- Connect this loop to existing proposal tracking, work claims, and external
  consumer surfaces.

## Non-Goals

- Implementing SpecSpace UI in this proposal.
- Making the SpecGraph supervisor execute SpecSpace code directly.
- Turning SpecGraph into a cross-repository task runner.
- Replacing GitHub PR review in SpecSpace.
- Requiring every SpecSpace PR to be initiated by SpecGraph.
- Defining a general multi-repository project management system.
- Implementing automatic deploy, packaging, or Platform orchestration changes.

## Core Proposal

Introduce a **Supervisor External Consumer Handoff Loop**:

```text
SpecGraph gap
  -> proposal / contract
  -> external consumer handoff
  -> SpecSpace implementation PR
  -> consumer evidence report
  -> SpecGraph gap reduction / closure
```

SpecGraph remains responsible for canonical graph semantics. SpecSpace remains
responsible for product UI/runtime implementation. The bridge is a typed
handoff/evidence contract.

## Responsibility Split

### SpecGraph-Owned

SpecGraph owns:

- canonical specs, proposals, policies, and derived graph artifacts;
- supervisor gap detection and next-move recommendations;
- stable artifact contracts for consumers;
- handoff records describing required external consumer work;
- evidence requirements for closing consumer-facing gaps;
- local-only and publishable-field boundaries.

SpecGraph does not own SpecSpace component implementation or UI layout.

### SpecSpace-Owned

SpecSpace owns:

- UI components, panels, routes, and runtime interaction behavior;
- artifact loading and fallback states;
- browser-visible user experience;
- tests/smoke checks proving the artifact contract is consumed correctly;
- evidence reports or release notes that reference the consumed contract.

SpecSpace should consume stable derived artifacts rather than scrape proposal
markdown or local supervisor logs.

### Platform-Owned

Platform enters only after a handoff needs packaging, deploy, CI composition, or
standard distribution changes.

Platform owns:

- deployment control-plane decisions;
- Docker/Compose/service image locks;
- packaged CLI tools;
- Timeweb deploy publication;
- cross-service release wiring.

Platform should not be the first place where a SpecGraph-to-SpecSpace contract
is invented.

## Handoff Contract

A SpecGraph-to-SpecSpace handoff should be represented as a derived, read-only
artifact. Candidate fields:

```json
{
  "artifact_kind": "external_consumer_handoff",
  "schema_version": 1,
  "handoff_id": "specspace::agent_authority_panel::0059",
  "consumer": "SpecSpace",
  "source_proposal_ids": ["0056", "0059"],
  "source_gap": "agent_passport_diagnostics_not_visible",
  "artifact_contract": {
    "producer": "SpecGraph",
    "paths": [
      "runs/agent_surface_index.json",
      "runs/agent_verification_gap_index.json"
    ],
    "stable_fields": [
      "artifact_kind",
      "schema_version",
      "summary",
      "surfaces",
      "gaps"
    ],
    "local_only_fields_forbidden": true
  },
  "expected_consumer_behavior": [
    "show available agent surfaces",
    "show verification gaps without exposing raw local paths",
    "show fallback state when artifact is absent"
  ],
  "evidence_required": [
    "SpecSpace PR link",
    "test or smoke evidence",
    "screenshots or UI state notes when applicable"
  ],
  "closure_state": "handoff_ready"
}
```

The handoff is not a command to mutate SpecSpace. It is the graph-visible
contract that a SpecSpace PR can implement against.

## Evidence Contract

SpecSpace should return evidence that can be referenced by SpecGraph without
copying the whole UI implementation:

```json
{
  "artifact_kind": "external_consumer_evidence",
  "schema_version": 1,
  "handoff_id": "specspace::agent_authority_panel::0059",
  "consumer": "SpecSpace",
  "implementation_ref": "https://github.com/0al-spec/SpecSpace/pull/123",
  "consumed_artifacts": [
    "runs/agent_surface_index.json",
    "runs/agent_verification_gap_index.json"
  ],
  "evidence": [
    {
      "kind": "test",
      "ref": "npm test -- agent authority panel"
    },
    {
      "kind": "operator_note",
      "ref": "panel renders missing-artifact fallback and live gap count"
    }
  ],
  "result": "implemented"
}
```

SpecGraph can then mark the original consumer gap as reduced or closed only when
the evidence matches the expected contract.

## Closure Rule

A SpecGraph proposal that requires SpecSpace work is not fully closed by writing
proposal text alone.

Closure requires:

- a stable SpecGraph producer artifact or explicit no-artifact rationale;
- a handoff record naming SpecSpace as the consumer;
- a SpecSpace implementation reference or an explicit blocked/deferred state;
- evidence that the consumer behavior matches the contract;
- no leakage of local-only fields into publishable UI surfaces.

This creates a clean distinction:

```text
proposal accepted: graph semantics are agreed
handoff ready: SpecSpace can implement
consumer implemented: SpecSpace has shipped the behavior
gap closed: SpecGraph has accepted the returned evidence
```

## Relationship To Existing Proposals

- `0056_supervisor_executor_adapter_gateway.md` defines executor adapter
  surfaces that SpecSpace may eventually display.
- `0057_graph_operator_surface_request_preparation.md` defines the operator
  surface boundary where SpecSpace prepares human-confirmed requests.
- `0059_agent_passport_adoption_for_graph_agents.md` defines agent authority
  indexes and verification gaps that SpecSpace should consume as safe derived
  surfaces.
- `0060_external_ontology_import_plane.md` defines lower semantic import
  artifacts that may later need SpecSpace display and review affordances.
- `0061_proposal_debt_report_viewer_api.md` already frames one SpecSpace-facing
  derived report and should be treated as an example consumer contract.
- `0063_proposal_work_claim_locks.md` provides coordination discipline for
  proposal work claims and deterministic proposal IDs.

This proposal connects those efforts into one cross-repository loop without
making SpecSpace part of SpecGraph canonical authority.

## Candidate Runtime Surfaces

Future bounded implementation slices may extend existing external consumer
artifacts or introduce:

```text
runs/external_consumer_handoff_index.json
runs/external_consumer_evidence_index.json
tools/external_consumer_handoff_policy.json
```

The first implementation should be report-only:

- no SpecSpace mutation;
- no GitHub issue creation;
- no deploy changes;
- no automatic closure without evidence.

## Acceptance Criteria

- The proposal defines SpecGraph, SpecSpace, and Platform responsibilities.
- The proposal defines handoff and evidence contracts.
- The proposal states that SpecSpace should consume stable derived artifacts,
  not proposal internals or local supervisor logs.
- The proposal defines a closure rule for consumer-facing gaps.
- The proposal links the relevant neighboring proposals.
- The proposal is tracked in proposal runtime and promotion registries.

## Risks and Mitigations

- **Over-centralization**: SpecGraph could become a cross-repo task manager.
  Mitigation: handoffs are contracts, not commands.
- **UI drift**: SpecSpace may implement behavior that no longer matches graph
  semantics. Mitigation: closure requires evidence against a stable artifact
  contract.
- **Premature Platform work**: packaging may begin before the producer/consumer
  contract is stable. Mitigation: Platform enters only after handoff readiness.
- **Artifact churn**: SpecSpace may depend on unstable fields. Mitigation:
  handoffs name stable fields and local-only boundaries explicitly.

