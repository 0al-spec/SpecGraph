# Executor Runtime Environment Boundary Source Draft

## Problem

After `0082`, public static publish has Agent Passport CLI verification
available. After `0083`, Pi is explicitly deferred and static publish is
identified as a non-executor runtime. The remaining confusing live state is the
Codex executor backend:

```text
agent_passport_cli_status: available
default_backend_id: codex
default_backend_status: not_applicable_in_producer_environment
```

This is expected in static publish, but without an explicit environment field a
viewer can read it as a broken backend, broken deploy, or missing Agent
Passport dependency.

## Proposed Slice

Add a small runtime-environment boundary to the existing executor adapter
surfaces.

The policy declares:

- `static_publish_environment`
- `local_operator_environment`
- `external_harness_environment`

The generated `supervisor_executor_adapter_index` records:

- environment that produced the probe;
- intended environment for the backend;
- executable probe scope;
- status semantics;
- whether static publish is required to have that executable;
- safe operator next action.

The derived `agent_surface_index` should carry the same nested field for
executor-backed surfaces.

## Non-Goals

- Do not install Codex in static publish.
- Do not add Pi.
- Do not implement BYOK.
- Do not change Timeweb deploy.
- Do not claim runtime enforcement.
- Do not persist local paths or credentials.

## Expected Result

SpecSpace and other consumers can display:

```text
not_applicable_in_producer_environment
producer: static_publish_environment
intended: local_operator_environment
```

That makes the live state actionable: configure Codex locally before executor
smoke/canonical trials; do not treat static publish as a Codex runtime.
