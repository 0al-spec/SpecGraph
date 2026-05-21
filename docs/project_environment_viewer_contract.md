# Project Environment Viewer Contract

`runs/project_environment.json` is the viewer-facing source for the active
SpecGraph workspace governance profile.

SpecSpace must not infer the profile from repository name, URL shape, or local
filesystem paths.

## Required Fields

```json
{
  "artifact_kind": "project_environment",
  "schema_version": 1,
  "project": {
    "project_id": "specgraph",
    "display_name": "SpecGraph Bootstrap",
    "governance_profile": "self_hosted_bootstrap",
    "requested_governance_profile": "self_hosted_bootstrap",
    "active_profile_known": true
  },
  "viewer_projection": {
    "environment_badge": {
      "mode_label": "Self-hosted bootstrap",
      "project_id": "specgraph",
      "governance_profile": "self_hosted_bootstrap",
      "requested_governance_profile": "self_hosted_bootstrap",
      "core_state": "proposal_first",
      "self_evolution": "enabled",
      "project_graph": "writable",
      "status": "valid"
    }
  },
  "summary": {
    "status": "valid",
    "core_locked": false,
    "self_evolution_enabled": true,
    "next_gap": "none"
  }
}
```

## UI Guidance

- Show a compact environment banner from
  `viewer_projection.environment_badge`.
- Treat `summary.status != "valid"` as an operator attention state, not as a
  fatal viewer error.
- In `product_workspace`, display core state as locked and self-evolution as
  disabled.
- If `governance_profile` is `unknown_profile_fail_closed`, display a warning
  and show `requested_governance_profile` in details. Treat the core as locked.
- Do not show absolute local paths; all workspace paths are expected to be
  repo-relative.

## Boundaries

This artifact is read-only. It describes the active project/workspace authority
boundary; it does not itself grant mutation authority.
