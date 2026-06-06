# Agent Passport Derived Surface Runtime

## Status

Draft proposal

## Source Material

This proposal realizes the next bounded runtime slice for
`0059 Agent Passport Adoption for Graph Agents`.

Source draft:

- `docs/archive/proposal_sources/0067_agent_passport_derived_surface_runtime.md`

## Context

Proposal `0059` adopts Agent Passport as the external authority for graph-facing
agent identity, capability, security policy, and verification semantics. It
intentionally does not define Agent Passport itself and does not implement
signing, verification, sandboxing, or runtime enforcement.

Proposal `0066` implemented the first producer artifact in this chain:

```text
runs/supervisor_executor_adapter_index.json
```

That artifact includes executor backend identity and Agent Passport CLI
availability diagnostics. `0059` must consume those diagnostics instead of
adding a second validator discovery path.

## Problem

SpecGraph has proposal-level agreement that graph-facing agents need Passport
identity and verification surfaces, but the derived runtime artifacts named by
`0059` are not yet materialized:

```text
runs/agent_surface_index.json
runs/known_agent_passport_index.json
runs/agent_verification_gap_index.json
```

Without these artifacts, SpecSpace cannot consume a stable agent/executor/passport
producer contract, and the external consumer handoff remains blocked at:

```text
stabilize_specspace_handoff_contract
```

## Goals

- Define `tools/agent_passport_adoption_policy.json`.
- Build a read-only `agent_surface_index` from declared graph-agent surfaces and
  the 0056 executor adapter index.
- Build a read-only `known_agent_passport_index` from those surfaces.
- Build a read-only `agent_verification_gap_index` that normalizes missing
  passports, unavailable validator tooling, unattempted verification, and
  unknown runtime enforcement.
- Consume Agent Passport CLI availability from the 0056 executor adapter index.
- Add a Makefile shortcut and focused tests.
- Mark 0059 runtime realization as covered in proposal runtime tracking.

## Non-Goals

- Implementing Agent Passport schema validation.
- Verifying signatures, issuers, lifecycle, revocation, or integrity hashes.
- Enforcing passport policies at runtime.
- Reading or persisting raw passport material.
- Launching nested agents or running executor smoke benchmarks.
- Implementing SpecSpace UI.
- Changing Platform packaging or deployment.

## Runtime Artifacts

This slice writes:

```text
runs/agent_surface_index.json
runs/known_agent_passport_index.json
runs/agent_verification_gap_index.json
```

The standalone command is:

```text
make agent-passports
```

The corresponding supervisor flag is:

```text
--build-agent-passport-derived-surfaces
```

## Runtime Semantics

`agent_surface_index` shows graph-facing agent surfaces:

- policy-declared surfaces such as `specgraph.supervisor` and
  `specspace.operator_assistant`;
- executor backend surfaces derived from
  `runs/supervisor_executor_adapter_index.json`, such as
  `specgraph.executor.codex`.

`known_agent_passport_index` records the current graph-side Passport reference
state. A Passport reference is not verification.

`agent_verification_gap_index` records report-only gaps:

- `missing_passport`;
- `verification_tool_unavailable`;
- `verification_not_attempted`;
- `runtime_enforcement_unknown`.

The verification tool availability gap must come from the 0056 executor adapter
diagnostic surface, not from a separate direct lookup.

## Safety Boundary

These artifacts are derived observation surfaces. They must not:

- persist local executable paths;
- persist raw Passport documents, signatures, validator logs, provider tokens, or
  secrets;
- claim verification when only a URI is known;
- claim runtime enforcement when no compatible runtime has enforced policy;
- mutate SpecSpace or Platform.

## Validation

This proposal is complete when:

- `make agent-passports` writes the three derived artifacts;
- focused tests cover policy shape, executor-derived surfaces, verification gaps,
  and standalone artifact writing;
- 0059 proposal runtime tracking is covered;
- proposal tracking/work-claim gates pass;
- full test suite passes.

