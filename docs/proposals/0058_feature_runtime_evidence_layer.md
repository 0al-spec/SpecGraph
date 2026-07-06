# Feature Runtime Evidence Layer

## Status

Draft proposal

## Source Material

This proposal captures the operator request to prove that a SpecGraph request or
feature reached production and produced user-visible runtime evidence.

Source draft:

- `docs/archive/proposal_sources/0058_feature_runtime_evidence_layer.md`

External Feature Passport authority:

- Feature Passport repository: <https://github.com/0al-spec/FeaturePassport>
- Feature Passport RFC:
  <https://github.com/0al-spec/FeaturePassport/blob/724e51c47fee89de1fcd4a3857ebbcea9bf1fa19/docs/proposals/0001_specgraph_feature_runtime_evidence_layer.md>
- RFC id/version: `FP-RFC-0001` / `0.2.0`
- Adoption follow-up: proposal `0203` records the bounded SpecGraph contract
  update required by FeaturePassport PR `#3`.

External standards and transport anchors remain non-authoritative inputs:

- GitHub Artifact Attestations:
  <https://docs.github.com/en/actions/security-for-github-actions/using-artifact-attestations/using-artifact-attestations-to-establish-provenance-for-builds>
- SLSA provenance:
  <https://slsa.dev/spec/v1.1/provenance>
- Sigstore/Cosign verification:
  <https://docs.sigstore.dev/cosign/verifying/verify/>
- OpenTelemetry resource semantic conventions:
  <https://opentelemetry.io/docs/specs/semconv/resource/>
- OpenTelemetry deployment attributes:
  <https://opentelemetry.io/docs/specs/semconv/registry/attributes/deployment/>
- OpenFeature hooks:
  <https://openfeature.dev/specification/sections/hooks>

## Context

SpecGraph already tracks specification state, proposals, trace contracts,
evidence chains, implementation work, release-oriented derived surfaces, and
external consumer handoffs. That is enough to answer:

```text
What did the graph say should exist?
Which specs, proposals, tools, tests, and runtime artifacts claim to embody it?
```

It does not yet answer the stronger product question:

```text
Did this user request become a shipped feature that real production users
actually saw, executed, and completed?
```

The Feature Passport repository now owns the architecture-level contract for
Feature Passport, evidence claims, observations, attestations, receipts, evidence
levels, canonical event envelopes, and honesty boundaries. SpecGraph should not
copy that contract. SpecGraph should consume it, reference it, and project its
evidence into graph-native surfaces.

`FP-RFC-0001` version `0.2.0` tightens the first downstream contract boundary:
receipt hashes cover receipt content and signature metadata, each chain declares
its scope, ladder levels are monotonic only across applicable levels, only
successful observations satisfy levels, aggregate claims require a separate
claim-evaluation step, and Feature Passport lifecycle/version pinning is
explicit. SpecGraph derived surfaces must preserve those constraints rather than
reconstructing earlier `0.1.0` semantics locally.

## Problem

Current engineering signals often stop too early:

- a commit exists;
- a pull request is merged;
- an artifact was built;
- a release was created;
- analytics reports a page view or flag exposure.

None of those alone proves that a specific SpecGraph request produced a
specific user-visible outcome in production.

SpecGraph needs a first-class integration point for Feature Passport evidence.
Without it, operators and viewers may confuse weak signals with strong proof:

- `merged` is not the same as `built`;
- `built` is not the same as `deployed`;
- `deployed` is not the same as `seen by runtime`;
- `flag evaluated` is not the same as `feature code path executed`;
- `code path executed` is not always the same as `intended outcome completed`;
- client-side telemetry is not adversarially perfect proof.

The graph should expose those distinctions explicitly while delegating the
canonical feature-evidence vocabulary to Feature Passport.

## Goals

- Adopt `FP-RFC-0001` as the external authority for Feature Passport evidence
  terminology and contract shape.
- Link SpecGraph request/spec/proposal identifiers to Feature Passport
  `request_id` and `feature_id`.
- Define SpecGraph-owned derived surfaces for imported Feature Passport evidence.
- Preserve evidence strength levels from the Feature Passport RFC without
  redefining them locally.
- Allow supply-chain provenance systems to satisfy build/release evidence
  through Feature Passport-compatible adapters.
- Allow telemetry systems to transport runtime observations without becoming
  graph authority.
- Treat signed or hash-linked receipts as the trusted ingestion output.
- Define viewer-facing evidence ladder semantics for SpecSpace or other Graph
  Operator Surfaces.
- Preserve honest limits for client-side telemetry and hostile endpoints.

## Non-Goals

- Redefining the Feature Passport RFC inside SpecGraph.
- Duplicating the Feature Passport schema, event envelope, or receipt schema.
- Implementing a telemetry SDK.
- Implementing an evidence ingestion backend.
- Implementing a database, queue, or ledger.
- Implementing SpecSpace UI.
- Requiring one vendor such as Datadog, Sentry, LaunchDarkly, OpenFeature, or
  OpenTelemetry.
- Requiring cryptographic certainty from client-side events alone.
- Replacing trace contracts, evidence-plane contracts, or implementation work.
- Turning metrics or adoption numbers into policy gates automatically.
- Creating user-level surveillance, PII collection, or behavioral scoring.

## Core Proposal

Introduce **Feature Runtime Evidence Layer** in SpecGraph as an integration and
projection layer above implementation work:

```text
SpecGraph request/spec/proposal
  -> Feature Passport reference
  -> implementation linkage
  -> build/release evidence projection
  -> runtime observation/receipt projection
  -> viewer evidence ladder
```

SpecGraph should report the strongest Feature Passport evidence level currently
observed for each linked request or feature. It should not claim that a feature
is "done" merely because code exists.

## External Contract Boundary

`FP-RFC-0001` is the source of truth for:

- `Feature Passport`;
- `EvidenceClaim`;
- `Observation`;
- `Attestation`;
- `EvidenceReceipt`;
- `EvidenceChain`;
- evidence levels `L0` through `L8`;
- canonical event envelope shape;
- receipt field contract;
- honesty and trust boundaries;
- absence semantics;
- vendor compatibility model.

SpecGraph is responsible for:

- storing or referencing Feature Passport identities;
- linking graph nodes to `request_id` and `feature_id`;
- building read-only derived indexes from available passports and receipts;
- surfacing gaps when required evidence is missing;
- projecting the evidence ladder to viewer-facing artifacts;
- preventing weak observations from being displayed as strong proof.

## Evidence Level Adoption

SpecGraph should display and query the Feature Passport evidence ladder using the
external RFC labels:

```text
L0 Specified
L1 Implemented
L2 Built
L3 Released
L4 Runtime Seen
L5 Feature Exposed
L6 Code Path Executed
L7 Effect Committed
L8 Outcome Completed
```

The phrases should keep their Feature Passport meaning:

- "commit reached production" requires at least `L4`.
- "feature worked for users" requires `L7` or `L8`.

SpecGraph may compute summaries, gaps, and viewer projections from these
levels, but it must not locally redefine the level semantics.

## Proposed SpecGraph Artifacts

Future bounded implementation slices may introduce these derived artifacts:

```text
runs/feature_passport_index.json
runs/feature_evidence_index.json
runs/feature_evidence_ladder.json
```

Suggested responsibilities:

- `feature_passport_index`: known passports, source repository, RFC version,
  linked SpecGraph request/spec/proposal IDs, and import validity.
- `feature_evidence_index`: observed attestations, observations, receipts, and
  evidence gaps grouped by `feature_id` and `request_id`.
- `feature_evidence_ladder`: viewer-facing projection of current evidence level,
  missing requirements, strongest proof, and honesty boundary notes.

These artifacts should be derived/read-only. They must not mutate canonical
specs, proposals, or product workspaces automatically.

## Viewer Surface

Viewers should show an evidence ladder instead of a single boolean:

```text
Request: SG-REQ-2026-001
Feature: feature.invoice.smart_summary

L0 Specified            yes
L1 Implemented          yes, PR/commit linked
L2 Built                yes, artifact digest observed
L3 Released             yes, production release active
L4 Runtime Seen         yes, runtime sg.release_seen received
L5 Feature Exposed      yes, user/session evidence observed
L6 Code Path Executed   yes, feature probe observed
L7 Effect Committed     yes, server-confirmed effect observed
L8 Outcome Completed    missing or satisfied

Evidence strength: L7 / server-confirmed
```

The viewer must distinguish:

- missing evidence;
- insufficient evidence;
- weak evidence;
- strong evidence;
- client-only evidence;
- server-confirmed evidence;
- tamper-evident receipt evidence.

The viewer should link to the Feature Passport RFC rather than embedding the full
passport schema or receipt schema in SpecGraph UI documentation.

## Relationship To Existing SpecGraph Layers

- Trace plane links specs to code and tests.
- Evidence plane links specs to declared artifact surfaces and observations.
- Implementation work links specs to work candidates and delivery deltas.
- Metric packs may compute adoption, drift, or cost signals from evidence.
- Feature Runtime Evidence Layer connects delivery and production usage to
  request-level proof through Feature Passport.

This proposal extends the evidence plane toward product runtime. It does not
replace existing trace or evidence contracts.

## Honesty Boundary

SpecGraph should preserve the Feature Passport honesty model:

- client-side events are observations, not final proof;
- server-issued receipts are canonical evidence;
- server-confirmed effects have stronger evidence value than client-only events;
- absence of evidence is not automatically evidence of absence;
- adoption metrics must declare sampling, retention, and upload policies.

Critical product proof should prefer backend-confirmed L7/L8 evidence. The exact
receipt and event names remain defined by `FP-RFC-0001`.

## Implementation Plan

Suggested bounded slices:

1. Feature Passport external authority policy and import/reference contract
   updated for `FP-RFC-0001` `0.2.0` through proposal `0203`.
2. Feature Passport index derived from known external/passport sources.
3. Schema contracts for `feature_passport_index`, `feature_evidence_index`,
   receipt projection, and claim-evaluation results before any implementation
   consumes `runs/feature_evidence_index.json`.
4. Build/release provenance projection linked by `request_id` and `feature_id`.
5. Runtime receipt projection linked by Feature Passport evidence claims.
6. Feature evidence ladder derived from passports, provenance, sealed receipts,
   and separate aggregate claim evaluation.
7. Viewer contract for evidence ladder, skipped/inapplicable levels, failure
   observations, aggregate-pending states, and honesty boundary badges.
8. Product workspace integration so non-SpecGraph projects can emit compatible
   evidence without enabling SpecGraph self-evolution.

## Acceptance Criteria

- SpecGraph proposal references `FP-RFC-0001` instead of duplicating the
  Feature Passport RFC content.
- The proposal names Feature Passport as external authority for passport,
  envelope, receipt, and evidence-level semantics.
- The proposal defines SpecGraph-owned derived surfaces for passport/evidence
  observation.
- The proposal preserves evidence ladder semantics and honesty boundaries.
- The proposal identifies compatible external standards without binding
  SpecGraph to a specific vendor.
- The proposal names future implementation slices and keeps this PR
  documentation-only.

## Risks

- Duplicating Feature Passport semantics inside SpecGraph and creating drift.
- Overclaiming proof from client-side telemetry.
- Collecting user-identifiable data when pseudonymous evidence is enough.
- Treating feature flags as proof of execution.
- Treating analytics dashboards as tamper-evident evidence.
- Mixing SpecGraph self-evolution evidence with product-workspace evidence.
- Making the first implementation too large by bundling SDK, backend, storage,
  and viewer UI in one PR.

## Open Questions

- Should SpecGraph discover Feature Passport contracts through SpecPM packages,
  product workspaces, or direct repository references first?
- Should evidence receipts be stored locally, in a product backend, or in a
  dedicated Platform service?
- Which product should provide the first end-to-end proof pilot?
- What is the minimum privacy-safe identity model for per-user or per-session
  counts?
- Should build provenance be pulled from GitHub attestations first, or generated
  as a local SpecGraph-compatible artifact?
