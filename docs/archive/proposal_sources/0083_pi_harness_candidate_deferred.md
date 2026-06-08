# Pi Harness Candidate Deferred

## Draft Plan

Record Pi as a deferred experimental executor harness candidate, while
preserving Codex as the default stable local executor.

## Scope

- Create proposal `0083`.
- Clarify executor runtime modes:
  - static publish is not an executor runtime;
  - local trusted operator mode can use Codex for cost/ergonomics;
  - future external harness mode may use Pi through BYOK/provider config.
- Record credential boundaries for Codex auth vs Pi/BYOK.
- State that Pi must not mutate canonical graph state directly.
- Defer Pi adapter implementation, Agent Passport surface changes, SpecSpace
  session import, and Platform packaging.

## Validation Intent

- proposal tracking gates
- full Python suite
