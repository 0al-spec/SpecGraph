# Spec Activity Feed Viewer Contract

This document defines the ContextBuilder/viewer-facing contract for
`runs/spec_activity_feed.json`.

The feed exists because node activity is broader than canonical YAML
`updated_at` changes. Trace/evidence baselines, proposal-lane updates,
implementation-work emissions, and review-feedback fixes can all update a
spec's practical state without editing `specs/nodes/*.yaml`.

## 1. Source Artifact

Build command:

```bash
python3 tools/supervisor.py --build-spec-activity-feed
```

Make shortcut:

```bash
make spec-activity
```

The artifact is also refreshed by:

```bash
make viewer-surfaces
```

Read:

- `runs/spec_activity_feed.json`

The artifact is a derived read model. It is not canonical graph truth and it
must not mutate specs, proposal-lane nodes, or runtime code.

## 2. Recommended ContextBuilder Endpoint

Recommended route:

```text
GET /api/spec-activity?limit=N&since=ISO
```

Server behavior:

- read only `SpecGraph/runs/spec_activity_feed.json`;
- return the artifact as raw `data` inside the same metadata envelope used by
  other SpecGraph runs artifacts;
- apply optional `limit` and `since` filters on `data.entries[]` if needed;
- return `404` when the artifact has not been built;
- return `422` when the JSON cannot be parsed;
- return `503` when the server is not configured with a SpecGraph root.

The viewer should not run `git log` or infer spec activity from path
heuristics. SpecGraph owns the mapping from repository activity to spec-node
activity.

## 3. Top-Level Fields

Stable fields:

- `artifact_kind`
- `schema_version`
- `generated_at`
- `source_artifacts`
- `entry_count`
- `entries`
- `summary`
- `viewer_projection`
- `viewer_contract`
- `canonical_mutations_allowed`
- `tracked_artifacts_written`

Expected shape:

```json
{
  "artifact_kind": "spec_activity_feed",
  "schema_version": 1,
  "generated_at": "2026-05-08T00:00:00+00:00",
  "source_artifacts": {
    "policy": "tools/spec_activity_feed_policy.json",
    "git_paths": []
  },
  "entry_count": 0,
  "entries": [],
  "summary": {
    "entry_count": 0,
    "event_type_counts": {},
    "spec_event_counts": {},
    "prompt_overlay": {
      "scope": "visible_entries",
      "label": "Prompt drift in visible runs",
      "status_counts": {},
      "drift_group_count": 0
    }
  },
  "viewer_projection": {
    "event_type": {},
    "spec_id": {},
    "prompt_overlay": {
      "scope": "visible_entries",
      "label": "Prompt drift in visible runs",
      "status_counts": {},
      "drift_group_count": 0,
      "drift_groups": []
    },
    "named_filters": {}
  },
  "viewer_contract": {
    "contract_doc": "docs/spec_activity_feed_viewer_contract.md",
    "recommended_endpoint": "GET /api/spec-activity?limit=N&since=ISO",
    "source_artifact": "runs/spec_activity_feed.json"
  },
  "canonical_mutations_allowed": false,
  "tracked_artifacts_written": false
}
```

`entry_count`, `summary.entry_count`, and `entries.length` should agree.

## 4. Entry Contract

Each `entries[]` item is one normalized activity event.

Stable fields:

- `event_id`
- `event_type`
- `spec_id`
- `title`
- `occurred_at`
- `summary`
- `source_kind`
- `source_ref`
- `source_paths`
- `prompt_overlay_provenance`
- `viewer`

`spec_id` is empty for graph-level process events that cannot be honestly
attached to a single canonical spec node, such as review-feedback records that
do not mention an `SG-SPEC-####` id. Those events remain available through
`viewer_projection.event_type` and `viewer_projection.named_filters`.

Expected entry:

```json
{
  "event_id": "spec_activity::abc123",
  "event_type": "trace_baseline_attached",
  "spec_id": "SG-SPEC-0026",
  "title": "SpecGraph - Reflective Mechanics Integration",
  "occurred_at": "2026-05-07T21:00:00+00:00",
  "summary": "Attach SG-SPEC-0026 trace baseline",
  "source_kind": "git_commit",
  "source_ref": {
    "sha": "abcdef...",
    "short_sha": "abcdef1",
    "subject": "Attach SG-SPEC-0026 trace baseline"
  },
  "source_paths": [
    "tools/spec_trace_registry.json",
    "tools/runtime_evidence_registry.json"
  ],
  "prompt_overlay_provenance": {
    "status": "enabled",
    "source_kind": "profile",
    "display_label": "default",
    "drift_key": "profile|default|...",
    "prompt_profile_id": "default",
    "prompt_extension_path": "tools/supervisor_prompts/default.md",
    "prompt_extension_sha256": "abcdef...",
    "prompt_overlay_authority": "project",
    "core_prompt_overridden": false,
    "policy_reference": {
      "artifact_path": "tools/supervisor_prompt_policy.json",
      "artifact_sha256": "123456...",
      "version": 1
    },
    "non_overridable_invariants": []
  },
  "viewer": {
    "tone": "trace",
    "label": "trace baseline attached"
  }
}
```

## 4.1. Prompt Overlay Projection

`entries[].prompt_overlay_provenance` is a viewer-facing projection of the
supervisor prompt overlay provenance. It is intentionally safe to render:

- raw prompt text is never included;
- paths are repo-relative or omitted;
- `status` is a derived summary field for UI badges;
- `core_prompt_overridden` remains as the source diagnostic fact;
- drift grouping uses `drift_key`, not the display label.

Per-entry provenance is only populated when the activity source can be tied to an
exact supervisor run id. SpecGraph may use an explicit activity `source_run_id`
or the `last_run_id` captured in the spec file at the activity commit. It must
not silently fall back to the latest current run for the same spec id. If no
exact run id is available, render `legacy_unknown` with
`reason: "missing_exact_run_link"`. If an exact run is visible but has no
prompt overlay provenance, render `legacy_unknown` with
`reason: "legacy_run_without_provenance"`.

Prompt drift summaries are run-scoped. Entries without an exact run id are still
renderable as `legacy_unknown`, but they are excluded from
`summary.prompt_overlay.status_counts` and drift groups. If several visible
activity entries point to the same run id, that run is counted once.

Statuses:

- `core`: provenance explicitly says no overlay was enabled.
- `enabled`: a profile or extension-file overlay was used and passed projection
  safety checks.
- `legacy_unknown`: provenance is missing, usually because the run predates this
  contract or no matching run log is visible.
- `unsafe`: the projection detected an unsafe or malformed state such as
  `core_prompt_overridden !== false`, raw prompt text, missing required hashes,
  or non-repo-relative paths.

Source kinds:

- `core`
- `profile`
- `extension_file`
- `unknown`

Stable drift key:

```text
source_kind + prompt_profile_id + prompt_extension_sha256 + policy_reference.artifact_sha256
```

SpecSpace should display compact labels from `display_label`, but should group
prompt drift by `drift_key`.

`display_label` is safe user-facing copy and can be shown as-is. `status` is the
semantic/tone field for badge styling, filtering, warnings, and tests.

For compact UI:

- show short hashes such as `abc123...`;
- keep full hashes for tooltip/copy actions;
- treat group-level `status`/`dominant_status` as the worst status in that
  `drift_key` group, with `unsafe` winning over enabled/core/legacy states;
- use group-level `status_counts` when showing mixed-state groups;
- never display raw prompt snippets.

The prompt drift summary is scoped to the currently visible feed entries:

```json
{
  "scope": "visible_entries",
  "label": "Prompt drift in visible runs",
  "status_counts": {
    "enabled": 3,
    "legacy_unknown": 42
  },
  "run_count": 45,
  "drift_group_count": 2,
  "drift_groups": [
    {
      "drift_key": "profile|default|...",
      "display_label": "default",
      "status": "enabled",
      "dominant_status": "enabled",
      "source_kind": "profile",
      "status_counts": {
        "enabled": 1
      },
      "event_ids": ["spec_activity::abc123"],
      "event_count": 1
    }
  ]
}
```

Because this scope is visible/currently loaded entries, UI copy should say
`Prompt drift in visible runs`, not global prompt drift.

Top-level `summary.prompt_overlay` intentionally stays compact and omits
per-event ids. Detailed drift groups live under
`viewer_projection.prompt_overlay`.

## 5. Event Types

Initial event vocabulary:

- `canonical_spec_updated`
- `trace_baseline_attached`
- `evidence_baseline_attached`
- `proposal_emitted`
- `proposal_promotion_trace_attached`
- `proposal_runtime_realization_attached`
- `implementation_work_emitted`
- `review_feedback_applied`
- `stack_only_merge_observed`

Viewer tone guidance:

- `canonical_spec_updated` -> existing node/spec accent
- `trace_baseline_attached` -> trace/evidence accent
- `evidence_baseline_attached` -> trace/evidence accent
- `proposal_emitted` -> proposal accent
- `proposal_promotion_trace_attached` -> proposal accent
- `proposal_runtime_realization_attached` -> proposal accent
- `implementation_work_emitted` -> implementation/work accent
- `review_feedback_applied` -> process/review accent
- `stack_only_merge_observed` -> process/review accent

`proposal_promotion_trace_attached` is emitted when commits update
`tools/proposal_promotion_registry.json` or archived proposal source drafts
under `docs/archive/proposal_sources/`.

`proposal_runtime_realization_attached` is emitted when commits update
`tools/proposal_runtime_registry.json`.

These proposal lifecycle events may have an empty `spec_id` because they often
represent graph-level proposal/process evidence rather than a direct canonical
spec-node edit. Viewers should render them as graph-level activity rows, not
drop them.

`stack_only_merge_observed` is a graph-level process warning: the commit was
reachable from a remote stacked branch but not yet from `origin/main` when the
feed was generated. Treat it as delivery-topology evidence, not as a canonical
spec mutation.

`stack_only_merge_observed` entries include a `merge_landing` object:

```json
{
  "status": "stack_only_merge_observed",
  "reachable_remote_branches": ["origin/codex/supervisor-run-36"],
  "main_contains_commit": false
}
```

`merge_landing.reachable_remote_branches` lists non-main remote branches that
contain the merge commit. `merge_landing.main_contains_commit` is `false` for
this event because the same commit was not reachable from `origin/main` during
feed generation. The object is present only on `stack_only_merge_observed`
events.

Unknown future event types should be displayed as neutral activity rows rather
than treated as parse failures.

## 6. Viewer Integration Guidance

Once this artifact exists, ContextBuilder can add a third source toggle such as
`Activity` next to the existing node-update and run-update sources.

Recommended behavior:

- default to `Activity` when the feed is present;
- keep existing YAML/recent-run modes as narrower diagnostic views;
- use `viewer_projection.spec_id` to attach recent events to node detail panels;
- use `viewer_projection.event_type` for filters and legend counts;
- show `generated_at` or file `mtime` so stale feeds are visible.

The current inline notice in ContextBuilder can be removed once the Activity
source is available and selected by default.
