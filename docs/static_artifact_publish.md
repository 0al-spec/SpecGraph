# Static Artifact Publish

SpecGraph can publish a static, HTTP-readable artifact mirror for SpecSpace or
other read-only consumers.

The intended public shape is:

```text
https://specgraph.tech/specs/
https://specgraph.tech/runs/
https://specgraph.tech/artifact_manifest.json
https://specgraph.tech/checksums.sha256
```

## Local Bundle

Build the bundle locally:

```bash
make publish-bundle
```

This runs `make viewer-surfaces` and `make implementation-work`, then writes a
static mirror under:

```text
dist/specgraph-public/
```

The bundle includes:

- `specs/`
- `runs/`
- `artifact_manifest.json`
- `checksums.sha256`

Deployment mirrors the contents of `dist/specgraph-public/` into
`SFTP_REMOTE_ROOT`. It must not create a nested `specgraph-public/` directory on
the static host.

Artifact deployment is intentionally non-destructive for the webroot. The
workflow must not run a root-level `mirror --delete` because the same
`SFTP_REMOTE_ROOT` can also contain the public landing page and hosting-managed
files. Consumers should use `artifact_manifest.json` and `checksums.sha256` as
the authoritative artifact index instead of inferring validity from every file
that happens to remain under `specs/` or `runs/`.

The repository landing page is deployed by a separate workflow job from
`landing/` into the same `SFTP_REMOTE_ROOT`. That job is also non-destructive and
excludes local QA screenshots under `landing/check/`. Landing files are not part
of `artifact_manifest.json`; the manifest describes only the SpecGraph artifact
surface.

The source `runs/` directory remains local and unchanged. The publish bundle is
a redacted mirror: local absolute paths such as `/Users/...` are replaced with
`$LOCAL_PATH` in the copied files.

## Safety Gate

The bundle builder fails before upload when it finds:

- malformed `runs/**/*.json`;
- secret-like content such as private key markers, `API_KEY=...`, or JSON keys
  named `api_key`, `authorization`, or `password`;
- missing core viewer surfaces:
  - `runs/graph_dashboard.json`
  - `runs/graph_backlog_projection.json`
  - `runs/graph_next_moves.json`
  - `runs/implementation_work_index.json`
  - `runs/spec_activity_feed.json`

Junk files such as `.DS_Store` and `.gitkeep` are not published.

## Static Host Deployment

The GitHub Actions workflow `.github/workflows/publish-static-artifacts.yml`
builds the bundle on PRs and can upload it from `main` or manual
`workflow_dispatch` runs.

After `.github/workflows/deploy-connection-check.yml` is present on the base
branch, pull requests from branches in this repository also run `Check deploy
connection` through `pull_request_target`. The check uses deploy tooling from
the trusted base commit, reads the `FTP` Environment secrets, validates the
deploy contract, and opens a real FTP/FTPS/SFTP connection to list
`SFTP_REMOTE_ROOT` without running `mirror` or uploading files. It does not
checkout or execute pull-request-controlled code in secret-bearing steps. Pull
requests from forks do not receive deployment secrets and skip this job.

The deploy job uses the GitHub Environment named `FTP`. Configure these
environment secrets:

```text
SFTP_HOST
SFTP_PORT
SFTP_USER
SFTP_PASSWORD
SFTP_PRIVATE_KEY
SFTP_KNOWN_HOSTS
SFTP_REMOTE_ROOT
FTPS_ALLOW_UNVERIFIED_CERT
```

For ordinary ISPmanager FTP accounts, use:

```text
SFTP_PORT=21
SFTP_USER=<FTP account>
SFTP_PASSWORD=<FTP password>
SFTP_REMOTE_ROOT=/www/specgraph.tech/
```

`SFTP_REMOTE_ROOT` must be the site directory served by the public HTTP origin,
not the FTP account root. The workflow rejects `/` because deploy uses
root-level uploads into the configured path; pointing it at the FTP account root
could pollute unrelated sites or hosting files.

Despite the historical `SFTP_*` secret names, port `21` makes the workflow use
`ftp://` through `lftp` with TLS forced. If the host does not support FTPS, the
deploy fails instead of sending credentials over plain FTP. `SFTP_KNOWN_HOSTS`
is ignored for port `21`. `SFTP_PASSWORD` is required for port `21`; the
workflow does not treat `SFTP_PRIVATE_KEY` as a password fallback for FTP/FTPS
uploads.

Some ISPmanager/shared-hosting FTP endpoints expose only an IP address while
serving a provider certificate with an incomplete or mismatched trust chain. For
that case, `FTPS_ALLOW_UNVERIFIED_CERT=true` disables certificate identity
verification for port `21` only. TLS encryption remains required and plain FTP
is still forbidden; this is an explicit accepted-risk mode for hosting providers
that cannot supply a verifiable FTPS endpoint.

`SFTP_PRIVATE_KEY` is used when it contains an SSH private key. Password-based
SFTP can use `SFTP_PASSWORD`; for compatibility, a non-key `SFTP_PRIVATE_KEY`
value is also treated as the password fallback only for SFTP-over-SSH paths.

For SFTP over SSH, use port `22`. `SFTP_KNOWN_HOSTS` should contain the host
keys from `ssh-keyscan`, for example:

```bash
ssh-keyscan -p 22 31.31.196.166
```

`SFTP_REMOTE_ROOT` must be the directory served by the public HTTP origin. For
example, if the remote root is served as `https://specgraph.tech/`, then
`artifact_manifest.json` should become available at:

```text
https://specgraph.tech/artifact_manifest.json
```

## Consumer Contract

SpecSpace should start from `artifact_manifest.json` and then fetch concrete
paths from the published roots. It should not assume that every historical run
artifact is present forever without checking the manifest and checksums.
