# EvidenceProvider and declaration TraceSnapshot

RFC 0226 slice C1 implements the first provider boundary. It collects publication
atoms and static resolutions; execution evidence and atom SVC remain follow-ups.

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

Next: an explicitly selected publication execution-artifact provider retaining
producer outcome, revision, run identity and freshness. Metric qualification and
viewer integration remain separate reviewed changes.
