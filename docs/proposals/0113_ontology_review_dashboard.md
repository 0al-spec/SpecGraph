# Ontology Review Dashboard

RFC: SG-RFC-0113
Version: 0.1.0

## Status

Implemented

Decision scope: deterministic read-only review dashboard derived from existing
Ontology semantic review, gate, intake, and closed-loop evidence artifacts.

This document does not import Ontology owner decisions, write Ontology packages,
update ontology lockfiles, mutate canonical SpecGraph specs, accept candidate
terms, close semantic gates, invoke prompt agents, parse arbitrary text, or run
ontologyc.

## Source Material

This proposal implements the next bounded runtime slice after
`0111_ontology_closed_loop_evidence` and follows the occupied `0112` executor
analysis report review outcome proposal.

Source draft:

- `docs/archive/proposal_sources/0113_ontology_review_dashboard.md`

## Summary

SpecGraph now emits a richer review dashboard artifact:

```text
runs/ontology_review_dashboard.json
```

The artifact aggregates the semantic review surface, supervisor semantic gate,
Ontology delta draft intake, and closed-loop evidence into a single read-only
projection for SpecGraph and SpecSpace dashboards.

## Goals

- Add `ontology_review_dashboard` to the semantic policy layout.
- Define a dashboard contract with source artifact kinds, display sections,
  status states, and consumer boundary.
- Build status summary from the supervisor gate, draft intake, and closed-loop
  evidence.
- Surface blocking items, review-required items, delta candidates, draft
  requests, closed-loop entries, and review actions in one artifact.
- Preserve source artifact refs and all authority boundary flags.
- Cover artifact shape, write path, source authority rejection, and registry
  trace in tests.

## Non-Goals

- Importing accepted/rejected Ontology owner decisions.
- Applying owner decisions back into SpecGraph.
- Writing Ontology package drafts.
- Updating ontology lockfiles.
- Marking candidate terms accepted.
- Closing semantic gates.
- Adding SpecSpace mutation UI.

## Runtime Contract

The dashboard artifact declares:

```json
{
  "artifact_kind": "ontology_review_dashboard",
  "schema_version": 1,
  "proposal_id": "0113",
  "source_artifacts": {
    "semantic_review_surface": "runs/ontology_semantic_review_surface.json",
    "supervisor_semantic_gate": "runs/ontology_supervisor_semantic_gate.json",
    "ontology_delta_draft_intake": "runs/ontology_delta_draft_intake.json",
    "ontology_closed_loop_evidence": "runs/ontology_closed_loop_evidence.json"
  },
  "canonical_mutations_allowed": false,
  "tracked_artifacts_written": false,
  "status_summary": {}
}
```

The dashboard status can be:

- `blocked_by_semantic_gate`;
- `pending_ontology_owner_decision`;
- `review_pending`;
- `clear`;
- `no_candidates`.

## Authority Boundary

The dashboard is a review projection only.

It may be read by SpecGraph and SpecSpace review dashboards.

It may not:

- import owner decisions;
- write Ontology packages;
- update ontology lockfiles;
- mutate canonical specs;
- mark candidate terms accepted;
- close semantic gates;
- execute prompt agents;
- become canonical authority for ontology deltas.

## Acceptance

This slice is complete when:

- `tools/ontology_semantic_control_policy.json` declares
  `ontology_review_dashboard`;
- `tools/ontology_imports.py` builds `ontology_review_dashboard` from the
  semantic review surface, supervisor semantic gate, delta draft intake, and
  closed-loop evidence artifacts;
- `make ontology-imports` writes `runs/ontology_review_dashboard.json`;
- focused tests cover dashboard shape, write path, and authority boundary;
- proposal `0113` is tracked in promotion and runtime registries;
- proposal gates, DocC sync, and focused Python tests pass.

## Next Gap

```text
build_specspace_rich_ontology_review_panel
```
