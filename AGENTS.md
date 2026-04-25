# AGENTS.md

See [CONSTITUTION.md](/Users/egor/Development/GitHub/0AL/SpecGraph/CONSTITUTION.md) for the runtime governance model used to grow SpecGraph during bootstrap.

## Repository rules
- Merge in main branch ONLY  via Pull (Merge) Request on GitHub
- Deliver feature changes through a dedicated branch and Pull Request; do not land feature work directly on `main`.
- Work on one spec node at a time.
- Refine specifications, not runtime code.
- Preserve stable spec IDs and terminology.
- For any change affecting SpecGraph tooling or SpecGraph specifications, do not let proposals accumulate separately from runtime realization; close the loop through `observe -> propose -> improve tools -> observe again`.
- When operating the supervisor, use the repo-local skills under [`.codex/skills`](/Users/egor/Development/GitHub/0AL/SpecGraph/.codex/skills) as the default operational wrapper before ad hoc CLI usage; especially `specgraph-supervisor`, `specgraph-supervisor-gate-review`, and `specgraph-supervisor-child-materialize`.
- Tool-related work belongs under `/tools` (including code when needed).
- Test-related work belongs under `/tests` (including test code).
- Runtime code is only allowed when it is scoped to `/tools` or `/tests`.
- Do not edit unrelated files.
- If blocked, stop and explain the blocker clearly.
