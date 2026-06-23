# 0155 Product Workspace Active Candidate Source

## Status

Implemented

## Summary

SpecGraph now has a deterministic active candidate source for product
`product_idea_to_spec` workspaces. Team Decision Log is the first fixture and
public pilot carried by the config data, not a separate system-level flow.

The source links the existing idea-to-spec artifacts:

- `idea_event_storming_intake`;
- `candidate_spec_graph`;
- `pre_sib_coherence_report`;
- `candidate_repair_loop_report`;
- `candidate_spec_materialization_report`;
- `idea_to_spec_promotion_gate`.

It emits:

- `runs/active_idea_to_spec_candidate.json`;
- stable candidate/workspace identity from the active candidate config;
- product workspace authority metadata;
- public-safe artifact refs and digests;
- readiness findings when the source is incomplete, placeholder-derived, or
  points at the wrong repository role.

## Implementation

This slice adds:

- `tools/active_idea_to_spec_candidate_source.py`;
- `make active-idea-to-spec-candidate-source`;
- `make product-workspace-active-candidate`;
- product workspace event-storming and candidate graph seed fixtures;
- static publish behavior that preserves real handoff surfaces only when the
  active source is ready;
- regression tests for ready source publication and placeholder blocking.

The product workspace target runs the deterministic chain. Team Decision Log is
the default fixture data for that target, not a separate script, Make target, or
runtime branch:

```text
event-storming seed
  -> idea_event_storming_intake
  -> candidate_spec_graph
  -> pre-SIB/coherence report
  -> repair-loop preview
  -> materialized candidate spec previews
  -> promotion gate
  -> active candidate source
```

## Authority Boundary

This proposal does not grant write authority.

It does not:

- execute prompt agents;
- mutate candidate source artifacts through SpecSpace;
- mutate canonical SpecGraph specs;
- write Ontology packages or lockfiles;
- accept ontology terms;
- create Git branches or commits;
- open pull requests;
- publish read models;
- merge or accept candidate specs.

The active candidate source requires `product_workspace` governance and
`product_spec_workspace` repository role. It rejects `specgraph_bootstrap`
targets.

## Public Publishing

When no active source exists, the static bundle continues to publish stable
Platform handoff placeholders with `placeholder_reason: no_active_candidate`.

When `runs/active_idea_to_spec_candidate.json` is ready, the bundle builder:

- publishes that active source;
- leaves real `candidate_spec_materialization_report.json` and
  `idea_to_spec_promotion_gate.json` artifacts intact;
- records the active source in `artifact_manifest.json`;
- still redacts local paths and scans public JSON for secret-like content.

## Validation

- `tests/test_active_idea_to_spec_candidate_source.py::test_active_candidate_source_builds_ready_report`
- `tests/test_active_idea_to_spec_candidate_source.py::test_active_candidate_source_rejects_public_placeholder`
- `tests/test_active_idea_to_spec_candidate_source.py::test_active_candidate_source_rejects_bootstrap_repository_role`
- `tests/test_static_artifact_bundle.py::test_refresh_publish_surfaces_preserves_ready_active_candidate_handoff`
- `tests/test_static_artifact_bundle.py::test_build_public_bundle_publishes_ready_active_candidate_source`

## Follow-ups

- SpecSpace should keep product workspace routes generic so any safe product
  workspace slug can read the candidate artifact surface.
- Platform should pass product workspace artifact sources through generic
  workspace metadata, not through pilot-specific deploy flags.
