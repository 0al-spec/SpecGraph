# Pilot follow-ups and return points

Proposal 0229 preserves a bounded inventory so work can resume through the
existing supervisor without reconstructing the conversation.

Its seven local handles are CN-PUBLISH, TESTS-VERIFIED, DELIVERY-TRUST,
ONTOLOGY-LINKS, CAPTURE-PROVENANCE, SPECDRAFT-PREVIEW and POC-LESSONS.
Each names its source, reported gap, return trigger, next bounded step and
closure evidence. These handles are not new canonical kinds or obligations.

The inventory remains `deferred_until_canonicalized`. Build the existing
`proposal_runtime_index`, `graph_backlog_projection` and `graph_next_moves`
through `make proposal-runtime-index`, `make backlog` and `make next-move`.
Find proposal `0229`, follow its retained source and select one handle. The
generic `canonicalization` next-gap value is a review/re-entry pointer, not
publication permission or a statement that all seven items need canonicalization.
Next Moves remains advisory and may prioritize unrelated work.

`make metric-signals` rebuilds the existing `metric_signal_index`. This is a
proxy observation; it does not measure these handles individually or implement
new debt metrics. Backlog counts retain one proposal, not seven canonical
obligations. Missing optional evidence, planning work and an unverified
architectural hypothesis must remain distinguishable. Document markers do not
prove semantic closure. No S/U, SIB, threshold or merge-policy change is made.

Provider-reported delivery remains separate from trusted admission. Current
`runtime_verified_v1` verification does not imply receipt issuance for the
delivery pilot; `tests_verified` remains unavailable pending its existing plan.
Preserving a publication task does not approve its writer or materialize origins.

See `docs/proposals/0229_pilot_followup_reentry.md`, its archived source and
`docs/evidence/0229_pilot_followup_reentry.json` for the bounded verification.
