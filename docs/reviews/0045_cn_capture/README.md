# CN-CAPTURE: one conversational note to an executable test

**Status: draft subjects, executable CLI observation. Canonical adoption pending.**

This bounded proposal-0045 pilot follows the existing `notes` node from the local
`hypercode-conversation-poc` sketch. Its original human quotation is already
published as `hypercode-notes/3` in the
[proposal source archive](../../archive/proposal_sources/0045_conversation_memory_exploration_vault.md).
[source-note.json](source-note.json) curates just this node and its provenance;
the ignored sketch and its full history remain local. Excerpt labels are local
references, not native chat IDs or authenticated conversation records.

## The chain and its current status

| Link | Actual artifact | Status |
| --- | --- | --- |
| Human words → note | `source-note.json`, sketch revision `62ea6b7d435d4bfa9d69eb748dd3a10e`, node `notes` | Retained quotation and agent-curated note |
| Note → proposal obligation | Proposal `SG-RFC-0045`, explicit atom `CN-CAPTURE` | Existing agent-authored draft obligation |
| Obligation → Requirement | [req.cn.capture.yaml](req.cn.capture.yaml) | Pending `subject_storage_candidate`, SG-SPEC-0069 shape |
| Requirement → criterion | [ac.cn.capture-without-kind.yaml](ac.cn.capture-without-kind.yaml), exact revision-1 membership | Pending candidate |
| Criterion → code | `conversation_notes.api.update_notes`, `read_notes`, `NotesStore.update` | Existing working implementation |
| Code → executed check | `tests/test_conversation_capture_pilot.py::test_cn_capture_saves_note_before_kind_selection` | CLI subprocess observation when executed |
| Check → retained evidence | `cn-capture-evidence` CI artifact | JUnit, inputs, raw CLI results and saved HC/HCS snapshot |

[bindings.json](bindings.json) keeps these links together. The binding test checks
the source quotation against the archive, the exact proposal statement,
Requirement/criterion membership, pending authority and Python declaration
resolution. Declaration existence is structural evidence; the separate CLI test
observes the behavior.

The proposed subject names reuse the **unallocated workspace plan** from
SG-SPEC-0069 / proposal 0221. They do not allocate that workspace or reserve
origins. Pending provenance, activation and disposition fields remain pending.
No canonical Requirement, criterion, Intent edge, promotion record or adoption
decision is created. SG-SPEC-0050/0051 remain the semantic and promotion context;
the pilot does not add a new semantic kind or writer authority.

## One bounded executable scenario

The replay uses a fresh isolated sketch and places the selected note at its root.
The historical `agent` parent and original sketch revision are retained as
context; this is not a reconstruction or continuation of that historical sketch.

The test invokes the real `conversation_notes_cli.py` in three fresh processes:

1. `read_notes` observes an empty sketch.
2. `update_notes` saves the selected ID, short label/detail and human quotation,
   without supplying a semantic `kind`.
3. `read_notes` restores the saved revision, ID, text and exact quotation.

Assertions cover the added-node diff, no semantic-kind field, `canonical: false`,
no approval history, and persisted `notes.hc`, `notes.hcs`, `metadata.json`.
The subject candidates describe this scenario; passing it does not adopt them.

## Reproduce and inspect

Run the binding and CLI checks with the repository environment:

```bash
.venv/bin/python -B -m pytest -q tests/test_conversation_capture_pilot.py
```

For a retained local observation, select a fresh task output directory:

```bash
CN_CAPTURE_EVIDENCE_DIR=/absolute/task-output/cn-capture \
  .venv/bin/python -B -m pytest -q tests/test_conversation_capture_pilot.py \
  --junitxml=/absolute/task-output/cn-capture/pytest-junit.xml
```

The output includes `request.json`, `observation.json`, curated input copies and
`captured-sketch/`. Every CLI invocation retains its exit code, stdout and stderr.
An assertion or command failure leaves the observation `incomplete`; the JUnit
result retains the test failure. A successful observation describes this one
case, not success of other tests in the suite.

`observation.json` records the actual Git checkout revision, explicit input/code
file SHA-256 inventory and `source_files_match_revision`. Local uncommitted edits
can produce a passing behavior test with that flag false. CI requires the listed
files to match its exact checkout commit; GitHub run IDs and the checkout SHA
are retained separately. A PR's merge-checkout SHA may differ from its authored
head. The inventory is bounded to this pilot, not a dependency/environment proof.

The existing CI test job runs the full suite once with JUnit output, then uploads
`cn-capture-evidence` even on failure. Inspect both the named tests and the raw
observation. A missing, incomplete or failed artifact is not successful evidence.
Retained GitHub identifiers and hashes are provider claims, not authentication.

## What this establishes

The pilot makes the source, draft subject, code references and executed CLI case
inspectable together. It does not establish canonical reachability, admitted
`tests_verified`, Requirement fulfillment, deployed runtime or outcome.
`fulfillment` and `admission` remain `not_evaluated`.

Canonical atoms remain unchanged. The draft proposal still has eight obligations:
this is a trace for its existing `CN-CAPTURE`, not a ninth atom. The next review
concerns the candidate statement, criterion and placement before canonical
adoption is considered through the existing process.

The [adoption review preparation](adoption/README.md) now collects the unchanged
candidates, human-source lineage, proposed Intent relation, pending transitions
and historical CI identity. It exposes the remaining publication decisions;
merging that preparation does not adopt the subjects.

The [separate semantic decision](adoption/semantic-review.json) records agreement
with the three displayed formulations. Canonical publication decisions and
Intent/relation storage bindings remain pending.

The [materialization package](materialization/README.md) supplies the complete
proposed Intent, two subjects, exact derivation, workspace/topology and writer
request. Its isolated preview creates no production origin or ref; templates
remain separate from actual publication decisions.
