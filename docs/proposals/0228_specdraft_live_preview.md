# SpecDraft Live Preview

## Status

Draft proposal; bounded technical pilot, specification review pending.
Runtime realization is `synchronous_runtime_slice`. A local read-only prototype
and focused tests are implemented. Bounded observations are retained separately;
SpecDraft acceptance and canonical publication remain pending.

## Intent and source

During a human-agent conversation, the person sees a readable mind map of the
saved SpecDraft notes updating alongside the discussion. The agent continues
using existing note operations; the visualization makes its understanding
visible early enough for the person to correct it.

- [Original request and scope](../archive/proposal_sources/0228_specdraft_live_preview.md)
- [Tool-captured source branch](../reviews/0228_specdraft_live_preview/source-notes.json)
- [Prepared specification draft](../reviews/0228_specdraft_live_preview/specdraft.md)
- [Review packet](../reviews/0228_specdraft_live_preview/packet.json)
- [Technical observations](../reviews/0228_specdraft_live_preview/verification.json)
- [Existing capture implementation](../conversation_notes.md)
- [Proposed SpecDraft layer name](https://github.com/0al-spec/SpecGraph/pull/803)

This is a realization follow-up to proposal 0045. Its original, hash-bound
proposal and review inputs stay unchanged.

## Existing specifications and intended placement

SG-SPEC-0007 governs the mediation boundary and original intent lineage.
SG-SPEC-0050 governs pre-spec meanings; SG-SPEC-0051 governs promotion and review.
Those nodes deliberately exclude concrete UI/storage details. This proposal
therefore prepares an implementation contract under `tools/`, with their
existing boundaries as constraints. It does not add HTTP or browser behavior
to the frozen core specifications or introduce another semantic kind.

## Bounded first slice

The viewer serves one explicitly selected local sketch as a mind map in a
browser tab. It uses existing IDs, hierarchy, labels, details, quotations and
links. Selecting a node exposes its detail and source attribution. The view
identifies the sketch as a draft and shows which saved revision is displayed.

The agent can add, rename or regroup notes through existing tools while the
page is open. A new committed revision updates the view without a manual page
reload. A temporary read failure is visible and does not masquerade as an empty
sketch or erase the last good display.

The viewer has no editing, approval, promotion, history-selection or rollback
controls in this slice. Existing storage history is preserved without a new
versioning subsystem. Agent-specific plugins, remote hosting and multi-user
collaboration are outside this first scope.

## Proposed architecture

```text
Human conversation → agent → update_notes → committed local snapshot
                                                ↓
                                           read_notes
                                                ↓
                                     local read-only sidecar
                                                ↓
                                   browser mind map / preview
```

The source remains the existing NotesStore. The sidecar selects its workspace
at startup and consumes `read_notes(..., history_limit=0)`; it does not parse a
second copy of Hypercode or write to the notebook.

The proposed minimal HTTP surface is `GET /` for the local page and
`GET /api/notes` for the current snapshot. Bind to loopback, select the port at
startup and report the resulting URL. The request cannot choose arbitrary disk
paths. Render note text as text rather than executable HTML. The browser can
poll for a changed revision; SSE and a separate filesystem-watcher dependency
are not required by the contract.

The two-second foreground update target, source inspector, last-good recovery
and read-only/loopback choices are agent-proposed details for review. The
operator requested a local, live visualization and deferred version controls.

## Acceptance and evidence plan

The four declared draft obligations are `SD-LIVE-VIEW`, `SD-LIVE-REFRESH`,
`SD-LIVE-FIDELITY` and `SD-LIVE-SCOPE`; their declarations are in the adjacent
`.intent.yaml` file. They remain separate from canonical Intent Atoms.

The [specification draft](../reviews/0228_specdraft_live_preview/specdraft.md)
addresses each proposed acceptance case and its source obligation:

| Case | Future verification |
| --- | --- |
| `SDPV-01` Initial view | Start with a selected sketch; inspect hierarchy, labels and displayed revision in a real browser. |
| `SDPV-02` Live update | Change notes through `update_notes`; observe the new revision/content within two seconds in a foreground page, without reload. |
| `SDPV-03` Identity and source | Rename/reparent a stable ID and inspect its retained detail and quotation; note text remains inert. |
| `SDPV-04` Read-only scope | Compare notebook state before/after viewing and reject mutation methods; bind only the selected local workspace. |
| `SDPV-05` Read failure | Make a snapshot temporarily unreadable; retain the last good view with a visible warning and recover automatically. |
| `SDPV-06` Deferred history | Show only the current revision, without selecting/restoring old checkpoints or promoting notes. |

These cases define the verification plan. The linked observation records which
parts were exercised; it does not report all six cases fully verified. A real
foreground update on nine notes took 588 ms in one sample. The specified
100-node profile and browser-level failure recovery remain unverified. Existing
note-storage tests and focused HTTP/state tests passed; none of this admits
evidence against a canonical Requirement. A render alone does not prove refresh.

## Local prototype

```sh
make specdraft-preview SPECDRAFT_PREVIEW_WORKSPACE=conversation_memory/sketches/hypercode-conversation-poc SPECDRAFT_PREVIEW_ARGS='--node-id specdraft_layer'
```

The command prints a loopback URL; port 0 selects a free port. Open that URL in
a browser or a supported local-page panel. The implementation is under
`tools/specdraft_preview/`; its immutable display facts and named specifications
classify current, empty, stale and unavailable observations. Losing a previously
saved head cannot silently become an empty notebook. HTTP and filesystem work
remain in adapters. Canonical state is unaffected.

## Dogfooding state and next action

```text
source captured → notes saved → proposal + SpecDraft prepared → technical pilot observed → human review pending
```

No whole-sketch approval, SpecDraft acceptance, canonical subject allocation or
writer permission is inferred from the request to use this process.
`canonical_mutations_allowed: false`; `implementation_started: true`.

Review this one contract and prototype, especially the proposed two-second
refresh target and read-only local scope. The next bounded validation is the
100-node foreground profile and browser failure/recovery; formal acceptance
and any canonical materialization remain their existing separate decisions.
