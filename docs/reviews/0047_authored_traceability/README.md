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

The [author-curated candidate](candidate.yaml) groups these six requirements
into **four acceptance criteria** and six **future** BDD scenarios. They are
proposed semantic interpretations, not executed tests. Each requirement has
explicit source references. Exact five spellings, opt-in selection, immutable
request context, SHA-256 pins, alias behavior, diagnostic/CLI vocabulary and a
shared checker are separately labeled design choices in [lineage](lineage.json).
All 16 identity-profile acceptance cases have proposed requirement links.
Mapping container/mode details remain a separate design follow-up.

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
is prepared for a future attempt, not executed. The historical failed workspace
and gate were not approved or reset; the pending candidate is a separate manual
review artifact.

The native bridge labels its operator node `canonical_candidate` even for this
failed attempt. That generator label is retained and does not override the run's
failure or create canonical truth. Report the actual run fields rather than
inferring success from that label or from the mere presence of a candidate file.

## Remaining boundary and next step

The inspectable preparation chain is:

```text
retained human intent + product authoring context
  -> native mediated intent / bounded operator request
  -> proposed local requirements (manual review candidate)
  -> requirement-to-contract and engineering-choice links
```

Canonical Intent -> Requirement reachability is **not yet satisfied**. Draft
handles, JSON links and proposal mentions are preparation, not admitted canonical
edges under SG-SPEC-0061. A reviewed canonical root, subject identities and valid
derivation edges must be resolved through the existing graph process before
claiming that closure. Human review also decides whether the source interpretation
and proposed parent are appropriate. No runtime checker/profile is activated.

Next: review this requirement/source separation and restore the intended
Supervisor executor route, then prepare the bounded canonical adoption. Do not
use the generic SG-SPEC-0020 citation as a replacement for that work.
