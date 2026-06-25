# 0171 Idea-To-Spec Repair Session Journal

## Status

Implemented

## Summary

The product `idea-to-spec` workflow now emits a durable review-only repair
session journal:

```bash
make idea-to-spec-repair-session-journal
```

The journal aggregates the current repair chain into one stable session
artifact:

```text
runs/active_idea_to_spec_candidate.json
runs/idea_to_spec_clarification_requests.json
runs/idea_to_spec_clarification_answers.json
runs/product_ontology_gap_review_decisions.json
runs/idea_to_spec_answer_rerun_input.json
runs/idea_to_spec_rerun_preview.json
runs/idea_to_spec_rerun_materialization.json
runs/idea_to_spec_promotion_gate.json
  -> runs/idea_to_spec_repair_session.json
```

`make product-workspace-decision-backed-repair-chain` now writes the journal as
its final step.

## Motivation

Proposals `0163` through `0170` created a complete review-only repair chain:
clarification requests, accepted answers, typed ontology decisions, rerun
input, rerun preview, rerun materialization, and a convenience Make target.

Downstream consumers still had to reconstruct one product repair session by
joining separate artifacts. SpecSpace needs one stable read model for the
product repair workspace, and Platform/Git Service handoff needs an auditable
summary of the session state before promotion intent is allowed.

## Implementation

The implemented surface is:

- `tools/idea_to_spec_repair_session_journal.py`;
- `make idea-to-spec-repair-session-journal`;
- `runs/idea_to_spec_repair_session.json`;
- final-step integration in `make product-workspace-decision-backed-repair-chain`;
- focused regression coverage in
  `tests/test_idea_to_spec_repair_session_journal.py`;
- Make integration coverage in
  `tests/test_product_workspace_active_candidate_runner.py`.

The journal records:

- candidate/workspace identity;
- source artifact refs, digests, summaries, and readiness states;
- ordered repair stages;
- accepted clarification answers;
- typed product ontology decisions;
- rerun overlay and preview refs;
- resolved/unresolved ontology gap counts;
- whether the candidate is ready for approval or Platform promotion.

## Contract

The artifact kind is:

```text
idea_to_spec_repair_session_journal
```

The contract ref is:

```text
specgraph.idea-to-spec.repair-session-journal.v0.1
```

The default output is:

```text
runs/idea_to_spec_repair_session.json
```

The builder validates artifact kind, contract ref, schema version,
`canonical_mutations_allowed`, `tracked_artifacts_written`, and authority
boundary flags for each input artifact. It also checks that chained source refs
match the journal input paths, so a stale answer, decision, rerun, or preview
artifact cannot silently masquerade as the current session.

## Authority Boundary

This proposal does not grant write authority.

It does not:

- execute prompt agents;
- apply answers to source artifacts;
- apply ontology decisions to source artifacts;
- mutate candidate source artifacts;
- mutate canonical SpecGraph specs;
- write Ontology packages or lockfiles;
- accept ontology terms;
- approve candidate graphs;
- create Git branches or commits;
- open pull requests;
- publish read models;
- add SpecSpace mutation UI.

The journal is a durable audit/read-model surface only.

## Validation

- `tests/test_idea_to_spec_repair_session_journal.py`
- `tests/test_product_workspace_active_candidate_runner.py::test_product_workspace_decision_backed_repair_chain_threads_ontology_decisions`
- `make idea-to-spec-repair-session-journal`
- `make product-workspace-decision-backed-repair-chain`

## Follow-Ups

- Teach SpecSpace product repair workspace to use
  `idea_to_spec_repair_session` as its primary model.
- Let future SpecSpace-owned answer/decision draft state replay into this
  session without mutating candidate artifacts.
- Require a ready repair session before Platform Git Service promotion intent
  can move beyond report-only planning.
