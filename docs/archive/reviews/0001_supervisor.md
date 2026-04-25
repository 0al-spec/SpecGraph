Привет. Смотрю это как review Python CLI-orchestrator для локального git-backed SpecGraph под Unix-like workflow. Разбор статический: я не исполнял код, поэтому замечания ниже — по control flow, state semantics и reliability-модели.

Концептуальный чек-лист
	•	Проверить, что review_pending действительно блокирует canonical mutation, а не только promotion статуса.
	•	Проверить, что filesystem authority у supervisor по умолчанию default-deny, а не allow-all.
	•	Проверить, что fallback-path никогда не расширяет привилегии child executor.
	•	Проверить, что derived queues строятся только из accepted canonical state, а не из rejected worktree state.
	•	Проверить atomic writes, locking, ID allocation и concurrency semantics.
	•	Проверить, что policy реально живёт в spec/declarative layer, а не расползается по Python constants.

Краткий roadmap
	1.	Сначала починить approval semantics и allowlist model.
	2.	Потом убрать dangerous sandbox fallback и добавить atomic/locked artifacts.
	3.	Затем вынести policy thresholds и heuristics из Python в declarative policy layer.
	4.	После этого дробить файл на модули и усиливать test harness.

TL;DR

У тебя получился не prompt-router, а уже вполне настоящий bounded orchestration kernel. Это сильная работа. Особенно хороши: isolated worktrees, explicit outcomes/gates, split proposal path, derived artifacts, stale runtime cleanup, refinement acceptance, mutation budget и run authority.

Но как zero-trust supervisor он пока ещё не дотягивает по трём критическим причинам:
	1.	Gate не является настоящим gate: unapproved content попадает в canonical root до approve.
	2.	Пустой allowed_paths = по сути unrestricted write authority.
	3.	Fallback на sandbox worktree включает --dangerously-bypass-approvals-and-sandbox, то есть в аварийном режиме система расширяет привилегии.

Из-за этого мой verdict такой: архитектурно очень сильный bootstrap supervisor, но ещё не fully trustworthy governance runtime.

Сама форма мышления у кода очень хорошо попадает в твою 0AL линию — execution as declaration, explicit constraints, bounded authority, introspectable artifacts, separation of logic and policy. Это хорошо бьётся и с 0AL, и с Agent Passport, и с Hypercode-идеей отделения logic от contextual configuration.  ￼  ￼  ￼

Что в коде уже реально сильное
	•	Supervisor как narrow execution layer. Это видно и по структуре файла, и по тому, что у тебя есть отдельные режимы refine, graph_refactor, split_proposal, apply_split_proposal, resolve_gate. Это уже похоже на compiler driver, а не на “главного умного агента”.
	•	Isolated worktree model. Для bounded refinement это правильная ставка. Особенно ценно, что есть stale runtime detection и cleanup.
	•	Разделение canonical / derived artifacts. runs/*.json, latest-summary.md, refactor_queue.json, proposal_queue.json, runs/proposals/*.json — это хорошая observability surface.
	•	Deterministic validation after executor run. Есть попытка сделать не просто “LLM что-то сделал”, а “изменение прошло через machine gate”.
	•	mutation_budget и run_authority. Это вообще одна из лучших идей в файле. По сути, ты уже подходишь к run-scoped capability passport для supervisor run.
	•	Split proposal как отдельный lane. Очень правильное решение: сначала proposal artifact, потом deterministic apply.

Где реальные проблемы

P0. review_pending не блокирует canonical content

Это главная проблема файла.

В _process_one_spec() внутри ветки if success: ты делаешь:

allowed_changes = select_sync_paths(effective_allowed_paths, changed)
sync_files_from_worktree(worktree_path, allowed_changes)
normalize_materialized_child_specs(materialized_child_paths)
node.reload()
...
if auto_approve:
    ...
else:
    node.data["gate_state"] = "review_pending"

То есть canonical files уже синхронизированы в ROOT до того, как run уходит в review_pending.

Потом в resolve_gate_decision() при decision != "approve" ты не откатываешь этот content. Ты только меняешь gate metadata:
	•	retry_pending
	•	split_required
	•	blocked
	•	redirected
	•	escalated

Но unapproved diff остаётся в canonical tree.

Почему это важно

Если по смыслу review_pending означает “человек ещё не одобрил canonical truth”, то сейчас это не так. Сейчас gate контролирует в основном:
	•	status promotion,
	•	maturity promotion,
	•	metadata,

но не canonical mutation.

Это фундаментально ослабляет всю governance-модель.

Что с этим делать

Нужна одна из двух моделей.

Модель A: true pre-merge review
	•	При success && !auto_approve не sync’ить ничего в ROOT.
	•	Хранить:
	•	pending_sync_paths,
	•	digests,
	•	worktree path,
	•	maybe patch artifact.
	•	На approve — sync + promote.
	•	На retry/block/redirect/escalate — cleanup без writeback в root.

Модель B: post-write review
	•	Тогда надо честно переименовать semantics:
	•	не review_pending, а что-то вроде post_write_review_pending;
	•	не approve, а confirm_promotion.
	•	И не делать вид, что это human approval barrier.

Сейчас код выглядит как будто ты хотел A, но поведение ближе к B.

⸻

P0. Пустой allowed_paths означает unrestricted authority

Это вторая критическая вещь.

У тебя сразу несколько мест трактуют пустой allowlist как “можно всё”:
	•	validate_changed_files_against_allowed_paths() → пустой список даёт [], то есть no errors.
	•	select_sync_paths() → пустой список возвращает все changed files.
	•	can_create_new_spec_files() → пустой список даёт True.

Для zero-trust supervisor это плохой default.

Почему это опасно

Если spec node не задал allowed_paths, child executor фактически получает broad write authority по репе — особенно в success path, где потом идёт sync в root.

Даже если prompt говорит “Refine specification only”, это остаётся prompt-level discipline, а не runtime enforcement.

Что бы я сделал

Сделал бы пустой allowed_paths не permissive, а default-deny with minimal implicit scope:

def default_allowed_paths(node_path: str) -> list[str]:
    return [node_path]

И дальше расширение только через:
	•	explicit allowed_paths,
	•	explicit run_authority,
	•	explicit materialization hint.

То есть базовый смысл должен быть не “no policy”, а “only the selected source node”.

⸻

P0. Fallback-path расширяет привилегии child executor

Это, пожалуй, самый неприятный security regression во всём файле.

Логика такая:
	•	если git worktree add не сработал из-за ref locking / permission issues,
	•	идёшь в create_sandbox_worktree_copy(),
	•	branch становится sandbox/...,
	•	child_executor_should_bypass_inner_sandbox() возвращает True,
	•	build_codex_exec_command() добавляет:

--dangerously-bypass-approvals-and-sandbox

То есть в ситуации деградации runtime ты переходишь в более привилегированный режим, а не в более ограниченный.

Для zero-trust системы это architectural red flag.

Что делать

Нужно сохранить invariant:

аварийный режим может ухудшать DX и throughput, но не может расширять authority.

То есть fallback должен быть:
	•	либо workspace-write в copied sandbox,
	•	либо отказ запуска,
	•	либо отдельный outer sandbox/container boundary,

но точно не dangerously-bypass-approvals-and-sandbox.

⸻

P1. Derived queues обновляются из неутверждённого worktree state

В _process_one_spec() ты строишь:

graph_health = observe_graph_health(... worktree_specs=worktree_specs ...)
proposal_queue_artifact, proposal_items = update_proposal_queue(...)
refactor_queue_artifact = update_refactor_queue(...)

Это делается до того, как стало понятно, accepted ли canonical change как truth, и даже в ветках, где потом run оказывается failed/retry/review_required.

В результате runs/refactor_queue.json и runs/proposal_queue.json могут быть derived не из canonical truth, а из candidate worktree state.

Почему это плохо

Ты начинаешь оркестрировать следующий шаг на основании того, что ещё не стало истиной.

Это почти всегда приводит к одному из двух:
	•	queue poisoning,
	•	ghost refactors/proposals.

Правильнее так

Обновлять derived queues только из:
	•	canonical root state после accepted sync,
	•	либо explicit proposal artifacts, которые сами first-class artifacts.

То есть сперва canonical truth, потом derivation. Не наоборот.

⸻

P1. Concurrency и artifact integrity пока хрупкие

Тут сразу несколько проблем в одном кластере.

1. Нет file locks
update_refactor_queue(), update_proposal_queue(), write_run_log() пишут напрямую.
Если два supervisor run идут параллельно, возможны:
	•	lost update,
	•	partial write,
	•	invalid JSON.

2. Запись не atomic
Нет temp file + os.replace().
Если процесс умер посередине записи queue/log — artifact может стать битым.

3. run_id, branch и worktree path коллидируют по секундам
И run IDs, и worktree branch/path используют timestamp с точностью до секунды.
Два запуска одного spec в одну секунду — и у тебя возможны collision/overwrite.

4. Sequential spec ID allocation не защищён
next_sequential_spec_id() просто берёт max + 1 из текущих specs.
Параллельные child materialization runs могут выбрать один и тот же ID.

Что делать

Минимальный набор:
	•	lockfile на queue/log/id allocation,
	•	atomic write через temp + os.replace,
	•	run_id/branch с uuid4 или time_ns,
	•	reserved-ID registry или allocator artifact.

⸻

P1. Код всё ещё содержит слишком много governance policy

Это уже architectural drift.

Docstring говорит, что canonical governance живёт в SG-SPEC-0002 / SG-SPEC-0003, а supervisor — execution layer. Но в коде зашито очень много policy:
	•	ATOMICITY_MAX_ACCEPTANCE = 5
	•	ATOMICITY_MAX_BLOCKING_CHILDREN = 3
	•	subtree shape thresholds
	•	signal priorities
	•	outcome classes
	•	status progression
	•	execution profiles
	•	mutation classes
	•	child executor model / disabled features

Часть из этого — runtime invariants. Но большая часть — именно policy.

А у тебя вся линия Hypercode как раз про радикальное отделение logic structure от contextual/policy configuration, плюс отдельный inspector для applied rules.  ￼  ￼

Что бы я сделал

Разделил бы это на три слоя:

1. Hard runtime invariants
	•	immutable field protection
	•	atomic write requirements
	•	schema loading contract

2. Declarative governance policy
	•	atomicity thresholds
	•	selector priorities
	•	proposal thresholds
	•	allowed mutation classes
	•	execution profile selection policy

3. Operator-local ephemeral overrides
	•	--operator-note
	•	temporary budgets
	•	temporary run authority

Сейчас 2-й слой у тебя в основном захардкожен в Python.

⸻

P2. Execution profiles сейчас не очень честные

Сейчас fast и standard почти одинаковые.

Почему:
	•	все три профиля используют один и тот же reasoning_effort = xhigh,
	•	timeout floor для xhigh = 420,
	•	fast.timeout_seconds = 420,
	•	standard.timeout_seconds = 420.

То есть fast и standard по сути не различаются ни по reasoning, ни по effective timeout.

Это не критический баг, но это ломает ментальную модель оператора.

Что лучше

Сделать реально разные профили:
	•	fast: medium/high reasoning, shorter timeout
	•	standard: high
	•	materialize: xhigh, longer timeout

⸻

P2. Prompt contract местами противоречивый

В общем refinement_section написано:
	•	“you may create multiple sibling child specs in one run”

Но для targeted child materialization дальше пишется:
	•	“may materialize exactly one new child spec”

То есть в одном prompt есть competing instructions.

Плюс ordinary refine prompt вообще довольно щедро разрешает decomposition, даже когда authority model этого не хочет.

Для LLM-orchestrated system это важно: когда authority contract не совпадает с prompt wording, enforcement начинает жить только в post-hoc validation.

Лучше делать prompts более жёстко mode-specific.

⸻

P2. Machine protocol недостаточно строгий

parse_outcome() по умолчанию трактует returncode == 0 как done, даже если executor не вывел обязательные строки:

RUN_OUTCOME: ...
BLOCKER: ...

То есть молчаливое нарушение machine protocol может пройти как success path.

Я бы сделал наоборот:
	•	нет валидного RUN_OUTCOME → protocol error,
	•	protocol error → blocked или retry,
	•	success только при explicit outcome.

⸻

Мелкие, но реальные баги/смеллы

Вот это я бы чинил почти сразу.
	•	ROOT = Path.cwd() — хрупко. Запуск из не-root директории сломает path semantics.
	•	load_specs_from_dir() не проверяет, что top-level YAML — mapping. Невалидный YAML может дать list, а дальше всё упадёт в SpecNode.id.
	•	update_refactor_queue() и update_proposal_queue() не ловят JSONDecodeError, в отличие от load_*. Повреждённый queue artifact может положить supervisor.
	•	last_errors записывается только когда errors есть, но не очищается на success. В итоге у узла могут висеть stale errors после успешного run.
	•	capture_nested_executor_progress() делает полный os.walk() по worktree каждые 30 секунд. На больших репах это дорогой polling.
	•	Progress grace можно удерживать почти бесконечно, если child постоянно шевелит stdout/stderr или какой-то файл. То есть timeout становится soft.
	•	create_sandbox_worktree_copy() копирует почти весь repo tree, вероятно включая .git, что делает fallback тяжёлым и не очень чистым.

Что я бы сделал первым делом

1. Превратил бы gate в настоящий pre-merge barrier

Минимально так:

if success and auto_approve:
    sync_files_from_worktree(worktree_path, allowed_changes)
    promote_status_and_maturity(node)
elif success:
    node.data["gate_state"] = "review_pending"
    node.data["pending_sync_paths"] = allowed_changes
    node.data["pending_worktree_path"] = worktree_path.as_posix()
    node.data["pending_base_digests"] = snapshot_file_digests(allowed_changes, ROOT)
    # ВАЖНО: никакого sync в ROOT здесь

А в resolve_gate_decision(approve) уже делать sync.
На reject/block/retry — просто cleanup pending artifact/worktree.

2. Ввел бы default-deny для writes

Примерно так:

def base_allowed_paths(node: SpecNode) -> list[str]:
    rel = node.path.relative_to(ROOT).as_posix()
    return list(node.allowed_paths) or [rel]

И расширение scope только через explicit authority.

3. Убрал бы dangerous fallback

Принцип:
	•	fallback может менять способ изоляции,
	•	fallback не может давать больше прав, чем normal path.

4. Сделал бы artifact store атомарным
	•	queue.lock
	•	temp file
	•	os.replace
	•	json schema validation на read/write

5. Разделил бы файл минимум на 6 модулей
	•	model.py — SpecNode, graph traversal, IDs
	•	selection.py — candidate picking, signals
	•	validation.py — YAML/status/acceptance/reconciliation
	•	executor.py — Codex adapter, timeouts, progress
	•	artifacts.py — logs, queues, proposals, atomic writes
	•	workflow.py — _process_one_spec, gate resolution, split apply

Сейчас файл уже слишком близок к “god-object in module form”.

Общая оценка

Мой честный вывод такой:

Как bootstrap prototype — это сильный код.
Как policy-constrained supervisor for zero-trust intent runtime — ещё нет.

Самое ценное у тебя уже есть:
	•	bounded orchestration mindset,
	•	artifact thinking,
	•	state/gate discipline,
	•	attempt at deterministic acceptance,
	•	explicit operator authority.

Самое опасное пока тоже уже видно:
	•	review не защищает canonical truth,
	•	authority по файлам слишком широкая,
	•	деградация среды расширяет привилегии,
	•	derived state может опираться на noncanonical state.

И ещё одна важная мысль.
У тебя в Hypercode TODO очень правильно звучит идея Configuration Inspector — показать, какие правила применились, в каком порядке, что что переопределило. Для supervisor тебе нужен почти такой же инструмент, только на уровне решений: Decision Inspector. Он должен отвечать:
	•	почему выбран именно этот spec,
	•	какой signal сработал,
	•	почему run попал в review_pending,
	•	какие diff paths отнесли change к graph_refactor,
	•	почему queue item появился или исчез.

Это был бы очень сильный следующий слой поверх текущего supervisor дизайна.  ￼

Следующий практический шаг — превратить этот review в 5 минимальных PR-серий: approval barrier, default-deny writes, safe fallback, atomic artifacts/locking, policy extraction.
