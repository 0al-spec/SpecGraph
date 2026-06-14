# Accepted Follow-up Proposal Draft Request

## Status

Draft proposal

## Source Material

This proposal realizes the next gap from `0122`:

```text
bridge_accepted_followup_to_proposal_draft_request
```

Source draft:

- `docs/archive/proposal_sources/0123_accepted_followup_proposal_draft_request.md`

## Context

`0122` records an explicit human/operator decision over an executor follow-up
packet. An `accept` decision should not directly create a proposal, mutate the
proposal lane, or change canonical specs. It should only permit the next
governed request surface.

This slice adds that bridge.

## Goals

- Add `executor_followup_proposal_draft_request_contract`.
- Add a local-only artifact:

  ```text
  runs/local_operator_executor_proposal_draft_request.json
  ```

- Add a Make/CLI surface:

  ```text
  make executor-proposal-draft-request
  tools/supervisor.py --build-local-operator-executor-proposal-draft-request
  ```

- Accept only source decisions with:

  ```text
  summary.status = accepted_for_proposal_draft_request
  human_review_decision.decision = accept
  ```

- Emit only a request with effect:

  ```text
  proposal_draft_request
  ```

## Non-Goals

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

The request artifact uses:

```json
{
  "artifact_kind": "local_operator_executor_proposal_draft_request",
  "schema_version": 1,
  "source_decision_artifact": "runs/local_operator_executor_analysis_report_followup_decision.json",
  "local_only": true,
  "request_kind": "accepted_executor_followup_to_proposal_draft_request",
  "summary": {
    "status": "ready_for_proposal_draft_request",
    "source_decision": "accept",
    "source_decision_status": "accepted_for_proposal_draft_request",
    "authority_level": "request_only",
    "canonical_mutations_allowed": false,
    "proposal_draft_candidate_allowed": false,
    "executor_invocation_allowed": false,
    "next_gap": "build_executor_followup_proposal_draft_candidate"
  }
}
```

## Authority Boundary

The request may connect an accepted decision to a later governed proposal-draft
workflow, but it must still not:

- create a proposal draft candidate;
- write proposal markdown;
- mutate proposal registries or proposal status;
- mutate canonical specs;
- invoke executors;
- apply patches;
- close gaps;
- publish local-only request state.

## Acceptance

This slice is complete when:

- proposal `0123` is tracked in promotion and runtime registries;
- `executor_followup_proposal_draft_request_contract` is declared;
- `make executor-proposal-draft-request` writes the local-only request after an
  accepted decision;
- non-accepted decisions block;
- missing or invalid decisions block without traceback;
- authority expansion and privacy leakage are rejected;
- static bundle tests prove the request artifact is excluded;
- proposal gates, focused tests, static bundle tests, DocC sync, publish bundle,
  and full Python suite pass.
