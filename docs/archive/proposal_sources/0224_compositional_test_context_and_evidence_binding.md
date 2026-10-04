# Source: Compositional Test Context and Evidence Binding

Captured: 2026-10-04
Source class: operator discussion and read-only local source inspection

## Operator intent

In the Zeusus legacy-sprite selection pilot the operator requested code-level
snapshot tests, explicit links from those tests to specifications, and noted
that SpecificationCore has tracing/evidence ideas but no `SpecificationTest`.
The follow-up supports composition to trace specifications in the context of a
test and carry all metadata from beginning to end.

Existing direction: SpecificationCore materializes policy objects, SpecGraph
owns spec/scenario intent and references, FeaturePassport remains provider-neutral
and does not depend on SpecGraph. Test execution, source inspection, runtime
observations and accepted receipts are distinct evidence kinds.

## Inspected baseline

- SpecGraph topic work starts from freshly fetched `origin/main`; proposals 0019,
  0047, 0058, 0221 and 0223 provide related contracts. Proposal 0223 explicitly
  leaves execution bindings and test-runner adapters to follow-up work.
- SpecificationCore checkout `483214469828c42f7b615654aa70d0acbecc4dbf`:
  `Sources/SpecificationCore/Tracing/SpecificationTraceRuntime.swift` has a private
  task-local context containing recorder and parent ID. Events carry local IDs,
  names, evaluation outcomes, timings and optional shared-timeline positions.
  This is not a provenance-rich test observation. No `SpecificationTest` API was
  found in the inspected Sources/Tests. This statement is scoped to that checkout.
- FeaturePassport checkout `0fe35e9edb1461744ffa89161ec64cc86d44f728`:
  RFC 0001 owns generic external references, observations and receipts; core
  schema validation does not establish behavior coverage. Existing uncommitted
  example changes were not used as contract authority or modified.
- Zeusus current `ZEU-SPEC-0024` declares `ZEU-LEGACY-ANCHOR-001` for declared
  anchor mapping and `ZEU-LEGACY-ANCHOR-003` for preview/committed parity. These
  scenario labels motivate the pilot; actual execution must resolve and pin
  the immutable workspace and exact source content independently.

## Preparation boundaries

The proposal is author-curated from the operator request. It is not a successful
Supervisor refinement, canonical adoption, SDK implementation, test result or
admission receipt. No existing test/build is retroactively claimed as produced
by this contract. Proposed BDD cases remain future acceptance obligations.
