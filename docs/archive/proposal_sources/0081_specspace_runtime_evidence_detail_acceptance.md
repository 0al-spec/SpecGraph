# SpecSpace Runtime Evidence Detail Acceptance

## Draft Plan

Record downstream evidence that SpecSpace expanded the runtime evidence consumer
from aggregate rows to safe detail artifact checks in PR `#229`.

## Scope

- Add one external consumer evidence registry entry for SpecSpace PR `#229`.
- Reference SpecSpace CI/production smoke and Platform Timeweb publish runs.
- Keep using `runs/external_consumer_evidence_index.json`.
- Include the runtime evidence index and the supervisor executor adapter smoke
  detail artifact as consumed artifacts.
- Add the detail artifact to the stable SpecSpace handoff contract.
- Do not mutate SpecSpace or Platform in this slice.
- Do not claim observed runtime enforcement.

## Validation Intent

- `make external-handoffs`
- `make external-consumer-evidence`
- proposal tracking gates
- focused external-consumer evidence tests
- full Python suite
