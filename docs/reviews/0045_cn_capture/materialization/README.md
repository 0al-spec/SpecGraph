# CN-CAPTURE: complete physical publication preparation

**Status: physical preview passed; human publication decisions pending.**
This is a proposal-0045 package over the proposal-0221 Intent graph writer
extension in [PR #800](https://github.com/0al-spec/SpecGraph/pull/800). It prepares
the complete future records and exact write request. It creates no production
workspace, source ref, origin, activation, admitted evidence or release.

## Exact proposed scope

| Item | Proposed canonical destination | Content |
| --- | --- | --- |
| Intent `intent.cn.capture`, revision 1 | `specs/intent_graph.yaml` | During a human-agent conversation, the agent preserves short notes while the person continues speaking and can later review them. |
| Requirement `req.cn.capture`, revision 1 | `specs/requirements/req.cn.capture.yaml` | The agent can save a short note during a conversation before choosing its semantic kind. |
| Criterion `ac.cn.capture-without-kind`, revision 1 | `specs/criteria/ac.cn.capture-without-kind.yaml` | The existing empty-sketch → capture without `kind` → fresh-process recovery scenario, retaining ID, text and human quotation, with `canonical: false` and no approval history. |
| Relation `edge.cn.capture.derived-from-intent` | `specs/intent_graph.yaml` | Exact Requirement revision 1 → Intent revision 1, `derived_from`. |

The complete criterion statement is in
[its candidate](subjects/ac.cn.capture-without-kind.yaml). The Requirement pins
exactly that criterion at revision 1. All three statements retain the meanings
already covered by the [semantic decision](../adoption/semantic-review.json).
The original pending candidates, semantic decision and adoption packet stay
unchanged; complete physical records are prepared here as a new scope.

The reused workspace plan is
`workspace:a2800523-3588-4820-a47f-9fddc0fed3f5`. Proposed dataset:
`dataset:specgraph-canonical-subjects-v1`. The one active topology entry is the
Requirement; criterion membership does not establish an SG-SPEC-0061 criterion
root path. Active reachability, fulfillment and `tests_verified` are not claimed.

## Files and provenance

- [Subject candidates](subjects/) contain complete revision-1 records, proposed
  activation projections and references to the future origin/activation effects.
- [Workspace candidate](workspace-identity.yaml) retains the existing identity
  plan and points to the proposed allocation effect.
- [Intent graph candidate](intent-graph.yaml) distinguishes the retained human
  source from agent-distilled wording and selects two separate origin effects.
- [Topology](topology.json) makes dataset, presence and decision references explicit.
- [Writer request](writer-request.json) is the exact version-2 payload consumed
  by `parse_write_request`; every physical record is embedded and cross-checked.
- [Lineages](lineages.json) bind each subject to its exact source proposal and
  the retained human IntentDraft. Their review fields remain null.
- [Decision template](decisions.template.json) proposes four paired transitions
  and eight effects: allocation, two subject origins, two activations, Intent
  origin, relation origin and topology selection.
- [Authorization template](authorization.template.json) selects exactly the
  seven write-effect references (topology has its separate decision reference).

Agent attribution and preparation times are real preparation metadata. The
Requirement remains `inferred`, with agent-assessed medium source confidence;
the Intent remains `distilled`. Human reviewer identities, approval times,
approval quotes and rationales have not been invented. A proposed `active`
projection or `true` allocation flag inside a template describes the requested
effect; it is not an existing decision or authority grant.

Templates have distinct artifact kinds and are not runtime publication evidence
or authorization. Future actual decisions belong at
`docs/reviews/0045_cn_capture/materialization/decisions.json`; this file does not
exist in the preparation. Candidate provenance already names its exact effect
pointers, so recording genuine decisions need not rewrite the physical records.

## Immutable source baseline and preview

The proposed dedicated ref is
`refs/specgraph/subject-storage/a2800523-3588-4820-a47f-9fddc0fed3f5`.
Its proposed initialization commit is
`ddf10b48fe8c0c288cf5597a04313185a4879e95`, the merged semantic-review baseline.
That commit has no selected subject source, so the complete prior source digest
inventory is empty. No production initialization was performed.

[preview.json](preview.json) records the real writer rehearsal in a disposable
Git clone. The dedicated ref was created only in that clone. Preview validates
the four-file candidate tree and leaves even that ref at its original value.
The prospective commit is an isolated object, not a published canonical version.
The producer's contract/readiness limits remain explicit in the report.

Request digest:

```text
a6adba8da293a16b7255a953fc4caace468e81ad7fe1271dfdf8d57285732866
```

[packet.json](packet.json) binds candidates, exact request, template bytes,
lineage, human sources, previous semantic agreement and writer code. Its scope:

```text
ef04e9dc665847e225b8add82777c9fea3e75f46c59a3a52541f2b9efc72ad24
```

The actual reviewed-head/raw-packet binding is filled only after committing and
reviewing the preparation. A request timestamp is fixed preparation metadata;
future human decision times are separate and remain unset.

## Remaining decision order

The existing [publication contract](../../../subject_publication.md) requires
actual reviewed ingress lineage as part of the immutable packet inputs. Thus:

1. Review the two subject lineages and exact prepared physical scope. Record
   genuine source-bound ingress decisions.
2. Retaining those reviews changes input bytes. Prepare the next packet scope
   and obtain final approval of that exact snapshot, rather than silently filling
   fields under this digest. The physical candidates and write request can stay
   unchanged.
3. Record actual transition, origin/activation, allocation, topology and exact
   publication decisions; select their immutable evidence commit and actual
   authorization. Only then may the writer publish the source.

This ordering is the existing strict gate, not an additional approval mechanism.
The current instruction **«Ок, готовь пакет»** authorizes preparation. Previous
semantic agreement remains agreement with the three meanings, and retained CI
observations remain historical draft evidence. Neither supplies these decisions.

## Verification

`tests/test_cn_capture_materialization.py` checks all input hashes, exact source
statements, effect references and request identity. A fresh isolated preview
must reproduce the prepared commit and its explicit Requirement-to-Intent path.
Pending templates cannot publish. A separate test-only copy with synthetic
fixture approvals and a newly bound packet demonstrates the complete existing
gate and one atomic publication; it grants no production authority.
