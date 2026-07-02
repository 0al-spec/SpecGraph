# 0199 Project-Local Ontology Decision Effect Report

Status: implemented.

## Problem

Proposals `0197` and `0198` expose project-local ontology terms and validate
SpecSpace-owned operator decisions, but downstream maturity diagnostics still
need a stable review-evidence surface. A ready import preview should improve
Idea Maturity explainability without being mistaken for global Ontology
acceptance or canonical SpecGraph mutation.

## Proposal

Add a review-only effect report:

```text
runs/project_local_ontology_decision_effect_report.json
```

and a Make target:

```bash
make project-local-ontology-decision-effect-report
```

The tool reads:

```text
runs/project_local_ontology_review_lane.json
runs/specspace_project_local_ontology_decision_import_preview.json
  -> runs/project_local_ontology_decision_effect_report.json
```

It summarizes accepted, non-resolving, invalid, and missing project-local
ontology decisions as maturity evidence. Accepted `keep_project_local`,
`bind_existing`, `alias`, `reject`, and `request_workspace_promotion` decisions
become explicit review evidence. Missing, invalid, or deferred decisions remain
visible as blockers or follow-up items.

## Authority Boundary

The effect report does not:

- apply decisions to SpecGraph artifacts;
- mutate candidate or canonical specs;
- write Ontology packages or lockfiles;
- accept Ontology terms;
- promote terms into a workspace ontology;
- approve candidates;
- create Git branches or commits;
- open pull requests;
- publish read models;
- execute prompt agents, SpecGraph, Platform, or Git Service.

The report is review evidence only. Idea Maturity may consume it to explain
project-local ontology review status, but concrete repair, approval, and
promotion gates remain separate.

## Acceptance Criteria

- Ready import previews produce action counts and maturity evidence refs.
- Missing or invalid decisions block project-local ontology maturity evidence.
- Deferred decisions remain visible as non-resolving follow-up.
- `request_workspace_promotion` is a follow-up, not global term acceptance.
- Idea Maturity surfaces project-local ontology review counters and readiness
  explainers without changing existing gates.
- The report remains public-safe and contains no raw/private operator notes.

## Validation

- `tests/test_project_local_ontology_decision_effect_report.py`
- `tests/test_idea_maturity_metrics_report.py`
- `make project-local-ontology-decision-effect-report`
- `make idea-maturity-metrics`
- `make proposal-tracking-gate`
- `make docc-sync`
