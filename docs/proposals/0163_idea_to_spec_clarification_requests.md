# 0163 Idea-To-Spec Clarification Requests

## Status

Implemented

## Summary

The product `idea-to-spec` path now has a unified clarification-request surface.

Earlier slices created deterministic artifacts for raw intake, event-storming
intake, ontology-bound candidate graph seed generation, candidate graph
construction, pre-SIB/coherence checks, and repair previews. Those reports could
say that a candidate needed review, but downstream users still had to inspect
several artifacts to understand the next question or action.

This slice adds `idea_to_spec_clarification_requests` as the read-only bridge
between reports and the future answer loop.

## Implementation

The implemented surface is:

- `tools/idea_to_spec_clarification_requests.py`;
- `make idea-to-spec-clarification-requests`;
- `runs/idea_to_spec_clarification_requests.json`;
- `make product-workspace-active-candidate`, which now writes the clarification
  artifact after the candidate repair loop.

The builder consumes any available standard idea-to-spec artifacts:

```text
runs/user_idea_intake_session.json
runs/idea_event_storming_intake.json
runs/candidate_spec_graph.json
runs/pre_sib_coherence_report.json
runs/candidate_repair_loop_report.json
explicitly supplied ontology_gap_review_workflow.json
```

Missing optional source artifacts are recorded as missing source inputs rather
than treated as fatal. A completely empty source set remains review-required.
The ontology gap review workflow is intentionally explicit rather than a default
input so a product workspace does not accidentally inherit bootstrap or legacy
SpecGraph gap groups.

## Semantics

Each request is a stable, typed unit:

```json
{
  "id": "clarification.repair.repair-review-unresolved-gaps",
  "kind": "ontology_gap",
  "severity": "blocking",
  "question": "How should ontology context be resolved for candidate_graph.gaps?",
  "target_artifact": "runs/candidate_repair_loop_report.json",
  "target_ref": "candidate_graph.gaps",
  "blocks": ["pre_sib_unresolved_gaps"],
  "suggested_answer_shape": "bind_existing_term | alias | propose_project_local_term | reject | defer",
  "suggested_actions": [
    "bind_existing_term",
    "alias",
    "propose_project_local_term",
    "reject",
    "defer"
  ],
  "source_findings": [],
  "status": "open"
}
```

The artifact intentionally distinguishes:

- blocking questions that prevent candidate promotion;
- review-required ontology or coherence work;
- advisory preview repairs that are already applied to a review-only preview.

It does not accept answers. Proposal `0164` is reserved for the answer contract
that can feed a subsequent deterministic pipeline rerun.

## Authority Boundary

This proposal does not grant write authority.

It does not:

- execute prompt agents;
- infer missing product semantics with an LLM;
- mutate candidate source artifacts through SpecSpace;
- mutate canonical SpecGraph specs;
- write Ontology packages or lockfiles;
- accept ontology terms;
- approve candidate graphs;
- create Git branches or commits;
- open pull requests;
- publish read models;
- add SpecSpace mutation UI.

The output is a public-safe review artifact. It strips raw prompt/operator trace
fields from copied evidence and exposes only source refs, finding ids, target
refs, suggested answer shapes, and suggested action names.

## Validation

- `tests/test_idea_to_spec_clarification_requests.py`
- `make idea-to-spec-clarification-requests`
- `make product-workspace-active-candidate`

## Follow-Ups

- Add `idea_to_spec_clarification_answers` as the typed answer surface.
- Feed accepted answers into the next deterministic intake/candidate rerun.
- Make ontology gap review actions explicit: bind, alias, propose
  project-local term, reject, or defer.
- Surface clarification requests in SpecSpace product workspace UX.
