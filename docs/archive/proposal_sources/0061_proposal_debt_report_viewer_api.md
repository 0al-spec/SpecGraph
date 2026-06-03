# Proposal Debt Report Viewer API Source Draft

## Source Context

The operator asked whether the growing set of incoming proposals that have not
yet been materialized can be exposed as a deterministic debt/gap surface for
SpecSpace.

SpecGraph already computes the underlying information through:

- `runs/proposal_runtime_index.json`
- `runs/graph_backlog_projection.json`

Those artifacts can identify proposals with open runtime, validation, or
observation gaps. However, they are broader than the desired UI concept. A
viewer that wants to show "proposal materialization debt" currently has to infer
meaning from lower-level artifacts.

## Operator Intent

Create a proposal-first plan for a dedicated viewer-facing proposal debt API.

The desired surface should make it easy for SpecSpace to render:

- total proposal debt count;
- proposals grouped by runtime status;
- proposals grouped by next gap;
- missing runtime markers;
- suggested bounded follow-up action;
- links back to source proposal documents and runtime index provenance.

The first step should be a proposal, not immediate implementation.

## Desired Boundary

SpecGraph owns the deterministic artifact:

```text
runs/proposal_debt_report.json
```

SpecSpace may expose it through:

```text
GET /api/v1/proposal-debt
```

SpecSpace should not be required to parse raw `proposal_runtime_index` semantics
to discover proposal debt.

## Non-Goals

This proposal should not:

- implement the report immediately;
- add SpecSpace UI;
- mutate canonical specs;
- change proposal prioritization semantics;
- hide proposal debt behind general backlog terminology;
- replace `proposal_runtime_index` or `graph_backlog_projection`.
