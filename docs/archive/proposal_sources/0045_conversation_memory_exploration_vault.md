# Conversation Memory Exploration Vault Source Draft

## Source Class

Working draft.

## Historical Concern

SpecGraph needed a structured Layer 0 memory path from raw conversation sources
into typed notes, exploration maps, and proposal pressure without making chat
history, PageIndex results, or memory notes canonical truth.

## Promotion Note

This archived source preserves the draft concern that was normalized into
`docs/proposals/0045_conversation_memory_exploration_vault.md`.


## Operator clarification: conversational Hypercode capture (2026-10-23)

Source: operator excerpts from the active SpecGraph development conversation.
These local excerpt labels are not native chat message IDs.

- `hypercode-notes/1`: «Придумай как сюда вписать Hypercode»
- `hypercode-notes/2`: «Да, это хороший PoC.»
- `hypercode-notes/3`: «Думаю для него не надо усложнять, надо просто представить как во время беседы человека и агента последний делает как бы заметки, вызывая некие инструменты и сабагентов. А человек просто говорит и одобряет.»
- `hypercode-notes/4`: «Да, хорошо подметил. Делай.»

The assistant interpretation approved for implementation is two agent-callable
operations, read_notes and update_notes, with persistent Hypercode notes, source
quotations and small reviewable diffs. Saving precedes semantic refinement.
Subagents may suggest changes when authorized; saving does not wait for them.
The human's implementation authorization is not an approval of a future saved
sketch revision and must not be copied into its approval history.

## Dogfooding handoff source excerpts

Captured on 2026-10-23 UTC from the same development conversation. The labels
below form a separate, document-local namespace; they are not native message
IDs or aliases for the earlier `hypercode-notes/*` labels. Original wording,
including transcription artifacts, is retained. The ordering supplies the
context of the final approval.

### dogfood/1 — human: design and realization

> Да, проектирование сложных систем это многоуровневый процесс поэтапного уточнения с последующим процессом реализации системы через построение её каркаса на основе проекта и реализации и устраивания конкретных узлов-модулей в этом каркасе, преимущественно снизу вверх, от частностей к общему, от простого к комплексному.

### dogfood/2 — human: conversation as the source of refinement

> Я сейчас не вижу всех документов, потому что я с телефона, но мне кажется, что узел многоуровневое поэтапное уточнение мы можем перенести почти на весь... всю ветку из предыдущего сообщения с узла беседа и далее. То есть смысл будет в том, что это уточнение, они из ниоткуда берутся, а вот из этой беседы. Как ты думаешь, подходит?

### dogfood/3 — human: proposed SpecGraph change

> Вот мы сейчас обсудили как бы способ добавления данных в SpecGraph, новых узлов, спецификаций. То есть мы сейчас dogfoodding занимаемся. Получается, мы сейчас описали то, чего нет, чтобы это добавить. То есть мы должны найти какой-то реальный уже узел в графе спецификаций SpecGraph, который может быть как-то обновлён, или создан, или как-то ещё там переструктурирован, не знаю, что с ним можно сделать, в котором, соответственно, этот процесс и будет описан далее. Нам нужно по текущему процессу видимо сделать какой-то proposal, и в этом proposal описать заметки и процесс их фиксации и их преобразования в пропозалы или узлы спек. Так?

### dogfood/4 — agent: proposed next action

> Следующая задача — подготовить дополнение к 0045 на материале нашей беседы, с выбранными узлами и предлагаемыми изменениями.

### dogfood/5 — human: authorization of that action

> Хорошо, одобряю. Это вот мне нравится. Получается, по итогам беседы, мы говорили заметку, обсудили, пришли к консенсусу и моего одобрения последующих, соответственно, действий.

The authorization is interpreted against `dogfood/4`: prepare the amendment.
It is not a whole-sketch approval, review of the subsequently authored canonical
delta, or permission to merge/apply that delta. The actor attribution comes
from the conversation; these excerpts are not an authenticated decision record.

### Selected local sketch lineage

The sketch is `hypercode-conversation-poc`. Its local source references
`operator-excerpt:hypercode-notes/4` through `/7` correspond to `dogfood/1`,
`dogfood/2`, `dogfood/3`, and `dogfood/5`, respectively. They belong to the live
sketch's namespace; the earlier archived `hypercode-notes/4` above names a
different excerpt and must not be joined by suffix alone.

- `system_design` groups the refinement concern.
- `conversation` moved under `system_design` without changing either ID.
- `notes_to_specgraph_proposal` records the proposed handoff and action scope.
- Revision `168eb03508b942499d7d7bfda6c7795e` contains the handoff request.
- Revision `62ea6b7d435d4bfa9d69eb748dd3a10e` adds the scoped action authorization.

Only these curated excerpts and identifiers are published. The live sketch and
its full revision history remain local. The proposed canonical change is an
assistant-authored interpretation in proposal 0045, not text quoted from the
operator and not an already applied graph mutation.

## Operator clarification: separate proposal counts (2026-10-24)

After inspecting `302 -> 302` for the capture PoC, the operator asked:

> Давай чуть улучшим этот подсчет, да

When asked whether the first improvement should include proposal obligations
as a separate draft count or extract more fields from canonical YAML, the
operator selected:

> Обязательства в proposals отдельно (рекомендую)

The assistant's bounded implementation uses explicit YAML declarations beside
proposals and the existing versioned analyzer in a separate Git root. The eight
statements in the 0045 declaration are agent-authored summaries of this proposal;
the excerpts above do not attest approval of those exact formulations.
Counts remain separate from canonical specification atoms and do not grant authority.
