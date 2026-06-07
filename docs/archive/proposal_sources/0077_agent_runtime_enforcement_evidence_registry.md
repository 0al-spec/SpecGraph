# Agent Runtime Enforcement Evidence Registry

## Draft Intent

Close the next small Agent Passport gap after `0076`: materialize the
report-only runtime enforcement evidence artifact family that `0076` described
as a plan.

## Bounded Scope

- Add a generated `agent_runtime_enforcement_evidence_index` surface.
- Add one curated runtime-smoke evidence detail artifact for
  `specgraph.supervisor.executor_adapter`.
- Keep the smoke report-only: it proves derived adapter/passport surfaces are
  internally consistent and safe to reference, not that sandbox or runtime
  policy enforcement exists.
- Add a standalone builder command and Make target.
- Preserve safe evidence refs and reject machine-local path leakage.

## Out of Scope

- No sandbox, seccomp, chroot, OPA, agentifyd, Pi adapter, or runtime policy
  enforcement implementation.
- No agent launches.
- No signature, revocation, lifecycle, trust-store, or integrity validation.
- No SpecSpace UI or Platform deploy change.
- No promotion to `runtime_enforcement_state: observed` or
  `V8_runtime_enforcement_observed`.

## Acceptance Notes

The slice is valid if focused tests prove a passed smoke record is emitted for
`specgraph.supervisor.executor_adapter`, missing producer contracts produce a
non-passing evidence record, generated refs stay repository-relative, and the
usual proposal gates plus full tests pass.
