# SpecPM Viewer Contract

This document fixes the viewer-facing JSON contract for the current
`SpecGraph -> SpecPM -> SpecGraph` review loop.

It does not introduce a new artifact family. The contract is a stable field
subset over already existing derived artifacts under `runs/`.

Use this document when implementing:

- `Build Export Preview`
- `Build Import Preview`
- `SpecPM` package cards
- handoff status cards
- local materialization status
- import review status
- downstream feedback status

## 1. Lifecycle Overview

The current downstream loop is:

1. build export preview
2. build handoff packets
3. materialize local draft bundle into sibling `SpecPM`
4. build import preview from local bundle inbox
5. observe downstream review or local adoption feedback from `SpecPM`

The corresponding artifacts are:

- `runs/specpm_export_preview.json`
- `runs/specpm_handoff_packets.json`
- `runs/specpm_materialization_report.json`
- `runs/specpm_import_preview.json`
- `runs/specpm_feedback_index.json`

Recommended rebuild order for a viewer button group:

```bash
python3 tools/supervisor.py --build-specpm-export-preview
python3 tools/supervisor.py --build-specpm-handoff-packets
python3 tools/supervisor.py --materialize-specpm-export-bundles
python3 tools/supervisor.py --build-specpm-import-preview
python3 tools/supervisor.py --build-specpm-feedback-index
```

## 2. Stable Top-Level Contract

All five artifacts should be consumed with the same top-level assumptions:

- `artifact_kind`
- `schema_version`
- `generated_at`
- `policy_reference`
- `source_artifacts`
- `entry_count`
- `entries`
- `viewer_projection`

Viewer code should treat these fields as stable entry points.

### Common rendering rule

For every artifact:

- render `entry_count` as the top-level badge
- use `viewer_projection` for grouped counters and filter chips
- use `entries[]` for cards or row-level detail
- use `source_artifacts` only for provenance / debug drawers

## 3. Export Preview Contract

Read:

- `runs/specpm_export_preview.json`

Use each `entries[]` object as one export-preview card.

Required fields for the viewer:

- `export_id`
- `consumer_id`
- `consumer_title`
- `consumer_reference_state`
- `consumer_bridge_state`
- `export_status`
- `review_state`
- `next_gap`
- `package_preview`
- `boundary_source_preview`
- `contract_errors`

Recommended card title:

- `package_preview.metadata.name`
- fallback: `export_id`

Recommended status badge:

- `export_status`

Recommended subtitle fields:

- `consumer_title`
- `consumer_reference_state`
- `consumer_bridge_state`

Recommended detail section:

- `boundary_source_preview.root_spec_id`
- `boundary_source_preview.bounded_context`
- `boundary_source_preview.provides_capabilities`
- `boundary_source_preview.requires_capabilities`
- `boundary_source_preview.evidence_refs`
- `boundary_source_preview.missing_fields_for_full_boundary_spec`

Current status vocabulary:

- `draft_preview_only`
- `ready_for_review`
- `blocked_by_consumer_gap`
- `invalid_export_contract`

## 4. Handoff Packet Contract

Read:

- `runs/specpm_handoff_packets.json`

Use each `entries[]` object as one downstream handoff card.

Required fields for the viewer:

- `handoff_id`
- `export_id`
- `consumer_id`
- `handoff_status`
- `review_state`
- `next_gap`
- `target_consumer`
- `package_identity`
- `preview_reference`
- `transition_packet`
- `transition_packet_validation`
- `contract_errors`

Recommended status badge:

- `handoff_status`

Recommended identity block:

- `package_identity.package_id`
- `package_identity.package_name`
- `package_identity.package_version`

Recommended consumer block:

- `target_consumer.title`
- `target_consumer.profile`
- `target_consumer.local_checkout_hint`
- `target_consumer.identity_verified`

Current status vocabulary:

- `ready_for_handoff`
- `draft_preview_only`
- `blocked_by_preview_gap`
- `invalid_export_contract`

## 5. Local Materialization Contract

Read:

- `runs/specpm_materialization_report.json`

Use each `entries[]` object as one local bundle materialization card.

Required fields for the viewer:

- `export_id`
- `handoff_id`
- `consumer_id`
- `materialization_status`
- `review_state`
- `next_gap`
- `bundle_root`
- `written_files`
- `copied_evidence_refs`
- `missing_evidence_refs`
- `source_handoff`
- `target_consumer`
- `package_identity`

Recommended actions:

- open `bundle_root`
- show written file list
- show copied evidence summary

Current status vocabulary:

- `draft_materialized`
- `materialized_for_review`
- `blocked_by_checkout_gap`
- `blocked_by_consumer_identity`
- `blocked_by_handoff_gap`
- `invalid_handoff_contract`

## 6. Import Preview Contract

Read:

- `runs/specpm_import_preview.json`

Use `import_source` as the global import panel and `entries[]` as one bundle
card per local bundle.

### Global import panel

Required fields:

- `import_source.consumer_id`
- `import_source.profile`
- `import_source.checkout_path`
- `import_source.checkout_status`
- `import_source.identity_verified`
- `import_source.inbox_root`
- `import_source.bundle_count`
- `import_source.next_gap`

### Bundle card

Required fields:

- `bundle_id`
- `bundle_root`
- `consumer_id`
- `import_status`
- `review_state`
- `next_gap`
- `suggested_target_kind`
- `target_consumer`
- `bundle_sources`
- `missing_files`
- `contract_errors`
- `manifest_summary`
- `boundary_summary`
- `handoff_continuity`

Recommended card title:

- `manifest_summary.package_name`
- fallback: `bundle_id`

Recommended status badge:

- `import_status`

Recommended detail block:

- `manifest_summary.package_id`
- `boundary_summary.boundary_spec_id`
- `boundary_summary.boundary_title`
- `boundary_summary.bounded_context`
- `boundary_summary.provides_capabilities`
- `handoff_continuity.handoff_status`
- `handoff_continuity.continuous`

Current status vocabulary:

- `ready_for_review`
- `draft_visible`
- `blocked_by_bundle_gap`
- `invalid_import_contract`

Current target vocabulary:

- `proposal`
- `handoff_candidate`
- `pre_spec`

## 7. Feedback Contract

Read:

- `runs/specpm_feedback_index.json`

Use each `entries[]` object as one downstream feedback card.

Required fields for the viewer:

- `feedback_id`
- `export_id`
- `package_id`
- `package_name`
- `feedback_status`
- `review_state`
- `next_gap`
- `target_consumer`
- `related_specs`
- `observed_checkout_feedback`

Recommended status badge:

- `feedback_status`

Recommended detail block:

- `related_specs.root_spec_id`
- `related_specs.source_spec_ids`
- `observed_checkout_feedback.current_branch`
- `observed_checkout_feedback.upstream_branch`
- `observed_checkout_feedback.tracked_bundle_paths`
- `observed_checkout_feedback.latest_bundle_commit`
- `observed_checkout_feedback.adoption_candidate`

Current status vocabulary:

- `downstream_unobserved`
- `review_activity_observed`
- `adoption_observed_locally`
- `blocked_by_delivery_gap`
- `invalid_feedback_contract`

## 8. Recommended Viewer Model

The viewer should not invent a separate persistence format yet. It should build
one in-memory adapter from the five artifacts.

Recommended normalized package-lifecycle shape:

```json
{
  "package_key": "specgraph.core_repository_facade",
  "export": {
    "status": "draft_preview_only",
    "review_state": "draft_preview_only",
    "next_gap": "review_draft_specpm_boundary"
  },
  "handoff": {
    "status": "draft_preview_only",
    "review_state": "draft_preview_only",
    "next_gap": "review_draft_specpm_boundary"
  },
  "materialization": {
    "status": "draft_materialized",
    "review_state": "draft_materialized",
    "next_gap": "review_draft_materialized_bundle"
  },
  "import": {
    "status": "draft_visible",
    "review_state": "draft_visible",
    "next_gap": "review_draft_specpm_import_preview",
    "suggested_target_kind": "handoff_candidate"
  },
  "feedback": {
    "status": "downstream_unobserved",
    "review_state": "not_observed",
    "next_gap": "observe_specpm_downstream_review"
  }
}
```

Recommended join keys:

- export side: `package_preview.metadata.id`
- handoff side: `package_identity.package_id`
- materialization side: `package_identity.package_id`
- import side: `manifest_summary.package_id`
- feedback side: `package_id`

If a join key is missing, fall back to:

- export/handoff/materialization: `export_id`
- import: `bundle_id`
- feedback: `export_id`

## 9. Recommended Buttons

### `Build Export Preview`

Run:

```bash
python3 tools/supervisor.py --build-specpm-export-preview
```

Then read:

- `runs/specpm_export_preview.json`

### `Build Import Preview`

Run:

```bash
python3 tools/supervisor.py --build-specpm-import-preview
```

Then read:

- `runs/specpm_import_preview.json`

### `Materialize Local Draft Bundle`

Run:

```bash
python3 tools/supervisor.py --materialize-specpm-export-bundles
```

Then read:

- `runs/specpm_materialization_report.json`

This is a real local write into the sibling checkout:

- `SpecPM/.specgraph_exports/<package_id>/`

It is still review-first and is not a git commit workflow.

### `Build SpecPM Feedback`

Run:

```bash
python3 tools/supervisor.py --build-specpm-feedback-index
```

Then read:

- `runs/specpm_feedback_index.json`

## 10. Current Live Mock

At the time this document was written, a live local mock exists for:

- package id: `specgraph.core_repository_facade`

Observed state:

- export: `draft_preview_only`
- handoff: `draft_preview_only`
- materialization: `draft_materialized`
- import: `draft_visible`
- feedback: `downstream_unobserved` or a blocked downstream status depending on
  current checkout state
- suggested target: `handoff_candidate`

This is enough for a viewer to render:

- one package lifecycle card
- export/import preview panels
- local materialization status
- downstream feedback status
- next-gap badges

## 11. Non-Goals For The Viewer

Do not assume yet:

- automatic export into committed `SpecPM` files
- automatic import into canonical `SpecGraph` specs
- cross-repo PR creation
- stable package publication semantics

Current UI should stay honest and use labels such as:

- `Export Preview`
- `Handoff Preview`
- `Local Draft Bundle`
- `Import Preview`
