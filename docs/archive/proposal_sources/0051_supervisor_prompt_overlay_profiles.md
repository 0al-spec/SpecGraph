# Supervisor Prompt Overlay Profiles Source Draft

## Operator Intent

SpecGraph supervisor should let an operator provide a bounded project or user
prompt extension that guides model behavior without replacing the supervisor's
hard protocol.

The intent is to support project-specific style, domain framing, decomposition
preferences, and model-behavior guidance while preserving:

- output protocol markers;
- allowed-path and lock discipline;
- evidence and trace requirements;
- review gates;
- validation and artifact contracts.

## Working Assumptions

- The Python supervisor remains responsible for assembling the full prompt.
- Core SpecGraph invariants must remain non-overridable.
- User prompt customization is useful, but raw system prompt replacement is too
  broad for the current governance model.
- Prompt overlays must be versioned and logged so run behavior stays
  reproducible.

## Candidate Shape

```text
core supervisor invariants
  -> task protocol
  -> prompt overlay profile
  -> node-specific prompt
```

Candidate runtime controls:

```text
--supervisor-prompt-profile <profile_id>
--supervisor-prompt-extension-file <path>
```

Candidate policy:

```json
{
  "artifact_kind": "supervisor_prompt_policy",
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
    "evidence_semantics_required"
  ]
}
```

## Boundary

Prompt overlays may guide style and priorities. They must not disable the
supervisor protocol, bypass validation, weaken evidence requirements, expand
write authority, or replace the core system prompt.
