# Product Workspace Initialization Viewer Contract

## Purpose

`runs/product_workspace_initialization.json` is the reviewable receipt emitted by
the SpecGraph-owned product workspace initializer. SpecSpace and Platform should
use it to decide whether a workspace was initialized safely instead of inferring
success from directory presence alone.

## Source

The artifact is written inside the target product workspace:

```text
runs/product_workspace_initialization.json
```

It is produced by:

```bash
python3 tools/supervisor.py \
  --init-product-workspace \
  --project-id swiftui-calculator \
  --display-name "SwiftUI Calculator" \
  --workspace-root ../SwiftUICalculator \
  --root-intent "Build a SwiftUI calculator for iOS and macOS."
```

## Boundary

- SpecGraph owns `specgraph.project.yaml`, initialization validation, safety
  rules, and the initialization report shape.
- Platform may call the initializer and record the workspace in its catalog
  after the report is successful.
- SpecSpace may render the report as a workspace status card.
- The initializer must not mutate SpecGraph core specs, tools, policies, tests,
  or self-evolution surfaces.
- Root intent capture is pre-canonical and does not create canonical spec nodes.

## Required Fields

```json
{
  "artifact_kind": "product_workspace_initialization",
  "schema_version": 1,
  "canonical_mutations_allowed": false,
  "tracked_artifacts_written": false,
  "project": {
    "project_id": "swiftui-calculator",
    "display_name": "SwiftUI Calculator",
    "governance_profile": "product_workspace"
  },
  "workspace": {
    "root": ".",
    "root_reference": "workspace_relative",
    "local_input_path_persisted": false,
    "created_paths": [],
    "existing_paths": [],
    "required_paths": []
  },
  "root_intent": {
    "status": "captured|captured_existing|not_provided|blocked",
    "artifact_path": ".specgraph/root_intent.md",
    "content_sha256": "...",
    "next_gap": "review_before_canonical_materialization"
  },
  "validation_findings": [],
  "review_state": "ready_for_review|blocked",
  "next_gap": "review_before_first_spec_materialization",
  "summary": {
    "status": "initialized|ready|blocked",
    "project_id": "swiftui-calculator",
    "governance_profile": "product_workspace",
    "root_intent_status": "captured",
    "created_path_count": 5,
    "validation_finding_count": 0,
    "next_gap": "review_before_first_spec_materialization"
  }
}
```

Proposal `0211` adds `workspace_binding_evidence` to the same receipt. The
evidence carries workspace identity, workspace-relative layout refs, the
`specgraph.project.yaml` digest, repository/worktree identity hints, and a
stable evidence digest. Platform may pin it into a durable workspace binding;
SpecSpace should consume only a public-safe projection and must not infer local
paths from the route.

## UI Guidance

- Show `summary.status` as the primary status.
- Show `project.project_id`, `project.display_name`, and
  `project.governance_profile`.
- Treat `workspace.local_input_path_persisted: false` as a safety guarantee that
  absolute local paths were not written into the shared report.
- Show `root_intent.status`, but never require raw root intent text from this
  report.
- Render `validation_findings[]` as repairable diagnostics.
- If `review_state` is `blocked`, do not offer canonical materialization actions.

## Non-Goals

- No SpecPM import materialization.
- No Platform catalog mutation.
- No SpecSpace project switcher implementation.
- No canonical spec node creation.
