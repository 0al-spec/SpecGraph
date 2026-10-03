# Governed subject publication

SG-SPEC-0051 / SG-SPEC-0069 has a mandatory decision gate in
`tools/subject_publication.py`, called by `write_subject_source` before source
export, candidate object creation or Git ref compare-and-swap. Preview remains
read-only preparation and does not require approval. Real publication requires
both the exact write authorization and `SubjectPublicationEvidence`.

## Evidence selection and trust

The version-1 `subject_publication_evidence` exchange has `repository_root`,
`evidence_commit` and repository-relative `decision_path`, plus `schema_version`
and `artifact_kind`. The root is explicit; the commit is a full Git SHA. The
gate reads **regular Git blobs at that immutable commit**, with inherited Git
overrides and replacement objects disabled. Working-tree edits, symbolic links,
missing objects and unresolved JSON-pointer fragments cannot supply evidence.

The decision artifact's `packet_binding` selects a separate `reviewed_head`,
`packet_path`, raw-file `packet_sha256` and `approval_scope_sha256`. It binds
the reviewed packet and every listed input, including candidates, proposals,
Intent lineage and original human Intent sources. A supplied historical
contract snapshot is also checked at its pinned commit.

This verifies **scope-bound recorded decisions**, not the person's identity.
The caller must select a trusted evidence repository/commit with genuinely
recorded human decisions. An attacker who can fabricate both decisions and
their human-source records in that trusted input remains outside this boundary.
The result explicitly reports
`scope_bound_recorded_decisions_verified_not_attested` and
`reviewer_identity_attested: false`. No signatures or trusted runtime receipts
are manufactured. A literal `human_project_author` field alone is insufficient:
the gate resolves its source record and checks the exact approved action scope.

## Version-1 artifact contract

These are bounded I/O exchanges, not new canonical semantic seed kinds.

### Review packet

`subject_publication_review_packet` v1 (or a new, complete
`rfc0221_canonical_materialization_packet` version) retains
`gate_state: review_pending`, `canonical_mutations_allowed: false` and pending
`transition_records`. Keep this packet immutable after approval.

- `workspace`: exact workspace identity, dedicated source ref and, for bootstrap,
  `proposed_declaration` referring to a reviewed candidate.
- `subjects`: one entry per requested change with local ID, exact
  `canonical_revision_selection`, candidate file/hash, draft reference,
  canonical target reference, statement and source proposal reference.
- `inputs.review_tree_file_sha256`: exact bytes of every referenced reviewed
  input. All candidate, lineage, IntentDraft, human Intent source, proposal and
  declaration inputs must be included; the gate checks even additional entries.
- `transition_records`: exactly one proposal ingress and canonical transition
  per subject. Every record has unique identifiers, matching source/target,
  `gate_type: review`, `state: review_pending` and `outcome: null`. An ingress
  carries an actual reviewed `intent_lineage_ref`; a canonical decision carries
  its exact revision target and `ingress_transition_id`.
- `approval_scope_sha256`: canonical UTF-8 JSON SHA256 excluding this one field;
  sorted keys, compact separators, Unicode retained, no NaN or trailing newline.

The old PR #760 packet remains historical pending preparation. Its null Intent
lineage cannot pass this gate. Create a new reviewed version after genuine
lineage is available; this implementation does not retroactively approve it.

### Human reviews and Intent

Every actual decision has a `review` object: `reviewer`,
`reviewer_authority: human_project_author`, timezone-aware `decision_timestamp`,
`outcome: approved`, nonempty `rationale`, `source_quote`, `source_ref` and
`scope_sha256`. The scope hash covers that action record excluding `review`.
`source_ref` resolves a `subject_human_review_record` v1 whose `review` is exactly
the same object. Reusing a schema approval for an origin fails the action scope
and artifact-kind checks. Record actual human attribution; never generate an
approval quote to make the gate pass. If no additional human rationale was
supplied, record that fact without attributing an invented argument to the human.

An ingress lineage is an explicitly reviewed `subject_intent_lineage` record
with `source_proposal_ref`, its exact `source_proposal_sha256` and `intent_ref`.
That reference resolves an `intent_draft` exchange with a substantive statement
and provenance: `authority_class: authored`, `actor_id: human:...`, `source_ref`.
The source resolves a `human_intent_record` with the same actor and nonempty
original `text`. The packet binds all those bytes. Semantic fidelity of the
proposal to human Intent remains the responsibility of the recorded review;
the gate does not infer Intent or perform an LLM semantic assessment.

### Actual publication decisions

`subject_publication_decisions` v1 contains:

- `packet_binding` and `packet_approval`: the latter has that exact binding and
  a scope-bound actual human review.
- `transition_decisions`: complete records matching the pending templates,
  approved outcomes, actor/timestamp/rationale agreeing with their reviews;
  canonical decisions link their approved ingress and exact target revision.
- `effects`: separately reviewed `origin` or `content_revision`, `activation`,
  `workspace_allocation` and `topology` records. Subject effects bind exact
  workspace/class/ID/revision; origin/revision effects identify the canonical
  transition. Actual revision and activation provenance point to their respective
  `decision_path#/effects/N` records. All supplied effects must be used.
- Bootstrap allocation additionally binds workspace, source ref, expected base
  commit and exact canonically serialized declaration SHA256, with both
  `identity_allocation_authorized` and `source_ref_initialization_authorized`
  explicitly true. It authorizes these effects, not an arbitrary future ref.
- `topology_decision_ref`: an effect with the exact existing topology-selection
  exchange. Dataset, workspace, topology/governance references and every
  Requirement presence must match the request; existence and disposition do
  not supply canonical presence.
- `publication`: actual human review of `request_sha256` and exact
  `transition_refs`. The separate writer authorization points to
  `decision_path#/publication`, matches reviewer/timestamp and covers exactly
  the new revision, activation and declaration provenance refs.

Gate checks preserve the reviewed identity, title, exact revision, statement,
authored revision scope and criterion membership. A later publication approval
cannot silently replace those reviewed semantics. The existing writer then
checks complete physical schema, unchanged historical records, metadata,
namespace, prior digests, candidate commit scope and atomic publication.

This first gate supports proposal-sourced origins/content revisions and review
gates. Direct IntentDraft ingress and confirmation decisions fail closed until
a separately tested adapter implements them. No allocator, transition author,
decision timestamp generator, evidence transfer or production materialization
is added here.

## CLI and diagnostics

```bash
.venv/bin/python tools/subject_source_write.py \
  --repository-root /path/to/source-repository \
  --request /path/to/exact-request.yaml \
  --authorization /path/to/exact-authorization.yaml \
  --governance /path/to/immutable-evidence-selection.yaml
```

Existing publication calls without governance now fail closed. Exit codes:
`0` prepared/published, `2` malformed request/physical input, `3` stale source
or compare-and-swap conflict, **`4` governance_blocked** for missing or
inconsistent decision evidence. A blocked result has `source_ref_updated: false`.
Preview is available with `--preview`; it remains unevaluated readiness and
does not confer publication permission.

`tests/test_subject_publication.py` uses synthetic approvals in temporary Git
repositories for both bootstrap and content revision. It proves success and
no-ref-update failures for wrong scopes, schema approval reuse, incomplete
transitions, lineage, revisions, effects, topology, request digests and review
sources. Missing governance is checked before candidate creation. The older
`test_subject_source_write.py` suite isolates storage/CAS with a scoped test
stub for this new seam; it makes no governance claim.
