# Contributing to SpecGraph

SpecGraph is grown through small, reviewable graph changes. The project has accumulated a working style that matters as much as the code: observe the graph, make one bounded improvement, verify the derived surfaces, open a PR, then repeat from updated `main`.

Use [AGENTS.md](AGENTS.md) for executable agent rules. Use this file for the human-readable process, conventions, lessons learned, and durable project experience.

## Core Loop

1. Start from updated `main`.
2. Ask the graph for the next action with `make next-move` and inspect backlog pressure with `make backlog`.
3. Change one bounded thing: one spec, one proposal runtime realization, one evidence mapping class, or one viewer/data contract.
4. Rebuild the affected surfaces with Makefile shortcuts.
5. Run focused tests first, then broader checks when shared tooling or contracts changed.
6. Open a PR for every feature or graph mutation.
7. Merge only through GitHub PRs, then update local `main` before the next change.

Do not treat this as a batch-edit repository. The graph is the coordination system, so the graph should remain explainable after every PR.

## Branches and PRs

- Feature work must go through a dedicated branch and PR.
- `main` is merged only through GitHub Pull Requests.
- Keep PRs small enough that the changed graph intent can be explained in the title and summary.
- For stacked PRs, merge from the oldest PR to the newest PR.
- After each merge, update local `main`, then rebase or retarget the next PR onto `main`.
- If GitHub branch rules reject force-push for a stacked branch, do not fight the rule. Retarget the PR to `main`, verify it is clean and checks are green, then merge.
- PR descriptions should include motivation, goal, scope, validation commands, and risks.

Useful skills and commands:

- `$gh-create-pr` for creating or updating PRs.
- `$gh-review-thread-fixer` for actionable review comments.
- `$gh-merge-pr-stack` for stacked PR merge flow.

## Supervisor Runs

Prefer the repository Makefile targets over direct verbose supervisor commands:

```bash
make next-move
make backlog
make viewer-surfaces
make dashboard
make test
make test-supervisor
```

Use direct `python3 tools/supervisor.py ... --output-mode full` only when you need complete artifact stdout for diagnosis.

When running supervisor marathons:

- Keep each supervisor result in its own PR.
- Stop and investigate if a run fails validation.
- A failed first run followed by a narrower valid run is useful autonomy evidence, but repeated failure should become a tooling or policy fix.
- Rebuild and inspect derived surfaces after each meaningful graph change.
- Prefer improving the graph by following explicit backlog gaps over inventing work from conversation history.

## Graph Semantics

Topology belongs in edges and registries, not in prose. Spec text should describe owned semantics; it should not narrate graph wiring such as "this node reaches that node through this path" unless the spec is explicitly about that protocol.

Rules of thumb:

- Stable spec IDs are part of the public contract.
- A `depends_on` edge means a required dependency, not automatically a scary blocker.
- Red edge coloring should be reserved for broken references or active blockers; satisfied requirements should not alarm the viewer.
- Historical lineage is still useful evidence, but it should be visually quieter than active work.
- Large fan-out is structural pressure. Prefer semantic clusters or bounded split proposals over prose cleanup.
- When a node has reached a refinement plateau, do not keep rewriting it. Emit a split proposal or move to evidence/runtime realization.

## Proposals and Runtime Realization

Proposals are not a parking lot. If a proposal introduces a new surface or process, close the loop:

```text
observe -> propose -> improve tools -> observe again
```

Use proposals for new semantics, governance rules, viewer contracts, or runtime processes. Use runtime realization PRs when the proposal already exists and the task is to register or implement its derived surface.

Useful patterns:

- Proposal first for new capabilities such as branch rewrite, conversation memory, metric packs, or standalone deployment.
- Runtime registry update when a proposal already has implementation artifacts.
- Evidence or trace contract update when a spec is implemented but not yet explainable to the graph.

## Evidence and Backlog

Current backlog classes have specific meanings:

- `add_verification_anchors`: the spec needs explicit tests, validators, or checks connected to its trace.
- `map_acceptance_evidence`: the behavior appears accepted, but the acceptance evidence is not mapped to the spec.
- `attach_trace_contract`: a spec needs baseline trace-plane representation.
- `attach_evidence_contract`: a spec needs evidence-plane representation.
- `attach_promotion_trace`: a proposal needs promotion trace linkage.
- `runtime_realization`: a proposal or spec has semantics that need a concrete derived artifact or registry entry.

Treat these as graph health signals, not generic todo items. If a backlog row is stale, suppress or reclassify it through policy and tests instead of ignoring it manually.

## Review Feedback Loop

Code review comments are process evidence. For each actionable review thread:

- Identify the root cause: brittle marker, missing validation, stale artifact, unclear contract, unsafe assumption, or missing test.
- Fix the immediate issue.
- Add a prevention action when reasonable: regression test, validator, policy rule, documentation rule, or agent instruction.
- Reply in the thread with what changed and how it was verified.
- Close the thread through GraphQL.

Use [tools/review_feedback_policy.json](tools/review_feedback_policy.json) as the vocabulary source.

## Capturing Lessons

Treat important project experience as a first-class contribution. When a PR, supervisor run, review thread, deploy incident, viewer integration, or graph diagnosis teaches a reusable lesson, record it in this file before the knowledge stays only in chat history.

Record lessons here when they are:

- repeated enough to become a rule of thumb;
- surprising enough that another contributor would likely repeat the mistake;
- important for PR stack handling, supervisor behavior, evidence mapping, viewer contracts, deploy, metrics, or graph semantics;
- a stable human-facing process convention rather than an agent-only instruction.

If the lesson changes how agents must behave, update [AGENTS.md](AGENTS.md) as well. If the lesson changes a machine contract, add or update the relevant policy, validator, test, or viewer contract instead of documenting it only in prose.

## Generated Artifacts

Generated runtime artifacts are local by default:

- `.worktrees/`
- `runs/*`
- temporary supervisor output

Do not commit generated files just because they exist locally. Promote an artifact only when it is intentionally curated as documentation, a fixture, or a published public bundle.

Important distinction:

- Local `runs/` is useful for SpecSpace/ContextBuilder and local diagnosis.
- Published artifact bundles are generated from the current repository state and deployed separately.
- If a viewer depends on a JSON surface, document its contract under `docs/*_viewer_contract.md` or a similarly explicit file.

## Viewer and External Consumers

SpecSpace/ContextBuilder should consume documented artifacts, not infer private implementation details.

When SpecGraph adds or changes a viewer-facing surface:

- Document the JSON contract.
- Include stable field names for the viewer.
- Keep unknown future statuses pass-through friendly.
- Prefer read-only overlays first; mutation flows need a separate proposal.
- Tell the viewer developer which artifact, endpoint, and UI behavior changed.

Common viewer-facing surfaces include:

- `runs/graph_dashboard.json`
- `runs/graph_backlog_projection.json`
- `runs/implementation_work_index.json`
- `runs/metric_pack_*.json`
- `runs/spec_activity_feed.json`
- `runs/conversation_memory_*.json`

## Metrics

Metrics should be treated as diagnostic plugins or metric packs, not as hard-coded truth. SpecGraph should preserve the distinction between:

- metric source: where the method came from;
- metric pack contract: machine-readable method definition;
- metric run artifact: one computed observation at one point in time;
- proposal pressure: human-reviewable follow-up, not automatic policy.

Draft metric sources can inform the graph without becoming operational scoring models. Use authority states such as `draft_reference`, `validated_reference`, `operational`, and `deprecated` when modeling maturity.

## Deployment

Static deploy is for public read-only artifacts, not for mutating the graph.

The intended shape is:

```text
SpecGraph CI
  -> build static artifact bundle
  -> upload to hosting
  -> SpecSpace reads via HTTP-backed provider
```

The FTP/FTPS hosting root for `specgraph.tech` is not the hosting account root. Use the configured website path, and avoid deleting the landing page while deploying artifact subdirectories.

## Validation

Choose checks based on blast radius:

- JSON registry change: validate JSON and run focused supervisor tests.
- Policy or supervisor behavior: run focused tests plus `make test-supervisor`.
- Viewer-facing artifact shape: rebuild surfaces and update or add contract tests.
- CI/deploy workflow: prefer a connection check or dry-run job before upload behavior changes.
- Broad graph marathon: run `make backlog` and `make next-move` after the stack lands.

Useful baseline:

```bash
make test
make test-supervisor
make viewer-surfaces
make backlog
make next-move
```

## Practical Lessons

- Brittle string markers are a common source of false evidence gaps. Prefer stable phrases, IDs, or structured anchors.
- Live trace tests that assert `implementation_state.status = verified` must control dirty-worktree inputs, usually by stubbing `git_status_changed_files`, because local edits to declared code or test surfaces legitimately produce `in_progress`.
- If generated artifacts show old data, rebuild the specific surface before assuming the viewer is wrong.
- If `gh pr checks` reports no required checks after retargeting, verify PR state directly before merging.
- ContextBuilder often reads artifacts as raw passthrough; most data-shape bugs originate in SpecGraph, not the viewer.
- Do not let `tasks.md` become a parallel backlog. The graph should surface gaps itself.
- Conversation memory and raw exploration are inputs to graph work, but promotion into specs should remain review-first.
- Accepted risk is temporary. Revisit it when surrounding context changes.
- A PR that only changes docs can still be a feature PR if it changes the operational contract.
