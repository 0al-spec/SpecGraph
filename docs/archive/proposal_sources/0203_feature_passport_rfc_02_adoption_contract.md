# Feature Passport RFC 0.2 Adoption Contract Source Draft

FeaturePassport PR `#3` tightened `FP-RFC-0001` from `0.1.0` to `0.2.0` and
was merged on 2026-07-06 as merge commit
`724e51c47fee89de1fcd4a3857ebbcea9bf1fa19`. SpecGraph should update its
Feature Runtime Evidence integration contract before any implementation consumes
Feature Passport evidence artifacts.

Bounded scope:

- update proposal `0058` to treat the merged `FP-RFC-0001` `0.2.0` source as
  the current external authority;
- record that `receipt_hash` covers receipt content and signature metadata;
- require declared receipt chain scope;
- preserve success-only level satisfaction;
- preserve `required_when` skipped-level semantics;
- keep aggregate claim evaluation separate from single receipt acceptance;
- require passport lifecycle/version pinning in downstream derived surfaces;
- leave schema implementation, SpecSpace UI, and Platform receipt issuance as
  separate follow-up slices.

This is an adoption contract and roadmap slice, not an SDK, ingestion service,
storage engine, viewer implementation, or Platform runtime change.
