# Ontology Semantic Lint Input

RFC: SG-RFC-0116
Version: 0.1.0

## Status

Implemented

Decision scope: deterministic, source-backed semantic lint input for real
SpecGraph proposal or supervisor output surfaces.

This document does not parse arbitrary text as ontology authority, run prompt
agents, invoke ontologyc, write Ontology packages, update ontology lockfiles,
mutate canonical SpecGraph specs, accept candidate terms, or close semantic
gates.

## Source Material

This proposal implements the next bounded runtime slice after the read-only
ontology review and owner-decision surfaces through
`0115_ontology_decision_import_preview`.

Source draft:

- `docs/archive/proposal_sources/0116_ontology_semantic_lint_input.md`

## Summary

SpecGraph now emits a deterministic semantic lint input artifact:

```text
runs/ontology_semantic_lint_input.json
```

The artifact replaces the full lint report's fixture-only input with a
source-backed input surface. It reads declared terms from tracked SpecGraph
proposal or supervisor output sources, verifies that each declared term appears
in the source text, and records source id, source kind, repository path, digest,
and span metadata. The downstream `ontology_semantic_lint_report` still uses the
same deterministic classifier, but its input is now a reviewable output surface
rather than a policy fixture.

## Goals

- Add `semantic_lint_input` to the semantic policy layout.
- Define a `semantic_lint_input_contract` for proposal/supervisor output
  sources, extraction mode, consumer boundary, and authority boundary.
- Build `ontology_semantic_lint_input` from tracked output sources and declared
  term anchors.
- Preserve source digests and spans so review surfaces can explain where a term
  came from.
- Wire `ontology_semantic_lint_report` to consume the lint input artifact.
- Keep all effects non-mutating and local under `runs/`.
- Cover input extraction, report source linkage, write paths, and registry trace
  in tests.

## Non-Goals

- Arbitrary natural-language parsing.
- Prompt-agent execution.
- Wiring the semantic gate into ordinary targeted supervisor runs.
- Writing Ontology package drafts.
- Updating ontology lockfiles.
- Applying accepted terms back into SpecGraph specs.
- Marking candidate terms accepted.
- Adding SpecSpace mutation UI.

## Runtime Contract

The lint input declares:

```json
{
  "artifact_kind": "ontology_semantic_lint_input",
  "schema_version": 1,
  "proposal_id": "0116",
  "source_outputs": [],
  "detected_terms": [],
  "canonical_mutations_allowed": false,
  "tracked_artifacts_written": false,
  "output_artifact": "runs/ontology_semantic_lint_input.json"
}
```

Each detected term records:

- term text and optional ontology source ref;
- source output id and kind;
- repository path;
- source span;
- deterministic extraction mode.

The checked-in fixture uses `docs/proposals/0105_ontology_semantic_lint_report.md`
as the first real proposal-output source because that proposal already contains
the examcalc semantic terms used by the existing ontology import fixture.

## Authority Boundary

The lint input may be used by the semantic lint report and supervisor semantic
gate evidence.

The lint input may not:

- parse arbitrary text as ontology authority;
- execute prompt agents;
- write Ontology packages;
- update ontology lockfiles;
- mutate canonical specs;
- mark candidate terms accepted;
- close semantic gates;
- become canonical authority for accepted terms or ontology deltas.

## Acceptance

This slice is complete when:

- `tools/ontology_semantic_control_policy.json` declares
  `semantic_lint_input`;
- `tools/ontology_imports.py` builds `ontology_semantic_lint_input` from tracked
  output sources;
- `ontology_semantic_lint_report` links to
  `runs/ontology_semantic_lint_input.json`;
- `make ontology-imports` writes `runs/ontology_semantic_lint_input.json`;
- focused tests cover input extraction, report linkage, write path, and
  authority boundary;
- proposal `0116` is tracked in promotion and runtime registries;
- proposal gates, DocC sync, and focused Python tests pass.

## Next Gap

```text
wire_supervisor_semantic_gate_into_targeted_runs
```
