# Worktree lifecycle and recovery

Worktrees isolate active work; durable results and return points belong outside
temporary execution directories. Use the portable
[worktree-lifecycle skill](../.codex/skills/worktree-lifecycle/SKILL.md) when
creating, handing off or retiring a tree. It is engineering guidance, not a new
runtime policy, canonical transition, approval boundary or CI gate.

## Closeout

Reuse a suitable worktree before creating another. Record the task/PR, exact
path and head, persistent data, disposition and next action in the existing task
or coordination record. A pending review may justify an active tree; a failed
candidate can instead be archived with a review return point. Do not create a
new registry for routine closeout.

Inspect staged/unstaged changes, untracked and ignored files, nested worktrees,
Git reachability, symlinks and live consumers. Clean status does not cover an
ignored notebook. A failed ancestor check after squash/rebase does not prove
that the work is missing. Compare the exact merged PR head and the candidate.

Use the app archive operation for managed attached trees. For ordinary Git
trees, preserve and verify needed contents before `git worktree remove`. Retire
children before parents. Force is reserved for the explicitly authorized,
fully preserved dirty tree; recursive deletion is not a failed-remove fallback.
Keep cleanup mutations sequential and stop for newly changed state.

## Recovery observed on 27 October 2026

The local audit began with 75 existing SpecGraph checkouts and 13 additional
registrations for absent temporary paths. The initial 57 clean completed trees
were archived and removed. The remaining 17 auxiliary trees were inspected by
content rather than treated as 17 necessary development environments.

| Return handle | Finding and disposition |
| --- | --- |
| WTR-0114 | Local head `42b5d33c` and the merged #548 head `fc8f5ed6` differ only by moving one test. The top-level Python AST nodes are identical as a multiset. No production rule or assertion was missing; archive the duplicate execution tree. |
| WTR-0047 | The retry child candidate and both retry intent projections are byte-identical to the retained files under `docs/reviews/0047_authored_traceability/retry/`. The failed first attempt and pending envelope are historical state. Keep the existing publication/review boundaries; do not replay an old runtime envelope into current canonical sources. |
| WTR-0033 | Current SG-SPEC-0033 retains the typo correction and source exclusions. Its later rule records a null selection and rationale rather than the old proposed handoff. Retain the historical patch instead of restoring its older output behavior. |
| WTR-0043 | The first invariants are present in later wording. One alternative adds a stricter prohibition on topology prose, while another adds reviewer guidance. These are not an instruction to restore old maturity or pending-gate fields. Retain the stricter alternative as not adopted; revisit if the same topology-prose problem recurs. |
| WTR-0058 | Current reviewer meanings, verdict evidence requirements and SG-SPEC-0060 boundary cover the proposed confirmation prose. The extra confirmation section is a redundant historical candidate. |
| WTR-0060 | The main checkpoint contract contains the candidate's acceptance/evidence and mixed-evidence rules, with later wording corrections including `or` instead of `and`. Archive the older candidate. |
| WTR-0063 | Later cross-member handoff rules and SG-SPEC-0066 address the aggregate/evidence direction. An alternative member-admission policy is not adopted. Retain it for review if a new cluster member is proposed, without substituting it for current member responsibilities. |
| WTR-0021 | The local Specification Verifiability clarification is absent from the current metric-family catalog. It distinguishes links, declarations, execution observations/results, freshness and revision scope. Preserve it for review against proposal 0226 and current providers; this is an unpublished candidate, not proof of a runtime defect or an accepted obligation. |

The canonical YAML was not changed by this recovery. Different wording and
archived alternatives are not counted as lost features or newly accepted work.

## Retained review and data

WTR-0021 uses the existing `supervisor-stalled-run-salvage` path from proposal
0048. Its local run ID is
`worktree-recovery-20261026t2150z-sg-spec-0021`; the JSON, patch and run log live
under `runs/`. The `review_salvaged_worktree_diff` action remains pending.
This is a recovery artifact builder, not a new model/executor run, and its
blocked recovery status is not an observation of a new infrastructure failure.
The recorded worktree path is historical after archival; use the retained patch
and archive mapping to inspect or restore the candidate.

The portable skill does not authorize adoption. Review only the still-relevant
semantic delta, then use normal validation and a focused PR. Do not apply the
whole old file, lifecycle metadata or historical maturity as a shortcut.

The live SpecDraft notebook moved to the primary checkout's Git-ignored
`conversation_memory/sketches/hypercode-conversation-poc`. All 50 file hashes
and all 16 history entries matched; a fresh CLI process recovered the same
source-attributed notes. The loopback preview uses that stable location.
Notebook contents, raw recovery patches and full archives stay local.

Full worktree archives include ignored files and preserve branches/heads. Nested
registered trees are archived separately, with parent/child mappings. The local
recovery manifest includes restoration instructions and the three return points:
WTR-0021 for active review, WTR-0043 for recurring topology prose, and WTR-0063
for a future cluster-member proposal. None of these return points admits evidence
or creates canonical subjects.

The skill and operator closeout address the observed retention problem. This
slice adds no automatic supervisor garbage collector. The salvage CLI's generic
default run ID is recorded separately as a potential artifact-collision issue;
this recovery used an explicit task-specific ID.
