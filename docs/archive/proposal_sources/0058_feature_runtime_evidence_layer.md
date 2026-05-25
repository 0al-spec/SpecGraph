# Feature Runtime Evidence Layer Source Draft

## Source Context

The operator asked how SpecGraph can prove that a user request or feature is
not only specified and implemented, but actually reached production and was
executed by users.

The desired evidence chain is stronger than ordinary analytics:

```text
user request / spec node
  -> pull request / commit
  -> build artifact / app binary / container image
  -> release / deployment
  -> runtime session
  -> feature exposure
  -> feature code path executed
  -> user-visible outcome
```

The key claim is that "commit reached production" should not mean "the commit
appears in release notes". It should mean:

- the commit is included in a build artifact;
- the artifact has build provenance and a digest;
- the artifact was released or deployed to production;
- the production runtime reported its build identity;
- feature-specific probes observed exposure, execution, effect, and outcome;
- the backend accepted those observations and sealed them as evidence receipts.

## Operator Intent

Add a proposal for a SpecGraph evidence layer that can connect specification
intent to implementation delivery and runtime product usage.

The layer should introduce a Feature Passport concept and a small event
vocabulary:

- `sg.release_seen`
- `sg.feature.exposed`
- `sg.feature.code_path.executed`
- `sg.feature.effect_committed`
- `sg.feature.outcome_completed`

The layer should treat OpenTelemetry, SLSA, GitHub Artifact Attestations,
Sigstore/Cosign, OpenFeature, Sentry, Datadog, or LaunchDarkly as compatible
sources or transports, not as the canonical SpecGraph model.

## Desired Outcome

Define a proposal for:

- a `FeaturePassport` contract;
- a delivery and runtime evidence graph;
- feature probe levels from commit to user-visible outcome;
- signed or hash-linked evidence receipts;
- a viewer-facing evidence ladder;
- explicit honesty boundaries for client-side telemetry.

## Boundary

This proposal should not implement telemetry SDKs, ingestion infrastructure,
storage, hosted services, or SpecSpace UI. It should define the product
evidence architecture that later proposals and specs can materialize in bounded
slices.
