# Inheritance validation gap, 2026-11-09

Status: **fixed in [Ontology 0.11.0](https://github.com/0al-spec/Ontology/releases/tag/0.11.0)**
by [PR #114](https://github.com/0al-spec/Ontology/pull/114). The original
observation is retained below for traceability.

The synthetic [cycle.yaml](cycle.yaml) has `A extends B` and `B extends A`.
Its SHA-256 is `904a5ce523bfbaeba55e8f7d3ec7af300878d4b85ded24c0cf151bbad30717c2`.
Both the released Ontology 0.10.0 compiler and a local build of the
[ONT-086 candidate](https://github.com/0al-spec/Ontology/pull/113) returned
success for `ontologyc check`. In a disposable Git repository with the fixture
staged, `advise-staged` returned success and emitted no diagnostic for the
cycle in either compiler.

The release compiler also returned success for `compile`. The ONT-086
candidate returned exit 1 with `class.inheritance.cycle` for both classes and
did not emit an SDK into a fresh destination. Thus the candidate protects SDK
generation, but does not yet make `check` or commit-time advice detect the
same invalid ancestry.

The release binary SHA-256 was
`ed6db089372b7ac4ad97eff89bb6f6e0825fbb6e5fea79d9181d75179850864e`.
The local candidate binary SHA-256 was
`395fd09c81f921d71dceac51ff5d0eb11e84fb10096961dc888837c2fbe57237`,
built from the code represented by candidate commit `4c65676a5ab9d37777e32a7f8ca8f28efdf0c7f3`.
These hashes identify locally exercised bytes; they do not authenticate the
executables or establish a published release.

The release adds source-attributed cycle and incompatible-field diagnostics in
`check`, `checkSources`, and `advise-staged`, including explicitly supplied
transitive imports. Advice retains its nonblocking exit contract; canonical
acceptance is separate from this compiler fix.
