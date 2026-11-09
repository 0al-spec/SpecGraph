# Foundation and SpecGraph invariant review

This review is linked to [SG-RFC-0232](../../proposals/0232_verified_project_ontology_context.md)
and the existing SG-SPEC-0010 and SG-SPEC-0072 nodes. It records the scope of
the name overlap; it does not introduce a new ontology identity or claim that
two independently versioned declarations are interchangeable.

## Evidence

- [SG-SPEC-0001](../../../specs/nodes/SG-SPEC-0001.yaml) defines an
  `invariant` graph-node kind as a stable property that must hold across
  changes, with a statement and optional scope and verification mode.
- [SG-SPEC-0010](../../../specs/nodes/SG-SPEC-0010.yaml) separately defines a
  vocabulary-layer invariant governing concepts, relation types and state
  families. Its terminology explicitly says it does not replace the broader
  graph-node kind in SG-SPEC-0001.
- [specgraph-core 0.3.0](../../../ontology/packages/specgraph-core/versions/0.3.0/domain-ontology-package.yaml)
  declares `sgcore:Invariant` as an `sg:DomainEntity` describing valid graph
  evolution and connects it to `SpecGraph`.
- The [pinned 0.1.0 foundation model](https://github.com/0al-spec/Ontology/blob/c52553f872f440dde26c61abf9193f5fff171d98/SPECS/ontology/foundation-types.md#foundation-interfaces)
  declares `Invariant` as an ontology node with `appliesTo: ConceptRef[]`.
  The [pinned export table](../../../tools/project_ontology_context/pinned_foundation/exports.json)
  supplies symbol names and roles, not full class declarations.

The same name is a useful collision signal. The evidence does not establish that
the broader graph invariant is identical to the foundation ontology-node type:
their scopes and representation differ. It would be incorrect to silently bind
one to the other purely by spelling. The current checker continues to report
the overlap; this assessment does not whitelist it.

## Bounded next change

Prepare a new version of the project core in which the graph-specific concept
has an unambiguous name, such as `GraphInvariant`, and migrate its relation
and consumers with an explicit compatibility report. Keep historical 0.3.0
inputs and URIs intact. Determine whether any narrower vocabulary invariant
should reuse the foundation type from its actual fields and scope; do not infer
that answer from the proposed name. The versioned candidate, migration and
comparison belong in a separate reviewed implementation.

## Foundation nodes in the Viewer

The five foundation references in the current combined projection are genuinely
unloaded. The pinned JSON catalogs enumerate exports and their package identity,
but are not `DomainOntologyPackage` source documents and do not contain full
definitions. The viewer correctly marks those references external. A real fix
belongs first in Ontology: expose versioned, source-attributed foundation
declarations in a machine-readable form that the visualizer and Viewer can
consume without fabricating a YAML source pointer. SpecGraph can then pin and
publish that projection, and SpecSpace can display it.

## Checks

On SpecGraph `88126b616a7fb2d3e300c9c3e5cd23af0f3beb6f`,
`make ontology-name-collisions` reported zero new collisions and one existing
import-closure pair: `sg:Invariant` and `sgcore:Invariant`.
`supervisor.py --target-spec SG-SPEC-0010 --observe-graph-health` reported two
subtree nodes, zero structural observations and no recommended action. This
does not assess the semantic equivalence of the two declarations.

The source digests for this assessment are recorded in
[foundation-invariant-20261109.json](foundation-invariant-20261109.json).
