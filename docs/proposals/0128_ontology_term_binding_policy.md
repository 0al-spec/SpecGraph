# Ontology Term Binding Policy

RFC: SG-RFC-0128
Version: 0.1.0

## Status

Implemented

Decision scope: machine-readable review-first policy for ontology term binding
in generated SpecGraph-facing artifacts.

This document adds a policy artifact only. It does not change active prompts,
execute prompt agents, add a hard write gate, mutate canonical specs, accept
ontology terms, write Ontology packages or lockfiles, import owner decisions,
or add SpecSpace mutation UI.

## Source Material

This proposal implements the first bounded child slice of
`0127_ontology_stdlib_type_discipline`.

Source draft:

- `docs/archive/proposal_sources/0128_ontology_term_binding_policy.md`

Related proposal context:

- `0100_ontology_grounded_semantic_control`
- `0116_ontology_semantic_lint_input`
- `0118_ontology_prompt_agent_context_artifact`
- `0119_ontology_canonicalization_backlog`
- `0126_specauthor_claim_calibration_prompt_contract`
- `0127_ontology_stdlib_type_discipline`

## Summary

SpecGraph now has a machine-readable term-binding policy:

```text
tools/ontology_term_binding_policy.json
```

The policy makes the SG-RFC-0127 process rule explicit:

```text
accepted ontology entity -> bind or cite
unknown generated term -> ontology_gap
practical ontology observation -> evidence only
SpecGraph topology edge -> topology evidence, not semantic ontology relation
proposal reference -> reference evidence, not semantic ontology relation
```

The policy is review-first. It gives future prompt contracts and generated
artifact validators a stable vocabulary without enabling canonical mutation or
hard rejection of existing artifacts.

## Goals

- Add `ontology_term_binding_policy`.
- Define authority classes for accepted entities, local bindings, practical
  observations, ontology gaps, topology edges, and proposal references.
- Define a minimum `term_bindings` contract.
- Define a minimum `ontology_gaps` contract.
- Define future generated-artifact gate rules for unknown terms, duplicate
  accepted entities, deprecated/rejected terms, observation authority
  expansion, and topology-as-semantic confusion.
- Keep the first mode `review_warning`, not hard enforcement.

## Non-Goals

- Implementing the generated-artifact write gate.
- Changing active SpecAuthorAgent or supervisor prompts.
- Executing prompt agents.
- Parsing arbitrary natural language.
- Accepting or rejecting ontology terms.
- Writing Ontology packages or ontology lockfiles.
- Mutating `specs/nodes/*.yaml`.
- Importing owner decisions into canonical SpecGraph specs.
- Adding SpecSpace mutation UI.

## Runtime Contract

The policy artifact declares:

```json
{
  "artifact_kind": "ontology_term_binding_policy",
  "schema_version": 1,
  "proposal_id": "0128",
  "policy_status": "review_first_contract",
  "generated_artifact_gate": {
    "default_mode": "review_warning",
    "future_hard_gate_allowed": true
  }
}
```

The authority boundary remains false:

```json
{
  "may_write_ontology_package": false,
  "may_write_ontology_lockfile": false,
  "may_mutate_canonical_specs": false,
  "may_mark_candidate_accepted": false,
  "may_execute_prompt_agent": false,
  "canonical_mutations_allowed": false
}
```

## Term Authority Classes

The policy defines these classes:

- `accepted_ontology_entity`: canonical type symbol owned by Ontology;
- `specgraph_term_binding`: local usage or binding under SpecGraph review;
- `practical_ontology_observation`: derived observed usage evidence;
- `ontology_gap`: candidate missing symbol requiring owner review;
- `specgraph_topology_edge`: graph topology fact such as `depends_on`,
  `relates_to`, or `refines`;
- `proposal_reference`: proposal markdown mention of a spec id.

Only `accepted_ontology_entity` can act as the canonical type symbol. Practical
observations, topology edges, and proposal references remain evidence classes.

## Gap Contract

Unknown generated terms must become gap records before graph-ready persistence:

```yaml
ontology_gaps:
  - proposed_term: ""
    proposed_kind: "entity | relation | alias | domain | context"
    reason: ""
    source_refs: []
    status: "requires_owner_review"
    canonical_mutations_allowed: false
```

The policy allows `needs_more_evidence`, `duplicate_candidate`, and `rejected`
states, but it does not allow SpecGraph to mark a gap accepted. Acceptance
remains with the Ontology owner decision path.

## Future Gate Rules

The policy declares future `reject_if` rules:

- `new_term_without_gap`;
- `duplicate_accepted_entity`;
- `deprecated_or_rejected_term_reused`;
- `observation_marked_accepted`;
- `topology_edge_as_semantic_relation`.

The first implementation mode is `review_warning`. A later proposal may turn
some rules into hard rejection for generated artifacts after fixtures and
operator workflow are stable.

## Acceptance

This slice is complete when:

- `tools/ontology_term_binding_policy.json` exists;
- the policy records SG-RFC-0128 as its source proposal;
- authority-expanding flags remain false;
- tests prove the policy contains the `new_term_without_gap`,
  `observation_marked_accepted`, and `topology_edge_as_semantic_relation`
  guardrails;
- `tools/README.md` documents the policy;
- proposal `0128` is tracked in promotion and runtime registries;
- proposal tracking gate passes;
- documentation sync passes.

## Authority Boundary

This proposal may be used as:

- a machine-readable policy reference for future generated-artifact validators;
- a source of vocabulary for prompt contracts;
- evidence that unknown generated terms must become `ontology_gap` records;
- evidence that practical ontology observations and topology edges are not
  accepted semantic ontology relations.

This proposal may not be used as:

- approval to execute prompt agents;
- approval to add a hard write gate;
- approval to accept, reject, deprecate, or rename ontology terms;
- approval to write Ontology packages or lockfiles;
- approval to mutate canonical SpecGraph specs;
- approval to import owner decisions;
- approval to add SpecSpace mutation UI.

## Next Gap

```text
implement_generated_artifact_term_binding_gate
```
