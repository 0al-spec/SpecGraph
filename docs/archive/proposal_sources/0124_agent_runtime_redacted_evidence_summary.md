# Agent Runtime Redacted Evidence Summary

## Draft Plan

Publish a safe, report-only runtime evidence detail that summarizes the local
executor evidence chain without publishing local-only artifact payloads.

Input refs:

```text
runs/local_operator_executor_readiness.json
runs/local_operator_executor_smoke.json
runs/local_operator_executor_task_smoke.json
runs/local_operator_executor_report.json
runs/local_operator_executor_report_review_packet.json
runs/local_operator_executor_analysis_report_review_outcome.json
runs/local_operator_executor_analysis_report_followup_packet.json
runs/local_operator_executor_analysis_report_followup_decision.json
runs/local_operator_executor_proposal_draft_request.json
```

Output:

```text
runs/agent_runtime_enforcement_evidence/supervisor-executor-adapter-redacted-local-summary.json
```

## Scope

- Add `redacted_local_summary` as an accepted report-only runtime evidence kind.
- Add a curated redacted evidence detail artifact for
  `specgraph.supervisor.executor_adapter`.
- Include only safe repository-relative refs to local executor artifacts.
- Keep local-only executor artifact payloads out of public static publishing.
- Extend the SpecSpace handoff contract to include the redacted detail artifact.

## Non-Scope

- Do not publish local-only executor artifacts.
- Do not include raw stdout, stderr, prompts, responses, logs, secrets, or
  machine-local paths.
- Do not claim observed runtime enforcement.
- Do not implement sandbox, seccomp, runtime policy enforcement, or executor
  invocation.
- Do not change SpecSpace UI or Platform deployment logic.

## Validation Intent

- Focused tests for the redacted evidence record, checks, index summary, and
  named filters.
- Static bundle tests proving the redacted detail artifact is required while
  local-only source artifacts remain excluded.
- Proposal tracking and work-claim gates.
- Publish bundle and full Python suite before merge.
