# 0156 CLI Candidate Approval Flow

## Status

Draft proposal

Decision scope: CLI and agent-mediated approval contract for advancing a
`product_idea_to_spec` candidate from review-ready state toward Git Service
promotion.

This document defines a CLI approval contract only. It does not add a runtime
command, mutate candidate artifacts, mutate canonical specs, write Ontology
packages, create Git branches or commits, open pull requests, publish read
models, or grant SpecSpace write authority.

## Source Material

This proposal captures the operator intent that CLI-mode SpecGraph work should
preserve explicit human approval when a product candidate is ready for
promotion, while still allowing the agent to prepare recommendations, evidence,
and a promotion request.

Source draft:

- `docs/archive/proposal_sources/0156_cli_candidate_approval_flow.md`

Related proposal context:

- `0149` Event-Storming Intake Artifact
- `0150` Candidate Spec Graph Contract
- `0151` Pre-SIB And Coherence Metrics
- `0152` Autonomous Candidate Repair Loop
- `0153` Candidate Spec Materialization Preview
- `0154` Idea-to-Spec Promotion Gate
- `0155` Product Workspace Active Candidate Source

## Summary

The idea-to-spec flow now has a deterministic active candidate source and a
promotion gate, but CLI operation still needs a stable approval boundary. The
agent may explain readiness and recommend the next step, but it must not treat a
ready candidate as accepted product truth.

The short rule is:

```text
No user/operator approval -> no Git Service execution.
No merged review -> no read-model publication.
No approval artifact -> no audit trail for candidate promotion.
```

This proposal introduces a future approval artifact:

```text
runs/candidate_approval_decision.json
```

The artifact records the operator decision that a candidate may advance to the
next controlled step. It is evidence for the Git Service handoff; it is not a
canonical spec mutation.

## Problem

The product workspace flow currently separates generated candidate state from
canonical graph state:

```text
event-storming intake
  -> candidate graph
  -> pre-SIB/coherence report
  -> repair loop
  -> materialization preview
  -> promotion gate
  -> active candidate source
```

That chain can make a candidate review-ready, but CLI mode still needs to answer
one operational question:

```text
Who approved moving this candidate from inspectable draft state into a Git
Service promotion attempt?
```

Without an explicit approval contract, the system can blur three distinct
states:

- the agent believes the candidate is ready;
- the operator approves a promotion attempt;
- repository review accepts and merges the resulting canonical change.

Those states must remain separate. Otherwise a CLI workflow can accidentally
look like human-approved product specification creation when it only produced a
validated draft.

## Proposal

Define a CLI candidate approval flow over the existing product workspace
handoff artifacts.

The flow has five explicit transitions:

1. `candidate_review_requested`
2. `promotion_request_approved`
3. `git_service_execution_approved`
4. `review_merged`
5. `read_model_publish_approved`

For the first implementation slice, SpecGraph should only define the contract
for recording the operator decision that a ready candidate may advance from
`candidate_review_requested` to `promotion_request_approved`.

Later Platform and Git Service slices can consume that decision before branch,
commit, pull request, review-status, and read-model publication operations.

## Candidate Approval Decision Artifact

The proposed artifact shape is:

```json
{
  "artifact_kind": "candidate_approval_decision",
  "schema_version": 1,
  "proposal_id": "0156",
  "generated_at": "2026-06-23T00:00:00Z",
  "canonical_mutations_allowed": false,
  "ontology_writes_allowed": false,
  "tracked_artifacts_written": false,
  "workspace": {
    "workspace_id": "team-decision-log",
    "mode": "product_idea_to_spec",
    "repository_role": "product_spec_workspace"
  },
  "candidate": {
    "candidate_id": "tdl.seed.v1",
    "active_candidate_ref": "runs/active_idea_to_spec_candidate.json",
    "promotion_gate_ref": "runs/idea_to_spec_promotion_gate.json"
  },
  "decision": {
    "state": "approved | rejected | needs_context | superseded",
    "approved_transition": "candidate_review_requested -> promotion_request_approved",
    "operator_ref": "local_operator:<redacted-or-stable-handle>",
    "reason": "short public-safe rationale",
    "conditions": []
  },
  "evidence_refs": [
    {
      "artifact": "runs/pre_sib_coherence_report.json",
      "digest": "sha256:..."
    },
    {
      "artifact": "runs/candidate_repair_loop_report.json",
      "digest": "sha256:..."
    },
    {
      "artifact": "runs/candidate_spec_materialization_report.json",
      "digest": "sha256:..."
    },
    {
      "artifact": "runs/idea_to_spec_promotion_gate.json",
      "digest": "sha256:..."
    }
  ],
  "authority_boundary": {
    "agent_may_recommend": true,
    "agent_may_approve": false,
    "git_service_execution_remains_separate": true,
    "review_merge_required_for_canonical_acceptance": true,
    "read_model_publish_requires_merged_review": true
  }
}
```

Raw prompt text, private operator notes, local paths, credentials, and private
environment data must not be published in this artifact.

## CLI Interaction Model

In CLI mode, the agent should present a bounded recommendation:

```text
Candidate: team-decision-log / tdl.seed.v1
Promotion gate: ready
Remaining blockers: none
Recommendation: approve promotion request creation
Authority: this approval does not create a branch, commit, PR, merge, or read model

Approve transition candidate_review_requested -> promotion_request_approved?
```

The accepted decision should write a future
`candidate_approval_decision` artifact. A rejected or context-seeking decision
should be equally explicit, so downstream tools can stop without guessing.

The CLI must not turn an unanswered prompt into approval. Silence, timeout, or
ambiguous response maps to `needs_context` or no artifact.

## Authority Boundary

This proposal does not grant write authority.

It does not:

- execute prompt agents;
- mutate candidate graph artifacts;
- mutate canonical SpecGraph specs;
- write Ontology packages or lockfiles;
- accept ontology terms;
- create Git branches or commits;
- open pull requests;
- merge reviews;
- publish read models;
- let SpecSpace write into a checkout.

Git Service execution remains a separate authority step. A candidate approval
decision can authorize a promotion request attempt, but it cannot replace
Platform validation, Git Service execution policy, repository review, merge
policy, or read-model publication policy.

## Acceptance Criteria

- A ready active candidate is not promoted without an explicit operator
  decision artifact.
- The agent can recommend approval, rejection, or context completion, but cannot
  approve on its own.
- The approval artifact links the active candidate source, promotion gate, and
  relevant metric/repair/materialization evidence by public-safe refs and
  digests.
- `canonical_mutations_allowed: false` remains true for the approval artifact
  itself.
- Low-quality or unresolved candidates must produce `rejected` or
  `needs_context`, not `approved`.
- No CLI response, timeout, or ambiguous answer may be interpreted as approval.
- Repository review and read-model publication remain separate downstream
  authorities.

## Future Implementation Slices

1. Add `tools/candidate_approval_decision.py` and a read-only Make target that
   writes `runs/candidate_approval_decision.json`.
2. Add a contract test that rejects approval when the active candidate source or
   promotion gate is missing or unready.
3. Teach Platform promotion-request generation to require or accept the approval
   artifact before Git Service execution.
4. Show the approval state in SpecSpace product workspace workflow lanes.
5. Add post-review closure artifacts for `review_merged` and
   `read_model_publish_approved`.

## Validation

This contract slice is complete when:

- this proposal and source draft exist;
- `tools/proposal_runtime_registry.json` classifies `0156` as
  `deferred_until_canonicalized`;
- `docs/product_workspace_graph_versioning_roadmap.md` and DocC mention the CLI
  candidate approval flow;
- proposal tracking gate passes.

