# 0182 Team Decision Log Happy-Path Repair Pack

Status: implemented.

## Problem

The product `idea_to_spec` pipeline can produce a diagnostic Team Decision Log
workspace, but the default repair chain leaves the demo in a blocked state:
some ontology gaps and product/spec candidate gaps remain unresolved until an
operator records consistent SpecSpace repair drafts and a rerun request.

That is useful for diagnostics, but it does not provide a reproducible
happy-path demo where the same workspace reaches candidate approval readiness
without hand-editing `runs/*.json`.

## Proposal

Add a review-only product workspace repair-pack materializer and a curated Team
Decision Log happy-path repair pack.

The generic materializer reads a `product_workspace_repair_pack` fixture and the
current repair-session/clarification-request artifacts, then emits standard
SpecSpace-owned state:

- `runs/idea_to_spec_repair_drafts.json`;
- `runs/idea_to_spec_repair_rerun_requests.json`.

The existing SpecGraph chain then validates and consumes that state through the
normal gates:

```bash
make product-workspace-team-decision-log-happy-path-repair-pack
```

This target builds the ordinary Team Decision Log candidate repair session,
materializes the pack into SpecSpace-owned draft/request state, runs the
requested repair-draft rerun, builds the repaired candidate promotion handoff,
and refreshes Idea Maturity with approval/promotion artifacts intentionally
absent so stale local Platform state cannot leak into the demo.

## Authority Boundary

This slice remains review-only:

- no prompt-agent execution;
- no automatic stale-state cleanup;
- no application of drafts to source artifacts;
- no canonical spec mutation;
- no candidate-source mutation;
- no Ontology package writes or lockfile writes;
- no ontology term acceptance;
- no candidate approval decision;
- no Git branch, commit, PR, merge, or read-model publication;
- no SpecSpace mutation authority expansion.

The repair pack is demo input data. It is not ontology authority and does not
make Team Decision Log part of SpecGraph system logic.

## Acceptance Criteria

- Team Decision Log repair-pack data can be materialized into SpecSpace-owned
  repair draft state and rerun request state.
- The materialized draft state passes `specspace_repair_draft_import_preview`.
- The rerun request passes `specspace_repair_rerun_request_gate`.
- The requested repair-draft rerun resolves all Team Decision Log ontology gaps
  and candidate gaps in preview/materialization.
- The repaired promotion handoff reports `ready_for_candidate_approval: true`.
- Idea Maturity reports `status: ready` and `lifecycle_state: approval_ready`
  after the happy-path target, with stale Platform approval/promotion artifacts
  excluded from that demo surface.
- No canonical specs, ontology packages, or Git state are mutated.

## Validation

- `tests/test_product_workspace_repair_pack.py`
- `make product-workspace-team-decision-log-happy-path-repair-pack`
- `make proposal-tracking-gate`
- `make docc-sync`
