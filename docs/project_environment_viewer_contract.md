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
    },
    "enforcement_summary": {
      "allowed_target_domains": ["specgraph_core", "project_graph"],
      "forbidden_target_domains": [],
      "allowed_mutation_roots": ["specs/", "docs/proposals/", "runs/"],
      "forbidden_mutation_roots": [],
      "default_next_move_behavior": "allow_profile_eligible_moves",
      "blocked_move_status": "not_applicable",
      "review_feedback_routing": "specgraph_core_allowed",
      "upstream_export_mode": "not_required"
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
- Use `viewer_projection.enforcement_summary` for operator details. It is the
  viewer-facing contract for allowed/forbidden target domains, mutation roots,
  feedback routing, and default next-move behavior.
- In `product_workspace`, display
  `blocked_move_status=blocked_by_governance_profile` as policy enforcement,
  not as a runtime crash.
- Do not show absolute local paths; all workspace paths are expected to be
  repo-relative.

## Boundaries

This artifact is read-only. It describes the active project/workspace authority
boundary; it does not itself grant mutation authority.
