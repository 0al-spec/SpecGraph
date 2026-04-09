Да, риск реальный.

Если `supervisor` продолжит обрастать флагами, он станет не “разумным исполнителем”, а неудобным low-level комбайном. Это нормально для bootstrap-этапа, но не должно стать финальным интерфейсом.

Я бы зафиксировал такую архитектуру:

**1. `supervisor` как kernel, не как user-facing tool**
Пусть он остаётся низкоуровневым движком:
- выполнить bounded refinement
- сделать split proposal
- применить proposal
- прогнать validation/gates
- вернуть structured result

То есть много параметров допустимо, если это внутренний API, а не то, чем человек пользуется напрямую каждый день.

**2. Снаружи нужен тонкий слой orchestration**
Именно то, что ты описываешь:
- внешний агент
- viewer/GUI
- mediator
- цикл с обратной связью

Он не должен дёргать 10 CLI-флагов руками. Он должен собирать один нормализованный request, например:
- `mode`
- `target`
- `instruction`
- `authority`
- `mutation_budget`
- `stop_condition`

А `supervisor` уже внутри раскладывает это на свои детали.

**3. В будущем loop должен быть не “запускай supervisor как попало”, а примерно такой**
- observe graph
- derive metrics/signals
- choose next bounded intervention
- call supervisor with one normalized request
- validate result
- update graph
- recompute metrics
- stop on plateau / budget / review checkpoint

То есть да, идея “внешний агент гоняет supervisor до плато по SIB и другим метрикам” выглядит правильной.

Но я бы добавил два предохранителя:
- stop not only on plateau, but also on repeated no-op / oscillation
- human review checkpoints on constitutional changes

Иначе система может застрять в локальном оптимуме или начать крутить граф ради метрики.

**Практический вывод**
Текущий рост сложности CLI не страшен, если мы сейчас осознанно считаем его internal kernel surface.

Следующий правильный слой:
- не ещё больше флагов для человека
- а `OperatorRequest` / `RunRequest` как единый объект
- и уже GUI/внешний агент работают только с ним

То есть:
- человек общается с mediator
- mediator формирует request
- supervisor исполняет
- metrics замыкают feedback loop

Это как раз снимет твоё опасение.

Если хочешь, следующим шагом я бы занялся именно этим: спроектировать минимальный `OperatorRequest` contract для внешнего агента и GUI, чтобы `supervisor` дальше можно было вызывать стабильно, без разрастания user-facing CLI.
