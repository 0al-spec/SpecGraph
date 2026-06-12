# Ontology-Grounded Semantic Control

RFC: SG-RFC-0100
Version: 0.1.0

## Status

Draft proposal

Decision scope: graph-facing semantic grounding for SpecGraph supervisor
agents, SpecSpace shell agents, and ontology delta review artifacts.

This document does not implement runtime linting, invoke `ontologyc`, execute
prompt agents, mutate canonical specs, write canonical ontology packages, or
build SpecSpace UI.

## Source Material

This proposal captures the operator intent that Ontology should reduce
assistant hallucination and terminology drift by fixing accepted vocabulary,
domain boundaries, and relations for graph-facing agents.

Source draft:

- `docs/archive/proposal_sources/0100_ontology_grounded_semantic_control.md`

Related draft proposal context:

- `0011_pre_spec_semantic_layer`
- `0060_external_ontology_import_plane`
- `0062_proto_graph_recursive_refinement`
- `0092_executor_report_consumption_policy`

Related implemented contract:

- `docs/ontologyc_adapter_report_contract.md`

## Summary

SpecGraph should treat Ontology as a **semantic control layer** for
graph-facing generation, not only as an external import source. Supervisor
agents and SpecSpace shell agents may propose ontology additions or extensions,
but they must use typed review artifacts and must not silently turn generated
terms into canonical vocabulary.

The control loop is:

```text
accepted ontology context
  -> agent generation request
  -> semantic term classification
  -> generated proposal/spec/review draft
  -> semantic lint report
  -> ontology gap, clarification question, or delta candidate
  -> human/Ontology/SpecGraph review
```

The goal is to reduce:

- hallucinated domain entities;
- misunderstood terms;
- wrong synonyms for already accepted concepts;
- invented relations that conflict with accepted relation vocabulary;
- accidental cross-domain leakage.

## Problem

The current Ontology line gives SpecGraph a useful external import boundary,
adapter report, package index, gap index, governance evidence index, and binding
preview. That is necessary but incomplete.

Agents still need a graph-native rule for what to do when they write with
domain language:

```text
agent sees product intent
  -> chooses plausible terms
  -> writes spec/proposal/review text
  -> plausible terms look authoritative
```

Without an explicit semantic control layer:

- an agent may use a near synonym when the graph already has an accepted term;
- an agent may collapse two distinct domain concepts into one term;
- an agent may invent relation names that look consistent but are not accepted;
- a missing concept may be hidden inside prose instead of becoming an
  `OntologyGap`;
- SpecSpace may display fluent text without showing whether it is grounded in
  accepted ontology material.

## Goals

- Define Ontology-grounded semantic control for graph-facing agents.
- Provide accepted vocabulary, alias, deprecation, domain, and relation context
  to generation requests.
- Classify generated terminology as accepted, alias, deprecated, ambiguous,
  unknown, out-of-domain, or candidate-delta.
- Convert unresolved terminology into reviewable artifacts instead of silent
  canonical claims.
- Allow agents to propose ontology extensions through typed
  `OntologyDeltaCandidate` artifacts.
- Keep Ontology package schema, validation, and governance authority in the
  Ontology repository.
- Keep SpecGraph proposal review as the boundary before graph semantics or
  bindings change.
- Give SpecSpace a future stable review surface for grounded terms, gaps,
  evidence, and review actions.

## Non-Goals

- Replacing the External Ontology Import Plane from `0060`.
- Replacing proto-graph seed generation from `0062`.
- Replacing the Pre-Spec Semantic Layer from `0011`.
- Running prompt packs inside the supervisor.
- Letting agents write canonical Ontology packages directly.
- Letting `ontologyc` or agents write `specs/nodes/*.yaml`.
- Creating canonical `specs/imports/ontology.lock.yaml`.
- Creating a SpecSpace mutation UI.
- Treating semantic lint pass as proof that a generated answer is correct.
- Blocking creative draft terminology before the system can ask for review.

## Control Model

The semantic control layer has three stages.

### 1. Grounding Context

Before a supervisor agent or SpecSpace shell agent generates graph-facing text,
the invocation should receive a bounded ontology context pack.

Candidate artifact:

```text
runs/ontology_semantic_context_pack.json
```

Candidate shape:

```json
{
  "artifact_kind": "ontology_semantic_context_pack",
  "schema_version": 1,
  "canonical_mutations_allowed": false,
  "tracked_artifacts_written": false,
  "source_artifacts": {
    "ontology_package_index": "runs/ontology_package_index.json",
    "ontology_binding_preview": "runs/ontology_binding_preview.json",
    "ontology_governance_evidence_index": "runs/ontology_governance_evidence_index.json"
  },
  "scope": {
    "target_kind": "proposal|spec|review_surface|product_workspace",
    "target_ref": "SG-RFC-0100"
  },
  "accepted_terms": [],
  "aliases": [],
  "deprecated_terms": [],
  "relations": [],
  "domain_boundaries": [],
  "unresolved_gaps": []
}
```

The context pack is a bounded prompt input and review aid. It is not an
ontology package, not a lockfile, and not canonical graph state.

### 2. Term Classification And Lint

After generation, SpecGraph should be able to produce a semantic lint report
over the generated output.

Candidate artifact:

```text
runs/ontology_semantic_lint_report.json
```

Candidate statuses:

```text
grounded
grounded_with_aliases
review_required_unknown_terms
review_required_ambiguous_terms
blocked_deprecated_terms
blocked_relation_conflict
blocked_out_of_domain
ontology_context_unavailable
```

Candidate term classifications:

```text
accepted_term
accepted_alias
deprecated_term
ambiguous_term
unknown_term
out_of_domain_term
relation_conflict
candidate_delta_term
```

The report should preserve evidence references, source spans, ontology concept
refs, and suggested review actions. It should not rewrite the generated text by
itself.

### 3. Delta Candidate Review

When an agent encounters a missing or insufficient concept, it may emit an
ontology delta candidate.

Candidate artifact:

```yaml
artifact_kind: ontology_delta_candidate
schema_version: 1
candidate_id: ontology-delta-0100-0001
producer:
  surface: specgraph.supervisor|specspace.shell
  invocation_ref: runs/ontology_delta_invocation_0100_0001.json
target:
  ontology_hint: product.workspace
  namespace_hint: agent
delta:
  kind: add_concept|add_relation|add_alias|deprecate_term|split_concept
  proposed_label: Accepted Vocabulary Context Pack
  rationale: Agent output needs a stable concept for bounded ontology context.
evidence_refs:
  - runs/ontology_semantic_lint_report.json
authority_boundary:
  candidate_is_authority: false
  ontology_governance_required: true
  specgraph_proposal_review_required: true
  canonical_mutations_allowed: false
```

An `OntologyDeltaCandidate` is not an accepted ontology delta. It is a review
object that may be routed to Ontology governance, SpecGraph proposal review, or
a clarification question.

## Agent Invocation Boundary

Agents may participate in ontology generation or extension only through typed
invocation artifacts.

The invocation boundary should record:

- source request and target scope;
- context pack refs;
- accepted ontology package refs and digests;
- generated output refs;
- semantic lint report refs;
- proposed delta refs;
- failure modes;
- capability and privacy boundary.

Forbidden in this proposal:

- embedding raw ontology prompts as hidden supervisor behavior;
- giving agent output direct ontology authority;
- letting SpecSpace write ontology mutations from UI actions;
- persisting raw prompts, raw responses, secrets, or machine-local paths in
  viewer-facing artifacts.

## Authority Boundary

Ontology owns:

- ontology package schema;
- `ontologyc` behavior;
- package validation;
- ontology governance decision semantics;
- accepted ontology package versions.

SpecGraph owns:

- graph-facing semantic control policy;
- proposal review;
- graph-side semantic bindings;
- term lint report contracts;
- review routing for gaps and delta candidates.

SpecSpace owns:

- operator review presentation;
- shell-agent interaction surface;
- review actions that call back into SpecGraph/Ontology workflows.

SpecSpace must not become the authority for ontology acceptance merely because
it displays a term, gap, or delta candidate.

## Relationship To Existing Proposals

`0011_pre_spec_semantic_layer` captures raw and synthesized intent before
canonical promotion. This proposal adds ontology-grounded vocabulary control to
agent generation over that material.

`0060_external_ontology_import_plane` defines how external Ontology artifacts
enter SpecGraph as read-only references, gaps, governance evidence, and import
proposals. This proposal consumes those surfaces as grounding context and adds
the missing generation-time and review-time control loop.

`0062_proto_graph_recursive_refinement` uses ontology-backed seed concepts to
produce shallow proto-graph structure. This proposal adds term and relation
discipline around that generation so proto-graph labels do not drift away from
accepted vocabulary.

`0092_executor_report_consumption_policy` and its follow-up packet/promotion
line establish that generated agent artifacts are review inputs, not authority.
Ontology delta candidates should follow the same posture.

## Future Bounded Slices

1. Add `ontology_semantic_control_policy` and a read-only semantic context/lint
   fixture over the existing `0060` ontology import surfaces.
2. Add a typed `ontology_delta_invocation` artifact for supervisor and
   SpecSpace shell agents.
3. Add a SpecSpace-facing review packet contract that can display grounded
   terms, unresolved gaps, governance evidence, and allowed review actions.
4. Only after those surfaces stabilize, consider canonical ontology lock or
   binding proposal workflows.

## Acceptance Criteria

- Agent-facing ontology context is source/version/digest aware.
- Generated terms can be classified without becoming canonical vocabulary.
- Unknown or ambiguous terms produce gaps, clarification questions, or delta
  candidates.
- Deprecated or conflicting terms can block promotion until reviewed.
- Ontology delta candidates are review objects, not accepted ontology changes.
- SpecSpace can eventually render the review surface without reading raw run
  logs.
- No prompt-agent execution, canonical spec mutation, ontology package write, or
  SpecSpace mutation UI is introduced by this proposal.

## Next Gap

```text
define_ontology_semantic_control_policy
```
