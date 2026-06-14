# Executor Follow-up Human Review Decision

## Status

Draft proposal

## Source Material

This proposal realizes the next gap from `0121`:

```text
human_review_decision_for_executor_followup
```

Source draft:

- `docs/archive/proposal_sources/0122_executor_followup_human_review_decision.md`

## Context

`0121` builds a local-only follow-up packet with governed decision options, but
there is no typed artifact recording which option the human/operator selected.
Without that artifact, the next bridge could either skip review or encode a
decision implicitly in code.

This slice adds the explicit decision record.

## Goals

- Add `executor_analysis_report_followup_decision_contract`.
- Add a local-only artifact:

  ```text
  runs/local_operator_executor_analysis_report_followup_decision.json
  ```

- Add a Make/CLI surface:

  ```text
  make executor-followup-decision EXECUTOR_FOLLOWUP_DECISION=<accept|reject|defer|needs_more_evidence>
  tools/supervisor.py --build-local-operator-executor-analysis-report-followup-decision
  ```

- Allow exactly four decision values: `accept`, `reject`, `defer`, and
  `needs_more_evidence`.
- Route accepted decisions to:

  ```text
  bridge_accepted_followup_to_proposal_draft_request
  ```

- Keep every decision local-only and non-canonical.

## Non-Goals

- Bridging accepted decisions to proposal draft requests.
- Creating proposal draft candidates.
- Materializing proposal markdown.
- Mutating proposal registries or proposal status.
- Mutating canonical specs.
- Running a new executor task.
- Applying patches.
- Closing gaps.
- Publishing local-only executor artifacts.
- Changing SpecSpace, Platform, Ontology, or deployment.

## Runtime Contract

The decision artifact uses:

```json
{
  "artifact_kind": "local_operator_executor_analysis_report_followup_decision",
  "schema_version": 1,
  "source_followup_packet_artifact": "runs/local_operator_executor_analysis_report_followup_packet.json",
  "local_only": true,
  "decision_kind": "executor_followup_human_review_decision",
  "summary": {
    "status": "accepted_for_proposal_draft_request",
    "decision": "accept",
    "authority_level": "human_review_followup_only",
    "canonical_mutations_allowed": false,
    "proposal_draft_candidate_allowed": false,
    "executor_invocation_allowed": false,
    "next_gap": "bridge_accepted_followup_to_proposal_draft_request"
  },
  "human_review_decision": {
    "decision": "accept",
    "reviewer": "local_operator",
    "decision_is_canonical_authority": false,
    "decision_requires_downstream_policy": true
  }
}
```

`reject`, `defer`, and `needs_more_evidence` remain terminal/deferred local
states and do not authorize proposal-draft request bridging.

## Authority Boundary

The artifact may record a human/operator follow-up decision, but it must still
not:

- mutate canonical specs;
- create proposal draft candidates;
- write proposal markdown;
- mutate proposal registries or proposal status;
- invoke executors;
- apply patches;
- close gaps;
- publish local-only decision state.

## Acceptance

This slice is complete when:

- proposal `0122` is tracked in promotion and runtime registries;
- `executor_analysis_report_followup_decision_contract` is declared;
- `make executor-followup-decision` writes the local-only decision artifact;
- `accept`, `reject`, `defer`, and `needs_more_evidence` are all explicit;
- accepted decisions route to
  `bridge_accepted_followup_to_proposal_draft_request`;
- invalid decisions, missing packets, authority expansion, and privacy leakage
  are rejected;
- static bundle tests prove the decision artifact is excluded;
- proposal gates, focused tests, static bundle tests, DocC sync, publish bundle,
  and full Python suite pass.
