# 0187 Real Idea Active Candidate Flow

Status: implemented.

## Problem

Proposals `0184`, `0185`, and `0186` made real idea intake practical:
operators can capture raw local-only idea text, answer intake clarification
questions, materialize a public-safe `user_idea_intake_source`, and keep raw
provenance out of public artifacts.

The remaining friction was the next CLI step. The generated
`user_idea_intake_source` is not the direct input contract for
`product-workspace-active-candidate`; it must first be converted into an
`idea_event_storming_seed`. Operators could accidentally pass the intake source
directly and get a correct but confusing contract mismatch.

## Proposal

Add a deterministic convenience flow:

```bash
make real-idea-intake-active-candidate
```

The target performs the missing bridge explicitly:

```text
ready real idea intake session
  -> user_idea_intake_source
  -> idea_event_storming_seed
  -> product-workspace-active-candidate
```

If no original or clarified intake session exists, the target first runs
`real-idea-intake`. If a clarified intake session exists, the existing
`real-idea-intake-ready-candidate-source` target prefers it over the original
session. Under-specified sessions remain blocked by the existing strict bridge.

The target does not change the core `product-workspace-active-candidate`
contract. It supplies the already-built event-storming seed as
`PRODUCT_WORKSPACE_INTAKE_SOURCE`.

## Guardrail

`product-workspace-active-candidate` now rejects a direct
`user_idea_intake_source` input with a clear operator message:

```text
Build an event-storming seed first with `make user-idea-intake-source ...`
or use `make real-idea-intake-active-candidate`.
```

This preserves the existing contract boundary while making the error actionable.

## Authority Boundary

This proposal does not grant write or execution authority.

It does not:

- execute prompt agents;
- infer missing product semantics with an LLM;
- mutate user intent;
- mutate candidate or canonical specs;
- write Ontology packages or lockfiles;
- accept ontology terms;
- approve candidates;
- create Git branches or commits;
- open pull requests;
- publish read models;
- add SpecSpace mutation UI.

Raw idea text remains local-only in `local_operator_*` artifacts. The new target
only sequences existing review-only artifacts and Make targets.

## Acceptance Criteria

- `make real-idea-intake-active-candidate` materializes an event-storming seed
  before running `product-workspace-active-candidate`.
- The target uses a clarified intake session when one exists.
- Directly passing a `user_idea_intake_source` to
  `product-workspace-active-candidate` fails with an actionable message instead
  of producing an opaque downstream contract mismatch.
- Existing real-intake clarification and bridge targets remain unchanged.
- Raw idea text remains outside public-safe artifacts.

## Validation

- `tests/test_idea_intake_clarification_rerun.py`
- `make real-idea-intake-active-candidate`
- `make proposal-tracking-gate`
