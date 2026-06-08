# Executor Runtime Environment Boundary

## Status

Draft proposal

## Source Material

This proposal records the bounded runtime slice for making executor backend
availability environment-aware.

Source draft:

- `docs/archive/proposal_sources/0084_executor_runtime_environment_boundary.md`

## Context

`0056 Supervisor Executor Adapter Gateway` defines the governed boundary for
future executor adapters. `0066 Supervisor Executor Adapter Index Runtime`
materializes the current Codex backend as
`runs/supervisor_executor_adapter_index.json`. `0082 Agent Passport CLI
Availability in Static Publish` made Agent Passport verification available in
public static publish, and `0083 Pi Harness Candidate Deferred` clarified that
static publish is not an executor runtime.

The live static artifact bundle can therefore show:

```text
default_backend_id: codex
default_backend_status: not_applicable_in_producer_environment
agent_passport_cli_status: available
```

That state is correct in static publish: the GitHub/static publisher is allowed
to have `agent-passport`, but it is not expected to provide a local Codex
runtime or a private Codex/ChatGPT identity. The missing Codex executable should
not look like a broken passport, failed deploy, or reason to introduce Pi
immediately.

## Decision

The supervisor executor adapter index records the runtime environment that
produced the availability probe and the intended runtime environment for each
backend.

The initial environment vocabulary is:

- `static_publish_environment`
- `local_operator_environment`
- `external_harness_environment`

The Codex backend remains intended for `local_operator_environment`. Static
publish may probe the executable, but the viewer-facing backend status remains
`not_applicable_in_producer_environment`, not "Codex backend contract is
invalid" and not "static publish can run Codex smoke".

The generated entry carries a `runtime_environment` object:

```json
{
  "producer_environment": "static_publish_environment",
  "intended_environment": "local_operator_environment",
  "executable_probe_scope": "current_process_environment",
  "backend_status_semantics": "executable_probe_not_required_for_producer_environment",
  "static_publish_executable_required": false,
  "local_operator_executable_required": true,
  "producer_environment_executable_required": false,
  "missing_executable_is_static_publish_gap": true,
  "producer_environment_execution_suppressed": true,
  "operator_next_action": "run_in_intended_runtime_environment"
}
```

The same object is projected onto the derived executor agent surface so
SpecSpace can show the boundary without inventing interpretation locally.

## Boundaries

This proposal does not:

- install Codex in static publish;
- make Codex available in public Timeweb containers;
- change the default executor backend;
- implement Pi;
- implement BYOK UI;
- run nested executor smoke tests;
- claim runtime enforcement is observed;
- persist executable absolute paths, auth caches, API keys, or provider
  secrets.

`missing_executable` remains a blocker for actually launching the backend in an
intended executor environment. When a producer environment is explicitly not an
executor runtime, the viewer-facing backend status is
`not_applicable_in_producer_environment`; the raw executable probe remains
available under `executable_availability` without making static publish
smoke-ready.

## Consumer Guidance

Viewer consumers should display `backend_status` together with
`runtime_environment.producer_environment` and
`runtime_environment.intended_environment`.

For static publish, the expected operator-facing interpretation is:

```text
Codex executable is missing in the static publish environment.
Codex remains a local operator backend. Configure it locally with PATH or
SPECGRAPH_CODEX_EXECUTABLE before running executor smoke or canonical trials.
```

## Acceptance

This slice is complete when:

- `tools/supervisor_executor_adapter_policy.json` declares the runtime
  environment vocabulary;
- `runs/supervisor_executor_adapter_index.json` includes environment semantics
  for executor backend availability;
- `runs/agent_surface_index.json` carries those semantics for executor-backed
  agent surfaces;
- tests prove static publish does not report Codex as a configuration blocker
  or smoke-ready backend, even when the executable probe finds a binary;
- proposal tracking, executor adapter generation, Agent Passport generation,
  and the full Python suite pass.
