# RFC 0221 canonical materialization review packet

**Status: prepared for human review; no transition has been approved and no canonical source has been changed.**

Approval scope SHA256 (`approval_scope_sha256`): `2df02209918ddd29ccd7e0f235104178058c4f4f058b7790ae87e74566253ebc`. The digest covers the complete JSON packet before this digest field is added, encoded as UTF-8 canonical JSON with sorted keys, compact separators, Unicode preserved, and no trailing newline.

The machine artifact declares `artifact_kind: rfc0221_canonical_materialization_packet` and `gate_state: review_pending`.

This packet prepares the next decision boundary after the approved RFC 0221 storage schema and merged validating writer. It binds six proposed subject origins—two Requirements and four acceptance criteria—to their review candidates and source Proposals. It records the SG-SPEC-0051 transition records that still need explicit decisions.

## What prior approvals establish

The decision in [`0221_subject_storage_decision.json`](0221_subject_storage_decision.json) approves the SG-SPEC-0069 physical schema, proposed workspace/ID plan, 3 + 1 Requirement membership, and bounded reader/writer implementation. It explicitly leaves `canonical_materialization_authorization` null, the workspace/IDs unallocated, evidence transfer unauthorized, and readiness unevaluated. Those approvals do not record the individual SG-SPEC-0051 transitions needed for these six SpecDraft candidates.

The proposed source drafts are the seven files in [`0221_subject_storage/`](0221_subject_storage/): one workspace declaration and six `subject_storage_candidate` envelopes. The two Requirement drafts partition the four exact criterion revision-1 references 3 + 1. The candidate YAML files contain `null` adoption provenance and are not accepted as canonical writer input.

## Prepared transition inventory

For each of the six subject candidates, the JSON packet contains:

1. A pending `proposal -> spec_draft` review record linking the cited proposal to that exact candidate's `proposed_record`.
2. A pending `spec_draft -> canonical_artifact` review record linking that candidate to its proposed canonical target.

Each record already has its proposed edge, gate type, source and target references, and a stable record identifier. Reviewer, decision timestamp, outcome, rationale, and decision provenance remain null. SG-SPEC-0051 requires an approved ingress before canonical materialization; the records cannot advance while those fields are pending.

The workspace declaration is storage bootstrap data rather than one of the six normative subjects. Its provenance and allocation are separately pending in the packet. The proposed source ref is `refs/specgraph/subject-storage/a2800523-3588-4820-a47f-9fddc0fed3f5`; initialization must be reviewed and bound to the actual base commit before use. No ref has been initialized by this packet.

## Publication prerequisites

Before preparing the exact writer request:

- review and approve all six proposal-to-draft ingress records and six draft-to-canonical records;
- approve the workspace declaration provenance and confirm the destination IDs are to be allocated;
- author the six revision-1 provenance envelopes, six activation events, and declaration provenance from those genuine decisions;
- choose the actual source ref base commit, then regenerate the complete expected source digest map and request digest against it;
- bind the publication authorization to that request digest and the writer's exact required transition-reference set;
- review destination evidence applicability separately. Historical pilot executions are not destination executions.

The writer can publish the declaration and all six subject origins in one validated Git commit/ref compare-and-swap. A failed or stale request publishes none of them. Even after publication, readiness, platform promotion permission, migration, evidence transfer, and trusted runtime receipts remain separate decisions.

## Review result

The machine-readable packet at [`0221_canonical_materialization_packet.json`](0221_canonical_materialization_packet.json) is a review artifact, not an authorization or writer request. Its `canonical_mutations_allowed` is false and `ready_for_materialization` is false. Approval must identify this exact packet digest and supply the missing decision records; merge of this preparation PR alone does not satisfy SG-SPEC-0051.
