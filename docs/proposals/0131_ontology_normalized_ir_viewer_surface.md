# Ontology Normalized IR Viewer Surface

RFC: SG-RFC-0131
Version: 0.1.0

## Status

Draft proposal

Decision scope: read-only SpecSpace consumer surface contract for presenting
Ontology compiler normalized IR together with package metadata, gaps, diffs,
and source evidence.

This document defines a consumer surface contract only. It does not implement
SpecSpace UI in SpecGraph, run ontologyc, write Ontology packages, update
ontology lockfiles, mutate canonical SpecGraph specs, accept candidate terms,
import owner decisions, close semantic gates, invoke prompt agents, or add
SpecSpace mutation UI.

## Source Material

This proposal captures the next Ontology UI slice after public-safe run
artifacts and normalized compiler IR became available to static consumers.

Source draft:

- `docs/archive/proposal_sources/0131_ontology_normalized_ir_viewer_surface.md`

Related proposal context:

- `0060_external_ontology_import_plane`
- `0100_ontology_grounded_semantic_control`
- `0113_ontology_review_dashboard`
- `0115_ontology_decision_import_preview`
- `0119_ontology_canonicalization_backlog`
- `0127_ontology_stdlib_type_discipline`
- `0128_ontology_term_binding_policy`
- `0129_generated_term_binding_gate`

## Summary

SpecGraph now publishes enough public-safe artifacts for SpecSpace to show a
curated Ontology package as more than raw JSON. The next consumer surface should
render the normalized Ontology compiler IR as a reviewable ontology view:

```text
package metadata -> classes/entities -> relations -> domains/namespaces
                 -> gaps/diffs -> evidence refs -> raw artifact links
```

The surface is read-only. It clarifies what the compiler currently knows and
what SpecGraph review artifacts still report as gaps or diffs. It must not make
derived observations look like accepted ontology authority.

## Problem

The generic artifact inspector proves that `ontology.normalized.json` and
related `runs/*.json` artifacts are published, but raw JSON is not the right
operator surface for ontology review.

Without a purpose-built view, operators have to reconstruct:

- which package the IR came from;
- which entities/classes exist in the accepted package;
- which relations exist and how they are named;
- whether domains or namespaces are represented;
- which gaps or diffs are still pending review;
- which artifact is the source of each displayed fact;
- whether a displayed term is compiler authority, SpecGraph evidence, or only
  a derived review observation.

This is especially risky after the practical-ontology demo work: a visually
convincing graph can look canonical even when it is only a demo or derived
observation.

## Proposal

Introduce `specspace.ontology.normalized_ir_viewer.v0.1` as a read-only
consumer contract for SpecSpace.

The surface should use the published artifact manifest to discover and read:

```text
runs/ontology_package_index.json
tests/fixtures/ontology_import/specgraph-core/ontology.normalized.json
runs/ontology_import_gap_index.json
runs/ontology_compatibility_diff_preview.json
runs/ontology_governance_evidence_index.json
```

The normalized IR path should be discovered through package metadata when
available, especially `packages[].materialized_ir`, rather than hardcoded as the
only possible path.

## Display Contract

The consumer surface should present these sections:

### Package Header

- package id or name;
- namespace;
- version;
- source ref;
- digest when available;
- normalized IR artifact path;
- authority state.

### Classes And Entities

- accepted class/entity id;
- display label;
- kind/type when present;
- namespace/domain when present;
- source refs when present.

### Relations

- relation id;
- display label;
- source and target types when present;
- relation kind when present;
- source refs when present.

### Domains And Namespaces

- domain or namespace id;
- label;
- related entity count when derivable;
- source refs when present.

### Gaps And Diffs

The viewer should place related review artifacts next to the normalized IR:

- ontology import gaps;
- compatibility diff preview rows;
- governance evidence entries;
- review or blocking state when present.

Gaps and diffs remain review evidence. They are not accepted ontology terms and
must not be displayed as accepted compiler IR.

### Raw Artifact Links

Every section should keep a path back to the generic artifact inspector so an
operator can inspect the source JSON without losing context.

## Authority Boundary

The viewer may:

- read public-safe artifact manifest entries;
- read normalized Ontology compiler IR;
- read public-safe run artifacts;
- search, filter, group, and display ontology package content;
- link displayed rows back to source artifacts;
- show gaps and diffs as review evidence.

The viewer may not:

- write Ontology packages;
- update ontology lockfiles;
- mutate `specs/nodes/*.yaml`;
- accept, reject, deprecate, or rename terms;
- import owner decisions;
- close semantic gates;
- execute prompt agents;
- treat practical ontology observations as accepted ontology;
- treat demo graph data as canonical ontology.

The minimum authority flags are:

```yaml
canonical_mutations_allowed: false
ontology_writes_allowed: false
spec_mutations_allowed: false
owner_decision_import_allowed: false
semantic_gate_closure_allowed: false
```

## Acceptance

This contract slice is complete when:

- proposal `0131` has source draft provenance;
- promotion/runtime tracking records the bounded source and scope;
- proposal tracking gate passes;
- the surface contract names the public artifacts it consumes;
- the surface contract requires normalized IR discovery through package
  metadata where possible;
- the surface contract separates compiler IR from gaps, diffs, practical
  observations, and demo data;
- the surface contract keeps all mutation and owner-decision authority disabled;
- a downstream SpecSpace implementation can cite this proposal while remaining
  read-only.

## Downstream SpecSpace Acceptance

A SpecSpace implementation that realizes this contract should prove:

- the UI loads `ontology.normalized.json` from the published artifact catalog;
- package metadata, classes/entities, relations, and domains/namespaces are
  visible without opening raw JSON;
- gap and diff summaries are visible when their run artifacts are published;
- raw artifact links still work;
- missing artifacts degrade to explicit unavailable states;
- no UI action writes Ontology packages or SpecGraph specs.

## Next Gap

```text
build_specspace_normalized_ontology_ir_panel
```
