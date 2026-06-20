# Project-Local Ontology Authoring Commands

RFC: SG-RFC-0133
Version: 0.1.0

## Status

Draft proposal

Decision scope: add review-only project-local ontology package authoring
commands and record the next five-PR ontology validation roadmap.

## Source Material

Source draft:

- `docs/archive/proposal_sources/0133_project_local_ontology_authoring_commands.md`

Roadmap:

- `docs/ontology_spec_validation_roadmap.md`

Depends on:

- `0132_project_local_ontology_package_boundary`

## Problem

Proposal 0132 moved the default SpecGraph Core ontology source to a
project-local package root. That fixes the storage boundary, but operators still
lack small, stable commands for inspecting package authoring state.

Without dedicated commands, package edits are easy to confuse with:

- canonical `specs/nodes/*.yaml` mutation;
- ontology lockfile adoption;
- owner acceptance of terms;
- SpecSpace mutation UI;
- prompt-agent execution.

## Proposal

Add review-only package authoring commands:

```bash
make ontology-package-validate
make ontology-package-preview
make ontology-package-gaps
```

The commands emit:

- `runs/ontology_package_authoring_report.json`;
- `runs/ontology_package_preview.json`;
- `runs/ontology_package_gap_preview.json`.

Each artifact must declare:

- `canonical_mutations_allowed: false`;
- `tracked_artifacts_written: false`;
- no lockfile updates;
- no accepted-term decisions;
- no SpecSpace writes.

## Implemented Slice

This slice adds:

- `tools/ontology_package_authoring.py`;
- Makefile targets for validate, preview, and gaps;
- roadmap documentation for the next five PRs;
- focused regression tests for output shape and authority boundaries.

## Acceptance

This proposal is complete when:

- the three Make targets write typed `runs/` artifacts;
- the validation artifact reports the project-local package source;
- the preview artifact exposes resolved/unresolved refs and compatibility
  summary;
- the gaps artifact exposes reviewable ontology gaps;
- tests assert the commands are review-only and do not claim mutation authority;
- proposal tracking gates pass.

## Out of Scope

- Running `ontologyc` directly;
- editing package YAML interactively;
- mutating canonical specs;
- writing or adopting canonical ontology lockfiles;
- accepting or rejecting terms;
- SpecSpace UI;
- SpecAuthor write gate enforcement.

