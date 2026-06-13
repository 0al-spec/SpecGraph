# Ontology Decision Import Preview

RFC: SG-RFC-0115
Version: 0.1.0

## Status

Implemented

Decision scope: read-only import preview for Ontology owner decisions.

This document does not apply owner decisions, import decisions into SpecGraph,
write Ontology packages, update ontology lockfiles, mutate canonical SpecGraph
specs, mark candidate terms accepted, close semantic gates, invoke prompt
agents, parse arbitrary text, or run ontologyc.

## Source Material

This proposal implements the next bounded runtime slice after
`0114_ontology_owner_decision_contract`.

Source draft:

- `docs/archive/proposal_sources/0115_ontology_decision_import_preview.md`

## Summary

SpecGraph now emits a deterministic decision import preview artifact:

```text
runs/ontology_decision_import_preview.json
```

The artifact joins the rich ontology review dashboard with the owner decision
report. It shows whether each owner decision is blocked by the semantic gate,
ready for operator review, rejected, clarification-needed, or unmatched, while
keeping the result as review evidence only.

## Goals

- Add `ontology_decision_import_preview` to the semantic policy layout.
- Define preview states for blocked, ready, rejected, clarification, and
  unmatched owner decisions.
- Preserve owner decision refs, candidate ids, intake ids, matched closed-loop
  evidence ids, source intake state, and required human action.
- Keep apply/import, semantic gate closure, canonical mutation, Ontology package
  writes, lockfile writes, and prompt execution authority disabled.
- Cover preview shape, write path, generated output, authority boundary, and
  registry trace in tests.

## Non-Goals

- Applying owner decisions to SpecGraph specs.
- Marking candidates accepted in canonical SpecGraph state.
- Closing semantic gates.
- Writing Ontology packages or lockfiles.
- Adding SpecSpace mutation UI.

## Runtime Contract

The preview artifact declares:

```json
{
  "artifact_kind": "ontology_decision_import_preview",
  "schema_version": 1,
  "proposal_id": "0115",
  "source_artifacts": {
    "ontology_review_dashboard": "runs/ontology_review_dashboard.json",
    "ontology_owner_decision_report": "runs/ontology_owner_decision_report.json"
  },
  "canonical_mutations_allowed": false,
  "tracked_artifacts_written": false,
  "decision_import_previews": []
}
```

Each preview row records:

- preview id;
- decision id;
- candidate id;
- intake id;
- owner decision state;
- Ontology decision ref;
- matched closed-loop evidence id when present;
- matched source intake state when present;
- preview state;
- required human action;
- import recommendation;
- explicit false import, gate-close, canonical mutation, Ontology package write,
  and lockfile update flags.

## Authority Boundary

The preview may be used by SpecGraph and SpecSpace as a read-only review surface.

The preview may not:

- apply itself;
- import decisions into SpecGraph;
- mark candidates accepted;
- close semantic gates;
- mutate canonical specs;
- write Ontology packages;
- update ontology lockfiles;
- execute prompt agents.

## Acceptance

This slice is complete when:

- `tools/ontology_semantic_control_policy.json` declares
  `ontology_decision_import_preview`;
- `tools/ontology_imports.py` builds and validates the decision import preview;
- `make ontology-imports` writes `runs/ontology_decision_import_preview.json`;
- focused tests cover blocked, unmatched, and read-only preview behavior;
- proposal `0115` is tracked in promotion and runtime registries;
- proposal gates, DocC sync, and focused Python tests pass.

## Next Gap

```text
build_specspace_owner_decision_review_surface
```
