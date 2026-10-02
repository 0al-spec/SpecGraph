# Proposed BDD Scenario Contract

SG-RFC-0223 proposes one scenario representation and a bounded Gherkin exchange
adapter. This is contract preparation only; runtime realization is deferred.

```yaml
canonical_mutations_allowed: false
runtime_code_mutations_allowed: false
evidence_admission_allowed: false
```

## Pilot observation

The Zeusus pilot authored 100 scenarios. The existing 0047 consumer extracted
34 because 66 used `specification.scenarios` rather than
`specification.bdd_scenarios`. Mechanical normalization preserved IDs and
ordered clause text and achieved 100/100 extraction. All six CLI previews still
reported `blocked` / exit 2. The final authoring candidate remained
`review_pending`; no gameplay execution or trusted evidence is implied.

The curated historical observation and original source hashes live in
`docs/reviews/0223_zeusus_bdd_observation.json`. The ordinary proposal and source
draft remain the authoritative preparation documents.

## Native contract and compatibility

The proposed `bdd_scenarios_v1` profile retains native `id`, optional descriptive
`scenario` title and ordered string `steps`. Repeated steps remain legal. One
shared loader should serve authoring validation and implementation extraction.
It distinguishes absent, explicitly empty, present and invalid input. A
recognized nonempty alternate container cannot be reported as an empty success.
Migration previews preserve source and emit counts, mappings and findings;
applying a migration requires separate authorization and review.
Application must match the exact reviewed preview and all source-byte/revision/
workspace bindings at a serialized mutation boundary. A `stale-preview` finding
means no source writes. The check and publication must prevent a concurrent edit
from being overwritten; validate the staged candidate before publishing it.

The native input matrix explicitly accepts absence and `bdd_scenarios: []`,
while rejecting null/wrong types, even an empty legacy `scenarios` container,
both containers (including two empty lists), malformed entries and whitespace-only
ID/step/title values. Duplicate YAML mapping keys fail before ordinary maps are
constructed, preserving the 0047 `UniqueKeyLoader` guard; repeated valid steps
remain ordered. Invalid input cannot have a successful extraction count.
These are proposed activated-profile rules; the
current 0047 default does not change.

Identity is independent of titles and parser-generated positions. Workspace
scope, owning-spec membership and source/content digests accompany bindings.
Moves, splits, merges and content edits do not silently transfer historical
execution evidence. Scenario identity is distinct from 0221 Requirement and
acceptance-criterion identity; no new canonical Scenario kind is introduced.

Immutable workspace identity is separate from slug/path, display name and URL.
It must agree with an explicit workspace binding. Observability references keep
owning-node resolution: a scenario in a sibling, parent or other workspace
cannot satisfy `observability.obligations[*].scenario_ids`. Equal local IDs in
different workspaces are distinct identities. Partial inventories declare scope
and cannot claim complete workspace uniqueness.

Normalized scenario pins require a reviewed canonical byte contract before
activation: included fields, serialization/encoding, text/Unicode policy, hash
algorithm, digest-contract version and domain separation, with cross-adapter
fixtures. Consumers reject unresolved/unknown contracts instead of making private
pins. Exact source/payload SHA-256 does not define normalized scenario equivalence;
historical pins retain their original contract.

## Exchange and evidence

The proposed `gherkin_basic_v1` adapter supports ordinary English scenarios
and plain ordered Given/When/Then/And/But steps with explicit scenario IDs.
It uses a pinned parser. Background, Rule, outlines, tables, doc strings,
non-English dialects and other unimplemented constructs produce findings.
Round-trip checks preserve supported identity, title, steps and retained
metadata structurally; they do not promise identical formatting bytes.

The lossless exchange package includes `bdd_scenario_exchange_envelope` schema
version 1 with workspace/spec binding, current payload digest, origin provenance,
Feature metadata, metadata keyed by scenario ID and file-level comments. Validate
the payload digest and agreement of representable fields before consuming the
envelope; retained exchange-only metadata cannot be independently proved from
the minimal native fields. Exactly one reserved ID tag must be directly on each
Scenario/Example. Duplicate reserved tags, even identical, a Feature-level ID,
and conflicting envelope IDs are invalid; ordinary tags retain scope and order.

File-level comments preserve parsed text/order, including duplicates, with
original locations retained as provenance. The first exporter uses one comment
block before Feature; proximity never assigns a comment to a scenario. Round-trip
comparison excludes emitted digests, locations, formatting and transient AST
IDs. Original pins remain in the envelope; without it historical provenance
retention is not promised. Native values that cannot round-trip unchanged through
the pinned grammar receive an explicit export finding.

Parsed, bound, executed and admitted evidence remain separate. Product test
adapters, including Swift Testing, own behavior execution; SpecificationCore
remains the product policy materialization layer. FeaturePassport keeps generic
producer bindings, and SpecSpace displays documented findings without deriving
readiness from scenario counts.

## Next bounded realization

The native contract candidate is proposed under **SG-SPEC-0062**. One targeted
Supervisor preparation used GPT 6 Luna Medium; its raw result and curated
`DRAFT-SPEC-0223` copy stay outside canonical specs. The curated copy has five
criteria, eleven future BDD cases and `review_pending`. It proposes an exact
`id`/`scenario`/`steps` allowlist, no v1 extensions and six separately named
SpecificationCore policies, including `BDDContainerPresenceSpec`, with RFC rule
references. These bindings are intended obligations, not implemented code or
canonical requirement identities.

`make test-native-bdd-characterization` passed 71 current compatibility tests:
50 new cases and 21 existing contract-pack cases. A bounded read-only audit pins
69 canonical SpecGraph files and six normalized historical Zeusus specs with
100 scenarios; the inspected scenario fields match the proposed allowlist. The
tests preserve existing behavior, including ignored alternate containers and
unchecked descriptive titles. They do not execute the future strict cases.

The preparation retains a false `state_runtime_failure` finding on quoted
diagnostic examples printed from documentation. Successful executor completion
does not clear the historical gate; a separate runtime follow-up must distinguish
actual diagnostics from transcript text. The raw/curated hashes, corpus scope
and exact excerpt live under `docs/reviews/0223_native_bdd_*` and
`docs/reviews/0223_executor_diagnostic_excerpt.txt`.

Review and adopt the native contract explicitly before one shared-loader slice
reproducing the pilot failure. Approved migration and Gherkin exchange follow
separately. Profile activation, the normalized digest byte contract and reserved
tag spelling remain separate decisions. Field policy is proposed for review,
not activated by these documents.

The [source preparation](https://github.com/0al-spec/SpecGraph/blob/365b387973ac61df32cc8532b3f3caddc3719b18/docs/proposals/0223_bdd_scenario_contract_and_gherkin_exchange.md)
received independent GPT 6 Astra / Ultra review with no P1/P2. Version 0.1.1
clarifies its three P3 items; the author follow-up is recorded separately in
`docs/reviews/0223_astra_review_followup.md`. New BDD-10/11/12 are future acceptance
cases, not executed tests or an independent review of the follow-up itself.
Separate GitHub review raised three P2 items. Version 0.1.2 retains the exchange
envelope and adds canonical digest activation prerequisites and stale-preview
write protection, with future BDD-13/14. Their process-evidence records live in
`tools/review_feedback_records.json`; document fixes do not prove writer enforcement.
PR #753 merged after the three threads were resolved. Version 0.1.3 records the
native preparation and executed compatibility tests; the original independent
verdict does not extend to that follow-up candidate.

`make proposal-tracking-gate` and `make docc-sync` check document preparation.
They do not execute future BDD cases or grant implementation authority.

## Source documents

- `docs/proposals/0223_bdd_scenario_contract_and_gherkin_exchange.md`
- `docs/archive/proposal_sources/0223_bdd_scenario_contract_and_gherkin_exchange.md`
- `docs/reviews/0223_zeusus_bdd_observation.json`
- `docs/reviews/0223_astra_review_followup.md`
- `docs/reviews/0223_native_bdd_contract_preparation.md`
- `docs/reviews/0223_native_bdd_preparation_evidence.json`
- `docs/reviews/0223_native_bdd_corpus_audit.json`
