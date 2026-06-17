# Generated Term Binding Gate

RFC: SG-RFC-0129
Version: 0.1.0

## Status

Implemented

Decision scope: executable review-mode gate for ontology term binding in
generated SpecGraph-facing artifacts.

This document adds a local review gate only. It does not change active prompts,
execute prompt agents, hard-block supervisor writes, mutate canonical specs,
accept ontology terms, write Ontology packages or lockfiles, import owner
decisions, or add SpecSpace mutation UI.

## Source Material

This proposal implements the next bounded slice after
`0128_ontology_term_binding_policy`.

Source draft:

- `docs/archive/proposal_sources/0129_generated_term_binding_gate.md`

Related proposal context:

- `0126_specauthor_claim_calibration_prompt_contract`
- `0127_ontology_stdlib_type_discipline`
- `0128_ontology_term_binding_policy`

## Summary

SpecGraph now has an executable review gate:

```text
tools/ontology_term_binding_gate.py
```

The gate reads:

```text
tools/ontology_term_binding_policy.json
generated artifact JSON
```

and emits:

```text
runs/ontology_term_binding_gate_report.json
```

The report is local and review-first. In default mode it returns `ok: true`
while setting `review_state: review_required` and
`would_reject_in_hard_gate: true` when hard-gate findings are present. Explicit
`--strict` mode exits non-zero for CI or local experiments that want hard
failure behavior.

## Goals

- Add an executable `ontology_term_binding_gate` tool.
- Add a Make target for local report generation.
- Detect the 0128 guardrails:
  - `new_term_without_gap`;
  - `duplicate_accepted_entity`;
  - `deprecated_or_rejected_term_reused`;
  - `observation_marked_accepted`;
  - `topology_edge_as_semantic_relation`.
- Keep default behavior review-only.
- Add tests for review-required, clean, and strict-failure behavior.

## Non-Goals

- Wiring the gate into ordinary supervisor write paths.
- Changing active SpecAuthorAgent or supervisor prompts.
- Executing prompt agents.
- Parsing arbitrary natural language.
- Accepting or rejecting ontology terms.
- Writing Ontology packages or ontology lockfiles.
- Mutating `specs/nodes/*.yaml`.
- Importing owner decisions into canonical SpecGraph specs.
- Adding SpecSpace mutation UI.

## Runtime Contract

The report shape is:

```json
{
  "artifact_kind": "ontology_term_binding_gate_report",
  "schema_version": 1,
  "gate_mode": "review_warning",
  "ok": true,
  "review_state": "review_required",
  "would_reject_in_hard_gate": true,
  "canonical_mutations_allowed": false,
  "tracked_artifacts_written": false,
  "findings": [],
  "warnings": []
}
```

The report is safe evidence only. It must not be treated as Ontology owner
acceptance, canonical SpecGraph mutation, or semantic gate closure.

## Make Target

The local operator target is:

```bash
make ontology-term-binding-gate \
  ONTOLOGY_TERM_BINDING_ARTIFACT=<generated-artifact.json>
```

By default it uses the checked-in review-required fixture and writes:

```text
runs/ontology_term_binding_gate_report.json
```

## Acceptance

This slice is complete when:

- `tools/ontology_term_binding_gate.py` exists;
- `make ontology-term-binding-gate` writes a review report under `runs/`;
- tests cover review-required, clear, and strict-failure behavior;
- `tools/ontology_term_binding_policy.json` records the gate tool and report
  path;
- proposal `0129` is tracked in promotion and runtime registries;
- proposal tracking gate passes;
- documentation sync passes.

## Authority Boundary

This proposal may be used as:

- local review evidence for generated artifacts;
- a future input to a hard generated-artifact write gate;
- a regression fixture proving topology edges are not semantic ontology
  relations.

This proposal may not be used as:

- approval to execute prompt agents;
- approval to hard-block ordinary supervisor writes;
- approval to accept or reject ontology terms;
- approval to write Ontology packages or lockfiles;
- approval to mutate canonical SpecGraph specs;
- approval to add SpecSpace mutation UI.

## Next Gap

```text
wire_term_binding_gate_into_specauthor_generated_artifact_flow
```
