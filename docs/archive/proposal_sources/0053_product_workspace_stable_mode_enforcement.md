# Product Workspace Stable Mode Enforcement Source Draft

## Source Context

This source draft captures the operator decision after Product Workspace
Governance Profile became visible as a derived environment artifact.

The next concern is not another read-only badge. Product workspace mode must
become an enforceable supervisor boundary so SpecGraph can be used against an
external project without accidentally continuing SpecGraph self-evolution.

## Operator Intent

SpecGraph should support a stable client/project mode:

- the engine and core policies remain locked by default;
- the supervisor works on the user's product graph;
- project-level reflection, diagnostics, implementation work, and quality
  feedback remain available;
- self-hosted SpecGraph improvement loops are disabled unless explicitly
  exported upstream by a human.

## Desired Outcome

Create one umbrella proposal that turns the existing product workspace profile
into a runtime enforcement epic. The proposal should decompose the follow-up
work into bounded PR slices:

- policy contract tightening;
- next-move filtering;
- target and path enforcement;
- viewer-facing diagnostics;
- stable client instance guidance;
- smoke coverage for an external product workspace.

## Boundary

This is not a managed cloud or multi-tenant hosting proposal. It is the first
stable-mode enforcement contract for local or self-managed SpecGraph project
workspaces.
