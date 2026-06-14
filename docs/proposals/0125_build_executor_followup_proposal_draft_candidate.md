# Build Executor Follow-up Proposal Draft Candidate

## Status

Draft proposal

## Source Material

This proposal realizes the next gap from `0123`:

```text
build_executor_followup_proposal_draft_candidate
```

Source draft:

- `docs/archive/proposal_sources/0125_build_executor_followup_proposal_draft_candidate.md`

## Context

`0123` records a local-only request after an accepted executor follow-up
decision. That request is not authority to create a proposal, mutate the
proposal lane, change canonical specs, or invoke another executor.

This slice adds the next local-only artifact: a follow-up proposal draft
candidate. It is separate from the older `0095` report-review candidate path,
because its source is an accepted follow-up request rather than a
`proposal_draft` executor report review packet.

## Goals

- Add `executor_followup_proposal_draft_candidate_contract`.
- Add a local-only artifact:

  ```text
  runs/local_operator_executor_followup_proposal_draft_candidate.json
  ```

- Add a Make/CLI surface:

  ```text
  make executor-followup-proposal-draft-candidate
  tools/supervisor.py --build-local-operator-executor-followup-proposal-draft-candidate
  ```

- Consume only a valid ready source request:

  ```text
  runs/local_operator_executor_proposal_draft_request.json
  summary.status = ready_for_proposal_draft_request
  proposal_draft_request.request_state = ready_for_proposal_draft_request
  ```

- Emit a candidate that still requires explicit downstream promotion policy and
  human review.

## Non-Goals

- Writing proposal markdown.
- Writing proposal source drafts.
- Mutating proposal registries.
- Changing proposal status.
- Mutating canonical specs.
- Running executors.
- Applying patches.
- Closing gaps.
- Publishing local-only artifacts to `specgraph.tech`.
- Changing SpecSpace, Platform, Ontology, or deployment.

## Runtime Contract

The candidate artifact uses:

```json
{
  "artifact_kind": "executor_followup_proposal_draft_candidate",
  "schema_version": 1,
  "source_request_artifact": "runs/local_operator_executor_proposal_draft_request.json",
  "local_only": true,
  "candidate_kind": "accepted_followup_proposal_draft_candidate",
  "draft_kind": "proposal_draft_candidate",
  "proposal_status": "draft_candidate",
  "promotion": {
    "requires_human_promotion": true,
    "target_lane": "proposal_lane",
    "canonical_mutations_allowed": false,
    "proposal_status_mutations_allowed": false,
    "proposal_registry_mutations_allowed": false,
    "proposal_markdown_writes_allowed": false
  },
  "summary": {
    "status": "ready_for_promotion_review",
    "next_gap": "define_followup_proposal_draft_candidate_promotion_policy"
  }
}
```

## Authority Boundary

The candidate may be reviewed for a future promotion policy, but it must still
not:

- create a proposal document;
- write proposal source drafts;
- mutate proposal registries or proposal status;
- mutate canonical specs;
- invoke executors;
- apply patches;
- close gaps;
- publish local-only candidate state.

## Acceptance

This slice is complete when:

- proposal `0125` is tracked in promotion and runtime registries;
- `executor_followup_proposal_draft_candidate_contract` is declared;
- `make executor-followup-proposal-draft-candidate` writes
  `runs/local_operator_executor_followup_proposal_draft_candidate.json`;
- ready requests produce `ready_for_promotion_review`;
- missing, invalid, or non-ready requests block;
- authority expansion and unsafe local payloads are rejected;
- the static bundle excludes
  `runs/local_operator_executor_followup_proposal_draft_candidate.json`;
- proposal gates, focused tests, static bundle tests, `make docc-sync`,
  `make publish-bundle`, and the full Python suite pass.
