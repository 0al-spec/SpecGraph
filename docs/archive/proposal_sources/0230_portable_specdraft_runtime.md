# Source: portable SpecDraft runtime

The operator asked how SpecGraph could be used in projects while it was also
being developed, including whether a Docker distribution was needed. The agent
proposed a separately installed versioned Python package, beginning with
SpecDraft note CLI, preview, resources and coherent skill.

The operator selected:

> Python-пакета с CLI, ресурсами и согласованным skill, устанавливаемого в отдельное окружение инструмента, например через pipx

That selection quotes the agent's proposed design. The operator then said:

> Ok, давай сделаем это
>
> Пропусти через пайплайн самого SpecGraph

The existing `update_notes` API saved that attributed request under
`specdraft_portable_runtime`, revision `2bf2408ebe0148f6a5c6a548f305e67a`.
The supervisor's existing `sync_user_intent_node` intake helper generated the
tracked `user_intent::specdraft-portable-runtime-20261027` node with state
`captured`. This is a real intake operation, not a model refinement, canonical
adoption or approval of the whole notebook. Source captures are retained in
`docs/reviews/0230_portable_specdraft/`.

Proposal 0230 was allocated after updating main and checking local/remote refs,
worktrees, proposal history/registries and open PRs. No collision was found.
SG-SPEC-0007/0050/0051 constrain mediation/promotion; they remain unchanged.
Concrete distribution details belong to this implementation contract.

The source CLI/store/preview packages remain in place and are included in the
wheel through explicit package mappings, preserving old imports and commands.
The `src/specgraph` package becomes the installed facade; no full supervisor
extraction or Docker behavior is inferred. Skill destination byte checks and
CLI/resource copying are I/O mechanics. Existing preview display-state
Specifications remain shared by source and installed entry points.
