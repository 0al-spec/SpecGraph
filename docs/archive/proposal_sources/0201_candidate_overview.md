# 0201 Candidate Overview

## Status

Draft / runtime slice.

## Summary

Add a public-safe `runs/candidate_overview.json` artifact that turns the current
idea-to-spec candidate lifecycle into a compact narrative and navigation surface
for SpecSpace.

The overview is read-only. It summarizes the active product intent, event
storming frame, candidate nodes, topology, repair state, Idea Maturity state,
project-local ontology review state, and the next safe operator action. It does
not infer new product semantics, execute prompt agents, apply repair answers, or
mutate canonical artifacts.

## Problem

SpecSpace can already read many product workspace artifacts:

- `idea_event_storming_intake.json`
- `candidate_spec_graph.json`
- `repaired_candidate_spec_graph.json`
- `idea_maturity_metrics_report.json`
- repair session journals
- project-local ontology review artifacts
- repaired promotion handoff reports

This is powerful but hard to explain to a product user. A user needs a single
first-pass answer to:

- what did the system understand;
- what entities/actions/events are in the bounded context;
- whether the graph is initial or repaired;
- what still blocks approval;
- where to go next.

Reconstructing that narrative independently in every downstream consumer would
duplicate policy and increase drift.

## Decision

Introduce `tools/candidate_overview.py` and `make candidate-overview`.

The tool reads existing public-safe lifecycle artifacts and writes:

```text
runs/candidate_overview.json
```

The artifact contains:

- `candidate` identity and route;
- `narrative.product_intent`;
- `narrative.understood_scope`;
- `narrative.readiness`;
- `sections.event_storming`;
- `sections.candidate_nodes`;
- `sections.topology`;
- `sections.repair`;
- `sections.idea_maturity`;
- `sections.project_local_ontology`;
- `next_action`;
- source artifact refs and summaries;
- read-only authority and privacy boundaries.

## Authority Boundary

The overview must keep these capabilities false:

- execute prompt agents;
- mutate candidate artifacts;
- mutate canonical specs;
- write Ontology packages or lockfiles;
- accept Ontology terms;
- approve candidate graphs;
- create branches or commits;
- open pull requests;
- publish read models.

If a source artifact claims one of those authorities, the overview becomes
`candidate_overview_review_required`.

## Privacy Boundary

The overview must not publish:

- raw idea text;
- raw prompts;
- raw model output;
- raw operator notes;
- private operator state;
- machine-local paths or secret-like values.

It may publish sanitized summaries, counts, source refs, and public-safe evidence
refs.

## Acceptance Criteria

- `make candidate-overview` writes `runs/candidate_overview.json`.
- The overview prefers `repaired_candidate_spec_graph.json` when present.
- The overview falls back to `candidate_spec_graph.json` when no repaired graph
  is present.
- Event-storming and topology summaries are present.
- Repair readiness and Idea Maturity summary are present.
- Project-local ontology review summary is present.
- Source authority expansion is reported as a review-required finding.
- Raw/private fields are removed or redacted.
- `make publish-bundle` refreshes and publishes the overview when public-safe.

## Non-goals

- Do not create a new score.
- Do not replace Idea Maturity.
- Do not apply repair decisions.
- Do not accept project-local ontology terms.
- Do not generate new candidate graph nodes.
- Do not execute prompt agents.
- Do not trigger Platform or Git Service.

