# Source: BDD scenario contract and Gherkin exchange

Captured on 2026-10-02 from the Zeusus pilot discussion. This is operator intent
and historical observation, not adoption of a canonical schema or execution
policy. The operator asked whether the Gherkin-style YAML format was a project
convention or a SpecGraph capability, then authorized finding a suitable proposal
or preparing a new one: "Да, найди proposal или напиши новый".

## Requested Concern

Separate the implemented `bdd_scenarios` / `id` / ordered `steps` consumer
contract from human Given/When/Then conventions. Propose one shared typed
scenario contract, strict shape validation and Gherkin import/export. Use
Zeusus as a source-grounded pilot and retain explicit evidence boundaries.

## Discovery

Discovery base: SpecGraph `ca3967e6b9d1b196c901ff6fcb0f77b7a98ecfc7` (main).
Fetched remote refs, topic branch names, proposal/source files in local
worktrees and open GitHub PR metadata were inspected. The open PR list was
empty at discovery. Searches for Gherkin, BDD and scenario-contract terms found
0047 consumer docs/code/tests and Gherkin examples in 0221, but no dedicated
proposal. Related architecture proposals 0006, 0021 and 0050 were inspected;
they do not define the scenario exchange contract.

`make proposal-id` returned `ready`, next `0223`, highest used `0222`, with no
blocking findings on 2026-10-02. No matching 0223/topic claim was found in the
inspected refs/worktrees/PRs. Allocation is a local observation, not a remote
reservation or canonical adoption.

## Historical Pilot Sources

Zeusus has no configured Git remote. Referenced paths are repository-relative
and pinned to its local commit `919320f7b0db246f2feee06cab01e62c20256ab0`:

- `docs/evidence/command-history-specgraph/bdd-amendment/README.md`
- `docs/evidence/command-history-specgraph/bdd-amendment/normalization-report.json`
- `docs/evidence/command-history-specgraph/bdd-amendment/cli-extraction-report.json`
- `docs/evidence/command-history-specgraph/bdd-amendment/final-run.json`

The curated [observation](../../reviews/0223_zeusus_bdd_observation.json) carries
source-file hashes and extracted counts without private absolute paths.
Original review commit: `93607cf024cb75f92cc711c90e3a1995bd612bad`.
Pilot tool commit: SpecGraph `c72f4017212a02da70dc275edf3f5cf06a27893f`.

Observed mismatch: 100 authored scenarios, 34 extracted before normalization;
66 scenarios used a different container. After mechanical conversion the real
parser and CLI extracted all 100. Six CLI previews still had `blocked` status
and exit code 2. The final root-only authoring run retained `review_pending`.
The normalized package preserves IDs, clause strings, order and gameplay fields.
No gameplay test execution, source adoption or signed receipt is claimed.

A title-only authoring pass produced "Clear Redo Only After a New Changing Root",
which overlooked independent expiry. Its exact candidate was archived and a
bounded follow-up changed the title to "New Changing Root Invalidates Redo".
This illustrates a semantic-review limit of structural checks.

## Design Intent and Boundaries

- Preserve native ID and ordered steps compatibility first.
- Reject recognized incompatible shapes instead of treating them as no scenarios.
- Keep identity separate from display text, pins and execution evidence.
- Reuse 0047 and 0221 boundaries; do not equate scenarios with all requirements.
- Add Gherkin as a versioned adapter with explicit supported/unsupported cases.
- Keep product test frameworks independent and FeaturePassport generic.
- Prepare the proposal now; implement a bounded shared-loader slice after review.

Primary exchange references: [Cucumber Gherkin reference](https://cucumber.io/docs/gherkin/reference/)
and [official parser project](https://github.com/cucumber/gherkin). These were
inspected as grammar/parser sources, not copied as application code.

## Follow-up after independent review

On 2026-10-02 the operator requested independent GPT 6 Astra / Ultra review of
head `365b387973ac61df32cc8532b3f3caddc3719b18`. The read-only review reported no
P1/P2 and three P3 clarifications before activation: the exact native input
matrix, immutable workspace/reference scope, and metadata/reserved-ID handling
for exchange. The operator then authorized clarification: "Уточни по замечаниям, да".

Version 0.1.1 makes these proposed rules explicit and adds acceptance cases.
The [author follow-up](../../reviews/0223_astra_review_followup.md) distinguishes
the original independent review from subsequent edits and future implementation
checks. This authorization does not activate a shared loader, migrate product
sources or grant evidence admission. Historical pilot source hashes are unchanged.

## Follow-up during final PR verification

The operator requested "Хорошо, проверяй" after the 0.1.1 clarification.
A live GraphQL check found three open P2 threads from the separate
chatgpt-codex-connector review of original head
365b387973ac61df32cc8532b3f3caddc3719b18: canonical digest bytes,
exchange metadata and stale migration previews. The independent Astra verdict
and this GitHub review are different evidence sources.

The author prepared version 0.1.2: retain the envelope, make canonical digest
decisions required before activation/binding, and require current source pins
at the serialized migration write boundary with no writes on stale input.
Future BDD-13/14 supplement the existing twelve cases.
See [the follow-up record](../../reviews/0223_astra_review_followup.md) and
tools/review_feedback_records.json for provenance and prevention classification.
This clarification does not implement or activate the proposed runtime.

## Follow-up after proposal merge

The operator authorized resolving the three P2 threads, then requested:
"Ок, сливай сейчас и продолжай". PR #753 merged by rebase at
`0a08e38a23fbbe5ad7450c0d31ed48cec84a094e`, with zero unresolved threads.
This authorizes continuation of preparation; it does not silently adopt a
canonical policy or activate a strict profile.

The author prepared one native declaration candidate through a targeted
Supervisor pass using GPT 6 Luna Medium and the RFC 0221 temporary-draft pattern.
SG-SPEC-0062 is its proposed parent. Raw and curated candidates remain outside
the canonical tree. Author curation proposes explicit fields, six named
SpecificationCore policies with rule references, local observability and two
additional future BDD cases. No implementation conformance is claimed.

Fifty new compatibility characterization cases plus 21 existing contract-pack
tests passed. A bounded audit pinned 69 canonical SpecGraph sources and six
historical normalized Zeusus sources with 100 scenarios; it is not a complete
workspace ecosystem inventory. The Supervisor's review gate remains pending.
A false runtime finding on quoted documentation is retained as a separate
diagnostic observation. See the [native preparation record](../../reviews/0223_native_bdd_contract_preparation.md).
