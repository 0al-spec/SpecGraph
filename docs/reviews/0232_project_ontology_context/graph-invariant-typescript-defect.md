# Graph invariant: TypeScript inheritance projection observation

## Correction, 2026-11-09

The original probe below compared an **instance** of `GraphInvariant` against
fields in the foundation model's **ontology declaration** interface. That
comparison does not establish that `kind` and `appliesTo` are missing instance
fields. The compiler still had a separate, real gap: declared fields and
semantic ancestry of domain classes were not projected into generated SDK
interfaces and schemas. [Ontology PR #113](https://github.com/0al-spec/Ontology/pull/113)
proposes a source-bound fix, including a type-only marker for the exact
foundation base. It remains subject to review, CI, merge and a later release.

Testing the proposed fix also exposed the separate
[inheritance validation gap](inheritance-validation-gap-20261109/README.md):
`check` and staged advice accept an inheritance cycle that the proposed
`compile` rejects. The original observation below is retained for traceability.

The [0.4.0 candidate](../../../ontology/packages/specgraph-core/versions/0.4.0/domain-ontology-package.yaml)
declares `GraphInvariant` with `extends: sg:Invariant`. Ontology 0.10.0
`ontologyc check` and `compile` succeed, and its normalized IR and full graph
retain that semantic base. The generated `types.ts` instead declares an
independent `GraphInvariant` interface containing `$type` and optional `id`;
it has no TypeScript `extends` clause or the foundation invariant's required
`kind` and `appliesTo` fields.

The versioned [foundation contract](https://github.com/0al-spec/Ontology/blob/a31935ab7e4051fec60651eec4196d71c2a5d265/SPECS/ontology/foundation/0.1.0/model.md#inheritance-rule)
states that TypeScript `extends` is generated as a projection of semantic
inheritance. A local TypeScript 5.8.3 check of the generated `GraphInvariant`
against a structural type containing only the foundation invariant's required
`kind: "Invariant"` and `appliesTo` fields failed with TS2739: both fields are
missing. The [emitter source](https://github.com/0al-spec/Ontology/blob/a31935ab7e4051fec60651eec4196d71c2a5d265/Sources/OntologyCompiler/TypeScriptEmitter.swift)
forms its TypeScript `extends` clause from implemented local protocols, not the
class's semantic `extends` reference. The [defect record](graph-invariant-typescript-defect.json)
connects the observation to the existing intent and proposal lane.

Reproduce with Ontology 0.10.0 and TypeScript 5.8.3, with `OUT` outside the
checkout:

```sh
ontologyc compile ontology/packages/specgraph-core/versions/0.4.0/domain-ontology-package.yaml \
  --target typescript --out "$OUT/sdk"
cat > "$OUT/inheritance-probe.ts" <<'EOF'
import type { GraphInvariant } from "./sdk/types";
type RequiredInvariantFields = { readonly kind: "Invariant"; readonly appliesTo: readonly unknown[] };
declare const graphInvariant: GraphInvariant;
const foundationInvariant: RequiredInvariantFields = graphInvariant;
void foundationInvariant;
EOF
tsc --noEmit --skipLibCheck --strict --target ES2022 "$OUT/inheritance-probe.ts"
```

The observed type-check exits 2 with TS2739, naming the missing `kind` and
`appliesTo` fields. The compiler check and export themselves exit successfully.

This establishes a discrepancy between the documented projection and this
generated artifact. It does not establish that the compiler should directly
extend the current foundation interface: foundation declarations use `kind`
and describe ontology nodes, while generated instance interfaces use `$type`.
Resolve that contract boundary in Ontology, then add a regression covering the
chosen representation. No upstream fix, TypeScript subtyping or runtime
enforcement is claimed by publishing this graph candidate.
