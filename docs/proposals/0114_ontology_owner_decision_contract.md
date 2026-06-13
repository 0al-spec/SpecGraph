# Ontology Owner Decision Contract

RFC: SG-RFC-0114
Version: 0.1.0

## Status

Implemented

Decision scope: typed read-only owner decision report for accepted/rejected
Ontology owner decisions.

This document does not import owner decisions into SpecGraph, write Ontology
packages, update ontology lockfiles, mutate canonical SpecGraph specs, mark
candidate terms accepted, close semantic gates, invoke prompt agents, parse
arbitrary text, or run ontologyc.

## Source Material

This proposal implements the next bounded runtime slice after
`0113_ontology_review_dashboard`.

Source draft:

- `docs/archive/proposal_sources/0114_ontology_owner_decision_contract.md`

## Summary

SpecGraph now emits a deterministic owner decision report artifact:

```text
runs/ontology_owner_decision_report.json
```

The artifact provides a typed contract for Ontology-supplied accepted/rejected
decisions while keeping those decisions as review evidence only. A later import
preview slice decides how those decisions would affect SpecGraph.

## Goals

- Add `ontology_owner_decision_report` to the semantic policy layout.
- Define accepted, rejected, and clarification decision states.
- Preserve Ontology decision refs, candidate ids, intake ids, decision actor,
  decision time, and accepted-delta status.
- Reject SpecGraph import, semantic gate closure, canonical mutation, prompt
  execution, and Ontology package/lockfile write authority.
- Cover report shape, write path, authority boundary, and registry trace in
  tests.

## Non-Goals

- Applying owner decisions to SpecGraph specs.
- Marking candidates accepted in canonical SpecGraph state.
- Closing semantic gates.
- Writing Ontology packages or lockfiles.
- Adding SpecSpace mutation UI.

## Runtime Contract

The report artifact declares:

```json
{
  "artifact_kind": "ontology_owner_decision_report",
  "schema_version": 1,
  "proposal_id": "0114",
  "source_artifacts": {
    "ontology_closed_loop_evidence": "runs/ontology_closed_loop_evidence.json"
  },
  "canonical_mutations_allowed": false,
  "tracked_artifacts_written": false,
  "decisions": []
}
```

Each decision records:

- decision id;
- candidate id;
- intake id;
- decision state;
- Ontology decision ref;
- decision actor and timestamp;
- accepted-delta flag;
- explicit false SpecGraph import, gate-close, and canonical mutation flags.

## Authority Boundary

The report may be used as owner-decision evidence by later import previews.

The report may not:

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
  `ontology_owner_decision_report`;
- `tools/ontology_imports.py` builds and validates the owner decision report;
- `make ontology-imports` writes `runs/ontology_owner_decision_report.json`;
- focused tests cover accepted/rejected report shape, write path, and authority
  boundary;
- proposal `0114` is tracked in promotion and runtime registries;
- proposal gates, DocC sync, and focused Python tests pass.

## Next Gap

```text
build_ontology_decision_import_preview
```
