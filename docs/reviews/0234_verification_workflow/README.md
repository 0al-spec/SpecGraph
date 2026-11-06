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

The first pure-core slice is implemented in `tools/verification_workflow/`.
The next slice supplies actual execution and persistence adapters, then connects
the native CLI and explicit Supervisor operation. Preserve 0224/0226 contracts
and keep 0225 admission separate. The first profile has no general DAG engine
or resume.

Preparation uses primary checkout branch `codex/0234-verification-workflow`;
no extra worktree was created. The PR is the durable handoff. After publication,
read-only review can inspect the branch commit without changing the checkout;
no service or notebook depends on this branch.

## First implementation: consistency core

The operator reminded the agent, “Не забывай про FeaturePassport”, and replied
“Думаю, можно приступать” to the proposed passport-through-workflow design.
These are agent-attributed conversation excerpts, not authenticated receipts.
The preceding agent proposal was to carry a pinned FeaturePassport through the
workflow and check observations against its feature and criteria, while keeping
admission separate. The reply authorizes starting implementation; it does not
adopt a canonical specification or approve the entire conversation sketch.
The local SpecDraft `conversation_memory/sketches/verification-workflow` retains
both speakers and the response link at revision
`aef9e59d13c6467fa7722a540456c355` (five revisions, history verified complete).
That notebook follows this checkout's existing Git-ignore rule. The selected
excerpts and scope are preserved here in tracked documentation.

The core provides immutable request, scope, stage and result records. Separate
SpecificationCore policies check the fixed mandatory topology, passport-bound
inventory, current-run record linkage, C2c collection compatibility, lifecycle
and verification verdict. Parsing, process execution and persistence remain
adapter responsibilities. C2c retains ownership of criterion interpretation.

FeaturePassport ID, feature ID, version, file hash, validator/schema pins and
criterion/contract/binding references are carried in the scope. Expected
measurements precede observation. The result keeps the complete inventory and
distinguishes `workflow_outcome` from `verification_outcome`; a normally
finished negative test remains `completed/failed`.

`tests/test_verification_workflow.py` has 65 passing cases, including missing or
disconnected execution, foreign-run records, source/passport drift, empty or
incomplete inventory, nonzero/aborted producers and inconsistent observations.
Independent review found two consistency defects: selected step statuses could
disagree with aggregate statuses, and nested conflicts/retry state could be
lost. Regression tests reproduced the failures before correction. Re-review
confirmed all four original negative probes now return `failed/incomplete`,
while passing and consistently failing controls retain their expected results.
Root cause: treating a derived C2c row as sufficient proof of the consistency of
its nested facts. Prevention: explicit nested-fact checks plus regressions.

These tests supply facts to a pure core. They do not establish that a process
ran or that file bytes were independently checked. The future adapter must
allocate unique runs, validate source/passport bytes, execute tests, establish
output custody, check mutation and atomically persist completion. No CLI or
Supervisor mode is activated, and no installed ExamCalc run is claimed here.
Admission remains `not_evaluated`, provenance `producer_declared`, receipt null.
The registry's `deferred_until_canonicalized` posture refers to activation;
the preparation code is now available for the next bounded slice.

Implementation workspace: primary checkout branch
`codex/0234-verification-core`, dependent on proposal PR #884. No extra worktree
was allocated. The historical proposal registration and its source hashes are
unchanged; this implementation does not manufacture an applied Supervisor run.
