# 0197 Project-Local Ontology Review Lane

Status: implemented.

## Problem

Real idea flows frequently surface useful product terms that are not part of the
structural SpecGraph core ontology. Treating those terms as ordinary unresolved
ontology gaps creates review noise, but automatically accepting them into an
Ontology package would expand authority too early.

Operators need an explicit lane where every project-local product term can be
reviewed as one of:

- keep project-local;
- bind to an existing ontology term;
- alias to another accepted term;
- reject as non-domain vocabulary;
- request a future workspace ontology promotion.

## Proposal

Add a read-only project-local ontology review lane artifact:

```text
runs/project_local_ontology_review_lane.json
```

The lane consumes the candidate graph, optional product ontology decisions,
optional rerun preview evidence, active-candidate context, and repair-session
context. It groups candidate ontology gaps by product term, attaches accepted
decision evidence, shows whether rerun preview resolves the gaps, and emits
operator-facing next actions.

## Authority Boundary

This proposal does not:

- write Ontology packages or lockfiles;
- accept global ontology terms;
- apply decisions to source artifacts;
- mutate candidate artifacts or canonical specs;
- approve candidates;
- create Git branches or commits;
- open pull requests;
- publish read models;
- execute prompt agents.

Workspace ontology promotion is represented only as a review/request state, not
as a package write.

## Acceptance Criteria

- Unreviewed project-local ontology terms are visible as blocking review items.
- Accepted project-local decisions become explicit review evidence.
- Bind, alias, reject, defer, and future promotion-request states have stable
  lane statuses.
- Rerun preview evidence shows whether a reviewed term resolved a candidate
  ontology gap.
- The artifact is public-safe and report-only.
- The lane can be consumed by SpecSpace without inferring status from lower-level
  gaps.

## Validation

- `tests/test_project_local_ontology_review_lane.py`
- `make project-local-ontology-review-lane`
