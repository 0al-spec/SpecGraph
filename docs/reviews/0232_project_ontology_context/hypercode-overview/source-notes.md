# Sources for the readable ontology outline prototype

Agent-curated excerpts from the development conversation on 2026-11-01.
These references identify this record's excerpts, not native message IDs or
independently authenticated utterance times. Original spelling is retained.

## Scope and intended reader

`overview-1`, user:

> То есть это одностороннее преобразование. Что думаешь по этому поводу? То есть как бы двустороннее мне не нужно. Это позволит читать антологию быстро и просто.

`overview-2`, user:

> То есть в исходном файле .hc там хранить нужно, по идее, только узлы, типы, роли. А как бы связи, да, relations там какие-то и прочее — это должно быть в каскадном .hcs файле.

`overview-3`, user:

> Поэтому тут надо держать в уме вот это вот всегда, что мы проектируем вот этот язык, фреймворк не для любого кода, а для особенного кода, особенного стиля.

`overview-4`, user:

> Концептуально верно, сейчас в проекте для этого почти есть SpecDraft - слой который пишет mindmap

The qualifier “Концептуально” applies to agreement with the described process;
this record does not expand it into approval of every future implementation.

`overview-5`, user:

> Да, оригинальный файл может содержать в себе служебные ссылки и прочие необходимые вещи, просто человеку их показывать ненужно.

`overview-6`, user:

> Потому что я бы хотел и на code review видеть тексты. Поэтому нужен, видимо, минимизированный гиперкод и где-то есть маппинг-файл для, соответственно, гиперкод-онтологии.

Interpretation for this prototype: retain a small readable composition and a
separate inspectable ontology mapping in Git. Technical identity may stay in
the mapping. Role names and a tree are deliberately selected, not inferred from
all relations, inheritance or incidental legacy code dependencies.

## Proposal and contextual response

`overview-7`, assistant proposal selected by the user:

> Для маппинга я бы первым вариантом рассмотрел сам .hcs: он уже предназначен для привязки свойств к узлам Hypercode. Тогда отдельный формат вводить не потребуется. Для чтения .hc открывать каскад по-прежнему необязательно.

`overview-8`, user response to `overview-7`:

> Отличная идея
>
> Давай попробуем сделать первый прототип

This authorizes preparing the first prototype of the proposed pair. It does
not approve the particular short names selected afterwards, a general exporter,
canonical ontology meanings, automatic promotion or a deployment. The current
HCS metadata explicitly keeps the composition proposed for review.

## Approved follow-up: production source bindings

`overview-9`, assistant proposal selected by the user:

> Следующий полезный шаг — добавить в HCS прямые привязки к production-символам, чтобы эту расшифровку можно было получить из самой пары файлов.

`overview-10`, user response to `overview-9`:

> Хорошо, меня устраивает, так что я одобряю. нужно делать далее.

This authorizes extending the prototype mapping with direct production-symbol
references and checking them. The response is linked to that bounded proposal;
it is not treated as canonical publication or approval of arbitrary ontology
interpretations. The existing role outline and note storage remain unchanged.
