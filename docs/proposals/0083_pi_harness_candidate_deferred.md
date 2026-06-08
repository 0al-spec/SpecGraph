# Pi Harness Candidate Deferred

## Status

Draft proposal

## Source Material

This proposal records an architectural decision about Pi as an external executor
harness candidate.

Source draft:

- `docs/archive/proposal_sources/0083_pi_harness_candidate_deferred.md`

## Context

`0056 Supervisor Executor Adapter Gateway` defines the launch-and-observe
boundary for nested executors. It keeps Codex as the default stable backend and
allows alternate backends only as explicit experimental adapters.

`0066 Supervisor Executor Adapter Index Runtime` surfaces the current Codex
backend through `runs/supervisor_executor_adapter_index.json` without launching
nested executors. `0080 Supervisor Executor Adapter Enforcement Smoke` then adds
a report-only invocation-boundary smoke check, but explicitly leaves Pi adapter
implementation out of scope.

After `0082 Agent Passport CLI Availability in Static Publish`, the public
static artifact bundle can verify Agent Passport references, but static publish
is still not an executor runtime. The static runner may report the Codex
backend executable as unavailable, while local operator work can still use Codex
through trusted local Codex/ChatGPT authentication. That should not force
SpecGraph to install Codex in static publish or treat Pi as an immediate
replacement.

Pi is useful as a future coding-agent harness, especially for SpecSpace
handoffs, BYOK demo flows, and external tool/RPC execution. It should be
introduced as a deferred experimental harness candidate, not embedded in the
canonical SpecGraph core.

## Decision

SpecGraph records three executor runtime modes:

```text
static_publish_environment
  - builds and publishes deterministic artifacts
  - may install verifier tools such as agent-passport
  - is not expected to provide Codex or Pi executor runtimes

local_operator_environment
  - trusted developer/operator machine
  - Codex remains the default stable local executor
  - Codex may use local Codex/ChatGPT authentication or local Codex CLI auth

external_harness_environment
  - future hosted or sandboxed agent harness
  - Pi is a deferred experimental candidate
  - Pi uses provider_config_ref / BYOK, not Codex auth cache
```

Codex remains the default stable backend for local operator work. This preserves
the cost and ergonomics benefits of the existing Codex workflow.

Pi is recorded as a planned external harness candidate only. It must not be
added to `tools/supervisor_executor_adapter_policy.json`, Agent Passport
runtime surfaces, SpecSpace UI, Platform packaging, or static publish until a
later implementation proposal defines the concrete adapter contract and
validation evidence.

## Boundaries

Pi must not become canonical authority:

- no direct mutation of canonical specs;
- no supervisor gate override;
- no raw credentials or ChatGPT/Codex auth cache in persisted artifacts;
- no public Timeweb demo container with a private ChatGPT/Codex identity;
- no fallback from a denied Pi capability to broader local privileges.

Pi may eventually produce only governed outputs:

- reports;
- proposal drafts;
- patch suggestions;
- session import artifacts;
- validation summaries.

Supervisor remains the only canonical graph mutator. Human/supervisor review
gates still decide whether Pi-produced work can be applied.

## Credential Boundary

The executor credential model is:

```text
codex backend
  auth: local Codex/ChatGPT or Codex CLI auth
  scope: trusted local operator machine
  persisted artifacts: no auth cache, no token, no executable path

pi backend candidate
  auth: OpenAI API key / BYOK provider_config_ref or another explicit provider ref
  scope: future external harness environment
  persisted artifacts: no raw API key, no browser session, no auth cache
```

`~/.codex/auth.json` and equivalent Codex credential stores are local secrets.
They must not be copied into public demo containers, static publish runners, or
SpecSpace/SpecGraph persisted artifacts.

## Relationship To SpecSpace

SpecSpace remains a deterministic viewer/context compiler, not an executor.
The likely Pi integration point is a future external-agent handoff:

```text
SpecSpace compiled context + provenance
  -> Pi harness
  -> report/proposal/patch suggestion
  -> SpecGraph supervisor review
```

Pi session import into SpecSpace lineage is a promising future slice, but this
proposal does not define the session artifact contract.

## Relationship To SpecAgent

`0056` already names a future SpecAgent boundary. Pi does not force that
extraction now. Pi becomes one pressure signal for a later SpecAgent runtime
only after real implementation work needs provider adapters, sandbox policy,
agent identity, BYOK execution, and tool policy outside the SpecGraph
deterministic core.

## Non-Goals

- Implementing a Pi adapter.
- Adding `specgraph.executor.pi` to runtime policy or Agent Passport surfaces.
- Installing Pi in CI, static publish, Timeweb, or local Makefile targets.
- Changing Codex default backend behavior.
- Implementing SpecSpace session import.
- Implementing sandbox, seccomp, chroot, agentifyd, or runtime enforcement for
  Pi.
- Claiming Pi is production-ready or safe for canonical graph mutation.

## Future Work

A later implementation proposal may add:

- `specgraph.executor.pi` as an experimental backend in
  `tools/supervisor_executor_adapter_policy.json`;
- a Pi Agent Passport document and report-only verification entry;
- a sandboxed Pi adapter smoke fixture;
- SpecSpace external-agent handoff UI/API support;
- Pi session JSONL import into SpecSpace lineage;
- BYOK provider configuration UX and secret-handling rules.

That proposal must include runtime evidence proving Pi cannot directly mutate
canonical graph state or bypass supervisor review.

## Acceptance

This slice is complete when:

- proposal `0083` is tracked in the proposal promotion registry;
- proposal runtime tracking records this as a deferred executor-harness
  candidate;
- existing executor adapter runtime artifacts remain unchanged;
- proposal gates and the full Python suite pass.
