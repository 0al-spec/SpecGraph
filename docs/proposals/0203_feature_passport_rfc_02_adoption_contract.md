# 0203 Feature Passport RFC 0.2 Adoption Contract

## Status

Draft / contract adoption slice.

## Summary

Adopt FeaturePassport PR `#3` as the current external authority for SpecGraph
Feature Runtime Evidence planning.

The merged RFC version is `FP-RFC-0001` / `0.2.0`. It tightens the evidence
contract in ways that affect future SpecGraph derived artifacts, but it does not
require SpecGraph to implement a telemetry SDK, ingestion service, storage
backend, hosted viewer, or Platform receipt issuer in this slice.

## Decision

SpecGraph proposal `0058` should reference the merged Feature Passport RFC
`0.2.0` and preserve these downstream constraints:

- `receipt_hash` covers the accepted event hash, validation/claim fields,
  previous receipt hash, and protected signature metadata; only the signature
  value is excluded from the hash input.
- Every receipt chain declares its scope, with one chain per Feature Passport per
  environment as the recommended default.
- Evidence levels form a ladder only over levels applicable to the feature.
  Levels skipped by `required_when` predicates are `not applicable`, not
  failures.
- Only `observation.result: "success"` can satisfy a level; failure observations
  remain evidence of attempts or errors.
- Single receipts record probe-level claim contributions. Aggregate claims such
  as minimum users or sessions require a separate claim-evaluation result over a
  sealed receipt set.
- Feature Passport lifecycle is explicit: `draft`, `sealed`, and amended
  versions. Receipts and derived projections must pin the active passport
  version used at sealing time.
- Probe attribute allowlists belong to the passport contract, and ingestion must
  not promote undeclared observation attributes into evidence projections.

## Follow-Up Tasks

Before implementing `runs/feature_evidence_index.json`, define schema contracts
for:

- `runs/feature_passport_index.json`;
- `runs/feature_evidence_index.json`;
- receipt projections, including hash-chain scope and protected signature
  metadata;
- claim-evaluation results, including aggregate-pending, satisfied, failed,
  inapplicable, and conflicting states.

After those producer schemas exist, SpecSpace can define the viewer contract for
the Feature Evidence panel. That UI must consume only safe derived SpecGraph
artifacts, not raw telemetry, private receipts, or external RFC parsing.

Platform remains out of scope until a later decision chooses whether Platform is
only a report producer, a receipt normalizer, or an evidence receipt issuer.

## Authority Boundary

This slice does not:

- redefine the Feature Passport RFC inside SpecGraph;
- implement SDKs, ingestion, storage, signing, or verification;
- add SpecSpace UI;
- make Platform a Feature Passport receipt issuer;
- mutate canonical specs or product workspaces;
- treat analytics dashboards, feature flags, or client observations as
  canonical proof.

## Acceptance Criteria

- Proposal `0058` references `FP-RFC-0001` / `0.2.0` and the merged PR `#3`
  authority.
- SpecGraph roadmap text names the pre-implementation schema task for Feature
  Passport indexes, receipt projections, and claim-evaluation results.
- SpecSpace and Platform follow-ups are recorded as downstream roadmap items,
  not implemented in this slice.
- Deprecated `tasks.md` remains untouched; durable tracking uses proposals,
  registries, and roadmaps.
