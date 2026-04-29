# AGENTS.md

See [CONSTITUTION.md](CONSTITUTION.md) for the runtime governance model used to grow SpecGraph during bootstrap.

## Repository rules
- Merge in main branch ONLY  via Pull (Merge) Request on GitHub
- Deliver feature changes through a dedicated branch and Pull Request; do not land feature work directly on `main`.
- Work on one spec node at a time.
- Refine specifications, not runtime code.
- Preserve stable spec IDs and terminology.
- For any change affecting SpecGraph tooling or SpecGraph specifications, do not let proposals accumulate separately from runtime realization; close the loop through `observe -> propose -> improve tools -> observe again`.
- When addressing actionable PR review threads, treat review feedback as process evidence: classify the root cause, add or name a prevention action such as a regression test, validator, policy rule, documentation rule, or agent instruction, record verification, and only use accepted risk when prevention is intentionally deferred. Use [tools/review_feedback_policy.json](tools/review_feedback_policy.json) as the vocabulary source.
- When operating the supervisor, use the repo-local skills under [`.codex/skills`](.codex/skills) as the default operational wrapper before ad hoc CLI usage; especially `specgraph-supervisor`, `specgraph-supervisor-gate-review`, and `specgraph-supervisor-child-materialize`.
- Prefer the repository Makefile shortcuts for routine supervisor/viewer/test operations instead of direct verbose commands: `make viewer-surfaces`, `make dashboard`, `make backlog`, `make metrics-source-promotion`, `make implementation-work`, `make review-feedback`, `make test`, and `make test-supervisor`. Use direct `python3 tools/supervisor.py ... --output-mode full` only when a task explicitly needs the complete artifact on stdout.
- Treat generated supervisor runtime artifacts as local by default, including `.worktrees/` and `runs/*`; only intentionally curated artifacts should be promoted into tracked documentation or specification surfaces.
- Tool-related work belongs under `/tools` (including code when needed).
- Test-related work belongs under `/tests` (including test code).
- Runtime code is only allowed when it is scoped to `/tools` or `/tests`.
- Do not edit unrelated files.
- If blocked, stop and explain the blocker clearly.
