# SpecDraft Live Preview — source draft

Source class: working draft. These are agent-curated excerpts from the active
development conversation on 2026-10-26 UTC. Labels are local references, not
native message IDs; original message times are unavailable.

## sidecar/1 — human: live view and deferred history

> Сейчас родилась идея, как SpecDraft сделать красиво. Мы поднимаем как бы такой sidecar сервачок маленький, который рендерит заметки и, соответственно, в реальном времени следит за содержимым и обновляет по ходу беседы где-то отображение этой заметки красивое в веб-вью, то бишь в браузере, например, на этом порту, где он обслуживает. И, соответственно, в кодексе или в клод код это можно сделать, как это у них называется, Browser Preview, по-моему, во вкладке. Вот такая вот идея. И, соответственно, человек беседует и видит свой mind map, как бы вот этот specdraft, черновик, заметку в таком движении, как она меняется. Можно даже сделать версионирование, но это так, по приколу. Но вообще может быть полезно, когда нужно по чекпойнтам откатиться к предыдущему варианту, или там агент не так понял. Но это чуть позже. Пока можно просто сделать визуализацию.

## sidecar/2 — human: use the existing dogfooding process

> Надо это сделать через докфудинг, через заметки, спейки и всё прочее, позы, там, всё по канону.

The transcription is retained verbatim. In this plan, the wording is interpreted
as using notes, specifications and proposals through the existing process. It
does not approve the subsequently prepared acceptance criteria.

## Captured note lineage

The existing `hypercode-conversation-poc` sketch was resumed through `read_notes`
and updated through `update_notes`. The relevant branches were captured as:

- `b3013d12f4df41afa53d5858ca911657`: SpecDraft naming/context;
- `254a91a0ec3247789ceeea4617f7b903`: sidecar, browser view, live updates and deferred history;
- `e255d0f2dce94685a353da78669b0886`: explicit dogfooding direction.

The [selected source snapshot](../../reviews/0228_specdraft_live_preview/source-notes.json)
retains six nodes beneath `specdraft_layer`, their source quotations and incident
links. Links can target omitted nodes; this is a bounded branch export, not the
entire local notebook or history. The live notebook remains Git-ignored.

## Agent interpretation for review

The person should see the current sketch change while continuing the
conversation. The agent keeps writing through the existing notes tools. A small
local viewer reads committed snapshots and presents them as a mind map.

Read-only HTTP, loopback binding, a two-second foreground refresh target,
source-detail navigation and visible recovery from read errors are proposed
engineering choices. The human did not specify those exact mechanisms or
numbers. Browser Preview is treated as an ordinary local-page consumer;
agent-specific integration is not yet verified. History browsing and rollback
are explicitly deferred by the human, although note storage already retains
revisions.

This source capture authorizes preparation and review. No final SpecDraft
acceptance, canonical materialization, implementation or runtime verification
has been recorded by these excerpts.
