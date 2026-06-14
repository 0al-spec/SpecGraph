# Ontology Canonicalization Backlog

## Operator Intent

After the Ontology semantic-control loop reached source-backed linting,
supervisor soft-gate evidence, typed prompt-agent context, real Ontology owner
decisions, and SpecSpace acknowledgement state, the remaining deferred
canonicalization work should be visible in one place.

The intent is to record the debt without prematurely authorizing canonical
mutation, lockfile writes, automatic imports, Platform packaging, SpecSpace
mutation UI, or supervisor package writes.

## Bounded Slice

Create an umbrella proposal that:

- inventories deferred Ontology materialization and packaging work;
- links the debt to `0060` and `0100` through `0118`;
- names child proposal slices that can be implemented later;
- states readiness gates before any canonical lockfile or mutation work starts;
- preserves the current review-first, read-only boundary.

## Deferred Debt

- Canonical `specs/imports/ontology.lock.yaml`.
- Automatic imports into `specs/nodes/*.yaml`.
- Platform/Docker packaging for `ontologyc`, prompt packs, and package caches.
- SpecSpace mutation UI for import proposals or semantic binding edits.
- Supervisor-driven Ontology package writes.

## Non-Goals

- Implementing any runtime surface.
- Creating or updating a canonical ontology lockfile.
- Importing owner decisions into canonical SpecGraph specs.
- Closing semantic gates from acknowledgement state.
- Running prompt agents or persisting raw prompts/responses.
- Writing Ontology packages from SpecGraph or SpecSpace.

## Follow-Up Shape

Each deferred item should become its own bounded proposal before
implementation. The first likely child slice is a lock preview and
compatibility report, not a canonical lockfile mutation.
