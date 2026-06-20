# 0143 SpecAuthor Ontology Layer Context

## Status

Implemented

## Source

- `docs/archive/proposal_sources/0143_specauthor_ontology_layer_context.md`

## Summary

SpecAuthor-generated artifacts now need explicit ontology layer context before
they can pass producer contract validation and the ontology write gate.

The active frame must include `ontology_layer_refs`, and every strong generated
claim must declare `ontology_layer_refs` or `layer_refs`. Claim layers must use
known ontology layers and must stay within the active frame.

## Motivation

`0141` imports layer metadata and `0142` makes gap/diff review layer-aware, but
SpecAuthor output could still produce strong claims against a flat ontology
frame. That weakens the goal of narrowing semantic space before specs enter the
graph.

This slice turns layer awareness into a deterministic artifact contract:

- no ontology layer in active frame -> no generated artifact contract pass;
- no layer context on a strong claim -> no graph write;
- claim layer outside active frame -> no graph write.

## Implementation

This slice updates:

- `tools/specauthor_generated_artifact_contract.py`;
- `tools/specauthor_ontology_write_gate.py`;
- ready/review fixtures for both tools;
- regression tests for missing layer context and layer mismatch.

Known ontology layers are:

- `objective`;
- `mechanics`;
- `execution`;
- `meta`;
- `multi_agent`.

## Authority Boundary

This proposal does not make SpecGraph an ontology authority.

It does not:

- infer missing ontology layers;
- write Ontology packages;
- update ontology lockfiles;
- mutate canonical specs;
- accept or reject ontology terms;
- execute prompt agents;
- import owner decisions;
- close semantic gates.

## Validation

- Producer contract tests verify that missing active layer context and missing
  strong-claim layer context are rejected.
- Write-gate tests verify that missing strong-claim layer context and claim
  layers outside the active frame are rejected.
- Ready fixtures include `ontology_layer_refs` and continue to pass.

## Follow-ups

- Add the prompt-side SpecAuthorAgent behavior that emits active layers before
  drafting.
- Reflect the behavior policy in Agent Passport extensions once the runtime
  declaration format is ready.
- Feed layer-aware write-gate findings into richer SpecSpace dashboards.
