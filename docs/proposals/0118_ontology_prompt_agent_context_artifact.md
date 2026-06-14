# Ontology Prompt-Agent Context Artifact

RFC: SG-RFC-0118
Version: 0.1.0

## Status

Implemented

Decision scope: typed, read-only ontology grounding context for future
prompt-agent invocations.

This document does not execute prompt agents, persist raw prompts or raw
responses, write Ontology packages, update ontology lockfiles, mutate canonical
SpecGraph specs, accept candidate terms, close semantic gates, or make a prompt
context artifact canonical ontology authority.

## Source Material

This proposal implements the next bounded runtime slice after
`0117_ontology_supervisor_soft_gate_wiring`.

Source draft:

- `docs/archive/proposal_sources/0118_ontology_prompt_agent_context_artifact.md`

## Summary

`runs/ontology_prompt_invocation_index.json` is now a typed prompt-agent
ontology context artifact rather than an empty 0060 placeholder when the
semantic control policy is available.

The artifact records the semantic context that a future prompt-agent invocation
should receive before graph-facing drafting:

- package refs, package versions, source refs, and digests;
- accepted terms and accepted relations;
- aliases and their accepted targets;
- deprecated terms and replacement refs;
- relation conflicts and accepted relation refs;
- unresolved ontology gaps;
- governance evidence refs;
- prompt input refs and output refs;
- failure modes for missing context, missing output, or invalid downstream
  review artifacts.

The integration mode is `context_only_no_execution`. The prompt-agent is not
run by this slice. The artifact records `prompt_agent_executed: false`,
`prompt_agent_execution_allowed: false`, `raw_prompt_persisted: false`, and
`raw_response_persisted: false`.

## Goals

- Add `prompt_agent_ontology_context_contract` to the semantic control policy.
- Generate `runs/ontology_prompt_invocation_index.json` from the existing
  ontology semantic context pack, lint input, lint report, review packet, and
  supervisor semantic gate.
- Carry stable prompt input refs, prompt output refs, package refs, context
  digest, context sections, evidence refs, and failure modes.
- Keep the artifact read-only and non-authoritative.
- Preserve the old 0060 placeholder behavior when semantic policy is absent.
- Cover execution-boundary rejection and generated artifact shape in focused
  tests.

## Non-Goals

- Prompt-agent execution.
- Raw prompt or raw response persistence.
- Automatic ontology delta drafting.
- Ontology package writes or ontology lockfile updates.
- Canonical `specs/nodes/*.yaml` mutation.
- Accepting candidate terms or closing semantic gates.
- SpecSpace mutation UI.
- Strict ontology compiler enforcement.

## Runtime Contract

The generated artifact declares:

```json
{
  "artifact_kind": "ontology_prompt_invocation_index",
  "schema_version": 1,
  "proposal_id": "0118",
  "integration_mode": "context_only_no_execution",
  "canonical_mutations_allowed": false,
  "tracked_artifacts_written": false,
  "prompt_agent_executed": false,
  "prompt_agent_execution_allowed": false,
  "raw_prompt_persisted": false,
  "raw_response_persisted": false,
  "source_artifacts": {
    "semantic_context_pack": "runs/ontology_semantic_context_pack.json",
    "semantic_lint_input": "runs/ontology_semantic_lint_input.json",
    "semantic_lint_report": "runs/ontology_semantic_lint_report.json",
    "ontology_delta_candidate_review_packet": "runs/ontology_delta_candidate_review_packet.json",
    "ontology_supervisor_semantic_gate": "runs/ontology_supervisor_semantic_gate.json"
  },
  "invocations": [
    {
      "invocation_kind": "prompt_agent_ontology_context",
      "status": "context_ready_no_invocation",
      "prompt_agent_executed": false,
      "prompt_input_materialized": true,
      "prompt_output_materialized": false
    }
  ]
}
```

Each invocation contains the bounded context sections from
`ontology_semantic_context_pack`: packages, accepted terms, accepted relations,
aliases, deprecated terms, relation conflicts, unresolved gaps, and governance
evidence.

## Authority Boundary

The prompt-agent context artifact may be used as:

- grounding input for a later prompt-agent invocation;
- evidence that a prompt-agent boundary had a typed ontology context available;
- SpecGraph/SpecSpace review context for explaining terminology choices.

The artifact may not:

- execute a prompt-agent by itself;
- persist raw prompts or raw responses;
- prove that a generated answer is correct;
- become canonical authority for accepted terms or relations;
- write Ontology packages or lockfiles;
- mutate canonical SpecGraph specs;
- mark ontology candidates accepted;
- close semantic gates.

## Acceptance

This slice is complete when:

- `tools/ontology_semantic_control_policy.json` declares
  `prompt_agent_ontology_context_contract`;
- `tools/ontology_imports.py` builds
  `ontology_prompt_invocation_index` proposal `0118` from validated semantic
  artifacts;
- `make ontology-imports` writes
  `runs/ontology_prompt_invocation_index.json`;
- focused tests verify the artifact shape and reject prompt execution boundary
  expansion;
- proposal `0118` is tracked in promotion and runtime registries;
- proposal gates, DocC sync, and focused Python tests pass.

## Next Gap

```text
produce_ontology_owner_decisions
```
