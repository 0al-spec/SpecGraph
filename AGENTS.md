# AGENTS.md

See [CONSTITUTION.md](CONSTITUTION.md) for the runtime governance model used to grow SpecGraph during bootstrap.
See [CONTRIBUTING.md](CONTRIBUTING.md) for accumulated project workflow, operational lessons, and human-readable contribution rules.

## 0AL Local Ops Logging

For cross-repo observations, coordination tasks, blockers, or handoffs, write a
local ops entry through the `.0al` logging CLI when it is available:

```bash
../.0al/scripts/0al-log.py --project specgraph --kind note --owner unclassified \
  --title "<short title>" \
  --text "<what happened, what is needed, and any suggested next action>"
```

Use `.0al` only for coordination. Canonical SpecGraph changes belong in this
repository. Do not edit `../.0al/tasks.md` or `../.0al/decisions.md` directly
unless the user explicitly asks for tracker maintenance, and never write secrets,
credentials, private keys, or machine-local tokens to `.0al`.

## Repository rules
- Merge in main branch ONLY  via Pull (Merge) Request on GitHub
- Deliver feature changes through a dedicated branch and Pull Request; do not land feature work directly on `main`.
- Work on one spec node at a time.
- Refine specifications, not runtime code.
- Preserve stable spec IDs and terminology.
- For any change affecting SpecGraph tooling or SpecGraph specifications, do not let proposals accumulate separately from runtime realization; close the loop through `observe -> propose -> improve tools -> observe again`.
- When adding or changing proposal markdown, include the source draft plus the required proposal tracking material: runtime registry, promotion registry/trace, or an explicit no-runtime classification. Verify with `make proposal-tracking-gate`.
- Before assigning, reserving, or materializing a proposal ID, check for collisions across the updated local checkout, remote branches/refs, local worktrees, and open GitHub PRs. Use `make proposal-id` only after fetching and updating the checkout to current `main` (or rebasing the task branch onto `origin/main`), inspect proposal files/registries plus `git branch -a`/`git worktree list`, and query open PR metadata, changed files, and relevant diffs with `gh`; if any PR or branch already uses the candidate ID, stop and choose the next deterministic ID after synchronizing with `main`.
- When project work reveals reusable lessons, update [CONTRIBUTING.md](CONTRIBUTING.md); if the lesson changes mandatory agent behavior, update this file too.
- Keep DocC documentation synchronized with ordinary repository documentation. When changing `docs/`, `README.md`, `CONTRIBUTING.md`, `AGENTS.md`, or `tools/README.md` in a way that affects published technical guidance, update the corresponding `Sources/SpecGraph/Documentation.docc/` page or the DocC sync contract, then run `make docc-sync`.
- When addressing actionable PR review threads, treat review feedback as process evidence: classify the root cause, add or name a prevention action such as a regression test, validator, policy rule, documentation rule, or agent instruction, record verification, and only use accepted risk when prevention is intentionally deferred. Use [tools/review_feedback_policy.json](tools/review_feedback_policy.json) as the vocabulary source.
- When operating the supervisor, use the repo-local skills under [`.codex/skills`](.codex/skills) as the default operational wrapper before ad hoc CLI usage; especially `specgraph-supervisor`, `specgraph-supervisor-gate-review`, and `specgraph-supervisor-child-materialize`.
- Prefer the repository Makefile shortcuts for routine supervisor/viewer/test operations instead of direct verbose commands: `make viewer-surfaces`, `make dashboard`, `make backlog`, `make next-move`, `make spec-activity`, `make proposal-spec-trace`, `make proposal-tracking`, `make proposal-tracking-gate`, `make external-consumers`, `make external-handoffs`, `make metrics-delivery`, `make metrics-feedback`, `make metrics-source-promotion`, `make metric-signals`, `make metric-thresholds`, `make metric-packs`, `make metric-pack-drift`, `make metric-pack-adapters`, `make metric-pack-runs`, `make metric-pricing`, `make model-usage`, `make conversation-memory`, `make conversation-memory-map`, `make conversation-memory-pressure`, `make pre-spec-semantics`, `make implementation-work`, `make supervisor-evidence-packet`, `make supervisor-stalled-run-salvage`, `make factory-architecture`, `make swift-typed-tooling`, `make project-environment`, `make init-product-workspace`, `make review-feedback`, `make docc-sync`, `make publish-bundle`, `make test`, and `make test-supervisor`. Use direct `python3 tools/supervisor.py ... --output-mode full` only when a task explicitly needs the complete artifact on stdout.
- Treat generated supervisor runtime artifacts as local by default, including `.worktrees/` and `runs/*`; only intentionally curated artifacts should be promoted into tracked documentation or specification surfaces.
- Tool-related work belongs under `/tools` (including code when needed).
- Test-related work belongs under `/tests` (including test code).
- Runtime code is only allowed when it is scoped to `/tools` or `/tests`.
- Do not edit unrelated files.
- If blocked, stop and explain the blocker clearly.
