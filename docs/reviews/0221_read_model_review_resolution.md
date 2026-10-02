# RFC 0221 read-model review resolution

An independent GPT-6 Astra reviewer with ultra reasoning reviewed the contract
and implementation at `794925b1665e3142b2adbaad5513d16cfb7a73b6` without the
author conversation or prior review packets. It reported three P2 findings.
The human subsequently requested corrections on 2026-10-02: “Хорошо, исправляй”.
This record describes the bounded corrections, not a new full-conformance claim.

## Findings and prevention

| Finding | Root cause | Correction and prevention |
| --- | --- | --- |
| Ambiguous source silently removes incoming lineage while subject remains resolved | `artifact_contract_validation_gap` | `relation_resolution` distinguishes complete from incomplete enumeration within `supplied_snapshots`, lists affecting source conflicts and makes the CLI exit nonzero for incomplete relations. Regression: `test_ambiguous_relation_source_reports_incomplete_enumeration` and `test_cli_incomplete_relations_exit_nonzero_with_resolved_content`. |
| Requirement revision does not define the lifetime of acceptance references | `policy_runtime_drift` | SG-SPEC-0068 and RFC 0221 now make reference collections part of governed Requirement content, with exact criterion pins. Changing links requires a new Requirement revision. Regression: `test_requirement_revision_preserves_acceptance_pins_across_criterion_move`. |
| Cross-workspace relation output loses the authored record's namespace | `scope_isolation_gap` | Returned relations preserve `source.workspace_identity` and dataset identity; workspace construction validates the binding. Regression: `test_relation_source_scope_survives_identical_cross_workspace_records`. |

The first and third findings were reproduced independently by the integrating
agent. For the second, the pre-fix reader returned changed references alongside
an unchanged selected Requirement revision. The chosen correction makes links
part of that revision rather than an unversioned current projection.

Astra's bounded follow-up closed all three findings after read-only inspection
and short counterexample probes. It did not rerun the full suite or audit the
later GitHub comments below.

## Additional GitHub review threads

- [Reference order](https://github.com/0al-spec/SpecGraph/pull/748#discussion_r4164479621):
  unordered acceptance collections now normalize at the typed value boundary;
  serialization order cannot make equivalent replicas ambiguous.
- [Disposition history](https://github.com/0al-spec/SpecGraph/pull/748#discussion_r4164479625):
  `retained_disposition_transitions` preserves independent authored events and
  provenance without selecting current state from their presentation order.
- [Replica binding](https://github.com/0al-spec/SpecGraph/pull/748#discussion_r4164479627):
  one dataset declaring different workspaces fails every affected scope closed.

Structured root causes, regression tests, verification kinds and residual limits
are recorded in `tools/review_feedback_records.json` under `pr-748-*`.

## Interpretation

- Subject resolution does not imply complete lineage. Conflicting relation
  sources remain visible as diagnostics; their disputed records are not treated
  as true. Completeness applies only to supplied snapshots.
- A relation key is its source workspace plus workspace-local relation ID.
  `dataset_identity` is retained provenance and does not establish authority.
- Exact Requirement lookup preserves its historical acceptance obligations.
  A criterion move does not silently change links. Intended ownership changes
  require explicit new revisions of affected Requirements while retaining old
  collections.
- The experimental, unmerged `subject_read_snapshot` schema version 1 now stores
  acceptance references per revision. The earlier record-level draft layout is
  rejected instead of being silently assigned to every historical revision.

See [Subject read model](../subject_read_model.md) for the public boundary and
remaining partial read-model scope. Its `current_subject_disposition` and
`retained_containment_history` retain their explicit interpretation;
`parse_compatibility_document` still preserves legacy/candidate authority scopes.

## Validation and remaining decisions

The regression cases are in `tests/test_subject_read_model.py`; compatibility
regressions remain in `tests/test_subject_legacy_reads.py`. Proposal tracking,
DocC synchronization, Python/YAML quality and the Spec evidence gate apply to
the corrected PR. Local validation results and final-head CI state are recorded
in the PR, not implied by this document's presence.

Criterion withdrawal effects on readiness, ordering of disposition events,
replica lag policy and historical-event versus current-endpoint relation
semantics remain explicit decisions before their respective future consumers or
writers. No dependency evaluator, migration application or allocator is added.
Frozen SG-SPEC-0019 is unchanged.
