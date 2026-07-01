# 0189 Candidate-Local Domain Derivation

Status: implemented.

## Problem

Real idea intake can include a broader product/domain frame such as
`domain.home_renovation_project_management`. The active candidate source also
requires a candidate-local domain ref derived from the candidate id, for example
`domain.apartment_renovation_assistant`.

During real-idea smoke runs this mismatch surfaced late as:

```text
active_candidate_domain_mismatch
```

The check was correct, but the operator experience was poor: the intake layer
already knows the candidate id and can carry both the broader product domain and
the candidate-local domain.

## Proposal

Ensure real idea intake source generation preserves broader domain refs and
adds the candidate-local domain ref:

```text
domain.home_renovation_project_management
domain.apartment_renovation_assistant
```

The derived ref is appended only when missing. Existing refs keep their order
and are not replaced. The generated frame records `domain_ref_derivations` for
the candidate-local ref; auto-appended refs are marked
`source: system_derived_candidate_id`, `owner_confirmed: false`, and
`confirmation_required: true` so downstream review/promotion surfaces do not
treat them as user-confirmed domain decisions.

## Authority Boundary

This proposal only normalizes active-frame metadata.

It does not:

- infer domain semantics with an LLM;
- accept ontology terms;
- write Ontology packages or lockfiles;
- mutate candidate or canonical specs;
- approve candidates;
- create Git branches or commits;
- open pull requests.

## Acceptance Criteria

- `user_idea_intake_session` appends `domain.<candidate_id>` when broader
  domain refs are present.
- `user_idea_intake_source` emits event-storming seeds with both broader and
  candidate-local domain refs.
- Auto-appended candidate-local domain refs carry derivation metadata and are
  not marked owner-confirmed.
- Existing candidate-local-only inputs remain unchanged.
- Active-candidate validation no longer produces
  `active_candidate_domain_mismatch` for real ideas that provide a broader
  domain plus candidate id.

## Validation

- `tests/test_user_idea_intake_session.py`
- `tests/test_user_idea_intake_source.py`
- `tests/test_active_idea_to_spec_candidate_source.py`
