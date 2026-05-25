# Feature Runtime Evidence Layer

## Status

Draft proposal

## Source Material

This proposal captures the operator request to prove that a SpecGraph request or
feature reached production and produced user-visible runtime evidence.

Source draft:

- `docs/archive/proposal_sources/0058_feature_runtime_evidence_layer.md`

External reference anchors:

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

The intended direction is a SpecGraph evidence layer that connects intent to
delivery and runtime use:

```text
User request / spec node
  -> PR / commit
  -> build artifact / binary / image
  -> release / deployment
  -> runtime session
  -> feature exposure
  -> feature code path executed
  -> user-visible outcome
  -> signed or hash-linked evidence receipt
```

This is not continuous profiling. It is product evidence: a governed chain of
facts showing how a graph request became observable production behavior.

## Problem

Current engineering signals often stop too early:

- a commit exists;
- a PR is merged;
- an artifact was built;
- a release was created;
- analytics reports a page view or flag exposure.

None of those alone proves that a specific SpecGraph request produced a
specific user-visible outcome in production.

SpecGraph needs a first-class contract for evidence strength. Without it,
operators and viewers may confuse weak signals with strong proof:

- `merged` is not the same as `built`;
- `built` is not the same as `deployed`;
- `deployed` is not the same as `seen by runtime`;
- `flag evaluated` is not the same as `feature code path executed`;
- `code path executed` is not always the same as `intended outcome completed`;
- client-side telemetry is not adversarially perfect proof.

The graph should expose those distinctions explicitly.

## Goals

- Define a Feature Passport contract for graph-owned feature identity and
  required probes.
- Define a delivery-to-runtime evidence chain from request to outcome.
- Distinguish evidence strength levels from weak Git visibility to strong
  production outcome evidence.
- Define a small feature probe vocabulary for exposure, execution, effect, and
  outcome.
- Allow supply-chain provenance systems to satisfy build/release evidence.
- Allow telemetry systems to transport runtime events without making them graph
  authority.
- Define signed or hash-linked evidence receipts as the trusted ingestion
  output.
- Define viewer-facing evidence ladder semantics for SpecSpace or other Graph
  Operator Surfaces.
- Preserve honest limits for client-side telemetry and hostile endpoints.

## Non-Goals

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

Introduce **Feature Runtime Evidence Layer** as a governed evidence layer above
implementation work:

```text
specification graph
  -> feature passport
  -> implementation linkage
  -> build provenance
  -> release/deployment observation
  -> runtime feature probes
  -> backend evidence receipts
  -> viewer evidence ladder
```

The layer should not claim that a feature is "done" merely because code exists.
It should report the strongest verified evidence level currently observed for
each request or feature.

## Evidence Strength Levels

### Level 0: Commit Visible

The request is linked to a PR or commit.

This is weak evidence. It is useful for development traceability, but it does
not prove delivery.

### Level 1: Commit Built Into Artifact

The commit is included in a build artifact with a digest and build provenance.

Compatible evidence may come from:

- GitHub Artifact Attestations;
- SLSA provenance;
- Sigstore/Cosign or equivalent artifact signatures;
- a local build-provenance artifact generated by the project.

This proves that a build artifact was produced from the implementation input,
but not that it reached production.

### Level 2: Artifact Released Or Deployed To Production

The artifact digest is connected to a release, deployment, app build, container
image rollout, or equivalent production delivery record.

This proves production delivery intent and deployment state, but not that a
user session exercised the feature.

### Level 3: Feature Code Path Executed In Production

Production runtime sessions emitted feature-specific probes from inside the
feature code path.

Required probe examples:

- `sg.feature.code_path.executed`

Conditional probe examples:

- `sg.feature.exposed`

`sg.feature.exposed` is required for UI or user-entry-point features. Backend,
headless, background, scheduled, or migration-style features may satisfy Level 3
without exposure evidence when their Feature Passport explicitly marks exposure
as not applicable.

This proves execution of instrumented code paths, but not necessarily
successful user-visible outcome.

### Level 4: Intended Outcome Completed

Production evidence confirms the feature produced the intended effect or
user-visible outcome.

Required probe examples:

- `sg.feature.effect_committed`
- `sg.feature.outcome_completed`

For server-backed features, `effect_committed` should be emitted by or confirmed
through the backend whenever possible.

## Feature Passport

Introduce a future artifact family:

```text
FeaturePassport
```

Suggested shape:

```yaml
artifact_kind: feature_passport
schema_version: 1
metadata:
  feature_id: feature.invoice.smart_summary
  request_id: SG-REQ-2026-001
  title: Smart invoice summary
  owner: product-ios
  created_at: "2026-05-25T12:00:00Z"
spec:
  intent:
    source_spec_ids:
      - SG-SPEC-XXXX
    acceptance_criteria:
      - Summary block is visible on invoice screen.
      - User can expand summary.
      - Backend records summary generation result.
  source:
    repo: github.com/org/product-ios
    pull_requests:
      - 1842
    commits:
      - 8ae73a0f
  rollout:
    platforms:
      - ios
      - macos
      - backend
    environments:
      - production
    feature_flag:
      provider: openfeature
      key: invoice.smart_summary
  required_runtime_evidence:
    - event: sg.feature.exposed
      probe_id: invoice_summary.visible.v1
      min_count: 1
      required_when: ui_or_user_entry_point
    - event: sg.feature.code_path.executed
      probe_id: invoice_summary.render.v1
      min_count: 1
    - event: sg.feature.effect_committed
      probe_id: invoice_summary.backend_accepted.v1
      min_count: 1
    - event: sg.feature.outcome_completed
      probe_id: invoice_summary.completed.v1
      min_count: 1
  privacy:
    user_identifier: pseudonymous_hash
    pii_allowed: false
    retention_days: 90
  evidence_strength:
    required_level: 4
```

The passport is not runtime proof by itself. It declares what proof must exist
for a feature to satisfy the graph request.

`metadata.request_id` is the canonical request identifier key for Feature
Passport and runtime events. Older or external sources may expose a field named
`specgraph_request_id`, but ingestion must normalize that alias into
`request_id` before validating events against passports.

## Runtime Event Vocabulary

The first runtime event vocabulary should be small:

- `sg.release_seen`: runtime reports build/release identity in production.
- `sg.feature.flag_evaluated`: feature flag or configuration decision was
  evaluated for a session.
- `sg.feature.exposed`: user could see or access the feature entry point.
- `sg.feature.code_path.executed`: instrumented feature code path ran.
- `sg.feature.effect_committed`: backend, local state, or durable side effect
  was committed.
- `sg.feature.outcome_completed`: intended user-visible outcome completed.
- `sg.feature.failed`: feature path failed before outcome.

Common event fields:

```json
{
  "event": "sg.feature.code_path.executed",
  "feature_id": "feature.invoice.smart_summary",
  "request_id": "SG-REQ-2026-001",
  "probe_id": "invoice_summary.render.v1",
  "env": "production",
  "platform": "ios",
  "app_version": "2.7.0",
  "build_number": "134",
  "git_sha": "8ae73a0f",
  "artifact_digest": "sha256:abc123",
  "provenance_id": "gh-attestation://...",
  "user_hash": "u_6d12",
  "session_id": "s_9a81",
  "trace_id": "01HV...",
  "timestamp": "2026-05-25T15:03:44Z"
}
```

Required common fields are `event`, `feature_id`, `request_id`, `probe_id`,
`env`, `platform`, and `timestamp`. Build and provenance fields are required
when the event claims release or artifact linkage. `user_hash` and `session_id`
are conditional: UI/session evidence should include them when privacy policy
allows pseudonymous identity, while backend-only or batch evidence may omit
them and rely on server-side operation identifiers instead.

Raw PII, raw prompt text, secrets, access tokens, private local paths, and
unredacted user content must not appear in viewer-facing evidence artifacts.

## Evidence Receipts

Client and runtime events should not be the final trust anchor. A backend
ingestion layer should normalize and seal events as evidence receipts:

```json
{
  "receipt_id": "rcpt_01J...",
  "event_hash": "sha256:...",
  "previous_hash": "sha256:...",
  "ingested_at": "2026-05-25T15:04:00Z",
  "source": "ios",
  "validated": true,
  "validation": {
    "known_release": true,
    "known_artifact_digest": true,
    "known_feature_passport": true,
    "probe_declared_in_passport": true,
    "user_session_valid": true
  },
  "signature": {
    "algorithm": "Ed25519",
    "signed_by": "specgraph-evidence-ingestor-prod",
    "value": "..."
  }
}
```

Receipt storage should be append-only or tamper-evident. A hash chain is the
minimum useful model:

```text
receipt_hash_n = sha256(canonical_json(event_n) + previous_hash)
```

where `previous_hash` is the sealed receipt hash for receipt `n-1` or a
well-known genesis value for the first receipt in a chain.

The graph should consume receipts or receipt summaries, not raw untrusted
client events.

## Evidence Graph Model

The logical evidence graph may contain:

```text
(:UserRequest)
(:Feature)
(:Probe)
(:PullRequest)
(:Commit)
(:Build)
(:Artifact)
(:Release)
(:Deployment)
(:RuntimeSession)
(:FeatureEvent)
(:Outcome)
(:EvidenceReceipt)
```

Suggested relations:

```text
(:UserRequest)-[:REQUESTED]->(:Feature)
(:Feature)-[:REQUIRES_PROBE]->(:Probe)
(:Feature)-[:IMPLEMENTED_BY]->(:Commit)
(:Commit)-[:BUILT_IN]->(:Build)
(:Build)-[:PRODUCED]->(:Artifact)
(:Artifact)-[:RELEASED_AS]->(:Release)
(:Release)-[:DEPLOYED_TO]->(:Deployment)
(:Deployment)-[:OBSERVED_IN]->(:RuntimeSession)
(:RuntimeSession)-[:EMITTED]->(:FeatureEvent)
(:FeatureEvent)-[:SATISFIES]->(:Probe)
(:FeatureEvent)-[:SEALED_BY]->(:EvidenceReceipt)
```

This graph can be represented as JSON artifacts first. It does not require a
graph database in the first implementation.

## Viewer Surface

Viewers should show an evidence ladder instead of a single boolean:

```text
Request: SG-REQ-2026-001
Feature: feature.invoice.smart_summary

Intent
  captured
  acceptance approved

Implementation
  PR linked
  commit linked
  required probes declared

Build
  artifact digest observed
  provenance verified

Release
  production release active
  runtime sg.release_seen received

Adoption
  feature exposed
  code path executed
  effect committed
  outcome completed

Evidence strength: Level 4 / strong
```

The viewer must distinguish:

- missing evidence;
- insufficient evidence;
- weak evidence;
- strong evidence;
- client-only evidence;
- server-confirmed evidence;
- tamper-evident receipt evidence.

## Relationship To Existing SpecGraph Layers

- Trace plane links specs to code and tests.
- Evidence plane links specs to declared artifact surfaces and observations.
- Implementation work links specs to work candidates and delivery deltas.
- Metric packs may compute adoption, drift, or cost signals from evidence.
- Feature Runtime Evidence Layer connects delivery and production usage to
  request-level proof.

This proposal extends the evidence plane toward product runtime. It does not
replace existing trace or evidence contracts.

## Honesty Boundary

Backend production evidence can approach strong cryptographic assurance when it
uses signed artifacts, verified deployments, server-side runtime events, and
signed receipts.

Client-side evidence cannot fully prove that an endpoint was not compromised.
For iOS, macOS, desktop, or browser clients, the graph should report the
strength honestly:

| Claim | Evidence strength |
|---|---|
| Commit was included in artifact | Strong with provenance or attestation |
| Artifact was released or deployed | Strong with release/deployment receipt |
| Runtime with build identity was seen | Strong for operational visibility |
| Feature flag was evaluated | Good if SDK event is sealed by backend |
| Feature code path executed | Good if probe is inside code path |
| Feature produced outcome | Strongest when confirmed by backend state |
| Client event cannot be forged | Not guaranteed without trusted hardware or remote attestation |

Critical product proof should prefer backend-confirmed `effect_committed` and
`outcome_completed` events.

## Implementation Plan

Suggested bounded slices:

1. Feature Passport policy and viewer contract.
2. Build/release provenance index for commit-to-artifact-to-release evidence.
3. Runtime evidence event vocabulary and sample SDK contracts.
4. Evidence receipt contract and append-only ledger shape.
5. Feature evidence index derived from passports and receipts.
6. Viewer projection showing evidence ladder per request or feature.
7. Product workspace integration so non-SpecGraph projects can emit compatible
   evidence without enabling SpecGraph self-evolution.

## Acceptance Criteria

- A proposal exists for Feature Runtime Evidence Layer with clear evidence
  levels and honesty boundaries.
- The proposal defines Feature Passport as declaration, not proof.
- The proposal defines runtime probe vocabulary and required common fields.
- The proposal defines evidence receipts as the trusted ingestion output.
- The proposal identifies compatible external standards without binding
  SpecGraph to a specific vendor.
- The proposal names future implementation slices and keeps this PR
  documentation-only.

## Risks

- Overclaiming proof from client-side telemetry.
- Collecting user-identifiable data when pseudonymous evidence is enough.
- Treating feature flags as proof of execution.
- Treating analytics dashboards as tamper-evident evidence.
- Mixing SpecGraph self-evolution evidence with product-workspace evidence.
- Making the first implementation too large by bundling SDK, backend, storage,
  and viewer UI in one PR.

## Open Questions

- Should Feature Passport live in SpecGraph, product workspaces, or SpecPM
  packages first?
- Should evidence receipts be stored locally, in a product backend, or in a
  dedicated Platform service?
- Which product should provide the first end-to-end proof pilot?
- What is the minimum privacy-safe identity model for per-user or per-session
  counts?
- Should build provenance be pulled from GitHub attestations first, or generated
  as a local SpecGraph-compatible artifact?
