# SpecSpace Runtime Evidence Handoff Contract

## Draft Plan

Extend the existing SpecSpace external-consumer handoff contract to cover the
new report-only Agent runtime enforcement evidence index emitted by proposal
`0077`.

## Scope

- Add `runs/agent_runtime_enforcement_evidence_index.json` to the stable
  SpecSpace producer artifact contract.
- Add runtime evidence statuses to the SpecSpace consumer-facing Agent Passport
  contract.
- Keep using `runs/external_consumer_handoff_packets.json`.
- Do not implement SpecSpace UI in this slice.
- Do not add Platform deploy changes in this slice.
- Do not accept downstream evidence until the SpecSpace implementation exists.

## Validation Intent

- `make agent-runtime-evidence`
- `make external-handoffs`
- proposal tracking gates
- focused external-consumer and Agent Passport contract tests
- full Python suite
