# 0047: source intent and authored traceability requirements

Status: **review preparation; canonical derivation remains unresolved**.
Runtime realization is `deferred_until_canonicalized`.

## Why this packet exists

The operator asked which Intent produced the identity and mapping contracts.
The answer exposed a gap: feedback was linked to proposal 0047, but the exact
requirements had not been prepared as source-bound graph material. A generic
`SG-SPEC-0020` PR citation cannot establish these requirements; that spec owns
executable-layer ontology and excludes runtime observability contract semantics.

The [capture](intent.json) retains three exact user quotes separately from the
assistant's interpretations. Original message timestamps are not retained.
Two Zeusus authoring inputs are identified by locator and exact SHA-256; only
their public summaries are included. These retained authoring instructions are
operator context, not independently attested transcripts. ZST-02/ZST-04 are
diagnostic feedback, not additional human product goals.

## What is proposed

| Candidate-local requirement | Meaning |
| --- | --- |
| ATC-REQ-001 | Retain the source intent and label inferred requirements and engineering choices. |
| ATC-REQ-002 | Preserve requested specification/rule/component/implementation attribution on each obligation. |
| ATC-REQ-003 | Preserve requested authoring meaning across refinement and projection; expose omissions or ambiguous renaming. |
| ATC-REQ-004 | Make intended mapping scope and omissions visible; distinguish valid references from coverage. |
| ATC-REQ-005 | Bind a scenario only when an actual tagged harness supplies it. |
| ATC-REQ-006 | Preserve non-interference and the declaration-versus-execution/evidence boundary. |

The historical [author-curated candidate](candidate.yaml) groups these six requirements
into **four acceptance criteria** and six **future** BDD scenarios. They are
proposed semantic interpretations, not executed tests. Each requirement has
explicit source references. Exact five spellings, opt-in selection, immutable
request context, SHA-256 pins, alias behavior, diagnostic/CLI vocabulary and a
shared checker are separately labeled design choices in [lineage](lineage.json).
All 16 identity-profile acceptance cases have proposed requirement links.
The latest [Supervisor candidate](retry/candidate.yaml) retains those identities
and acceptance statements, and proposes explicit mapping scope, location and
full/partial coverage semantics. Its declaration syntax and implementation remain
separate design follow-ups.

## Existing SpecGraph workflow used

One bounded OperatorRequest was submitted through the native Supervisor bridge
in an isolated preparation worktree. It generated native pre-canonical captures:

- `user_intent::authored-traceability-0047` (`mediated`, authority `mediator`);
- `operator_request::0047-authored-traceability-preparation`.

The first is a mediated capture grounded in the quotes, not a newly adopted
canonical Intent root. The packet/source are assistant-curated; neither node
attests that the human accepted every interpretation. The temporary target
`DRAFT-SPEC-0047-TRACEABILITY` is retained outside canonical `specs/nodes` in this
PR. No canonical ID is reserved. The proposed parent `SG-SPEC-0062` groups
record/declaration semantics, alongside native BDD `SG-SPEC-0070`; it is a review
decision, not a change to the frozen observability or executable boundaries.

## Actual run and correction

Run `20261022T220513Z-DRAFT-SPEC-0047-TRACEABILITY-f7d8f0ac` attempted the configured
Sol 6.1 / Medium profile. The installed CLI rejected `gpt-6.1-sol` for the signed-in
ChatGPT account before refinement. Result: `failed / escalate / escalated`,
zero changed files, `accepted_canonical_diff: false`; no model substitute or
successful refinement is claimed.

The initial assistant-authored seed also had six acceptance criteria (limit five)
and no aligned acceptance evidence. Its four validation errors are retained in
[evidence](evidence.json), with original-input pins and raw-record digest. The
original input/request are preserved in PR ancestor `f52254d8`; the isolated
seed revision is recorded as well. The [corrected input](input.yaml) has four
aligned acceptance/evidence pairs. Its evidence prose describes candidate
sections only, never actual runtime conformance. The [corrected request](corrected-operator-request.json)
was executed in the isolated retry described below. The historical failed
workspace and gate were not approved or reset; the original pending candidate
remains a separate manual review artifact.

The native bridge labels its operator node `canonical_candidate` even for this
failed attempt. That generator label is retained and does not override the run's
failure or create canonical truth. Report the actual run fields rather than
inferring success from that label or from the mere presence of a candidate file.

### Repeat after CLI update

Run `20261023T050721Z-DRAFT-SPEC-0047-TRACEABILITY-d98b7e69` used the corrected
request and a fresh preparation worktree. Executor stderr identifies Codex
`0.163.0`, `gpt-6.1-sol`, reasoning effort `medium`; the native record's
`child_model` field is empty and is not repaired by this packet. The result was
`ok / done / review_pending`, exit `0`, with all eight validator results true.
`accepted_canonical_diff` remains **false**. The local refinement check's
`decision: approve` is not a human adoption decision.

The [retained raw child candidate](retry/candidate.yaml) changes only the proposed
mapping contract: expected rule scope is independent of mapping rows, exact
reference validity is distinct from coverage, and full coverage cannot be
established by row counts. The unexecuted ATC-SCENARIO-004 now describes the
observed 10-of-15 case and names the five uncovered rules. All six requirement
IDs/source references, four acceptance statements and six future scenario IDs
are preserved. No BDD or runtime test was executed.

The raw child file retains `gate_state: none`; the **parent pending envelope**
records `review_pending` and the candidate's sanitized sync digest. These are
different lifecycle surfaces. The parent's root spec still contains the seed
body, so it is not archived as the refinement output. [Retry evidence](retry/evidence.json)
records both the raw-byte hash and the Supervisor's sanitized sync hash, along
with the envelope, result, diagnostic finding and source pins. Retry native
intent projections are archived under `retry/native_intent/`; the active
first-attempt captures remain historical and unchanged. Original `evidence.json`
artifact pins refer to revision `6b995ceb14b42024aeea6d68af1aef11e45ef862`.

The run is not diagnostically clean. Its retained `state_runtime_failure` finding
matches examples printed from `CONTRIBUTING.md`, not an observed initialization
failure. Separately, the CLI emitted real PATH-alias and rollout-flush warnings.
The executor still exited zero and supplied both protocol markers. No finding
was erased, classifier patched or gate approved by this preparation.

## Remaining boundary and next step

The inspectable preparation chain is:

```text
retained human intent + product authoring context
  -> native mediated intent / bounded operator request
  -> proposed local requirements (Supervisor candidate pending review)
  -> requirement-to-contract and engineering-choice links
```

Canonical Intent -> Requirement reachability is **not yet satisfied**. Draft
handles, JSON links and proposal mentions are preparation, not admitted canonical
edges under SG-SPEC-0061. A reviewed canonical root, subject identities and valid
derivation edges must be resolved through the existing graph process before
claiming that closure. Human review also decides whether the source interpretation
and proposed parent are appropriate. No runtime checker/profile is activated.

Next: review the refined mapping semantics and requirement/source separation,
then prepare the bounded canonical adoption. Do not
use the generic SG-SPEC-0020 citation as a replacement for that work.
