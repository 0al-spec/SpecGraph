# One publication criterion — PB-PAYLOAD

If a fetched file has a different SHA-256 from its entry in the bundle manifest,
bundle verification must fail. This pilot covers **one of the five** criteria of
`SG-REQ-PUBLICATION-VERIFIED`. The [source node](../../nodes/SG-SPEC-0071.yaml)
identifies the criterion at `/specification/requirement/criteria/1`.
Its obligation and existing pytest binding are at `/atoms/intents/1`.
[case.json](case.json) pins the node's bytes, IDs, pointers and statement.

## What the vocabulary expresses

| Part of the criterion | Expression | How it was checked |
| --- | --- | --- |
| Which requirement, criterion and test are involved | Existing `sgcore:Requirement`, `AcceptanceCriterion`, `Test`, `requirementValidatedByCriterion` and `testValidatesRequirement`. A local observation specializes `sgcore:Evidence` and can use `evidenceSupportsCriterion`. | Resolve the criterion and its test against the source and passport bindings. Type-check [model.ts](model.ts) against the generated SDKs and check the instance edges against their compiled endpoints. |
| Which values to compare | Two draft local classes, `ManifestEntry(path, expectedSHA256)` and `PayloadObservation(observedSHA256)`. Each observation has exactly one `comparedAgainst` entry. | Compile the [local package](domain-ontology-package.yaml) with Ontology 0.5.0. Both matching and mismatching digests fit the same field types and relation. |
| What a mismatch does | The product computes SHA-256 over the fetched bytes and rejects a mismatch for that path. | Run the production [bundle verifier](../../../tools/static_artifact_incremental_stage.py) against the two inputs below. |

The project-local `specgraph-core@0.1.0` has no manifest-entry type or relation
for this comparison. As a control, we constructed an object with
`$type: "sgcore:Evidence"` and `observedSHA256` against the unextended generated
SDK. TypeScript 6.0.3 rejected the property (`TS2353`). The released event vocabulary does include an
[`artifactDigest` on a direct observation origin](https://github.com/0al-spec/Ontology/blob/0fcc94469d971aaf39fcc182bc5c6b8acff37fd2/SPECS/ontology/packages/events-core/versions/0.2.0/domain-ontology-package.yaml).
That identifies an observation's source artifact. It supplies neither the digest
expected by a publication manifest nor the rule that rejects a mismatch.
The two additions are scoped to this example. SHA-256 fields in the generated
SDK are strings. The production verifier supplies the hash algorithm and comparison.

![Local types and the observation-to-entry relation](ontology.svg)

The [DOT](ontology.dot) and SVG show the package's type declarations.
[model.ts](model.ts) links the synthetic observations to the actual criterion.

## Controls and replay

Both runs use the same local file `payload.txt`, manifest and checksums.
The test substitutes an in-memory HTTPS response for the network fetch. All
other verification logic runs through `verify_remote_bundle`.

| Served bytes | Observed result |
| --- | --- |
| `abc` (matches the local bytes) | `verified` for the one-file fixture |
| `abd` (one changed byte, same length) | `IncrementalStageError: remote artifact digest mismatch: payload.txt` |

A separate structural control changed only the local relation range from
`ManifestEntry` to `ManifestEntyr`. The released compiler exited 1 with
`relation.range.unresolved` at `spec.relations.comparedAgainst.range`.
The digest mismatch itself is a valid observation in the ontology; the error in
the second row comes from exercising the product. These runs use synthetic
payloads and establish no deployment or evidence admission.

From the SpecGraph root, select the extracted 0.5.0 compiler and TypeScript
6.0.3 (Node on PATH) to include the generated SDK check:

```sh
ONTOLOGYC_BINARY_PATH=/absolute/path/to/ontologyc \
TYPESCRIPT_TSC_PATH=/absolute/path/to/typescript/bin/tsc \
  .venv/bin/python -m pytest -q tests/test_pb_payload_ontology_model.py \
  tests/test_static_artifact_incremental_stage.py -k pb_payload

/absolute/path/to/ontologyviz specs/models/SG-SPEC-0071/domain-ontology-package.yaml \
  --format svg --out /path/to/diagram
```

The macOS Ontology compatibility job runs the source, SDK and behavior controls
and compares the rendered DOT. Ordinary Python runs can exercise the source
binding and both payloads without installing either external tool.
