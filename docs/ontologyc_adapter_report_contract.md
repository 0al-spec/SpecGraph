# Ontologyc Adapter Report Contract

## Purpose

This document defines the SpecGraph-side contract for consuming
`ontologyc validate-specgraph` output as a typed adapter report under proposal
`0060`.

The adapter report is evidence for review surfaces. It is not canonical
SpecGraph state, not an accepted ontology lock, and not permission for
`ontologyc` to write `specs/nodes/*.yaml`.

## Boundary

```text
SpecGraph fixture or future binding artifact
  -> ontologyc validate-specgraph
  -> concept refs, ontology lock candidate, ontology gaps
  -> ontologyc_adapter_report
  -> SpecGraph validation
  -> read-only derived surfaces
```

SpecGraph accepts the report only as an adapter boundary artifact. The report
may explain what `ontologyc` resolved, which refs remained gaps, and which
package source/version/digest was used. SpecGraph still requires normal
proposal review before any canonical import lock, semantic binding, or spec
node change exists.

## Accepted Report Shape

The accepted report artifact kind is:

```yaml
artifact_kind: ontologyc_adapter_report
schema_version: 1
producer:
  tool: ontologyc
  command: validate-specgraph
package:
  package_id: edu.university.examcalc
  namespace: examcalc
  version: 0.1.0
  source_uri: git+https://github.com/0al-spec/Ontology.git
  source_ref: main
  digest: sha256:...
inputs:
  binding_ref: import-fixture.yaml
  normalized_ir_ref: ontology.normalized.json
outputs:
  concept_refs_ref: ontologyc/concept-refs.yaml
  ontology_lock_ref: ontologyc/ontology.lock.yaml
  ontology_gaps_ref: ontologyc/ontology-gaps.yaml
summary:
  status: passed
  resolved_ref_count: 2
  gap_count: 1
  canonical_mutations_allowed: false
  tracked_artifacts_written: false
authority_boundary:
  report_is_authority: false
  digest_authority: normalized_ir_sourceDigest
  ontology_lock_is_canonical: false
  automatic_import_lock_update: false
  automatic_canonical_node_update: false
```

The machine-readable contract lives in:

```text
tools/ontology_import_policy.json
```

The current smoke fixture lives under:

```text
tests/fixtures/ontology_import/examcalc/
```

## Authority Fields

SpecGraph treats these report fields as authority-bearing inputs that must be
validated before any downstream surface may cite the report:

- `package.package_id`
- `package.namespace`
- `package.version`
- `package.source_uri`
- `package.source_ref`
- `package.digest`

The package digest must match the normalized IR `sourceDigest`. The package id,
namespace, and version must match both the import fixture and the normalized IR.

`outputs.ontology_lock_ref` is deliberately not accepted as canonical
`ontology.lock.yaml`. It is a report artifact emitted by `ontologyc`, useful for
review and drift analysis, but a canonical SpecGraph import lock remains a
separate governance action.

## Validation

`tools/ontology_imports.py --write` builds the existing proposal `0060`
read-only surfaces and also validates the checked-in adapter report fixture.
The smoke artifact is:

```text
runs/ontologyc_adapter_report_smoke.json
```

The smoke passes only when:

- the report kind, schema version, producer tool, and command match policy;
- source/version/digest fields match the fixture and normalized IR;
- `concept-refs.yaml`, `ontology.lock.yaml`, and `ontology-gaps.yaml` resolve
  under the fixture directory;
- reported resolved-ref and gap counts match the output artifacts;
- `canonical_mutations_allowed` and `tracked_artifacts_written` remain `false`;
- the authority boundary forbids report authority, automatic import-lock
  updates, and automatic canonical node updates.

## Failure Modes

The policy names these report-level failure modes:

- `ontologyc_unavailable`
- `invalid_binding`
- `invalid_normalized_ir`
- `source_digest_mismatch`
- `output_artifact_missing`
- `unsupported_report_shape`

The current smoke fixture requires `summary.status: passed`. Future runtime
adapters may emit failed or blocked reports, but those reports must remain
evidence only and must not close ontology gaps or mutate canonical specs.

## Project-Local Package Boundary

Project-specific ontology package data should be stored under the owning
SpecGraph project, for example `ontology/packages/specgraph-core/`. The sibling
Ontology repository remains the tooling, schema, compiler, stdlib primitive,
and example authority; it is not the default storage location for every product
ontology built with SpecGraph and SpecSpace.

## Non-Goals

This contract does not:

- invoke `ontologyc` from the supervisor;
- create canonical `specs/imports/ontology.lock.yaml`;
- auto-import concepts into `specs/nodes/*.yaml`;
- execute prompt agents;
- define Platform or Docker packaging;
- define SpecSpace mutation UI.
