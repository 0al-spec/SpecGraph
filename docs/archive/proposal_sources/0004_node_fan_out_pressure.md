# Draft: Detect Broad Nodes by Refinement Fan-out Pressure

## Idea

- Root or non-root seed-like nodes that spawn many direct child specs may indicate over-broadened concerns.
- High fan-out alone is not a hard error, but should trigger an explicit quality signal to consider an intermediate consolidation split.
- Objective is to improve graph coherence and reduce semantic leakage across many unrelated downstream specs.

## Proposed Rule (Draft)

1. Introduce a heuristic score in refinement/runtime analysis: `broadness_pressure`.
2. Compute pressure from `outgoing_refinement_count` (number of direct child specs created/declared in current neighborhood), optionally weighted by:
   - acceptance criteria count in parent
   - evidence cross-dependency density
   - number of distinct policy domains touched in child names/acceptance
3. If pressure exceeds a warning threshold (for example, >6 children or equivalent score), mark:
   - Node remains valid and accepted as-is.
   - Node is annotated as `broader_than_preferred` and a recommendation is recorded to perform an intermediate clustering split pass.
4. Recommendation shape:
   - Create 2–4 intermediate cluster specs.
   - Move each cluster's concrete children under its cluster spec.
   - Keep existing direct children only if they are tightly bound to atomic concern.

## Why this matters

- Single node with many unrelated children becomes difficult to reason about and maintain.
- Over-branching increases accidental duplicate terminology and repeated context in proposals.
- Intermediate cluster specs can restore locality: fewer unrelated edges per node, easier validation and review.

## Suggested Terminology

- `broadness_pressure`: heuristic signal (not hard validator failure)
- `intermediate_decomposition_pass`: optional follow-up refinement pass producing clustering nodes
- `must_not_split_directly`: reserved rule for explicit design constraints that disallow forced decomposition

## Open Questions

- Should threshold be absolute (e.g., >6 children) or adaptive by node kind/role?
- Should the warning include a minimum minimum-coverage rule (e.g., cluster nodes must own at least 2 children)?
- Is this signal global or profile-specific (operator-run only vs autonomous supervisor runs)?

## Minimal acceptance criteria (for later spec)

- The system emits a non-blocking warning when broadness_pressure exceeds threshold.
- Warning is tied to a recommendation artifact in the supervisor output/runtime log.
- No forced hard failure is introduced for valid specs with high fan-out.
- Optional cluster decomposition path exists for explicit follow-up run.
