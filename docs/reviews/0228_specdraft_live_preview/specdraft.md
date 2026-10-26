# SpecDraft candidate: live notes preview

Status: `review_pending`; prepared by the agent, not accepted or canonical.
Requirement candidate: `req.specdraft.live-preview`.
Source proposal: [0228](../../proposals/0228_specdraft_live_preview.md).
Source sketch revision: `e255d0f2dce94685a353da78669b0886`.
Source nodes: `specdraft_sidecar`, `sidecar_browser`, `sidecar_live_updates`,
`sidecar_history_later`, `sidecar_dogfooding` in [source-notes.json](source-notes.json).

This Markdown is a review surface for a specification draft, not a new serialized
promotion exchange or canonical subject-storage schema. The proposed candidate
ID is a review address; no namespace or subject origin has been allocated.

## Requirement

During a conversation, the person can observe the latest saved note sketch as
a local browser mind map that updates when the agent saves a new revision,
retaining the notes' structure and provenance and their draft status.

The user supplies the local sidecar/live-map goal and defers version controls.
Source inspection, read-only behavior, loopback binding, error recovery and the
exact latency target below are disclosed agent design choices.

## Addressable acceptance criteria

### SDPV-01 — selected sketch

Given one explicitly selected local notes workspace, starting the sidecar
produces a loopback URL. A browser at that URL shows the current hierarchy and
labels as a navigable mind map, plus the saved revision and draft designation.
An empty valid sketch has a recognizable empty state.

Maps to `SD-LIVE-VIEW` and `SD-LIVE-FIDELITY`.

### SDPV-02 — committed updates

With the page in the foreground and a sketch of up to 100 nodes, a successful
`update_notes` revision is reflected within two seconds without page reload.
The displayed revision and node content come from one complete saved snapshot.
Adding, renaming and reparenting through the existing tool are covered.

Maps to `SD-LIVE-REFRESH`; two seconds and the fixture size are proposed bounds,
not claims extracted verbatim from the operator.

### SDPV-03 — identity, text and provenance

Selecting a note shows its ID, detail and attributed quotations. Rename or
reparent operations preserve that ID in the display. Hierarchy is distinguished
from other named links. Note labels/details/quotations are rendered as text,
including HTML-like content; they do not execute scripts or become canonical
claims by being shown.

Maps to `SD-LIVE-FIDELITY`.

### SDPV-04 — observation boundary

Serving or viewing notes leaves notebook files, revision history and recorded
approvals unchanged. The HTTP surface is read-only, exposes only the startup-
selected workspace, and does not offer edit, approve or promotion operations.
It binds to loopback. Arbitrary filesystem paths cannot be selected over HTTP.

Maps to `SD-LIVE-SCOPE`; these are proposed realization constraints.

### SDPV-05 — visible stale state and recovery

After a good display, a temporary read failure keeps the last good content and
its revision, visibly marks it stale/unavailable, and clears that warning after
the next successful read. Before any successful snapshot, a failure has an
explicit unavailable state. A failed read is not reported as an empty notebook.

Maps to `SD-LIVE-REFRESH` and `SD-LIVE-FIDELITY`; this is an agent-proposed
failure contract for a trustworthy live view.

### SDPV-06 — deferred capabilities

The first UI has no checkpoint browser, rollback, multi-user editing or canonical
promotion. The existing revision storage remains available to note tools but
the viewer selects only the current saved revision. Opening the local URL in
an agent's browser panel is ordinary page consumption; a custom Codex/Claude
integration is not part of the contract or a claimed verified capability.

Maps to `SD-LIVE-SCOPE` and the operator's explicit history deferral.

## Proposed implementation and verification

Reuse `read_notes` as the snapshot adapter. A thin local HTTP boundary serves
one page and the current snapshot; an offline browser renderer owns layout and
interaction. Keep HTTP/file handling apart from display-state decisions. Review
stable last-good/current/error decisions for named SpecificationCore policies
when implementing them; this preparation introduces no runtime policy code.

Focused server/state tests and a real browser observation now cover initial
view, mutation through the existing tool, new revision display and source
inspection; model tests cover stale/unavailable recovery. See
[verification.json](verification.json) for exact limits. The 100-node browser
profile, browser-level error recovery and hostile-text rendering in a browser
remain unverified. This is technical prototype evidence; acceptance of this
specification draft and canonical materialization remain pending.
