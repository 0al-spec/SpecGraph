# 0159 Ontology-Bound Candidate Graph Seed

## Status

Implemented

## Summary

SpecGraph now has a deterministic ontology-bound seed generator for
`product_idea_to_spec` candidate graphs.

The generator consumes:

- a ready `idea_event_storming_intake`;
- the normalized project-local SpecGraph core ontology IR;
- active ontology/domain/context refs;
- ontology layer refs;
- model applicability refs.

It emits:

- `runs/candidate_spec_graph_seed.json`;
- candidate nodes bound to core ontology classes;
- requirement and acceptance-criterion records for commands, constraints, and
  policies;
- ontology gaps for product-domain terms that are not yet accepted ontology
  terms;
- source-generation findings when the ontology frame or required core classes
  are missing.

This makes Ontology a required foundation of the idea-to-spec candidate path
instead of a loosely related review panel.

## Implementation

This slice adds:

- `tools/ontology_bound_candidate_graph_seed.py`;
- `make ontology-bound-candidate-graph-seed`;
- a new default step inside `make product-workspace-active-candidate`;
- regression tests for ready generic intake, downstream candidate graph
  compatibility, source-generation readiness blocking, duplicate node slug
  disambiguation, stable source-id-derived node slugs, bounded long constraint
  slugs, missing ontology/layer/applicability frame, missing required ontology
  classes, and CLI output.

The deterministic chain is now:

```text
user_idea_intake_source
  -> idea_event_storming_seed
  -> idea_event_storming_intake
  -> ontology_bound_candidate_graph_seed
  -> candidate_spec_graph
  -> pre-SIB/coherence report
  -> repair/materialization/promotion gates
```

The generator maps only structural SpecGraph concepts to authoritative ontology
classes:

- `Spec`;
- `Node`;
- `Requirement`;
- `AcceptanceCriterion`;
- `Constraint`.

Product-domain terms such as actors, commands, domain events, and vocabulary
questions are not auto-accepted into the ontology. They are emitted as
non-blocking ontology gaps so a later owner review can bind, reject, or promote
them explicitly.

The downstream `candidate_spec_graph` builder now blocks seeds whose
`source_generation.findings` contain `review_required` entries or whose
`source_generation.readiness` is not ready. This prevents a seed with ontology
binding errors from becoming `ready_for_pre_sib`, even when the seed reports
readiness blockers separately from findings.

`make product-workspace-active-candidate` treats the generated seed path as an
output by default. Operators who want to supply a prebuilt seed can set
`PRODUCT_WORKSPACE_CANDIDATE_SEED_INPUT=<json>` or the legacy explicit
`PRODUCT_WORKSPACE_CANDIDATE_SEED=<json>` override; in that mode the target
does not regenerate or overwrite the supplied seed.

## Authority Boundary

This proposal does not grant write authority.

It does not:

- execute prompt agents;
- infer a domain model with an LLM;
- mutate canonical SpecGraph specs;
- write Ontology packages or lockfiles;
- accept ontology terms;
- create Git branches or commits;
- approve or promote candidate graphs;
- publish a SpecSpace mutation UI.

The output remains a review-only seed. It may be used by the candidate graph
builder and pre-SIB reports, but it cannot become canonical specification truth
without the existing approval and Git Service promotion gates.

## Validation

- `tests/test_ontology_bound_candidate_graph_seed.py::test_ontology_bound_candidate_seed_builds_ready_seed_from_generic_intake`
- `tests/test_ontology_bound_candidate_graph_seed.py::test_ontology_bound_candidate_seed_feeds_candidate_graph_builder`
- `tests/test_ontology_bound_candidate_graph_seed.py::test_ontology_bound_candidate_seed_disambiguates_duplicate_node_slugs`
- `tests/test_ontology_bound_candidate_graph_seed.py::test_ontology_bound_candidate_seed_uses_stable_command_ids_for_node_slugs`
- `tests/test_ontology_bound_candidate_graph_seed.py::test_ontology_bound_candidate_seed_bounds_long_constraint_node_slugs`
- `tests/test_ontology_bound_candidate_graph_seed.py::test_ontology_bound_candidate_seed_requires_ontology_frame`
- `tests/test_ontology_bound_candidate_graph_seed.py::test_ontology_bound_candidate_seed_requires_core_ontology_classes`
- `tests/test_ontology_bound_candidate_graph_seed.py::test_ontology_bound_candidate_seed_cli_writes_seed`
- `tests/test_candidate_spec_graph.py::test_candidate_spec_graph_blocks_unready_seed_generation_without_findings`
- `tests/test_candidate_spec_graph.py`

## Follow-ups

- Add prompt-side enrichment that can propose richer domain nodes while still
  emitting ontology gaps for unaccepted terms.
- Add a SpecSpace review lane that shows ontology bindings and gaps next to the
  candidate graph.
- Add owner-decision import for accepting, rejecting, or aliasing proposed
  product-domain ontology terms.
