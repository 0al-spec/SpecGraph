# Agent Passport CLI Availability in Static Publish

## Status

Draft proposal

## Source Material

This proposal closes the static-publish availability gap for report-only Agent
Passport verification.

Source draft:

- `docs/archive/proposal_sources/0082_agent_passport_cli_static_publish.md`

## Context

SpecGraph emits Agent Passport producer artifacts consumed by SpecSpace:

```text
runs/supervisor_executor_adapter_index.json
runs/agent_surface_index.json
runs/known_agent_passport_index.json
runs/agent_passport_verification_report.json
runs/agent_verification_gap_index.json
```

Before this slice, the public static publish job could build and deploy these
artifacts without the `agent-passport` CLI installed on the GitHub Actions
runner. That left published artifacts with `agent_passport_cli_status: missing`
and `verification_tool_unavailable` gaps even though the repository contains
draft passport documents and the Agent Passport release artifact is available.

## Goals

- Install the Agent Passport CLI in the `Publish Static Artifacts` build job
  before `make publish-bundle`.
- Keep the Agent Passport binary out of the repository.
- Require public static bundles to contain successful report-only Agent Passport
  validation results.
- Preserve artifact privacy: no machine-local CLI path is persisted in
  published JSON.
- Keep local/draft bundle opt-out explicit.

## Non-Goals

- Changing the Agent Passport schema.
- Verifying signatures, lifecycle, revocation, or trust stores.
- Implementing runtime enforcement.
- Mutating SpecSpace or Platform.
- Publishing the Agent Passport binary as a SpecGraph artifact.

## Runtime Behavior

The publish workflow downloads the latest `0al-spec/agent-passport` Linux
release asset, verifies its `.sha256`, installs it into `$RUNNER_TEMP`, and
adds that directory to `PATH`.

`make publish-bundle` then refreshes Agent Passport surfaces and fails closed if
the generated publish bundle does not show:

- `runs/supervisor_executor_adapter_index.json` summary field
  `agent_passport_cli_status: available`;
- `runs/agent_passport_verification_report.json` summary field `valid_count`
  equal to `runs/agent_passport_verification_report.json` summary field
  `entry_count`;
- `runs/agent_verification_gap_index.json` summary fields
  `verification_tool_unavailable_count: 0` and
  `verification_not_attempted_count: 0`.

The bundle builder defaults to strict verification. The local Makefile
shortcut passes `--allow-unverified-agent-passports` by default for draft
operator builds, while the public publish workflow clears that local flag and
keeps the static host path strict.

## Acceptance

This slice is complete when:

- the `Publish Static Artifacts` workflow installs the Agent Passport CLI before
  `make publish-bundle`;
- static bundle tests prove missing CLI or partial validation fails closed;
- `make publish-bundle` succeeds when Agent Passport CLI is available;
- proposal tracking gates and the full Python suite pass;
- no absolute CLI path, raw validator log, secret, or raw passport material is
  persisted in published artifacts.
