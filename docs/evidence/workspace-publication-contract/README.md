# Workspace publication contract regression — 2026-09-30

Related realization: proposal `0215`, checksum-aware static publication.
Status: local publisher/real HTTP consumer observations; production remains unchanged.

## Failure and contract

Deployed SpecSpace `bd3de6137ebe5c2fa2c53079b699f6d9d18f89da` required manifest-authorized `runs/hosted-operation-canary/<file>` after recognizing a ready binding. Producer `401cc0b7a3c98fef8e1887aebbdc4eb1bc8ead58` only listed the selected workspace files at flat `runs/<file>` aliases. Direct HTTP availability of stale unlisted files did not authorize consumption.

The scoped paths are now published with identical sanitized bytes and SHA-256 digests while flat compatibility aliases and bootstrap discovery remain. The canonical Decision index is regenerated only at its established root address; no stale source Decision index is copied into the scoped namespace. Manifest checks, source authority, and blocked-vs-ready lifecycle semantics remain in the consumer.

## Observations

- Observed Red: selected-workspace publisher regression failed with the missing scoped candidate file before alias implementation.
- Focused publisher/deploy-plan/smoke preflight unit tests and Ruff passed (see task PR for final counts/commands).
- [Canary HTTP smoke](canary-smoke.json): actual publisher bundle yielded a ready binding, complete readable workspace and eight nodes. Unlisted scoped candidates were rejected while flat aliases still existed; altered payload digest and foreign workspace identity were rejected.
- [Team Decision Log compatibility](team-decision-log-smoke.json): complete readable workspace, six nodes; its domain state remained `blocked`. This is a valid read model, not promotion approval. Legacy smoke does not assert a trusted workspace binding.

The Team local fixture build used `--allow-unverified-agent-passports --allow-missing-required-surfaces` because the isolated checkout lacked unrelated root generated surfaces. Its publication safety gate remained failed. This result verifies legacy HTTP consumption only, not a publishable production bundle. Normal CI builds the full root bundle with existing fail-closed gates before running both consumer checks.

## Repeat

```sh
make workspace-bundle-consumer-smoke \
  WORKSPACE_BUNDLE_CONSUMER_REPO=/path/to/pinned/SpecSpace \
  WORKSPACE_BUNDLE_SMOKE_DIR=/path/to/workspace/bundle
```

For the legacy Team workspace, supply `WORKSPACE_BUNDLE_SMOKE_ID=team-decision-log` and `WORKSPACE_BUNDLE_SMOKE_FLAGS=--legacy-workspace`. Both commands use an exact consumer source pin and reject dirty consumer source. The local server backlog accommodates the consumer's twelve parallel artifact requests. No operation is executed; a temporary bundle copy is modified for negative checks and deleted afterward.

Next gate: review/merge the producer fix, publish with normal safety gates, then rerun production smoke against the newly published manifest and deployed SpecSpace.

## PR #741 review closure

Thread [4146823908](https://github.com/0al-spec/SpecGraph/pull/741#discussion_r4146823908) exposed a `test_coverage_gap`: candidate corruption from the digest negative could mask a foreign-identity regression. Candidate bytes are now restored in `finally`, and the selected workspace must be readable before the independent identity check.

Prevention: `test_identity_negative_uses_restored_candidate` exercises both rejecting and incorrectly accepting consumers, checks the healthy identity baseline, and verifies the original fixture is unchanged. Both cases failed against the original implementation; the incorrect accepting consumer previously produced no error. After the fix, 75 focused publisher/deploy-plan/smoke tests passed, Ruff passed, and the actual pinned SpecSpace HTTP Canary smoke passed again. The retained `canary-smoke.json` was refreshed from that corrected run. Production verification remains pending publication.
