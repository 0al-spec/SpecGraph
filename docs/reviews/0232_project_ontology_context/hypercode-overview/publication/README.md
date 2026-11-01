# Second readable ontology fragment: publication criteria

The operator requested a second ontology-fragment experiment after clarifying
that SpecDraft notes and a formal ontology are different layers. This replay
uses the existing project core vocabulary and real SG-SPEC-0071 data. It does
not consume a notebook, change the ontology or add canonical spec nodes.

## Proposed composition and names

The [selected HC](selection.hc) declares the existing specification, its one
publication-verification Requirement and its five AcceptanceCriterion IDs.
The source YAML already nests these criteria under that requirement. The
[HCS](selection.hcs) selects the core declarations and readable names, with
one shared type selector for the five criterion bindings. The generated
[context.hc](generated/context.hc) is:

```hc
Publication
  Verification
    AllFiles
    Payload
    Manifest
    Checksums
    Missing
```

This is a proposed presentation of a bounded fragment. The names have not
received separate human approval. Tree order follows the authored selection;
it is not inferred by traversing every ontology relation. The source requirement
owns this criterion list locally; the view does not redefine every
`requirementValidatedByCriterion` relation as global containment or execution
order. Other delivery policies and graph links stay in the original sources.

| Readable role | Existing identity | Versioned core declaration |
| --- | --- | --- |
| Publication | SG-SPEC-0071 | Spec |
| Verification | SG-REQ-PUBLICATION-VERIFIED | Requirement |
| AllFiles | PB-ALL | AcceptanceCriterion |
| Payload | PB-PAYLOAD | AcceptanceCriterion |
| Manifest | PB-MANIFEST | AcceptanceCriterion |
| Checksums | PB-CHECKSUMS | AcceptanceCriterion |
| Missing | PB-MISSING | AcceptanceCriterion |

All types resolve in `org.0al.specgraph.core@0.1.0`. Root and Requirement record
the selected `definesRequirement` and `requirementValidatedByCriterion` URIs.
These relation declarations exist in compiled IR; the exporter does not prove
their applicability to the selected hierarchy. The source ontology remains
draft. This illustrates a typed instance composition, not an inventory of all
classes or a transformation of inheritance into a tree.

## Exact sources and implementation scope

- Ontology: `ontology/packages/specgraph-core/domain-ontology-package.yaml`,
  SHA-256 `5bfa2ff40b6174def589546ab2fea2501e1f256c4f1446f36c45c7f3fffcd929`.
- Scenario: `specs/nodes/SG-SPEC-0071.yaml`, SHA-256
  `9f4a8b8332138ef3b6d1d9cc873b2a40a1a4620f7fceb35db32d4d9e1d6521a9`.
- Production: `tools/static_artifact_incremental_stage.py`, SHA-256
  `247a69929786a136baa9606d5bc847a371bfb09b53c6a94097d996a5d3ed16b0`.

Each criterion selects an existing fragment of `verify_remote_bundle`. AllFiles
points at the map over manifest entries; Payload points at digest mismatch;
Missing points at request failure. Manifest and Checksums intentionally point
at the **same generic metadata comparison** used for both metadata paths. Their
distinct IDs are not merged. The binding does not prove path-specific behavior;
the existing publication behavior tests provide that separate observation.
Nested helper statements are inside the selected top-level function's AST span.

The [generated HCS](generated/context.hcs) retains all seven role IDs, source
types and exact package/source/IR/compiler digests. Repeated types and shared
implementation do not imply that the five criteria are one occurrence. Target
production modules are parsed, never imported or executed by this export.

## Verification and limits

Replay base: exporter `b6c90d81130e85d3f202b3cae13ae0a64615ace9` from PR #861.
No exporter implementation change was needed. Real Hypercode IR v2
(`0.6.0-dev`) and ontologyc `0.5.0` produced the pair; HCS records executable
byte identities, without certifying publisher provenance.

The second-fragment test set passed **10 tests, zero skips** locally:

- Compare selected IDs and their order against the real source specification.
- Export seven roles at three levels twice; require identical HC/HCS bytes and
  preserve the five occurrences of one type.
- Rename Manifest to ManifestBytes while preserving identities and ontology
  bindings; independently swap the final two roles and preserve authored order.
- Reject unknown class, wrong package version, duplicate ID, missing production
  function and wrong package digest before destination creation.
- Reject a child renamed Publication when the root's selector would leak its
  properties into that child. This is a profile limitation, not a semantic claim
  that the ontology or repeated role is invalid.

HC SHA-256: `732b6dc6aa0b9e98e35f6a8259723cd6c5292138b70319dc29c5fc6034edf1cc`.
HCS SHA-256: `f83653cc7004d296945859a94fd864e4c5703cff599cfa013b3d05db2c64db1f`.

From the checkout, set both reference executable variables and run:

```sh
HYPERCODE_BIN=/path/to/hypercode ONTOLOGYC_BIN=/path/to/ontologyc \
  .venv/bin/python -m pytest -q tests/test_ontology_overview_publication.py
```

Without those tools, the source-ID test still runs and nine real-tool cases
explicitly skip. The tests exercise compiler-backed reference lookup and export
mechanics; they do not run the verifier or prove criterion satisfaction. No
import-closure, semantic-equivalence, runtime or readability score is claimed.
The result supports reuse beyond the first three-node case while leaving the
proposed names available for human review.
