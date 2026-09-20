# Composition and Observation Comparison

Proposal `0219` defines a comparison contract only. Its runtime posture is
`deferred_until_canonicalized`; no comparator, scanner, code generator, quality
gate, or UML Viewer adapter is implemented by this documentation slice.

## Ownership

Hypercode supplies minimal composition and resolved context through canonical
IR. A consumer-owned generation contract supplies platform rules, potentially
as a versioned system prompt. SpecGraph is the proposed comparison consumer;
Metrics owns reusable metric methods, while application policies choose thresholds.
A future Clojure application and viewer experiment are deferred.

## Evidence boundary

Desired composition and the Observed Graph can have different relation
vocabularies. Extra code relations must survive a tree projection. Results must
identify the structure/property contract, external rule, or policy being checked
and link it to mapped entities, source evidence, revisions, and limitations.

The proposed outcomes are `satisfied`, `violated`, and `unknown`. Incomplete
observations cannot prove absence; ambiguous mapping or incompatible snapshots
must not become success. A positive violation witness may remain decisive in an
incomplete scan. Malformed inputs fail validation. Satisfaction is limited to a
supported predicate and snapshot, not whole-program correctness.

Existing HCS contracts narrow resolved-property constraints. They do not already
check implementation architecture or metric thresholds. `hypercode diff` remains
IR-to-IR comparison. Metric observations are not threshold authority; cascade and
aggregation of quality policies require a separate consumer contract.

## Next bounded slice

Start with fixed positive, negative, incomplete, ambiguous, and stale fixtures;
validate mapping, preserved extra relations, and evidence-linked results before
adding live generation, scanning, or UI. Reuse existing evidence and
Implementation Work surfaces after inspecting their actual contracts.

The future report remains derived and read-only:
`canonical_mutations_allowed: false`. Tracking and DocC checks verify this
proposal's documentation, not an operational comparator.

Canonical proposal:
[Composition and Observation Comparison Contract](https://github.com/0al-spec/SpecGraph/blob/main/docs/proposals/0219_composition_observation_contract.md).
