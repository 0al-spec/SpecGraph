# SpecAuthor Generated Artifact Contract

RFC: SG-RFC-0137
Version: 0.1.0

## Status

Draft proposal

Decision scope: add a deterministic producer-side contract for
`generated_spec_artifact` records emitted by SpecAuthorAgent before downstream
ontology write-gate validation.

## Source Material

Source draft:

- `docs/archive/proposal_sources/0137_specauthor_generated_artifact_contract.md`

Roadmap:

- `docs/ontology_spec_validation_roadmap.md`

Depends on:

- `0126_specauthor_claim_calibration_prompt_contract`
- `0128_ontology_term_binding_policy`
- `0129_generated_term_binding_gate`
- `0136_specauthor_ontology_write_gate`

## Problem

SpecGraph now has a deterministic write gate for SpecAuthor-generated artifacts,
but the producer-side artifact shape is still implicit. Existing fixtures use
`generated_spec_artifact`, yet there is no standalone contract that says what a
SpecAuthorAgent invocation must emit before the artifact reaches the write gate.

Without this contract, a future invocation wrapper could pass loosely shaped
JSON or markdown-like payloads into the write gate. That makes the boundary
between prompt output, review material, and graph-ready material too easy to
blur.

## Proposal

Add:

```bash
make specauthor-generated-artifact-contract \
  SPECAUTHOR_GENERATED_ARTIFACT_CONTRACT_ARTIFACT=<generated-artifact.json>
```

The command emits:

```text
runs/specauthor_generated_artifact_contract_report.json
```

The validator checks that a `generated_spec_artifact` is a typed producer
record, not a free-form draft:

- `artifact_kind: generated_spec_artifact`;
- `schema_version: 1`;
- `contract_ref: specgraph.specauthor.generated-artifact.v0.1`;
- `source_ref`;
- `producer` metadata for `SpecAuthorAgent`, including invocation ref and the
  0126 prompt-contract ref;
- `active_frame` with ontology refs, domain refs, context refs, project,
  subsystem, agent layer, target artifact, and lifecycle phase;
- `target_artifact` metadata scoped to a review draft;
- `draft` payload with declared format and content;
- `materialization_intent` that routes only to review-required downstream write
  gate validation;
- list-valued `new_terms`, `term_bindings`, `ontology_gaps`, and `claims`.

## Implemented Slice

This slice adds:

- `tools/specauthor_generated_artifact_contract.py`;
- `make specauthor-generated-artifact-contract`;
- clear and review-required fixtures under
  `tests/fixtures/specauthor_generated_artifact_contract/`;
- focused tests for contract success, authority expansion, missing context,
  missing draft content, missing producer invocation, and strict CLI behavior;
- proposal tracking metadata.

The validator does not replace `tools/specauthor_ontology_write_gate.py`. It
precedes it. A contract-clear artifact becomes `write_gate_ready: true`, which
means it is shaped well enough to be passed into the downstream write gate.

## Acceptance

This proposal is complete when:

- a review-bound `generated_spec_artifact` with producer metadata, active frame,
  target artifact metadata, draft payload, materialization intent, term
  bindings, gaps, and claims passes the contract;
- authority expansion, missing active context, missing draft payload, missing
  producer invocation, and auto-apply materialization intent are rejected;
- strict CLI mode exits non-zero for rejected artifacts;
- the report keeps ontology writes, lockfile writes, canonical spec mutations,
  and accepted-term authority disabled;
- proposal tracking gates pass.

## Out of Scope

- Running SpecAuthorAgent;
- changing active prompts;
- parsing free-form markdown into typed artifact records;
- invoking the downstream write gate automatically;
- materializing proposal/spec files;
- mutating `specs/nodes/*.yaml`;
- accepting ontology terms;
- writing Ontology packages or lockfiles;
- adding SpecSpace UI for generated artifacts.
