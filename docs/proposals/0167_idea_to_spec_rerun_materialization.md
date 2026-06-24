# 0167 Idea-To-Spec Rerun Materialization

## Status

Implemented

## Summary

The product `idea-to-spec` path can now materialize a review-only candidate
graph preview from a ready rerun preview.

Proposal `0166` shows how accepted clarification answers would affect current
intake and candidate graph state. This slice takes the ready preview and
produces a materialized candidate graph preview where preview-resolved ontology
gaps are removed from node `gaps` and preserved as explicit
`ontology_gap_resolutions`.

## Implementation

The implemented surface is:

- `tools/idea_to_spec_rerun_materialization.py`;
- `make idea-to-spec-rerun-materialization`;
- `runs/idea_to_spec_rerun_materialization.json`;
- regression tests for gap removal, unready preview blocking, unsupported
  candidate graph kind, redaction, and CLI output.

The tool consumes:

```text
runs/idea_to_spec_rerun_preview.json
runs/candidate_spec_graph.json
```

and writes:

```text
runs/idea_to_spec_rerun_materialization.json
```

## Semantics

The materialization report contains:

- a copied candidate graph preview;
- removed ontology gap ids;
- still-unresolved ontology gap ids;
- per-node `ontology_gap_resolutions`;
- a delta summary for review and downstream UI surfaces.

The copied candidate graph preview is not written back to
`runs/candidate_spec_graph.json`. It remains nested in the materialization
report until a later controlled rerun or promotion step decides how to use it.

## Authority Boundary

This proposal does not grant write authority.

It does not:

- execute prompt agents;
- apply answers to source artifacts;
- mutate candidate source artifacts;
- mutate canonical SpecGraph specs;
- write Ontology packages or lockfiles;
- accept ontology terms;
- approve candidate graphs;
- create Git branches or commits;
- open pull requests;
- publish read models;
- add SpecSpace mutation UI.

The output is a review-only materialized preview. It makes the repair loop more
concrete without crossing into canonical graph mutation or Git Service
promotion.

## Validation

- `tests/test_idea_to_spec_rerun_materialization.py`
- `make idea-to-spec-rerun-materialization`

## Follow-Ups

- Add a controlled candidate rerun step that can use a ready materialization
  preview as the next candidate source under explicit operator approval.
- Add a CLI or agent conversation wrapper that fills answer sets from a real
  operator interview.
- Surface request, answer, rerun input, rerun preview, and materialized delta in
  SpecSpace product workspace UX.
