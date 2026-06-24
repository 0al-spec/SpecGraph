# 0166 Idea-To-Spec Rerun Preview

## Status

Implemented

## Summary

The product `idea-to-spec` path can now preview how accepted clarification
answers would affect the next deterministic run.

Proposal `0165` emits a review-only rerun input overlay. This slice consumes
that overlay together with the current event-storming intake and candidate spec
graph, then produces a public-safe preview of active-frame changes,
event-storming additions, ontology gap resolutions, and candidate review hints.

## Implementation

The implemented surface is:

- `tools/idea_to_spec_rerun_preview.py`;
- `make idea-to-spec-rerun-preview`;
- `runs/idea_to_spec_rerun_preview.json`;
- regression tests for ontology gap resolution preview, unready rerun input,
  active-frame merge/redaction, and CLI output.

The tool consumes:

```text
runs/idea_to_spec_answer_rerun_input.json
runs/idea_event_storming_intake.json
runs/candidate_spec_graph.json
```

and writes:

```text
runs/idea_to_spec_rerun_preview.json
```

## Semantics

The preview:

- merges accepted active-frame hints into an active-frame preview;
- appends accepted event-storming hints into an event-storming preview;
- matches ontology review hints against candidate graph ontology gaps;
- reports preview-resolved and still-unresolved ontology gaps;
- carries candidate review hints for acceptance criteria, graph edges, and
  claim review decisions.

Matching ontology-gap decisions remains preview-only. A project-local term,
binding, alias, rejection, or deferral can resolve the preview state for a gap,
but this does not accept the term into an ontology package and does not mutate
the candidate graph.

If the rerun input artifact is not ready, or any source artifact has an
unsupported contract, the preview remains blocked with review findings.

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

The output is a review-only preview. A later proposal may define a deterministic
rerun consumer that materializes a new candidate from the approved preview.

## Validation

- `tests/test_idea_to_spec_rerun_preview.py`
- `make idea-to-spec-rerun-preview`

## Follow-Ups

- Add a deterministic intake/candidate rerun consumer that can materialize a new
  candidate from a ready preview.
- Add a CLI or agent conversation wrapper that fills answer sets from a real
  operator interview.
- Surface request, answer, rerun input, and rerun preview state in SpecSpace
  product workspace UX.
