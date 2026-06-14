# Build Executor Analysis Report Follow-up Packet

## Draft Plan

Build the local-only packet that consumes a ready analysis report review outcome
and prepares the explicit human/supervisor decision step.

Input:

```text
runs/local_operator_executor_analysis_report_review_outcome.json
```

Output:

```text
runs/local_operator_executor_analysis_report_followup_packet.json
```

## Scope

- Add `executor_analysis_report_followup_packet_contract`.
- Add `make executor-analysis-report-followup-packet`.
- Add `tools/supervisor.py --build-local-operator-executor-analysis-report-followup-packet`.
- Build only from a source outcome accepted by
  `executor_analysis_report_followup_policy`.
- Preserve sanitized findings and safe evidence refs.
- Carry governed decision options:
  - `accept`
  - `reject`
  - `defer`
  - `needs_more_evidence`
- Preserve review-only authority:
  - follow-up packet is not authority;
  - human/supervisor decision remains required;
  - proposal draft production remains forbidden;
  - executor invocation, canonical mutation, proposal mutation, patch
    application, and gap closure remain forbidden.
- Exclude the local-only packet from public static publishing.

## Non-Scope

- Do not record the human review decision yet.
- Do not create proposal draft candidates.
- Do not materialize proposal markdown.
- Do not mutate proposal registries or proposal status.
- Do not mutate canonical specs.
- Do not invoke an executor.
- Do not apply patches.
- Do not close gaps.
- Do not publish local-only executor artifacts.
- Do not change SpecSpace, Platform, Ontology, or deployment.

## Validation Intent

- Focused supervisor tests for ready packet generation, missing source outcome,
  blocked source outcome, authority expansion, privacy leakage, validator
  rejection, and CLI write behavior.
- Static bundle regression proving the packet is excluded.
- Proposal tracking and work-claim gates.
- `make executor-analysis-report-review-outcome executor-analysis-report-followup-packet`.
- Full Python suite before merge.
