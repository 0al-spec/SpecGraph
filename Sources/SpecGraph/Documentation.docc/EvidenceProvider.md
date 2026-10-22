# EvidenceProvider and TraceSnapshot

RFC 0226 slice C1 exposes `EvidenceProvider`, an explicit `EvidenceRegistry` and
immutable `TraceSnapshot` under `specgraph.trace-snapshot/declarations-v1`.

Run `tools/publication_trace_snapshot.py` with `--repository-root`,
`--repository-id`, `--revision` and `--spec-id SG-SPEC-0071`. The built-in provider
is `publication.declarations`, using `specgraph.publication-exact-links/v1`.
`EvidenceRequest` carries an absolute root and explicit immutable scope/selection.
Nonempty execution-artifact selection is rejected. Unknown/duplicate provider
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
admission and `tests_verified_v1` remain unchanged. Execution artifacts and metric
qualification require follow-up integration.

See `docs/evidence_provider.md` and the pinned observation at
`docs/evidence/0226_publication_provider_snapshot.json`.
