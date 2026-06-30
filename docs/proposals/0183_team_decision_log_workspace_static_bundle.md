# 0183 Team Decision Log Workspace Static Bundle

Status: implemented.

## Problem

The production SpecSpace route `/team-decision-log` now expects a product
workspace artifact base, for example:

```text
https://specgraph.tech/workspaces/team-decision-log
```

The SpecGraph static publish workflow still produced only the bootstrap root
bundle at `https://specgraph.tech/artifact_manifest.json`. After SpecSpace was
deployed with the workspace-specific artifact base contract, the production
workspace endpoint correctly looked for
`workspaces/team-decision-log/artifact_manifest.json`, but that file was not
published.

That made the product workspace route fail closed even though the bootstrap
bundle remained healthy.

## Proposal

Extend the `Publish Static Artifacts` workflow so it publishes both:

- the ordinary SpecGraph bootstrap/static artifact bundle at the root; and
- a Team Decision Log product workspace bundle under
  `workspaces/team-decision-log/`.

The workflow builds the root bundle first with the existing `make publish-bundle`
target. Then it runs:

```bash
make product-workspace-team-decision-log-happy-path-repair-pack
python tools/build_static_artifact_bundle.py \
  --output-dir dist/specgraph-public/workspaces/team-decision-log
```

The workspace bundle has its own `artifact_manifest.json` and `checksums.sha256`
inside the workspace directory. SpecSpace should consume that workspace-specific
manifest for `/team-decision-log`.

## Authority Boundary

This slice only changes static publishing:

- no prompt-agent execution;
- no canonical spec mutation;
- no candidate approval decision;
- no Ontology package writes or lockfile writes;
- no ontology term acceptance;
- no Git branch, commit, PR, merge, or read-model publication;
- no SpecSpace mutation authority expansion.

The Team Decision Log repair pack remains demo input data. Publishing its
public-safe artifact bundle does not make product artifacts canonical.

## Acceptance Criteria

- `Publish Static Artifacts` uploads a bundle tree that includes
  `workspaces/team-decision-log/artifact_manifest.json`.
- The Team Decision Log workspace bundle is built after the happy-path repair
  pack, so it contains approval-ready demo artifacts.
- The root bundle remains available for the SpecGraph bootstrap/showcase route.
- SpecSpace can configure `/team-decision-log` to use the workspace-specific
  artifact base without falling back to the root bundle.
- Static publishing remains public-safe and does not delete unrelated host
  content.

## Validation

- `tests/test_publish_static_artifacts_workflow.py`
- `make docc-sync`
- `make proposal-tracking-gate`
- local static bundle smoke:
  `make product-workspace-team-decision-log-happy-path-repair-pack` followed by
  `python tools/build_static_artifact_bundle.py --output-dir <workspace-dir>`
