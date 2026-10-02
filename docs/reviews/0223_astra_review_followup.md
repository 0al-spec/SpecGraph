# 0223 Independent Review Follow-up

Date: 2026-10-02
Reviewer: GPT 6 Astra / Ultra, independent read-only agent with no conversation fork
Reviewed head: `365b387973ac61df32cc8532b3f3caddc3719b18`
Review object: [PR #753](https://github.com/0al-spec/SpecGraph/pull/753)
Evidence class: independent automated contract review, followed by author clarification

## Original Verdict and Scope

The reviewer reported no P1/P2. It considered the reviewed head suitable for
review/merge as contract preparation, with canonical adoption and activation
remaining separate decisions. It examined all eight changed files, governing
documents, the 0047 consumer/code/tests, relevant 0006/0021/0221 contracts and
official Gherkin sources. Four pinned Zeusus packet hashes and its extraction
counts matched the curated historical observation.

No tests, builds, Supervisor or gates were run by the reviewer. It made no file
or GitHub changes. The original verdict applies to the reviewed head; the
clarifications below are author changes, not an independent approval of new bytes.
The operator authorized them with "Уточни по замечаниям, да".

## Three P3 Items and Clarifications

| Item | Root cause / counterexample | Documented prevention |
| --- | --- | --- |
| Native profile matrix | `artifact_contract_validation_gap`: null/empty alternate shapes could be interpreted differently; a last-key-wins parser could discard one `steps` declaration before validation | Explicit matrix for absence, valid empty native, invalid null/empty legacy/mixed containers, whitespace-only values and duplicate YAML keys. BDD-03 covers the matrix; characterization fixtures remain future work. |
| Workspace identity and reference scope | `scope_isolation_gap`: mutable slug/path could appear to create identity; a sibling scenario could incorrectly satisfy an owning-node obligation | Immutable workspace binding distinct from display/path; preserve 0047 owning-node reference resolution. BDD-10 covers separate workspaces, rename and cross-node references. |
| Metadata and reserved IDs | `artifact_contract_validation_gap`: a Feature ID could be inherited, two differing tags could select arbitrary identity, or comments between scenarios could acquire guessed ownership | Exactly one direct reserved Scenario ID; scoped ordinary tags; versioned payload/envelope binding and file-level ordered comments. BDD-05/11/12 cover round-trip, duplicate/wrong-scope IDs, stale digests and conflicting metadata. |

Prevention action: `documentation_rule_added`. This records explicit proposed
contract rules; it does not claim `validator_added` or `regression_test_added`.
Verification kind for the author contract check: `manual_contract_review`.
Current 0047 `UniqueKeyLoader`, string eligibility and node-local observability
resolution were read as the compatibility baseline; behavior tests were not run.
Document gates and JSON/link checks verify preparation coherence only.

## Separate GitHub Review of the Original Head

The GitHub `chatgpt-codex-connector` review of the same original head reported
three P2 items. This is a separate review, not the Astra verdict above:

- [Canonical scenario digest](https://github.com/0al-spec/SpecGraph/pull/753#discussion_r4167455778): version 0.1.2 makes field selection, canonical bytes/encoding, text policy, hash/version/domain separation and cross-adapter fixtures explicit prerequisites before activation or normalized evidence binding. BDD-14 names the future check; no serializer is selected or implemented by this PR.
- [Exchange metadata envelope](https://github.com/0al-spec/SpecGraph/pull/753#discussion_r4167455789): version 0.1.1 already added the versioned envelope, bindings/digests, scoped metadata and comment provenance. BDD-05/11/12 name future checks.
- [Stale migration previews](https://github.com/0al-spec/SpecGraph/pull/753#discussion_r4167455799): version 0.1.2 requires matching the reviewed preview and all input pins before any write, with serialized check/publication protection against concurrent edits. Mismatch emits `stale-preview` with no source writes. BDD-13 names the future check.

All three are classified `artifact_contract_validation_gap` with prevention
`documentation_rule_added` and `manual_contract_review` verification in
`tools/review_feedback_records.json`. Runtime fixtures/enforcement remain future
work, and documented fixes do not themselves resolve GitHub thread state.

## Remaining Work and Evidence Boundary

The [proposal](../proposals/0223_bdd_scenario_contract_and_gherkin_exchange.md)
retains versioned profile activation, corpus audit and schema fixtures as gates
before runtime implementation/activation. Historical pilot observation bytes are
unchanged. Native-loader fixtures, exchange schema/adapter and gameplay execution
remain unimplemented by this preparation PR; no trusted receipt is issued.

Next bounded slice: graph-owned shared-loader contract and characterization
fixtures for the current 0047 behavior, including the complete native matrix
and reference-scope cases. Default activation requires a separate explicit decision.
