# Supervisor Executor Adapter Enforcement Smoke

## Draft Intent

Advance the Agent Passport runtime evidence line from report existence to a
minimal executable-boundary smoke for `specgraph.supervisor.executor_adapter`.

## Bounded Scope

- Add one concrete runtime-smoke check:
  `executor_adapter_invocation_boundary`.
- Verify the supervisor executor adapter policy uses declarative CLI executable
  lookup instead of shell command templates.
- Verify the generated executor adapter index does not persist executable paths
  or command lines.
- Keep the evidence report-only and continue publishing it through the existing
  `agent_runtime_enforcement_evidence_index` surface.
- Ensure the static artifact publish bundle refreshes and requires the
  executor/passport/runtime evidence producer artifacts so HTTP consumers can
  see the evidence after deployment.

## Out of Scope

- No sandbox, seccomp, chroot, OPA, agentifyd, Pi adapter, or runtime policy
  enforcement implementation.
- No agent launches.
- No passport signature, revocation, lifecycle, trust-store, or integrity
  validation.
- No SpecSpace UI or Platform deploy change.
- No promotion to `runtime_enforcement_state: observed` or
  `V8_runtime_enforcement_observed`.

## Acceptance Notes

The slice is valid if focused tests prove the new invocation-boundary check
passes for the current declarative executor adapter policy, fails when shell
command fields are introduced, fails when executable paths are persisted,
`make publish-bundle` includes the generated agent/runtime evidence artifacts,
and the usual proposal gates plus full tests pass.
