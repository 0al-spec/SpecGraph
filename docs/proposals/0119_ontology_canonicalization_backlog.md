# Ontology Canonicalization Backlog

RFC: SG-RFC-0119
Version: 0.1.0

## Status

Informational

Decision scope: umbrella backlog and sequencing for deferred Ontology
canonicalization, materialization, packaging, and mutation UI work.

This document is a backlog index only. It does not create a canonical
`ontology.lock.yaml`, import concepts into `specs/nodes/*.yaml`, write
Ontology packages, update lockfiles, close semantic gates, execute prompt
agents, define Platform/Docker packaging, or add SpecSpace mutation UI.

## Source Material

This proposal records deferred debt after the implemented Ontology semantic
control line from `0100` through `0118`, plus the downstream Ontology owner
decision and SpecSpace acknowledgement workflow.

Source draft:

- `docs/archive/proposal_sources/0119_ontology_canonicalization_backlog.md`

Primary upstream anchors:

- `0060_external_ontology_import_plane`
- `0100_ontology_grounded_semantic_control`
- `0116_ontology_semantic_lint_input`
- `0117_ontology_supervisor_soft_gate_wiring`
- `0118_ontology_prompt_agent_context_artifact`
- Ontology ONT-031, ONT-035, ONT-036, and ONT-037
- SpecSpace owner decision acknowledgement workflow

## Summary

The Ontology line now has a review-first semantic loop:

```text
accepted ontology context
  -> source-backed semantic lint input
  -> semantic lint and supervisor soft gate
  -> prompt-agent ontology context artifact
  -> Ontology owner decisions
  -> SpecGraph decision import preview
  -> SpecSpace acknowledgement state
```

That loop deliberately avoided canonical materialization. The remaining work is
real, but it should not be spread across chat history or hidden in non-goals of
earlier proposals. This umbrella proposal collects that debt and defines the
order in which later bounded proposals should split it.

## Problem

Deferred Ontology work is currently mentioned across several places:

- `0060` defines the external ontology import plane and blocks canonical
  adoption until accepted.
- `0100` defines semantic control but explicitly avoids lockfiles, package
  writes, and mutation UI.
- `0116` through `0118` implement source-backed grounding and prompt-agent
  context without canonical writes.
- Ontology ONT-031 describes a future import-to-lockfile workflow.
- SpecSpace can acknowledge owner decisions, but that state is local and
  non-authoritative.

Without one umbrella proposal, future work risks skipping the review loop and
jumping straight to canonical `ontology.lock.yaml`, automatic imports, or
mutation UI before compatibility and authority boundaries are proven.

## Current Boundary

The current accepted boundary remains:

- Ontology owns package shape, package validation, compiler behavior,
  governance decisions, and package publication.
- SpecGraph owns graph-side import review, semantic lint/gate artifacts,
  decision previews, proposal sequencing, and eventual canonical acceptance.
- SpecSpace owns read-only review surfaces and SpecSpace-owned local operator
  workflow state.
- Platform owns packaging/deploy coordination only after upstream contracts are
  stable.

No current artifact grants authority to:

- write `specs/imports/ontology.lock.yaml`;
- mutate `specs/nodes/*.yaml`;
- import owner decisions into canonical SpecGraph specs;
- write Ontology packages from SpecGraph supervisor output;
- close semantic gates from SpecSpace acknowledgement state;
- treat prompt-agent context as proof that generated text is correct.

## Deferred Debt Inventory

### 1. Canonical Ontology Lockfile

Future work may introduce:

```text
specs/imports/ontology.lock.yaml
```

This must wait for a compatibility report and explicit import-review boundary.
The first child slice should be a lock preview, not a canonical lockfile write.

### 2. Automatic Imports Into Canonical Specs

Future work may materialize accepted ontology bindings into
`specs/nodes/*.yaml`. This requires a separate proposal because it changes
canonical graph state and must preserve stable spec IDs, provenance, and
review evidence.

### 3. Platform And Docker Packaging

Future work may package `ontologyc`, prompt packs, and ontology package caches
for CI, local operator workflows, and deployment environments. This must not
claim that SpecGraph has accepted any ontology package unless SpecGraph has an
accepted import lock.

### 4. SpecSpace Mutation UI

Future work may add SpecSpace UI for import proposals, semantic binding review,
or lockfile update proposals. It must begin as a proposal/review workflow, not
as direct mutation of Ontology packages or SpecGraph canonical specs.

### 5. Supervisor-Driven Ontology Package Writes

Future work may allow a supervisor or prompt-agent flow to propose Ontology
package changes. Such work must remain behind typed invocation artifacts,
governance decisions, and explicit human review. It must not silently turn
generated terms into accepted ontology vocabulary.

## Proposed Child Proposal Sequence

### 0119-A: Lock Preview And Compatibility Report

Build a derived, read-only report that compares current ontology imports,
owner decisions, semantic bindings, and package refs with a candidate lockfile.

Expected boundary:

- no canonical lockfile write;
- no import into specs;
- no package download cache mutation;
- clear incompatible, missing, stale, and ready states.

### 0119-B: Canonical Lockfile Adoption

Define and implement the first accepted `specs/imports/ontology.lock.yaml`
contract after the preview report is stable.

Expected boundary:

- explicit source/version/digest discipline;
- compatibility report required;
- owner/governance evidence required;
- canonical write only through a reviewed PR.

### 0119-C: Import Proposal Materialization

Define how accepted owner decisions and semantic bindings become reviewable
SpecGraph import proposals before canonical spec mutation.

Expected boundary:

- proposal artifact first;
- no direct `specs/nodes/*.yaml` mutation from owner decision reports;
- explicit affected spec refs and semantic before/after state.

### 0119-D: Platform Packaging

Package the stable Ontology consumer pieces for local/CI/deploy use.

Expected boundary:

- packaging follows accepted contracts;
- deploy artifacts do not create semantic authority;
- missing runtime dependencies are reported as environment gaps, not ontology
  acceptance.

### 0119-E: SpecSpace Mutation UI

Add review actions for lock/update/import proposals only after the backend
proposal and authority boundary exists.

Expected boundary:

- UI can propose or acknowledge;
- UI cannot directly mutate Ontology packages or canonical SpecGraph specs;
- every action has evidence refs and review state.

### 0119-F: Supervisor Write Boundary

Define whether supervisor or prompt-agent outputs may ever request Ontology
package writes.

Expected boundary:

- typed invocation input/output;
- Agent Passport or equivalent capability policy before execution;
- Ontology governance decision before acceptance;
- no raw prompt authority;
- no silent canonical graph mutation.

## Readiness Gates

No child slice may move from preview/review into canonical mutation until it
has:

- a source draft and proposal markdown;
- promotion/runtime tracking or explicit no-runtime classification;
- authority boundary fields that default to false;
- source/version/digest discipline for external ontology packages;
- tests or validators for malformed, stale, and authority-expanding inputs;
- a review path that separates accepted Ontology authority from accepted
  SpecGraph canonical state;
- a rollback or blocked-state story for incompatible ontology package changes.

## Authority Boundary

This umbrella proposal may be used as:

- a backlog index;
- a sequencing reference;
- evidence that deferred debt is known and intentionally bounded;
- a parent for later child proposals.

This umbrella proposal may not be used as:

- approval to create or update `ontology.lock.yaml`;
- approval to import decisions into `specs/nodes/*.yaml`;
- approval to write Ontology packages;
- approval to execute prompt agents;
- approval to close semantic gates;
- approval to add SpecSpace mutation UI.

## Acceptance

This informational slice is complete when:

- `docs/proposals/0119_ontology_canonicalization_backlog.md` lists the deferred
  debt and child proposal sequence;
- `docs/archive/proposal_sources/0119_ontology_canonicalization_backlog.md`
  preserves the source draft;
- proposal `0119` is tracked in proposal promotion provenance;
- proposal runtime tracking records this as a deferred umbrella backlog rather
  than an implemented runtime slice;
- proposal tracking gate passes.

## Next Gap

```text
split_ontology_lock_preview_compatibility_report
```
