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

This runs `make viewer-surfaces`, then writes a static mirror under:

```text
dist/specgraph-public/
```

The bundle includes:

- `specs/`
- `runs/`
- `artifact_manifest.json`
- `checksums.sha256`

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
  - `runs/spec_activity_feed.json`

Junk files such as `.DS_Store` and `.gitkeep` are not published.

## Static Host Deployment

The GitHub Actions workflow `.github/workflows/publish-static-artifacts.yml`
builds the bundle on PRs and can upload it from `main` or manual
`workflow_dispatch` runs.

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
```

For ordinary ISPmanager FTP accounts, use:

```text
SFTP_PORT=21
SFTP_USER=<FTP account>
SFTP_PASSWORD=<FTP password>
SFTP_REMOTE_ROOT=/
```

Despite the historical `SFTP_*` secret names, port `21` makes the workflow use
`ftp://` through `lftp` with TLS forced. If the host does not support FTPS, the
deploy fails instead of sending credentials over plain FTP. `SFTP_KNOWN_HOSTS`
is ignored for port `21`.

`SFTP_PRIVATE_KEY` is used when it contains an SSH private key. Password-based
SFTP can use `SFTP_PASSWORD`; for compatibility, a non-key `SFTP_PRIVATE_KEY`
value is also treated as the password fallback.

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
