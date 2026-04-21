Status: Draft proposal

# 0027. SpecGraph-to-SpecPM Boundary Export Preview

## Problem

SpecGraph now has enough canonical and derived structure to expose stable
external-consumer bridges, handoff packets, evidence chains, and trace-backed
metric pressure. However, it still lacks a first-class bridge to **SpecPM**,
the sibling package manager that aims to publish and import reusable
boundary-first specification packages.

Today this creates a gap:

- SpecGraph can govern and inspect internal semantic structure.
- SpecPM can package boundary contracts for reuse.
- But there is no reviewable bridge that shows how a bounded SpecGraph region
  could be exported as a **SpecPM package preview** without pretending that the
  full package has already been finalized.

Without that bridge:

- SpecPM remains only an external idea, not an observed downstream consumer.
- Exportable module boundaries stay implicit in prose or operator memory.
- SpecGraph cannot review a package-shaped preview before real cross-repo
  delivery exists.

## Why This Matters

SpecPM is not just another repository. It is the first concrete downstream
consumer that turns SpecGraph semantics into a reusable published boundary.

That means SpecGraph needs a bounded way to answer:

- which external consumer contract is being targeted;
- which canonical spec region is the source of export intent;
- what minimal `specpm.yaml`-shaped preview can already be derived;
- which fields still require further boundary refinement before real delivery.

This also keeps the reflective loop honest:

> observe -> propose -> improve tools -> observe again

The bridge should therefore begin as a **preview artifact**, not as automatic
publication and not as silent package generation.

## Goals

- Add SpecPM as an external consumer in the existing external-consumer bridge
  model, not as a parallel ad hoc integration path.
- Distinguish SpecPM as a **boundary package consumer** profile rather than a
  sibling metric consumer.
- Define a repository-tracked export registry that declares which bounded
  SpecGraph regions are intended to produce SpecPM package previews.
- Emit a derived preview artifact that combines:
  - SpecPM consumer readiness,
  - declared export contract,
  - manifest preview,
  - boundary-source preview,
  - explicit unresolved gaps for a future full BoundarySpec.
- Keep the bridge reviewable even while the SpecPM RFC remains draft.

## Non-Goals

- Publishing packages into SpecPM automatically.
- Treating a draft SpecPM RFC as threshold-driving authority.
- Generating a complete final `BoundarySpec` for every SpecGraph region.
- Replacing product-spec or techspec handoff semantics.
- Designing a bidirectional import pipeline in the same change.

## Core Proposal

SpecGraph should add a **SpecPM export preview layer** with four bounded pieces.

### 1. External Consumer Entry for SpecPM

The external-consumer registry should gain a new consumer:

- `consumer_id = specpm`
- `profile = boundary_package_consumer`
- `reference_state = draft_reference`

The entry should point to the local sibling checkout when available and inspect
the minimal consumer-defining artifacts:

- `README.md`
- `RFC/SpecGraph-RFC-0001.md`

This keeps SpecPM visible inside the same bridge framework already used for
Metrics.

### 2. Repository-Tracked Export Registry

SpecGraph should define a small repository-tracked export registry describing
which bounded SpecGraph concern is intended to produce a SpecPM package preview.

Each export entry should at minimum declare:

- stable export ID;
- target external consumer ID;
- package ID;
- package name;
- package version;
- package summary;
- package license;
- root SpecGraph source spec;
- bounded source spec IDs;
- provided capability IDs.

This registry is the authored declaration of export intent. The runtime artifact
should not invent package identities or capabilities from free-form graph text
alone.

### 3. Derived SpecPM Export Preview Artifact

SpecGraph should emit a derived artifact, for example:

- `runs/specpm_export_preview.json`

Each entry should carry:

- consumer bridge state;
- export contract validity;
- review state;
- next gap;
- minimal `specpm.yaml` preview;
- boundary-source preview linking the export to canonical source specs and
  acceptance/evidence inputs;
- explicit missing fields required before a full BoundarySpec can be emitted.

The key principle is:

- **manifest preview may already be complete enough to review**
- while **boundary spec preview may still be intentionally incomplete**

This keeps the export path honest and reviewable.

### 4. Draft-Friendly Review Semantics

Because the current SpecPM RFC is still draft, SpecGraph should allow:

- preview emission for draft-visible SpecPM consumer state

but should not treat that as:

- stable external authority,
- automatic delivery,
- or final package publication readiness.

The preview layer should therefore distinguish between:

- stable-ready consumer review,
- draft-preview-only review,
- blocked-by-consumer-gap,
- invalid export contract.

## Canonical vs Derived Boundary

Canonical:

- the external-consumer registry entry for SpecPM;
- the SpecPM export registry entries that declare intended export contracts.

Derived:

- checkout availability and repo identity;
- preview manifest rendering;
- preview boundary-source packet;
- export readiness classification;
- next-gap grouping and viewer projections.

## Adoption Order

1. Add SpecPM to the external-consumer registry as a draft boundary-package
   consumer.
2. Add one repository-scoped export registry entry for the first bounded
   SpecGraph export candidate.
3. Emit the derived SpecPM export preview artifact.
4. Later add cross-repo delivery and reverse import/feedback paths.

## Open Questions

- Which additional SpecGraph regions, beyond the initial repository-facade
  candidate, should become package export candidates?
- When should draft SpecPM references become stable enough for real delivery
  workflow?
- How should future full BoundarySpec generation map interfaces and effects
  without inventing behavior that the source graph does not yet govern?
