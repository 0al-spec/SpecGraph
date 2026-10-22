# EvidenceProvider and TraceSnapshot

RFC 0226 slice C1 exposes `EvidenceProvider`, an explicit `EvidenceRegistry` and
immutable `TraceSnapshot` under `specgraph.trace-snapshot/declarations-v1`.

Run `tools/publication_trace_snapshot.py` with `--repository-root`,
`--repository-id`, `--revision` and `--spec-id SG-SPEC-0071`. The built-in provider
is `publication.declarations`, using `specgraph.publication-exact-links/v1`.
`EvidenceRequest` carries an absolute root and explicit immutable scope/selection.
Nonempty legacy `artifact_paths` selection is rejected. Unknown/duplicate provider
IDs, invalid cohorts and mismatched result identity/version/scope fail without
a snapshot. Provider selection is in process, without dynamic imports/discovery.

`PublicationEvidenceProvider` consumes one `PublicationLinkCollection`, reusing
the resolver's immutable atoms/resolutions. `build_publication_links` preserves
its business fields. Collection remains in adapters; snapshot assembly is pure.
There are no inference calls or measured-code execution. Reports retain provider
version/profile, analyzer/source digests, declarations, resolutions, diagnostics
and raw source lifecycle. File-and-pointer provenance is not a canonical
per-Requirement revision or approval.

Each node has independent `inventory.complete` and
`declaration_resolution.complete` flags. `RESOLUTION_COMPLETENESS_SPEC` accepts
completed resolved/unresolved/ambiguous/wrong-kind observations; unsupported,
unavailable and unknown statuses remain incomplete. Required-source failure
returns incomplete evidence with `publication_source_unavailable`, never a
complete empty inventory. Informational reports exit 0; invalid selection or
nonexistent revision exits 1. The older CLI's behavior is unchanged.

Nested collections are immutable. Reports/facts are canonically ordered;
`content_sha256` excludes collection time and checkout location.
`observed_subject_count` coalesces identities, not origins, and is not an exact
denominator for incomplete inventories. `FACT_AGREEMENT_SPEC` retains conflicting
atom-source/link observations with every variant/origin, without picking a
winner by provider order.

This profile retains `execution: not_collected`, `fulfillment: not_evaluated`,
`readiness: not_evaluated`, `admission: not_evaluated` and
`canonical_mutations_allowed: false`. SVC, legacy metrics, S/U, trusted receipt
admission and `tests_verified_v1` remain unchanged. Metric qualification requires
follow-up integration.

See `docs/evidence_provider.md` and the pinned observation at
`docs/evidence/0226_publication_provider_snapshot.json`.

## Retained execution provider (C2a)

Explicitly add `--provider publication.execution`, at least one `--tests-report`
or `--delivery-report`, and `--run-id` / `--run-attempt`. It composes with
`publication.declarations`. `PublicationExecutionSelection` carries absolute
paths and a full GitHub Actions identity; no environment or latest-file fallback
is used. Relative CLI paths resolve from the caller's working directory.

`PublicationExecutionEvidenceProvider` reads existing
`specgraph_publication_test_observation` schema 1 and
`feature_delivery_signals` schema 1 / `linked_delivery_signals_v1` reports.
It never executes pytest, HTTP, measured source or inference. Original hashes and
parsed producer outcomes are retained under stable role labels, without putting
local artifact paths in snapshot identity. Missing/malformed/unknown inputs have
explicit unavailable entries; JSON duplicate keys, nonfinite values and inputs
larger than 2 MiB are rejected.

The producer's expected file inventory comes from the selected Git revision.
`SOURCE_SNAPSHOT_SPEC` matches repository/revision/file hashes;
`EXECUTION_BINDING_SPEC` matches the complete selected run/attempt/URI. Ambiguous
local-run identities cannot satisfy this profile. `TEST_OBSERVATION_SPEC` checks
the exact ordered test bindings and `TEST_SUITE_SPEC` supplies an independent
`evaluated_result` without rewriting `producer_result`. Binding mismatch leaves
the evaluated result absent; complete failed observations remain failures.

Delivery test selectors and observer identities are checked. Embedded HTTP
revision, run, origin and bundle identity are checked through
`RETAINED_RUNTIME_BINDING_SPEC`. A matching outer artifact can contain mismatched
inner signals; each status is retained. A missing signal with no observer stays
`not_asserted`. Native HTTP bytes, JUnit/XML and bundle payloads are not reread.
No authenticity, newest-attempt or wall-clock freshness is claimed: this is
`provider_reported_not_attested` provenance for the selected revision/run only.
Conflicting execution outcomes remain separate by artifact/stage without a winner.

Execution selection produces `specgraph.trace-snapshot/execution-v1` with
`execution: retained_artifacts`: collection attempted, not successful execution.
This provider does not enumerate atoms; composition retains the original
declaration inventory. Declaration-only JSON remains unchanged. SVC, S/U,
fulfillment, readiness, canonical admission and mutation remain unchanged.

The real CI observation in
`docs/evidence/0226_publication_execution_snapshot.json` retains five successful
pytest obligations from run 39757869156 attempt 1 at its actual merge-checkout
SHA. Deploy/runtime stay missing because deployment was skipped on the PR.
Successful HTTP paths are tested through synthetic offline producer fixtures.
