# Local formal scenarios for SG-SPEC-0072

Both examples exercise the production rule for combining ontology checks.

| CLI scenario | Selected inputs | Expected context outcome |
| --- | --- | --- |
| `SG72-MIXED` (default) | Duplicate package selection and missing compiler | `invalid` with both diagnostics |
| `SG72-UNSUPPORTED-CLOSURE` | A pinned package with an import, verified source and IR, and an unsupported closure check | `unavailable` with both check results attributed to the same member |

Each example has a readable `.feature`, a source map with exact clauses and four
acceptance rows, and a typed declaration (`model.ts` or `unsupported-closure.ts`).
They share `case-model.ts`, the draft vocabulary in `domain-ontology-package.yaml`
and the SDK generated from that vocabulary and `specgraph-core`.

Edit these source files, then run the pilot from repository root using Python
from the repository environment. Supply an existing ontologyc and TypeScript
compiler; generated SDK/JavaScript and the report go to a new scratch directory:

```sh
.venv/bin/python tools/local_ontology_pilot.py \
  --scenario SG72-UNSUPPORTED-CLOSURE \
  --ontologyc /absolute/path/to/ontologyc \
  --tsc /absolute/path/to/typescript/bin/tsc \
  --work-dir /absolute/path/to/new-run
```

Use another empty work directory and select `SG72-MIXED` to compare both reports.

The reference toolchain is SpecGraph's pinned Ontology 0.3.0 source revision
`d831e25b46095dfea5e17befbc88c5fdcd03e031`, TypeScript `6.0.3`, and Node.js.
The existing Ontology compatibility workflow documents building ontologyc from
that revision. TypeScript can be installed in a separate tool directory with
`npm install --prefix /path/to/toolchain --no-audit --no-fund typescript@6.0.3`.
Use the configured external build/cache locations for local work. The pilot
does not install dependencies or change the project's selected ontology.

This local vocabulary declares no policy or lifecycle, so `policies` and
`stateMachines` are omitted. Ontology 0.3.0 supports this minimal form; the
previous 0.2.0 compiler required artificial declarations. The release
compatibility jobs check this package on macOS and Linux. The historical
observation retains the original input hashes and is not evidence for this edit.

Exit codes are `0` for this case satisfied, `1` for a model or behavior mismatch,
and `2` for a tool/environment failure. `report.json` retains per-layer results,
input/tool hashes, generated-file hashes and paths to command diagnostics.
An existing nonempty run directory is rejected, preserving its previous result.
The compiler binary is recorded by digest; this does not attest its source.

For the real-tool regressions, export `ONTOLOGYC_BINARY_PATH` and
`TYPESCRIPT_TSC_PATH` with the same executable paths, then run
`python -m pytest tests/test_local_ontology_pilot.py` from the repository
environment. Without those variables the integration cases explicitly skip;
the source-mapping cases still run. Use an external pytest `--basetemp` and
cache directory under the configured local build root.

## What the layers mean

The ontology compiler validates package structure and generates SDK files.
TypeScript checks model construction against those real generated types.
The local consumer checks the declared relations and this scenario's expected
outcome/diagnostics; these checks are not supplied by the SDK alone. Each case runs the existing project-context implementation. The closure case also
passes the selected compiler into that implementation to recompile the package
and compare the resulting IR with the captured bytes. Gherkin is linked descriptive input, not a
general-purpose step-definition engine.

The model is a test declaration, not a factual EventCore record. Imported
vocabulary stays draft. The local package is not added to global ontology
selection, and optional shared relations do not become globally mandatory.
Passing this example does not establish completeness of SG-SPEC-0072.

Source clauses and their mapping are authored and reviewed by a person/agent.
The tool checks the selected source bytes, node ID and fixed clause inventory;
it does not infer the meaning of arbitrary prose. The Gherkin tag identifies
this case, while its step text is descriptive and is not executed or compared
semantically. The local diagnostic strings are test-fixture expectations,
not a new specification-wide promise about exact error-message wording.

Return to the [pilot record](../../../docs/reviews/0233_mechanical_specification_authoring/local-model-pilot/README.md)
for observed results and the next task.
