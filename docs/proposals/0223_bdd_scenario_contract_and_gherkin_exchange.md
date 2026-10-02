# 0223 BDD Scenario Contract and Gherkin Exchange

RFC: SG-RFC-0223
Version: 0.1.0

## Status

Draft proposal; contract preparation only. Runtime realization is deferred
until the bounded contract is reviewed and adopted through the existing graph
process. This PR registers the proposal and historical pilot observations; it
does not enable a new validator, import scenarios, change canonical specs, or
grant implementation/admission authority.

```yaml
canonical_mutations_allowed: false
runtime_code_mutations_allowed: false
evidence_admission_allowed: false
```

## Source Material

- [Operator request and discovery](../archive/proposal_sources/0223_bdd_scenario_contract_and_gherkin_exchange.md)
- [Curated Zeusus observation](../reviews/0223_zeusus_bdd_observation.json)
- [0047: Evidence-Backed Build Protocol](0047_evidence_backed_build_protocol.md)
- [0006: Typed Validation](0006_typed_validation.md)
- [0021: Deterministic Validation Profiles](0021_deterministic_transition_checks_and_validator_profiles.md)
- [0221: Requirement Identity and Lineage](0221_stable_requirement_identity_and_lineage.md)
- [Current explicit-node contract pack](../implementation_contract_pack.md)

## Problem and Observed Baseline

The Zeusus command-history pilot authored 100 scenarios across six specs.
Four specs placed 66 scenarios under `specification.scenarios`, with separate
`given`, `when`, and `then` fields. The downstream 0047 parser reads
`specification.bdd_scenarios`, defaults a missing container to `[]`, and
expects `id` plus ordered string `steps`. It consequently extracted only 34
scenario IDs. The pilot reported an accepted authoring-validation pass despite
this incompatible representation.

Mechanical normalization preserved all IDs, clause text, order and gameplay
rules, and increased actual extraction to 100/100. Six real CLI previews still
returned `blocked` / exit 2 because source gates/status and missing
observability remained independent requirements. The final root authoring run
remained `review_pending`. These observations are historical, source-pinned
pilot evidence, not execution of the gameplay scenarios or trusted receipts.

Today the parser validates IDs and nonempty ordered steps, permits repeated
steps, and rejects duplicate IDs within one node. It does not interpret the
human `scenario` title or enforce Gherkin grammar. Given/When/Then strings in
YAML are therefore an authoring convention around a partial machine contract.
Full `.feature` support is absent from this consumer.

No dedicated BDD/Gherkin proposal was found in the inspected `main`, topic
refs, local worktrees or open PRs. Proposals 0006/0021 supply validation
architecture, 0047 owns implementation/evidence handoff, and 0221 owns
normative requirement/criterion identity. This proposal fills the scenario
representation and exchange gap without replacing those contracts.

## Proposed Contract

### 1. Shared native scenario model

One typed scenario model and deterministic loader MUST be used by the
supervisor's candidate validation, prompt contract, sync-back checks and
implementation-contract extraction. Consumers may add their own gate checks,
but MUST NOT reinterpret the scenario container independently.

The first profile, provisionally named `bdd_scenarios_v1`, preserves the
existing native representation:

```yaml
specification:
  bdd_scenarios:
    - id: EXAMPLE-HISTORY-001
      scenario: Expired operation cannot restore a building
      steps:
        - Given a retained demolition operation whose deadline has been reached
        - When undo is requested at the command boundary
        - Then the operation is unavailable and the live world is unchanged
```

The ID MUST be a nonempty string. Steps MUST be a nonempty ordered list of
nonempty strings; repeated text is legal and MUST NOT be deduplicated or sorted.
`scenario` is
an optional human title for backward compatibility; new authoring SHOULD
supply a nonempty title. A missing title may be displayed as the ID without
writing a generated title into the source. A supplied malformed title is a
finding. The v1 field allowlist and reserved extension rules must be finalized
with a corpus audit before activation; unsupported fields cannot be silently
dropped during exchange.

This native profile does not infer executable step bindings or require exactly
one Given/When/Then triplet. A stricter authoring policy can be separately
selected; it cannot silently invalidate existing 0047 step sequences.
Profile/version selection and effective configuration are recorded in derived
evidence. Missing selection means the documented legacy profile during rollout;
unknown versions fail closed once this resolver is implemented. This proposal
does not add a configuration key or change the current default.

### 2. Presence, incompatible shapes and migration

The loader MUST distinguish `absent`, `explicit_empty`, `present` and
`invalid` scenario input. Absence can be legitimate for a non-scenario node;
the readiness policy, not the loader, decides whether that is sufficient.
The observation must report the selected profile, source container, authored
count when identifiable, extracted count and findings.

For the activated shared profile:

- A nonempty `specification.scenarios`, a known alternate/misspelled container
  declared by the profile, or a clauses-only entry MUST produce an explicit
  incompatibility finding. The loader does not guess scenario meaning from
  arbitrary product fields or fuzzy key matching.
- If both recognized containers are supplied, reject ambiguous ownership even
  if their contents look equivalent; do not merge or pick one silently.
- Reject wrong types, duplicate scenario IDs within the supplied identity
  scope, malformed entries and dangling observability scenario references.
- Zero extracted scenarios MUST NOT be reported as successful consumption of
  a recognized nonempty alternate container.

An explicit migration preview MAY convert the known legacy shape containing
one scalar string each for `given`, `when`, `then` into three prefixed steps.
It MUST preserve IDs, exact clause strings and order, emit before/after counts,
source digests, mapping and unsupported fields, and leave source files intact.
Ambiguous or richer inputs require review rather than guessed conversion.
Applying the preview is a separate authorized source change, followed by the
same loader checks; extraction success does not resolve source review gates.

Diagnostic commands may emit a partial inventory with findings and a failure
status. An implementation handoff MUST fail closed on invalid scenario input.
Existing CLI distinctions remain: input/contract error is not an emitted
`blocked` preview, and a `blocked` preview is not readiness. Exit codes and
artifact statuses must be documented and checked at each integration boundary.

### 3. Scenario identity and evidence binding

Scenario IDs identify examples, not Requirement or acceptance-criterion
subjects. They MUST NOT be derived from titles, line numbers, array positions,
test discovery order or a Gherkin parser's transient AST IDs.

Existing Zeusus IDs remain unchanged. For cross-node exchange, a workspace
identity and scenario ID provide a qualified declaration address; uniqueness
is checked within the supplied workspace snapshot. The owning spec is explicit
membership/provenance. Moving a scenario between specs requires a reviewed
mapping, rather than silently granting the same evidence to a new owner.
A partial snapshot must declare its scope and cannot claim workspace-wide
uniqueness or complete references.

Pinned observations MUST carry the containing source revision/digest, native
scenario ID, selected profile/version and normalized scenario digest. Renaming
a title preserves identity; changes to source or scenario content cannot
automatically transfer an old execution result to the new contract. Historical
results retain their original pins. Split, merge or replacement needs explicit
mapping; neither an import nor a matching title invents lineage or adoption.

Requirement/criterion references use the adopted 0221 contract where available.
This proposal does not create a canonical Scenario node kind, allocate new
requirement IDs, or extend 0221 subject semantics by implication.

### 4. Bounded Gherkin import/export

Gherkin is an exchange adapter around the shared model. Its grammar is defined
by [Cucumber's reference](https://cucumber.io/docs/gherkin/reference/), and the
official [Gherkin project](https://github.com/cucumber/gherkin) provides parser
implementations. The adapter should use a pinned parser/AST rather than a
regular-expression approximation of the complete language.

The first proposed adapter profile, `gherkin_basic_v1`, supports one English
Feature, ordinary Scenario/Example declarations, titles and ordered plain
Given/When/Then/And/But steps. Explicit IDs are transported through reserved
scenario tags, provisionally `@specgraph-id=EXAMPLE-HISTORY-001`; the spec and
workspace binding are supplied in the exchange manifest. IDs not representable
by the selected tag profile produce a finding, not a rewritten identity.

For example, the native declaration above could be exchanged as follows. This
is a proposed mapping, not an implemented export:

```gherkin
Feature: History operation expiry

  @specgraph-id=EXAMPLE-HISTORY-001
  Scenario: Expired operation cannot restore a building
    Given a retained demolition operation whose deadline has been reached
    When undo is requested at the command boundary
    Then the operation is unavailable and the live world is unchanged
```

Import MUST reject a missing or duplicate reserved scenario ID, a conflicting
binding, malformed grammar or unsupported construct. Creating a fresh ID is
a separate authorized authoring action. Export MUST reject native steps that
cannot be represented under the selected grammar profile. A native scenario
without a title remains loadable but is not exportable by this first adapter;
it must not gain a source title merely to satisfy an exchange round-trip.
Arbitrary native step strings remain valid native input; they do not imply
Gherkin exportability.

| Construct | First adapter profile |
| --- | --- |
| Feature and Scenario/Example | Supported with explicit bindings |
| Plain Given/When/Then/And/But | Supported; preserve keyword, text and order |
| Descriptions, comments, ordinary tags | Retain in exchange source metadata; never treat as evidence |
| Background, Rule, `*`, non-English dialect | Explicit unsupported finding |
| Scenario Outline/Examples, data tables, doc strings | Explicit unsupported finding |

Unsupported constructs cannot be flattened, skipped or accidentally counted
as successful imported scenarios. Their later support requires a richer
versioned model and explicit compatibility fixtures. Metadata that cannot be
retained/exported must be surfaced as loss before writing output.

For supported inputs, native -> Gherkin -> native and Gherkin -> native ->
Gherkin MUST preserve qualified IDs, titles, step keywords/text/order and
retained metadata. Round-trip equivalence is structural, not byte-for-byte
formatting identity. The original bytes and digest remain provenance. Exchange
outputs are review-only candidates; import does not activate canonical specs.

### 5. Execution and ownership boundaries

The evidence chain stays explicit:

```text
authored scenario -> validated scenario contract -> execution binding
  -> observed test/run result -> existing evidence admission policy
```

Parsing or export does not prove behavior. A title is descriptive and cannot
override steps; the pilot's misleading redo title demonstrates the need for
semantic review even when structure and original steps remain unchanged.
Unbound, skipped, pending, failed and passed executions remain distinct.
A native Swift Testing adapter is possible without requiring Cucumber as the
test runner. Step binding and runtime storage are follow-up concerns.

SpecGraph owns the scenario model, profile validation, migration/exchange
provenance and references. Product repositories own scenario behavior,
implementation bindings and tests. SpecificationCore remains the policy
materialization layer for branching/classification in Zeusus; this proposal
does not replace it with step text. SpecSpace consumes documented read models
and displays profile/findings; it does not infer readiness from a count.
FeaturePassport receives generic pinned producer evidence through existing
adapters; no FeaturePassport -> depends_on -> SpecGraph dependency is introduced.
Issuer trust, receipt storage and admission remain owned by existing contracts.

## Bounded Realization Plan

1. Prepare one graph-owned contract and shared native model/loader; characterize
   current 0047 behavior, reproduce the alternate-container failure and audit
   legacy fields/IDs. Wire the same checks into authoring and extraction. Keep
   rollout explicit and obtain review for activation/default changes.
2. Add deterministic migration previews and rerun the six-node Zeusus package.
   Preserve all 100 IDs and existing review/observability blockers.
3. Implement `gherkin_basic_v1` and structural round-trip fixtures using a
   pinned parser. Record parser/profile/source provenance and unsupported cases.
4. Separately propose execution bindings, richer grammar support or viewer
   features when demanded by pilot observations.

New domain policy should use typed composition and named SpecificationCore
rules where decisions branch. Parsing, file reads and artifact writes stay at
I/O boundaries; constructors/imports stay inert. No language migration or full
supervisor rewrite is required by this proposal.

## Proposed Acceptance Cases

These are future implementation checks, not tests executed by this PR.

| ID | Given / When / Then obligation |
| --- | --- |
| BDD-01 | Given recognized nonempty legacy `scenarios`, when strict extraction runs, then a typed incompatibility finding replaces the false empty success. |
| BDD-02 | Given the curated six-spec pilot, when an approved migration is applied, then 100 unique IDs and exact clause order survive; independent source gates still block handoff. |
| BDD-03 | Given absent, empty, malformed and mixed containers, when all shared consumers validate, then presence and findings agree. |
| BDD-04 | Given duplicate IDs, repeated steps and dangling references, when loading, then duplicates/references fail and repeated ordered steps survive. |
| BDD-05 | Given supported native and Gherkin fixtures with IDs, when exchanged both ways, then identity/title/step/metadata equivalence holds. |
| BDD-06 | Given malformed grammar, missing IDs, unsupported features or unexportable steps, when exchanging, then no success or partial canonical adoption is emitted. |
| BDD-07 | Given a title edit, semantic edit, move, split or merge, when binding historical evidence, then identity and pinned content/membership are handled separately without automatic evidence transfer. |
| BDD-08 | Given parse success and an unbound/skipped/pending/failed run, when projecting readiness, then it is not reported as executed-and-passed or admitted. |
| BDD-09 | Given the same pinned input and profiles, when adapters repeat, then normalized results/findings are deterministic; diagnostics do not mutate source. |

## Proposal Validation and Remaining Decisions

Required document checks: `make proposal-tracking-gate`, `make docc-sync`,
JSON parsing and local Markdown-link verification. These establish proposal
tracking/document coherence only; they do not validate the future scenario
implementation, Gherkin exchange or gameplay.

Before implementation activation, finalize the v1 field allowlist/extension
policy, profile selection location and reserved tag spelling with fixtures.
Select and pin the parser after the dependency/license check. Full Gherkin
coverage, a universal execution DSL, mandatory Cucumber, source migration and
canonical Scenario ontology are outside this preparation slice.
