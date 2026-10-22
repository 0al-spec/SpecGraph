# Exact publication trace links

RFC 0226 resolution prerequisite for the SG-SPEC-0071 publication pilot.
Profile: `specgraph.publication-exact-links/v1`.

## Run

```bash
.venv/bin/python tools/publication_trace_links.py \
  --repository-root . --revision <commit>
```

The command prints a `publication_trace_links` JSON report to stdout. Capture it
in a task-local output directory if needed. Exit 0 means collection completed,
including reports with `needs_review`; this diagnostic is not a merge gate.
An invalid revision or malformed/missing required inventory exits 1, writes an
error to stderr, and produces no JSON report. There is no default revision or
implicit selection of a latest artifact.

## Flow and boundaries

```text
selected Git commit
  -> spec + passport + publication bindings
  -> authored IDs and references
  -> static Python declarations from the same Git commit
  -> REFERENCE_STATUS_SPEC
  -> declared links + exact resolution + source provenance
```

`tools/traceability/context.py` holds immutable facts and results.
`references.py` resolves exact keys within one explicitly bounded node inventory.
`reference_status_spec.py` owns the named resolution policy.
`POLICY_ATOM_BINDINGS_SPEC` and `ATOM_ROLES_SPEC` own mapping completeness and
inventory-role coverage in separate source modules, using immutable
`PolicyAtomBindingsFacts` and `AtomRolesFacts`. The adapter collects their inputs
and serializes findings; it does not recompute their predicates.
`publication.py` adapts the existing pilot inputs and reads regular Git blobs
through the shared `GitSources` boundary. The CLI composes these pieces.
The additive [EvidenceProvider](evidence_provider.md) interface consumes the same
single collection as immutable facts. This diagnostic remains separate from
the new declaration-only TraceSnapshot.
No measured Python module is imported or executed. Working-tree edits cannot
replace a declaration in the selected revision. A symlink is not a regular
source blob.

## Inventory and links

The selected spec comes from `tools/feature_passports/static-publication-bindings.json`.
The report enumerates `atoms.intents`, requirement criteria, passport criteria,
bound tests, policy atom IDs and policy/implementation declarations. Authored
links retain their source path and JSON pointer even when resolution fails.
Candidates retain exact source locations, syntax kinds and whole-file SHA-256.

The existing `BINDING_ERROR_SPEC` checks criterion/binding completeness and
distinct selectors. Additional diagnostics retain missing policy bindings,
duplicate IDs, empty or repeated atom channels and bound tests absent from the
criterion's atom. Duplicate IDs are reported rather than coalesced. An incomplete
or malformed required inventory never becomes a successful empty collection.

For Python, this profile resolves direct top-level functions and single-name
assignments. Pytest channels additionally require `tests/**/test_*.py::test_*`.
Decorators and parameterized function bodies are retained in source, but the
profile does not select individual parameter instances. Class methods, imports,
aliases, re-exports, conditional declarations and dynamic exports do not resolve
as direct targets. Assignment resolution proves the declaration exists; it does
not establish the value's runtime type, Specification semantics or actual use.

Local IDs use exact spelling in a single node scope. Ranges are never expanded:
an invalid range syntax is `unsupported`, and a syntactically valid string which
names no actual ID is `unresolved`. A caller combining multiple nodes must keep
their inventories separate. Human-readable identity aliases from Zeusus are not
silently treated as a shared runtime event schema by this profile.

## Outcomes and provenance

`REFERENCE_STATUS_SPEC` applies this precedence:

| Status | Meaning |
| --- | --- |
| `unsupported` | The reference is outside this exact-ID/direct-declaration profile |
| `unavailable` | The required target source cannot be read or parsed |
| `unresolved` | The available inventory contains no exact target |
| `ambiguous` | More than one direct declaration has that key |
| `wrong_kind` | One declaration exists, but it is not the expected function/value kind |
| `resolved` | One supported declaration of the expected kind exists |

The report-level `status` is `resolved` only when all selected references resolve
and inventory/mapping diagnostics are empty; otherwise it is `needs_review`.
`atom_inventory.complete` describes unambiguous atom enumeration, independently
of missing test files. `resolution_counts` counts authored link occurrences,
including repeated uses of one target; it is not an atom coverage percentage.

`source_revision` is the full measured Git SHA. `sources` binds each input to its
digest or an unavailable diagnostic. `analyzer` identifies the executing
implementation by version and source digests, separately from the measured
revision. `content_sha256` deterministically hashes the report before that field
is added, using sorted compact JSON with UTF-8 and no nonfinite values. No
collection timestamp participates in this content identity. These hashes are
provenance, not an authenticated runtime attestation.

`source_lifecycle` preserves the selected YAML's own status and gate. It is not
overwritten with a later Supervisor run's state. Candidate-aware formal review
projection requires separate run/digest provenance and is not implemented here.

The report explicitly retains:

```json
{
  "execution": "not_collected",
  "fulfillment": "not_evaluated",
  "admission": "not_evaluated",
  "readiness": "not_evaluated",
  "canonical_mutations_allowed": false
}
```

This prerequisite does not compute atom SVC, change the legacy proxy or S/U,
implement the full EvidenceProvider/TraceSnapshot contract, validate Swift
declarations or activate trusted evidence admission.

## Observation and regression evidence

The [pinned observation](evidence/0226_publication_link_resolution.json) records
the real pilot's inventory and resolution results. Tests cover absent and
ambiguous targets, wrong declaration kinds, unsupported selectors, Git symlinks,
malformed/missing inventories, old-revision isolation and independent CLI use.
Mapping policy tables preserve duplicate, missing, extra, empty and overlapping
role behavior; adapter-integration tests require the named policy outcomes to
drive findings and report status.

Zeusus intake on 2026-10-22 supplied negative-case requirements: a nonexistent
obligation ID, scenario range strings and a missing planned target. Small
synthetic examples in `tests/test_publication_trace_links.py` exercise the common
exact-ID resolver. They do not claim validation of Zeusus's whole package or
execution of its 100 authored scenarios. Future product adapters must validate
their own mapping schema and explicit aliases before feeding that resolver.
