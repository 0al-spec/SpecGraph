# RFC 0221: recorded physical-schema and mapping approval

## Actual human decision

The project author approved the complete [PR #752](https://github.com/0al-spec/SpecGraph/pull/752)
packet in the current Codex conversation with the exact message:

> Одобряю пакет PR #752

[The separate decision record](0221_subject_storage_decision.json) binds:

- Delivered head: `6c88190d379b787661a47b07cf1279c25f0d585e`.
- Schema baseline: `ca3967e6b9d1b196c901ff6fcb0f77b7a98ecfc7`.
- `approval_scope_sha256`: `dcaf235e3345ef09604245161b4f0e57c54954fdd0052272a5a0ea27494bd2e1`.
- The complete packet's byte digest and actual source quote, reviewer authority,
  outcome, recording time and attribution for each of the four mappings.

The decision timestamp labels the first local observation of the message; its
original message timestamp is unavailable. No additional human rationale was
supplied. The agent records the decision and its scope; it has not submitted a
GitHub review on behalf of the human or inferred approval from successful checks
or merge. The digest is not a cryptographic signature or identity verification.

## Approved scope and remaining boundaries

| Item | Recorded effect |
| --- | --- |
| SG-SPEC-0069 v1 physical schema | `human_approved`; native gate resolution sets `status: specified` and `gate_state: none` |
| Workspace and six exact IDs | Approved future plan; `approved_but_unallocated` |
| Two Requirements and four criteria | Approved exact 3 + 1 membership and distinct source/destination mapping |
| Bounded implementation | Read-only canonical-source adapter, then validating origin/content-revision writer |
| Canonical materialization | Separate decision still required; `ready_for_materialization: false` |
| Migration, evidence applicability, Platform promotion and trusted receipts | Not authorized by this approval |

The canonical storage contract is approved; canonical **subject adoption** remains
false and runtime conformance remains `not_implemented` in this recording slice.
SG-SPEC-0068's semantics and frozen SG-SPEC-0019 are unchanged. SG-SPEC-0051
governance still applies to any later canonical transition.

## Historical evidence is preserved

The [prepared packet](0221_subject_storage_approval.md), its YAML and validation
evidence, the original mapping packet and all seven candidate envelopes retain
their historical `review_pending` state and unfilled decision/origin fields.
The actual decision is separate; it does not rewrite earlier evidence.

The decision record names byte-exact reviewed snapshots of the previous
SG-SPEC-0069 and its original preparation test. Their stored hashes preserve the
old validation boundary after current approval metadata and regression tests
advance. Current schema fields still equal the approved physical schema.
Historical pilot executions remain keyed to their pilot identities.

## Verification and next slice

Focused regression tests bind the actual quote to the exact packet, audit each
mapping's attribution, compare the unchanged approved schema and verify the
remaining materialization and evidence boundaries. Native supervisor gate
resolution is performed after recording the genuine decision.

Next: implement the read-only canonical-source adapter against the approved
schema, retaining revision-specific metadata, provenance and `revision_scope`.
