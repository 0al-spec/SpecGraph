# Executor Follow-up Human Review Decision

## Draft Plan

Record the explicit human/operator decision after a local analysis report
follow-up packet.

Input:

```text
runs/local_operator_executor_analysis_report_followup_packet.json
```

Output:

```text
runs/local_operator_executor_analysis_report_followup_decision.json
```

## Scope

- Add `executor_analysis_report_followup_decision_contract`.
- Add `make executor-followup-decision`.
- Add `tools/supervisor.py --build-local-operator-executor-analysis-report-followup-decision`.
- Allow decisions:
  - `accept`
  - `reject`
  - `defer`
  - `needs_more_evidence`
- Default the Make target to `needs_more_evidence`.
- Treat `accept` as authorization only for the next governed request-building
  step, not as proposal/canonical authority.
- Preserve local-only status and exclude the decision artifact from public
  static publishing.

## Non-Scope

- Do not bridge accepted decisions to proposal draft requests yet.
- Do not create proposal draft candidates.
- Do not materialize proposal markdown.
- Do not mutate proposal registries or proposal status.
- Do not mutate canonical specs.
- Do not invoke executors.
- Do not apply patches.
- Do not close gaps.
- Do not change SpecSpace, Platform, Ontology, or deployment.

## Validation Intent

- Focused tests for accepted decisions, default `needs_more_evidence`, missing
  packet, invalid decisions, authority expansion, and CLI write behavior.
- Static bundle regression proving the decision artifact is excluded.
- Proposal tracking and work-claim gates.
- Full Python suite before merge.
