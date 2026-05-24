# Supervisor Problem Diagnosis Viewer Contract

## Purpose

`runs/supervisor_problem_diagnosis.json` is the reviewable diagnostic surface
produced by the supervisor. SpecSpace and operators should consume it as a
read-only summary of detected problems and safe recovery options rather than
inferring those states from raw run logs.

This contract is governed by:

- proposal: `docs/proposals/0055_supervisor_problem_diagnosis_and_recovery_planner.md`
- policy: `tools/supervisor_problem_diagnosis_policy.json`

## Source

The artifact path is reserved at:

```text
runs/supervisor_problem_diagnosis.json
```

The CLI builder is:

```bash
python3 tools/supervisor.py --build-supervisor-problem-diagnosis
```

By default it diagnoses the latest available supervisor run log under `runs/`.
Operators may pass `--supervisor-run-path <path-or-run-id>` to diagnose a
specific run and `--target-spec SG-SPEC-XXXX` to force the target identity used
for canonical context checks.

The artifact is derived. It is not canonical graph truth and must not be
treated as an approval, gate decision, or merge authority signal.

## Boundary

- The supervisor owns detection vocabulary and the diagnosis artifact.
- The diagnosis artifact must not mutate canonical specs, approve review gates,
  merge PRs, or change ontology, policy, or supervisor authority.
- SpecSpace and other viewers must consume the diagnosis artifact, not raw run
  logs.
- The artifact must not include raw prompt text, secrets, provider credentials,
  or machine-local private tokens.

## Required Fields

```json
{
  "artifact_kind": "supervisor_problem_diagnosis",
  "schema_version": 1,
  "canonical_mutations_allowed": false,
  "tracked_artifacts_written": false,
  "generated_at": "2026-05-23T00:00:00Z",
  "target": {
    "spec_id": "SG-SPEC-XXXX",
    "run_id": "<supervisor-run-id>"
  },
  "diagnosis": {
    "overall_status": "clean|actionable|hard_stop|insufficient_evidence",
    "detected_problem_count": 0,
    "hard_stop": false
  },
  "detected_problems": [
    {
      "problem_id": "<per-run-unique-id>",
      "problem_class": "<one of policy.problem_classes[].id>",
      "severity": "informational|actionable|blocking",
      "root_cause": "<short human-readable cause>",
      "evidence": ["<observed evidence pointer>"],
      "recommended_action": "<one of policy.safe_action_vocabulary>",
      "deterministic": true,
      "requires_human_review": true
    }
  ],
  "safe_next_actions": [
    {
      "action_id": "<one of policy.safe_action_vocabulary>",
      "action_kind": "deterministic_recovery|bounded_llm_run|stop",
      "command_hint": "<shell command suggestion>",
      "success_condition": "<observable result>"
    }
  ],
  "blocked_actions": [
    {
      "action_id": "<one of policy.safe_action_vocabulary>",
      "hard_stop_reason": "<one of policy.hard_stop_reasons>"
    }
  ],
  "validation_plan": [
    "<command or check>"
  ],
  "policy_reference": {
    "artifact_path": "tools/supervisor_problem_diagnosis_policy.json"
  }
}
```

`problem_id` is per-run unique. `problem_class` must match one of the
enumerated vocabulary values in
[tools/supervisor_problem_diagnosis_policy.json](../tools/supervisor_problem_diagnosis_policy.json).

The builder may also include:

- `source`: sanitized source-run metadata such as `artifact_path`,
  `source_status`, `content_sha256`, `schema_errors`, and `local_path_redacted`.
- `insufficient_evidence`: machine-readable reasons explaining why the builder
  refused to classify a sparse, stale, or under-evidenced run as clean.

Viewers should treat `source.source_status = schema_incomplete` and non-empty
`insufficient_evidence[]` as diagnostic warnings, not as recovery commands.

## UI Guidance

- Show `diagnosis.overall_status` as the primary status.
- Show `diagnosis.detected_problem_count` and the top `detected_problems[0]`
  summary.
- Show `safe_next_actions[0]` as the recommended next step.
- If `diagnosis.hard_stop` is true, do not offer recovery actions; surface the
  matching `blocked_actions[].hard_stop_reason`.
- Treat `requires_human_review: true` as a hard rule — never auto-execute.

## Non-Goals

- No autopilot loop.
- No PR creation, PR merge, or gate approval.
- No canonical spec mutation.
- No SpecSpace UI implementation in this contract.
