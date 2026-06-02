# External Ontology Import Plane

RFC: SG-RFC-0060
Version: 0.1.0

## Status

Draft proposal

Decision scope: graph-side ontology import, binding, proposal, and adjacency
contract.

This document does not define the Ontology package schema, implement
`ontologyc`, execute prompt agents, implement Agent Passport enforcement,
package Docker images, create a hosted registry, or build SpecSpace UI.

## Source Material

This proposal captures the operator request to integrate the sibling Ontology
layer at the lower boundary of mature SpecGraph without bypassing proposal-only
canonical mutation.

Source draft:

- `docs/archive/proposal_sources/0060_external_ontology_import_plane.md`

External Ontology authority:

- Ontology repository: <https://github.com/0al-spec/Ontology>
- Local observed Ontology main: `402889c`
- Current relevant tool contract: `ontologyc import-hypercode` consumes
  `hypercode.ir/v1` and emits a draft `DomainOntologyPackage`.

External Hypercode authority:

- Hypercode repository: <https://github.com/0al-spec/Hypercode>
- Current relevant artifact contract: `hypercode.ir/v1`.

Related external agent authority:

- Agent Passport repository: <https://github.com/0al-spec/agent-passport>

## Summary

SpecGraph should consume external ontology packages through a proposal-first
import plane. Ontology packages, `ontologyc` reports, Hypercode-derived drafts,
and prompt-agent outputs may produce reviewable artifacts and proposals. They
must not mutate canonical SpecGraph state directly.

The import plane gives SpecGraph stable references to external ontology
packages, concepts, prompt packs, import locks, semantic bindings, and gaps
while preserving Ontology as the owner of the reusable ontology compiler and
package contracts.

## Context

SpecGraph already describes itself as an executable product ontology and has a
mature governance model:

```text
SpecGraph governs.
Supervisor executes.
Derived artifacts inform.
Human approval resolves constitutional change.
```

The sibling Ontology repository is now becoming the owner of reusable
`DomainOntologyPackage` artifacts, `ontologyc`, prompt contracts, and Hypercode
IR import tooling. That creates a useful lower semantic layer, but it also
creates a risk:

```text
external ontology compiler or prompt output
  -> looks semantically structured
  -> gets mistaken for canonical SpecGraph truth
```

That path would violate SpecGraph's proposal-first mutation model.

The correct boundary is:

```text
Ontology / Hypercode / Prompt Agent
  -> typed draft or report artifact
  -> ontology import proposal
  -> SpecGraph proposal review
  -> accepted canonical update, if approved
```

## Problem

Without an explicit external ontology import plane:

- SpecGraph may duplicate Ontology package schema and compiler semantics.
- Ontology packages may be copied into SpecGraph without source, version, or
  digest discipline.
- Prompt-generated drafts may be mistaken for accepted graph semantics.
- Semantic bindings between specs and ontology concepts may become informal
  prose instead of reviewable references.
- Future `ontologyc` adapter work has no artifact contract.
- Future prompt-agent work has no isolation, capability, or authority boundary.
- Platform packaging has no stable target for `ontologyc`, prompt packs, or
  package cache materialization.
- SpecSpace cannot safely display ontology import status or review actions.

This is structurally similar to the SpecPM import/handoff boundary: external
structured packages are useful, but they must enter SpecGraph as reviewable
candidates, not as silent canonical mutations.

## Goals

- Define the graph-side import plane for external ontology packages.
- Preserve Ontology as the external authority for ontology package shape,
  compiler behavior, prompt contracts, and Hypercode import semantics.
- Define minimal SpecGraph references for packages, concepts, prompt packs,
  semantic bindings, locks, gaps, and import proposals.
- Require source/version/digest discipline for any package recognized by
  SpecGraph.
- Treat compiler outputs and prompt-agent outputs as proposal artifacts until
  accepted by SpecGraph review.
- Map ontology import and prompt output authority through existing
  `authority_class` semantics.
- Establish adjacency and sequencing for the later `ontologyc` adapter, prompt
  agent invocation, Agent Passport capability policy, Platform packaging, and
  SpecSpace review surface work.

## Non-Goals

- Redefining the Ontology package schema inside SpecGraph.
- Migrating existing SpecGraph nodes into Ontology packages.
- Letting `ontologyc` write `specs/nodes/*.yaml`.
- Letting prompt agents write canonical SpecGraph files.
- Implementing `ontologyc` invocation in the supervisor.
- Implementing prompt-agent execution or SpecAgent runtime.
- Implementing Agent Passport signing, verification, sandboxing, or runtime
  enforcement.
- Implementing a hosted ontology registry.
- Implementing Docker packaging or Platform cache materialization.
- Implementing SpecSpace UI.
- Creating a universal cross-repo package manager.

## Core Proposal

Introduce an **External Ontology Import Plane** as a review-first boundary
between SpecGraph and external ontology tooling:

```text
Hypercode source
  -> hypercode.ir/v1
  -> ontologyc import-hypercode
  -> DomainOntologyPackage draft
  -> OntologyImportProposal
  -> SpecGraph review
  -> accepted import lock or semantic binding change
```

SpecGraph owns the import plane, proposal routing, review semantics, accepted
locks, and graph-side bindings. Ontology owns package validation, compiler
behavior, prompt contracts, and package source material.

## Graph-Side Artifacts

Future bounded implementation slices may introduce these graph-side artifacts.
This proposal defines their intended role, not their final serialization.

### OntologyPackageRef

References one external ontology package without copying it into SpecGraph as
canonical graph truth.

Candidate shape:

```yaml
artifact_kind: ontology_package_ref
schema_version: 1
package:
  package_id: 0al.agent
  namespace: agent
  version: 0.1.0
  source_uri: git+https://github.com/0al-spec/Ontology.git
  source_ref: v0.1.0
  digest: sha256:...
  authority_class: imported
```

### ConceptRef

References a concept inside an ontology package.

Candidate shape:

```yaml
concept_ref:
  package_id: 0al.agent
  namespace: agent
  version: 0.1.0
  concept_id: agent.passport.capability
  display_name: Agent Passport Capability
```

### SemanticBinding

Links a SpecGraph governed subject to one or more external concepts without
claiming that the external concept replaced the subject.

Candidate shape:

```yaml
artifact_kind: semantic_binding
schema_version: 1
subject:
  kind: spec
  id: SG-SPEC-0059
bindings:
  - relation: aligns_with
    concept_ref:
      package_id: 0al.agent
      namespace: agent
      version: 0.1.0
      concept_id: agent.passport
    authority_class: authored
```

### OntologyImportLock

Records the accepted set of ontology package imports recognized by SpecGraph.
Changing the lock is a canonical governance act and must flow through proposal
review.

Candidate path:

```text
specs/imports/ontology.lock.yaml
```

Candidate shape:

```yaml
artifact_kind: ontology_import_lock
schema_version: 1
imports:
  - package_id: 0al.agent
    namespace: agent
    version: 0.1.0
    source_uri: git+https://github.com/0al-spec/Ontology.git
    source_ref: v0.1.0
    digest: sha256:...
    accepted_by_proposal: SG-RFC-0060-followup
```

### OntologyGap

Names a missing or insufficient external concept needed by SpecGraph or a
product workspace.

Candidate shape:

```yaml
artifact_kind: ontology_gap
schema_version: 1
gap_id: ontology-gap-agent-prompt-invocation-context
needed_by:
  - SG-RFC-0060
missing_concept:
  namespace_hint: agent
  concept_hint: prompt_agent_invocation_context
severity: medium
recommended_route: ontology_package_draft
```

### OntologyImportProposal

Represents the reviewable candidate that may update import locks, semantic
bindings, or gap status after approval.

Candidate shape:

```yaml
artifact_kind: ontology_import_proposal
schema_version: 1
proposal_id: ontology-import-2026-0001
inputs:
  package_refs:
    - 0al.agent@0.1.0
  compiler_reports:
    - runs/ontology/ontologyc-check-agent-0.1.0.json
  prompt_invocations:
    - runs/ontology/prompt-invocation-agent-gap-0001.json
proposed_changes:
  lock_updates: true
  semantic_bindings: true
  canonical_node_edits: false
review_state: pending
```

## Prompt-Agent Invocation Boundary

Ontology prompt contracts should not be treated as raw prompt snippets embedded
inside the SpecGraph supervisor. They should be invoked through a future
agent-boundary contract:

```text
PromptPackRef
  -> PromptInvocation
  -> Agent Passport capability profile
  -> isolated context
  -> typed draft artifact
  -> validation/report
  -> proposal
```

Prompt-agent outputs are `inferred` until accepted by review. Even after
acceptance, the accepted canonical subject receives the authority class required
by the canonical act that admits it.

Candidate prompt pack reference:

```yaml
artifact_kind: prompt_pack_ref
schema_version: 1
prompt_pack:
  id: ontology-induction-prompts
  version: 0.1.0
  source_uri: git+https://github.com/0al-spec/Ontology.git
  digest: sha256:...
allowed_outputs:
  - domain_ontology_package_draft
  - ontology_gap_report
  - ontology_import_proposal
```

Prompt agent capability should be default-deny:

```yaml
capabilities:
  read:
    - specgraph.canonical.snapshot
    - ontology.package
    - ontology.prompt_pack
    - hypercode.ir
  write:
    - runs/ontology/*
    - runs/proposals/*
  forbidden:
    - specs/nodes/*
    - canonical_graph.write
    - secrets.read
```

## Authority-Class Mapping

This proposal relies on existing `SG-SPEC-0057` authority-class semantics:

- External ontology package content preserved by import is `imported`.
- Prompt-agent or compiler-generated drafts are `inferred`.
- Source-bounded summaries of ontology packages are `distilled`.
- Human-authored semantic bindings or restatements are `authored`.
- Review approval alone does not change authority class unless the accepted
  canonical act materially restates or replaces the governed expression.

Derived indexes, previews, and prompt guesses must not assign canonical
authority class by viewer inference.

## Storage Boundary

Canonical ontology packages should not live inside SpecGraph as ordinary
`specs/nodes/*.yaml` records.

Recommended storage roles:

| Layer | Responsibility |
| --- | --- |
| Ontology repository | Shared package sources, compiler, prompt contracts, package tests |
| Product workspace | Product/domain-specific ontology packages |
| Published artifact source | Immutable package releases or Git refs with digests |
| Platform cache | Local materialized package cache for tools and containers |
| SpecGraph | Import refs, locks, semantic bindings, gaps, and proposals |
| Docker image | Read-only pinned `ontologyc`, packages, prompts, and digest metadata |

SpecGraph should answer:

> Which ontology packages and concepts are recognized as imported dependencies?

Ontology and registry-like materialization should answer:

> Where is the package, how is it validated, and what digest/version identifies
> it?

## Work Sequence And Adjacency

This proposal is a bridge proposal. It intentionally exists to make a large
multi-repository effort sequenced rather than amorphous.

### Grounded In

- SpecGraph constitution: derived artifacts inform, proposals precede
  constitutional mutation, and human review resolves governance changes.
- `SG-SPEC-0057`: authority-class semantics for authored, imported, inferred,
  and distilled governed subjects.
- Proposal/split readiness and reviewer action semantics in `SG-SPEC-0058` and
  `SG-SPEC-0059`.
- Proposal 0030 and 0031: SpecPM import preview/handoff pattern for external
  structured package candidates.
- Proposal 0051: prompt overlays as additive supervisor guidance, contrasted
  with isolated prompt-agent invocation.
- Proposal 0056: executor adapter gateway as launch-and-observe boundary.
- Proposal 0059: Agent Passport adoption for graph agents.

### Introduces

- `OntologyPackageRef`
- `ConceptRef`
- `SemanticBinding`
- `OntologyImportLock`
- `OntologyGap`
- `OntologyImportProposal`
- `PromptPackRef`
- Prompt-agent invocation boundary for ontology work

### Enables Next

1. `ontologyc` adapter/report contract for SpecGraph.
2. Ontology package index and import gap derived surfaces.
3. Prompt-agent invocation proposal with isolated context and typed outputs.
4. Agent Passport capability profile for ontology prompt agents.
5. Platform packaging for `ontologyc`, prompt packs, package cache, and Docker
   materialization.
6. SpecSpace review surface for ontology import proposals and semantic binding
   review.

### Blocked Until Accepted

- Any canonical `ontology.lock.yaml` adoption.
- Any supervisor code that applies ontology package imports directly.
- Any prompt-agent flow that writes canonical SpecGraph files.
- Any Platform deploy path that claims SpecGraph has accepted ontology packages
  without a SpecGraph import lock.

### Explicitly Does Not Do

- Full SpecAgent runtime.
- Hosted ontology registry.
- Direct Ontology-to-SpecGraph canonical migration.
- Prompt text execution inside the supervisor core prompt.
- Docker packaging.
- SpecSpace mutation UI.

## Future Runtime Realization

The first runtime realization should be a narrow adapter/report slice, not full
automation.

Candidate future artifacts:

```text
tools/ontology_import_policy.json
runs/ontology_package_index.json
runs/ontology_import_gap_index.json
runs/ontology_binding_preview.json
runs/ontology_prompt_invocation_index.json
```

Candidate future commands:

```text
--build-ontology-package-index
--build-ontology-import-gap-index
--build-ontology-binding-preview
```

Any runtime slice must preserve:

- `canonical_mutations_allowed: false` for derived reports;
- no automatic writes to `specs/nodes/*.yaml`;
- no automatic import lock update;
- explicit proposal artifact emission for reviewable changes;
- package source/version/digest in every package reference.

## Acceptance Criteria

- Defines ontology package import as a proposal-first boundary.
- Defines minimal graph-side artifacts for package refs, concept refs,
  semantic bindings, locks, gaps, and import proposals.
- Defines prompt packs and prompt-agent invocation as isolated future agent
  actions, not supervisor prompt replacement.
- Maps imported packages and prompt/compiler outputs to existing
  authority-class semantics.
- Defines storage responsibility across Ontology, product workspaces, Platform,
  Docker images, and SpecGraph.
- Names upstream anchors and downstream work sequence so follow-up PRs have
  explicit adjacency.
- Keeps runtime implementation, registry service, Docker packaging, SpecAgent
  runtime, and SpecSpace UI out of this proposal.
