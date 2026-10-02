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

Identity is independent of titles and parser-generated positions. Workspace
scope, owning-spec membership and source/content digests accompany bindings.
Moves, splits, merges and content edits do not silently transfer historical
execution evidence. Scenario identity is distinct from 0221 Requirement and
acceptance-criterion identity; no new canonical Scenario kind is introduced.

## Exchange and evidence

The proposed `gherkin_basic_v1` adapter supports ordinary English scenarios
and plain ordered Given/When/Then/And/But steps with explicit scenario IDs.
It uses a pinned parser. Background, Rule, outlines, tables, doc strings,
non-English dialects and other unimplemented constructs produce findings.
Round-trip checks preserve supported identity, title, steps and retained
metadata structurally; they do not promise identical formatting bytes.

Parsed, bound, executed and admitted evidence remain separate. Product test
adapters, including Swift Testing, own behavior execution; SpecificationCore
remains the product policy materialization layer. FeaturePassport keeps generic
producer bindings, and SpecSpace displays documented findings without deriving
readiness from scenario counts.

## Next bounded realization

Review the shared native model and corpus compatibility first, then implement
one shared-loader slice reproducing the pilot failure. Approved migration and
Gherkin exchange follow separately. Field allowlists, profile selection and
reserved tag spelling remain decisions for activation review.

`make proposal-tracking-gate` and `make docc-sync` check document preparation.
They do not execute future BDD cases or grant implementation authority.

## Source documents

- `docs/proposals/0223_bdd_scenario_contract_and_gherkin_exchange.md`
- `docs/archive/proposal_sources/0223_bdd_scenario_contract_and_gherkin_exchange.md`
- `docs/reviews/0223_zeusus_bdd_observation.json`
