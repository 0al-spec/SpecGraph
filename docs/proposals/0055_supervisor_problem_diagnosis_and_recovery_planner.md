# Supervisor Problem Diagnosis and Recovery Planner

## Status

Draft proposal

## Source Material

This proposal captures the operator decision to make supervisor operation more
deterministic, autonomous, and focused on problem detection plus bounded
problem solving.

Source draft:

- `docs/archive/proposal_sources/0055_supervisor_problem_diagnosis_and_recovery_planner.md`

## Context

SpecGraph now has enough derived surfaces for the supervisor to act with more
context:

- graph health and next-move surfaces;
- backlog projection;
- trace and evidence planes;
- proposal lane and proposal runtime;
- review feedback learning loop;
- supervisor run logs and performance artifacts.

The supervisor can already refine specs, emit split proposals, apply approved
split proposals, resolve gates, and build viewer surfaces. However, the current
operation still depends heavily on an external operator to interpret failures
and choose recovery paths.

Recent runs showed the same pattern repeatedly:

```text
supervisor finds a real pressure
  -> run leaves gate or artifact state
  -> operator diagnoses whether it is runtime, graph, or policy
  -> operator picks deterministic repair
  -> operator adds tests or registry anchors
  -> graph returns to steady state
```

This proposal defines the missing diagnostic and recovery layer.

## Problem

Supervisor runs currently produce useful signals, but the system does not yet
have a first-class artifact that answers:

- what problem was detected;
- whether the problem is a runtime failure, graph defect, process gap, or
  governance boundary;
- what root cause is most likely;
- which deterministic recovery actions are safe;
- which actions are blocked by policy, authority, or missing context;
- what validation should prove the recovery worked;
- whether the same failure should become a new prevention rule.

Without that layer, autonomy stays limited. The supervisor can generate
candidates, but a human or coding agent still has to provide most of the control
logic.

## Goals

- Define a typed problem-diagnosis artifact for supervisor operation.
- Define an initial vocabulary of recurring problem classes.
- Map diagnosed problems to deterministic recovery plans when safe.
- Preserve hard stops for governance, ontology, policy, authority, repeated
  failure, and unsafe canonical mutation.
- Make problem solving auditable through root cause, prevention, and validation
  fields.
- Keep one bounded concern per recovery action.
- Support future SpecSpace display without requiring SpecSpace to read raw run
  logs directly.
- Improve supervisor autonomy without making it a merge authority or policy
  authority.

## Non-Goals

- Implementing a full `while true supervisor.run()` autopilot.
- Allowing the supervisor to merge PRs.
- Allowing silent ontology or policy changes.
- Automatically approving review gates.
- Bypassing proposal-first governance for constitutional changes.
- Building hosted multi-tenant orchestration.
- Implementing SpecSpace UI in this proposal.
- Replacing human-in-the-loop review.

## Core Proposal

Introduce a bounded diagnostic layer around supervisor operation:

```text
observe
  read latest run, target spec, graph surfaces, gate state, worktree state

diagnose
  classify detected problems with typed vocabulary and evidence

plan
  choose deterministic recovery action, one bounded LLM run, or hard stop

validate
  name the checks that must prove recovery

report
  emit reviewable problem-solving artifact
```

This layer should be advisory at first. It may recommend and prepare safe
actions, but canonical mutation remains governed by existing supervisor,
proposal, and review gates.

## Artifact Contract

The first viewer-facing artifact should be derived and reviewable:

```text
runs/supervisor_problem_diagnosis.json
```

Suggested shape:

```json
{
  "artifact_kind": "supervisor_problem_diagnosis",
  "schema_version": 1,
  "generated_at": "2026-05-23T00:00:00Z",
  "target": {
    "spec_id": "SG-SPEC-0066",
    "run_id": "20260523T070623Z-SG-SPEC-0066-a82e00c6"
  },
  "diagnosis": {
    "overall_status": "actionable",
    "detected_problem_count": 1,
    "hard_stop": false
  },
  "detected_problems": [
    {
      "problem_id": "split_required_candidate_without_proposal_path",
      "problem_class": "graph_recovery",
      "severity": "actionable",
      "root_cause": "A rejected candidate hit atomicity, while the canonical node remained bounded.",
      "evidence": [
        "latest_run.outcome=split_required",
        "last_validator_results.atomicity=false",
        "canonical acceptance count <= atomicity limit"
      ],
      "recommended_action": "emit_split_proposal_from_atomicity_pressure",
      "deterministic": true,
      "requires_human_review": true
    }
  ],
  "safe_next_actions": [
    {
      "action_id": "emit_split_proposal_from_atomicity_pressure",
      "action_kind": "deterministic_recovery",
      "command_hint": "tools/supervisor.py --target-spec SG-SPEC-0066 --split-proposal",
      "success_condition": "A proposal artifact is emitted without canonical spec mutation."
    }
  ],
  "blocked_actions": [],
  "validation_plan": [
    "focused supervisor regression tests",
    "make viewer-surfaces",
    "make backlog",
    "make next-move"
  ]
}
```

The artifact must not include raw prompt text, secrets, provider credentials,
or machine-local private tokens.

## Initial Problem Vocabulary

The first vocabulary should be small and based on observed project failures:

- `runtime_residue`: failed or blocked run left misleading canonical gate or
  metadata residue.
- `quota_or_provider_failure`: nested executor failed because of provider
  quota, transport, or account state.
- `split_required_candidate_without_proposal_path`: a rejected candidate hit
  atomicity, but canonical content is not itself oversized.
- `false_dependency_atomicity`: a deterministic graph operation creates a
  blocking dependency that is structurally a refinement or cluster relation.
- `missing_trace_contract`: a new or changed spec lacks a registry-backed trace
  contract.
- `missing_evidence_contract`: a new or changed spec lacks a complete evidence
  chain.
- `stale_queue_pressure`: proposal, refactor, or backlog pressure remains after
  the canonical issue was already resolved.
- `malformed_or_stale_artifact`: a derived artifact has the wrong shape,
  malformed JSON, stale source data, or incompatible contract version.
- `repeated_same_failure`: the same problem recurs across runs and should stop
  automation until a prevention rule is added.

Future vocabulary may expand, but the first implementation should prefer
stable, testable problem classes over broad natural-language labels.

## Recovery Planner

The recovery planner maps detected problems to allowed actions.

Examples:

| Problem | Safe deterministic action | Hard stop condition |
|---|---|---|
| `runtime_residue` | Clear failed-run residue or rerun after provider recovery | Residue changes canonical semantics |
| `quota_or_provider_failure` | Stop, report provider blocker, retry only after reset | Repeated quota failure |
| `split_required_candidate_without_proposal_path` | Emit split proposal from atomicity-pressure evidence | Split would alter ontology/policy |
| `false_dependency_atomicity` | Apply cluster/refinement-safe dependency normalization | Dependency semantics unclear |
| `missing_trace_contract` | Add registry trace contract with focused tests | Runtime implementation claim is ambiguous |
| `missing_evidence_contract` | Add evidence registry chain or classify accepted gap | Evidence ownership unclear |
| `stale_queue_pressure` | Clear scoped queue item and refresh surfaces | Active proposal still owns issue |
| `malformed_or_stale_artifact` | Rebuild surface or fail safe with contract error | Artifact is canonical input |
| `repeated_same_failure` | Stop and emit proposal or process lesson | None; repeated failure is itself a stop |

The planner should make one recommendation at a time. If multiple actions are
possible, it should prefer the smallest deterministic action that restores graph
truth without expanding scope.

## Hard Stops

The diagnosis layer must stop instead of recovering automatically when the next
step would:

- change ontology;
- change policy;
- expand supervisor authority;
- alter approval boundaries;
- rewrite stable spec IDs;
- bypass a live proposal;
- approve a review gate;
- merge a PR;
- write outside allowed paths;
- depend on unclear or missing source authority;
- repeat the same failure after a previous recovery attempt.

Hard stops should be explicit and reviewable, not silent failures.

## Problem-Solving Report

Every recovery-oriented run should be able to report:

- detected problem;
- root cause;
- prevention action;
- changed files;
- validation commands;
- graph surface delta after refresh;
- remaining gaps;
- whether a new proposal, test, validator, policy rule, documentation rule, or
  agent instruction was added.

This aligns supervisor operation with the review-feedback policy: review and
runtime failures are process evidence, not just one-off bugs.

## SpecSpace Boundary

SpecSpace should eventually be able to display the diagnosis artifact as a
read-only operator surface:

- current problem class;
- severity;
- safe next action;
- hard stop reason;
- validation status;
- last recovery result.

SpecSpace should not infer these states from raw run logs. It should consume a
documented derived artifact when one exists.

## Implementation Sequence

Suggested follow-up PRs:

1. Add the proposal and source draft.
2. Add a policy file for problem vocabulary and recovery action vocabulary.
3. Build `runs/supervisor_problem_diagnosis.json` for latest run plus selected
   target.
4. Add deterministic recognizers for the first three observed classes:
   `runtime_residue`, `quota_or_provider_failure`, and
   `split_required_candidate_without_proposal_path`.
5. Add recovery planner output without automatic mutation.
6. Add focused deterministic fixers one by one.
7. Add SpecSpace viewer contract after the artifact stabilizes.

## Safety Rules

- Diagnosis artifacts are derived surfaces, not canonical graph truth.
- Recovery planning is advisory until an explicit deterministic command is
  invoked.
- The planner may recommend a bounded LLM run, but it should not loop
  indefinitely.
- The planner must preserve one bounded concern per action.
- The planner must prefer deterministic utilities over LLM calls when the
  repair is mechanical.
- All new deterministic recovery actions need regression tests.
- If a lesson changes mandatory agent behavior, update `AGENTS.md`; otherwise
  record reusable operational experience in `CONTRIBUTING.md`.

## Acceptance Criteria

- The proposal defines supervisor problem diagnosis as a first-class derived
  layer.
- The proposal names an initial typed problem vocabulary based on observed
  failures.
- The proposal defines a recovery planner boundary without granting merge,
  policy, or approval authority.
- The proposal includes a candidate artifact contract for
  `runs/supervisor_problem_diagnosis.json`.
- The proposal defines hard stops and non-goals for safe autonomy.
- The proposal defines a future SpecSpace boundary without implementing UI.
- The proposal has a bounded source draft in `docs/archive/proposal_sources/`.
