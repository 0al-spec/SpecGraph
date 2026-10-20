# Publication Delivery Pilot

The `linked_delivery_signals_v1` bootstrap pilot links
`specgraph.publication.verify_bundle` to `SG-SPEC-0071` and a draft Feature
Passport, five explicit pytest obligations, CI artifacts and the existing HTTP
publication check. Its requirement is `SG-REQ-PUBLICATION-VERIFIED`.

Run `make test-publication-delivery` and `make publication-delivery-report` with
an explicit output directory for local evidence. The adapter retains JUnit,
source and passport digests, run/attempt identity, JSON and a Markdown table.

The publication workflow retains
`specgraph-publication-delivery-signals-build` before deploy and
`specgraph-publication-delivery-signals-deploy` afterwards for 30 days. It also
adds the table to the job summary. Runtime means matching HTTP-published bundle
bytes observed by an Actions-side verifier. It does not mean that Python
executes on the static host. Missing or skipped evidence never becomes success.

Every stage separates `provenance.observer` (the actual CI/local execution) from
`provenance.target` (environment and URI). Deploy/runtime target the explicitly
bound production origin `https://specgraph.tech`; the report environment labels
only the projection context. Retained CI reports keep their original observer
when projected locally. Missing runtime evidence has a null observer and an
intended target, which does not establish deployment success.

This is `provider_reported` evidence with `admission: not_evaluated`.
The profile does not activate `tests_verified_v1` or alter signed receipt and
claim-admission contracts. The Python bindings do not use the Swift resolver.
Ontology supplies the existing `SG-SPEC-0020` trace vocabulary.

The rule inventory is `SG-SPEC-0071.atoms.intents[]`: 13 explicitly identified
atoms with executable `verifiable_by` references. Seven SpecificationCore
policies in `tools/publication_evidence/` receive immutable typed contexts.
Binding errors, testcase and suite outcomes have explicit `FirstMatch` priority;
fresh and retained tests reuse the suite policy. Source collection and retained
test joins reuse the snapshot policy. Bindings name the policy symbols actually
used by the adapter; the source identity pins the extracted modules too.

The existing Intent Atoms v1 profile counts the explicit inventory and keeps
the three broad acceptance entries as non-counted context. This representation
change does not imply ten new behaviors. See the rule-to-implementation/test
table in `docs/publication_delivery_pilot.md`.

The report's test observations cover the five `PB-*` feature scenarios.
The ordinary Python suite separately verifies the `PE-*` adapter policies.

Intent/spec success describes declarations; deploy/runtime share one HTTP
observation. These are linked observations with limited independence.

Acceptance uses retained GitHub PR metadata matching the exact merged revision
and base repository. Missing metadata and closed-but-unmerged PRs do not count.
Operational evidence does not change canonical maturity.
See repository `docs/publication_delivery_pilot.md` for commands, scope and limits.
