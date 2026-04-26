# 0037. SpecPM Public Registry Observation

## Status

Accepted for implementation.

## Context

SpecPM can now serve a local static public index in dev mode at:

```text
http://localhost:8081
```

The current SpecPM surface is intentionally small:

- `GET /v0/packages/{package_id}`
- `GET /v0/packages/{package_id}/versions/{version}`
- `GET /v0/capabilities/{capability_id}/packages`

There is no global package index endpoint, canonical public authority URL, or
publish/mutation API yet.

## Problem

SpecGraph can materialize local SpecPM draft bundles, but the viewer cannot
tell whether those bundles are visible through SpecPM's public registry
surface. Without a derived observation layer, the operator must manually probe
the registry and compare payloads against the expected package identities and
capabilities.

## Proposal

Add a read-only public registry observation layer for SpecPM:

- declare the local-dev registry contract on the `specpm` external consumer
- add `tools/specpm_public_registry_policy.json`
- add `runs/specpm_public_registry_index.json`
- add a standalone supervisor mode:

```bash
python3 tools/supervisor.py --build-specpm-public-registry-index
```

The registry base URL must be stored as `http://localhost:8081`, not
`http://localhost:8081/v0`. Endpoint templates carry the `/v0/...` prefix.

## Non-Goals

- No package publishing.
- No `SpecPM` checkout writes.
- No canonical `SpecGraph` spec mutation.
- No global package listing assumption.
- No stable public authority claim.

## Viewer Contract

The viewer should surface:

- `registry available`
- `visible in /v0`
- `registry drift`
- `dev observation only`

Use wording such as `registry-visible package versions`, not `published
packages`.

If the local registry is unavailable, treat that as an observation gap with
`next_gap = start_specpm_public_index_service`, not as a lifecycle blocker.
