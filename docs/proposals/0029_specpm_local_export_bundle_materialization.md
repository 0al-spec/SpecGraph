Status: Draft proposal

# 0029. SpecPM Local Export Bundle Materialization

## Problem

`SpecGraph` can now emit:

- a `SpecPM` package preview;
- a reviewable `SpecPM` handoff packet.

That is enough for inspection, but not yet enough for an actual export button.
There is still no bounded workflow that materializes a concrete local package
bundle with:

- `specpm.yaml`
- `specs/main.spec.yaml`
- copied evidence files

without pretending that the package is already published or stable.

## Why This Matters

The next practical step for `SpecPM` is not registry publication. It is a local
reviewable bundle that a human can inspect inside the sibling checkout before
any future import, commit, or release workflow.

This needs to be:

- explicit;
- reversible;
- confined to a controlled inbox path;
- derived from already-reviewed preview and handoff artifacts.

## Goals

- Add a local materialization workflow for `SpecPM` export bundles.
- Write only into a controlled inbox path inside the sibling `SpecPM` checkout.
- Derive bundle contents from `specpm_handoff_packets`, not from raw graph
  state.
- Emit a materialization report in `runs/` so viewers can show export results.

## Non-Goals

- Auto-committing into the `SpecPM` repository.
- Publishing to any registry.
- Promoting draft RFCs to authority.
- Implementing import back from `SpecPM`.

## Core Proposal

Add a standalone supervisor flow that:

1. rebuilds the current `SpecPM` export preview;
2. rebuilds the current `SpecPM` handoff packets;
3. writes concrete local bundle files under a controlled inbox path in the
   sibling `SpecPM` checkout;
4. emits a derived report describing what was materialized and what remains
   blocked.

The materialization output should include:

- `specpm.yaml`
- `specs/main.spec.yaml`
- copied evidence files under `evidence/source/`
- a machine-readable handoff/provenance sidecar

## Expected Effect

After this change, `SpecGraph` still will not publish a package, but it will be
able to materialize a draft export bundle that another tool or human reviewer
can inspect directly inside the local `SpecPM` checkout.
