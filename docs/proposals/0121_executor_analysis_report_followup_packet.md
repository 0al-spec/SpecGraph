# Build Executor Analysis Report Follow-up Packet

## Status

Draft proposal

## Source Material

This proposal realizes the next gap from `0120`:

```text
build_executor_analysis_report_followup_packet
```

Source draft:

- `docs/archive/proposal_sources/0121_executor_analysis_report_followup_packet.md`

## Context

`0120` defined the policy boundary for consuming a local analysis report review
outcome. That policy intentionally stopped before writing a new artifact.

This slice adds the local-only follow-up packet that can be reviewed by a human
or supervisor before any downstream action is allowed.

## Goals

- Add `executor_analysis_report_followup_packet_contract`.
- Add a local-only artifact:

  ```text
  runs/local_operator_executor_analysis_report_followup_packet.json
  ```

- Add a Make/CLI surface:

  ```text
  make executor-analysis-report-followup-packet
  tools/supervisor.py --build-local-operator-executor-analysis-report-followup-packet
  ```

- Build the packet only from an outcome accepted by
  `executor_analysis_report_followup_policy`.
- Carry sanitized findings, safe evidence refs, and governed decision options.
- Reject missing, invalid, blocked, privacy-leaking, or authority-expanding
  source outcomes.
- Exclude the local-only packet from public static publishing.

## Non-Goals

- Recording the human review decision.
- Creating proposal draft candidates.
- Materializing proposal markdown.
- Mutating proposal registries or proposal status.
- Mutating canonical specs.
- Running a new executor task.
- Applying patches.
- Closing gaps.
- Changing SpecSpace, Platform, Ontology, or deployment.

## Runtime Contract

The follow-up packet uses:

```json
{
  "artifact_kind": "local_operator_executor_analysis_report_followup_packet",
  "schema_version": 1,
  "source_outcome_artifact": "runs/local_operator_executor_analysis_report_review_outcome.json",
  "local_only": true,
  "packet_kind": "analysis_report_followup",
  "summary": {
    "status": "ready_for_followup_review",
    "report_kind": "analysis_report",
    "authority_level": "review_only",
    "human_review_required": true,
    "canonical_mutations_allowed": false,
    "proposal_draft_candidate_allowed": false,
    "executor_invocation_allowed": false,
    "next_gap": "human_review_decision_for_executor_followup"
  },
  "followup_packet": {
    "packet_state": "ready_for_followup_review",
    "decision_options": ["accept", "reject", "defer", "needs_more_evidence"],
    "operator_decision_required": true,
    "followup_packet_is_authority": false
  }
}
```

Blocked packets use explicit statuses such as
`blocked_missing_review_outcome`, `blocked_invalid_review_outcome`,
`blocked_followup_policy`, `blocked_authority_boundary`,
`blocked_privacy_boundary`, or `blocked_policy_contract`.

## Authority Boundary

The packet must preserve these invariants:

- executor report is not authority;
- review packet is not authority;
- review outcome is not authority;
- follow-up packet is not authority;
- human/supervisor review remains required;
- proposal draft candidate production is forbidden;
- executor invocation is forbidden;
- proposal status and registry mutations are forbidden;
- proposal markdown writes are forbidden;
- canonical mutations are forbidden;
- patch application is forbidden;
- gap closure is forbidden;
- local packet publication in the public static bundle is forbidden.

## Acceptance

This slice is complete when:

- proposal `0121` is tracked in promotion and runtime registries;
- `executor_analysis_report_followup_packet_contract` is declared;
- `make executor-analysis-report-followup-packet` writes the local-only packet;
- valid ready outcomes produce `ready_for_followup_review`;
- missing or invalid outcomes block without traceback;
- blocked outcomes remain blocked by policy;
- authority expansion and privacy leakage are rejected;
- static bundle tests prove the packet is excluded;
- proposal gates, focused tests, static bundle tests, DocC sync, publish bundle,
  and full Python suite pass.
