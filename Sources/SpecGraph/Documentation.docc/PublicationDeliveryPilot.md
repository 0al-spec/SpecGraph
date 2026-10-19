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

This is `provider_reported` evidence with `admission: not_evaluated`.
The profile does not activate `tests_verified_v1` or alter signed receipt and
claim-admission contracts. The Python bindings do not use the Swift resolver.
Ontology supplies the existing `SG-SPEC-0020` trace vocabulary.

Acceptance uses retained GitHub PR metadata matching the exact merged revision
and base repository. Missing metadata and closed-but-unmerged PRs do not count.
Operational evidence does not change canonical maturity.
See repository `docs/publication_delivery_pilot.md` for commands, scope and limits.
