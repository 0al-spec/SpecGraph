# Proposal Debt Report Viewer API

RFC: SG-RFC-0061
Version: 0.1.0

## Status

Draft proposal

Decision scope: viewer-facing proposal materialization debt artifact and API
contract.

This document does not implement the report, add SpecSpace UI, mutate canonical
specs, change proposal prioritization, or replace existing backlog/runtime
artifacts.

## Source Material

This proposal captures the operator request to expose incoming proposal
materialization debt as a deterministic surface for SpecSpace.

Source draft:

- `docs/archive/proposal_sources/0061_proposal_debt_report_viewer_api.md`

## Summary

SpecGraph should expose proposal materialization debt as a first-class
viewer-facing artifact:

```text
runs/proposal_debt_report.json
```

This report should be derived from existing deterministic surfaces such as
`runs/proposal_runtime_index.json` and `runs/graph_backlog_projection.json`, but
it should present a narrower contract: proposals that still need runtime,
validation, observation, or materialization follow-up.

SpecSpace may consume the report through a stable endpoint such as:

```text
GET /api/v1/proposal-debt
```

The goal is to keep proposal debt observable without requiring SpecSpace to
reconstruct proposal-runtime semantics from lower-level artifacts.

## Problem

SpecGraph is proposal-first. That is correct, but it creates a visible debt
class:

```text
incoming proposal
  -> tracked proposal document
  -> no realized runtime/spec/viewer artifact yet
```

The current graph can already identify this debt through
`proposal_runtime_index.reflective_backlog` and `graph_backlog_projection`, but
those artifacts are broader operational surfaces. They mix proposal runtime
follow-up with process feedback and other backlog domains.

For SpecSpace, this means a clean UI concept such as "Proposal Debt" requires
knowledge of lower-level SpecGraph implementation details.

## Goals

- Define a dedicated proposal debt report artifact.
- Keep the report deterministic and derived.
- Preserve `proposal_runtime_index` as the source of proposal runtime truth.
- Preserve `graph_backlog_projection` as the broad backlog projection.
- Make proposal materialization debt visible as its own viewer/API surface.
- Support grouping by next gap and runtime status.
- Surface missing markers and suggested bounded follow-up actions.
- Avoid exposing raw local paths, logs, prompts, or secrets.

## Non-Goals

- Adding SpecSpace UI in this proposal.
- Auto-implementing proposals.
- Changing proposal priority ordering.
- Replacing `proposal_runtime_index`.
- Replacing `graph_backlog_projection`.
- Treating proposal debt as failure. Proposal debt is an expected consequence of
  proposal-first development.

## Proposed Artifact

```text
runs/proposal_debt_report.json
```

Candidate shape:

```json
{
  "artifact_kind": "proposal_debt_report",
  "schema_version": 1,
  "generated_at": "2026-06-04T00:00:00+00:00",
  "source_artifacts": [
    "runs/proposal_runtime_index.json",
    "runs/graph_backlog_projection.json"
  ],
  "summary": {
    "proposal_count": 60,
    "debt_count": 5,
    "by_next_gap": {
      "runtime_realization": 5
    },
    "by_runtime_status": {
      "partial": 1,
      "untracked": 4
    }
  },
  "entries": [
    {
      "proposal_id": "0056",
      "title": "Supervisor Executor Adapter Gateway",
      "status": "partial",
      "next_gap": "runtime_realization",
      "priority": "medium",
      "source_artifact": "proposal_runtime_index",
      "proposal_path": "docs/proposals/0056_supervisor_executor_adapter_gateway.md",
      "missing_runtime_markers": [
        {
          "path": "tools/supervisor.py",
          "pattern": "def build_supervisor_executor_adapter_index("
        }
      ],
      "suggested_action": "implement_next_bounded_runtime_slice"
    }
  ]
}
```

## Viewer Contract

SpecSpace should be able to render:

- `summary.debt_count` as a badge;
- `summary.by_runtime_status` as grouped counts;
- `summary.by_next_gap` as grouped counts;
- `entries[]` as a proposal debt table;
- `entries[].missing_runtime_markers` in expanded details;
- `entries[].suggested_action` as an advisory next action.

The report should be safe for read-only viewer consumption. It must not contain
raw logs, raw prompts, secrets, local private paths, or provider credentials.

## Relationship To Existing Artifacts

`proposal_runtime_index` remains the detailed source of proposal runtime
posture, marker coverage, validation closure, observation coverage, and
reflective next gaps.

`graph_backlog_projection` remains the broad graph backlog projection across
proposal, process feedback, and future backlog domains.

`proposal_debt_report` is a narrower read model derived from those surfaces for
viewer and operator workflows that specifically ask:

```text
Which proposals have not been materialized yet?
```

## Implementation Plan

1. Add a supervisor build mode:

   ```text
   --build-proposal-debt-report
   ```

2. Generate:

   ```text
   runs/proposal_debt_report.json
   ```

3. Add a Makefile shortcut:

   ```text
   make proposal-debt
   ```

4. Include the artifact in `make viewer-surfaces`.

5. Add a viewer contract document for SpecSpace.

6. Add regression tests for:

   - report shape;
   - grouping counts;
   - missing marker projection;
   - no raw prompt/secrets/local private path leakage;
   - unchanged broad backlog behavior.

## Acceptance Criteria

- `runs/proposal_debt_report.json` is generated deterministically.
- The report lists proposal-only materialization debt without process-feedback
  entries.
- Summary counts match `entries[]`.
- Open proposal gaps remain visible when proposals are only contract-tracked.
- SpecSpace can consume the artifact without reading raw `proposal_runtime_index`
  internals.
- Viewer-facing fields are safe and redacted.

## Risks

- If the report duplicates too much of `proposal_runtime_index`, the two
  artifacts may drift. The report should stay a narrow read model.
- If all backlog semantics move into this report, the broad graph backlog loses
  value. Keep this surface proposal-specific.
- If proposal debt is shown as failure, operators may avoid proposal-first work.
  The UI should frame it as planned materialization debt.
