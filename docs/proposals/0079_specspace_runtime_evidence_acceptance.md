# SpecSpace Runtime Evidence Acceptance

## Status

Draft proposal

## Source Material

This proposal closes the downstream evidence loop for
`0078 SpecSpace Runtime Evidence Handoff Contract`.

Source draft:

- `docs/archive/proposal_sources/0079_specspace_runtime_evidence_acceptance.md`

## Context

`0078` made `runs/agent_runtime_enforcement_evidence_index.json` a stable
SpecSpace handoff artifact. SpecSpace then implemented the consumer slice in
PR `0al-spec/SpecSpace#228`, projecting runtime evidence summary counts and
per-surface evidence rows in its Agent surfaces API/UI.

This proposal records that downstream implementation evidence in the existing
external consumer evidence acceptance plane.

## Goals

- Add a report-only external consumer evidence record for SpecSpace PR `#228`.
- Bind the record to the existing `external_consumer_handoff::specspace`
  handoff.
- Include the runtime evidence index in both consumed and accepted contract
  artifacts.
- Reference SpecSpace CI/deploy smoke and Platform Timeweb publish evidence.

## Non-Goals

- Mutating SpecSpace.
- Mutating Platform.
- Re-validating live production UI by scraping Timeweb.
- Claiming observed runtime enforcement.
- Introducing a new evidence artifact family.

## Evidence

The accepted evidence record references:

- SpecSpace PR: `https://github.com/0al-spec/SpecSpace/pull/228`;
- SpecSpace CI and production smoke:
  `https://github.com/0al-spec/SpecSpace/actions/runs/27096542168`;
- Platform Timeweb publish:
  `https://github.com/0al-spec/Platform/actions/runs/27096573214`.

The consumed artifact set includes:

```text
runs/supervisor_executor_adapter_index.json
runs/agent_surface_index.json
runs/known_agent_passport_index.json
runs/agent_passport_verification_report.json
runs/agent_verification_gap_index.json
runs/agent_runtime_enforcement_evidence_index.json
```

## Acceptance

This slice is complete when:

- `runs/external_consumer_evidence_index.json` accepts the new SpecSpace
  runtime evidence entry;
- existing SpecSpace evidence entries remain accepted;
- no local paths, raw logs, secrets, or raw passport material are introduced;
- proposal tracking gates, `make external-handoffs`,
  `make external-consumer-evidence`, focused evidence tests, and the full
  Python suite pass.
