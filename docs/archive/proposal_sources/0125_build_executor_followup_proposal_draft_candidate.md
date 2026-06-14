# Build Executor Follow-up Proposal Draft Candidate

## Context

`0123` added a local-only request bridge from an accepted executor follow-up
decision into the proposal-draft workflow. That request intentionally cannot
create a candidate, write proposal markdown, or mutate proposal/canonical
state.

The next bounded step is to turn a ready request into a separate local-only
candidate artifact. This keeps accepted follow-up requests visible to the
proposal workflow without granting the request direct proposal-lane authority.

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

- Consume only a valid source request:

  ```text
  runs/local_operator_executor_proposal_draft_request.json
  summary.status = ready_for_proposal_draft_request
  proposal_draft_request.request_state = ready_for_proposal_draft_request
  proposal_draft_request.requested_effects = ["proposal_draft_request"]
  ```

- Emit a candidate with:

  ```text
  artifact_kind = executor_followup_proposal_draft_candidate
  local_only = true
  candidate_kind = accepted_followup_proposal_draft_candidate
  draft_kind = proposal_draft_candidate
  proposal_status = draft_candidate
  promotion.requires_human_promotion = true
  ```

## Non-Goals

- Writing `docs/proposals/*.md`.
- Writing `docs/archive/proposal_sources/*.md`.
- Reusing or changing the 0095 report-review candidate artifact.
- Mutating proposal registries or proposal status.
- Mutating canonical specs.
- Running executors.
- Applying patches.
- Closing gaps.
- Publishing local-only candidate state.
- Adding SpecSpace, Platform, Ontology, or deployment changes.

## Authority Boundary

The candidate is review input only. It must not:

- treat the source request as authority;
- treat the candidate as authority;
- write proposal markdown;
- mutate proposal registries or proposal status;
- mutate canonical specs;
- invoke executors;
- apply patches;
- close gaps;
- directly create a public proposal.

The successful next gap is:

```text
define_followup_proposal_draft_candidate_promotion_policy
```

## Acceptance

This slice is complete when:

- proposal `0125` is tracked in promotion and runtime registries;
- `executor_followup_proposal_draft_candidate_contract` is declared;
- `make executor-followup-proposal-draft-candidate` writes the local-only
  candidate from a ready request;
- missing, invalid, or non-ready requests block without traceback;
- authority expansion and privacy leakage are rejected;
- static bundle tests prove the candidate artifact is excluded;
- proposal gates, focused tests, static bundle tests, DocC sync, publish bundle,
  and full Python suite pass.
