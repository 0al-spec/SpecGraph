# Agent Passport CLI Availability in Static Publish

## Draft Plan

Make the public static artifact publish path install and require the Agent
Passport CLI so published Agent Passport producer artifacts no longer report
`agent_passport_cli_status: missing`.

## Scope

- Reuse the Agent Passport GitHub Release download pattern already proven in
  SpecSpace CI.
- Install the binary into GitHub Actions runner temp storage and add it to
  `PATH`.
- Fail closed in public static bundle builds when report-only Agent Passport
  verification is missing or incomplete.
- Keep an explicit local/draft opt-out for unverified bundles.
- Do not commit or publish the binary.
- Do not change SpecSpace, Platform, Agent Passport schema, or runtime
  enforcement behavior.

## Validation Intent

- focused static artifact bundle tests
- `make agent-passports`
- `make publish-bundle`
- proposal tracking gates
- full Python suite
