# Source: composition and observation contract

Captured from the operator discussion on 2026-09-19/20 and the Hypercode working
source draft. This source is discussion evidence, not accepted architecture.
The operator authorized small Hypercode RFC/documentation changes and a SpecGraph
proposal; a separate Clojure application and UML Viewer experiment are deferred.

Hypercode source: `DOCS/uml-viewer-specgraph-integration-source-draft.md`.
Hypercode source revision: `0661903e94c8e3d0ea47cf9971fe4911cebace9c`.
Relative source links below are pinned to that documentation revision.
The archived source is a snapshot; the proposal owns its bounded decision scope.

---

# Hypercode, UML Viewer, and SpecGraph: Composition, Generation, and Implementation Verification

> **Status:** Temporary source draft for subsequent proposal preparation and decomposition. This is a structured discussion, not an approved specification, proposal, or description of an integration that has already been implemented. The first proposal extracted from it is [SG-RFC-0219](https://github.com/0al-spec/SpecGraph/blob/main/docs/proposals/0219_composition_observation_contract.md). No IDs have been assigned to the other topics.
>
> **Sources:** ChatGPT conversation “UML Hypercode Transpilation” from 2026-09-19 and the follow-up discussion with the Hypercode author on 2026-09-20 about composition, directionality, the external generation contract, and quality policies. Source projects: [UML Viewer](https://github.com/unclebob/uml-viewer), [Hypercode](https://github.com/0al-spec/Hypercode).
>
> The Hypercode author's clarifications guide this draft. Implementation options, comparison schema, quality-policy cascade, and MVP below remain proposals for investigation. The current grammar, IR, and tool capabilities have not been audited here.

## Core idea after clarification

Hypercode should preserve a constrained declarative architecture model: composition
and hierarchy, reading from whole to details, and directed provision of data and
dependencies. These constraints are part of the language's intent and the author's
vision of Elegant Objects. The ability to express additional information through
HCS alone is not a reason to add arbitrary architectural relations.

The intended integration enables generation and verification of an implementation
of that model:

- **Hypercode** defines program composition and structure.
- An **external generation contract** defines how to realize that structure on a
  specific platform. An LLM agent's system prompt could be its first form.
- **Quality policies** define quality requirements and check conditions; their
  location and relationship to HCS have not been chosen.
- **Scanners and measurement tools** extract code facts and measurements with
  provenance.
- **SpecGraph** could map an implementation to Hypercode structure, the external
  contract, and quality policies, and explain results through evidence.
- **UML Viewer** could serve as a visual consumer and an external format for a
  constrained adapter, without defining Hypercode's expressive capabilities.

```text
.hc / applicable .hcs ──► Desired composition ─────┐
                                                   │
External generation contract ──────────────────────┤
                                                   ├─► SpecGraph
Quality policies ──────────────────────────────────┤   compare / explain
                                                   │
Code ──► scanners ──► Observed Graph ──────────────┤
Checks and measurements ──► evidence / metrics ────┘
```

The **Desired Graph ↔ Observed Graph** formulation remains, but it does not mean
that two arbitrary graphs must be equal. The Desired Graph may be a composition
tree. The Observed Graph may contain richer relations needed to analyze actual
code, without transferring those relations into the Hypercode language.

## Clarification after repository review

Hypercode already defines consumer-owned adapters and an IR boundary
([Backends.md](https://github.com/0al-spec/Hypercode/blob/0661903e94c8e3d0ea47cf9971fe4911cebace9c/DOCS/Backends.md)), and HCS property contracts already accumulate by intersection and only narrow
([Usage.md](https://github.com/0al-spec/Hypercode/blob/0661903e94c8e3d0ea47cf9971fe4911cebace9c/DOCS/Usage.md#2-guardrails-contracts-as-a-ci-gate)). The proposed quality-policy cascade below does not replace those rules: applying measurements and code-level checks requires a separate consumer contract. The [codegen demo](https://github.com/0al-spec/Hypercode/blob/0661903e94c8e3d0ea47cf9971fe4911cebace9c/Examples/codegen-demo/README.md) already illustrates generation and freshness/CONFIG checks, but not arbitrary architecture comparison.

The main comparison contract belongs in SpecGraph; Hypercode only receives a
clarification of composition principles and consumer responsibilities. The
external generation contract could initially live alongside the application. A
possible later experiment is a separate Clojure repository to evaluate a scanner
and UML Viewer output. Creating it and checking its compatibility have been
deferred and are outside the current changes. Reusable metric packs belong to
Metrics, thresholds to an explicitly selected application policy, and their
evaluation to the checking consumer.

## 1. From EDN transpilation to preserving the Hypercode model

The original idea came from a UML Viewer EDN example: packages, classes, fields,
operations, typed edges, namespace identity, and metric overlays. The initial
hypothesis was to transfer this structure losslessly into Hypercode and export it
back to EDN.

After discussion, that hypothesis was no longer a requirement. A complete EDN
round-trip could force Hypercode to express inheritance, associations, and other
relations the author deliberately does not want in the architecture model.

The revised sequence is to define the permitted Hypercode composition model first,
then investigate mappings to external representations. A constrained adapter must
describe its supported subset and how it handles unsupported elements. Relations
must not be silently lost, and a complete round-trip must not be claimed based on
one subset.

The original discussion considered this path:

```text
.hc + .hcs → resolved graph → canonical IR → adapter → target
```

This is a direction for investigation. Its correspondence to current Hypercode
code and schemas must be checked before an implementation proposal. Even if the
internal IR can store arbitrary relations, that does not mean they should become
permitted constructs in the authoring language.

## 2. Hypercode author's architectural intent

The discussion formulated four related principles:

| Principle | Intended meaning |
|---|---|
| Users read top-down | A description unfolds the whole through its constituent parts |
| A program initializes from App to Button | The root organizes construction of the nested composition |
| Data enters through the root | External inputs belong to the system boundary and are routed inward |
| The larger depends on the smaller, not vice versa | A composite uses its parts; a part should not know the structure of the whole that contains it |

Illustration of structure, not `.hc` syntax:

```text
App
└── Screen
    └── Form
        └── Button
```

Desired properties are declarativity, cascading structure, linear reading, and
local comprehensibility. Understanding a part should not require reconstructing an
arbitrary network of relations across the application.

Inheritance and arbitrary interweaving of entities are not goals for expanding
Hypercode. Nearly imperative scenarios and manually described temporal coupling
should not be introduced just to achieve compatibility with an external format.

However, construction order and temporal coupling should be distinguished. A
runtime may derive assembly order from declarative composition. A separate problem
is a hidden obligation for a component's user to call `prepare → attach → start`
in the right order. Specific constraints of this kind may belong in the external
generation contract.

These principles do not yet formally define what counts as a dependency, or how
shared dependencies, reuse, asynchrony, and lifecycle work. “From App to Button”
expresses the direction of assembly organization; it does not assert that a
platform-specific constructor-call order has already been selected.

## 3. External input, routing, and results

The UIKit discussion clarified what it means for input to enter through the root.
A touch does not arrive at a Button as an independent external input: hit-testing
starts at the root of the view hierarchy, usually `UIWindow`, and identifies its
recipient through nested views. This is an example of runtime-organized routing.
See [Apple: Delivering touch events](https://developer.apple.com/library/archive/qa/qa2013/qa1812.html).

Further handling uses several mechanisms. Unhandled touch events may travel along
the responder chain; a `UIControl` action is delivered through target–action, and
when its target is `nil`, a handler is searched for through the responder chain.
This is not a required reverse traversal of the same tree for every tap. See
[Apple: UIResponder](https://developer.apple.com/documentation/uikit/uiresponder)
and [Target–action](https://developer.apple.com/documentation/uikit/responding-to-control-based-events-using-target-action).

Architectural direction:

```text
External input
    → system boundary / runtime
    → routing through composition
    → component handling
    → result through the component contract
```

Returning a result does not itself require knowledge of a specific parent. One
analogy is a function returning a value to its caller without knowing the caller's
implementation. For events, the concrete mechanism should be defined by the
generator contract.

The platform runtime may own the routing root. This does not require manually
describing dispatch for every event inside App or moving the responder chain,
callbacks, and target–action into `.hc`.

## 4. External generation contract

Details for realizing composition may live outside Hypercode. For example, an
agent's system prompt for generating code from `.hc` could say:

> Assemble components through top-down composition. Provide dependencies during
> construction. A child component must not know its parent's concrete type. Connect
> external inputs through platform mechanisms. Return results through the
> component contract. Avoid required multi-step setup protocols when readiness
> can be guaranteed during construction.

This illustrates a possible contract; it is not an accepted platform profile.
Specific event-delivery mechanisms, lifecycle, state management, and restrictions
on inheritance in generated code require separate decisions. The absence of
inheritance in the architecture language does not automatically prohibit all
platform subclassing, such as UIKit subclassing.

```text
.hc + applicable .hcs + external generation contract
                         ↓
                    LLM generator
                         ↓
                    source code
```

A prompt guides generation but does not guarantee compliance. Important
requirements need review, scanner checks, tests, or runtime evidence. Rules stated
only in natural language must not be presented as mechanically verified
contracts.

For traceability, it is useful to link generated output to the Hypercode source
revision and external-contract version. The contract need not live in `.hc`; its
location, format, versions, and the precedence of multiple contracts remain to be
designed.

## 5. Desired composition and Observed Graph have different roles

Hypercode defines authorial intent. A scanner records what it detects in an
implementation. Neither source should automatically replace the other.

An Observed Graph may contain inheritance, calls, references, imports, cycles, and
other relations if the scanner can extract them. This is a vocabulary of
observations, not a list of new Hypercode constructs.

For example, a scanner detects a reference from Button to a concrete Form. This
does not require adding that relation to `.hc`. SpecGraph can compare the
observation with an external rule requiring a child component to remain
independent of its concrete parent.

An additional relation is not always a violation. First determine its semantics,
architectural significance, and applicable rule. Platform details may be
permitted by the generator contract.

Comparison should answer these questions:

- Are the expected components and composition implemented?
- Which observations support conformance to the selected rules?
- Which relations violate a specific contract or policy?
- Is there enough data to make each claim?

Projecting the Observed Graph onto a tree must not silently discard remaining
relations; otherwise the check could hide precisely the unwanted entanglement. The
relations should be retained as observations, and the outcome of reviewing them or
the limits of that review should be explicit.

## 6. Identity, provenance, and explaining results

A common schema has not been agreed. Identity and mapping must be compatible, but a
single universal vocabulary of relations is not necessarily required.

Each data type should retain its own basis:

| Data | Required traceability |
|---|---|
| Desired component / composition | Identity, source in `.hc` or applicable `.hcs`, revision |
| Generation rule | External-contract source and version, identifiable rule |
| Quality requirement | Policy source, scope, version |
| Observed entity / relation | Code source, source span if available, revision, scanner and version |
| Check result | Applied rule, mapping, evidence, and check limitations |

A display label should not automatically be treated as identity. Namespaces,
aliases, ambiguity, and cases where one component corresponds to multiple code
entities need a separate contract. The `:ns` rule mentioned in the original UML
Viewer example should be considered when developing the adapter, without
automatically turning it into a universal Hypercode identity rule.

Example explanation, not a data schema:

```text
.hc structure:
  Form contains Button

External generation contract:
  a child component does not depend on its parent's concrete type

Observation:
  Button stores a reference typed as Form
  evidence: Button.swift:47, revision R, scanner S

Result:
  violation of the external-contract rule
  scope: Button component from .hc
```

“Not detected” does not mean “absent.” A check must account for scanner coverage
and allow an `unknown` / “insufficient evidence” state. Static scanning alone does
not prove initialization order, delivery of all runtime events, or program
correctness.

## 7. Metrics and quality policies

Metrics remain a separate layer of observations: coverage, CRAP, cyclomatic
complexity, mutation testing, and other measurements. They are neither composition
structure nor automatically requirements on that structure.

Distinguish:

```text
Structure:     Form consists of Button
Policy:        a mutation-score threshold applies to the selected scope
Observation:   tool T measured value M on revision R
Check result:  value evaluated against policy P with scope and completeness considered
```

A measurement needs a source, revision or timestamp, tool version, units,
applicable scope, and completeness information. A measured value must not be
recorded as an authored requirement or moved into an overlay without provenance.

**Cascading quality policies through a composition tree is a possible future
direction, not an accepted decision.** The root could define baseline requirements
that nested scopes inherit and refine. It remains necessary to decide whether
parent requirements may be weakened, how exceptions are expressed, and how
conflicts are resolved.

Cascading requirements does not define how measurements are aggregated. For
example, a parent's coverage cannot generally be computed as a simple average of
its children's percentages; the underlying numerators, denominators, and scope
overlap must be considered.

Storing policies outside Hypercode, in HCS, or in a separate overlay needs
investigation. Do not expand `.hc` with metric details in advance. Quality gates
and their authority also require a separate contract.

## 8. UML Viewer and Clojure roles

UML Viewer could be used independently in several roles:

1. A **visual consumer** of Hypercode composition.
2. A **constrained adapter** for an explicitly selected EDN subset.
3. A **review surface** for desired structure, observed facts, and check results.
4. A **source of scanner observations and metric overlays**, if actual contracts
   and licensing permit this use.

None of these roles requires transferring full UML semantics into Hypercode.
Displaying two states and their diff remains an integration hypothesis, not a
confirmed capability of an existing adapter.

Clojure is conceptually close to some of the intent: functional programming,
immutable data, and polymorphism without implementation inheritance in its own
type model. However, the viewer's implementation language does not guarantee a
linear architecture, absence of temporal coupling, or conformance to Hypercode
constraints. UML Viewer itself describes namespaces and dependencies between
them. See [Clojure: Functional Programming](https://clojure.org/about/functional_programming),
[Runtime Polymorphism](https://clojure.org/about/runtime_polymorphism), and the
[UML Viewer README](https://github.com/unclebob/uml-viewer).

Inheriting UML Viewer semantics through an adapter is not a goal. Before
implementation, the current EDN schema, scanner pipeline, UI, licensing, and
format stability still need to be audited.

## 9. Possible feedback loop

The longer-term goal is code generation or repair with verification against
explicitly identified grounds:

```text
Hypercode + external generation contract
                  ↓
             generation / patch
                  ↓
                 code
                  ↓
        scan + tests + measurements
                  ↓
     SpecGraph: structure + rules + policies
                  ↓
       explainable results → review
                  ↓
       bounded agent task, if authorized
```

The agent receives a localized issue, the affected composition scope, the
applicable rule, and evidence. Necessary checks run again after a change.

Failure to find violations is not proof of correctness. Results should show
coverage, unchecked requirements, and the revision used. Agent authority, gates,
and completion criteria are not approved here.

## Possible decomposition into future proposals

These are topics for investigation and proposal shaping; no IDs are reserved:

1. **Hypercode composition-model boundary.** Compare the author's intent with the
   current grammar, HCS, and IR; define permitted structures without expanding the
   language for UML's sake.
2. **External generation contract.** Select one platform profile and describe its
   rules, versioning, and checkable subset; a system prompt may be the first form.
3. **Identity, mapping, and provenance.** Link authored composition, rules, and
   observations, including ambiguous correspondences.
4. **Observed graph ingestion.** Specify scanner capabilities, completeness, and
   retention of relations beyond the composition tree.
5. **SpecGraph checking.** Separate structural conformance, external-rule
   violations, and insufficient evidence.
6. **Composition adapter / viewer.** Check rendering of a selected subset without
   promising a complete EDN round-trip.
7. **Metric observations and quality policies.** Define scope, thresholds,
   possible cascading, exceptions, and aggregation separately from structure.
8. **Constrained agent feedback loop.** Once checkable contracts exist, define
   review, authority, and rechecking.

## Options for a first bounded MVP

The proposed first step is one composition example, one external contract, and one
implementation that can be checked. For example:

- a small `.hc` fixture with nested components;
- an external rule prohibiting a child component from depending on its parent's
  concrete type;
- two code fixtures: one conforming to the rule and one with an intentional
  violation;
- scanner observations and an explicit mapping to components;
- a result naming the rule, violation source, and check limitations;
- an incomplete observation as a separate case that must not produce a false
  conformance result.

This would check bounded comparison of structure and an external rule. LLM
generation could be connected as a separate experiment; it need not be part of
the first comparison-contract test. Such an MVP would not prove all four
architectural principles, full conformance, or scanner universality.

If the first goal is to investigate visual representation, an alternative MVP is
to export one composition to a supported EDN subset and inspect the rendering. It
would check the adapter and display, but not the scanner-to-SpecGraph loop. A
round-trip is possible only for a clearly defined subset.

Metrics, policy cascading, interactive editing, and automatic code repair should
not be combined with these steps into one MVP.

## Open questions and boundaries

- What can the current `.hc`, `.hcs`, and IR already express, and where do they
  differ from the author's clarified intent?
- Which hierarchy is authoritative: composition, ownership, construction, or
  namespace? Do not treat them as equivalent without a contract.
- What exactly counts as a part depending on its whole? How should shared
  services, callbacks, interfaces, and platform runtime be handled?
- How are input roots defined for multiple windows, background events, network
  input, and other platform boundaries?
- Which requirements belong to Hypercode, the generator, or quality policies?
  How are conflicts resolved?
- Which rules can be checked statically, which need runtime evidence, and which
  remain subject to review?
- How can composition be compared with code under ambiguous mapping and incomplete
  scans while preserving additional observations?
- Are cascading policies needed, may they be weakened, and where should
  exceptions live?
- Do not automatically transform observations into authoritative Hypercode
  source or present a prompt as enforcement.
- Do not treat this source draft as an accepted contract, implemented integration,
  or basis for assigning proposal IDs outside the normal intake process.

## Short formulation for later proposal intake

Investigate verifiable generation and analysis of programs where Hypercode defines
a constrained declarative composition and hierarchy, while an external contract
defines implementation details. SpecGraph could compare code with Hypercode
structure, generation rules, and quality policies while preserving identity,
provenance, and evidence boundaries. A richer Observed Graph does not
automatically expand Hypercode semantics. UML Viewer is considered as a consumer
and an adapter for a selected subset. The first bounded step should check one
comparison contract or one composition rendering; metrics, policy cascading, and
the agent feedback loop should be investigated separately.
