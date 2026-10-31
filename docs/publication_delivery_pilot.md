# Publication delivery pilot

One bootstrap feature: `specgraph.publication.verify_bundle`.
Its canonical requirement is
[`SG-SPEC-0071`](../specs/nodes/SG-SPEC-0071.yaml), requirement
`SG-REQ-PUBLICATION-VERIFIED`. Proposal `0215` already implements the
publication path. This pilot joins its existing signals.

## Passport and bindings

For source-bound declaration diagnostics without executing this pilot, use
[Exact publication trace links](publication_trace_links.md). That report keeps
declared and resolved links separate from test/runtime observations.

- [Feature Passport](../tools/feature_passports/static-publication.json), draft
  `0.1.0`, local criteria `PB-ALL`, `PB-PAYLOAD`, `PB-MANIFEST`,
  `PB-CHECKSUMS`, `PB-MISSING`.
- [Explicit pytest bindings](../tools/feature_passports/static-publication-bindings.json).
- `tools/static_artifact_incremental_stage.py::verify_remote_bundle` is the
  implementation anchor; the adapter records actual Git revision and file
  digests. These Python locators do not use the Swift source resolver.

The external profile is FeaturePassport's
[`linked_delivery_signals_v1`](https://github.com/0al-spec/FeaturePassport/blob/832e922e80b2f6e48b06445b8ed44bc61e1b21bb/docs/contracts/linked-delivery-signals-v1.md).
It is provider-reported, function-level evidence with `admission: not_evaluated`.
The profile does not activate the separate `tests_verified_v1` plan in proposal
`0225`, reinterpret signed receipts, or alter the existing claim gate.

## Rule, intent atom, implementation and test

The canonical rule inventory is `SG-SPEC-0071.atoms.intents[]`. Every atom has
a stable local ID and executable `verifiable_by` selectors. The five publication
criteria refer to those atoms by `intent_atom_id`; the bindings file names the
actual SpecificationCore objects used by the adapter for evidence decisions.
The table below abbreviates module paths under `tools/publication_evidence/`.

| Intent atom | Rule / implementation | Executable check |
| --- | --- | --- |
| `PB-ALL` | Matching metadata and payloads; existing `verify_remote_bundle` | `test_verify_remote_bundle_hashes_every_manifest_file` |
| `PB-PAYLOAD` | Payload digest mismatch; existing verifier | `test_verify_remote_bundle_fails_on_digest_drift` |
| `PB-MANIFEST` | Stale manifest; existing verifier | `test_verify_remote_bundle_fails_on_stale_published_manifest` |
| `PB-CHECKSUMS` | Stale checksums; existing verifier | `test_verify_remote_bundle_fails_on_stale_checksums` |
| `PB-MISSING` | Missing remote payload; existing verifier | `test_verify_remote_bundle_fails_on_missing_remote_payload` |
| `PE-BINDINGS` | Complete distinct bindings; `bindings_spec.BINDING_ERROR_SPEC` | `test_binding_contract` |
| `PE-CASE` | One completed case, failure precedence; `case_spec.TEST_CASE_SPEC` | `test_test_case_decision` |
| `PE-SUITE` | Full passing suite, runner failure precedence; `suite_spec.TEST_SUITE_SPEC` | `test_test_suite_decision` |
| `PE-SNAPSHOT` | Relevant source bytes unchanged; `snapshot_spec.SOURCE_SNAPSHOT_SPEC` | `test_changed_source_during_tests_cannot_report_success` |
| `PE-TEST-IDENTITY` | Same source, execution and obligations; `bound_observation_spec.TEST_OBSERVATION_SPEC` | `test_test_observation_identity` |
| `PE-HTTP` | Matching origin, bundle, payload count and execution; `http_observation_spec.HTTP_OBSERVATION_SPEC` | `test_http_observation_identity` |
| `PE-OBSERVER` | Known native observer, separate target scope; HTTP policy and stage projection | `test_stage_provenance_separates_ci_execution_and_production_target` |
| `PE-ACCEPTANCE` | Merged PR for this revision; `merged_revision_spec.MERGED_REVISION_SPEC` | `test_merged_revision_acceptance` |

`test_every_declared_atom_has_a_real_test_and_policy_binding` checks that the
inventory has distinct IDs, real test functions and matching policy bindings
whose symbols the production adapter actually uses. This checks trace structure;
the listed behavioral tests check the decisions. No runtime coverage is inferred
from the existence of a reference.

The report's `tests` stage still covers the five bound `PB-*` feature scenarios.
The `PE-*` tests verify the evidence adapter through the ordinary Python suite;
their declaration does not add them to that five-scenario observation artifact.

Policies receive frozen typed contexts and perform no I/O. `FirstMatch` gives
binding errors, case outcomes and suite outcomes explicit precedence. The same
suite policy evaluates fresh JUnit and retained JSON; the same snapshot policy
is used during collection and when joining retained evidence. Parsing XML/JSON,
reading files, invoking pytest and projecting report fields stay in the adapter.
The source identity includes every extracted policy/context module.

Both publication producers obtain their native execution identity through
`publication_evidence.execution_context.PublicationExecutionContext`, a frozen
snapshot of an explicitly supplied environment mapping. Its projections retain
the existing four-field test provenance and six-field HTTP execution context.
This is shared adapter mechanics; it does not determine evidence admissibility,
infer a missing revision or change the policies above. The HTTP verifier retains
its standard-library-only import path. The context module is included in the
existing publication source digest inventory.

`PE-OBSERVER.verifiable_by` also names
`test_publication_producers_preserve_execution_contract`: its parameterized
cases check the native identity projections for local execution, GitHub Actions,
a custom GitHub server/repository and partial environment data. This complements
the existing stage-separation and missing-observer checks; it does not add a
policy or expand the five-scenario `PB-*` execution report.

JSON object reading and report writing are shared through `tools/artifact_json.py`
with the active-candidate and intake-clarification tools. The public facades keep
their argument order, non-object diagnostics and exception types. Reports retain
UTF-8 encoding, ASCII escaping, sorted keys, two-space indentation and a trailing
newline; the HTTP verifier also retains its separate stdout summary. The shared
module is explicitly included by `PE-SNAPSHOT`, with
`test_shared_json_change_invalidates_publication_source_snapshot` as an additional
`verifiable_by` regression binding. Artifact-specific validation and evidence
admissibility remain in their existing adapters and policies.

This refinement also closes two identity gaps: test reports must name the same
repository, and a local projection cannot reuse an HTTP report for another
recorded revision. A change only to the working-tree clean/dirty flag is
diagnostic; changes to relevant source bytes invalidate test evidence.

The v1 analyzer/profile is unchanged. It now counts the 13 explicit atoms and
retains the three broad `acceptance[]` entries as non-counted context. This is a
documented source-mode transition, not a claim that the behavior grew by ten
new requirements. Five atoms describe the pre-existing verifier; eight describe
the evidence adapter's obligations. Typed contexts and named rules add source
code; assess the complete adapter plus policy family when comparing metrics.

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

The deploy job sets up its own Python 3.10 environment and installs the project's
runtime dependencies before invoking tools. Build-job package installations do
not carry into the deploy job. The deploy job downloads that run's test signals
and the bundle. The existing
HTTP verifier now records the checked manifest/checksum digests, observation time
and Actions source/run/attempt identity. A successful HTTP result joins only to
the matching expected bundle and current run. It confirms published bytes; the
Python observer executes in Actions, not on the static host.

Joining an HTTP observation requires a known source revision equal to the
report's revision, including local projections. A local verifier without
`GITHUB_SHA` can verify HTTP bytes but does not supply that revision binding;
its linked deploy/runtime stages remain `missing`. Empty expected and observed
revisions cannot confirm the link either.

Every stage records separate `provenance.observer` and `provenance.target`
objects. The observer identifies the actual CI/local process and its native
run/attempt reference; the target identifies the environment and URI being
observed. For deploy/runtime, the reviewed bindings explicitly pair
`runtime_environment: production` with `https://specgraph.tech`. Test targets
are the CI/local test execution; intent/spec targets are the source revision;
acceptance targets GitHub repository metadata. The report's top-level
`--environment` labels the projection context only and never overrides these
stage environments. A locally projected native CI report retains its CI observer.
Missing runtime observations have a null observer and the intended target;
that target does not establish a successful deployment.

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

## Offline PB-ALL check for one deployment

Enable `capture_root_paths` in a manual **Publish Static Artifacts** run to
sample the root bundle. This runs the normal deployment. During its successful
HTTPS verification attempt the verifier records each fetched path and the
SHA-256 of the bytes it received, including the two metadata files. The root
receipt binds the exact bytes of `root-path-observations.json` by SHA-256.
Failed attempts contribute no rows to the successful attempt. The option
defaults to off and applies only to the root.

After the run completes, download the build and deploy artifacts from the
same run and use the offline reader from that revision. Use a fresh directory.

```bash
gh run download "$RUN_ID" -R 0al-spec/SpecGraph -n specgraph-static-artifacts -D evidence/bundle
gh run download "$RUN_ID" -R 0al-spec/SpecGraph -n specgraph-incremental-deployment-reports -D evidence/deploy
python3 tools/publication_path_coverage.py \
  --run-id "$RUN_ID" \
  --bundle-dir evidence/bundle \
  --receipt evidence/deploy/root-verification.json \
  --observations evidence/deploy/root-path-observations.json
```

The reader needs only the root `artifact_manifest.json` and `checksums.sha256`
from the build. It compares the expected and observed path/digest pairs
including repetitions, checks the receipt binding, origin and attempt, and
prints missing or unexpected paths. Exit 0 means complete matching evidence,
1 means a comparison failed, and 2 means the inputs could not be read as that
contract. This is a retrospective check of one provider-reported observation.

## Interpretation

| Stage | Meaning of success |
| --- | --- |
| intent | An authored, addressable intent exists in the passport/spec |
| spec | The authored requirement and explicit test bindings exist |
| tests | The required bound pytest functions passed for the recorded snapshot |
| deploy | The expected root bundle was observed at the HTTP origin |
| runtime | The HTTP verifier observed matching metadata and every payload |
| acceptance | A GitHub PR was merged into exactly the recorded revision and repository |

Intent/spec success describes authored declarations. Deploy/runtime share one
HTTP observation, rather than two independent confirmations. The report links
these sources; it does not establish a full requirement-to-assertion runtime trace.

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
