# Agent Runtime Redacted Evidence Summary

## Status

Draft proposal

## Source Material

This proposal follows the local executor chain through `0123` and upgrades the
public runtime evidence surface without publishing local-only executor payloads.

Source draft:

- `docs/archive/proposal_sources/0124_agent_runtime_redacted_evidence_summary.md`

## Context

SpecGraph now has a local-only executor path from readiness through smoke,
report review, follow-up decision, and proposal-draft request. Those artifacts
are intentionally not part of the public static bundle because they can carry
operator-local execution context.

At the same time, external consumers such as SpecSpace need a stable, public,
sanitized signal that the local executor evidence chain exists and was handled
under the runtime evidence policy.

## Goals

- Add `redacted_local_summary` as a report-only runtime evidence kind.
- Emit a public detail artifact:

  ```text
  runs/agent_runtime_enforcement_evidence/supervisor-executor-adapter-redacted-local-summary.json
  ```

- Record only safe repo-relative source refs to local executor artifacts.
- State explicitly that local source payloads are not published.
- Extend the static bundle required surfaces and SpecSpace handoff contract.

## Non-Goals

- Publishing local-only executor readiness, smoke, report, follow-up, decision,
  request, proposal-draft, or materialization artifacts.
- Including raw stdout, stderr, prompts, responses, logs, secrets, or
  machine-local paths.
- Claiming observed runtime enforcement.
- Implementing sandbox, seccomp, runtime policy enforcement, or executor
  invocation.
- Changing SpecSpace UI, Platform packaging, or Timeweb deployment.

## Runtime Contract

The redacted detail artifact is still an
`agent_runtime_enforcement_evidence` record:

```json
{
  "artifact_kind": "agent_runtime_enforcement_evidence",
  "schema_version": 1,
  "agent_surface": "specgraph.supervisor.executor_adapter",
  "evidence_kind": "redacted_local_summary",
  "runtime_enforcement_state": "policy_only",
  "status": "passed",
  "safe_evidence_ref": "runs/agent_runtime_enforcement_evidence/supervisor-executor-adapter-redacted-local-summary.json",
  "redacted_local_executor_summary": {
    "source_artifact_refs": [
      "runs/local_operator_executor_readiness.json"
    ],
    "source_payloads_published": false,
    "public_summary_only": true,
    "contains_raw_logs": false,
    "contains_raw_prompts": false,
    "contains_raw_responses": false,
    "contains_secrets": false,
    "contains_machine_local_paths": false
  }
}
```

The evidence index adds:

```text
viewer_projection.named_filters.redacted_local_summary
```

## Authority Boundary

The redacted summary may be published as evidence metadata. It must not grant
proposal authority, canonical mutation authority, executor invocation
authority, or observed runtime enforcement claims.

## Acceptance

This slice is complete when:

- proposal `0124` is tracked in promotion and runtime registries;
- `redacted_local_summary` is accepted by the runtime evidence policy;
- `make agent-runtime-evidence` writes both the runtime smoke and the redacted
  local summary detail artifacts;
- the public static bundle requires the redacted summary detail artifact;
- local-only source artifacts remain excluded from the public bundle;
- the SpecSpace handoff contract lists the redacted detail artifact;
- focused tests, static bundle tests, proposal gates, publish bundle, and full
  Python suite pass.
