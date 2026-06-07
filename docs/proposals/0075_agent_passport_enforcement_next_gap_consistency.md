# Agent Passport Enforcement Next-Gap Consistency

## Status

Draft proposal

## Source Material

This proposal captures the operator request to align Agent Passport
next-gap summaries after report-only verification and runtime enforcement
posture classification.

Source draft:

- `docs/archive/proposal_sources/0075_agent_passport_enforcement_next_gap_consistency.md`

## Context

The Agent Passport line now has:

- declared passport references for every graph-facing surface;
- report-only schema validation through the Agent Passport CLI;
- classified runtime enforcement posture (`policy_only`, `boundary_only`,
  `deferred`);
- SpecSpace evidence for displaying those posture states.

The remaining derived gaps are runtime posture gaps, not missing declaration or
verification-run gaps.

## Problem

After successful report-only verification, `known_agent_passport_index` and
`agent_verification_gap_index` correctly point at closing remaining verification
gaps, while `agent_surface_index.summary.next_gap` can still point at
`run_report_only_passport_verification`.

That creates an inconsistent operator signal:

```text
known_agent_passport_index.summary.next_gap: close_agent_verification_gaps
agent_verification_gap_index.summary.next_gap: close_agent_verification_gaps
agent_surface_index.summary.next_gap: run_report_only_passport_verification
```

The surface index is an upstream artifact, but the combined `make
agent-passports` flow has enough downstream context to align the published
surface summary with the final verification/gap indexes.

## Goals

- Keep standalone `build_agent_surface_index()` useful before verification.
- Align `agent_surface_index.summary.next_gap` after the full Agent Passport
  derived-surface build.
- Ensure missing-passport gaps still point at
  `declare_missing_agent_passports`.
- Ensure missing tool or not-attempted verification still points at
  `run_report_only_passport_verification`.
- Ensure successful report-only verification with remaining runtime posture gaps
  points at `close_agent_verification_gaps` across the derived indexes.

## Non-Goals

- Implementing runtime enforcement.
- Changing Agent Passport documents.
- Mutating SpecSpace.
- Changing Platform deployment.
- Claiming `observed` runtime enforcement.

## Realization

This slice updates the Agent Passport derived builders so the final
`agent_surface_index` emitted by `make agent-passports` inherits the final
next-gap signal from the verification gap index when the full pipeline has run.

The gap index owns the final next-gap classification:

```text
missing_passport -> declare_missing_agent_passports
verification_tool_unavailable / verification_not_attempted
  -> run_report_only_passport_verification
remaining verification/runtime posture gaps
  -> close_agent_verification_gaps
no gaps -> none
```

## Validation

This slice is valid when:

- focused Agent Passport tests prove the aligned next-gap behavior;
- `make agent-passports` emits consistent summaries;
- proposal gates pass;
- the full Python test suite passes.

