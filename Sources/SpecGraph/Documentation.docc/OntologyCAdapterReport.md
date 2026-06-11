# Ontologyc Adapter Report

SpecGraph consumes `ontologyc validate-specgraph` output through an
`ontologyc_adapter_report` boundary. The report is evidence for read-only
ontology import surfaces, not canonical graph authority.

## Contract

The repository contract source is:

```text
docs/ontologyc_adapter_report_contract.md
```

The machine-readable policy is:

```text
tools/ontology_import_policy.json
```

The accepted adapter report records source/version/digest identity for the
Ontology package, points to `concept-refs.yaml`, `ontology.lock.yaml`, and
`ontology-gaps.yaml`, and preserves `canonical_mutations_allowed: false`.

`ontology.lock.yaml` from the adapter output is a non-canonical report artifact.
SpecGraph still needs proposal review before any accepted import lock, semantic
binding, or canonical node mutation exists.

## Smoke Surface

`tools/ontology_imports.py --write` validates the checked-in report fixture and
emits:

```text
runs/ontologyc_adapter_report_smoke.json
```

The smoke requires matching package id, namespace, version, source URI, source
ref, and digest. The digest must match the normalized IR `sourceDigest`.

The smoke also verifies that output refs resolve under the fixture directory and
that report counts match the resolved concept refs and ontology gaps.

## Boundary

The adapter report must not:

- update canonical `ontology.lock.yaml`;
- mutate `specs/nodes/*.yaml`;
- close ontology gaps automatically;
- execute prompt agents;
- redefine Ontology package schema inside SpecGraph.
