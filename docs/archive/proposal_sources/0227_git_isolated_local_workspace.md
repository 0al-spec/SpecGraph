# Git-Isolated Local Workspace: Source Draft

## Source and authority

Operator discussion on 2026-10-23, followed by source inspection and a disposable
local probe against the current `origin/main`. This is proposal input, not an
adopted product rule or permission to change the ontology.

The operator proposed a local `.specgraph/` inside an existing implementation
repository, with its own Git history and an outer-repository exclusion in
`git info/exclude`. The original principle was:

> Code and Knowledge are colocated, but independently versioned.

The intended knowledge includes intent, specifications, decisions, evidence and
development experience, linked to implementation revisions. A proposed
`specgraph-workspace` built-in skill would recover context, use SpecGraph tools,
preserve traceability and avoid adding internal artifacts to the code history.
The original candidate CLI was `specgraph init --local`.

The operator explicitly retained structured SpecGraph semantics:

> Workspace не должен становиться просто каталогом Markdown-файлов.
> Источником истины остаётся структурированная модель SpecGraph; файлы
> могут выступать её сериализацией или представлением.

## Clarification

An assistant suggested SQLite as an optional future index. The operator asked
whether SQL was already present. Inspection confirmed that the existing
Supervisor reads and writes YAML files; SQL is not its spec storage backend.
SQLite was an assistant suggestion, not an operator requirement. It is excluded
from the selected MVP.

The operator then requested:

> Оформим MVP как proposal? Я хочу минимальных правок в код проекта.
> Мне кажется, что можно буквально лишь настроить сам путь до workspace,
> чтобы это уже заработало. Пойди в код - проверь.

This authorizes a source-grounded proposal and investigation. The proposal
records a future skill/workflow; this change does not ship that skill or a new
initialization command.

## Bounded interpretation

Use the existing Product Workspace initializer, YAML layout, product governance
and installed engine. Select `project/.specgraph` as the workspace root and run
existing Supervisor commands with that directory as their working directory.
Keep the implementation checkout as the implementation agent's working root.

The initial folder names `intents/`, `specifications/`, `decisions/`, `evidence/`
and `experience/` express information categories, not a requirement to replace
the existing on-disk contract. Preserve `specs/`, `docs/proposals/`, `runs/` and
the inner `.specgraph/` state directory for the MVP.

Independent Git initialization, an outer exclusion, existing spec-ID namespace
configuration and agent discovery are setup work. They do not require a new
storage engine or refactoring every path in the Supervisor.

Cross-repository implementation scanning, trusted runtime evidence, enforced
hooks, automatic synchronization, parallel code-worktree coordination and
publication remain separate follow-ups. The location probe must not be
presented as completion of the original full implementation/evidence cycle.

## Investigation outcome

The inspected engine uses `ROOT = Path.cwd()` and installed `TOOLS_DIR` policies.
Initialization, dry-run, graph observation, product advice and a deterministic
refinement/review path ran against an independent nested Git without runtime
source edits. A committed knowledge checkpoint was cloned to another path and
read successfully. The parent implementation fixture retained its commit and
clean status.

The probe also exposed an existing narrow gap: rerunning the initializer after
Supervisor execution rejects its generated `.worktrees/` directory. Separately,
trace/evidence builders return `unclaimed`/`untracked` without product contracts;
they do not automatically inspect the outer implementation repository.

See the [proposal](../../proposals/0227_git_isolated_local_workspace.md) and its
retained observation for exact boundaries and future acceptance cases.
