# Supervisor Prompt Overlay Profiles

## Status

Draft proposal

## Source Material

This proposal captures the operator request to let users provide a custom base
prompt extension for the model used under the SpecGraph supervisor.

Source draft:

- `docs/archive/proposal_sources/0051_supervisor_prompt_overlay_profiles.md`

## Context

SpecGraph supervisor already coordinates increasingly strict runtime behavior:

- bounded target selection;
- protocol markers;
- allowed-path and lock discipline;
- evidence and trace requirements;
- review gates;
- derived artifacts and graph diagnostics.

At the same time, different projects may need different model behavior:

- domain framing for a product or technology stack;
- preferred decomposition style;
- preferred level of detail;
- implementation philosophy;
- terminology preferences;
- local operator conventions.

Today those preferences can only be encoded indirectly through node prompts,
repository instructions, or ad hoc operator notes. That makes reusable behavior
hard to version, audit, or compare across runs.

## Problem

Giving users a raw "replace system prompt" control would be powerful but unsafe
for SpecGraph's current governance model.

The supervisor's prompt is not just style guidance. It carries operational
contracts that keep runs inspectable:

```text
protocol markers
allowed paths
review gates
artifact boundaries
validation expectations
evidence semantics
```

If a user-provided prompt can replace these contracts, the supervisor can
silently produce outputs that look successful while bypassing graph discipline.

The missing capability is a controlled prompt extension layer: configurable
enough to steer model behavior, but explicitly unable to override hard
SpecGraph invariants.

## Goals

- Define a governed prompt overlay layer for supervisor runs.
- Allow project/user prompt extensions to guide style, priorities, domain
  framing, and decomposition preferences.
- Preserve non-overridable supervisor invariants.
- Make active prompt profile and prompt extension provenance visible in run
  logs.
- Support project-level reusable prompt profiles.
- Keep prompt overlays reviewable as repository artifacts.

## Non-Goals

- Replacing the supervisor's core system prompt.
- Allowing prompt overlays to disable validation, evidence semantics, review
  gates, lock discipline, or protocol markers.
- Creating an interactive prompt editor.
- Adding model-provider-specific prompt syntax.
- Granting prompt overlays write authority.
- Implementing the runtime flags in this proposal-only slice.

## Core Proposal

SpecGraph should introduce **Supervisor Prompt Overlay Profiles**.

The prompt stack should be treated as layered:

```text
1. SpecGraph hard invariants
2. Supervisor task protocol
3. Project/user prompt overlay
4. Node-specific prompt
```

The overlay layer is additive. It may guide how the model approaches the task,
but it must not cancel or weaken layers above it.

## Prompt Overlay Scope

Allowed overlay guidance:

- domain vocabulary;
- preferred decomposition granularity;
- preferred evidence style;
- project-specific examples;
- product/runtime philosophy;
- operator-facing tone;
- known local anti-patterns;
- preferred tradeoff framing.

Disallowed overlay guidance:

- bypass required output markers;
- broaden allowed paths;
- ignore validation failures;
- suppress review gates;
- skip evidence or trace anchors;
- mutate canonical specs outside the selected scope;
- replace the core supervisor prompt;
- hide errors or blockers from run logs.

## Candidate Policy Artifact

Runtime implementation should define a declarative policy, tentatively:

```text
tools/supervisor_prompt_policy.json
```

Candidate shape:

```json
{
  "artifact_kind": "supervisor_prompt_policy",
  "schema_version": 1,
  "profiles": [
    {
      "profile_id": "default",
      "authority": "project",
      "prompt_extension_path": "tools/supervisor_prompts/default.md"
    }
  ],
  "non_overridable_invariants": [
    "protocol_markers_required",
    "allowed_paths_required",
    "review_gates_required",
    "evidence_semantics_required",
    "artifact_contract_validation_required"
  ]
}
```

Prompt extension files should be plain Markdown so they can be reviewed in PRs.

## Candidate CLI Surface

Runtime implementation may add:

```text
--supervisor-prompt-profile <profile_id>
--supervisor-prompt-extension-file <path>
```

The profile flag selects a policy-defined prompt extension. The file flag may be
useful for local experiments, but should be constrained to read-only prompt
input and recorded as non-canonical unless promoted into policy.

## Run Log Provenance

Every supervisor run that uses an overlay should record provenance:

```json
{
  "prompt_profile_id": "swift_product_runtime",
  "prompt_extension_path": "tools/supervisor_prompts/swift_product_runtime.md",
  "prompt_extension_sha256": "...",
  "prompt_overlay_authority": "project",
  "core_prompt_overridden": false
}
```

This makes behavior changes debuggable. If two supervisor runs produce different
quality, the active prompt overlay is visible alongside model, target, run kind,
and validation results.

## Validation Strategy

Runtime implementation should validate that:

- selected profiles exist in policy;
- prompt extension files stay under approved paths;
- overlay text is non-empty when selected;
- overlay provenance is written to run logs;
- hard invariants remain present in assembled prompts;
- raw system prompt replacement is unavailable by default.

Tests should cover both successful profile use and rejection of invalid overlay
paths or missing profiles.

## Relationship To Existing Architecture

Prompt overlays fit the multi-service factory model as an operator-facing
control surface:

```text
operator intent
  -> prompt overlay profile
  -> supervisor run
  -> reviewable artifact/output
```

They should complement, not replace:

- node-specific prompts;
- conversation memory;
- proposal sources;
- review feedback policy;
- model usage telemetry.

## Future Follow-Ups

- Add `tools/supervisor_prompt_policy.json`.
- Add `tools/supervisor_prompts/*.md`.
- Add supervisor CLI flags and prompt assembly logic.
- Add run-log prompt overlay provenance.
- Add graph/viewer surfaces for active prompt profile and prompt drift.
- Allow ContextBuilder/SpecSpace to select approved prompt profiles.

## Acceptance Criteria

- Prompt overlays are described as additive, not replacing core supervisor
  prompt authority.
- Non-overridable supervisor invariants are named.
- Candidate policy, CLI, and run-log provenance are defined.
- Runtime implementation remains out of scope for this proposal-only slice.
