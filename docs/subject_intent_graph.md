# Intent roots and authored derivation in subject storage

Proposal 0221 adds an opt-in physical extension for the existing `intent` and
`derived_from` kinds from SG-SPEC-0001/0023. It closes the writer seam identified
by the CN-CAPTURE and authored-traceability pilots. Requirement/criterion records,
their `SubjectClass` values and snapshot v1 stay unchanged.

## Source format

The optional **`specs/intent_graph.yaml`** belongs to the same selected workspace,
source commit, digest inventory and dedicated Git ref as the subjects. Its fields:

| Surface | Version-1 contract |
| --- | --- |
| Envelope | `schema_version: 1`, `artifact_kind: subject_intent_graph`, exact `workspace_identity` |
| `intents` | List of immutable revision-1 origins: `id`, `kind: intent`, `revision: 1`, `title`, `status`, `authority_class`, `source_ref`, SG-SPEC-0024 `provenance`, `statement`, `adoption_provenance` |
| `derived_from` | List with `id`, `kind: derived_from`, exact Requirement revision `source`, `target_intent_id`, `target_revision: 1`, `adoption_provenance` |

The Intent source reference selects the original human Intent exchange; the
provenance envelope records who authored/imported/distilled the node. Adoption
provenance separately selects the actual origin effect. The original human words
and an agent's normalized Intent remain distinguishable.

Record IDs use the shared ASCII convention and portable lowercase collision
keys. Intent and relation IDs cannot alias one another or stored subjects.
Unknown keys, duplicate YAML keys, noncanonical YAML, symlinks and a directory
where the single graph file should be are invalid. A missing graph file preserves
the previous reader result. Existing older tools do not understand this extension;
use the updated reader/writer for sources containing it.

`CanonicalSourceRead.intent_graph` exposes immutable typed values. Its audit adds
the graph payload and names its relation scope separately from the unchanged
subject snapshot. `source_file_sha256` includes the graph file, including after
immutable Git export. Filesystem reads recheck the full inventory and hashes.

## Exact authored paths

`CanonicalIntentGraph.paths_from(selection)` returns the explicitly authored edge
IDs and target Intent IDs for that **exact Requirement revision**. A criterion pin
does not create a path, and a link to revision 1 does not silently apply to revision
2. Source and target must exist in the same declared workspace. Unsupported edge
kinds, cross-workspace links and criterion-to-Intent endpoints fail validation.

This provides inspectable authored paths. It does not evaluate SG-SPEC-0061 active
reachability, criterion closure, fulfillment, runtime behavior or evidence admission.
Historical subject presence and disposition retain their separate contracts.

## Version-2 write request

Use the existing `subject_source_write_request` with **`schema_version: 2`** and
the additional required `intent_graph` mapping containing the complete proposed
graph. All existing request fields, including `changes` and the complete prior
`expected_source_file_sha256`, remain required. `changes` may be empty when only
the graph is extended. Version 1 rejects the new field; version 2 rejects its
absence. Existing version-1 request digests remain byte-for-byte unchanged.

For version 2, `request_sha256` binds the legacy parsed-request fields plus
`schema_version: 2` and canonically serialized `intent_graph_yaml`. The serializer
uses the same sorted compact UTF-8 JSON/no-NaN convention. The complete graph,
subject changes and workspace bootstrap can publish in **one** existing
`git_commit_compare_and_swap_v1` transaction. Unrelated branches, checkout files
and the operator's index remain untouched.

The extension is append-only: existing Intent and relation records cannot be
edited or deleted, and an unchanged graph is not a new append. New origins and
edges may be added in one batch. Intent content revisions, withdrawal, relation
replacement, migration and arbitrary graph traversal remain future slices.

Two named SpecificationCore policies own these rules:

- `subject_intent_graph.exact_requirement_to_intent` validates prepared endpoint facts.
- `subject_intent_graph.append_preserves_origins` preserves all prior records while adding origins.

Parsing, file discovery, serialization, Git and effect execution stay in adapters.

## Reviewed publication

The existing publication contract remains mandatory. The new review-packet
`intent_graph` entry contains `candidate_file`, `candidate_sha256`,
`source_draft_ref: <candidate_file>#/proposed_record` and
`target_path: specs/intent_graph.yaml`. The complete proposed graph and every
new Intent's original human source must be in the reviewed input inventory.
`subject_publication.complete_reviewed_record` compares the full reviewed graph
with the requested graph; pending fields cannot be filled under an old approval.

Each new Intent or relation selects one `intent_graph_origin` record in the
existing decision artifact's `effects` list. That effect binds exact
`workspace_identity`, `record_id`, `record_kind`, and `record_sha256` (canonical
JSON scope digest of that complete record), with the existing source-bound human
`review`. Its reference is the item's `adoption_provenance`. The final publication
decision and writer authorization must cover exactly these effects together with
the subject and allocation effects. Existing origins retain their old provenance.

No new approval service or gate is introduced. Permission checks run before
candidate export/object creation; reading prior immutable Git blobs for an append
does not grant permission. Preview remains available, explicitly `prepared` and
`source_ref_updated: false`. Missing or mismatched governance is exit 4; stale
source/CAS conflicts are exit 3; malformed physical input is exit 2.

The implementation is verified in temporary fixture repositories by
`tests/test_subject_intent_graph.py`, alongside existing subject reader, writer
and publication tests. Fixtures use synthetic human decisions. No real workspace,
Intent or relation is allocated by this implementation. CN-CAPTURE's semantic
agreement still needs a complete, newly reviewed materialization packet; it is
not publication permission. Readiness remains `not_evaluated`.
