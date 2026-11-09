# SpecGraph ontology review overview

This is a **public, read-only draft overview** of SpecGraph ontology models.
It brings four existing source packages into one `ontologyviz` diagram
without adding relations between those models:

| Package | Source | Purpose in this view |
| --- | --- | --- |
| `sgcore` | [Project core](../../../../ontology/packages/specgraph-core/versions/0.3.0/domain-ontology-package.yaml) | Current public core 0.3.0 |
| `sgproposal` | [Intent to proposal](../../SG-SPEC-0053/intent-to-proposal/README.md) | Draft capture and authoring interpretation |
| `sgpromotion` | [Proposal promotion](../../SG-SPEC-0051/proposal-promotion/README.md) | Draft promotion and materialization interpretation |
| `pubverify` | [Publication verification](../../SG-SPEC-0071/verification-action/README.md) | Draft model of an existing verification action |

The first two candidate models reuse declarations from the core.
The publication model is displayed alongside them; **no domain relation to
the other models is implied**. Each declaration retains its own source package
identity, version, digests and logical YAML pointer. Explicitly supplied
foundation catalogs provide source-attributed definitions for the referenced
0.1.0 and 0.2.0 foundation imports; they are not synthetic YAML packages.
Other unprovided imports remain external references. A digest identifies bytes;
it does not authenticate their author.

The `sgreview` package is only scaffolding for this selection. Its two classes
and `scopeIncludesPackage` relationship describe review metadata, not
SpecGraph's product domain. They exist because the current compiler requires a
root ontology package to have classes and relations. Filter out the
`org.0al.specgraph.review.ontology-overview` package in the Viewer to focus on
the four source packages. Inclusion, compilation and display do not accept
any candidate or prove that an action was executed.

## Reproduce

Use `ontologyviz` from Ontology **0.10.0**. The profile explicitly supplies all
four model files and byte-identical foundation catalogs copied from that tagged
release under `tools/project_ontology_context/pinned_foundation/`. From the
SpecGraph root, with `OUT` naming a directory outside the checkout:

```sh
ontologyviz --profile specs/models/review/ontology-overview/ontology.profile.json \
  --format json --out "$OUT"
```

Open `$OUT/ontology.graph.json` in SpecSpace at `/ontology?source=local`.
The inspector shows the owning package and pointer; package filters can hide
scaffolding or narrow the comparison. The file is a compiler-derived draft
projection of declarations, not executable evidence.

## Check for duplicate names

Run `make ontology-name-collisions` after updating the projection. The check
compares its exact names with `origin/main`; set `ONTOLOGY_COLLISION_BASE` to
compare another Git revision. CI compares against the exact pull request base
and rejects a newly colliding pair, identifying each package and YAML pointer.
The current selection has no exact-name collisions: four classes and six
relations formerly repeated in the intent-proposal draft now reuse core.

The check covers classes, relations, protocols, policies and state machines in
this overview. It also inspects import closures of tracked ontology packages
throughout the repository outside `tests/`, including packages omitted from this
overview. Package imports resolve by exact ID and version; missing project-local
imports and ambiguous identities fail closed. An unavailable external import
is reported as not checked, so an empty collision report does not cover it.
The pinned foundation 0.1.0 and 0.2.0 export catalogs, including the legacy
`specgraph.foundation` alias, are checked against their recorded digests and
included. This broader check reports the existing `Invariant` name overlap
between foundation and specgraph-core for semantic review.
Local runs inspect tracked files in the working tree; add a new package to the
index before checking it. CI checks the committed PR head against its base.
Matching names signal a conflict to resolve; they do not prove that meanings
are equal. The separate reproducibility check ensures that the committed graph
matches its source packages before merge.
