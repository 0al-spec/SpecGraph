# RFC 0221: standalone subject storage preparation

**Prepared for review; not adopted.** [SG-SPEC-0069](../../specs/nodes/SG-SPEC-0069.yaml)
is a pending child of the human-approved semantic contract SG-SPEC-0068.
Preparation follows the human instruction `Отлично, давай делай.` on 2026-10-02.
This authorizes the concrete draft; approval of its physical schema is pending.

The child has `gate_state: review_pending`. Candidate files have
`canonical_adoption: false`, `canonical_readiness: not_evaluated` and
`ready_for_materialization: false`.

## Concrete choices to review

| Concern | Proposed version-1 convention |
| --- | --- |
| Workspace identity | Persisted `workspace:<UUID>` at `specs/workspace_identity.yaml` |
| Requirement | Existing `kind: requirement`, one file in `specs/requirements/` |
| Criterion | Separate record in `specs/criteria/`; no new seed node kind |
| Content history | Append-only inline `revisions`; `current_revision` selects the last revision |
| Node metadata | Retained `node_fields` per revision; top-level fields are validated current projections |
| Acceptance membership | Full exact criterion references in each Requirement revision |
| Retirement | Separate retained disposition events and a labelled current projection |
| Publication | Validate an isolated candidate tree and publish affected records atomically with conflict preconditions |

The Requirement node itself contains its subject history. There is no second
embedded Requirement inside a specification. A criterion revision or move cannot
silently repin a Requirement; membership changes need a new Requirement revision.
Historical pins remain readable. Exact lookup uses the selected revision's
`node_fields`, rather than current title/status. Current disposition does not
claim the disposition as of an old revision. Canonical topology presence comes
from a governed source, not from file existence or an `active` disposition.

## Prepared files

The [manifest](0221_subject_storage/manifest.yaml) lists seven review-only
`subject_storage_candidate` envelopes outside canonical storage. Each contains
`proposed_path`, `proposed_record`, preparation provenance and
`adoption_fields_pending`. These null fields require genuine decisions before a
future writer can emit canonical records.

| Candidate | Intended concern |
| --- | --- |
| [workspace_identity.yaml](0221_subject_storage/workspace_identity.yaml) | Workspace declaration; UUID remains an unreserved review token |
| [req.repaired-candidate-review-readiness.yaml](0221_subject_storage/req.repaired-candidate-review-readiness.yaml) | Clean no-op, repaired preview and unresolved gaps |
| [req.platform-promotion-approval-boundary.yaml](0221_subject_storage/req.platform-promotion-approval-boundary.yaml) | Separate Platform promotion authorization |
| [ac.clean-noop.yaml](0221_subject_storage/ac.clean-noop.yaml) | Clean readiness with no repair actions |
| [ac.repaired-preview.yaml](0221_subject_storage/ac.repaired-preview.yaml) | Preserve repaired-preview evidence |
| [ac.unresolved-gaps.yaml](0221_subject_storage/ac.unresolved-gaps.yaml) | Keep unresolved gaps blocking |
| [ac.approval-boundary.yaml](0221_subject_storage/ac.approval-boundary.yaml) | Keep promotion unauthorized until a separate decision |

The **3 + 1** partition and all statements match the
[mapping packet](0221_requirement_mapping_review.json). That packet remains
historical preparation with its then-deferred physical-schema status. This slice
supplies concrete physical choices for review, without changing its old status.

Each Requirement reference explicitly pins a destination criterion:

```yaml
subject:
  workspace_identity: workspace:a2800523-3588-4820-a47f-9fddc0fed3f5
  subject_class: criterion
  local_subject_id: ac.clean-noop
mode: exact
revision: 1
```

Candidate revision `provenance: null` deliberately exposes the adoption gap.
Candidate `created_at` dates preparation; destination revision 1 begins only at
actual adoption. Copying a candidate cannot produce a valid canonical record.

## Identity and evidence boundaries

The namespace mapping remains pending. Pilot workspace
`pilot:baa72850-bf2e-42c6-a3a9-68930a1ba44e` and the proposed destination
workspace identify different subjects even when local IDs and statements match.
Criterion candidates retain complete source mappings, exact references, source
occurrences, statement digests and pending reviewer fields. They create no
same-identity predecessors or supersession events.

Original PR 743/744 test executions and the direct policy trace retain their
pilot references. This task does not rerun that experiment or transfer evidence.
A future reviewed applicability link may address a destination criterion; it
does not relabel an original execution or create a trusted runtime receipt.

## Validation scope

`tests/test_subject_storage_preparation.py` protects preparation boundaries:
3 + 1 exact membership, statement fidelity, distinct namespaces, shared-ID
uniqueness, current metadata projections and unfilled adoption fields. It also
checks that the existing snapshot parser rejects candidate envelopes. These
checks do not implement a canonical-source adapter or verify writer atomicity
and durability.

The manifest's `validation_snapshot` records native checks and digests of the
checked files. Its bounded backlog projection retains `review_pending` and
`resolve_review_gate`; unrelated delivery/consumer surfaces are omitted. A
graph-health diagnostic outcome of `done` is not an approval or readiness result.

SpecGraph's native YAML, output/allowed-path, atomicity and graph reconciliation
checks validate the single new spec node. Read-only operational projections
must preserve its pending review gate. No LLM refinement run is used here; the
previous failed execution remains recorded in the
[mapping evidence](0221_requirement_mapping_evidence.json).

## Next bounded slice

1. Review SG-SPEC-0069 and its candidates at a specific commit. Record schema,
   ID and 3 + 1 namespace mapping decisions with genuine human provenance.
2. Implement the canonical-source adapter and validating writer, with conflict
   and incomplete-publication tests.
3. Materialize the two Requirements and four criterion origins through explicit
   SG-SPEC-0051 SpecDraft-to-canonical transitions. Author evidence applicability
   separately.

CONSTITUTION.md and SG-SPEC-0051 require actual review decisions before canonical
adoption. PR merge of preparation does not fulfill those gates.
