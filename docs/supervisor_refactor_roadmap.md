# Supervisor Refactor Roadmap

This document records the long-running engineering roadmap for reducing the
`tools/supervisor.py` monolith. It is **engineering governance**, not a
SpecGraph semantic specification: it does not define graph behavior, lifecycle
states, artifact schemas, or product-facing runtime semantics.

Use this roadmap to sequence refactor work, interpret architecture metrics, and
keep future PRs small enough to review safely.

## Status

- Scope: `tools/supervisor.py` and its test surface.
- Mode: report-only roadmap.
- Blocking gate for new package code: `make architecture-style`.
- Trend report: `make architecture-metrics`.
- Legacy baseline: report-only; do not fail work only because the historical
  baseline is large.

## Current Baseline

Measured with `make architecture-metrics` after PR #666:

| Metric | Current value |
|---|---:|
| `architecture_gate.findings_total` | 0 |
| `new_supervisor_package.file_count` | 0 |
| `legacy_supervisor.line_count` | 60,390 |
| `legacy_supervisor.function_count` | 1,393 |
| `legacy_supervisor.top_level_function_count` | 1,352 |
| `legacy_supervisor.class_count` | 2 |
| `legacy_supervisor.top_level_assignment_count` | 668 |
| `legacy_supervisor.dict_any_signature_count` | 1,186 |
| `legacy_supervisor.isinstance_call_count` | 1,295 |
| `legacy_supervisor.functions_over_50_lines` | 221 |
| `legacy_supervisor.functions_over_100_lines` | 135 |
| `legacy_supervisor.max_function_lines` | 4,616 |
| `legacy_supervisor.max_parameter_count` | 125 |

Interpretation:

- Runtime/test health is currently carried by broad test coverage.
- Architecture health is weak in the legacy supervisor because behavior is
  concentrated in procedural top-level functions and untyped mappings.
- New supervisor package health is not yet meaningful because the package scope
  is empty; the gate is intentionally visible as a zero-file baseline.

## Invariants

- Preserve the `tools/supervisor.py` CLI contract: flags, exit codes, stdout and
  stderr behavior used by Makefile targets and operators.
- Preserve artifact contracts for `runs/*.json`, documented viewer surfaces, and
  curated evidence artifacts unless a separate proposal explicitly changes them.
- Keep `tools/supervisor.py` available as the stable facade until package code
  proves the replacement path.
- Keep each PR bounded to one seam, domain, gate, or characterization layer.
- Run focused tests first, then the broader gate matching the blast radius.
- Treat architecture metrics as trend signals, not as automatic merge blockers
  for legacy code.

## Methodology

1. Identify the observable contract before changing internals.
2. Add or name characterization coverage for the behavior being preserved.
3. Extract one seam behind the existing facade.
4. Move filesystem, subprocess, policy loading, and artifact writing to visible
   boundaries.
5. Move domain decisions into typed values, domain objects, or protocols.
6. Keep YAML/JSON dictionaries at I/O boundaries with explicit serialization.
7. Re-run the relevant Make target, focused tests, `make architecture-style`, and
   `make architecture-metrics`.

This is inspired by Elegant Objects, adapted to Python pragmatically. The goal is
not a literal ban on functions. The goal is that important behavior belongs to
named domain abstractions instead of anonymous dictionaries and procedural
branches.

## Phases

### Phase 0: Safety Net

- Keep the architecture gate scoped to new package code.
- Expand characterization coverage before extracting shared behavior.
- Add golden or snapshot tests for high-value artifact contracts where useful.
- Keep `tests/test_supervisor.py` working while package seams are introduced.

Exit criteria:

- `make architecture-style` passes.
- `make architecture-metrics` emits valid JSON.
- `make test-supervisor` and focused contract tests pass for touched behavior.

### Phase 1: Package Skeleton

Create package seams under:

```text
src/specgraph/supervisor/
```

Expected eventual areas:

```text
cli/
policy/
spec/
run/
gate/
proposal/
executor/
specpm/
metrics/
agent/
consumer/
memory/
```

Important adjustment to the original plan: do **not** mechanically move the
entire legacy file into the package first. Extract small modules from behind the
stable `tools/supervisor.py` facade.

### Phase 2: Policy Catalog

First high-value seam:

- Replace duplicated `load_*_policy()`, `*_policy_path()`, and
  `*_policy_lookup()` clusters with a shared policy catalog.
- Remove import-time policy loading from new package code.
- Keep policy reads lazy and explicit.
- Preserve current policy artifact paths and digest behavior.

Expected benefit:

- Less import-time work.
- Fewer duplicated policy validators.
- A clear injection point for tests that currently monkeypatch module globals.

### Phase 3: Domain Waves

Extract by domain, one wave at a time:

| Wave | Domain | Candidate abstractions |
|---|---|---|
| 3.1 | Spec graph | `SpecNode`, `SpecGraph`, `Subtree`, `EligibleNodes` |
| 3.2 | Runs | `RefinementPass`, `RunLog`, `RunId`, `Worktree` |
| 3.3 | Executor | `CodexCommand`, `ExecutionProfile`, `ChildCodexHome`, `ExecutorAdapter` |
| 3.4 | Gates | `ReviewGate`, `GateDecision`, `StalledRun`, `Salvage` |
| 3.5 | Proposals | `SplitProposal`, `ProposalQueue`, `MaterializedSplit` |
| 3.6 | Overlays | `Overlay` protocol for build/write surfaces |
| 3.7 | Consumers | SpecPM, metrics, external consumers, agent passports, conversation memory |

Recipe per wave:

1. Find the function cluster by prefix and shared data flow.
2. Identify the dictionary passed through the cluster.
3. Introduce a typed value/object at the package boundary.
4. Preserve `to_payload()` / `from_payload()` behavior for artifact
   compatibility.
5. Move focused tests toward `tests/supervisor/` without breaking the legacy
   fixture.

### Phase 4: Declarative Dispatch

After enough domain seams exist:

- Move CLI parsing and action selection toward a declarative action table.
- Represent standalone modes as `SupervisorAction`-like objects.
- Keep `tools/supervisor.py` as compatibility facade until all Make targets and
  docs are proven.

### Phase 5: Consolidation

- Move remaining tests out of the monolithic `tests/test_supervisor.py`.
- Tighten `make architecture-style` from empty/new package baseline to the whole
  extracted package.
- Reduce the legacy facade toward a small wrapper only after behavior has moved.

## Metrics To Watch

Use:

```bash
make architecture-metrics
```

Primary trend metrics:

- `legacy_supervisor.line_count`
- `legacy_supervisor.top_level_function_count`
- `legacy_supervisor.functions_over_100_lines`
- `legacy_supervisor.max_function_lines`
- `legacy_supervisor.max_parameter_count`
- `legacy_supervisor.dict_any_signature_count`
- `legacy_supervisor.isinstance_call_count`
- `new_supervisor_package.file_count`
- `architecture_gate.findings_total`

Healthy direction:

- legacy counts decrease gradually;
- new package file count increases with focused modules;
- gate findings remain zero for new package code;
- function size and parameter count maxima decrease over time.

## Risks

- Tests import `tools/supervisor.py` by path and monkeypatch module globals.
  Early seams need compatibility fixtures and explicit dependency injection.
- YAML/JSON artifact drift is the highest compatibility risk. Keep payload
  serialization explicit and covered.
- Import-time behavior is easy to reintroduce accidentally. Keep constructors
  cheap and package imports inert.
- Over-applying EO rules can produce unnatural Python. Prefer readable domain
  objects and protocols over dogma.

## Exit Criteria

The roadmap can be considered complete when:

- `tools/supervisor.py` is a small compatibility facade.
- Shared policy loading is lazy, explicit, and centralized.
- Major domains live under `src/specgraph/supervisor/`.
- Monolithic test coverage has moved into domain-oriented test files.
- `make architecture-style`, `make architecture-metrics`, `make test-supervisor`,
  and `make test` pass from the package-backed implementation.
