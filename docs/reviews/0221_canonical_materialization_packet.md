# RFC 0221 canonical materialization review packet

**Status: prepared for human review; no transition has been approved and no canonical source has been changed.**

Approval scope SHA256 (`approval_scope_sha256`): `29bb79bae19e096671aab6ababe34ff32c37002b9e3255b283d2001398c97fa6`. The digest covers the complete JSON packet before this digest field is added, encoded as UTF-8 canonical JSON with sorted keys, compact separators, Unicode preserved, and no trailing newline.

The machine artifact declares `artifact_kind: rfc0221_canonical_materialization_packet` and `gate_state: review_pending`.

This packet prepares the next decision boundary after the approved RFC 0221 storage schema and merged validating writer. It binds six proposed subject origins—two Requirements and four acceptance criteria—to their review candidates and source Proposals. It records the SG-SPEC-0051 transition records that still need explicit decisions.

## What prior approvals establish

The decision in [`0221_subject_storage_decision.json`](0221_subject_storage_decision.json) approves the SG-SPEC-0069 physical schema, proposed workspace/ID plan, 3 + 1 Requirement membership, and bounded reader/writer implementation. It explicitly leaves `canonical_materialization_authorization` null, the workspace/IDs unallocated, evidence transfer unauthorized, and readiness unevaluated. Those approvals do not record the individual SG-SPEC-0051 transitions needed for these six SpecDraft candidates.

The proposed source drafts are the seven files in [`0221_subject_storage/`](0221_subject_storage/): one workspace declaration and six `subject_storage_candidate` envelopes. The two Requirement drafts partition the four exact criterion revision-1 references 3 + 1. The candidate YAML files contain `null` adoption provenance and are not accepted as canonical writer input.

## Prepared transition inventory

For each of the six subject candidates, the JSON packet contains:

1. A pending `proposal -> spec_draft` review record linking the cited proposal to that exact candidate's `proposed_record`.
2. A pending `spec_draft -> canonical_artifact` review record linking that candidate to its proposed canonical target.

Each record already has its proposed edge, gate type, source and target references, and a stable record identifier. Canonical templates also link their paired ingress and carry an exact workspace/class/ID revision-1 selection. Reviewer, decision timestamp, outcome, rationale, and decision provenance remain null. These are immutable pending templates, not decisions to fill in place.

**Intent lineage is unresolved for all six ingresses.** Proposals 0177/0191 and the candidate envelopes do not establish a motivating IntentDraft or an attributed Intent lineage. Each ingress therefore has `intent_lineage_ref: null` and `intent_lineage_state: unresolved`; `intent_lineage_unresolved` is an explicit review blocker. Merely approving a template cannot satisfy SG-SPEC-0051. Locate genuine historical evidence or author a new attributed Intent record and a revised packet; do not infer human Intent from agent-written proposal text.

The workspace declaration is storage bootstrap data rather than one of the six normative subjects. Its provenance and allocation are separately pending in the packet. The proposed source ref is `refs/specgraph/subject-storage/a2800523-3588-4820-a47f-9fddc0fed3f5`; initialization must be reviewed and bound to the actual base commit before use. No ref has been initialized by this packet.

## Publication prerequisites

Before preparing the exact writer request:

- establish and review the motivating Intent lineage for every ingress in a new packet version;
- review and approve all six proposal-to-draft ingress records and six draft-to-canonical records;
- approve the workspace declaration provenance and confirm the destination IDs are to be allocated;
- explicitly approve `topology_selection`: workspace, dataset, topology reference, governance evidence reference and canonical presence for each Requirement; neither file existence nor disposition supplies this decision;
- author the six revision-1 provenance envelopes, six activation events, and declaration provenance from those genuine decisions;
- resolve every origin, activation and declaration provenance reference to its actual decision and approved effect; one decision may cover origin and activation only if its scope explicitly authorizes both;
- choose the actual source ref base commit, then regenerate the complete expected source digest map and request digest against it;
- bind the publication authorization to that request digest and the writer's exact required transition-reference set;
- review destination evidence applicability separately. Historical pilot executions are not destination executions.

The writer can publish the declaration and all six subject origins in one validated Git commit/ref compare-and-swap. A failed or stale request publishes none of them. Even after publication, readiness, platform promotion permission, migration, evidence transfer, and trusted runtime receipts remain separate decisions.

The `writer_request` object here is an unusable placeholder, not parser-compatible input. Its `topology_selection` and all publication fields remain null. The current writer labels authorization `operator_supplied_not_attested`: it validates structure, the exact request digest and the supplied provenance-reference set, but does not resolve those references to authentic SG-SPEC-0051 decisions. A governed decision-to-request publication gate is **not implemented** and is an explicit blocker before automated materialization. It must verify packet/input bindings, actual human decision scope, Intent lineage and ingress, canonical transitions, workspace/topology decisions, provenance effects, and exact request authorization. This PR's consistency check implements none of that authority transfer.

## Immutable approval lifecycle and input checks

Before approval, preparation corrections change this scope digest and must update both documentation surfaces. After approval, preserve the packet bytes and pending templates. Store actual decisions in a **separate artifact** binding `packet_path`, raw-file `packet_sha256`, `approval_scope_sha256` and `reviewed_head`. Follow the existing storage-decision pattern. A changed scope requires a new packet version and new approval. Create the actual writer request separately with its own digest; bind its publication authorization to that exact request. Merge and validator success supply no decision provenance.

`inputs.review_tree_file_sha256` covers all seven candidate files, both source proposals, the RFC proposal, the preparation manifest and prior decision artifact, including additional source references. `inputs.contract_snapshot` binds SG-SPEC-0051/0068/0069 bytes at `prepared_against_commit`; validation requires that Git history and never substitutes current contract files. The review inputs must retain their exact bytes for this pending packet. Future edits require a new reviewed snapshot/version rather than silently changing its sources.

Run `make materialization-packet-check`. CI executes the same check and mutation regressions in `tests/test_materialization_packet.py`: stale hashes, omitted declaration, malformed inventories, mismatched source/target or exact revision, changed membership, in-place decisions, missing lineage/topology blockers and unearned publication flags fail. Success means **consistent pending review snapshot**, with `ready_for_materialization: false`; it does not mean an approvable ingress or permission to publish.

## Review result

The machine-readable packet at [`0221_canonical_materialization_packet.json`](0221_canonical_materialization_packet.json) is a review artifact, not an authorization or writer request. Its `canonical_mutations_allowed` is false and `ready_for_materialization` is false. Approval must identify this exact packet digest and supply the missing decision records; merge of this preparation PR alone does not satisfy SG-SPEC-0051.
