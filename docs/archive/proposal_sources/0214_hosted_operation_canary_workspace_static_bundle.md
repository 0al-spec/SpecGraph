# 0214 Hosted Operation Canary Workspace Static Bundle

## Status

Implemented bounded static-publication slice.

## Problem

The durable workspace binding for `hosted-operation-canary` identifies the
public artifact base:

```text
https://specgraph.tech/workspaces/hosted-operation-canary
```

Proposal `0213` and the replacement promotion review published a tracked,
public-safe 59-file candidate packet, but the static publish workflow still
created workspace bundles only for Team Decision Log. The binding URL therefore
could not serve the packet after a clean deployment.

## Decision

The static artifact workflow now builds a second product workspace bundle from
the tracked Hosted Operation Canary packet:

```bash
python tools/build_static_artifact_bundle.py \
  --output-dir dist/specgraph-public/workspaces/hosted-operation-canary
```

The existing deploy job uploads the complete `dist/specgraph-public` tree, so
the workspace receives its own `artifact_manifest.json` and
`checksums.sha256`. A repository test verifies that all 59 approved paths are
tracked, digest-pinned approval sources resolve, Idea Maturity is ready at the
`promotion_requested` stage, and machine-local host paths are absent.

## Authority Boundary

This proposal changes static publication only. It does not:

- start the production hosted worker;
- enqueue or execute a managed operation;
- mutate canonical specs or Ontology packages;
- accept ontology terms;
- approve another candidate;
- create or merge another Git review;
- publish a post-merge read model.

The published packet remains review evidence. Its presence at a durable URL
does not make the candidate canonical and does not expand SpecSpace authority.

## Acceptance Criteria

- The publish workflow creates
  `workspaces/hosted-operation-canary/artifact_manifest.json`.
- The manifest contains the 59 approved packet paths.
- Candidate approval source digests match the published active candidate and
  promotion gate.
- Idea Maturity remains `ready` at lifecycle `promotion_requested`, with zero
  blockers and stale refs, and its validation report is `ok`.
- Static bundle safety validation passes.
- The production URL returns the workspace manifest and packet artifacts after
  deployment from `main`.
