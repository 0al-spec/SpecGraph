# EvidenceProvider and declaration TraceSnapshot

RFC 0226 slice C1 implements the declaration provider boundary. Slice C2a adds
explicit retained publication execution artifacts. Atom SVC remains a follow-up.

## Run and composition

```bash
.venv/bin/python tools/publication_trace_snapshot.py \
  --repository-root . --repository-id 0al-spec/SpecGraph \
  --revision <commit> --spec-id SG-SPEC-0071
```

```mermaid
flowchart LR
    R[EvidenceRequest: explicit scope] --> G[EvidenceRegistry]
    G --> P[PublicationEvidenceProvider]
    P --> C[One pinned resolver collection]
    C --> E[Typed ProviderEvidence]
    E --> S[Immutable TraceSnapshot]
    S --> D[Diagnostics and future metric adapters]
```

`EvidenceProvider` is a Python Protocol: `collect(request) -> ProviderEvidence`,
with `provider_id` and `version`. `EvidenceRegistry` receives reviewed in-process
implementations and invokes each explicitly selected provider once. The default
built-in is `publication.declarations`; `--provider` selects registered IDs.
Unknown/duplicate IDs, invalid subject selection and mismatched result
identity/version/scope are errors. No dynamic imports or plugin discovery occur.

The CLI pins the supplied revision to a full SHA. `EvidenceRequest` carries an
absolute repository root, immutable `EvidenceScope`, explicit node selection
and artifact selection. This first provider requires exactly SG-SPEC-0071 and
`specgraph.publication-exact-links/v1`, rejecting nonempty `artifact_paths`.
It never selects a latest report, runs measured code, tests, network observations
or inference. Constructors and imports do not collect sources.

`collect_publication_links` returns a `PublicationLinkCollection` with immutable
atom declarations/resolutions and the original JSON projection. The provider
consumes this single collection without rereading YAML or inferring atoms from
links. `build_publication_links` preserves the existing business fields and CLI
contract; analyzer fingerprints/content digests change with analyzer code.

## Facts and completeness

`evidence.py` defines typed immutable facts; `publication_provider.py` adapts
inputs. Pure `snapshot.py` performs no Git, filesystem, configuration or artifact
I/O. `ProviderEvidence` retains provider ID/version/profile, analyzer-file hashes,
scope, source digests or unavailable diagnostics and the collection digest.
Each `NodeEvidence` retains all atom declarations, authored links, resolution
candidates, mapping findings and original YAML lifecycle state.

Atom addresses contain spec/local atom ID, file path, JSON pointer and file
digest under the measured revision. File provenance is not presented as a
canonical per-Requirement revision, lineage decision or approval.

Each node has independent flags:

- `inventory.complete`: complete, unambiguous atom enumeration from the resolver.
- `declaration_resolution.complete`: supported resolution with available sources.

`RESOLUTION_COMPLETENESS_SPEC` accepts completed `resolved`, `unresolved`,
`ambiguous` and `wrong_kind` observations. Unsupported, unavailable and unknown
statuses are incomplete. Completeness is not success: a conclusively missing
function is a completed failed resolution. A missing test file leaves a valid
atom inventory complete while making resolution incomplete.

Missing/malformed required spec/passport/binding returns an explicit node with
both flags false and `publication_source_unavailable`, never an apparently
complete empty inventory. Retained partial resolutions and unavailable sources
remain visible. Incomplete evidence is an informational JSON report (exit 0).
Invalid configuration or nonexistent revision exits 1 with no JSON. The older
diagnostic CLI's error behavior remains unchanged.

## Determinism and conflicts

`TraceSnapshot` uses `specgraph.trace-snapshot/declarations-v1`. Its constructor
enforces exact scope/revision and coverage of every selected node, including
unavailable-node records. Nested collections are immutable; serialization
returns fresh JSON containers. These invariants also apply to direct API callers.

Reports and facts are canonically ordered. `content_sha256` uses sorted compact
JSON, excludes checkout location and collection time, and is independent of
provider registration/selection order. Digests record provenance, not
authentication of provider claims.

`observed_subjects` coalesces `(spec_id, atom_id)` across providers while retaining
every report. `observed_subject_count` is not an exact SVC denominator for
incomplete inventories and is never a coverage ratio. `FACT_AGREEMENT_SPEC`
reports differing atom-source or declared-link observations as conflicts with
all variants and origins, without choosing a winner. Other diagnostics,
completeness and lifecycle remain in their original reports rather than becoming
a global approval/health verdict.

## Limits and observation

This profile retains `execution: not_collected`, `fulfillment: not_evaluated`,
`readiness: not_evaluated`, `admission: not_evaluated` and
`canonical_mutations_allowed: false`. It does not implement execution-event
schemas, atom SVC, legacy metric migration, S/U changes, graph maturity,
`tests_verified_v1` or trusted receipt admission.

The [pinned observation](evidence/0226_publication_provider_snapshot.json) records
the actual inventory/snapshot and comparison with the earlier diagnostic.
Synthetic multi-provider tests cover order independence, duplicate identity
coalescing, explicit conflicts and stale scope; they do not claim real additional
providers or executed product tests.

## Retained execution artifacts (C2a)

`PublicationExecutionEvidenceProvider` (`publication.execution`) reads existing
producer JSON, without running pytest, the HTTP verifier, source imports or
inference. Add it explicitly alongside the declaration provider:

```bash
.venv/bin/python tools/publication_trace_snapshot.py \
  --repository-root . --repository-id 0al-spec/SpecGraph \
  --revision <artifact-source-commit> --spec-id SG-SPEC-0071 \
  --provider publication.declarations --provider publication.execution \
  --tests-report /absolute/selected/tests.json \
  --delivery-report /absolute/selected/report.json \
  --run-id <github-run-id> --run-attempt <attempt>
```

At least one report is required; paths and run selection never come from a
latest directory or environment. CLI relative paths resolve against the caller's
working directory. API callers provide absolute paths in immutable
`PublicationExecutionSelection`, independently of the legacy `artifact_paths`
field (which remains rejected). The default declaration-only CLI is unchanged.

Supported producer contracts are `specgraph_publication_test_observation`,
schema 1, and `feature_delivery_signals`, schema 1, profile
`linked_delivery_signals_v1`. The adapter reads up to 2 MiB per selected file,
rejects duplicate JSON keys/nonfinite values and preserves valid parsed producer
reports without rewriting outcomes. Original byte hashes are recorded under
stable `artifact:tests` / `artifact:delivery` source labels; moving identical
selected files does not change snapshot identity. Unavailable/malformed inputs
produce diagnostics and no invented success. Unknown profiles remain unavailable.

The expected file inventory is reconstructed from Git objects at the requested
SHA using the existing producer's inventory: bindings, passport, spec,
implementation, test files, JSON I/O, producer and publication policy package.
`SOURCE_SNAPSHOT_SPEC` compares repository, revision and the exact file hashes;
the current working copy is not the reference. `EXECUTION_BINDING_SPEC` requires
the selected complete GitHub Actions identity (provider, run, attempt and
repository-specific run URI). Current local producers use ambiguous `local-run`
with empty IDs, so they cannot provide this binding profile. Invalid selection
is a CLI error; a stale/missing observation is an informational snapshot.

For tests, `TEST_OBSERVATION_SPEC` checks the exact ordered criterion/test
selectors; `TEST_SUITE_SPEC` interprets the retained case outcomes and exit code.
The original `producer_result` remains separate from `evaluated_result`. A bound
failed suite remains failed; mismatched inputs never receive an evaluated result.
The delivery report retains its normalized tests/deploy/runtime outcomes. Its
test selectors and observer identities are checked. For claimed deploy/runtime
signals, `RETAINED_RUNTIME_BINDING_SPEC` checks the embedded HTTP observation's
revision, full run identity, origin and bundle identity against the selected
report and pinned origin. An externally bound report can still contain an
internally mismatched signal; both statuses remain visible. A producer's missing
signal with no observer is `not_asserted`.

This adapter checks provenance binding, not authenticity or HTTP bytes. It does
not rerun native verification, reread JUnit/XML or bundle payloads, establish
wall-clock freshness, select the newest attempt or authenticate GitHub claims.
Timestamps and all producer metadata stay inside retained reports. Freshness is
explicitly limited to the caller-selected revision and run; digests do not turn
`provider_reported_not_attested` data into trusted receipts. Contradictory retained
outcomes stay separate by artifact/stage; C1 atom/link conflict rules do not pick
an execution winner.

Selecting this provider uses `specgraph.trace-snapshot/execution-v1` and
`execution: retained_artifacts`, including explicit unavailable-artifact entries.
This means collection was attempted, not that execution succeeded. Execution
providers supply no atom inventory: their node completeness flags stay false.
Composition preserves the declaration inventory and does not multiply subjects.
The declaration-only profile and JSON shape remain intact. Fulfillment,
readiness and admission remain `not_evaluated`; canonical mutations stay disabled.

The [real CI observation](evidence/0226_publication_execution_snapshot.json) uses
explicitly downloaded build reports from run `39757869156`, attempt 1, at its
actual PR merge-checkout SHA. Five pytest obligations report success; deploy and
runtime remain missing because this PR run skipped deployment. Synthetic offline
fixtures cover successful HTTP observations and negative binding cases; they do
not establish a live deployment.

Next: qualify atom-to-check channels for a separately reviewed SVC profile and
connect snapshot diagnostics to the existing viewer. Neither is activated here.

## Retained Cucumber criterion observations (C2c)

The explicit `criterion.retained_cucumber` provider produces
`criterion_observation_report/v1` through the existing registry and
`TraceSnapshot`. The additive snapshot profile is
`specgraph.trace-snapshot/criterion-observations-v1`. The snapshot
reports the retained-artifact capability independently of observation
success. The collector profile is
`specgraph.criterion-observation/cucumber-messages-34.2.1-v1`. Select one
Git repository, one full commit ID, one spec node, and its entire
`acceptance` list of strings. The provider reads the pinned Git blob and retains
its lifecycle, exact text, file SHA-256 and JSON Pointer for every criterion.
An unreadable or invalid inventory has no criterion count. A readable inventory
with a mismatched pin retains its rows as invalid. Subset selection is outside
this profile.

Run from SpecGraph with the repository Python environment. The roots and
variables below refer to inputs prepared by the operator. Each `PATH SHA256`
pair is independent and `--journal` can be repeated for additional artifacts.

```sh
python tools/criterion_observation_report.py \
  --repository-root "$source_checkout" --retained-root "$retained_artifacts" \
  --repository-id "$repository_id" --workspace "$workspace" \
  --revision "$declaration_commit" --spec-id "$spec_id" \
  --spec "$spec_path" "$spec_sha" \
  --passport "$passport_path" "$passport_sha" \
  --binding-plan "$plan_path" "$plan_sha" \
  --journal "$journal_id" "$journal_path" "$journal_sha" \
  --validator "$trusted_feature_passport_binary" --validator-sha256 "$validator_sha"
```

The executable is a trusted, operator-installed native `feature-passport` tool
with an adjacent SwiftPM/Xcode resource bundle. The adapter pins its binary
digest and checks the bundled v1 schema from FeaturePassport commit
`0fe35e9edb1461744ffa89161ec64cc86d44f728`. It passes the captured, hash-checked
passport bytes to the native `validate` command. This checks schema shape and
local references, including the test element role. Tool and resource custody
are the operator's responsibility. The provider reads pinned Git objects and
explicit regular files, up to 2 MiB each. The retained root constrains retained
paths. Only the operator selects the validator, never the evidence package.
The CLI prints one report and returns 0 when that report was produced, including
a report with gaps or failures. Invocation errors produce a nonzero status.
Treat output as local diagnostic data because it includes selected JSON
attachment values.

### Binding plan v1

The pinned JSON object has the exact keys below. SHA-256 pins are lowercase hex.
The scope fields also appear in the selected passport `specgraph` contract
locator, alongside `pointer` and `scenario_id`.

| Field | Shape |
| --- | --- |
| `artifact_kind` | `criterion_observation_binding_plan` |
| `schema_version` | `1` |
| `profile` | `specgraph.criterion-observation/cucumber-messages-34.2.1-v1` |
| `scope` | `workspace`, `repository`, `node_id`, `revision`, `path`, `sha256` |
| `passport_sha256` | Exact passport bytes |
| `journals[]` | `artifact_id`, `sha256`, `run_id`, `test_source_revision`, `execution_source_revision`, and `feature` with `path`, `sha256` |
| `bindings[]` | `pointer`, `criterion_id`, `contract_ref_id`, `passport_binding_id`, `artifact_id`, `case_id`, `case_started_id`, `attempt`, `assertions` |
| `bindings[].assertions[]` | `id`, `step_id`, `media_type`, `expected_measurement` as a JSON object |

Each pointer is `/acceptance/N` in the selected Git blob. The selected passport
criterion text must match exactly. Its named implementation binding must name
that criterion, the selected `implements` contract reference and at least one
test element. A plan journal declaration must match its independently selected
artifact digest. Each binding has at least one expected assertion. Each
assertion selects one step and JSON attachment media type. The entire observed
JSON object is compared with the expected object using a stable key order.
The report takes measured values from the retained attachment. The plan carries
expectations only. Binding integrity, observed outcome and admission are
reported separately. A checked binding can yield a failed outcome.

### Supported journal profile

- UTF-8 NDJSON Cucumber Messages `34.2.1`, one run per artifact. Select the
  exact test case and case start. Attempt 0 is supported when the selected
  case has no retry or ambiguous selection. A run may contain other cases
  and supply multiple assertions or criteria.
- The selected test case and attempt must join the sole run and pickle. The
  pickle names the pinned feature URI and explicit `@specgraph-id=<scenario_id>`
  tag. The journal source text must match the feature bytes in both selected
  test and execution commits. The execution commit must also contain identical
  spec bytes. These compatibility checks allow distinct revisions while
  preserving `producer_declared` source-build provenance. They do not
  independently resolve test source anchors, compile Gherkin, or attest checkout.
- Every case step, including hooks, needs a passing result for the criterion
  to pass. Run and case must finish and every expected attachment must be
  present and match. Unrelated cases do not supply results or measurements
  for the selected attempt. When its own steps and assertions pass but the
  overall run reports failure, the criterion is partial and retains
  `run_success: false` plus the passing selected-step facts. The report
  retains available step statuses and measurements. Unfinished, missing, skipped, pending,
  unsupported, and failed evidence remain distinguishable. Attachments use
  `IDENTITY` encoding and `application/json` or `application/*+json` types.
- Exact repeated plan rows and identical journal messages are idempotent.
  Inconsistent records for the same selected identity remain conflicts.
  The raw plan and journal fingerprints still reflect duplicates and ordering.
  Unknown journal versions, retries of the selected case and alternate
  attachment encodings remain outside the supported profile.

`tools/traceability/` keeps the decision policies in separate modules.
`CRITERION_PASSPORT_BINDING_SPEC` checks the declaration join,
`CRITERION_BINDING_INTEGRITY_SPEC` classifies binding findings and
`CRITERION_OBSERVATION_OUTCOME_SPEC` evaluates the observed outcome. Git, file
and native-tool invocation, Cucumber indexing and serialization are adapters.
The report carries `admission: not_evaluated` and a null receipt. Proposal
0225 owns future trusted admission. C2b, legacy acceptance coverage, S/U and
existing publication snapshots retain their existing behavior.
