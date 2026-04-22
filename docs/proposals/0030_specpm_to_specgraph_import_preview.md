Status: Draft proposal

# 0030. SpecPM-to-SpecGraph Import Preview

## Problem

`SpecGraph` can now emit:

- a `SpecPM` export preview;
- a `SpecPM` handoff packet;
- a local materialized draft bundle in the sibling `SpecPM` checkout.

That is enough for downstream inspection, but not enough for the reverse
question: how should `SpecGraph` inspect a local `SpecPM` bundle **without**
silently importing it into the canonical graph?

Right now there is no bounded review-first layer that says:

- which local bundle was found under `.specgraph_exports/<package_id>/`;
- whether its `specpm.yaml` is structurally valid;
- whether its `specs/main.spec.yaml` looks like a coherent boundary spec;
- whether `handoff.json` preserves continuity with the original export/handoff;
- what kind of upstream `SpecGraph` artifact this bundle could become.

## Why This Matters

The `SpecPM` bridge is no longer only about export. Once local bundle
materialization exists, the next safe step is **inspection of the resulting
package as an inbound candidate**.

That inspection must remain:

- review-first;
- explicit;
- non-mutating for canonical specs;
- derived from the bundle itself, not from wishful assumptions about upstream
  state.

Without that layer, a viewer can show export previews and local bundles, but it
still cannot answer the practical question:

> “If this bundle came back into SpecGraph, what would it mean and what is still
> missing?”

## Goals

- Add a reviewable import-preview layer for local `SpecPM` bundles.
- Treat `.specgraph_exports/<package_id>/` inside the sibling `SpecPM` checkout
  as the immediate source of truth for import inspection.
- Validate manifest, boundary spec, and handoff continuity without mutating the
  canonical graph.
- Emit a derived artifact that viewers can render directly.

## Non-Goals

- Auto-importing bundles into `specs/nodes/*.yaml`.
- Writing proposal-lane or intent-layer nodes automatically.
- Creating cross-repo commits.
- Treating draft import previews as canonical truth.

## Core Proposal

Add a standalone supervisor flow that:

1. inspects the declared `SpecPM` external consumer checkout;
2. scans the controlled inbox path `.specgraph_exports/`;
3. reads any discovered `specpm.yaml`, `specs/main.spec.yaml`, and
   `handoff.json`;
4. derives a reviewable import preview for each bundle.

The import preview artifact should answer four questions:

1. **Was a bounded bundle found?**
2. **Is the bundle structurally valid enough for review?**
3. **Does it preserve continuity with the original SpecGraph handoff?**
4. **What upstream artifact kind should this bundle map to next?**

## Expected Artifact

Add:

- `tools/specpm_import_policy.json`
- `runs/specpm_import_preview.json`
- `--build-specpm-import-preview`

Each entry should include:

- bundle path;
- import status;
- review state;
- next gap;
- manifest validity;
- boundary-spec validity;
- handoff continuity summary;
- suggested target kind such as `proposal`, `pre_spec`, or
  `handoff_candidate`.

## Expected Effect

After this change, `SpecGraph` still will not import anything automatically.
But it will be able to inspect local `SpecPM` bundles as **reviewable inbound
candidates**, which is the missing reverse step after export preview, handoff,
and local bundle materialization.
