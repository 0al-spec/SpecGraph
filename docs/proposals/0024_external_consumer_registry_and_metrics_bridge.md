# External Consumer Registry and Metrics Bridge

## Status

Draft proposal

## Problem

SpecGraph now derives several useful internal metric and inspection surfaces:

- implementation trace
- evidence plane
- graph-health overlays and trends
- proposal-runtime overlays
- metric-derived signals

That is enough to support a bootstrap composite such as `sib_proxy`.

But the project now also has a real neighboring consumer in the same
organization:

- [Metrics / SIB](https://github.com/0al-spec/Metrics/tree/main/SIB)
- and a broader draft extension in `Metrics/SIB_FULL`

This creates a new gap.

SpecGraph can point at the idea of an external sibling consumer, but it still
has no governed way to answer:

> Which external consumer artifacts are relevant, which of them are stable
> enough to affect local derived metrics, and how should that bridge be
> inspected?

Without that bridge, one of two bad patterns emerges:

- `sib_proxy` remains a purely internal surrogate with weak relation to the
  real SIB framework
- or SpecGraph starts depending on ad hoc local checkout assumptions with no
  declared contract and no reviewable distinction between stable and draft
  references

## Why This Matters

SpecGraph is now mature enough that some of its derived surfaces should start
anchoring against real external consumers, not only internal bootstrap
proxies.

This matters for three reasons.

### 1. Real Ecosystem Feedback

If a sibling repository already defines the intended consumer surface, SpecGraph
should be able to inspect that surface directly instead of reasoning only from
internal placeholders.

### 2. Safer Cross-Repo Semantics

Not every external artifact should immediately become threshold authority.

The project needs an explicit distinction between:

- stable external references that may influence derived signals
- draft or extended references that are visible but not yet authoritative

### 3. Better Future Bridges

Once one external consumer bridge exists, the same shape can later support:

- downstream product-spec graphs
- tech-spec consumers
- metric repositories
- runtime observability registries in neighboring repos

## Goals

- Define a repository-tracked registry of external consumers.
- Introduce a derived bridge artifact that inspects declared external consumer
  contracts.
- Distinguish stable and draft external references explicitly.
- Support optional local sibling checkouts without requiring Git submodules.
- Let `sib_proxy` become bridge-backed when a stable Metrics/SIB bridge is
  available.
- Preserve bootstrap fallback semantics when no stable bridge is available in
  the local environment.

## Non-Goals

- Adding `Metrics` as a Git submodule
- Making remote network fetches part of ordinary supervisor execution
- Treating draft external documents as immediate threshold authority
- Replacing the final SIB framework with a one-step local approximation
- Parsing the full semantic content of external papers in this first slice
- Turning external consumer availability into canonical graph truth

## Core Proposal

SpecGraph should add an **external consumer registry** as a tracked repository
artifact.

This registry should declare:

- consumer identity
- repository URL
- optional local checkout hint
- profile or consumer family
- declared artifact paths
- metric or bridge bindings
- reference state such as `stable_reference` or `draft_reference`

SpecGraph should also add a derived **external consumer index** that inspects
those declarations and reports:

- whether the declared local checkout is present
- whether required artifacts exist
- whether expected markers are visible
- whether the external consumer contract is currently reviewable

This makes the bridge inspectable without turning the external repository into
canonical SpecGraph state.

## Stable vs Draft External References

This proposal introduces a strict distinction:

- `stable_reference`
- `draft_reference`

The first bridge should register:

- `Metrics/SIB` as `stable_reference`
- `Metrics/SIB_FULL` as `draft_reference`

The intended meaning is:

- stable references may influence derived bridge-backed metric behavior
- draft references may be surfaced for inspection and future contributions, but
  do not yet drive threshold pressure or policy expectations directly

## Bridge-Backed `sib_proxy`

The current `sib_proxy` should not disappear immediately.

Instead, it should become a bridge-aware derived metric with two modes:

- `bridge_backed`
- `bootstrap_fallback`

In `bridge_backed` mode, the metric may use the stable external consumer bridge
as one of its declared inputs.

In `bootstrap_fallback` mode, the metric continues to rely only on internal
SpecGraph-derived observability surfaces.

This keeps the metric environment-tolerant while still allowing it to anchor
against a real sibling consumer when available.

## Local Checkout Model

The bridge should prefer a declared sibling checkout model over a Git
submodule.

That means:

- the registry declares `repo_url`
- the registry may declare `local_checkout_hint`
- the derived bridge artifact inspects the checkout if it exists locally

This allows:

- local strong inspection in development
- reviewable bridge declarations in the repository
- zero mandatory vendoring of the sibling repo

## Suggested Derived Artifact Shape

The first bridge artifact may include fields such as:

- `consumer_id`
- `reference_state`
- `repo_url`
- `local_checkout.status`
- `contract_status`
- `artifact_status_counts`
- `metric_bindings`
- `viewer_projection`

The exact field names may evolve, but the semantic boundary should remain:

- registry declares what should be inspected
- index reports what is actually available

## Expected First Application

The first bounded application should cover only:

- external consumer registry
- Metrics/SIB and Metrics/SIB_FULL declarations
- one bridge index artifact
- one bridge-backed upgrade of `sib_proxy`

This is intentionally smaller than a full cross-repo metric runtime.

It gives SpecGraph a reviewable bridge contract before any deeper integration
or threshold redesign.
