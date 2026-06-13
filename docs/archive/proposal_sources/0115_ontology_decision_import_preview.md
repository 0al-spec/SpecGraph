# Ontology Decision Import Preview

Source artifact class: working draft

## Motivating concern

SpecGraph now has a typed Ontology owner decision report, but it still needs a
deterministic preview that shows how accepted/rejected decisions line up with
closed-loop evidence before any operator considers importing them into
SpecGraph.

## Bounded scope

Add a deterministic `ontology_decision_import_preview` artifact under `runs/`
that joins `ontology_review_dashboard` and `ontology_owner_decision_report` by
candidate id and intake id. The preview records matched evidence ids, source
intake state, owner decision state, preview state, required human action, and
explicit false apply/import/gate-close/canonical-mutation flags. Ignored owner
decisions from the source report remain visible as diagnostics and do not become
import previews.

This slice must not apply owner decisions, import decisions into SpecGraph, mark
candidates accepted, close semantic gates, write Ontology packages, update
ontology lockfiles, mutate canonical specs, invoke prompt agents, parse
arbitrary text, or run ontologyc.

## Acceptance sketch

- Declare the decision import preview layout and contract in
  `tools/ontology_semantic_control_policy.json`.
- Build `runs/ontology_decision_import_preview.json` from the review dashboard
  and owner decision report.
- Classify preview rows as blocked, ready for operator review, rejected,
  clarification-needed, unmatched, or no-decisions.
- Carry ignored owner-decision diagnostics from the source report without
  recommending import.
- Validate the read-only boundary and reject policy or source authority
  expansion.
- Cover artifact shape, write path, generated output, and authority rejection in
  focused tests.
- Register proposal `0115` in promotion and runtime registries.

## Next gap

```text
build_specspace_owner_decision_review_surface
```
