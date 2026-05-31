# Supervisor Executor Adapter Gateway Contract

## Purpose

This document is the first SpecGraph-side contract surface for proposal
`0056_supervisor_executor_adapter_gateway`.

The gateway is a launch-and-observe boundary for nested supervisor executors. It
does not implement a BYOK demo, a SpecSpace UI, a container runner, or an
alternate executor backend. It defines the request and report shapes that future
runtime implementations must use when they connect external executors to
SpecGraph.

## Boundary

```text
SpecGraph supervisor
  -> bounded executor request
  -> executor adapter gateway
  -> backend-specific runner
  -> normalized executor report
  -> supervisor validation and gates
```

The adapter gateway is not the trust boundary. It prepares a backend-specific
run and reports what happened. Existing deterministic supervisor validation
continues to decide whether the run is acceptable.

## Request Contract

A bounded executor request must contain:

- `request_id`: stable request identifier for correlation.
- `workspace_root`: repo-relative or sandbox-root workspace reference.
- `target_ref`: target spec, proposal, operator request, or smoke fixture.
- `provider_config_ref`: opaque runtime provider configuration reference.
- `policy_envelope`: sandbox, approval, allowed-path, and timeout constraints.
- `capability_envelope`: declared backend capabilities for this run.

The gateway must not store API key values, raw provider secrets, billing account
details, or web authentication session data. BYOK-style provider configuration
is represented only through `provider_config_ref`.

## Report Contract

A normalized executor report must contain:

- `request_id`: the request being answered.
- `run_id`: concrete executor run identifier.
- `status`: `ready`, `blocked`, or `failed`.
- `logs_ref`: redacted/local-only log reference.
- `produced_artifacts`: repo-relative artifacts produced by the run.
- `policy_decisions`: adapter-side policy decisions and denials.
- `error_class`: normalized failure class.

`status: ready` means the executor produced a report that can enter supervisor
validation. It does not mean the task succeeded, the graph should be mutated, or
review gates can be skipped.

## Error Classes

The initial normalized error vocabulary is:

- `none`
- `provider_config_missing`
- `auth_unavailable`
- `unsupported_backend`
- `policy_denied`
- `timeout`
- `protocol_failure`
- `executor_crash`
- `unknown`

Backends may produce backend-specific details, but viewer-facing projections
should use the normalized class first.

## BYOK/Demo Precursor

This contract intentionally supports a future BYOK demo through
`provider_config_ref`, not through stored secrets.

Out of scope for this contract slice:

- SpecSpace login.
- BYOK form.
- OpenAI billing or account logic.
- Timeweb deployment wiring.
- Real Codex/Copilot/Claude/Gemini container runner.
- Agent Passport enforcement implementation.

## Safety Requirements

- The gateway must not persist raw prompt text or secrets.
- Backend fallback must not broaden permissions.
- Unsupported backends must fail before launch.
- Experimental backends require explicit operator selection.
- Canonical mutations require normal supervisor validation.
- Raw logs are local-only unless redacted into a derived artifact.
- Adapter success is never final supervisor success.

## Policy Artifact

The machine-readable policy surface is:

```text
tools/supervisor_executor_adapter_policy.json
```

The policy declares request/report required fields, status vocabulary, error
classes, BYOK boundary rules, and non-overridable invariants.
