# Graph Operator Surface Request Preparation Source Draft

## Source Context

SpecSpace is expected to support conversations with an AI assistant where a
human operator can add graph nodes, artifacts, diagnostics, and other graph
elements into context.

The product-specific implementation name is less important than the role. The
same capability could later exist in a web application, IDE plugin, CLI/TUI,
or hosted product console.

The core idea is an abstract **Graph Operator Surface**:

```text
human operator
  -> selects graph context
  -> discusses or drafts intent with an LLM assistant
  -> reviews structured request
  -> explicitly authorizes downstream supervisor work
```

## Operator Intent

Define this as a pre-execution request preparation layer, not as an executor
adapter and not as canonical graph authority.

The LLM assistant in this layer may help phrase intent, summarize context,
draft a proposal, or prepare a supervisor request packet. It should not mutate
canonical graph state directly.

## Desired Outcome

Define:

- an implementation-agnostic `Graph Operator Surface`;
- its relationship to the existing `operator_request_packet` bridge;
- the boundary between chat assistance, request preparation, supervisor
  execution, and executor adapters;
- human confirmation requirements before execution;
- future viewer/GUI/IDE compatibility without naming one product as canonical.

## Boundary

This proposal should not implement a UI, chat service, tool-calling agent, or
new supervisor runtime behavior.

It should not require SpecSpace specifically. SpecSpace can be one conforming
implementation of the abstract operator surface.

