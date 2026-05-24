# Supervisor Executor Adapter Gateway

## Status

Draft proposal

## Source Material

This proposal captures the operator request to evaluate GitHub Copilot CLI and
other agent backends without binding SpecGraph supervisor to one hardcoded
executor implementation.

Source draft:

- `docs/archive/proposal_sources/0056_supervisor_executor_adapter_gateway.md`

## Context

SpecGraph supervisor currently runs bounded refinement through a nested Codex
CLI execution path. That path provides important operational guarantees:

- isolated child configuration;
- explicit model and reasoning profile control;
- bounded worktree mutation;
- timeout and progress handling;
- required machine protocol markers;
- validation before canonical synchronization.

The current implementation is effective, but the boundary is Codex-shaped. A
future experiment with GitHub Copilot CLI, Claude Code, Gemini CLI, OpenCode, or
another agent executor would have to imitate the same implicit assumptions.

At the same time, external model routing projects such as LiteLLM, Portkey, and
OpenRouter solve a different layer: they route model API calls. UI/event
protocols such as AG-UI solve another layer: they coordinate agent-visible UI
events. Neither category is a drop-in replacement for a file-mutating nested
executor that must satisfy SpecGraph governance.

## Problem

The supervisor lacks a first-class executor boundary.

Today, executor concerns are entangled:

- command construction;
- child config isolation;
- auth/profile handling;
- model selection;
- sandbox and approval mode;
- stdout/stderr capture;
- protocol parsing;
- environment failure classification;
- capability assumptions.

This makes alternative executor experiments risky. A backend can appear to work
because it edits files, while still failing the properties SpecGraph actually
needs: non-interactive operation, strict output protocol, deterministic timeout
behavior, no privilege escalation, or inspectable failure state.

## Goals

- Define a supervisor executor adapter layer.
- Keep Codex as the default stable backend.
- Allow alternate backends to be introduced as explicit experimental adapters.
- Normalize executor results before supervisor gate and validation logic sees
  them.
- Record backend capabilities and unsupported features explicitly.
- Distinguish model API gateways from agent CLI executors.
- Distinguish agent CLI executors from SpecSpace/operator UI protocols.
- Provide a benchmark path before any alternate executor can participate in
  canonical graph work.
- Preserve current sandbox, approval, protocol, and validation guarantees.

## Non-Goals

- Replacing Codex as the default executor.
- Implementing GitHub Copilot CLI support in this proposal.
- Adding a full LLM gateway or provider router.
- Implementing SpecSpace UI.
- Allowing backend fallback to broaden privileges.
- Allowing a backend to skip `RUN_OUTCOME:` and `BLOCKER:` markers.
- Allowing raw prompt text, secrets, credentials, or private local paths into
  viewer-facing artifacts.
- Letting alternate executors merge PRs or approve gates.

## Core Proposal

Introduce a **Supervisor Executor Adapter Gateway**:

```text
supervisor task
  -> executor adapter selection
  -> backend-specific command/env preparation
  -> backend run
  -> normalized ExecutorRunResult
  -> existing protocol parsing, validation, and gates
```

The adapter gateway is not a model router. It is a supervisor-runtime boundary
for nested agent execution.

The first implementation should extract the current Codex path into the adapter
interface without changing behavior. Only after that should an experimental
backend, such as GitHub Copilot CLI, be added behind capability gates and smoke
tests.

## Layer Boundaries

### Agent CLI Executor

An agent CLI executor is allowed to operate on an isolated worktree and produce
file changes, subject to supervisor constraints.

Examples:

- Codex CLI;
- GitHub Copilot CLI;
- future Claude Code, Gemini CLI, or OpenCode backends.

This layer must satisfy worktree mutation, protocol, timeout, sandbox, and
failure-classification expectations.

### Model API Gateway

A model API gateway routes raw model calls or provider traffic.

Examples:

- LiteLLM;
- Portkey;
- OpenRouter.

This layer may become useful inside a future executor backend, but it does not
replace the executor adapter because it does not own file mutation, process
isolation, or supervisor protocol compliance.

### Operator/UI Protocol

An operator/UI protocol coordinates visible agent state with a UI.

Examples:

- AG-UI-style event streams;
- future SpecSpace run-control events.

This layer may display adapter state, but it should not execute supervisor
tasks or read raw executor logs directly.

## Adapter Capability Contract

Each executor backend should declare capabilities before it can run:

```json
{
  "backend_id": "codex",
  "display_name": "Codex CLI",
  "authority_state": "default",
  "command_surface": "cli",
  "non_interactive": true,
  "can_edit_worktree": true,
  "supports_sandbox": true,
  "supports_approval_policy": true,
  "supports_model_select": true,
  "supports_reasoning_effort": true,
  "supports_prompt_overlay": true,
  "supports_timeout": true,
  "supports_tool_allowlist": false,
  "protocol_contract": "run_outcome_blocker",
  "auth_isolation": "isolated_child_home",
  "config_isolation": "isolated_child_home"
}
```

Suggested `authority_state` values:

- `default`: stable backend used by ordinary supervisor runs.
- `experimental`: available only through explicit operator selection.
- `unsupported`: discovered but not safe to run.
- `deprecated`: retained for compatibility, not for new runs.

Experimental backends should default to read-only smoke tests until their
capability contract is proven.

## Normalized Run Result

The adapter gateway should return a backend-neutral result shape:

```json
{
  "backend_id": "codex",
  "run_status": "completed",
  "returncode": 0,
  "protocol_status": "valid",
  "outcome": "done",
  "blocker": "none",
  "stdout_path": "local-only",
  "stderr_path": "local-only",
  "environment_issues": [],
  "adapter_metadata": {
    "model": "gpt-5.5",
    "reasoning_effort": "medium"
  }
}
```

The supervisor should continue to treat missing protocol markers as protocol
failure, not success. Backends may provide extra metadata, but the normalized
fields are the contract used by gate and validation logic.

## Candidate Policy Artifact

Runtime implementation may introduce:

```text
tools/supervisor_executor_adapters.json
```

Candidate shape:

```json
{
  "artifact_kind": "supervisor_executor_adapter_policy",
  "schema_version": 1,
  "default_backend_id": "codex",
  "backends": [
    {
      "backend_id": "codex",
      "authority_state": "default",
      "capability_profile": "codex_cli_v1"
    },
    {
      "backend_id": "gh_copilot",
      "authority_state": "experimental",
      "capability_profile": "gh_copilot_cli_v1",
      "allowed_modes": ["smoke", "dry_run"]
    }
  ],
  "non_overridable_invariants": [
    "protocol_markers_required",
    "sandbox_must_not_be_weakened",
    "approval_policy_must_not_be_weakened",
    "canonical_validation_required",
    "raw_prompt_text_must_not_be_published"
  ]
}
```

The policy should be project-owned and reviewable in PRs.

## Candidate CLI Surface

Runtime implementation may add:

```text
--executor-backend <backend_id>
--build-supervisor-executor-adapter-index
--smoke-supervisor-executor <backend_id>
```

Rules:

- omitted backend means the policy default;
- experimental backend selection requires explicit operator intent;
- unsupported backend selection fails before launching a child process;
- smoke mode must not mutate canonical specs;
- direct backend fallback must not broaden permissions.

## Benchmark And Smoke Requirements

Before an alternate executor can run canonical graph work, it should pass a
bounded benchmark suite:

- command discovery and version capture;
- missing-auth failure classification;
- no-op prompt that emits valid protocol markers;
- temp-worktree file-edit fixture;
- timeout handling;
- malformed protocol handling;
- no raw prompt publication;
- no absolute private path publication;
- sandbox/approval non-escalation checks.

The initial GitHub Copilot CLI experiment should probably stop at smoke and
dry-run modes until it proves non-interactive behavior and protocol reliability.

## Derived Artifacts

Future runtime implementation should expose adapter state through derived
artifacts rather than raw logs:

```text
runs/supervisor_executor_adapter_index.json
runs/supervisor_executor_smoke_benchmark.json
```

The adapter index should summarize:

- discovered backends;
- authority state;
- capability support;
- unsupported capability gaps;
- latest smoke result;
- safe next action;
- whether a backend can be selected for canonical runs.

SpecSpace should consume these artifacts or their projection in existing viewer
surfaces. It should not parse raw executor stdout/stderr.

## Safety Rules

- Codex remains default until an explicit policy changes it.
- Experimental backends cannot run canonical mutation paths by default.
- Missing protocol markers are always executor protocol failure.
- Backend fallback cannot weaken sandbox, approval policy, allowed paths, or
  validation.
- Backend-specific stdout/stderr is local-only unless projected through a safe
  artifact.
- Adapter metadata must redact secrets, credentials, raw prompts, and private
  machine-local paths.
- Backend choice and adapter capability state must be visible in run
  provenance.

## Implementation Plan

1. Extract the current Codex executor path into an adapter-shaped interface with
   no behavior change.
2. Add the adapter policy artifact and tests for capability parsing.
3. Add adapter index generation for the default Codex backend.
4. Add smoke-test plumbing for experimental backends without canonical mutation.
5. Add an experimental GitHub Copilot CLI backend if smoke semantics are
   sufficient.
6. Project adapter state into SpecSpace-facing surfaces only after the derived
   artifacts are stable.

## Acceptance Criteria

This proposal is accepted when SpecGraph has a documented executor adapter
boundary with clear safety constraints.

Runtime realization should be considered complete only when:

- existing Codex behavior is preserved by regression tests;
- backend selection is explicit and policy-driven;
- unsupported backends fail before launching;
- normalized run results feed existing protocol and gate logic;
- smoke fixtures prove protocol, timeout, and failure handling;
- experimental backends cannot silently mutate canonical specs;
- viewer-facing artifacts expose adapter state without raw logs.

## Risks

- Some agent CLIs may not support true non-interactive operation.
- Some backends may edit files but fail reliable machine protocol emission.
- Provider-specific auth flows can make CI or hosted operation difficult.
- A generic abstraction can become too broad if it tries to hide real backend
  differences.
- Model API routers may be mistaken for executor adapters unless the layer
  boundary stays explicit.

The mitigation is to keep the first runtime slice narrow: extract the current
Codex path into a named adapter, then add experimental backends only through
read-only smoke contracts.

