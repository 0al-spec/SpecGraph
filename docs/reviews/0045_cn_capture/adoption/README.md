# CN-CAPTURE: review preparation for canonical adoption

**Goal:** agree what the existing capture behavior means before preparing its
canonical records. This package is `review_pending`; merging it stores review
material and does not publish or activate subjects.

The [trace pilot](../README.md) already links one conversational note, the
existing `CN-CAPTURE` obligation, two candidates, working code and an executed
CLI test. This package makes the meaning and adoption scope inspectable through
the existing [publication process](../../../subject_publication.md). It adds no
promotion gate.

## The two proposed subjects

| Subject | Candidate | Proposed canonical file | Revision |
| --- | --- | --- | --- |
| Requirement `req.cn.capture` | [Requirement](../req.cn.capture.yaml) | `specs/requirements/req.cn.capture.yaml` | 1 |
| Criterion `ac.cn.capture-without-kind` | [Criterion](../ac.cn.capture-without-kind.yaml) | `specs/criteria/ac.cn.capture-without-kind.yaml` | 1 |

Requirement statement:

> The agent can save a short note during a conversation before choosing its semantic kind.

Criterion statement:

> Given an empty sketch, the CLI accepts one short note without a semantic kind, returns its stored revision and added-node diff, and a fresh process reads the same ID, label, detail and original human quotation with canonical false and no approval record.

The Requirement selects this criterion at **exact revision 1**. Both candidates
are unchanged from `1b2a6f22796769a3a5c1bcb5addc48a71ebe3f9b`. Their origin,
activation, disposition and adoption provenance remain unfilled. These are
proposed new origins, not updates to existing canonical subjects.

## Human words and their interpretation

[intent-lineage.json](intent-lineage.json) retains the original quotation:

> Думаю для него не надо усложнять, надо просто представить как во время беседы человека и агента последний делает как бы заметки, вызывая некие инструменты и сабагентов. А человек просто говорит и одобряет.

It comes from the already retained `notes` node and archive excerpt
`hypercode-notes/3`. This is an agent-curated excerpt with attributed human
authorship. Excerpt labels are document-local references, not native chat IDs.
Preparation time is recorded separately; the original message time is unknown.

The logical Intent candidate `intent.cn.capture` normalizes that quotation as:

> During a human-agent conversation, the agent preserves short notes while the person continues speaking and can later review them.

This is an agent interpretation for review. **Before choosing a semantic kind**
is the narrower interpretation already expressed by the proposal's `CN-CAPTURE`
obligation; those words do not occur in the human quotation. Review must assess
that interpretation, not infer acceptance from the instruction to prepare this
package.

The criterion is an agent-formalized executable scenario based on the proposal
context. Its candidate-statement hash does not claim a verbatim source quotation.

The proposed edge is `req.cn.capture --derived_from--> intent.cn.capture`. It
has no canonical storage binding or adoption decision. Exact criterion membership
alone does not establish the criterion's Intent-root path under SG-SPEC-0061.

## Review scope and pending decisions

[packet.json](packet.json) contains two subject selections, source hashes, the
proposed edge and four pending transition records:

| Subject | Proposal ingress | Canonical adoption |
| --- | --- | --- |
| Requirement | Proposal YAML → Requirement draft | Draft → canonical Requirement |
| Criterion | Proposal Markdown → criterion draft | Draft → canonical criterion |

Both ingress lineages refer to the retained quotation. Every transition has an
unset reviewer, decision time, outcome, rationale and review. The passing test
and previous authorization to implement the pilot supply no adoption decisions.

The reused workspace plan is
`workspace:a2800523-3588-4820-a47f-9fddc0fed3f5`, from proposal 0221. Its planned
source ref is
`refs/specgraph/subject-storage/a2800523-3588-4820-a47f-9fddc0fed3f5`.
The packet proposes the preparation base as the initial source commit; allocation,
initialization and topology selection remain pending. No source ref is initialized.

The next semantic review concerns the normalized Intent, both statements, exact
criterion membership, proposed new origins and subject-specific ingress. After
those decisions, complete origin/activation provenance, workspace/topology and
the exact writer request must be prepared for publication review.

The existing subject writer publishes Requirement/criterion records but does
not publish Intent roots or external `derived_from` relations. Their canonical
representation must be bound before claiming a complete Intent → Requirement →
criterion path. This package records that implementation gap.

## Binding and later publication

The packet binds inputs by SHA-256 and historical contracts and writer code by
immutable Git commit. Its scope digest is:

```text
9df09aa0388399ed38471043ec018ec6ff1565c1c98a994654c5cd815ade3d27
```

This hashes canonical sorted compact UTF-8 JSON excluding only
`approval_scope_sha256`. An actual review decision must also bind the reviewed
Git head, packet path and SHA-256 of the packet's raw bytes, as required by the
existing contract. Choose the reviewed commit after committing the preparation;
no self-referential commit is embedded.

This is pending semantic/adoption preparation, **not a complete materialization
request**. Filling provenance or activation changes the full records. Complete
records and the exact writer request require a newly bound review packet;
approval of this preparation cannot authorize those future bytes implicitly.
Writer request, publication authorization and topology selection remain `null`.

## Existing execution evidence

[execution-summary.json](execution-summary.json) identifies the successful
[PR #797 CI run](https://github.com/0al-spec/SpecGraph/actions/runs/40137206124),
attempt 1, and `cn-capture-evidence` artifact `12577211630` with its digest. Both
named pilot tests passed. Three CLI calls succeeded, and the draft candidate
hashes match the unchanged candidates in this package.

This historical evidence has not been transferred to future canonical revisions,
admitted as `tests_verified`, or used to claim Requirement fulfillment. Artifact
retention is finite; later use must recheck availability and byte identity.
Checkout revision and authored PR head remain distinct in the summary.

## Checks

```bash
.venv/bin/python -B -m pytest -q \
  tests/test_cn_capture_adoption_packet.py \
  tests/test_conversation_capture_pilot.py
```

Checks cover candidate/source identity, exact criterion membership, pending
transitions and the existing packet reader against committed Git blobs. Changed
input bytes and a changed scope are rejected. Successful reading establishes
integrity, not publication readiness or semantic approval. Production capture
code and counted Intent Atoms remain unchanged.
