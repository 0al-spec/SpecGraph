# 0154 Idea-to-Spec Promotion Gate

## Status

Implemented

## Summary

SpecGraph now has a deterministic, review-only final gate before the
idea-to-spec workflow hands materialized candidate specs to Platform.

The gate consumes:

- `pre_sib_coherence_report`;
- `candidate_repair_loop_report`;
- `candidate_spec_materialization_report`.

It emits:

- `runs/idea_to_spec_promotion_gate.json`;
- a single readiness state for Platform promotion-request handoff;
- promotion paths only when the gate is ready;
- findings for unresolved context, unsafe paths, unready repair loops, and
  unready materialization.

The original pre-SIB report may still contain findings when the materialization
uses a repair-loop preview. In that case the gate records a warning instead of
blocking, provided the repair loop is ready and no owner/operator context is
still required.

## Implementation

This slice adds:

- `tools/idea_to_spec_promotion_gate.py`;
- `make idea-to-spec-promotion-gate`;
- regression tests for ready handoff, unresolved context blocking, unsafe path
  blocking, and strict-mode failure.

The gate keeps the autonomous path explicit:

```text
candidate graph
  -> pre-SIB report
  -> repair preview
  -> materialized candidate specs
  -> promotion gate
  -> Platform promotion-request
```

## Authority Boundary

This proposal does not grant write authority.

It does not:

- execute prompt agents;
- mutate candidate source artifacts;
- mutate canonical specs;
- write Ontology packages or lockfiles;
- accept ontology terms;
- create Git branches or commits;
- open pull requests;
- publish read models;
- merge or accept candidate specs.

## Validation

- `tests/test_idea_to_spec_promotion_gate.py::test_promotion_gate_allows_resolved_repair_preview`
- `tests/test_idea_to_spec_promotion_gate.py::test_promotion_gate_blocks_unresolved_context`
- `tests/test_idea_to_spec_promotion_gate.py::test_promotion_gate_blocks_unsafe_promotion_path`
- `tests/test_idea_to_spec_promotion_gate.py::test_promotion_gate_cli_strict_exits_nonzero_for_unresolved_context`

## Follow-ups

- SpecSpace should show this gate in the Idea-to-Spec Workspace beside the
  Promotion preview lane.
- Platform can optionally consume this gate before `promotion-request`, while
  preserving its existing plan and path validation.
