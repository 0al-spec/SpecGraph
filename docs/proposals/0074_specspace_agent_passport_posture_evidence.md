# SpecSpace Agent Passport Posture Evidence

## Status

Draft proposal

## Source Material

This proposal records downstream evidence that SpecSpace implemented the
Agent Passport posture consumer contract introduced by `0073`.

Source draft:

- `docs/archive/proposal_sources/0074_specspace_agent_passport_posture_evidence.md`

## Context

Proposal `0073 Agent Passport Posture Consumer Contract` extended the existing
SpecGraph -> SpecSpace handoff to include the full report-only Agent Passport
posture artifact set:

```text
runs/supervisor_executor_adapter_index.json
runs/agent_surface_index.json
runs/known_agent_passport_index.json
runs/agent_passport_verification_report.json
runs/agent_verification_gap_index.json
```

SpecSpace PR `0al-spec/SpecSpace#227` implemented the consumer side in the
existing Agent surfaces panel and deployed through the Platform Timeweb publish
flow.

## Problem

The producer contract is stable, and SpecSpace now displays the posture states,
but SpecGraph has not yet accepted evidence for this second consumer slice. If
the evidence registry is not updated, the handoff loop remains operationally
open even though the downstream UI and deploy evidence exist.

## Goals

- Add report-only evidence for SpecSpace PR #227.
- Require the evidence entry to name all producer artifacts from the 0073
  contract.
- Link SpecSpace CI, production smoke, and Platform Timeweb publish evidence.
- Keep historical PR #225 evidence accepted against its earlier artifact
  snapshot.
- Preserve the privacy boundary: no local-only paths or raw logs.

## Non-Goals

- Mutating SpecSpace.
- Changing Platform deployment logic.
- Implementing Agent Passport runtime enforcement.
- Claiming `observed` runtime enforcement.
- Polling GitHub live from the evidence builder.

## Evidence

The new evidence record binds:

- SpecSpace PR: <https://github.com/0al-spec/SpecSpace/pull/227>
- SpecSpace CI run:
  <https://github.com/0al-spec/SpecSpace/actions/runs/27086013200>
- Platform Timeweb Publish run:
  <https://github.com/0al-spec/Platform/actions/runs/27086037221>

This proves that SpecSpace consumes and displays the report-only Agent Passport
posture artifacts. It does not prove runtime enforcement; `policy_only`,
`boundary_only`, and `deferred` remain posture states, not enforcement claims.

## Validation

This slice is valid when:

- `external_consumer_evidence_index` accepts both SpecSpace evidence entries;
- the PR #227 evidence consumes all five 0073 producer artifacts;
- proposal tracking gates pass;
- `make external-consumer-evidence`, `make external-handoffs`, focused evidence
  tests, and the full test suite pass.
