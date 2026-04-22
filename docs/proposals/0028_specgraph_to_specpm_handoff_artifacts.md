Status: Draft proposal

# 0028. SpecGraph-to-SpecPM Handoff Artifacts

## Problem

`SpecGraph` can now emit a reviewable `SpecPM` package preview, but it still
stops one step too early. A preview answers:

- what package-like shape could be derived;
- which bounded region it comes from;
- which fields are still missing.

It does **not** yet answer:

- what exact handoff packet should be reviewed before downstream delivery;
- which `SpecPM` checkout or consumer identity that packet targets;
- whether the preview is ready for handoff, still draft-only, or blocked by a
  preview gap.

Without this layer, viewer integrations can show previews but cannot cleanly
distinguish “interesting draft preview” from “reviewable downstream handoff”.

## Why This Matters

`SpecPM` is the first downstream consumer intended to package a bounded
`SpecGraph` region through its external interface. The bridge should therefore
progress in bounded steps:

1. detect the consumer;
2. declare what export is intended;
3. build a package preview;
4. build a reviewable handoff packet;
5. only later attempt true export/import workflows.

The missing handoff layer is the boundary between preview-only observation and
future operational delivery.

## Goals

- Add a dedicated `SpecPM` handoff artifact on top of the existing preview.
- Reuse the preview as the semantic source of truth rather than recomputing
  package readiness from raw graph state.
- Expose reviewable statuses such as `ready_for_handoff`,
  `draft_preview_only`, and `blocked_by_preview_gap`.
- Carry target consumer identity, local checkout hint, package preview, and
  boundary source preview inside the handoff packet.

## Non-Goals

- Writing package files into the `SpecPM` repository.
- Defining the final stable `specpm.yaml` schema.
- Importing `SpecPM` packages back into `SpecGraph`.
- Promoting `SpecPM` draft RFCs into authority.

## Core Proposal

Add a new derived artifact:

- `runs/specpm_handoff_packets.json`

This artifact is built from:

- `runs/specpm_export_preview.json`
- `tools/specpm_export_registry.json`
- `tools/external_consumers.json`

Each handoff entry should:

- point to one declared export entry;
- preserve the target `SpecPM` consumer metadata;
- include the previewed `specpm.yaml`-shaped manifest;
- include the boundary-source preview;
- derive a handoff status from preview status, not from ad hoc re-analysis;
- optionally emit a reviewable transition packet for future downstream delivery.

## Expected Effect

After this change, `SpecGraph` still will not perform a real export into
`SpecPM`, but it will have a stable reviewable handoff layer:

- preview answers “what would be exported”;
- handoff answers “what can now be reviewed for downstream transfer”.
