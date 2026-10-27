# Pytest channel qualification: candidate C2b profile

Profile: `specgraph.pytest-channel-qualification/v1`.
Status: `proposed_contract`; runtime evaluator: **not implemented**.
Owner proposal: [RFC 0226](proposals/0226_traceability_evidence_providers_and_svc.md).
The six [draft obligations](proposals/0226_traceability_evidence_providers_and_svc.intent.yaml)
remain separate from canonical Intent Atoms.

This profile asks whether a selected atom has an explicitly declared, statically
resolvable test channel. It does not ask whether the test ran, passed, is
collectable in a particular pytest environment, or sufficiently verifies the
atom's meaning. Here `qualified` means **structurally qualified under this
profile**, not `tests_verified` or accepted.

```yaml
qualification_basis: source_resolution_only
runtime_profile_activation_allowed: false
canonical_mutations_allowed: false
evidence_admission_allowed: false
```

## Selected input and identity

The first cohort is exactly SG-SPEC-0071 at an explicitly selected repository
identity and full Git SHA. Use the existing declaration EvidenceProvider and
immutable TraceSnapshot with resolver profile
`specgraph.publication-exact-links/v1`. The declared atom inventory is the
canonical node's explicit `atoms.intents`, not every test, policy object,
acceptance mention or producer obligation in the repository.

An atom key is `(repository_id, source_revision, spec_id, atom_id)`. A link keeps
its owner, relation, target kind/selector and declaring source location. Its
resolved candidate retains the target path/location and source digest. Neither
a function rename nor an array-index move silently creates a new atom identity;
the selected revision remains part of measurement provenance.

Select declaration providers explicitly from the existing registry. Record
their IDs, versions, resolver profile and analyzer/source digests. A profile
string supplied by an arbitrary provider is not authority to join that selection.
Execution-only and other capability reports are retained as provenance but do
not supply atom inventory or qualification facts. No provider discovery,
source import, `pytest --collect-only`, test run, network request or LLM call is
required by the qualification operation.

Canonical authored evidence and trace links remain the governing inputs.
Resolution is a derived interpretation of those links. This proposed diagnostic
contract does not admit raw execution reports as a new SG-SPEC-0021 input class
or activate an SVC profile in the metric registry/viewer.

## Channel decision

Consider only an atom's explicit `verifiable_by` links. For v1, the supported
selector is `tests/.../test_*.py::test_*`, naming one direct top-level Python
function or async function under the existing resolver. Class methods, imported
aliases, dynamic exports, parameter-case IDs and non-Python channels need a
separately qualified extension; they are not guessed or silently discarded.

| Prepared facts | Channel state | Meaning |
| --- | --- | --- |
| Supported pytest link, owner in selected inventory, exact source available, one matching function declaration, `resolved`, no disputed binding | `qualified` | There is a source-bound structural verification channel. |
| Supported, available source with conclusive `unresolved`, `ambiguous` or `wrong_kind` resolution | `unqualified` | This declared link does not establish the required unique function binding. |
| `unsupported`, `unavailable`, unknown status, contradictory provenance, inconsistent resolved candidate, or unresolved provider conflict | `unknown` | The profile cannot decide; this is not a negative observation. |

The candidate must match the declared target kind/selector and its digest must
agree with the selected source manifest. A nonempty selector, an arbitrary
same-named function, a policy object's existence, or an old successful run alone
does not qualify. `resolved` is interpreted under its resolver profile rather
than trusted as an unqualified string from an arbitrary JSON document.

This AST boundary deliberately does not prove importability, pytest collection,
fixture validity, assertion coverage or semantic sufficiency. A function with
an import error elsewhere in its module may still have a structurally resolved
declaration. Execution evidence can expose that limitation independently.

## Atom decision and repeated observations

Apply these alternatives in order:

1. At least one uncontested qualified channel makes the atom `qualified`.
2. Otherwise, at least one unknown channel makes it `unknown`.
3. Otherwise it is `unqualified`, including an explicitly empty channel list
   when enumeration of that authored list is complete.

Several good channels still count as one atom. A known good channel plus an
unavailable alternative remains a qualified atom; retain that alternative's
diagnostic. A conflict on one candidate does not invalidate a different,
uncontested good channel. A disputed binding cannot qualify by selecting the
first provider or whichever report says `resolved`.

Identical repeated observations coalesce with all origins retained. Required
providers must agree on complete atom membership and declaration identity;
conflicting or duplicate authored atom IDs make the inventory incomplete.
Disagreement over enumeration of an atom's channels remains explicit unknown
input, not proof that the missing link was absent. An orphan `verifiable_by`
owner is an integrity diagnostic and cannot add an atom to the denominator.
Unreconciled inventory integrity prevents an exact result.

Do not use `NodeEvidence.resolution_complete` as a blanket score gate: C1
resolves policy, passport and other links as well as test channels. Qualification
completeness concerns the selected atom inventory and its relevant channels;
unrelated link diagnostics remain visible without becoming test failures.

## Exact result and unknown data

Let N be the complete, unambiguous selected atom inventory. Preserve each atom's
state and report qualified/unqualified/unknown counts separately.

| Inventory and atom states | Result | Exact numerator / denominator / value |
| --- | --- | --- |
| Required inventory missing, incomplete or conflicting | `not_computable` | `null / null / null`; retain observed subjects as partial data. |
| Complete inventory, N = 0 | `not_applicable` | `null / 0 / null`. |
| Complete nonempty inventory, at least one unknown atom | `not_computable` | `null / N / null`; known-qualified count is partial, not an exact numerator. |
| Complete nonempty inventory, no unknown atoms | `computed` | Q / N / Q÷N, counting each qualified atom once. |

A complete inventory with no qualified or unknown atoms therefore has a valid
zero. Missing required data must not manufacture that zero or shrink N by
dropping difficult atoms. Missing optional execution does not make an atom
unknown when its structural channel is already conclusive. Do not compare this
candidate fraction with the legacy acceptance-status proxy as one time series.

## Execution and revision boundary

Execution is a parallel observation. A completed failure leaves a structurally
qualified channel qualified and retains the recorded test failure. A skipped,
missing, unavailable or mismatched run is reported with its own meaning. None
of these states becomes successful execution or a semantic fulfillment verdict.

C2a currently retains five explicitly bound PB publication scenarios. Its
aggregate suite result cannot stand in for execution of all PE policy-test
channels. Joining an observation to a channel requires the explicit selector
and atom/criterion binding, source SHA and full selected run/attempt identity.
Until that exact join exists, leave execution association unknown/not collected.
Do not match by function basename or infer that the whole suite ran each link.

Historical PR review and test records keep their original revision/scope. A new
source revision requires resolving the current link again; an old successful
run cannot repair current missing source. Revision/run binding does not prove
wall-clock freshness or authenticate the observer. Fulfillment, readiness,
admission and semantic sufficiency stay `not_evaluated` in this profile.

## Acceptance examples for implementation

These are proposed acceptance cases, not newly executed runtime tests.

| ID | Input | Expected interpretation |
| --- | --- | --- |
| C2B-01 | One exact resolved test and no execution report | Atom qualified; execution not collected. |
| C2B-02 | Same binding with a recorded failed run | Qualification unchanged; test failure retained separately. |
| C2B-03 | Test name absent in an available file | Channel unqualified; complete single-atom result is zero. |
| C2B-04 | Required test file cannot be read/parsed | Channel unknown; single-atom exact fraction unavailable. |
| C2B-05 | One good and one unknown alternative | Atom qualified once; unknown alternative retained. |
| C2B-06 | Only bad and unknown alternatives | Atom unknown, not unqualified. |
| C2B-07 | Complete authored atom with no channels | Atom unqualified; no invented execution result. |
| C2B-08 | Repeated identical provider observation | Same atom/channel counts; origins preserved. |
| C2B-09 | Providers disagree on the only binding | Atom unknown; provider order cannot select a winner. |
| C2B-10 | Disputed alternative plus independent good channel | Atom qualified through the uncontested channel. |
| C2B-11 | Duplicate atom ID or incompatible complete inventories | Exact denominator and fraction unavailable. |
| C2B-12 | Complete empty selection versus missing source | Respectively not_applicable versus not_computable. |
| C2B-13 | Test deleted in new source revision; earlier run passed | Current resolution fails; historical success stays historical. |
| C2B-14 | Policy link fails but all relevant test channels resolve | Preserve policy diagnostic; structural channel result is independent. |
| C2B-15 | Async/function declaration resolves but pytest cannot collect it | Structural qualification remains bounded; do not claim runnable/verified behavior. |
| C2B-16 | C2a PB suite passes; no exact observations for PE tests | Do not transfer PB execution outcomes to PE atoms. |

## Pinned reference worksheet and next slice

The [reference worksheet](evidence/0226_c2b_reference_worksheet.json) applies the
proposed interpretation by author review to declarations at
`b4d0f25ec8856c7cd3e8af886506f837253ccdbd`. C1 observed 13 atoms and 18 explicit
test links; every link resolved. The candidate expected result is 13/13, while
execution was not collected. This is a proposed-profile reference case, not a
production SVC calculation or evidence that 13 obligations passed tests.

The implementing slice should add one pure qualifier over the typed snapshot,
named SpecificationCore policies for the three decisions above and an opt-in
diagnostic entry point. Keep parsing/collection outside the rules. Reuse the
existing resolver, preserve legacy outputs and verify negative/conflict cases
before proposing any default metric, viewer or CI integration.
