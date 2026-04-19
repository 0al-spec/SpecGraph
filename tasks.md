# TODO

Active backlog only. Completed tasks were moved to [tasks_archive.md](/Users/egor/Development/GitHub/0AL/SpecGraph/tasks_archive.md).
Task numbers are preserved for traceability across commits and PRs.

## Reflective Evolution Loop

17. [inprogress] Add support for retrospective spec refactoring after a graph has already grown suboptimally, not only at creation time.
20. [todo] Introduce metric-driven signals later, using SIB, Specification Verifiability, Process Observability, Structural Observability, and related measures as derived inputs rather than canonical facts.
21. [todo] Define how metric thresholds become proposals first, and only later become normative policy in SpecGraph after human approval.

## Intent Layer


## Supervisor Trust and Governance

37. [done] Turn `review_pending` into a true pre-merge truth barrier so unapproved candidate content does not enter canonical root before approval.
38. [done] Rebuild canonical graph-health and queue derivation from accepted canonical state or first-class proposal artifacts, not from unapproved candidate worktrees.
39. [done] Make supervisor write authority default-deny so empty `allowed_paths` collapses to source-node-only scope instead of unrestricted sync authority.
40. [done] Require explicit structural authority for new spec creation so child materialization cannot occur from permissive path defaults alone.
41. [done] Ensure fallback isolation never expands child executor privileges beyond the normal execution path.
42. [done] Add atomic write and lock discipline for run logs, summaries, queues, and proposal artifacts.
43. [done] Add collision-safe run, branch, and worktree identifiers plus reserved spec-ID allocation for parallel child materialization safety.
44. [done] Harden malformed-artifact loading and executor machine protocol so missing structured outcomes or corrupted queue files fail safely.
45. [done] Move supervisor thresholds, selection priorities, mutation classes, and execution profiles into a declarative policy layer instead of Python constants.
46. [done] Add a Decision Inspector artifact that explains selection, gate, diff-classification, and queue-emission decisions from applied rules.

## Evaluator, Validation, and Benchmarking

52. [todo] Define an evaluator-loop control artifact that records chosen intervention, improvement basis, stop conditions, and escalation reasons for each reflective cycle.
53. [todo] Let evaluator choose among refine/propose/rewrite/merge/handoff actions from derived graph-health and authority constraints instead of fixed operator heuristics alone.
54. [done] Introduce typed validation findings and error classes so YAML, relation, acceptance, authority, and artifact failures stop flowing as ad hoc strings.
55. [todo] Add a safe repair contract that lets supervisor or helper tools propose bounded fixes from structured findings without silently mutating canonical truth.
56. [todo] Record supervisor performance and yield metrics as derived run artifacts so throughput, intervention cost, and graph impact can be inspected over time.
57. [todo] Add a cheap LLM bootstrap smoke benchmark that measures structural yield from a minimal seed without treating exact node text as the oracle.

## Semantic Shape and Handoff

60. [done] Define the SpecGraph-to-TechSpec handoff boundary so decomposition can stop at semantic saturation and emit downstream handoff artifacts instead of deeper graph slicing.

## Evidence Plane

62. [todo] Define telemetry evidence artifacts that link canonical nodes to runtime entities, observations, outcomes, and adoption without leaking raw telemetry into canonical specs.
63. [todo] Add viewer and inspection overlays for the evidence plane so operators can inspect runtime-backed evidence chains separately from canonical graph truth.

## Proposal Promotion

64. [done] Define the semantic boundary between informal working drafts and reviewable proposal artifacts so proposal promotion becomes a governed transition rather than a folder move.
65. [done] Define the minimal promotion packet and provenance contract for draft-to-proposal promotion, including source draft references, motivating concern, normalized title, and bounded scope.
66. [done] Clarify how repository projections such as `docs/proposals_drafts/` and `docs/proposals/` relate to graph-owned pre-spec and proposal semantics without making file layout the sole source of meaning.
67. [done] Add viewer or tooling support to inspect proposal promotion provenance and identify promoted proposals that still lack bounded source traceability.

## Deterministic Transitions

68. [done] Define normalized transition packet families such as promotion, proposal, apply, and handoff packets so validators stop inferring transition intent from free-form prose alone.
69. [done] Define deterministic transition check families for schema, legality, provenance, boundedness, authority, reconciliation, and diff-scope validation.
70. [done] Introduce a core transition validator that enforces graph-family-independent invariants for governed artifact movement.
71. [done] Define validator profiles so SpecGraph self-specs, product specs, tech specs, and later trace artifacts can share one transition engine while adding profile-specific rules.
72. [done] Add structured failure reporting for transition checks so denied promotions and applies can be explained by typed findings rather than ad hoc strings.
73. [done] Define how product-spec graphs inherit the deterministic transition framework instead of re-implementing promotion and apply semantics per product domain.

## Implementation Trace Plane

74. [done] Define graph-bound trace artifacts that link `spec_id` to code refs, test refs, PRs, commits, verification basis, and acceptance coverage without polluting canonical spec YAML.
75. [done] Define an implementation-state overlay vocabulary and derivation rules such as `unclaimed`, `planned`, `in_progress`, `implemented`, `verified`, `drifted`, and `blocked`.
76. [done] Add freshness and drift detection for implementation traces so later code changes can mark a previously verified spec as stale or drifting.
77. [done] Add viewer or report projections that derive implementation backlog and coverage views from the trace plane instead of relying only on a flat manual `tasks.md`.

## Broadness and Clustering

78. [done] Add a non-blocking refinement fan-out pressure signal that detects when a node is becoming too broad through excessive direct-child spread.
79. [done] Teach graph-health and proposal flows to distinguish healthy multi-child aggregate roles from broad hubs that are missing intermediate semantic clustering.
80. [done] Prefer regrouping or intermediate-cluster recommendations over further flat child splitting when fan-out pressure is high.

## Reflective Co-Evolution

81. [done] Define a proposal-processing posture that distinguishes `document_only`, `bounded_runtime_followup`, `synchronous_runtime_slice`, and `deferred_until_canonicalized` for implementation-relevant proposals.
82. [done] Make backlog generation treat proposal normalization, runtime realization, validation, and re-observation as one connected reflective chain instead of separate planning layers.
83. [done] Pair implementation-relevant proposal work with bounded `tools/` or `tests/` slices by default where the affected runtime surface already exists.
84. [done] Add inspection or trace artifacts that show, for each proposal, its runtime realization status, validation closure, and observation coverage.
