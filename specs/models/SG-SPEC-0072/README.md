# SG72-MIXED: a local formal scenario

This optional model accompanies SG-SPEC-0072. It asks one question: when a
duplicate package identity is detected and the compiler is unavailable, does the
result remain invalid while retaining both diagnostics?

- `mixed-outcome.feature` is the readable scenario.
- `source-map.json` selects exact clauses from the spec and keeps all four
  acceptance rows visible: one partial, three unmodelled.
- `domain-ontology-package.yaml` is a local draft vocabulary extension.
- `model.ts` uses the SDK generated from that draft and project-local
  `specgraph-core` to construct the example.

Edit these source files, then run the pilot from repository root using Python
from the repository environment. Supply an existing ontologyc and TypeScript
compiler; generated SDK/JavaScript and the report go to a new scratch directory:

```sh
.venv/bin/python tools/local_ontology_pilot.py \
  --ontologyc /absolute/path/to/ontologyc \
  --tsc /absolute/path/to/typescript/bin/tsc \
  --work-dir /absolute/path/to/new-run
```

The reference toolchain is SpecGraph's pinned Ontology 0.2.0 source revision
`1a47f7058228efb412cbdeaabbaf27bca25e9846`, TypeScript `6.0.3`, and Node.js.
The existing Ontology compatibility workflow documents building ontologyc from
that revision. TypeScript can be installed in a separate tool directory with
`npm install --prefix /path/to/toolchain --no-audit --no-fund typescript@6.0.3`.
Use the configured external build/cache locations for local work. The pilot
does not install dependencies or change the project's selected ontology.

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
outcome/diagnostics; these checks are not supplied by the SDK alone. A bounded
execution calls the existing project-context implementation with duplicate
selection and a missing compiler. Gherkin is linked descriptive input, not a
general-purpose step-definition engine.

The model is a test declaration, not a factual EventCore record. Imported
vocabulary stays draft. The local package is not added to global ontology
selection, and optional shared relations do not become globally mandatory.
Passing this example does not establish completeness of SG-SPEC-0072.

Source clauses and their mapping are authored and reviewed by a person/agent.
The tool checks the selected source bytes, node ID and fixed clause inventory;
it does not infer the meaning of arbitrary prose. The Gherkin tag identifies
this case, while its step text is descriptive and is not executed or compared
semantically. The two local diagnostic strings are test-fixture expectations,
not a new specification-wide promise about exact error-message wording.

Return to the [pilot record](../../../docs/reviews/0233_mechanical_specification_authoring/local-model-pilot/README.md)
for observed results and the next task.
