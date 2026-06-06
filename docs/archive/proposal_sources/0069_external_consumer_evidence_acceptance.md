# Source Draft: External Consumer Evidence Acceptance

Operator request:

> Ok делаем этот план для задачи
>
> 0069 External Consumer Evidence Acceptance

Plan captured by the proposal:

- close the SpecGraph -> SpecSpace external consumer loop by accepting downstream
  implementation evidence back into SpecGraph;
- use the existing external consumer handoff evidence contract shape;
- add a tracked evidence registry and derived evidence index;
- record SpecSpace PR #225, SpecSpace CI/smoke, and Platform Timeweb publish as
  evidence for `external_consumer_handoff::specspace`;
- keep the slice report-only and avoid SpecSpace UI, Platform deploy, live
  GitHub polling, or Agent Passport enforcement changes.

