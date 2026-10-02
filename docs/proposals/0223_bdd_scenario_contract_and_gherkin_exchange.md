# 0223 BDD Scenario Contract and Gherkin Exchange

RFC: SG-RFC-0223
Version: 0.1.3

## Status

Draft proposal; contract preparation only. Runtime realization is deferred
until the bounded contract is reviewed and adopted through the existing graph
process. Preparation records the proposal, historical pilot observations and
current compatibility tests; it
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
- [Independent Astra review and clarification record](../reviews/0223_astra_review_followup.md)
- [Native contract preparation and compatibility evidence](../reviews/0223_native_bdd_contract_preparation.md)
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

### Current bounded preparation

After PR #753 merged, one targeted Supervisor pass on GPT 6 Luna Medium prepared
a temporary native contract candidate under proposed parent **SG-SPEC-0062**.
The curated copy stays outside canonical `specs/nodes`, with five criteria,
eleven future BDD cases and `review_pending`. No canonical ID is allocated.

The candidate proposes an allowlist of `id`, `scenario`, `steps`, with unknown
fields rejected and no v1 extension field. It names six SpecificationCore policy
objects, including `BDDContainerPresenceSpec`, with RFC rule references and
read-only observability. These are proposed bindings, not implemented objects or
canonical subject identities. The field policy still needs explicit adoption.

`make test-native-bdd-characterization` passed **71 current compatibility tests**.
The bounded corpus audit pins 69 canonical SpecGraph files and six normalized
Zeusus files containing 100 scenarios; all inspected scenario fields match the
proposed allowlist. This is not a full ecosystem audit or strict-profile
conformance. The [preparation record](../reviews/0223_native_bdd_contract_preparation.md)
retains raw/curated candidates, hashes and the runtime diagnostic caveat.

Normalized digest bytes, source migration, exchange implementation and activation
remain separate review prerequisites. The original fourteen proposal acceptance
cases remain future cases; the candidate's eleven native cases refine one slice.

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
`scenario` is an optional human title for backward compatibility; new authoring
SHOULD supply a nonempty title. A missing title may be displayed as the ID without
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

The proposed activated profile has the following explicit matrix. These are
future shared-profile outcomes, not changes to the current 0047 implementation.
YAML mapping keys MUST be checked for duplicates before constructing ordinary
maps; a last-key-wins parse cannot be repaired by later scenario validation.
This preserves the existing 0047 `UniqueKeyLoader` guard.

| Authored input | Presence | Loader outcome |
| --- | --- | --- |
| Neither recognized container is supplied | `absent` | Valid absence; readiness is evaluated separately |
| Only `bdd_scenarios: []` | `explicit_empty` | Valid explicit zero; no behavior coverage implied |
| Only a nonempty `bdd_scenarios` list of valid entries | `present` | Preserve IDs and exact ordered steps |
| `bdd_scenarios: null`, scalar, boolean or mapping | `invalid` | Container-type finding; do not coerce to `[]` |
| Only `scenarios: []` | `invalid` | Unsupported-container finding, even though empty |
| Only `scenarios`, with any other value | `invalid` | Unsupported-container finding; inspect clauses only in an explicit migration preview |
| Both recognized containers, including two empty lists | `invalid` | Ambiguous-container finding; neither takes precedence |
| Repeated YAML mapping key anywhere in the input, including `steps` or a container | `invalid` | Duplicate-key finding before mapping construction |
| Null/non-mapping entry, missing ID/steps, or empty steps list | `invalid` | Entry/field finding; do not skip the entry |
| ID, step or supplied title is non-string, empty or whitespace-only | `invalid` | Value finding; do not invent a replacement |
| Repeated ID in the supplied identity scope | `invalid` | Duplicate-ID finding |
| Repeated nonempty step strings in a valid list | `present` | Valid; preserve repetition and order |

Known alternate keys explicitly declared by the profile follow the same
unsupported/ambiguous rules as `scenarios`. Whitespace is used only to reject
empty string content, not to trim valid values or collapse distinct IDs. An
invalid input has no successful extracted count; a diagnostic partial count
must be labeled separately and cannot be an implementation handoff. The corpus
audit must include the empty legacy cases and record any migration requirement
before activation. The matrix does not authorize a default/profile change.

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
Applying the preview is a separate authorized source change. Before any source
write, application MUST bind that authorization to the exact reviewed preview
and match every input's workspace/path binding, exact source-byte digest and
source revision when pinned. Re-read the current source at the serialized
mutation boundary; a mismatch emits a `stale-preview` finding and performs no
source writes. An obsolete authorization cannot be silently reused for a new
preview; regenerate and review that preview separately.

The precondition check and publication MUST be protected against concurrent
source changes: a source edited after the check cannot be overwritten by the
old candidate. Validate the staged candidate with the same loader before
publication and retain the checked source pins in the application record.
Extraction success still does not resolve source review gates. These are
requirements for the future migration writer, not a claim about current tooling.

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
identity MUST be immutable and distinct from its mutable slug, display name,
filesystem path or hosting URL. Missing identity requires an explicit binding
decision; the adapter MUST NOT derive an identity from a directory name or
silently allocate one. An identity supplied by an exchange manifest must agree
with the selected workspace binding. Renaming or moving the workspace does not
change the qualified scenario identity.

This workspace identity and scenario ID provide a qualified declaration address;
uniqueness is checked within the supplied workspace snapshot. The owning spec is explicit
membership/provenance. Moving a scenario between specs requires a reviewed
mapping, rather than silently granting the same evidence to a new owner.
A partial snapshot must declare its scope and cannot claim workspace-wide
uniqueness or complete references.

The 0047 observability reference scope remains the owning node:
`observability.obligations[*].scenario_ids` MUST resolve against that node's
`specification.bdd_scenarios`. A scenario found only in a sibling, parent or
another workspace does not satisfy the reference. Workspace-wide uniqueness
checks and node-local reference resolution are separate checks. Equal local IDs
in distinct workspaces are distinct qualified identities; duplicate active IDs
in one supplied workspace snapshot require a finding. No cross-node or inherited
reference syntax is introduced by this proposal.

Pinned observations MUST carry the containing source revision/digest, native
scenario ID, selected profile/version and normalized scenario digest. Renaming
a title preserves identity; changes to source or scenario content cannot
automatically transfer an old execution result to the new contract. Historical
results retain their original pins. Split, merge or replacement needs explicit
mapping; neither an import nor a matching title invents lineage or adoption.

The normalized scenario digest needs a separately reviewed, versioned canonical
byte contract before shared-profile activation or evidence handoff uses that
digest. Finalize all of the following together, with pinned fixtures:

- Included/excluded fields: ID, optional title, ordered steps, qualified
  workspace/spec binding and exchange metadata each need an explicit decision.
- Canonical serialization and encoding, including key order, absent versus null
  values, and preservation of list order and repeated steps.
- Text/Unicode handling consistent with this profile's exact ID and step-value
  preservation; normalization cannot silently rewrite authored content.
- Hash algorithm, digest-contract version and domain separation from source-file
  or exchange-payload hashes.
- Cross-adapter fixtures for equivalent supported native/Gherkin projections,
  plus content changes that must yield different digests.

Consumers MUST record the selected digest-contract version and reject an unknown
or unresolved contract instead of generating implementation-private pins. Until
the canonical contract is reviewed, normalized digest binding remains unavailable;
exact byte SHA-256 pins still describe sources/payloads, not normalized scenario
equivalence. Existing historical pins keep their original contract and are not
silently recomputed. This proposal deliberately makes the canonical byte choice
an activation prerequisite rather than selecting an untested serializer here.

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

Exactly one reserved ID tag MUST be authored directly on each Scenario/Example
declaration. Two reserved tags are invalid whether their values agree or differ.
A reserved ID tag on Feature is invalid even if each scenario also supplies one;
Feature tags cannot provide inherited scenario identity. Missing/empty values
and conflicting envelope IDs also fail. Ordinary tags retain their authored
Feature or Scenario scope, order and multiplicity; the adapter does not flatten
them into an inherited list. Text resembling a tag inside a comment is not a
tag declaration.

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

#### Exchange envelope and round-trip scope

The lossless exchange unit is a native/Gherkin artifact plus a versioned
`bdd_scenario_exchange_envelope`. Metadata is not injected into the minimal
native scenario fields. A first import without an envelope needs an explicit
workspace/spec binding and creates a new envelope from the actual source;
it does not claim to recover earlier metadata or provenance.

The proposed envelope carries these dimensions. Serialized key names and the
strict allowlist require schema fixtures before activation.

| Dimension | Required contract |
| --- | --- |
| Kind/version/profile | `bdd_scenario_exchange_envelope`, schema version 1 and the selected adapter/native profile versions |
| Binding | Immutable workspace identity and owning spec; agreement with the selected snapshot and payload IDs |
| Payload | Native YAML or Gherkin format and the exact current payload SHA-256; verify before consuming metadata |
| Origin provenance | Original format/digest, source revision when available, recorded parser implementation/version and dialect for Gherkin; do not overwrite original pins with emitted-file positions |
| Feature metadata | Nonempty name, description (possibly empty) and ordered directly authored ordinary tags |
| Scenario metadata | Entries keyed by stable scenario ID, description (possibly empty), Scenario/Example declaration keyword and ordered directly authored ordinary tags; title agrees with the native declaration |
| File comments | Ordered text occurrences, including duplicates, with original parser locations retained as provenance; no inferred scenario ownership |

For a Gherkin payload, envelope metadata MUST agree with the actual parsed
projection: scenario IDs, titles, steps and supported declarations/tags/
descriptions, plus comment text/order. For a native payload, validate the
representable fields against that payload and validate retained exchange-only
metadata under the envelope schema; it cannot be claimed independently verified
from native fields that do not carry it. A matching payload digest alone is
insufficient if representable fields conflict. Stale digests, missing binding,
duplicate metadata IDs, unknown profile versions or conflicting metadata produce
findings before successful output. Envelope validity is not a trusted receipt
or evidence admission.

Comments are a file-level sequence. The official
[Gherkin AST builder](https://github.com/cucumber/gherkin/blob/main/python/src/gherkin/ast_builder.py)
collects comments separately with locations; proximity to a scenario does not
establish membership. The adapter preserves parsed comment text and source
order. Original locations identify the original bytes for diagnosis, not
logical IDs or export positions. The first exporter uses one deterministic
comment block before Feature, retaining that sequence; updated emitted locations
are derived. No attachment of a comment to a Scenario is inferred by this policy.

For supported exchange packages, native -> Gherkin -> native and Gherkin ->
native -> Gherkin MUST preserve qualified IDs, titles, exact native step strings,
parsed step keywords/text/order, declaration metadata and comment text/order.
If a native value cannot survive the pinned grammar projection unchanged, export
fails explicitly rather than trimming/rewording it. Round-trip comparison excludes
formatting, emitted digests/parser locations and transient AST IDs. Original
provenance stays retained in the accompanying envelope; it is not compared to
the newly emitted file as if both were the same source revision. Without the
envelope, retention of that historical provenance is not promised. Outputs are
review-only candidates; import does not activate canonical specs.

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
| BDD-03 | Given every native input-matrix row, including null, empty legacy/both containers, whitespace-only values and duplicate YAML keys, when all shared consumers validate, then presence/findings agree and no last-key-wins map reaches policy validation. |
| BDD-04 | Given duplicate IDs, repeated steps and dangling references, when loading, then duplicates/references fail and repeated ordered steps survive. |
| BDD-05 | Given supported native/Gherkin packages and an envelope with Feature/Scenario metadata, repeated ordinary tags and comments between scenarios, when exchanged both ways, then identity/title/step/scoped-metadata/comment-order equivalence holds while original locations remain provenance. |
| BDD-06 | Given malformed grammar, missing IDs, unsupported features or unexportable steps, when exchanging, then no success or partial canonical adoption is emitted. |
| BDD-07 | Given a title edit, semantic edit, move, split or merge, when binding historical evidence, then identity and pinned content/membership are handled separately without automatic evidence transfer. |
| BDD-08 | Given parse success and an unbound/skipped/pending/failed run, when projecting readiness, then it is not reported as executed-and-passed or admitted. |
| BDD-09 | Given the same pinned input and profiles, when adapters repeat, then normalized results/findings are deterministic; diagnostics do not mutate source. |
| BDD-10 | Given equal local IDs in different immutable workspaces, a renamed workspace, and a scenario found only outside an obligation's owning node, when resolving, then distinct workspace identities remain distinct, the rename preserves identity and the cross-node reference fails. |
| BDD-11 | Given zero/one/two reserved Scenario ID tags, a Feature-level reserved ID, or an envelope/tag mismatch, when importing, then only exactly one direct matching Scenario ID is accepted and no identity is inherited or invented. |
| BDD-12 | Given a stale envelope digest or conflicting metadata despite a matching digest, when exchanging, then a finding prevents successful output; comments cannot acquire inferred Scenario ownership. |
| BDD-13 | Given a reviewed migration preview and a changed source, binding or pinned revision, when application is attempted, then `stale-preview` prevents all source writes; a concurrent edit cannot be overwritten by an old candidate. |
| BDD-14 | Given an unresolved or unknown canonical digest contract, when normalized scenario pins are requested, then binding fails explicitly; after review, pinned equivalent native/Gherkin fixtures agree across consumers and semantic changes follow the declared field/text policy. |

## Proposal Validation and Remaining Decisions

Required document checks: `make proposal-tracking-gate`, `make docc-sync`,
JSON parsing and local Markdown-link verification. These establish proposal
tracking/document coherence only; they do not validate the future scenario
implementation, Gherkin exchange or gameplay.

Before implementation activation, finalize the v1 field allowlist/extension
policy, profile selection location, reserved tag spelling and the versioned
canonical scenario-digest byte contract with fixtures. The digest decisions in
section 3 are required activation gates, not optional implementation details.
Select and pin the parser after the dependency/license check. Full Gherkin
coverage, a universal execution DSL, mandatory Cucumber, source migration and
canonical Scenario ontology are outside this preparation slice.
