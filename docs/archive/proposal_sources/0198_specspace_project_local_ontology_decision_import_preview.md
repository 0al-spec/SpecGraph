# 0198 SpecSpace Project-Local Ontology Decision Import Preview

Status: implemented.

## Problem

Proposal `0197` gives SpecGraph a read-only lane for project-local product
ontology terms. SpecSpace can now collect operator decisions for that lane, but
that state is SpecSpace-owned and mutable. SpecGraph must not treat it as
authority until it is validated against the current lane artifact.

Without a typed import preview, downstream flows could confuse local operator
intent with accepted ontology terms or with applied SpecGraph mutations.

## Proposal

Add a review-only import preview:

```text
runs/specspace_project_local_ontology_decision_import_preview.json
```

and a Make target:

```bash
make specspace-project-local-ontology-decision-import-preview
```

The tool reads:

```text
runs/project_local_ontology_review_decisions.json
runs/project_local_ontology_review_lane.json
  -> runs/specspace_project_local_ontology_decision_import_preview.json
```

It validates the SpecSpace-owned decision state, verifies workspace/candidate/
repair-session identity, checks every decision against the lane term and allowed
action set, emits sanitized decision candidates, and reports missing, invalid,
or deferred decisions.

## Authority Boundary

The import preview does not:

- apply decisions to SpecGraph artifacts;
- mutate candidate or canonical specs;
- write Ontology packages or lockfiles;
- accept Ontology terms;
- request or perform workspace ontology promotion;
- approve candidates;
- create Git branches or commits;
- open pull requests;
- publish read models;
- execute prompt agents, SpecGraph, Platform, or Git Service.

The output is operator-intent evidence only. A later slice may consume a ready
preview as input to rerun or maturity accounting, but this proposal only
validates and summarizes the handoff.

## Acceptance Criteria

- SpecSpace-owned state with authority-expanding flags is rejected.
- Decisions for unknown terms, stale lane refs, mismatched workspace/candidate/
  session ids, or disallowed actions are invalid.
- `keep_project_local`, `bind_existing`, `alias`, `reject`, and
  `request_workspace_promotion` can produce sanitized decision candidates.
- `defer` remains visible as non-resolving review evidence and blocks ready
  status.
- Missing required lane decisions block ready status.
- The preview remains public-safe and contains no raw/private operator notes.

## Validation

- `tests/test_specspace_project_local_ontology_decision_import_preview.py`
- `make specspace-project-local-ontology-decision-import-preview`
- `make proposal-tracking-gate`
- `make docc-sync`
