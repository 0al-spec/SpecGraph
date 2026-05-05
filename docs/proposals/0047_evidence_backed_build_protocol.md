# Evidence-Backed Build Protocol

## Status

Draft proposal

## Source Material

This proposal distills the expert review captured in:

- `docs/income/runs.md`

The source review is treated as input evidence, not as canonical policy by
itself. This proposal records the SpecGraph-native interpretation.

## Context

SpecGraph has reached a stage where the supervisor can repeatedly select weak
spots, produce bounded graph mutations, validate them, and open reviewable pull
requests. That makes self-hosting credible, but it also exposes a missing
governance layer.

The raw `runs/` directory contains important operational evidence:

- why a spec node was selected;
- what candidate mutation was produced;
- what validation accepted or rejected;
- what gate decision was required;
- what changed after approval.

At the same time, `runs/` is a noisy runtime workspace. It contains timestamps,
retry attempts, local paths, intermediate failures, and generated projections.
Committing all of it as source would make review harder and would confuse raw
runtime logs with canonical graph truth.

SpecGraph needs a stricter distinction:

```text
raw runtime runs
  -> curated evidence packets
  -> implementation/build readiness
  -> code/test/runtime evidence
  -> graph update
```

## Problem

Today SpecGraph has two incomplete interpretations of supervisor evidence:

1. Treat `runs/` as local noise and rely on PR descriptions to summarize what
   happened.
2. Treat `runs/` as proof and risk committing a large, unstable log directory.

Neither is enough.

If raw runs are ignored, SpecGraph loses explainability. A reviewer cannot
fully reconstruct why a change happened, which validation failed first, whether
an auto-retry recovered safely, or whether a gate decision was justified.

If raw runs are committed wholesale, the repository becomes dominated by
generated artifacts that are not canonical product state. Reviewers must sift
through local machine paths and retry residue to find the evidence that matters.

The broader implementation problem is similar. A mature spec graph should not
jump directly from `spec -> code`. It needs a governed build protocol that
answers:

- which subgraph is ready to implement;
- which nodes are semantic leaves versus implementation leaves;
- which contracts and tests are required before coding;
- which parent compositions can be assembled safely;
- which evidence must flow back into the graph after code changes.

## Goals

- Keep raw `runs/` local by default while preserving important supervisor work
  as curated, reviewable evidence.
- Define an evidence packet concept that captures the minimal proof needed for
  a PR or self-hosting step.
- Introduce the Build Protocol as the bridge from mature spec subgraphs to
  implementation work, tests, runtime evidence, and graph feedback.
- Distinguish semantic leaves, implementation leaves, and runtime-observable
  leaves.
- Define implementation readiness as a derived signal over contracts,
  dependencies, tests, invariants, side effects, and evidence.
- Define composition contracts for parent nodes so branch assembly is more than
  summing child implementations.
- Preserve risk-based ceremony: critical governance/security nodes require more
  evidence than simple adapters or documentation updates.
- Require external anchors so graph-health optimization does not replace real
  product, runtime, security, or human-review evidence.
- Keep license and source provenance explicit when reconstructing or learning
  from external systems.

## Non-Goals

- Committing all of `runs/`.
- Making raw runtime artifacts canonical graph truth.
- Implementing the Build Protocol in this proposal.
- Starting autonomous code generation from specs.
- Replacing the Implementation Work layer proposal.
- Replacing human PR review or merge boundaries.
- Defining final JSON schemas for every future artifact.

## Core Proposal

SpecGraph should treat supervisor and build evidence as a two-layer system:

1. **Raw operational evidence** lives in generated runtime artifacts such as
   `runs/*` and remains local or CI-artifact scoped by default.
2. **Curated evidence packets** are intentionally promoted summaries that can
   be committed, cited by PRs, attached to graph nodes, or consumed by viewer
   surfaces.

The rule is:

```text
Do not commit raw runs by default.
Do commit curated evidence when it is needed for audit, review, or graph state.
```

## Curated Supervisor Evidence Packet

A supervisor evidence packet should capture the smallest stable proof that a
bounded graph mutation was lawful.

Minimum fields should include:

```json
{
  "artifact_kind": "supervisor_evidence_packet",
  "schema_version": 1,
  "canonical_mutations_allowed": false,
  "tracked_artifacts_written": false,
  "evidence_kind": "supervisor_run_packet",
  "run_id": "20260505T210742Z-SG-SPEC-0030-8616d24c",
  "spec_id": "SG-SPEC-0030",
  "selection": {
    "selected_because": ["graph_gap", "maturity_pressure"],
    "source_artifacts": ["runs/graph_next_moves.json"]
  },
  "mutation": {
    "changed_files": ["specs/nodes/SG-SPEC-0030.yaml"],
    "change_class": "local_refinement",
    "diff_summary": "Strengthened boundary separation evidence."
  },
  "validation": {
    "format": "passed",
    "lint": "passed",
    "tests": "passed",
    "initial_failures": [],
    "retry_recovery": null
  },
  "gate": {
    "gate_state": "none",
    "decision": "approve",
    "review_reason": "bounded local refinement"
  },
  "raw_artifact_reference": {
    "availability": "retained_ci_artifact",
    "run_path": "runs/20260505T210742Z-SG-SPEC-0030-8616d24c.json",
    "content_sha256": "sha256:example",
    "artifact_uri": "gh-artifact://0al-spec/SpecGraph/actions/runs/example",
    "retention_expires_at": "2026-06-05T00:00:00Z"
  }
}
```

The packet is stable enough for review. The raw run remains available for deep
debugging only when a durable artifact URI and content digest are recorded. If a
raw run is not retained, the packet must say so explicitly with
`availability: "summary_only"` and must not imply that deep raw-run recovery is
possible after local workspace or CI retention expiry.

## Build Protocol

SpecGraph should not wait for the entire graph to become perfect before code
exists. Instead, it should move through frontiers:

```text
specification frontier
  -> implementation frontier
  -> composition frontier
  -> runtime evidence frontier
```

The Build Protocol should define how a mature subgraph is converted into code:

1. Select an implementation-ready subgraph.
2. Freeze or identify the graph snapshot used for the build decision.
3. Generate or verify implementation contract packs for selected leaves.
4. Implement bounded leaves.
5. Run unit, contract, and integration tests.
6. Attach code/test/runtime evidence back to the graph.
7. Recompute parent composition readiness.
8. Repeat until root-level scenarios and runtime anchors are satisfied.

This is not pure bottom-up construction. The protocol should combine:

- top-down skeleton and architecture boundaries;
- bottom-up implementation of ready leaves;
- middle-out integration and composition checks.

## Leaf Taxonomy

SpecGraph should distinguish at least three leaf meanings:

- `semantic_leaf`: no further useful conceptual decomposition is currently
  modeled in the graph.
- `implementation_leaf`: bounded enough to implement as code with clear
  inputs, outputs, invariants, dependencies, and tests.
- `runtime_leaf`: observable enough to verify with runtime evidence after
  implementation.

Only implementation-ready leaves should be handed to coding agents.

## Implementation Readiness

Implementation readiness should be a derived signal, not a manual label.

Example shape:

```json
{
  "spec_id": "SG-SPEC-0123",
  "implementation_readiness": {
    "status": "ready_to_implement",
    "score": 0.91,
    "blockers": [],
    "required_artifacts": {
      "contract": "present",
      "tests": "present",
      "invariants": "present",
      "dependencies": "resolved",
      "side_effects": "declared",
      "failure_modes": "declared",
      "security_policy": "present",
      "observability": "present"
    }
  }
}
```

Blocked nodes should name why they are blocked:

- `blocked_by_missing_contract`;
- `blocked_by_missing_tests`;
- `blocked_by_unstable_parent`;
- `blocked_by_unresolved_dependency`;
- `blocked_by_undeclared_side_effects`;
- `blocked_by_missing_failure_modes`;
- `blocked_by_missing_runtime_evidence_boundary`.

## Implementation Contract Pack

Each implementation-ready leaf should have a contract pack before code is
generated.

Minimum contract dimensions:

- target spec node;
- behavior summary;
- inputs and outputs;
- dependencies;
- invariants;
- failure modes;
- negative cases;
- side effects;
- test requirements;
- observability events or evidence expectations;
- forbidden mutations or forbidden capabilities.

The contract pack is the bounded handoff to an implementation agent. The agent
should not need authority over the whole graph to implement one leaf.

## Parent Composition Contract

A parent node is not just the sum of child implementations.

When children become implemented, the parent needs its own composition contract:

- child set being composed;
- cross-child invariants;
- integration tests;
- ordering or lifecycle expectations;
- evidence writeback rules;
- failure behavior at component boundaries.

Many important bugs occur at child boundaries. Composition contracts keep those
bugs visible as graph work rather than accidental implementation detail.

## Implementation Frontier

The first derived surface for the Build Protocol should be an implementation
frontier:

```json
{
  "artifact_kind": "implementation_frontier",
  "schema_version": 1,
  "canonical_mutations_allowed": false,
  "tracked_artifacts_written": false,
  "generated_at": "2026-05-06T00:00:00Z",
  "source_snapshot": {
    "graph_ref": "main",
    "graph_digest": "sha256:example"
  },
  "frontier": [
    {
      "spec_id": "SG-SPEC-0123",
      "kind": "implementation_leaf",
      "readiness": 0.94,
      "priority": 0.88,
      "reasons": [
        "contract_complete",
        "dependencies_resolved",
        "unblocks_parent:SG-SPEC-0200",
        "deterministic_tests_available"
      ]
    }
  ],
  "blocked": [
    {
      "spec_id": "SG-SPEC-0150",
      "reasons": [
        "missing_failure_modes",
        "parent_contract_unstable"
      ]
    }
  ]
}
```

Ranking should not be pure topology. It should consider:

- readiness score;
- dependency-unblocking value;
- risk reduction;
- graph centrality;
- volatility;
- unresolved assumptions;
- security or governance sensitivity.

## SCC and Component Handling

Implementation scheduling must not assume that useful leaves always exist.

If a subgraph has cycles, the Build Protocol should:

1. detect strongly connected components;
2. collapse the SCC into a temporary implementation component;
3. define the component boundary first;
4. split implementation internally after the component boundary is stable.

This prevents the scheduler from looping forever while looking for a nonexistent
leaf.

## Risk-Based Ceremony

Evidence requirements should be proportional to risk.

High-ceremony examples:

- security boundaries;
- graph mutation semantics;
- supervisor authority;
- agent permission models;
- irreversible canonical transitions.

Lower-ceremony examples:

- documentation-only updates;
- cosmetic viewer labels;
- simple adapters with bounded tests;
- generated index projection with no canonical mutation.

No change should have zero evidence, but not every change needs the same amount
of evidence.

## External Anchors

SpecGraph must not optimize only for its own graph-health metrics.

Build and supervisor evidence should eventually anchor to:

- user scenarios;
- integration tests;
- runtime behavior;
- security properties;
- external consumer observations;
- human review;
- deployment or production telemetry when available.

These anchors keep graph maturity from becoming a self-referential score.

## Source and License Provenance

When SpecGraph reconstructs, imports, or learns from external systems, evidence
packets and future contract packs should preserve source provenance:

```json
{
  "source_type": "open_source_repository",
  "license": "MIT",
  "copied_code_used": false,
  "copied_code_policy": "not_used_without_explicit_license_review",
  "clean_room_required": false,
  "allowed_use": ["public_api_shape", "behavioral_specification"]
}
```

For proprietary or unclear sources, the default should be conservative:

```json
{
  "source_type": "proprietary_observation",
  "license": "unknown",
  "copied_code_used": false,
  "copied_code_policy": "forbidden",
  "clean_room_required": true,
  "allowed_use": ["behavioral_compatibility_notes"]
}
```

This keeps reverse specification from becoming hidden implementation copying.
`copied_code_used` is always a boolean fact. `copied_code_policy` is the
enum-like policy field that explains whether copying is forbidden, deferred to
license review, or otherwise constrained.

## Proposed Runtime Slices

### Slice 1: Supervisor Evidence Packet Proposal

- Add a policy for curated supervisor evidence packets.
- Add a command that can distill one raw run into a stable evidence packet.
- Keep raw `runs/*` ignored by default.
- Write reviewable packets to a stable curated location such as
  `docs/evidence/supervisor-runs/<run_id>.json` until a future dedicated
  evidence store exists.
- Let PR descriptions cite the curated packet path and run id.

### Slice 2: Implementation Readiness Projection

- Add a derived artifact that classifies candidate nodes as
  `ready_to_implement`, blocked, or not applicable.
- Start with conservative rule-based blockers.
- Do not create code tasks yet.

### Slice 3: Implementation Frontier Viewer Contract

- Document the viewer-facing contract for frontier rows, blockers, risk, and
  next action.
- Keep this read-only.

### Slice 4: Contract Pack Preview

- Emit reviewable implementation contract-pack previews for selected ready
  leaves.
- Do not write code.

### Slice 5: Composition Readiness

- Project parent composition readiness from child implementation evidence and
  cross-child invariants.

## Relationship To Existing Proposals

- `0037_implementation_work_layer.md` defines Layer 2 as the bridge from specs
  to implementation work. This proposal defines evidence and readiness rules
  that make that bridge safer.
- `0039_review_feedback_learning_loop.md` already treats review comments as
  process evidence. This proposal extends the same principle to supervisor and
  build evidence.
- `0041_graph_next_moves_game_master_surface.md` can consume implementation
  frontier signals as future next moves.
- `0045_conversation_memory_exploration_vault.md` covers pre-canonical source
  memory. This proposal covers post-spec build and evidence feedback.

## Acceptance Criteria

- Raw `runs/*` remain local by default.
- The proposal defines why curated evidence packets are different from raw run
  logs.
- The proposal defines implementation readiness as a derived signal.
- The proposal distinguishes semantic, implementation, and runtime leaves.
- The proposal defines parent composition contracts.
- The proposal includes risk-based evidence ceremony.
- The proposal preserves external anchors and source/license provenance.
