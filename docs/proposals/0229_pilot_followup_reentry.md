# Pilot Follow-up Inventory and Supervisor Re-entry

RFC: SG-RFC-0229

## Status and purpose

This is a backlog index only. Runtime realization is
`deferred_until_canonicalized`: no debt evaluator, new metric profile, new
canonical kind or automatic scheduler is implemented. The completed slice is
preservation of known follow-ups and verification that the existing supervisor
can rediscover this proposal. Review determines any later implementation scope.

The purpose is to resume a bounded task without reconstructing the conversation.
A missing optional improvement is not automatically an unfulfilled obligation.

Source: [human requests and supplied weekly feedback](../archive/proposal_sources/0229_pilot_followup_reentry.md).

## Retained inventory

IDs below are local return handles, not canonical subjects. Reported states are
intake observations; revalidate them before acting. Dates refer to this inventory
capture on 26 October 2026, not an inferred date when a problem first appeared.

### CN-PUBLISH — finish the canonical capture pilot

- Source/target: proposal [0045](0045_conversation_memory_exploration_vault.md),
  existing [CN-CAPTURE review](../reviews/0045_cn_capture/README.md), and
  [#800](https://github.com/0al-spec/SpecGraph/pull/800) →
  [#801](https://github.com/0al-spec/SpecGraph/pull/801) →
  [#802](https://github.com/0al-spec/SpecGraph/pull/802).
- Observed gap: final publication remains pending; a prepared package and
  SpecDraft agreement do not create production origins or writer permission.
- Return trigger: review/publication work resumes, or a consumer needs canonical
  Requirement/Intent addresses. First re-read the current #802 packet and source.
- Next bounded step: settle the exact publication package and its required
  decisions, then perform publication only when authorized.
- Closure: real selected-workspace subjects, origins and derivation links are
  readable and match the accepted package. A merge or disposable-clone preview
  alone cannot close this item. Until then, only canonical publication is blocked.

### TESTS-VERIFIED — retain the stronger test-evidence plan

- Source/target: [0224](0224_compositional_test_context_and_evidence_binding.md),
  [0225](0225_tests_verified_evidence_admission_plan.md) and
  [current admission semantics](../evidence_claim_admission.md).
- Observed gap: `tests_verified` remains
  `unknown / evidence_evaluator_unavailable`; 0225 is a planning contract.
- Return trigger: an accepted feature needs assertion-level test admission.
- Next bounded step: review one runner/obligation binding and its upstream
  prerequisites under 0225. Do not duplicate that plan here.
- Closure: a reviewed bounded evaluator and fresh target-bound evidence support
  the chosen claim. Ordinary passing CI does not establish it. This item blocks
  the stronger claim, not provider-reported publication signals.

### DELIVERY-TRUST — choose the required confirmation boundary

- Source/target: [publication pilot](../publication_delivery_pilot.md),
  SG-SPEC-0071 and [0047](0047_evidence_backed_build_protocol.md).
- Observed gap: delivery observations are `provider_reported`, admission
  `not_evaluated`. Existing `runtime_verified_v1` verification is narrower than
  receipt issuance and its use by this delivery slice.
- Return trigger: a consumer requests trusted delivery/runtime admission, or
  the release scope changes beyond the current pilot.
- Next bounded step: explicitly select the MVP confirmation level. If stronger
  evidence is needed, reuse FeaturePassport issuance/verification boundaries
  and name one bounded claim, authority and target.
- Closure: either record the accepted limited MVP scope and its revisit trigger,
  or supply the chosen fresh admitted evidence. These are different outcomes;
  deferral never becomes a claim that signed evidence exists.

### ONTOLOGY-LINKS — investigate the integration hypothesis

- Source/target: SG-SPEC-0020,
  [0119](0119_ontology_canonicalization_backlog.md), and
  [0226](0226_traceability_evidence_providers_and_svc.md).
- Observed gap: the report questions integration and possible competing relation
  semantics. Absence of a recent Ontology commit does not prove either defect.
- Return trigger: intent/evidence relation vocabulary or its consumer changes.
- Next bounded step: compare one real relation path with the pinned Ontology
  package and current binding. Record whether any disagreement exists.
- Closure: the bounded path either resolves through existing contracts, or an
  identified mismatch has its own reviewed amendment. An unchanged repository
  date alone neither opens nor closes an architectural defect.

### CAPTURE-PROVENANCE — keep the source limitation visible

- Source/target: [conversation notes](../conversation_notes.md) and CN-PUBLISH.
- Observed gap: existing source excerpts have local attribution without
  independently established human identity or original message timestamp.
- Return trigger: import/export, cross-session citation, or a consumer requiring
  stronger provenance than the pilot currently supplies.
- Next bounded step: decide which native source fields are actually available
  and required. Preserve unknown fields as unknown and retain original quotes.
- Closure: document the bounded source guarantee and, if adopted, exercise the
  stronger capture path on fresh messages. Never retroactively attest old notes.
  This limitation does not prevent ordinary local sketch capture.

### SPECDRAFT-PREVIEW — finish review and the bounded UI observation

- Source/target: [#803](https://github.com/0al-spec/SpecGraph/pull/803) and
  [#804](https://github.com/0al-spec/SpecGraph/pull/804), proposal 0228.
- Initial observation: the technical prototype was observed on nine nodes, with
  a single 588 ms save-to-render sample. The retained original packet describes
  that earlier source snapshot and is unchanged.
- Follow-up on 26 October 2026: a separate [browser observation](../evidence/specdraft_preview_browser_20261026.json)
  against merged revision `5b50da3f` exercised a synthetic notebook up to 100
  nodes. Add, rename and reparent reached the DOM after 400, 440 and 16 ms,
  retaining selection and identity. Selecting either endpoint preserved named
  link direction. A controlled read failure kept the saved view and warning;
  restoring the fixture returned to Live. These are single samples for ten
  chains, not a distribution, arbitrary-topology guarantee or first-paint test.
- Remaining gap: human SpecDraft acceptance, hostile-text browser behavior,
  initial unavailable state and network/process recovery remain unverified.
  At 31 percent overview zoom, detailed reading needs zoom or the inspector.
- Return trigger: resume preview review or claim the proposed update target.
- Next bounded step: use the original packet and this separate observation for
  human review; select a remaining browser case only if needed for the chosen
  MVP. Keep the live ignored notebook intact across worktrees.
- Closure: resolve the bounded review/acceptance and record the chosen UI cases.
  Do not equate the nine-node sample with the full acceptance profile.

### POC-LESSONS — transfer useful intent-capture ideas

- Source/target: the human PoC clarification in the archived source and proposal
  0045. The private local experiment is not a required dependency.
- Observed gap: proposed lessons have not been mapped against existing notes:
  speech-act hints, source/interpretation separation, uncertainty and avoiding
  duplicate notes during refinement.
- Return trigger: the next conversational-capture improvement pilot.
- Next bounded step: choose one existing-note refinement example, identify the
  actual missing behavior, and prepare a small reviewed change if needed.
- Closure: record the useful lesson and one bounded observation, or explain
  that existing behavior already covers it. Direct pipeline integration is not
  the default next step and is not authorized by this inventory.

## Return through the existing supervisor

From the selected checkout with its configured Python environment:

```sh
make proposal-runtime-index
make backlog
make next-move
make metric-signals
```

Find proposal `0229` in `runs/proposal_runtime_index.json` and the corresponding
`domain: proposals` row in `runs/graph_backlog_projection.json`. Follow this
inventory to one local handle and re-read its source/current state. The existing
`deferred_until_canonicalized` posture produces `next_gap: canonicalization`;
that generic label is a review/re-entry pointer, not authorization to publish
all listed work or proof that every item needs canonicalization. `Next Moves`
may recommend more urgent unrelated work; discoverability does not imply top
priority or automatic execution. No LLM refinement or loop run is necessary.

## Metric observation and boundaries

Existing proposal-runtime and backlog summaries expose this unresolved proposal
as one retained item. They do not count the seven inventory handles as seven
canonical obligations or seven verified defects. The source and runtime markers
measure document presence, not semantic fulfillment.

`runs/metric_signal_index.json` remains the existing proxy-profile observation.
The current metric system does not consume these seven handles individually.
Before a future per-item age, closure or evidence metric is introduced, its
denominator must name the selected handles, distinguish accepted obligations
from plans/limitations/hypotheses, and preserve source revision and freshness.
An unavailable evaluator is unknown, not zero evidence or a passed claim.
This slice does not change S/U, SIB formulas, thresholds or merge policy.

## Completion of this preservation slice

- The source and seven return handles are tracked, with triggers and closure
  conditions. No new approval or accepted risk is inferred from capture.
- Proposal runtime, promotion and backlog outputs resolve this proposal.
- Existing metric output can be rebuilt without a new evaluator or inference.
- A curated verification summary records what was actually observed.

The follow-ups remain open after this informational slice is complete. Resolving
or deferring one handle later should update its source record and this index;
do not delete its history or mark every item complete when this PR merges.
