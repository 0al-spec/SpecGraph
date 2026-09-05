# 0218 Workspace-Scoped Repair Publication

## Status

Implemented bounded workspace publication.

## Problem

Platform repair publication invoked the root `publish-bundle` target. That
target refreshes the default product surfaces before building the bundle, so a
bound real-idea workspace could be reported as published using root Team
Decision Log repair artifacts and Idea Maturity telemetry.

## Decision

Add `publish-workspace-bundle` for durable product workspace bindings. The
target requires an explicit workspace run directory and output directory and
builds the public-safe bundle without `--refresh-publish-surfaces`.

Platform remains responsible for validating the binding and proving that the
selected paths are exactly:

```text
runs/<workspace-id>
workspaces/<workspace-id>
workspaces/<workspace-id>/artifact_manifest.json
```

Legacy unbound publication may continue to use the root target. A bound
publication must validate repair outputs and Idea Maturity under the scoped run
directory and cannot satisfy those checks from root artifacts.

## Authority Boundary

This proposal changes public-safe artifact selection only. It does not mutate
canonical specs, write Ontology packages, accept terms, approve candidates,
execute Git operations, or publish a read model.

## Acceptance Criteria

- Bound repair publication does not refresh default product fixtures.
- The command consumes the run and bundle paths from a validated durable binding.
- Published repair and maturity evidence is checked only under the bound run path.
- Root Team Decision Log artifacts cannot satisfy a bound workspace publication.
- Legacy unbound publication remains compatible.
