# 0215 Incremental Static Workspace Deployment

## Status

Implemented bounded static-publication optimization.

## Problem

The production static workflow rebuilds the root artifact surface and two product
workspace bundles, then runs one recursive `lftp mirror -R` over the complete
tree. After proposal `0214`, the upload spent about 30 minutes traversing and
transferring thousands of small files even though the tracked Hosted Operation
Canary packet was already unchanged on the static host.

## Decision

The deploy job now computes a checksum-aware payload stage for each independently
manifested surface:

- the root SpecGraph artifact bundle;
- Team Decision Log;
- Hosted Operation Canary.

The staging tool compares each local `artifact_manifest.json` with the manifest
at the durable HTTPS base and copies only added or content-changed payload files
into one remote-root-shaped staging directory. Manifest-matched files are also
checked at the HTTPS origin, so a missing or stale payload is staged again and
the next deploy self-heals partial publication. Removed files remain physically
present because the shared webroot is non-destructive, but the new manifest no
longer authorizes them.

Deployment uploads the changed payload first, then each `checksums.sha256`, and
finally each `artifact_manifest.json`. A post-upload verifier downloads each
published manifest, checksum file, and manifest-authorized payload from all
three HTTPS bases and checks its SHA-256. A missing, malformed, partial, or
digest-mismatched public surface fails the job.

The Hosted Operation Canary bundle also publishes its scoped initialization
execution report at the top-level `runs/` bootstrap path. That single
public-safe alias lets SpecSpace discover and validate the durable workspace
binding before it follows the binding's scoped `runs/hosted-operation-canary`
refs. The remaining artifacts stay scoped and are not flattened by route slug.

## Authority Boundary

This proposal changes static artifact transport only. It does not:

- delete remote webroot files;
- publish files absent from a public-safe manifest;
- start Platform or hosted workers;
- execute managed operations;
- mutate canonical specs or Ontology packages;
- approve candidates, create Git reviews, or publish read models.

Remote manifests are planning hints, not final authority. Successful
post-publication HTTP digest verification is required.

## Acceptance Criteria

- Unchanged files are absent from the staged payload.
- Changed root and workspace payloads retain their relative durable URL paths.
- Path traversal and local digest mismatches fail closed.
- Payload upload precedes checksums and manifest finalization.
- All three published surfaces receive post-upload HTTP digest verification.
- Hosted Operation Canary exposes a public-safe initialization bootstrap alias
  without flattening the remaining scoped run artifacts.
- Root-level `mirror --delete` remains forbidden.
- Static bundle safety validation and existing publication tests pass.
