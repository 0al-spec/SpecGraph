# Tools

## Minimal Spec-Node Supervisor MVP

This repository includes a local MVP that orchestrates **specification nodes** (not tasks):

- Spec nodes live in `specs/nodes/*.yaml`.
- The supervisor script is `tools/supervisor.py`.
- Run logs are written to `runs/`.

Run locally:

```bash
python tools/supervisor.py
```

The supervisor loop is:

`pick spec gap -> refine spec -> validate -> update state`

Supervisor modes:

- Default: pick the next eligible bounded refinement run.
- `--loop --auto-approve`: keep processing eligible work until the queue is empty.
- `--resolve-gate SPEC_ID --decision ...`: apply a human review decision.
- `--target-spec SPEC_ID --split-proposal`: run the explicit proposal-first split pass for one
  oversized non-seed spec and emit a structured artifact under `runs/proposals/` without editing
  canonical spec files.
- `--target-spec SPEC_ID --apply-split-proposal`: deterministically materialize one reviewed split
  proposal into canonical parent/child spec files and mark the proposal artifact as applied.

## Supervisor Bootstrap Runtime Troubleshooting

When a `supervisor` run behaves unexpectedly, debug it in this order:

1. Check `runs/latest-summary.md`.
   It is the fastest operator-facing snapshot and shows:
   - `outcome`
   - `gate_state`
   - `validation_errors`
   - `executor_environment_issues`
   - `executor_environment_primary_failure`
   - `required_human_action`
2. If the summary suggests an environment problem, open the full run log in `runs/<RUN_ID>.json`.
   The run payload preserves:
   - raw `stdout`
   - raw `stderr`
   - structured `executor_environment`
   - derived `graph_health`
3. Only treat the run as a spec-quality problem when
   `executor_environment_primary_failure: no`.
   If it is `yes`, fix the runtime first and rerun `supervisor`.

### Expected Child Executor Profiles

Nested `codex exec` runs are intentionally constrained and deterministic. `supervisor` now uses named
execution profiles instead of one implicit child runtime:

- `standard`
  - model: `gpt-5.4`
  - reasoning effort: `xhigh`
  - timeout: `420s` base and effective timeout floor for `xhigh`
- `materialize`
  - model: `gpt-5.4`
  - reasoning effort: `xhigh`
  - timeout: `720s`
  - auto-selected when run authority includes sanctioned child materialization
- `fast`
  - model: `gpt-5.4`
  - reasoning effort: `xhigh`
  - timeout: `420s` effective timeout floor for heuristic ordinary refinement runs

Timeout rule:

- `supervisor` uses the larger of the profile's base timeout and the minimum timeout floor implied by
  the profile's reasoning effort
- this keeps `xhigh` targeted refinements from inheriting the same timeout budget as lighter reasoning
  modes
- `fast` means heuristic profile selection, not low-effort reasoning; it still uses `xhigh` and a bounded
  but non-trivial timeout so useful split signals are not lost to premature executor termination

Shared child-runtime constraints:

- approval policy: `never`
- sandbox mode: `workspace-write`
- disabled features:
  - `shell_snapshot`
  - `multi_agent`
- isolated `CODEX_HOME` with copied `auth.json` and minimal generated `config.toml`
- no inherited MCP startup beyond what the isolated child home explicitly enables

If a nested run reports a different profile or timeout than the selected execution profile, treat that as
runtime drift.

Command-line overrides for nested runs:

- `--child-model` sets an explicit model for the nested codex run (for example `gpt-5.3-codex-spark`).
- `--child-timeout` sets an explicit timeout in seconds for nested child runs.
- Explicitly targeting a seed/root-like spec (`--target-spec`) without `--child-timeout` uses a 1200s default.

### Worktree Fallback Mode

`supervisor` first tries to create an isolated `git worktree`. If local ref creation is blocked by
permission-style errors (for example `cannot lock ref` or `Operation not permitted` under
`.git/refs/heads/...`), it falls back to a copied sandbox worktree under `.worktrees/`.

Interpretation:

- `git worktree` mode is preferred and should be used when the local environment allows it.
- copied worktree mode is an operational fallback, not a canonical storage mode.
- stale `.worktrees/` directories are safe to delete when no run is actively using them.

### Failure Interpretation

Current nested executor environment issues are classified into these kinds:

- `transport_failure`
  - terminal backend connectivity failures such as disconnected streams, request send failures, or DNS lookup failures
- `mcp_startup_failure`
  - one or more MCP servers failed to start in the child runtime
- `state_runtime_failure`
  - child state DB or migration initialization failed
- `sandbox_permission_failure`
  - local permission or sandbox restrictions prevented the child runtime from operating normally

Important distinction:

- websocket fallback warnings by themselves are not treated as `transport_failure`
- a spec run may still end in `blocked` or another non-`done` outcome for legitimate spec reasons even when stderr contains non-terminal warnings

Runtime anomalies that should not be read as spec-quality failures:

- timeout-driven stale tails
  - if an interrupted refinement leaves `gate_state`, `last_run_id`, or similar runtime fields without an
    accepted canonical content change, treat that as runtime residue rather than evidence that the spec
    itself regressed
  - the authoritative incident record is the run log under `runs/`, not the interrupted tail
- partial worktree diffs from interrupted runs
  - edits visible only inside the copied worktree or interrupted sandbox are diagnostic artifacts until a
    canonical writeback is accepted
  - do not classify a spec as low quality merely because a timed-out run produced a partial draft diff
- profile-selection mismatch
  - if observed timeout behavior or logged profile metadata disagree with the intended execution profile,
    treat that as runtime misconfiguration or drift
  - inspect execution profile selection, reasoning-depth timeout floors, and run authority before
    concluding that the target spec is inherently blocked

Productive nonterminal results:

- `completion_status: progressed`
  - use this when the executor produced a valid canonical refinement, but the node still requires the next
    structural step such as `split_required`
  - this is not a runtime failure and should not be grouped with timeout, transport, or invalid-diff cases

### Operator Actions

Use this decision path:

- `executor_environment_primary_failure: yes`
  - repair the runtime and rerun
  - do not treat `graph_health` or queue side effects from that run as authoritative
- `executor_environment_primary_failure: no` and `gate_state: blocked`
  - treat it as a real spec/workflow blocker and follow `required_human_action`
- `executor_environment_primary_failure: no` and `gate_state: split_required`
  - treat it as an atomicity/spec-structure issue, not a runtime issue
- `completion_status: progressed`
  - treat the run as a productive refinement with required follow-up, not as a failed execution
  - use the resulting canonical diff as the new starting point for the next bounded run
- interrupted run with no accepted canonical content change
  - read `runs/latest-summary.md` and the corresponding run log first
  - if the anomaly is timeout-driven stale tail, partial worktree diff, or profile mismatch, repair the
    runtime path and rerun instead of classifying the target spec as poor quality
- `No eligible auto-refinement gaps found.`
  - this means the automatic selector found no runnable non-gated work item
  - if pending gate actions are printed, the graph still has work; resolve or redirect those gates before
    expecting the default selector to continue

### Quick Commands

```bash
python tools/supervisor.py --dry-run
python tools/supervisor.py
cat runs/latest-summary.md
```

Canonical YAML helpers for spec nodes:

```bash
python tools/spec_yaml_format.py
python tools/spec_yaml_lint.py
python tools/python_quality.py
```

Both commands default to `specs/nodes/*.yaml`. The formatter rewrites files into the
repository's canonical YAML style; the linter enforces syntax, rejects duplicate keys,
and fails when a file has drifted from canonical formatting.

`python_quality.py` mirrors the blocking `python-quality` CI job by running:

- `ruff check .`
- `ruff format --check .`

The same project-wide gate is also installed in `.pre-commit-config.yaml` as the
`python-quality` hook.

Quality tool versions are intentionally pinned to match GitHub Actions:

- `ruff==0.15.9`
- `pytest==9.0.2`
- `pyyaml==6.0.3`


## JSON Knowledge Search MVP

Use `tools/search_kg_json.py` to extract and search structured requirement statements from nested
conversation archives stored as JSON files.

Example:

```bash
python tools/search_kg_json.py "success criteria limitations" --json-dir /path/to/jsons --limit 15
```

The script traverses each JSON tree, extracts requirement-like lines, classifies them (`goal`,
`constraint`, `acceptance`, `risk`, `scope`, `assumption`), and prints ranked matches with:
- filename
- JSON path
- requirement kind
- matched text preview

Filter by kind when needed:

```bash
python tools/search_kg_json.py "acceptance evidence" --json-dir /path/to/jsons --kind acceptance
```

The tool also stores a request-response cache at `<json-dir>/.search_kg_cache.json` by default for fast repeated queries.
Use `--cache-file` to override location or `--no-cache` to disable it.

## PageIndex Conversation Search

Use `tools/search_pageindex.py` to search indexed ChatGPT conversations through the local PageIndex API.
It is the companion search tool for the PageIndex manual in `tools/docs/PAGEINDEX_SEARCH_MANUAL.md`.

Example:

```bash
python3 tools/search_pageindex.py "agent orchestration" --top-k 10 --context
```

The script expects the PageIndex API to be running on `http://localhost:8765` and uses the
`~/Development/GitHub/PageIndexInstance/results/chatgpt_dialogs/catalog.json` catalog by default.
