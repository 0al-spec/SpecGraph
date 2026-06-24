# 0161 Artifact-Derived Active Candidate Source Defaults

## Status

Implemented

## Summary

The active `product_idea_to_spec` candidate source now derives its standard
artifact chain from generated `runs/*` artifacts by default.

Proposal `0160` made `make product-workspace-active-candidate` start from a
generic `user_idea_intake_source`, but the final active candidate source still
depended on an explicit active candidate config fixture to name the generated
artifact paths. That was still too close to product-specific orchestration:
Team Decision Log had become data, but a config fixture remained part of the
normal happy path.

This slice makes the config optional. The default active source path is now:

```text
runs/idea_event_storming_intake.json
runs/candidate_spec_graph.json
runs/pre_sib_coherence_report.json
runs/candidate_repair_loop_report.json
runs/candidate_spec_materialization_report.json
runs/idea_to_spec_promotion_gate.json
  -> runs/active_idea_to_spec_candidate.json
```

The active candidate identity still derives from
`idea_event_storming_intake.source_intake.workspace` when available. Config can
still override artifact refs or candidate identity for compatibility and tests,
but it is no longer required for the standard generated flow.

## Implementation

This slice adds:

- built-in standard artifact refs for the active candidate source builder;
- CLI behavior where `tools/active_idea_to_spec_candidate_source.py` can run
  without `--config`;
- `make active-idea-to-spec-candidate-source` and
  `make product-workspace-active-candidate` defaults that omit config args;
- `config_source.required=false` and `config_source.mode` on the active
  candidate artifact;
- `source_derivation` metadata recording identity source, artifact path source,
  config requirement, and the standard artifact paths;
- regression coverage proving that the full product workspace target builds
  through the default artifact paths without an active candidate config.

Explicit config remains supported. When present, it is treated as an override
for nonstandard artifact paths, legacy prepared-seed compatibility, or test
fixtures rather than as the normal product flow.

## Semantics

The active candidate source is now artifact-derived by default:

- generated intake is the authority for workspace identity;
- standard `runs/*` paths are the authority for the local pipeline shape;
- explicit config is optional and visible in `source_derivation`;
- missing or unready upstream artifacts still produce review findings rather
  than silently publishing an active candidate.

This means a new product idea can replace Team Decision Log by changing
`PRODUCT_WORKSPACE_IDEA_SOURCE` while keeping the same Make target and active
candidate source defaults.

## Authority Boundary

This proposal does not grant write authority.

It does not:

- execute prompt agents;
- infer missing product semantics with an LLM;
- mutate canonical SpecGraph specs;
- write Ontology packages or lockfiles;
- accept ontology terms;
- approve candidate graphs;
- create Git branches or commits;
- open pull requests;
- publish read models;
- add SpecSpace mutation UI.

The output remains a public-safe, review-only handoff surface until the
existing approval and Git Service promotion boundaries accept it.

## Validation

- `tests/test_active_idea_to_spec_candidate_source.py::test_active_candidate_source_builds_from_default_artifact_paths_without_config`
- `tests/test_product_workspace_active_candidate_runner.py::test_product_workspace_active_candidate_default_paths_do_not_require_config`
- `make product-workspace-active-candidate`

## Follow-Ups

- Add prompt-side/event-storming capture that produces
  `user_idea_intake_source` from an operator conversation.
- Make repair suggestions more actionable for ontology gaps and promotion
  blockers.
- Continue Git Service promotion/read-model publication after explicit
  candidate approval.
