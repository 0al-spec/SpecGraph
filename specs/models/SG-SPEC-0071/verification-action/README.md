# Verify a published bundle

This draft declaration model covers the existing action behind
[SG-SPEC-0071](../../../nodes/SG-SPEC-0071.yaml),
`SG-REQ-PUBLICATION-VERIFIED`, and criterion `PB-ALL`
(`/atoms/intents/0`). The [production verifier](../../../../tools/static_artifact_incremental_stage.py)
receives a local `bundle_dir` and a remote `remote_base_url`. It compares both
remote metadata files with their retained bytes, then compares each remote
payload with its manifest digest. A matching bundle produces a `verified`
observation. A missing file or mismatched digest prevents that result.

| Declaration | Meaning in the production behavior |
| --- | --- |
| `PublicationVerifier` | The executing verifier occupies the subject role. The site serving files is the target environment. |
| `VerifyPublishedBundle` | The action requests the comparison. Its required `expectedBundle: Ref<RetainedBundle>` identifies the retained input that supplies both metadata files and the payload expectations. |
| `PublishedBundle` | The object is the bundle served at the selected HTTPS base URL for the attempt. |
| `RetainedBundle` | The reference target is the local build's retained bundle. Its application locator can resolve to the directory passed as `bundle_dir`. |

Both bundles describe the same intended publication, but can contain different
bytes. The model gives the verifier a distinct reference to the expected side
and the implementation resolves that input independently of the served bytes.
Verification reads the two bundles and produces an observation. The existing [file observation models](../README.md)
cover individual digests, missing responses and coverage of the complete manifest.

The [package](domain-ontology-package.yaml) has approval status `draft`. It
adds a view of the existing behavior with explicit roles and a typed input.
The Python verifier still owns lookup, comparison and observations. Loading
the declaration graph grants no authority to execute verification or admit
evidence. The existing `specgraph-core` publication remains the baseline.

## Reproduce the projection

Use `ontologyc` and `ontologyviz` built from
Ontology commit `35b9eb1408f0160317cbd2846f84ce10931f3c6c`.
That source revision includes typed references and the matching graph export.
The sole import, `ontology.foundation@0.2.0` as `ont`, resolves from the
compiler's built-in catalog. It requires no external package file. The graph
may show `ont:Action` and `ont:DomainEntity` as unloaded declarations because
the built-in catalog supplies type exports, while the projection contains the
source declarations of the local package.

From the SpecGraph root, with the two binaries on PATH and `OUT` pointing to
a build directory outside the checkout:

```sh
model=specs/models/SG-SPEC-0071/verification-action/domain-ontology-package.yaml
ontologyc check "$model"
ontologyviz "$model" --view full --format json --out "$OUT"
ontologyc compile "$model" --target typescript --out "$OUT/sdk"
```

The export is `$OUT/ontology.graph.json`. Its SHA-256 with the pinned tools
and source above is
`2b3520a76b70089e3a9a0b5ddf6fa22278e978a9edfeb8201001a5b7c29fe0f1`.
The graph records package identity, logical YAML pointers and the package
source digest. The generated SDK requires `Ref<RetainedBundle>` on the action.
The verifier's existing behavior can be replayed with
`pytest -q tests/test_static_artifact_incremental_stage.py`.

## Compare the canvas in SpecSpace

1. Open `/ontology` to see the default published core graph. Open
   `/ontology?source=local` in a second tab and select the exported file.
   For an offline baseline, open
   `ontology/packages/specgraph-core/generated/ontology.graph.json` manually
   in the first tab as well.
2. Select `pubverify:verifiesPublishedBundle` under Relationships. Check the
   Subject, Action and Object ports, then follow Action in the inspector.
   `VerifyPublishedBundle` is labeled Action. The
   `expectedBundle: Ref<RetainedBundle>` port has its own edge and its
   inspector link selects `RetainedBundle`.
3. Compare References right, References left (mirrored), Directed layers
   and Relationship layers on the same file. Keep Ontology relations and
   Field references enabled. Toggle Inheritance to see the domain connections
   separately from the foundation references. Switch Line type between Rect
   and Curve and check whether each edge is easy to follow to its named port.
