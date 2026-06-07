# Agent Passport Report-Only Verification

## Status

Draft proposal

## Source Material

This proposal realizes the next bounded runtime slice after `0070 Agent
Passport Reference Declaration`.

Source draft:

- `docs/archive/proposal_sources/0071_agent_passport_report_only_verification.md`

## Context

Proposal `0070` declared Agent Passport references for every required graph
agent surface. The derived indexes now report:

```text
missing_passport_count: 0
next_gap: run_report_only_passport_verification
```

The Agent Passport CLI is available through the `0056` executor-adapter
diagnostic surface. The next slice should use that CLI in practice, but remain
report-only: no runtime enforcement, no signature trust-store validation, no
agent launch, and no raw passport material in generated reports.

## Goals

- Add repository-relative Agent Passport document mappings for declared
  `agent-passport://...` refs.
- Add draft passport YAML documents for the current five graph-agent surfaces.
- Run `agent-passport validate --json` from the Agent Passport CLI when building
  Agent Passport derived surfaces.
- Produce a sanitized `runs/agent_passport_verification_report.json`.
- Reflect schema-valid report-only verification in
  `runs/known_agent_passport_index.json`.
- Replace `verification_not_attempted` gaps with concrete
  `verification_failed`, `verification_unavailable`, or no verification gap.
- Preserve `runtime_enforcement_unknown` as an open gap.

## Non-Goals

- Cryptographic signature verification against a trust store.
- Lifecycle, revocation, or issuer trust verification.
- Runtime policy enforcement.
- Integrity-file verification with local source hashes.
- Launching graph agents or executor backends.
- Persisting raw passport YAML contents inside generated runtime artifacts.
- Mutating SpecSpace or Platform.

## Runtime Surfaces

This slice adds:

```text
tools/agent_passports/*.passport.yaml
runs/agent_passport_verification_report.json
```

It also extends existing surfaces:

```text
tools/agent_passport_adoption_policy.json
runs/known_agent_passport_index.json
runs/agent_verification_gap_index.json
```

`make agent-passports` remains the operator command. It now writes the
verification report in addition to the existing executor adapter, surface,
known-passport, and gap indexes.

## Verification Semantics

Report-only verification has these statuses:

- `valid`: CLI schema/content validation passed.
- `invalid`: CLI validation ran and rejected the passport document.
- `unavailable`: the declared reference has no safe repository-relative document.
- `tool_unavailable`: the Agent Passport CLI is not available.

`valid` maps to `V3_schema_valid`. It does not imply:

- `V4_signature_verified`;
- lifecycle validity;
- runtime enforcement;
- integrity hash verification.

## Privacy Boundary

Generated artifacts may include:

- `agent-passport://...` refs;
- repository-relative passport document paths;
- CLI status and sanitized checks.

Generated artifacts must not include:

- raw passport YAML contents;
- absolute local paths;
- raw validator logs;
- secrets or private keys.

## Acceptance

This slice is complete when:

- `agent-passport validate --json tools/agent_passports/*.passport.yaml` succeeds;
- `make agent-passports` emits `passport_verification_valid_count: 5`;
- `runs/agent_passport_verification_report.json` reports five `valid` entries;
- `runs/agent_verification_gap_index.json` reports
  `verification_not_attempted_count: 0`;
- `runtime_enforcement_unknown_count` remains non-zero and out of scope.

