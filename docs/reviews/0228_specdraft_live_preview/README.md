# 0228: conversation → notes → proposed live preview

This is the review package for [proposal 0228](../../proposals/0228_specdraft_live_preview.md).
The [source draft](../../archive/proposal_sources/0228_specdraft_live_preview.md)
retains the original request and the explicit direction to use dogfooding.

## What actually happened

1. Resumed the existing local sketch with `read_notes`.
2. Used `update_notes` to retain the SpecDraft naming, sidecar idea and dogfooding
   direction as source-attributed notes. No approval operation was added.
3. Exported only the six-node source branch at
   `e255d0f2dce94685a353da78669b0886` into [source-notes.json](source-notes.json).
4. Prepared one proposal and [specification draft](specdraft.md), with four
   declared proposal obligations and six addressable acceptance cases.
5. Added the proposal/draft handoff back into the live sketch using the same
   notes tool; [handoff.json](handoff.json) retains that actual update receipt.
6. Implemented the bounded local read-only prototype and observed its updates
   through the real notes tool. [verification.json](verification.json) records
   test/browser coverage, source revisions and unverified acceptance parts.

The live sketch is still local and Git-ignored at
`conversation_memory/sketches/hypercode-conversation-poc/`. Its handoff revision
is `b7244c6348c64bfb8ec08f3ba630d9d3`; the earlier captured source revision stays
fixed. Note labels/details are agent summaries; quotations retain their source
speaker and original wording. Incident links can point to omitted nodes.

## Proposed scope to review

The person talks and sees the saved sketch as a live mind map in a local browser
page. The agent writes through the existing notes tools. The sidecar reads one
selected workspace and exposes the current snapshot and a viewer page.

The contract covers initial rendering, committed updates, identity/source
fidelity, read-only scope, visible read-error recovery and deferred history.
Two-second foreground refresh for a 100-node fixture, loopback binding and the
source inspector are agent-proposed details. The operator's scope is the local
live visualization, with version controls explicitly left for later.

SG-SPEC-0007/0050/0051 provide the existing semantic and promotion boundaries.
The concrete HTTP/UI behavior is kept in this realization draft rather than
added to implementation-agnostic core nodes. No new canonical kind is proposed.

[packet.json](packet.json) binds the source, proposal, declaration, draft and
handoff bytes. Its state is `review_pending`; it is preparation, not an actual
promotion decision or writer authorization. The four draft obligations have
individual engineering dispositions linking mechanical adapters or named display
specifications to their callers. Those dispositions do not approve semantics
or admit evidence.

## Current boundary and next step

The sidecar is a technical prototype. No canonical subject allocation, accepted
SpecDraft, canonical materialization or evidence admission is supplied here.
One nine-node foreground update was observed at 588 ms; the target 100-node
profile and browser error recovery remain unverified. Narrow screens need zoom
to read the full overview.

Review the [specification draft](specdraft.md) together with its prototype and
bounded observations. The next technical slice is the 100-node profile and
browser failure/recovery; acceptance/publication retain their stated scope.

## Review correction: relation direction

PR #804's inspector correction preserves the saved source, label and target
when selecting either endpoint, including endpoints outside the selected branch
and self-links. Run `node --test tests/specdraft_preview_inspector.cjs` (Node 24
in CI). The test executes the shipped app and click handlers against a minimal
DOM double; it does not establish browser layout or accessibility conformance.
The original `verification.json` retains the original prototype observations
and code hashes. The separate `review-fix-verification.json` binds this later
correction and its focused checks; earlier browser samples are not re-attested.
