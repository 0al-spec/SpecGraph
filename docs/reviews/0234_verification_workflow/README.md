# Verification workflow return path

SG-RFC-0234 records the requested `verify-criteria/v1` composition. Status:
`deferred_until_canonicalized`; planning target SG-SPEC-0009. Runtime workflow
execution and canonical adoption remain pending.

- [Proposal](../../proposals/0234_verification_workflow.md)
- [Attributed conversation](../../archive/proposal_sources/0234_verification_workflow.md)
- [Draft obligations](../../proposals/0234_verification_workflow.intent.yaml)
- [Registration packet](operator-request.json)
- [Registration observation](graph-links.json)
- [User intent](../../../intent_layer/nodes/user_intent--0234-verification-workflow--c03e0097.json)
- [Operator request](../../../intent_layer/nodes/operator_request--0234-verification-workflow--f6d7f9ec.json)
- [Proposal node](../../../proposal_lane/nodes/proposal--0234-verification-workflow--26beab5e.json)

The existing route is UserIntent -> OperatorRequest -> Proposal -> SG-SPEC-0009.
Return through `proposal::0234-verification-workflow`. The authored proposal is
`under_review`, with an empty queue status: it is not a derived queue item.
The request is `proposal_linked`, not an executed refinement. Existing helper
functions registered the nodes; no executor or workflow was invoked.
The older lineage vocabulary labels authored document references as
`runtime_artifact`; that label does not establish execution evidence.

Do not pass operator-request.json to the refinement CLI. It records the request
to prepare this proposal, not permission to refine a canonical node.

## Source-grounded findings

Three read-only investigations examined the existing Supervisor/CLI seams,
the contract and the ExamCalc producer. Parent inspection confirmed:

- C2c collects retained observations and intentionally returns CLI exit 0 on
  diagnostic report generation; workflow success needs a separate predicate.
- Hash/revision checks do not establish that a journal came from a new process.
- A missing terminal execution record must remain incomplete.
- Existing delivery workflow artifacts describe review readiness, not a
  general execution engine. The planned supervisor package extraction is not
  an already implemented operation API.

The reviewed SpecGraph source is `002eb0691b39ea2ccdcc50d0c5c31fc84022e3bf`.
ExamCalc local evidence is recorded in the proposal with its source revisions;
raw journals and project-private files remain local. New workflow behavior was
not tested or implemented in this proposal.

## Next task and workspace

Review the fixed profile and five bypass controls, then implement the narrow
operation and façade in a separate PR. Preserve 0224/0226 contracts and keep
0225 admission separate. The first profile has no general DAG engine or resume.

Preparation uses primary checkout branch `codex/0234-verification-workflow`;
no extra worktree was created. The PR is the durable handoff. After publication,
read-only review can inspect the branch commit without changing the checkout;
no service or notebook depends on this branch.
