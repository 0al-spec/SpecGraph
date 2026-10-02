# Subject read model

The first implementation slice of RFC 0221 / SG-SPEC-0068 provides immutable
subject values, strict snapshot parsing, and read-only exact/current lookup.
The semantic contract was approved by the human and merged in PR #747 at
`ed8a00c7d34ab5df5f3c8c29460a8d9231a10311`. The subsequent human instruction
“Делай” authorized this bounded read-model implementation.

The subsequent [canonical-source adapter](subject_canonical_source.md), authorized
by the exact PR #752 packet approval, applies the stronger SG-SPEC-0069 storage
checks. Snapshot v1 optionally retains paired `node_fields`/`revision_scope` and
`retained_disposition_order`; legacy snapshots keep their existing output shape.

## Run a lookup

Use the repository Python environment:

```bash
.venv/bin/python tools/subject_read_model_io.py \
  --snapshot tests/fixtures/subject_read_model/snapshot.json \
  --workspace-identity workspace-a \
  --subject-class criterion --subject-id AC-1 --revision 1
```

Replace `--revision 1` with `--current` for the separately requested current
revision. The fixture returns revision 1 in `spec-a` for the exact request and
revision 3 in `spec-b` for current. Revision 2 is not retained and returns
`unavailable_revision`; no fallback supplies revision 3.

The CLI writes JSON to stdout and leaves the source unchanged. Exit codes:

| Code | Meaning |
| --- | --- |
| `0` | `resolved` with complete relation enumeration within the supplied snapshots; a retired subject can also resolve |
| `1` | Unresolved lookup, or resolved subject with incomplete relation enumeration |
| `2` | Invalid snapshot/reference, or invalid CLI arguments |

Data failures return `status: invalid_input` with a diagnostic. Argument errors
use standard argparse stderr. An unresolved result has no `resolved` payload.

## Explicit snapshot boundary

`subject_read_snapshot`, schema version 1, is an experimental exchange/fixture
format. It is not the canonical storage schema or a workspace declaration
format. YAML and JSON use the same strict fields; duplicate keys, unknown fields,
missing identifiers and malformed values are rejected. See the complete
[fixture](../tests/fixtures/subject_read_model/snapshot.json).

| Object | Fields |
| --- | --- |
| Snapshot | `schema_version`, `artifact_kind`, `workspaces` |
| Workspace | `workspace_identity`, `dataset_identity`, `subjects`, `relations` |
| Subject reference | `workspace_identity`, `subject_class`, `local_subject_id` |
| Revision selection | `subject`, `mode: exact` + positive integer `revision`, or `mode: current` |
| Subject | `reference`, `current_revision`, `revisions`, `current_disposition`, `canonical_presence`, `retained_disposition_transitions` |
| Revision | `number`, `predecessor`, `statement`, `containment`, `provenance`, `acceptance_criteria_refs` |
| Current disposition | `state: active/retired`, `basis_ref`, `observation_provenance` |
| Retained disposition transition | `event_ref`, `transition: activation/withdrawal`, `provenance` |
| Authored relation | `relation_id`, `kind`, `endpoints`, `provenance` |
| Endpoint | `role`, `selection` |

Identity is `(workspace_identity, local_subject_id)`. `subject_class` is either
`Requirement` or `criterion` and validates the selected record; it cannot make
duplicate IDs distinct. Workspace identities are explicit opaque values in this
boundary, with no UUID/URI syntax decision. Equal `dataset_identity` values
declare replicas of one source; they do not prove authority or trust. Only
identical declared replicas coalesce. Independent sources or conflicting
replicas sharing a workspace identity return `ambiguous_workspace_identity`
before subject selection.
One dataset identity cannot declare multiple workspace identities: every
affected workspace fails closed. Acceptance-reference order is not semantic;
the typed model normalizes it before replica comparison, along with revision,
endpoint and retained-transition presentation order.

Revision 1 has `predecessor: null`; every later retained revision names its
immediate predecessor number. Missing historical records stay missing. The
explicit `current_revision` must be retained, and no retained revision may be
greater. This checks a supplied snapshot, not the atomicity of a revision writer
or the completeness of its history.

Requirements declare canonical presence as `active` or
`historical_lineage_only`; criteria use `null`. This is supplied metadata, not
verification against the canonical graph. Every Requirement revision owns its
`acceptance_criteria_refs`: full references pinning exact criterion revisions.
Current selection is rejected. Criterion revisions have an empty list.
Adding/removing/repinning links requires a new Requirement revision; exact
lookup preserves the previous collection. A criterion move never rewrites
ownership automatically. An intended ownership transfer is recorded through
new revisions of the affected Requirements; storage containment is separate.
The earlier unmerged record-level layout is rejected, not assigned to history.
All supplied references must resolve within the index; dangling references and
unavailable pinned revisions reject construction through the Python API as well
as the CLI.

`decomposes_into` has one `source` and at least two `result` endpoints.
`composed_from` has one `result` and at least two `contributor` endpoints.
Participants must have distinct identities and the same subject class. Incoming
and outgoing queries return the authored relation and all its endpoint roles;
they never generate an inverse relation kind or alter participant disposition.
Each returned relation also carries `source.workspace_identity` and
`source.dataset_identity`, inherited from its enclosing snapshot. The stable
relation key is `(source.workspace_identity, relation_id)`; dataset identity is
source provenance. Python construction rejects source bindings that disagree
with the containing snapshot. Source identity is retained even when it differs
from all endpoint workspaces.

## Lookup semantics

The Python API exposes `SubjectIndex.lookup_exact(reference, revision)` and
`SubjectIndex.lookup_current(reference)`. Parsing produces frozen values with
tuple collections, detached from the input mapping. Construction and lookup
perform no filesystem access or mutation.

Lookup statuses are `resolved`, `unknown_workspace_identity`,
`ambiguous_workspace_identity`, `unknown_subject_id`, `subject_class_mismatch`,
and `unavailable_revision`. Duplicate/conflicting definitions are invalid input,
with a diagnostic instead of an arbitrary selected record.

`subject_lookup_result` returns the selected statement/containment and the
explicitly labelled `current_subject_disposition`, including its basis and
observation provenance. Exact content selection is not historical as-of
disposition. The result also exposes `current_revision`,
`retained_containment_history`, canonical presence, authored relations and the
selected revision's acceptance references. Authored relation enumeration has no
historical as-of claim. Retained history lists only supplied records;
missing revisions are not reconstructed from Git, text similarity or filenames.

`retained_disposition_transitions` preserves supplied activation/withdrawal
facts independently of the current projection. Each has a subject-scoped
`event_ref`, transition kind and provenance. Duplicate event references are
rejected; if the current basis event is retained, its result must agree with
the supplied current state. Current state is never inferred from list order.
Presentation sorts by event reference and asserts no chronology, as-of cutoff
or complete event history; the current basis may refer to an origin or event
outside the retained subset. Both exact/current lookup return the retained
facts. Empty retained history does not prove that no transitions occurred.

`resolved.relation_resolution` states `complete` or `incomplete`, always scoped
to `supplied_snapshots`. A source workspace conflict affecting the requested
identity leaves the subject content available but reports the conflicting
workspace/dataset identities. Disputed relations are excluded, with an explicit
incomplete result and CLI exit 1. An unrelated workspace conflict does not imply
missing relations. A complete supplied-scope result cannot establish that all
canonical history or external workspaces have been supplied.

Every result states `canonical_mutations_allowed: false`. A resolved retired
Requirement still cannot satisfy a Requirement dependency under SG-SPEC-0068;
this slice does not implement dependency evaluation or a readiness gate.

## Legacy and candidate compatibility

`subject_legacy_reads.parse_compatibility_document(mapping, source_ref)` reads
existing `candidate_graph.nodes`, materialized `specification.requirements` /
`acceptance_criteria`, and legacy string-valued `acceptance` into a typed
inventory. `source_ref` is supplied by the caller. This API has no file discovery
or output writer.

Candidate IDs and acceptance references stay node-local within their original
source artifact. Missing IDs produce diagnostics and are never generated.
Duplicates remain visible with diagnostics rather than choosing a winner.
Legacy strings retain their exact text and source locator. Equal strings are
separate occurrences; their locators are not durable subject identities.

No compatibility record becomes a canonical `SubjectRef` automatically. A
reviewed mapping must establish workspace binding and resolve collisions before
any future migration. Existing validators, materializers and writers are
unchanged.

## Evidence and limits

Focused tests: `tests/test_subject_read_model.py` and
`tests/test_subject_legacy_reads.py`. They cover scope collisions, class checks,
exact/current selection, retained containment, current disposition, relation
roles, immutable inputs, malformed snapshots, legacy scopes and CLI exit codes.

This is partial read-model evidence, not full runtime conformance. Storage,
workspace declaration persistence, allocation, revision/disposition writers,
replacement events, migration application, evidence mapping, Hypercode binding,
as-of queries and production integration remain separate work. The original
[preparation document](reviews/0221_subject_address_read_model.md) records earlier
proposals; SG-SPEC-0068 and this implemented boundary define the current names.
