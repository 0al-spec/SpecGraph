# SpecDraft Live Preview Proposal

Proposal 0228 prepares a local live mind map of conversational notes through
SpecGraph's own dogfooding path: source quotation, saved note branch, proposal,
specification draft and review. Runtime is `synchronous_runtime_slice`: a bounded
local prototype is implemented while specification acceptance and canonical
publication remain pending.

## Proposed first slice

The person sees the selected saved sketch in a browser while the agent keeps
writing through `update_notes`. A read-only local sidecar consumes `read_notes`
snapshots and updates the page when the saved revision changes. Existing note
IDs, hierarchy, text and source quotations remain attributable draft material.

The four declared proposal obligations are `SD-LIVE-VIEW`, `SD-LIVE-REFRESH`,
`SD-LIVE-FIDELITY` and `SD-LIVE-SCOPE`. The specification draft addresses them
through six cases, `SDPV-01` through `SDPV-06`: selected view, committed refresh,
identity/source fidelity, read-only scope, visible failure/recovery and deferred
history controls. A two-second foreground refresh target, loopback binding and
source inspection are proposed engineering details for human review.

History selection, rollback, editing and canonical promotion are outside the
first viewer scope. Existing note version storage stays unchanged. A browser
panel is an ordinary local-page consumer; custom agent integration is not
implemented or verified by this proposal.

## Trace and review

`docs/reviews/0228_specdraft_live_preview/source-notes.json` retains the selected
branch at revision `e255d0f2dce94685a353da78669b0886`. Original quotations are
distinct from agent summaries; no whole-sketch approval is recorded.

`docs/proposals/0228_specdraft_live_preview.md` and its `.intent.yaml` declaration
lead to `docs/reviews/0228_specdraft_live_preview/specdraft.md` and the pending
review packet. SG-SPEC-0007, SG-SPEC-0050 and SG-SPEC-0051 provide existing
semantic/governance boundaries; concrete UI details are not added to those
core specifications. No canonical mutation, evidence admission or publication
permission is supplied by this preparation.

## Technical observation

`make specdraft-preview` starts a loopback sidecar. Set
`SPECDRAFT_PREVIEW_WORKSPACE` to the saved sketch and optionally pass
`SPECDRAFT_PREVIEW_ARGS='--node-id specdraft_layer'`. The sidecar consumes the
existing notes API; named Specifications classify current, empty, stale and
unavailable display state with no canonical authority. Their contexts are
immutable and each new predicate has its own module.

The retained `verification.json` records 52 focused tests passed and one optional
Hypercode CLI compatibility check skipped. A real nine-node foreground update
was rendered after 588 ms in one sample; source inspection and initial/narrow
layouts were observed. The 100-node browser profile, browser error recovery and
hostile-text browser execution remain unverified. Screenshots stay local.

The next step is review of the contract/prototype, then bounded validation of
remaining cases. See <doc:ConversationNotes> for the existing note tools.
## Inspector relation fidelity

Selecting either endpoint retains the saved relation as source — label → target.
Endpoints outside the selected branch retain their IDs and an explicit outside
marker. `node --test tests/specdraft_preview_inspector.cjs` executes the shipped
app with a minimal DOM double; CI runs these four regressions on Node 24. These
checks cover inspector text, not browser layout or accessibility conformance.
