# Ontology 0.6.0 consumer update

Bounded tooling realization under SG-SPEC-0072 / proposal 0232. The delegated
operator request is to consume published Ontology 0.6.0, update the compiler pin
and canonical foundation export, and retain supported legacy packages. SpecGraph
versioning is handled separately. No new semantic requirement or package approval
is inferred from this maintenance update.

## Source and compatibility

- Release: [Ontology 0.6.0](https://github.com/0al-spec/Ontology/releases/tag/0.6.0),
  commit `c52553f872f440dde26c61abf9193f5fff171d98`.
- The vendored `export-foundation` catalog now identifies
  `ontology.foundation@0.1.0`, namespace `ont`. Its bytes match the release source
  and the executable export; SHA-256 is recorded in [verification.json](verification.json).
- The published macOS arm64 archive matches both the GitHub asset digest and
  the published checksum file. This identifies downloaded bytes; it does not
  attest a binary-to-source build correspondence.
- The context profiles accept the two exact default-namespace imports:
  `ontology.foundation` / `ont` and legacy `specgraph.foundation` / `sg`, both
  version `0.1.0`. Other aliases/versions remain outside this bounded consumer
  profile, even where the compiler supports more aliases.
- Both imports consult the same canonical catalog. Resolved names and URIs
  retain the package's actual declared import. Composition resolves imports per
  package and can mix supported canonical and legacy dependencies.
- Joint vocabulary exposes only foundation aliases actually imported by the
  captured closure. Its analysis profile advances to
  `specgraph-composed-symbol-advisory-v4`; old observations are not relabeled.

## Checks performed

The real release compiler passed 112 focused tests covering foundation,
composition, joint reports, context capture, release smoke and the bounded
metamodel check. The canonical and legacy foundation cases each verify
`ValueObject` and reject `Typo`, both with missing IR and with retained stale IR.
A rejected source has no verified snapshot or context revision.

Five additional real-compiler checks passed for mixed-closure inventory and
shadowing of either foundation ID/default namespace. The release visualizer
reproduced the preserved SG-SPEC-0072 and SG-SPEC-0071 DOT files byte-for-byte.

Pure closure checks additionally cover all-canonical and mixed imports,
unknown canonical references and unsupported foundation identities/versions.
Release compatibility CI builds from the pinned source and compares its export
catalog on macOS and Linux. CI also runs the real canonical/legacy controls.
Local testing here used macOS; Linux execution is reported independently by CI.

The adapter release smoke passed against the unchanged draft
`org.0al.specgraph.core@0.1.0`: normalized IR matches the checked-in file, seven
references resolve, and `sgcore:ClaimCalibration` remains a visible gap.
The `sgcore` source, fixtures, authority and applicability-decision inputs are
not migrated to a new namespace. Historical evidence keeps its original compiler
and catalog pins. New verification is stored separately in this directory.

## Outcome boundaries

This updates the provider/compiler and supported reference resolution. It does
not approve ontology meanings, accept product specifications, modify canonical
specifications, activate new runtime policies or claim verified tests/runtime
behavior for a product. Name resolution and a compiler smoke do not close
semantic gaps. The release does not alter SpecGraph's own version.
