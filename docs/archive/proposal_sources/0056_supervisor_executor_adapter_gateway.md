# Supervisor Executor Adapter Gateway Source Draft

## Source Context

SpecGraph supervisor currently treats the nested executor as a Codex CLI-shaped
implementation detail. That has been productive while the project is
bootstrapping, because the supervisor can rely on one command surface, one
protocol contract, and one isolated runtime profile.

Recent operator discussion raised two related pressures:

- GitHub Copilot CLI is available locally and may be useful as an alternate
  executor experiment.
- Generic LLM gateways and routers exist, but they do not directly solve
  worktree-mutating agent execution, sandboxing, or supervisor protocol
  guarantees.

This means SpecGraph needs a clearer boundary between:

- model API routing;
- agent CLI execution;
- supervisor machine protocol parsing;
- operator-facing UI protocols.

## Operator Intent

Define a proposal for a pluggable supervisor executor adapter layer.

The goal is not to replace Codex immediately. The goal is to stop hardcoding
Codex-specific assumptions into the supervisor boundary so future executor
experiments can be compared safely.

Desired direction:

```text
Supervisor
  -> ExecutorAdapter
      -> codex default backend
      -> gh_copilot experimental backend
      -> future agent CLI backends
  -> normalized ExecutorRunResult
  -> existing protocol, validation, and gate logic
```

The adapter layer should preserve the current governance model. Alternate
executors must prove they can satisfy non-interactive execution, file mutation
boundaries, timeout behavior, machine protocol markers, and safe failure
classification before they can influence canonical graph work.

## Desired Outcome

Define:

- a stable executor adapter vocabulary;
- a capability contract for supported and experimental backends;
- a normalized run result contract;
- a safety distinction between LLM API gateways, agent CLI executors, and UI
  protocols;
- a benchmark/smoke path for new executor backends;
- a future viewer-facing artifact for adapter capability and health.

## Boundary

This proposal should not implement a new executor immediately.

It should not:

- make GitHub Copilot CLI the default;
- weaken sandbox or approval behavior;
- allow backend-specific prompt output to bypass supervisor protocol markers;
- replace the current Codex path before an equivalent adapter passes regression
  tests;
- confuse model API routing with worktree-mutating agent execution;
- require SpecSpace to read raw executor logs.

