# Supervisor Executor Adapter Enforcement Smoke

## Status

Draft proposal

## Source Material

This proposal realizes the next bounded runtime slice after
`0077 Agent Runtime Enforcement Evidence Registry`, `0078 SpecSpace Runtime
Evidence Handoff Contract`, and `0079 SpecSpace Runtime Evidence Acceptance`.

Source draft:

- `docs/archive/proposal_sources/0080_supervisor_executor_adapter_enforcement_smoke.md`

## Context

SpecGraph now emits report-only Agent Passport runtime evidence and SpecSpace
can consume it. The current supervisor executor adapter smoke proves the
derived adapter/passport surfaces are internally consistent and safe to
reference, but it does not yet test a concrete executable boundary.

The next step should remain narrow: prove one local, deterministic boundary
without claiming full sandbox or runtime policy enforcement.

## Goals

- Add a concrete `executor_adapter_invocation_boundary` runtime-smoke check for
  `specgraph.supervisor.executor_adapter`.
- Verify that the 0056 executor adapter policy is declarative: CLI executable
  lookup metadata is present and shell command/template fields are absent.
- Verify that the generated executor adapter index does not persist executable
  paths or command lines.
- Keep the result in the existing
  `runs/agent_runtime_enforcement_evidence_index.json` and detail artifact.
- Keep the generated executor/passport/runtime evidence artifacts in the static
  publish bundle so HTTP consumers such as SpecSpace do not see stale
  `missing` agent surfaces after a green publish workflow.
- Preserve report-only semantics and keep generated JSON free of local paths,
  raw supervisor logs, raw prompts, raw passport material, and secrets.

## Non-Goals

- Implementing sandbox, seccomp, chroot, OPA, agentifyd, Pi adapter, or runtime
  policy enforcement.
- Launching agents or executing an external executor.
- Verifying Agent Passport signatures, lifecycle, revocation, trust stores, or
  integrity.
- Changing SpecSpace UI/API.
- Changing Platform deploy packaging.
- Claiming `runtime_enforcement_state: observed` or
  `V8_runtime_enforcement_observed`.

## Runtime Contract Delta

The existing supervisor executor adapter smoke detail artifact gains one
required check:

```text
executor_adapter_invocation_boundary
```

The check passes only when:

- `tools/supervisor_executor_adapter_policy.json` declares at least one backend;
- every backend uses `command_surface: cli` with declared `executable_names`;
- the backend policy does not contain shell or command-template fields such as
  `shell_command`, `command_template`, or `command_line`;
- `runs/supervisor_executor_adapter_index.json` does not persist executable
  paths or command lines.

If the boundary check fails, the existing runtime evidence status aggregation
marks the record as `failed`, and the index emits
`next_gap: repair_runtime_enforcement_evidence`.

## Expected Runtime Behavior

`make agent-runtime-evidence` continues to write:

```text
runs/agent_runtime_enforcement_evidence_index.json
runs/agent_runtime_enforcement_evidence/supervisor-executor-adapter-smoke.json
```

The generated detail artifact now includes the invocation-boundary check in
`evidence.checks`. SpecSpace does not need a new consumer contract for this
slice because it already consumes evidence rows and statuses from the stable
runtime evidence index.

`make publish-bundle` refreshes the executor adapter, Agent Passport, and
runtime evidence surfaces before its final viewer-surface rebuild. The static
bundle safety gate treats those agent/runtime artifacts as required surfaces,
so a green publish workflow cannot upload a bundle that omits the producer
artifacts required by the SpecSpace Agent surfaces panel.

## Acceptance

This slice is complete when:

- focused tests prove the invocation-boundary check passes for the current
  declarative policy;
- focused tests prove shell command/template policy fields fail the evidence;
- focused tests prove persisted executable paths fail the evidence;
- `make agent-runtime-evidence` succeeds and reports one passing evidence entry;
- `make publish-bundle` includes the executor adapter, Agent Passport, runtime
  evidence index, and runtime evidence detail artifacts in
  `artifact_manifest.json`;
- proposal gates and the full Python suite pass;
- generated artifacts contain no machine-local paths, raw logs, prompts,
  secrets, or raw passport material.
