# Publication delivery pilot

One bootstrap feature: `specgraph.publication.verify_bundle`.
Its canonical requirement is
[`SG-SPEC-0071`](../specs/nodes/SG-SPEC-0071.yaml), requirement
`SG-REQ-PUBLICATION-VERIFIED`. Proposal `0215` already implements the
publication path. This pilot joins its existing signals.

## Passport and bindings

- [Feature Passport](../tools/feature_passports/static-publication.json), draft
  `0.1.0`, local criteria `PB-ALL`, `PB-PAYLOAD`, `PB-MANIFEST`,
  `PB-CHECKSUMS`, `PB-MISSING`.
- [Explicit pytest bindings](../tools/feature_passports/static-publication-bindings.json).
- `tools/static_artifact_incremental_stage.py::verify_remote_bundle` is the
  implementation anchor; the adapter records actual Git revision and file
  digests. These Python locators do not use the Swift source resolver.

The external profile is FeaturePassport's
[`linked_delivery_signals_v1`](https://github.com/0al-spec/FeaturePassport/blob/bc47d9cf5ca0f528a0df6766a12266d0191f5974/docs/contracts/linked-delivery-signals-v1.md).
It is provider-reported, function-level evidence with `admission: not_evaluated`.
The profile does not activate the separate `tests_verified_v1` plan in proposal
`0225`, reinterpret signed receipts, or alter the existing claim gate.

## Run

```sh
make test-publication-delivery PYTHON=.venv/bin/python \
  PUBLICATION_EVIDENCE_DIR=/path/to/run/publication-pilot
make publication-delivery-report PYTHON=.venv/bin/python \
  PUBLICATION_EVIDENCE_DIR=/path/to/run/publication-pilot
```

Local builds/tests follow the host's configured cache/output policy. Pass an
explicit run directory and pytest cache/temp overrides when using external
storage. The CI default is `dist/publication-pilot`.

The first command runs only the five bound pytest functions using the normal
runner, retaining `tests.xml` and `tests.json`. A failed collection discards old
XML. Every required function must occur once, complete without skips or errors,
and the runner must exit zero. No test name infers coverage beyond its reviewed
binding. A partial, skipped or duplicated result is not success.

The report also retains the exact passport, requirement and binding inputs under
`inputs/`, so its table can be inspected from the downloaded artifact alone.

The report joins tests only for the same source snapshot and provider run/attempt.
Generated run artifacts may dirty unrelated tracked files; the relevant source,
passport, requirement, bindings, adapter and test file digests still have to match.
The clean/dirty flag remains visible. Local uncommitted runs describe their file
snapshot, not a claim that all bytes were committed at the reported Git parent.

## CI and publication

`publish-static-artifacts.yml` runs the bound tests before building the bundle.
It retains a pre-deploy report as the Actions artifact
`specgraph-publication-delivery-signals-build`. Missing deployment, runtime and
acceptance signals stay visible. This job runs on PRs without deploying them.

The deploy job downloads that run's test signals and the bundle. The existing
HTTP verifier now records the checked manifest/checksum digests, observation time
and Actions source/run/attempt identity. A successful HTTP result joins only to
the matching expected bundle and current run. It confirms published bytes; the
Python observer executes in Actions, not on the static host.

The post-deploy table and raw reports are retained in
`specgraph-publication-delivery-signals-deploy` for 30 days. JSON and Markdown
reports also appear in the job summary. Follow the run URL and artifact name in
the provenance to retrieve evidence; these are historical run observations,
not an assertion about a later deployment. HTTP failure or skipped deployment
cannot create a successful runtime signal. Missing native reports are shown as
missing; the original deploy job preserves its failure diagnostics.

The initial scope is the **root** bundle. Existing workspace verification
continues independently. No keys, signer service or new telemetry backend are
needed for this provider-reported profile. Raw artifacts remain in Actions;
the pilot does not publish them automatically to the public webroot.

## Interpretation

| Stage | Meaning of success |
| --- | --- |
| intent | An authored, addressable intent exists in the passport/spec |
| spec | The authored requirement and explicit test bindings exist |
| tests | The required bound pytest functions passed for the recorded snapshot |
| deploy | The expected root bundle was observed at the HTTP origin |
| runtime | The HTTP verifier observed matching metadata and every payload |
| acceptance | A GitHub PR was merged into exactly the recorded revision and repository |

Success is an observation under `provider_reported`, not a trusted admission
decision or a statement that tests are exhaustive. Ontology participates through
the existing `SG-SPEC-0020` vocabulary for code surfaces, tests, releases and
runtime results. Its job is semantic linkage, not execution adjudication.

For this engineering pilot, acceptance is a merged implementation PR. On push or
manual dispatch, the workflow retains native GitHub associated-PR metadata in
`associated-pulls.json`. The adapter matches `merged_at`, `merge_commit_sha` and
the base repository. Closed-but-unmerged PRs and another revision do not count.
Unavailable metadata remains missing without blocking delivery. Explicit customer
acceptance can be added as a separate source later. A separate production benefit
needs its own outcome criterion; merge metadata does not establish that benefit.
