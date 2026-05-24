# Graph Operator Surface Request Preparation

## Status

Draft proposal

## Source Material

This proposal captures the operator request to describe graph-context chat and
viewer-driven request preparation without hardcoding SpecSpace as the only
consumer.

Source draft:

- `docs/archive/proposal_sources/0057_graph_operator_surface_request_preparation.md`

## Context

SpecGraph already has an `operator_request_packet` bridge policy for bounded
requests from chat instructions, GUI selections, or mediated artifacts:

```text
tools/operator_request_bridge_policy.json
```

SpecSpace is expected to provide a practical implementation where a human
operator can inspect graph state, select graph elements, discuss them with an
AI assistant, and prepare a structured request for the supervisor.

However, core SpecGraph specifications should not depend on one product name or
one GUI implementation. The same role can be fulfilled by:

- a web graph viewer;
- an IDE extension;
- a local desktop client;
- a CLI/TUI;
- a hosted operator console;
- SpecSpace.

SpecGraph needs an abstract name for this upstream layer.

## Problem

If the graph spec names SpecSpace directly, product implementation details can
leak into core architecture. That creates three risks:

- other viewers or operator tools look second-class even when they satisfy the
  same contract;
- UI-specific behavior may be mistaken for graph authority;
- chat output may be confused with supervisor execution or canonical graph
  mutation.

At the same time, a plain "viewer" concept is too passive. The intended surface
does more than render graph data. It helps an operator select context, draft
intent, prepare request packets, and authorize transitions into governed
supervisor work.

## Goals

- Define an implementation-agnostic **Graph Operator Surface** role.
- Keep SpecSpace as one possible implementation, not as the canonical layer.
- Define the surface as request preparation, not graph mutation.
- Connect the surface to the existing `operator_request_packet` bridge.
- Allow LLM-assisted chat inside the surface without treating chat output as
  canonical state.
- Require explicit human confirmation before supervisor execution.
- Preserve the boundary with proposal `0056`: operator surfaces prepare
  requests; executor adapters launch and observe nested agent execution.

## Non-Goals

- Implementing a UI or chat product.
- Defining SpecSpace component layout.
- Defining a general-purpose autonomous agent.
- Allowing chat output to mutate canonical graph files.
- Allowing an operator surface to bypass supervisor gates.
- Replacing `operator_request_packet`.
- Replacing executor adapters.
- Requiring a specific LLM provider, model, or chat protocol.

## Core Proposal

Introduce **Graph Operator Surface** as the abstract role for human-facing graph
operation:

```text
Graph Operator Surface
  = an implementation-agnostic UI/API layer where a human operator inspects
    graph state, selects graph context, drafts intents/proposals/requests,
    and explicitly authorizes transitions into supervisor execution.
```

The surface is upstream from supervisor execution:

```text
graph nodes + derived artifacts + operator conversation
  -> selected context bundle
  -> LLM-assisted draft or deterministic form
  -> operator_request_packet
  -> human confirmation
  -> supervisor run
  -> executor adapter
  -> deterministic validation and gates
```

The surface may use an LLM assistant, but it remains an operator copilot until
it starts invoking tools and managing an observe/decide/act/validate loop. The
first specification boundary should assume copilot mode, not autonomous agent
mode.

## Relationship To Operator Request Packets

The Graph Operator Surface should emit or prepare the existing bridge artifact:

```json
{
  "artifact_kind": "operator_request_packet",
  "schema_version": 1,
  "user_intent": {
    "source_kind": "gui_selection",
    "source_summary": "Operator selected SG-SPEC-0056 and asked for a bounded refinement."
  },
  "operator_request": {
    "target_spec_id": "SG-SPEC-0056",
    "run_mode": "targeted_refine",
    "operator_note": "Clarify adapter boundary without over-specifying agent behavior.",
    "mutation_budget": ["documentation_only"],
    "stop_conditions": ["first_structured_outcome", "review_boundary_reached"]
  }
}
```

The existing policy already permits `source_kinds` such as:

- `chat_instruction`;
- `gui_selection`;
- `mediated_artifact`.

This proposal names the upstream role that produces those packets.

## Context Bundle

A conforming surface may assemble a context bundle from:

- selected spec nodes;
- selected proposal documents;
- graph next moves;
- backlog projection entries;
- supervisor diagnosis artifacts;
- trace/evidence overlays;
- activity feed entries;
- operator-written chat context.

The context bundle is prompt input or UI state. It is not canonical graph truth.

## LLM Assistance Boundary

An LLM inside a Graph Operator Surface may:

- explain selected graph state;
- summarize relevant specs and artifacts;
- draft an intent;
- draft a proposal source note;
- draft an `operator_request_packet`;
- suggest a supervisor run mode;
- identify missing context.

It must not directly:

- edit canonical spec files;
- mark gates approved;
- run supervisor without human authorization;
- treat its answer as a canonical proposal or spec;
- bypass `operator_request_packet` validation;
- bypass deterministic supervisor validation.

## Human Confirmation

Before a request crosses into supervisor execution, the surface should require
an explicit human confirmation step.

The confirmation should show at least:

- target spec ID or target scope;
- run mode;
- operator note;
- mutation budget;
- requested authority;
- stop conditions;
- whether the request was LLM-assisted;
- any missing or inferred fields.

This makes the authority transition visible:

```text
LLM/chat draft -> human-approved operator request -> supervisor execution
```

## Relationship To Proposal 0056

Proposal `0056` defines how the supervisor launches and observes a nested
executor backend.

This proposal defines the upstream preparation layer:

```text
Graph Operator Surface
  prepares: operator_request_packet

Supervisor
  consumes: operator_request_packet
  uses: executor adapter
```

Therefore:

- Graph Operator Surface is not an executor adapter.
- Graph Operator Surface is not a model API gateway.
- Graph Operator Surface is not the supervisor trust boundary.
- Executor adapter is not an operator chat surface.

## Implementation-Agnostic Naming

SpecGraph specifications should use:

```text
Graph Operator Surface
```

or, where shorter wording is required:

```text
operator surface
```

They should avoid making core semantics depend on:

- `SpecSpace`;
- `ContextBuilder`;
- `GUI`;
- `viewer`;
- `chat app`.

Those names may appear in implementation docs, integration guides, or examples,
but not as the canonical role name.

## Future Runtime Artifacts

Future implementation may expose request-preparation surfaces such as:

```text
runs/operator_surface_request_preview.json
runs/operator_surface_context_bundle.json
```

These should be derived and reviewable. They should not contain raw private
chat transcripts unless explicitly redacted and intentionally retained.

## Safety Rules

- Chat output is draft material.
- Context bundles are derived input, not canonical graph state.
- `operator_request_packet` validation is required before execution.
- Human confirmation is required before supervisor execution.
- The surface must not infer authority from UI selection alone.
- Raw prompt text, secrets, credentials, and private local paths must not be
  published to viewer-facing artifacts.
- Product-specific surfaces must not redefine core graph semantics.

## Implementation Plan

1. Keep this proposal documentation-only.
2. Add a viewer/operator-surface contract after the first request-preview
   artifact exists.
3. Extend `operator_request_bridge_policy.json` only when runtime needs a
   concrete new field.
4. Let SpecSpace or another product implement the first conforming surface.
5. Add smoke tests for request packet validation before adding run buttons or
   tool invocation.

## Acceptance Criteria

This proposal is accepted when SpecGraph has an implementation-agnostic name and
boundary for human-facing graph operation.

Runtime realization should be considered complete only when:

- at least one operator surface can prepare an `operator_request_packet`;
- LLM-assisted drafts are clearly labeled as drafts;
- human confirmation is required before supervisor execution;
- request packets validate against policy before execution;
- supervisor execution still passes through existing gates and executor adapter
  boundaries;
- no canonical graph mutation occurs directly from chat output.

## Risks

- Product UI details can leak into core specs if the abstract role is ignored.
- Operators may over-trust polished LLM drafts.
- A chat surface can become an accidental autonomous agent if tool invocation is
  added without new gates.
- Storing raw conversation context can create privacy and retention problems.

The mitigation is to keep the first layer as request preparation: draft,
validate, confirm, then hand off to the governed supervisor path.

