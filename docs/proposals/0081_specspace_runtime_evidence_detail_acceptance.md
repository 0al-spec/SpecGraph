# SpecSpace Runtime Evidence Detail Acceptance

## Status

Draft proposal

## Source Material

This proposal closes the downstream evidence loop for SpecSpace PR `#229`.

Source draft:

- `docs/archive/proposal_sources/0081_specspace_runtime_evidence_detail_acceptance.md`

## Context

`0078` made Agent runtime enforcement evidence available to SpecSpace, and
`0079` accepted the first SpecSpace implementation that rendered runtime
evidence summary and per-surface rows from
`runs/agent_runtime_enforcement_evidence_index.json`.

SpecSpace PR `0al-spec/SpecSpace#229` then expanded the consumer behavior by
loading safe detail artifacts under
`runs/agent_runtime_enforcement_evidence/` and rendering nested evidence checks,
including `executor_adapter_invocation_boundary`.

This proposal records that detail-expansion implementation in the existing
external consumer evidence acceptance plane.

## Goals

- Add one report-only external consumer evidence record for SpecSpace PR `#229`.
- Bind the record to the existing `external_consumer_handoff::specspace`
  handoff.
- Include both the runtime evidence index and the supervisor executor adapter
  smoke detail artifact in consumed and accepted contract artifacts.
- Reference SpecSpace CI/deploy smoke and Platform Timeweb publish evidence.

## Non-Goals

- Mutating SpecSpace.
- Mutating Platform.
- Re-validating live production UI by scraping Timeweb in this proposal.
- Claiming observed runtime enforcement.
- Introducing a new evidence artifact family.

## Evidence

The accepted evidence record references:

- SpecSpace PR: `https://github.com/0al-spec/SpecSpace/pull/229`;
- SpecSpace CI and production smoke:
  `https://github.com/0al-spec/SpecSpace/actions/runs/27107160978`;
- Platform Timeweb publish:
  `https://github.com/0al-spec/Platform/actions/runs/27107183404`.

The consumed artifact set includes:

```text
runs/supervisor_executor_adapter_index.json
runs/agent_surface_index.json
runs/known_agent_passport_index.json
runs/agent_passport_verification_report.json
runs/agent_verification_gap_index.json
runs/agent_runtime_enforcement_evidence_index.json
runs/agent_runtime_enforcement_evidence/supervisor-executor-adapter-smoke.json
```

## Acceptance

This slice is complete when:

- `runs/external_consumer_evidence_index.json` accepts the new SpecSpace detail
  evidence entry;
- existing SpecSpace evidence entries remain accepted;
- no local paths, raw logs, secrets, or raw passport material are introduced;
- proposal tracking gates, `make external-handoffs`,
  `make external-consumer-evidence`, focused evidence tests, and the full
  Python suite pass.
