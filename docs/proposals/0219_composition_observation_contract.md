# Composition and Observation Comparison Contract

RFC: SG-RFC-0219
Version: 0.1.0

## Status

Draft proposal

This document defines a comparison contract only. Runtime realization is
**deferred_until_canonicalized**. The current slice registers the proposal,
source provenance, and review boundaries; it does not implement a comparator,
scanner, generator, quality gate, or viewer adapter. Registry markers demonstrate
contract tracking, not operational conformance.

## Source Material

- [Discussion source](../archive/proposal_sources/0219_composition_observation_contract.md)
- [Hypercode consumer boundary](https://github.com/0al-spec/Hypercode/blob/0661903e94c8e3d0ea47cf9971fe4911cebace9c/DOCS/Backends.md)
- [Hypercode RFC clarification](https://github.com/0al-spec/Hypercode/blob/0661903e94c8e3d0ea47cf9971fe4911cebace9c/RFC/Hypercode.md)

The operator wants Hypercode to retain composition and hierarchy, top-down
reading and assembly, root-controlled input, and parts independent of their
concrete containing whole. Implementation details may live in an external
system prompt for a code generator. A separate Clojure application is a possible
later pilot for UML Viewer output, not a prerequisite or deliverable here.

Related work to reuse rather than duplicate:

- [0037 Implementation Work](0037_implementation_work_layer.md): planning/handoff
  from specification to implementation, not automatic code mutation.
- [0018 Telemetry Evidence Plane](0018_telemetry_evidence_plane.md): observations
  remain evidence, not canonical intent.
- [0043 Metric Packs](0043_metric_pack_plugin_architecture.md) and
  [metric pack viewer contract](../metric_pack_viewer_contract.md): preserve
  metric provenance and distinguish diagnostic observations from policy authority.
- [0060 External Ontology Import](0060_external_ontology_import_plane.md): useful
  import/authority precedent, not a requirement to route composition through an
  ontology package or reuse historical IR-version assumptions.

## Problem and Bounded Decision

A lossless UML EDN import could force arbitrary relations into Hypercode merely
because a scanner or viewer can express them. Conversely, projecting code to a
composition tree could hide undesired dependencies. An IR diff alone cannot
establish architectural compliance, and a generation prompt is not enforcement.

Propose one consumer-side comparison boundary: SpecGraph can evaluate a desired
composition against versioned code observations and explicitly selected external
rules. Hypercode remains the producer of minimal structure and resolved context.
**Desired composition is not required to share the Observed Graph edge vocabulary.**

No Hypercode grammar/IR extension, canonical spec-node mutation, approval change,
or quality-threshold change is proposed by this slice.

## Responsibility Split

| Owner | Responsibility |
|---|---|
| Hypercode | `.hc` composition, `.hcs` resolution/property contracts, canonical IR, provenance |
| Application / generator | Versioned platform profile or prompt, implementation, scanner/test invocation |
| SpecGraph | Consumer mapping, comparison results, evidence and bounded follow-up planning |
| Metrics | Reusable metric methods and pack contracts; not application threshold authority |
| Application policy | Explicit rule/threshold selection and scope |
| Viewer adapter | Read-only composition/observation/result projection and evidence navigation |

An initial generator contract can reside in the application repository.
Hyperprompt may assemble prompt documents; SpecPM may later distribute reusable
packages; SpecNode may later execute jobs. None is a required dependency of this
comparison slice. Backend/EDN projection remains consumer-owned.

## Proposed Input Contract

These are conceptual records for review, not a released JSON schema or new
ontology vocabulary. Runtime realization must reconcile names and serialization
with the existing evidence and Implementation Work surfaces before publishing
an artifact kind.

| Input | Required information |
|---|---|
| Desired composition | Source revision/digest, IR version, resolved context, node identity, parent/child structure, available property provenance |
| Generation contract | Immutable version/digest, rule identity, rule source, scope, supported check method or explicit review-only status |
| Observations | Code revision/digest, scanner identity/version/configuration, scanned scope, supported relation kinds, completeness/limitations, entities/relations with source evidence |
| Mapping | Desired node to observed entity correspondence, producer/method, explicit ambiguity/unmapped state; support one-to-many where declared |
| Optional policy selection | Policy identity/version/source, selected scope and thresholds; separate from measured observations |

A display label is not sufficient identity. An IR node hash is an invalidation
signal, not a stable entity ID or proof that code implements the node. Provenance
must distinguish requirement, generation rule, observation, mapping, and result.
Input records must bind to the same declared comparison snapshot; cross-revision
inputs require explicit compatibility evidence or an unknown result.

External contracts and scanner payloads are data for the checker. Ingestion does
not execute embedded prompts, run tools, grant an agent authority, or turn code
observations into Hypercode source.

## Proposed Comparison Semantics

1. Validate snapshot coherence, supported formats, and input availability.
2. Establish mapping; retain ambiguity rather than guessing identity from labels.
3. Compare supported composition facts and explicitly selected generation rules.
4. Retain observations outside the tree projection and classify their disposition.
5. Emit evidence-linked results with coverage and limitations.

Existing HCS contracts accumulate by intersection and narrowing over resolved
properties. This proposal does not redefine that semantics or claim those checks
already validate code architecture. `hypercode diff` compares two resolved IR
snapshots, not desired architecture with code.

Rule examples for a future pilot may include a required component and a ban on a
child's dependency on its concrete parent. No blanket ban on every code-level
inheritance relation follows from the absence of inheritance in `.hc`: platform
mechanisms are interpreted against an explicitly selected generation contract.
Likewise, a returned result does not by itself prove a reverse dependency.

Top-down assembly and root-routed input are architectural intentions. A static
scanner cannot in general prove initialization order or all runtime delivery
paths. The contract must identify checks requiring runtime evidence or review.

### Result and Evidence Semantics

Proposed per-check outcomes:

- `satisfied`: the declared bounded check has sufficient supporting evidence;
- `violated`: sufficient evidence contradicts the applicable requirement/rule;
- `unknown`: incomplete scan, ambiguous mapping, unsupported check, stale inputs,
  or missing evidence prevents a decision.

Malformed input is an input-validation failure, never a successful comparison.
Each result names the requirement or rule source, affected desired node(s),
observation evidence, code revision, checker version, and limitations. A report
must also list unevaluated rules and unclassified relations. It must not collapse
an unknown check into success because no violations were found.

Evidence for one violation can remain decisive under an incomplete scan. A
universal absence claim requires sufficient declared scope and scanner capability;
absence from an incomplete observation set is not proof of absence from code.
A `satisfied` result is scoped to the supported predicate and snapshot, not a
claim of whole-program correctness.

Relations outside the desired tree are preserved, with disposition such as
checked, allowed by a cited rule, unknown, or out of scope. Out-of-scope relations
remain visible and are not evidence of satisfaction. A tree projection must not
silently discard contradictory facts.

Illustrative result, not a wire-format schema:

```text
Desired: Form contains Button                 [Hypercode source + revision]
Rule: child does not depend on concrete parent [generator profile + rule ID]
Observed: Button references concrete Form     [file/span + code revision]
Result: violated                              [mapping + checker evidence]
```

## Metrics and Quality Policies

Measurements remain separate observations with tool/version, snapshot, units,
scope, denominator where applicable, and gaps. Application-selected policies
supply thresholds; metric availability does not grant threshold authority.

A future cascade over composition requires an explicit consumer policy contract:
selection, narrowing or exceptions, conflict handling, and scope. It must not
silently weaken existing HCS property contracts. Cascading requirements does not
define aggregation; coverage percentages cannot simply be averaged without their
underlying counts and overlap rules.

Metric computation, thresholds, cascade realization, and gating are deferred from
the first comparison MVP. Existing metric packs remain diagnostic unless a
separately reviewed operational policy explicitly changes their use.

## Bounded Realization and Acceptance Plan

The next implementation slice should consume fixed fixtures before introducing
LLM generation, live scanning, UI, or agent execution. It should reuse existing
evidence/Implementation Work seams after checking actual producer semantics.

| Fixture / condition | Expected evidence |
|---|---|
| Mapped required composition with sufficient observations | `satisfied` for the bounded structural predicate |
| Child references concrete parent under explicit prohibition | `violated`, linked to rule and source span |
| Incomplete scan with no forbidden edge found | `unknown`, never an absence proof |
| Ambiguous mapping | `unknown`, with candidate mappings visible |
| Extra relation omitted by tree projection | Retained in report with explicit disposition |
| Mismatched revisions or unsupported rule | `unknown` with the specific limitation |
| Malformed observation payload | Input-validation failure |

Use a positive and a negative implementation fixture plus incomplete/ambiguous
observations. No new schema is considered stable until the focused fixture checks
and consumer-facing report contract exist. An initial comparator should be
read-only and must not edit `.hc`, canonical specs, or implementation code.

A later, separately scoped Clojure application may exercise a versioned generator
profile and UML Viewer scanner/output. Validate the actual upstream contract and
license before selecting dependencies. Clojure and a diagram alone do not prove
these architectural constraints; full EDN round-trip and visual acceptance are
separate checks. Repository creation is explicitly deferred.

## Completion of This Proposal Slice

This contract slice is complete when the proposal tracking gate passes, the
source snapshot and promotion entry are present, the deferred runtime posture is
visible, and DocC mirrors the same scope. These are document/tracking checks;
none is runtime comparison evidence.

Future activation requires a reviewed bounded implementation with fixture tests,
a report contract, and an explicit mapping to existing evidence/work surfaces.
The proposed report is derived and read-only (`canonical_mutations_allowed: false`).
No current artifact grants code-generation, repair, publication, or approval authority.

## Open Questions

- What mapping survives refactors, one-to-many realization, and shared services?
- Which scanner can prove the first predicate, and how is its scope represented?
- How should multiple composition roots map to platform input boundaries?
- Which rules need runtime evidence instead of static facts?
- Where should reusable generation profiles live after the first application?
- Which existing report/envelope should the consumer extend without creating a
  second evidence or Implementation Work system?
