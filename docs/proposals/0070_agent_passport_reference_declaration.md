# Agent Passport Reference Declaration

## Status

Draft proposal

## Source Material

This proposal captures the next Agent Passport adoption step after the
SpecGraph -> SpecSpace handoff loop accepted downstream implementation evidence.

Source draft:

- `docs/archive/proposal_sources/0070_agent_passport_reference_declaration.md`

## Context

Proposal `0067` materialized report-only Agent Passport derived surfaces:

```text
runs/agent_surface_index.json
runs/known_agent_passport_index.json
runs/agent_verification_gap_index.json
```

After `0069`, the first SpecGraph -> SpecSpace consumer handoff is evidenced as
implemented. The remaining high-severity Agent Passport adoption gap is no
longer the external handoff loop. It is missing graph-side passport references
for required agent surfaces.

Before this proposal, the derived indexes reported:

```text
known_agent_passport_index.summary.next_gap: declare_missing_agent_passports
missing_passport_count: 3
```

The missing required surfaces were:

- `specgraph.supervisor.executor_adapter`;
- `specspace.operator_assistant`;
- `product_workspace.implementation_agent`.

## Problem

SpecGraph can show that these surfaces require Agent Passports, but some required
surfaces still have no graph-side passport reference. That leaves downstream
indexes with `missing_passport` gaps even though the next implementation need is
not verification or runtime enforcement yet.

Without declared references:

- SpecSpace can display missing identity rather than unverified identity;
- reviewers cannot distinguish "no declared passport ref" from "passport ref is
  declared but not verified";
- future report-only verification has no target refs to evaluate;
- runtime enforcement discussion can start before identity declarations are
  complete.

## Goals

- Declare graph-side Agent Passport references for the remaining required
  surfaces.
- Reduce `missing_passport_count` to zero in the report-only derived indexes.
- Preserve `verification_not_attempted` gaps for declared but unverified refs.
- Preserve `runtime_enforcement_unknown` gaps until a policy runtime actually
  observes enforcement.
- Keep the future product workspace implementation agent marked as a future
  surface.
- Avoid storing raw passport material, signatures, local paths, validator logs,
  or secrets.

## Non-Goals

- Validating Agent Passport schemas.
- Verifying signatures, issuers, lifecycle state, revocation, or integrity.
- Fetching passport documents from the Agent Passport repository.
- Mutating SpecSpace or Platform.
- Launching agents.
- Claiming runtime enforcement.
- Replacing the external Agent Passport RFC as canonical authority.

## Runtime Realization

This slice updates:

```text
tools/agent_passport_adoption_policy.json
```

The newly declared refs are:

```text
agent-passport://specgraph/supervisor-executor-adapter/0.1.0
agent-passport://specspace/operator-assistant/0.1.0
agent-passport://product-workspace/implementation-agent/0.1.0
```

The derived artifacts continue to be built by:

```text
make agent-passports
```

The expected index transition is:

```text
missing_passport_count: 3 -> 0
known_agent_passport_index.summary.next_gap:
  declare_missing_agent_passports -> run_report_only_passport_verification
```

The verification gap index should still report:

- `verification_not_attempted` for declared refs;
- `runtime_enforcement_unknown` for required surfaces whose enforcement is not
  observed.

## Safety Boundary

The refs are identifiers, not verified passport documents. They must not be used
as proof of:

- schema validity;
- signature validity;
- issuer trust;
- lifecycle validity;
- runtime enforcement.

Those concerns remain separate follow-up work.

## Validation

This proposal is complete when:

- `make agent-passports` reports no missing passport refs;
- focused tests prove the required surfaces have declared refs;
- focused tests prove missing passport gaps disappear while verification and
  runtime enforcement gaps remain;
- proposal tracking and work-claim gates pass;
- full test suite passes.

