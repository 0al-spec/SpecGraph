# 0170 Decision-Backed Repair Chain Target

## Status

Implemented

## Summary

The product `idea-to-spec` workflow now has a single Make target for the full
decision-backed repair chain:

```bash
make product-workspace-decision-backed-repair-chain
```

The target runs the standard product workspace candidate pipeline, validates
clarification answers, derives product ontology gap decisions, feeds those
typed decisions into rerun input, and then builds rerun preview plus rerun
materialization.

## Implementation

The implemented surface is:

- `product-workspace-decision-backed-repair-chain` in `Makefile`;
- help text for the target;
- regression coverage in `tests/test_product_workspace_active_candidate_runner.py`.

The wrapper runs:

```text
product-workspace-active-candidate
-> idea-to-spec-clarification-answers
-> product-ontology-gap-review-decisions
-> idea-to-spec-answer-rerun-input
-> idea-to-spec-rerun-preview
-> idea-to-spec-rerun-materialization
```

When invoking `idea-to-spec-answer-rerun-input`, the wrapper passes
`PRODUCT_ONTOLOGY_GAP_REVIEW_DECISIONS_OUTPUT` as
`IDEA_TO_SPEC_ANSWER_RERUN_INPUT_ONTOLOGY_DECISIONS`. This avoids manual smoke
and CI invocations that forget to provide the decision artifact.

The wrapper also forwards custom output paths between steps so tests and local
smoke runs can keep artifacts isolated from default `runs/*` outputs.

## Authority Boundary

This proposal does not grant write authority.

It does not:

- execute prompt agents;
- infer product semantics with an LLM;
- apply answers or decisions to source artifacts;
- mutate candidate source artifacts;
- mutate canonical SpecGraph specs;
- write Ontology packages or lockfiles;
- accept ontology terms;
- approve candidate graphs;
- create Git branches or commits;
- open pull requests;
- publish read models;
- add SpecSpace mutation UI.

## Validation

- `tests/test_product_workspace_active_candidate_runner.py::test_product_workspace_decision_backed_repair_chain_threads_ontology_decisions`
- `make product-workspace-decision-backed-repair-chain`

## Follow-Ups

- Use this target from smoke/CI paths that need the complete review-only repair
  chain.
- Keep promotion readiness blocked until unresolved ontology gaps, repair
  context, and pre-SIB findings are resolved.
