# RFC 0221: PR #751 storage contract review resolution

**Prepared for review; not adopted.** This corrects the pending physical contract
SG-SPEC-0069 and its seven `subject_storage_candidate` envelopes. SG-SPEC-0068,
frozen SG-SPEC-0019, the historical mapping packet and pilot evidence are unchanged.
The review gate remains `review_pending`; no source adapter or writer is added.

## Review evidence

An independent GPT-6 Astra review at Medium reasoning inspected head
`e427f1927e8a0fa723d4339a777a2cda1f238c85` without the author conversation.
Its initial pass identified missing bounded revision scope. A separate comparison
with the four GitHub threads confirmed three P2 contract defects: missing node
provenance, revision scope and portable ID allocation. Disposition spelling was
a compatibility clarification, not a demonstrated runtime regression: the source
adapter is still absent. The draft now uses the existing typed vocabulary directly.

A second read-only pass by the same Astra Medium reviewer inspected the corrected
contract, candidates, tests and this resolution before commit. It confirmed all
three original P2 defects were addressed, found no remaining P2+ in that scope,
and independently checked all nine manifest file digests. It did not rerun the
test suite; the 94 passing focused cases are the primary agent's local execution.

The case issue was reproduced on the local case-insensitive filesystem:
`REQ.A.yaml` and `req.a.yaml` addressed one physical file despite distinct logical
IDs. The temporary probe was removed. No canonical files were written.

## Corrections and prevention

| Feedback | Governing rule and correction | Prevention |
| --- | --- | --- |
| Node provenance omitted from a closed schema | SG-SPEC-0024 requires structured actor, authority and timestamp, conditional source reference/confidence, and revision attribution. Requirement records now retain the full envelope per revision and in the current projection, separate from the revision decision reference. | `test_requirement_provenance_retains_the_governing_node_envelope` compares the physical fields and conditional requirements with SG-SPEC-0024. Candidate adoption metadata remains null and explicitly pending. |
| Revision scope omitted | SG-SPEC-0019 and SG-SPEC-0068 require bounded change scope. Every proposed Requirement/criterion origin now has an authored `revision_scope`; later revisions must retain their own scope. | `test_revision_scope_is_authored_for_every_proposed_origin` checks all six origins and the independent governing minimum semantics. |
| Case-only IDs overwrite portable filenames | Logical identity stays case-sensitive. Allocation, publication and whole-tree source validation must reject workspace-wide ASCII case collision keys across classes, folders and disposition. | `test_candidate_namespace_passes_portable_allocation_audit` checks the six proposed IDs; `test_case_aliases_collide_across_classes_and_grouping` exercises the collision counterexample. This is a preparation-fixture audit, not writer conformance. |
| New disposition aliases lack a mapping | Physical events use existing `activation`/`withdrawal` directly; no new aliases are needed. | `test_disposition_vocabulary_matches_the_typed_model` constructs both existing typed transitions and checks their resulting states. |

The manifest's native validation snapshot is regenerated from the corrected
node and candidate digests. Local targeted tests, Python/YAML quality, DocC sync,
proposal tracking and commit spec-evidence validation are recorded with the fix.
Successful checks prove preparation consistency; they do not approve the schema,
validate writer durability, adopt subjects or transfer historical evidence.

## Remaining bounded work

Review the corrected physical schema, workspace token and 3 + 1 mapping at a
specific commit. Only after actual decision provenance exists should a separate
slice implement the source adapter and writer, with provenance/scope preservation,
portable collision rejection and incomplete-publication tests.
