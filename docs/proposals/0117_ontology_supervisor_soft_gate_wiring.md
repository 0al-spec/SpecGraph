# Ontology Supervisor Soft Gate Wiring

RFC: SG-RFC-0117
Version: 0.1.0

## Status

Implemented

Decision scope: soft, read-only supervisor wiring for existing ontology
semantic gate evidence during ordinary targeted runs.

This document does not run prompt agents, write Ontology packages, update
ontology lockfiles, mutate canonical SpecGraph specs, accept candidate terms,
close semantic gates, or make missing semantic gate artifacts a hard supervisor
runtime blocker.

## Source Material

This proposal implements the next bounded runtime slice after
`0116_ontology_semantic_lint_input`.

Source draft:

- `docs/archive/proposal_sources/0117_ontology_supervisor_soft_gate_wiring.md`

## Summary

Ordinary supervisor runs now read the existing semantic gate artifact:

```text
runs/ontology_supervisor_semantic_gate.json
```

The run embeds an `ontology_supervisor_semantic_gate` evidence block in the run
log and a compact projection in both `selected_by_rule` and the
`decision_inspector` gate section. The wiring is soft review evidence: it never
invokes prompt agents, rebuilds ontology surfaces, writes Ontology packages, or
mutates canonical specs by itself.

When the source semantic gate is `clear`, current supervisor approval behavior
is unchanged. When the source semantic gate is `blocked` or `review_pending`,
the supervisor still runs the executor but suppresses silent `--auto-approve`
canonical sync. A structurally successful refinement is routed through the
existing `review_pending` path with the ontology gate required human action and
preserved blocking/review item ids.

When the source semantic gate artifact is missing or malformed, the run records
`source_artifact_status: missing` or `invalid` and continues without semantic
gate enforcement. This keeps the first wiring slice observable without turning
local artifact freshness into a blanket supervisor outage.

## Goals

- Add a `supervisor_semantic_gate_wiring_contract` to the semantic control
  policy.
- Read `runs/ontology_supervisor_semantic_gate.json` as supervisor run
  evidence without rebuilding it inside ordinary runs.
- Preserve gate state, outcome, required human action, blocking item ids,
  review-required item ids, and candidate item ids.
- Suppress `--auto-approve` canonical sync when the semantic gate is
  `blocked` or `review_pending`.
- Keep missing or invalid gate artifacts soft and explicit in run artifacts.
- Cover missing-artifact evidence and blocked-gate auto-approve suppression in
  focused tests.

## Non-Goals

- Prompt-agent execution or prompt-pack injection.
- Ontology package drafting or writes.
- Ontology lockfile updates.
- Automatic canonical SpecGraph mutation from ontology evidence.
- Closing semantic gates or accepting candidate terms.
- SpecSpace mutation UI.
- Hard-blocking every ordinary supervisor run on missing semantic gate
  artifacts.

## Runtime Contract

The embedded run evidence declares:

```json
{
  "artifact_kind": "ontology_supervisor_semantic_gate_run_evidence",
  "schema_version": 1,
  "proposal_id": "0117",
  "source_artifact": "runs/ontology_supervisor_semantic_gate.json",
  "source_artifact_status": "available",
  "integration_mode": "soft_review_evidence",
  "canonical_mutations_allowed": false,
  "tracked_artifacts_written": false,
  "prompt_agent_executed": false,
  "prompt_agent_execution_allowed": false,
  "gate_state": "blocked",
  "run_decision": {
    "run_action": "require_review_before_approval",
    "blocks_executor_invocation": false,
    "suppresses_auto_approve": true,
    "auto_approve_requires_gate_state": "clear"
  }
}
```

The full run log keeps the complete evidence block. `selected_by_rule` and the
`decision_inspector` keep compact projections for operator review and future
dashboards.

## Authority Boundary

This wiring may be used as supervisor run evidence and as a reason to route
successful executor output through human review before canonical approval.

The wiring may not:

- execute prompt agents;
- rebuild ontology surfaces during ordinary supervisor runs;
- write Ontology packages;
- update ontology lockfiles;
- mutate canonical specs by itself;
- mark candidate terms accepted;
- close semantic gates;
- become canonical authority for accepted terms or ontology deltas.

## Acceptance

This slice is complete when:

- `tools/ontology_semantic_control_policy.json` declares
  `supervisor_semantic_gate_wiring_contract`;
- `tools/supervisor.py` reads the existing semantic gate artifact as soft run
  evidence;
- `--auto-approve` is suppressed for `blocked` and `review_pending` ontology
  semantic gates;
- missing or malformed gate artifacts remain soft and explicit in run
  evidence;
- focused tests cover missing-artifact evidence and blocked-gate auto-approve
  suppression;
- proposal `0117` is tracked in promotion and runtime registries;
- proposal gates, DocC sync, and focused Python tests pass.

## Next Gap

```text
build_prompt_agent_ontology_context_artifact
```
