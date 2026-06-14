# Accepted Follow-up Proposal Draft Request

## Draft Plan

Bridge an accepted executor follow-up decision to a local-only proposal draft
request without producing a proposal draft candidate yet.

Input:

```text
runs/local_operator_executor_analysis_report_followup_decision.json
```

Output:

```text
runs/local_operator_executor_proposal_draft_request.json
```

## Scope

- Add `executor_followup_proposal_draft_request_contract`.
- Add `make executor-proposal-draft-request`.
- Add `tools/supervisor.py --build-local-operator-executor-proposal-draft-request`.
- Accept only decisions with:
  - `summary.status=accepted_for_proposal_draft_request`;
  - `human_review_decision.decision=accept`.
- Produce only a request for a later proposal-draft candidate builder.
- Preserve local-only status and exclude the request artifact from public
  static publishing.

## Non-Scope

- Do not create proposal draft candidates.
- Do not materialize proposal markdown.
- Do not mutate proposal registries or proposal status.
- Do not mutate canonical specs.
- Do not invoke executors.
- Do not apply patches.
- Do not close gaps.
- Do not change SpecSpace, Platform, Ontology, or deployment.

## Validation Intent

- Focused tests for accepted decisions, non-accepted decisions, missing
  decisions, authority expansion, and CLI write behavior.
- Static bundle regression proving the request artifact is excluded.
- Proposal tracking and work-claim gates.
- Full Python suite before merge.
