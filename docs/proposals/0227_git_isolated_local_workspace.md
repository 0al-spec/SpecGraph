# Git-Isolated Local SpecGraph Workspace

## Status

Draft proposal; minimal workspace-location and candidate skill contract only.
The existing engine was probed without runtime source edits. The built-in skill,
automatic Git setup and a `specgraph init --local` command are not implemented
by this proposal. Runtime realization is `deferred_until_canonicalized`.

## Source Material

- [Operator source and bounded MVP request](../archive/proposal_sources/0227_git_isolated_local_workspace.md)
- [Retained local path-reuse observation](../evidence/0227_local_workspace_path_reuse.json)
- [Existing initializer contract](../product_workspace_initialization_viewer_contract.md)
- [Product Workspace stable mode](../product_workspace_stable_mode_guide.md)
- [Canonical Decision boundary](0220_decision_nodes_in_product_workspaces.md)

## Problem and intended result

An existing product should be able to keep its SpecGraph knowledge beside its
code without adding internal knowledge artifacts to the implementation Git
history. Reuse the existing Product Workspace and configure its location instead
of inventing another graph schema, persistence backend or generalized path layer.

The MVP uses an independent Git repository at `project/.specgraph/`, ignored by
the outer Git through its local `info/exclude`. The externally visible contract
is no changes to tracked implementation files or implementation commits.

## What the current code already supports

The retained observation pins the inspected engine commit and source digests.

| Surface | Existing behavior | MVP consequence |
| --- | --- | --- |
| `tools/supervisor.py`: root globals | `ROOT = Path.cwd()`; specs, runs, state and Supervisor worktrees are relative to that root | Run the installed script with `cwd=project/.specgraph` |
| `TOOLS_DIR` and installed policy functions | Core policies are located beside the installed tool | Do not copy engine policies or tools into the product |
| `initialize_product_workspace` | Accepts an external `--workspace-root`, creates a product config, root-intent capture and initialization receipt | Point it at `project/.specgraph` |
| `SpecNode.save()` / `load_specs_from_dir` | Read/write YAML under `specs/nodes` | Keep the existing YAML model and paths |
| `product_workspace_next_moves.py` | Already accepts `--workspace-root` | Reuse the existing product advisor |
| `load_spec_id_policy()` | Reads `.specgraph/spec-id-policy.json`, defaulting to `SG-SPEC` when absent | Configure an existing product namespace before child allocation |
| `spec_trace_registry_path()` / `runtime_evidence_registry_path()` | Registry data remains workspace-local under `tools/` | Missing contracts stay unknown; no outer-code scanning is implied |
| `build_spec_trace_index()` | Its source scan uses workspace `tools/` and `tests/` | An outer implementation root requires a separate contract |

`workspace.specs_root` and `workspace.runs_root` in the project config are not a
general runtime root-rebinding API: the main Supervisor globals and the advisor
still use their standard paths. Merely changing these YAML fields is therefore
insufficient. Selecting the entire working root preserves those existing paths.

## Existing layout, nested location

```text
project/
  .git/                         # implementation history; may be a Git file
  Sources/
  Tests/
  .specgraph/                   # outer knowledge workspace, independently versioned
    .git/
    .gitignore                  # knowledge-repository artifact retention rules
    specgraph.project.yaml
    specs/nodes/
    docs/proposals/
    docs/evidence/              # explicitly curated evidence when present
    runs/                       # local derived artifacts by default
    .worktrees/                 # local Supervisor execution worktrees
    .specgraph/                 # existing internal state, intentionally retained
      root_intent.md
      spec-id-policy.json       # existing namespace contract, e.g. PRODUCT-SPEC
```

The inner `.specgraph/` is an intentional consequence of reuse. Renaming or
flattening it would create migrations without helping the first pilot.
The initializer creates `specs/`; `specs/nodes/` is created when materializing
the first project spec. Empty directories alone do not survive Git cloning.

## Candidate `specgraph-workspace` skill

The first realization should be a thin setup/context workflow using existing
commands. A wrapper CLI is optional convenience, not an engine prerequisite.

1. Resolve and retain the implementation root, knowledge root and a pinned
   installed engine separately. Reject tracked `.specgraph` content, conflicting
   existing directories and redirection through symlinks. Do not overwrite an
   unrelated repository or its existing instructions.
2. Invoke the existing initializer from the engine checkout with the knowledge
   root as `--workspace-root`. Preserve its product governance and review-first
   root-intent capture. Check receipt readiness, not just command completion.
3. Add exactly `/.specgraph/` to the outer repository's exclusion, preserving
   other entries. Resolve its location with `git rev-parse --git-path info/exclude`
   to support Git files/linked worktrees. Initialize independent knowledge Git
   only when absent; configure the existing product spec-ID policy. Keep
   `runs/` and `.worktrees/` local unless selected artifacts are curated.
4. Run Supervisor operations in a subprocess with the knowledge root as `cwd`,
   retaining the implementation agent's own root for product code work. Use
   installed tools, explicit paths for YAML formatting/linting, and the separate
   product advisor. Do not use core `graph_next_moves` as a product selector.
5. On resume, read the project config, selected specs and applicable run/gate
   state through existing tools. Commit selected knowledge records independently.
   Reattach the engine locally after relocation; do not commit machine paths or
   credentials as portable workspace identity.

Agent discovery must be configured through the supported agent's explicit skill
or session entrypoint. An ignored folder is not automatically discovered. This
local-mode workflow does not edit tracked `CLAUDE.md` or `AGENTS.md` in the product.

Existing command recipe, with absolute engine/Python paths supplied by the caller:

```sh
# Run from the installed engine checkout; PROJECT is an external product root.
"$PYTHON" "$ENGINE/tools/supervisor.py" --init-product-workspace \
  --project-id example-product --workspace-root "$PROJECT/.specgraph" \
  --root-intent "Describe the product objective."

# After safe Git setup and creation of a valid project spec:
(cd "$PROJECT/.specgraph" && "$PYTHON" "$ENGINE/tools/supervisor.py" \
  --target-spec PRODUCT-SPEC-0001 --dry-run)
"$PYTHON" "$ENGINE/tools/product_workspace_next_moves.py" \
  --workspace-root "$PROJECT/.specgraph" --target-spec PRODUCT-SPEC-0001
```

`specgraph init --local` remains a candidate user-facing alias. There is no need
to add that command or a new persistent root setting to prove location reuse.

## Narrow correction identified by the probe

Initial initialization and an immediate rerun succeed. After a Supervisor run,
the generated `.worktrees/` directory remains under the selected knowledge root.
The initializer's `PRODUCT_WORKSPACE_ALLOWED_TOP_LEVEL_ENTRIES` omits that entry,
so a later rerun reports `unexpected_top_level_entries` and blocks.

The bounded initializer correction accepts an existing ordinary `.worktrees/`
directory without changing its contents, and blocks a file or symlink at that
path. Unrelated entries remain subject to the existing conflict checks. A
regression covers init -> execution-created layout -> init. This does not
implement the candidate skill or setup helper.

## Observation and evidence limits

The disposable pilot used a parent Git with one implementation fixture and an
independent nested knowledge Git. It confirmed:

- initializer: `initialized`, then `ready`, zero initial validation findings;
- product environment: valid `product_workspace`, core locked;
- explicit dry-run, graph-health observation and product advisor: exit 0;
- existing YAML formatter/linter: pass after correcting fixture formatting;
- existing refinement path with a deterministic local executor: `ok / done /
  review_pending`, zero validation errors after correcting fixture evidence;
- parent commit unchanged, parent status clean and no workspace paths tracked;
- a committed knowledge checkpoint cloned elsewhere supports dry-run and advice;
- post-execution initializer rerun: blocked on `.worktrees/`, as described above.

The first fixture used JSON-shaped YAML and failed canonical-format lint. Its
initial acceptance evidence also failed semantic grounding; the existing runtime
retried once and kept `retry_pending`. Those failures are retained separately
from the corrected run. No validator was bypassed or altered.

The probe used three deterministic executor calls across the initial failed
attempt, its automatic retry and the corrected run, with zero real agent/provider
calls. It proves the local
execution/review plumbing, not agent quality, adopted specs or runtime evidence.

The trace and evidence commands exited successfully but reported `unclaimed`
and `untracked`. Changing the working directory does not bind the outer Git,
scan its code/tests or establish trusted verification. Do not populate those
states by copying SpecGraph-core registries. Cross-repository trace/evidence
binding is a separate slice with its own input and authority contract.

Cloning restored the committed knowledge checkpoint only. It did not restore
ignored runs or the uncommitted pending-review state. Durable review recovery
requires an explicit artifact-retention decision; Git initialization alone does
not provide it. Git ignore also provides no access-control boundary.

## Delivery and acceptance plan

1. Review this bounded location/skill contract and the observed initializer gap.
2. In a separate realization PR, add the candidate skill and, if needed, a thin
   setup helper. The reproduced initializer correction is implemented separately.
3. Run one real product pilot, preserving initial parent status and commits,
   knowledge history, exact gate state, tool version and portability evidence.

The future realization must verify safe first setup, setup rerun after execution,
outer tracked-file/history preservation, independent knowledge commits, explicit
context recovery, clone/reattach from a different path and rejection of a
tracked/conflicting/symlinked workspace. These are future acceptance cases; the
observation above characterizes only the existing paths and its named fixture.

Do not add SQL, change YAML envelopes/ontology, refactor all Supervisor paths,
install mandatory hooks, modify product source layouts, or add multi-agent,
publication or remote synchronization machinery for this first MVP. A full
Human Intent -> Specification -> Implementation -> Tests -> Evidence -> Outcome
pilot remains open until implementation binding and real verification have
their own evidence. Local artifacts do not confer trusted evidence admission.

```yaml
canonical_mutations_allowed: false
runtime_code_mutations_allowed: false
evidence_admission_allowed: false
```
