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

The first two candidate models already reference one another and the core.
The publication model is displayed alongside them; **no domain relation to
the other models is implied**. Each declaration retains its own source package
identity, version, digests and logical YAML pointer. The foundation imports
are intentionally not loaded as source packages and may appear as external
references. A digest identifies bytes; it does not authenticate their author.

The `sgreview` package is only scaffolding for this selection. Its two classes
and `scopeIncludesPackage` relationship describe review metadata, not
SpecGraph's product domain. They exist because the current compiler requires a
root ontology package to have classes and relations. Filter out the
`org.0al.specgraph.review.ontology-overview` package in the Viewer to focus on
the four source packages. Inclusion, compilation and display do not accept
any candidate or prove that an action was executed.

## Reproduce

Use `ontologyviz` from the Ontology **0.8.0** release or a compatible later
version. All four model files are explicitly supplied by the profile. The
same selection has also been checked with the post-release Ontology commit
`b1a0da17ddd9256c74c36d6ea83f50d96af10e48`, producing identical bytes for
the current sources. From the SpecGraph root, with `OUT` naming a directory
outside the checkout:

```sh
ontologyviz --profile specs/models/review/ontology-overview/ontology.profile.json \
  --format json --out "$OUT"
```

Open `$OUT/ontology.graph.json` in SpecSpace at `/ontology?source=local`.
The inspector shows the owning package and pointer; package filters can hide
scaffolding or narrow the comparison. The file is a compiler-derived draft
projection of declarations, not executable evidence.
