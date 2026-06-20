# 0147 Publish SpecAuthor Invocation Artifacts

## Status

Implemented

## Summary

SpecGraph static artifact publishing now treats the SpecAuthor authoring-flow
outputs as public-safe `runs/` surfaces.

The published surfaces are:

- `runs/specauthor_invocation_artifact.json`;
- `runs/specauthor_invocation_artifact_contract_report.json`;
- `runs/specauthor_authoring_flow_report.json`.

## Implementation

This slice updates the static bundle builder so `make publish-bundle` refreshes
`specauthor-authoring-flow` and requires the three public-safe SpecAuthor
surfaces in `artifact_manifest.json`.

The existing bundle safety gates still apply:

- JSON artifacts must parse;
- local paths are redacted;
- secret-like content blocks publication;
- local-only operator artifacts remain denied.

## Authority Boundary

The published SpecAuthor surfaces are derived review artifacts only. They do
not publish raw prompts, raw model outputs, generated draft prose, local private
paths, secrets, canonical spec mutations, Ontology package writes, or lockfile
writes.

## Validation

- `tests/test_static_artifact_bundle.py`
- `make publish-bundle PYTHON=.venv/bin/python`
