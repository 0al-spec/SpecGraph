# Readable ontology outline: first HC/HCS prototype

Open [context.hc](context.hc) for the human review:

```hc
ContextVerification
  Member
  Dependencies
```

Read this as: the selected context-verification case has a member-check role
and a dependency-check role. Names describe these local roles. The indentation
expresses their selected composition; it establishes no execution order,
inheritance, approval or inferred causal relationship.

The [companion context.hcs](context.hcs) maps each role to a versioned ontology
declaration and the existing scenario. Reviewers can read the `.hc` on its own;
the pair is tracked so a pull request exposes an ordinary text diff.

## Source, scope and interpretation

This is a **manually authored, proposed view of one existing scenario**,
`SG72-UNSUPPORTED-CLOSURE`, from
`specs/models/SG-SPEC-0072/unsupported-closure.ts` and its local ontology package.
The scenario already declares two `CheckResult` values, with distinct IDs
`captured-member` and `unsupported-closure`, included by
`contextcase:caseIncludesCheck`. The root maps to `ContextVerificationCase`.
The source package remains draft. The source files and their hashes are recorded
in HCS; the package version is part of every ontology URI.

Choosing that relation as the composition basis and choosing the short role
names are attributed authoring decisions. This prototype does not discover a
hierarchy from an arbitrary ontology graph. It reuses the existing case's
assembly and proposes a compact description for human review.
It introduces neither new ontology classes nor an automatic exporter.

Two local roles can reuse one type while retaining distinct role IDs. Here
`Member` and `Dependencies` both map to `CheckResult`; they are two declared
checks, not a shared central runtime object. Full-path HCS selectors bind each
occurrence without printing technical IDs in the `.hc`.

The HCS properties use a prototype consumer convention:

| Property | Purpose |
| --- | --- |
| `role_id` | Existing scenario/check identity, independent of the short display name |
| `ontology_ref` | Exact package/version/declaration URI |
| `ontology_pointer` | Declaration address inside the source YAML where supplied |
| `composition_ref` | Explicit selected relation motivating this view's composition |
| `ontology_source`, `ontology_sha256` | Source package and exact bytes |
| `scenario_source`, `scenario_sha256` | Existing case declaration and exact bytes |
| `hc_sha256` | The readable outline bytes paired with this mapping |
| `projection_profile`, `composition_status` | Prototype convention and proposed interpretation |

Root metadata describes the pair. It is not implicitly inherited by child nodes:
Hypercode resolves properties on matched nodes. The root supplies shared input
identity; each child has its own complete versioned type URI and role ID.

## What remains outside the outline

Imported foundation/core scaffolding, fields, cardinalities, diagnostic strings
and expected outcome are omitted from `.hc`. The cross-check relation
`closureUsesMemberCheck` and the reference to a Requirement are also omitted;
they are not converted into composition children. The original ontology and
scenario retain them. This view does not claim full ontology coverage.

SpecDraft already provides capture, identity and hierarchy in its HC/HCS notes.
This prototype demonstrates readable role names plus an HCS ontology mapping;
it does not change `Note#id`, the note codec, existing notebooks or promotion.
The captured design sources and the operator's bounded authorization are in
[source-notes.md](source-notes.md). Return anchors are SG-SPEC-0072 and
[proposal 0232](../../../proposals/0232_verified_project_ontology_context.md).

## Reproduce the syntax and cascade checks

From the SpecGraph root, using an existing Hypercode reference CLI:

```sh
hypercode parse docs/reviews/0232_project_ontology_context/hypercode-overview/context.hc
hypercode validate docs/reviews/0232_project_ontology_context/hypercode-overview/context.hc \
  --hcs docs/reviews/0232_project_ontology_context/hypercode-overview/context.hcs
hypercode emit docs/reviews/0232_project_ontology_context/hypercode-overview/context.hc \
  --hcs docs/reviews/0232_project_ontology_context/hypercode-overview/context.hcs \
  --ir-version 2
hypercode explain docs/reviews/0232_project_ontology_context/hypercode-overview/context.hc \
  --hcs docs/reviews/0232_project_ontology_context/hypercode-overview/context.hcs \
  'ContextVerification > Member' ontology_ref
```

The retained [local verification](verification.json) records executable/input
hashes, parse/validate/emit checks, declaration lookup, mapping coverage and
negative controls. Generated IR and command transcripts remain on TB5.
No new compiler build or inference is needed to inspect the pair.

Hypercode validates syntax and resolves property strings with provenance.
It does **not** interpret `ontology_ref`, fetch an ontology or validate the
meaning of this composition. In the local probe those links were separately
checked against the exact ontology package and compiler-produced IR. A typo in
an ontology URI or an unmatched selector can still be valid Hypercode; those
controls distinguish cascade success from a usable mapping. These observations
do not install a production mapping checker or a new blocking quality gate.

## Next bounded slice

First review the short outline and role choices. If useful, define a small
deterministic export profile taking an explicit selected composition plus its
ontology bindings, then produce this same pair without a reverse importer.
Preserve source/role identity and known omissions as names and structure evolve.
