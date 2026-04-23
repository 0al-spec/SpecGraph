Status: Draft proposal

# 0031. SpecPM Import Handoff Artifacts

## Problem

`SpecGraph` can already:

- build a `SpecPM` export preview;
- build a downstream `SpecPM` handoff packet;
- materialize a local draft bundle into the sibling `SpecPM` checkout;
- inspect that bundle through `runs/specpm_import_preview.json`.

That still leaves one review-first gap:

> how does a valid inbound `SpecPM` bundle become an explicit upstream
> candidate for `SpecGraph` without silently mutating canonical specs?

`specpm_import_preview` tells us what exists and whether it is structurally
sound enough for review. It does **not** yet emit a dedicated artifact that
answers:

- whether the bundle is now ready to become a proposal-lane candidate;
- whether it should remain only a handoff candidate;
- whether import gaps still block any upstream routing;
- what reviewable packet should represent that next transition.

## Why This Matters

The current `SpecPM` loop now has four bounded stages:

1. export preview;
2. downstream handoff;
3. local materialization;
4. import preview.

Without a fifth stage, the loop still stops just before a meaningful upstream
handoff.

That means viewers can show:

- “a bundle exists”;
- “the bundle looks draft-visible or reviewable”;

but cannot show:

- “this bundle is now an explicit proposal-lane candidate”;
- “this bundle is still only a handoff candidate”;
- “this bundle remains blocked by import gaps”.

## Goals

- Add a reviewable import-handoff artifact on top of `specpm_import_preview`.
- Reuse the import preview as the semantic source of truth rather than
  re-parsing bundle structure from scratch.
- Emit explicit route metadata for proposal-lane, handoff-candidate, or
  pre-spec-candidate outcomes.
- Emit a transition packet only when the inbound bundle is genuinely ready for
  review as an upstream candidate.

## Non-Goals

- Auto-importing `SpecPM` bundles into canonical `specs/nodes/*.yaml`.
- Writing tracked proposal-lane nodes automatically.
- Applying inbound bundles silently.
- Cross-repo delivery or review automation.

## Core Proposal

Add a new derived artifact:

- `runs/specpm_import_handoff_packets.json`

Built from:

- `runs/specpm_import_preview.json`

And exposed through:

- `--build-specpm-import-handoff-packets`
- `tools/specpm_import_handoff_policy.json`

Each handoff entry should:

- point to one import-preview bundle;
- preserve the current import status and continuity summary;
- derive a bounded upstream handoff status such as:
  - `ready_for_lane`
  - `draft_visible_only`
  - `blocked_by_import_gap`
  - `invalid_import_contract`
- carry route metadata that says whether the bundle currently maps to:
  - a proposal-lane candidate
  - a handoff candidate
  - a pre-spec candidate
- emit a transition packet only for the `ready_for_lane` case.

## Expected Effect

After this change:

- `specpm_import_preview` answers “what does the inbound bundle look like?”
- `specpm_import_handoff_packets` answers “what upstream reviewable candidate
  does this bundle become next?”

The graph still remains review-first:

- no canonical mutation;
- no automatic lane write;
- only explicit, inspectable, bounded upstream handoff artifacts.
