# SpecSpace Executor Runtime Environment Boundary Acceptance

## Status

Draft proposal

## Source Material

This proposal closes the downstream evidence loop for SpecSpace PR `#231`.

Source draft:

- `docs/archive/proposal_sources/0085_specspace_executor_runtime_environment_boundary_acceptance.md`

## Context

`0084` added report-only runtime environment semantics to executor backend
availability. In static publish, the Codex backend is intended for a local
operator environment, so public producer artifacts must not present the missing
local executable as a broken deployment or Agent Passport failure.

SpecSpace PR `0al-spec/SpecSpace#231` consumed those fields from
`runs/supervisor_executor_adapter_index.json` and `runs/agent_surface_index.json`
and rendered the executor runtime environment boundary in the Agent surfaces
panel/API.

This proposal records that consumer implementation in the existing external
consumer evidence acceptance plane.

## Goals

- Add one report-only external consumer evidence record for SpecSpace PR `#231`.
- Bind the record to the existing `external_consumer_handoff::specspace`
  handoff.
- Accept the existing producer artifacts that carry the runtime environment
  fields:
  - `runs/supervisor_executor_adapter_index.json`
  - `runs/agent_surface_index.json`
- Reference SpecSpace CI/deploy smoke and Platform Timeweb publish evidence.
- Preserve the existing SpecSpace handoff and evidence artifact family.

## Non-Goals

- Mutating SpecSpace.
- Mutating Platform.
- Re-validating live production UI as a required build step.
- Claiming observed runtime enforcement.
- Installing or invoking Codex in static publish.
- Introducing a new handoff or evidence artifact family.

## Evidence

The accepted evidence record references:

- SpecSpace PR: `https://github.com/0al-spec/SpecSpace/pull/231`;
- SpecSpace CI and production smoke:
  `https://github.com/0al-spec/SpecSpace/actions/runs/27185889613`;
- Platform Timeweb publish:
  `https://github.com/0al-spec/Platform/actions/runs/27185926531`.

The consumed artifact set includes:

```text
runs/supervisor_executor_adapter_index.json
runs/agent_surface_index.json
```

The consumer-facing state verified before this proposal was recorded:

```text
backend_status: not_applicable_in_producer_environment
producer_environment: static_publish_environment
intended_environment: local_operator_environment
operator_next_action: run_in_intended_runtime_environment
```

## Acceptance

This slice is complete when:

- `runs/external_consumer_evidence_index.json` accepts the new SpecSpace
  executor runtime environment evidence entry;
- existing SpecSpace evidence entries remain accepted;
- accepted contract artifacts remain a subset of the stable SpecSpace handoff
  artifact contract;
- no local paths, raw logs, secrets, or raw passport material are introduced;
- proposal tracking gates, `make external-handoffs`,
  `make external-consumer-evidence`, focused evidence tests, and the full
  Python suite pass.
