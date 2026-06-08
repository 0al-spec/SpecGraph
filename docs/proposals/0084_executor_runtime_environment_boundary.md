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
default_backend_status: missing_executable
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
publish may probe the executable and report it missing, but that means
`executable_not_available_in_current_process_environment`, not "Codex backend
contract is invalid".

The generated entry carries a `runtime_environment` object:

```json
{
  "producer_environment": "static_publish_environment",
  "intended_environment": "local_operator_environment",
  "executable_probe_scope": "current_process_environment",
  "backend_status_semantics": "executable_not_available_in_current_process_environment",
  "static_publish_executable_required": false,
  "local_operator_executable_required": true,
  "missing_executable_is_static_publish_gap": true,
  "operator_next_action": "configure_local_operator_executable"
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

`missing_executable` remains a blocker for actually launching the backend in
the current process environment. The new fields only explain which environment
was probed and where the backend is intended to run.

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
- tests prove static publish `missing_executable` is explained as an
  environment probe without persisting local executable paths;
- proposal tracking, executor adapter generation, Agent Passport generation,
  and the full Python suite pass.
