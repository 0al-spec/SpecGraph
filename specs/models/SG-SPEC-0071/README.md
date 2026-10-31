# Publication digest criteria

This pilot exercises three of the five criteria of `SG-REQ-PUBLICATION-VERIFIED`.
All three ask the bundle verifier to compare fetched bytes with an expected SHA-256.
The expected digest has a different origin in each case.

| Criterion | Address in [SG-SPEC-0071](../../nodes/SG-SPEC-0071.yaml) | Source of the expected digest |
| --- | --- | --- |
| [PB-PAYLOAD](case.json) | `/specification/requirement/criteria/1`, `/atoms/intents/1` | The selected payload's entry in the local manifest. |
| [PB-MANIFEST](manifest-case.json) | `/specification/requirement/criteria/2`, `/atoms/intents/2` | SHA-256 computed from the exact bytes of the retained local `artifact_manifest.json`. Its entries describe payloads; none serves as the expected digest of the manifest itself. |
| [PB-CHECKSUMS](checksums-case.json) | `/specification/requirement/criteria/3`, `/atoms/intents/3` | SHA-256 of the entire retained local `checksums.sha256` file, including its line ending. |

Each fixture pins the source spec's bytes, criterion ID, statement and existing
pytest binding. The tests also check the binding in the publication passport.

## Shared model

All cases use the same three core relations to link the requirement, criterion,
test and evidence. A single [typed graph builder](model.ts) uses the SDKs generated
from the project core and the [local package](domain-ontology-package.yaml).
The fetched digest is represented by the same observation type in each case.
`comparedAgainst` selects exactly one expected source per observation.

The first pilot used `ManifestEntry` and `PayloadObservation`. The second adds
one source type, `LocalManifest`. Both source types have a path and an expected
digest. Draft package version 0.2.0 names their shared observation
`FetchedFileObservation` and widens the range of the existing relation to
`oneOf(ManifestEntry, LocalManifest)`.

For the third criterion, draft 0.3.0 generalizes `LocalManifest` to
`LocalMetadataFile`. This keeps three classes and one local relation. The two
metadata cases share the same fields, generated SDK and relation target. The
executable model binds each criterion to its required relative path. Swapping
only the path in either fixture, while preserving the type, body and digest,
causes model construction to fail before the HTTP replay. The two arrows in
the diagram are alternative sources for one observation.

![A fetched observation compares against either a manifest entry or a retained local metadata file](ontology.svg)

The compiled SDK and [type diagram](ontology.dot) allow both targets. The
criterion-specific endpoint check supplies the narrower rule. In a disposable
copy of the second pilot, assigning the `ManifestEntry` type to PB-MANIFEST's
reference still type-checked, but its endpoint test expected `LocalManifest` and failed.
The compiler itself rejects an unknown type in the relation's range. The
earlier [core-only experiment](https://github.com/0al-spec/SpecGraph/tree/045b43f662c8cb28a5507361be38b89a61128229/specs/models/SG-SPEC-0071)
also showed that the generated core `Evidence` type lacks `observedSHA256`
(TypeScript `TS2353`).

## Behavior observed

The tests call the production [bundle verifier](../../../tools/static_artifact_incremental_stage.py)
with an in-memory HTTPS fetcher. The fixture replaces only the selected remote
response. All manifest runs retain the same local manifest, payload `abc` and
checksums. The stale manifest is valid JSON of the same length and contains the
digest of the earlier payload `abd`.

For PB-CHECKSUMS the bundle writer produces the baseline list from the current
payload. The remote manifest and payload match the local files in all three
checksum-list controls.

| Criterion | Remote response | Production result |
| --- | --- | --- |
| PB-PAYLOAD | `abc` | `verified` |
| PB-PAYLOAD | `abd` | `remote artifact digest mismatch: payload.txt` |
| PB-MANIFEST | Exact local manifest bytes | `verified`; the report identifies the local manifest digest |
| PB-MANIFEST | Stale manifest | `remote metadata digest mismatch: artifact_manifest.json` |
| PB-MANIFEST | Current manifest followed by one ASCII space | Same metadata mismatch, even though the parsed JSON is equal |
| PB-CHECKSUMS | Exact list emitted by `write_checksums` | `verified`; the receipt contains the SHA-256 of the list itself |
| PB-CHECKSUMS | Same path, checksum for the earlier payload `abd` | `remote metadata digest mismatch: checksums.sha256` |
| PB-CHECKSUMS | Correct digest and path, CRLF in place of LF | Same checksum-list mismatch |

The whitespace and line-ending cases characterize byte-level comparison.
In a separate local probe we kept the current payload and manifest but put the
same obsolete checksum list on both sides. The verifier returned `verified`
for one payload and two metadata files. It checks that the remote list matches
the retained list and that payloads match the manifest. List contents depend
on the local producer. This probe records the current trust boundary. The
inputs in this pilot are synthetic.

## Replay

Use the extracted Ontology 0.5.0 tools, TypeScript 6.0.3 and Node on PATH.
From the repository root:

```sh
ONTOLOGYC_BINARY_PATH=/absolute/path/to/ontologyc \
TYPESCRIPT_TSC_PATH=/absolute/path/to/typescript/bin/tsc \
  .venv/bin/python -m pytest -v tests/test_publication_digest_ontology_model.py \
  tests/test_static_artifact_incremental_stage.py::test_pb_payload_model_against_bundle_verifier \
  tests/test_static_artifact_incremental_stage.py::test_pb_manifest_model_against_bundle_verifier \
  tests/test_static_artifact_incremental_stage.py::test_pb_checksums_model_against_bundle_verifier

/absolute/path/to/ontologyviz specs/models/SG-SPEC-0071/domain-ontology-package.yaml \
  --format svg --out /path/to/diagram
```

The macOS compatibility job compiles both SDKs once, checks all three cases and
compares the released visualizer's DOT to the checked-in diagram. Source
bindings and byte-level behavior tests also run with Python alone.
