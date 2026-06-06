# Supervisor Executor Adapter Index Runtime

## Status

Draft proposal

## Source Material

This proposal realizes the next bounded runtime slice for
`0056 Supervisor Executor Adapter Gateway`.

Source draft:

- `docs/archive/proposal_sources/0066_supervisor_executor_adapter_index_runtime.md`

## Context

Proposal `0056` defined the executor adapter gateway as a launch-and-observe
boundary. It intentionally stopped at the policy and contract surfaces:

```text
tools/supervisor_executor_adapter_policy.json
docs/supervisor_executor_adapter_gateway_contract.md
```

Proposal `0065` then made SpecSpace a typed external consumer of future
agent/executor/passport visibility artifacts. The first SpecSpace handoff is
blocked until the producer contract is stable, starting with:

```text
runs/supervisor_executor_adapter_index.json
```

## Problem

The 0056 contract names the adapter index, but the repository has no builder,
standalone command, or generated artifact shape for that index. That leaves
SpecSpace with a declared producer path but no stable producer fields to consume.

Without a runtime index:

- executor backend availability is only implicit in local supervisor code;
- Agent Passport CLI availability is not visible as a graph-side diagnostic;
- missing executor tools cannot be reported without reading raw local logs;
- SpecSpace handoff readiness remains blocked by a draft producer contract.

## Goals

- Implement a read-only `runs/supervisor_executor_adapter_index.json` builder.
- Keep the builder policy-driven from
  `tools/supervisor_executor_adapter_policy.json`.
- Surface the default Codex backend as the current stable executor backend.
- Surface Agent Passport CLI availability as report-only diagnostics.
- Expose backend capability gaps without launching nested executors.
- Avoid publishing absolute executable paths, raw prompts, raw logs, secrets, or
  provider credentials.
- Add a Makefile shortcut and focused tests.
- Mark 0056 runtime realization as implemented in proposal runtime tracking.

## Non-Goals

- Running executor smoke benchmarks.
- Launching Codex, Copilot, Claude, Gemini, or other nested executors.
- Implementing Agent Passport validation or enforcement.
- Implementing SpecSpace UI.
- Marking the full 0065 SpecSpace handoff ready.
- Adding Platform packaging or deploy changes.

## Runtime Artifact

The artifact is:

```text
runs/supervisor_executor_adapter_index.json
```

Stable top-level fields:

- `artifact_kind`;
- `schema_version`;
- `summary`;
- `entries`;
- `capability_gaps`;
- `passport_diagnostics`;
- `viewer_projection`.

Each backend entry reports:

- backend identity and authority state;
- executable availability without persisting absolute paths;
- declared operational capabilities;
- Agent Passport diagnostic status;
- smoke state;
- canonical-trial eligibility;
- safe next action;
- capability gaps.

## Safety Boundary

This slice is an observation/indexing layer. It must not:

- execute nested agents;
- persist resolved executable paths;
- persist raw prompts or logs;
- persist provider secrets;
- treat adapter availability as supervisor success;
- allow canonical trials before smoke coverage exists.

## Validation

This proposal is complete when:

- `make executor-adapters` writes the index;
- focused tests cover available and missing backend cases;
- focused tests cover standalone CLI writing;
- proposal runtime tracking marks 0056 as implemented;
- proposal tracking/work-claim gates pass;
- full test suite passes.

