# TODO

Active backlog only. Completed tasks were moved to [tasks_archive.md](/Users/egor/Development/GitHub/0AL/SpecGraph/tasks_archive.md).
Task numbers are preserved for traceability across commits and PRs.

## Reflective Evolution Loop

17. [inprogress] Add support for retrospective spec refactoring after a graph has already grown suboptimally, not only at creation time.
20. [todo] Introduce metric-driven signals later, using SIB, Specification Verifiability, Process Observability, Structural Observability, and related measures as derived inputs rather than canonical facts.
21. [todo] Define how metric thresholds become proposals first, and only later become normative policy in SpecGraph after human approval.
22. [todo] Add viewer-facing overlays or reports for graph health so oversized or weakly linked regions are visible without reading raw run logs.
23. [todo] Add longitudinal graph-health reporting so repeated structural problems can be seen as trends rather than isolated failures.

## Proposal Lane

29. [todo] Add a tracked proposal lane between canonical spec nodes and ephemeral runtime artifacts so `supervisor` can grow proposal subgraphs without mutating canonical truth.
30. [todo] Define proposal-lane node semantics, including stable provisional IDs, authority or approval state, and lineage between proposal nodes and canonical nodes.
31. [todo] Let `supervisor` autonomously create and refresh tracked proposal nodes while keeping canonical writeback behind explicit review/apply flow.
32. [todo] Extend graph and viewer projections so proposal-lane nodes can be shown as an overlay or secondary layer on top of the canonical graph.

## Intent Layer

33. [todo] Define an intent-facing layer and mediated discovery path between raw user goals and canonical SpecGraph specs.
34. [todo] Distinguish `UserIntent` and `OperatorRequest` from canonical `spec` and proposal-lane nodes.
35. [todo] Add a bounded operator-request bridge so GUI selections and chat instructions can steer one supervisor run without mutating canonical specs directly.
36. [todo] Define how mediator outputs become canonical specs or proposals through reviewable supervisor-driven refinement instead of raw chat-to-spec mutation.

## Supervisor Trust and Governance

37. [todo] Turn `review_pending` into a true pre-merge truth barrier so unapproved candidate content does not enter canonical root before approval.
38. [todo] Rebuild canonical graph-health and queue derivation from accepted canonical state or first-class proposal artifacts, not from unapproved candidate worktrees.
39. [todo] Make supervisor write authority default-deny so empty `allowed_paths` collapses to source-node-only scope instead of unrestricted sync authority.
40. [todo] Require explicit structural authority for new spec creation so child materialization cannot occur from permissive path defaults alone.
41. [todo] Ensure fallback isolation never expands child executor privileges beyond the normal execution path.
42. [todo] Add atomic write and lock discipline for run logs, summaries, queues, and proposal artifacts.
43. [todo] Add collision-safe run, branch, and worktree identifiers plus reserved spec-ID allocation for parallel child materialization safety.
44. [todo] Harden malformed-artifact loading and executor machine protocol so missing structured outcomes or corrupted queue files fail safely.
45. [todo] Move supervisor thresholds, selection priorities, mutation classes, and execution profiles into a declarative policy layer instead of Python constants.
46. [todo] Add a Decision Inspector artifact that explains selection, gate, diff-classification, and queue-emission decisions from applied rules.
