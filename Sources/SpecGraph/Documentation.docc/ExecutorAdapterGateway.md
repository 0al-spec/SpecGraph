# Executor Adapter Gateway

SpecGraph uses the executor adapter gateway as the current in-repository
anti-corruption layer between deterministic graph work and future
non-deterministic agent runtime work.

## Responsibility Split

SpecGraph owns:

- canonical graph state;
- specification and proposal records;
- deterministic validation;
- search, indexing, reports, and lifecycle state;
- supervisor planning state and review gates.

The executor adapter gateway owns only the boundary:

- normalize a bounded execution request;
- invoke an external executor adapter;
- collect the structured report contract;
- classify execution results without deciding graph acceptance.

A future dedicated SpecAgent runtime may own provider adapters, sandbox runtime,
agent identity, capability enforcement, BYOK execution, and tool policy. That
future extraction is justified only after real runtime use cases prove the
boundary.

## Request Contract

A bounded executor request must carry:

- `request_id`;
- `backend_id`;
- `workspace_root`;
- `target_ref`;
- `provider_config_ref`;
- `policy_envelope`;
- `capability_envelope`.

`backend_id` is explicit so experimental or non-default executor choices are
auditable. Future implementations must not infer backend selection from
out-of-band process state.

## Report Contract

A normalized executor report must carry:

- `request_id`;
- `run_id`;
- `backend_id`;
- `status`;
- `logs_ref`;
- `produced_artifacts`;
- `policy_decisions`;
- `error_class`.

`status: ready` means only that the executor produced a report that can enter
supervisor validation. It does not mean the task succeeded, the graph should be
mutated, or review gates can be skipped.

## Policy Artifact

The machine-readable policy surface is:

```text
tools/supervisor_executor_adapter_policy.json
```

The repository contract source is:

```text
docs/supervisor_executor_adapter_gateway_contract.md
```

The contract supports future BYOK execution through `provider_config_ref`, not
through persisted API key values, raw provider secrets, web authentication
sessions, billing account details, or raw prompts.
