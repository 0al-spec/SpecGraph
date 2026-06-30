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

This runs `make viewer-surfaces`, `make implementation-delta`,
`make implementation-work`, and then `make viewer-surfaces` again before writing
a static mirror under:

```text
dist/specgraph-public/
```

The bundle includes:

- `specs/`
- public-safe `runs/`
- Ontology materialized IR files referenced by `runs/ontology_package_index.json`
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

GitHub Pages is not the product landing surface. The repository Pages root is
published from `docs/github-pages-root/` as a technical entrypoint with links to
the operator-facing DocC entrypoint at `documentation/specgraph/`, the public
artifact manifest, generated runs, and the custom landing page at
`https://specgraph.tech/`. The specgraph.tech static host owns the product
landing page; GitHub Pages owns only the technical documentation and integration
entrypoints. The workflow publishes a mixed-case
`documentation/SpecGraph/` compatibility redirect for old links, but new links
should use the lowercase DocC path emitted by the plugin. Do not deploy
`landing/` to GitHub Pages root; doing so can create navigation loops where
documentation links return to the marketing page.

The source `runs/` directory remains local and unchanged. The publish bundle is
a redacted mirror: local absolute paths such as `/Users/...` are replaced with
`$LOCAL_PATH` in the copied files.

The order matters and is intentionally two-pass:

1. The first `make viewer-surfaces` refreshes prerequisite trace/evidence
   surfaces used by the implementation delta.
2. `make implementation-delta` and `make implementation-work` build the publish
   implementation surface from those prerequisites.
3. `make executor-adapters`, `make agent-passports`, and
   `make agent-runtime-evidence` build the Agent Passport producer artifacts
   consumed by SpecSpace.
4. The final `make viewer-surfaces` rebuilds `graph_backlog_projection.json`,
   `graph_next_moves.json`, and external handoff packets from the same
   implementation and agent/runtime artifacts that are copied into the bundle.
5. `make external-handoffs` and `make external-consumer-evidence` rebuild the
   downstream handoff and evidence acceptance artifacts after the final viewer
   pass, so the published evidence index references the published handoff
   packet state.
6. `make ontology-imports` builds the compiler-backed SpecGraph Core ontology
   package, binding, gap, compatibility-diff, governance, and adapter-smoke
   artifacts used by SpecSpace.
7. `make ontology-gap-review` and `make legacy-spec-ontology-backfill-plan`
   build the public-safe grouped gap review and legacy backfill planning
   surfaces.
8. `make ontology-imports-public` overwrites only the public-unsafe
   ontology review/lint-context surfaces with placeholders or tombstones so
   static hosts that do not delete old remote files cannot keep serving demo
   fixture content.
9. `make ontology-owner-decision-import-v2` then builds the public-safe owner
   decision review surface from the refreshed gap review and public-safe
   decision preview.
10. `make specauthor-authoring-flow` refreshes the prompt-side SpecAuthor
    invocation artifact chain used by the authoring review surface.
11. The bundle builder writes public-safe Platform Git Service handoff
    placeholders for review-only candidate promotion when no active candidate
    source is configured. These placeholders keep stable HTTP artifact names
    without publishing fixture-derived promotion paths.
12. When `runs/active_idea_to_spec_candidate.json` is present and ready, the
    bundle builder preserves real product workspace handoff surfaces instead of
    overwriting them with placeholders.

The bundle publishes `runs/*.json` by default after redaction and safety
scanning. Local-only operator diagnostics remain excluded by denylist instead of
requiring every public artifact to be allowlisted. When
`runs/ontology_package_index.json` declares `packages[].materialized_ir`, the
referenced JSON file is copied into the bundle at the same relative path and is
listed in `artifact_manifest.json`; this lets SpecSpace fetch the normalized IR
over the same static artifact host. Project-local ontology packages should
materialize IR below `ontology/packages/`, not below `tests/fixtures/`.
The manifest also exposes stable Platform handoff names under
`platform_handoff_surfaces`:
`runs/candidate_spec_materialization_report.json` and
`runs/idea_to_spec_promotion_gate.json`. During public publishing these
surfaces use `source_mode: public_placeholder` and `placeholder_reason:
no_active_candidate` until a real idea-to-spec candidate publish source exists.
When `runs/active_idea_to_spec_candidate.json` is ready, the manifest also
reports that active source and the publisher leaves the real materialization and
promotion gate artifacts intact.

When present, `runs/candidate_approval_decision.json` is published as an
ordinary public-safe run artifact. It is intentionally not generated as a public
placeholder: absence means no explicit operator approval has been recorded. The
artifact must contain refs, digests, decision state, findings, and authority
metadata only; it must not publish raw prompts, private operator notes, local
paths, branches, commits, pull requests, merges, read models, canonical spec
mutations, or Ontology writes. Static publishing skips this artifact when the
active candidate source is not publishable or when the approval artifact's
recorded active-candidate or promotion-gate refs/digests no longer match the
current run artifacts.

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
- missing Agent Passport producer surfaces required by SpecSpace:
  - `runs/supervisor_executor_adapter_index.json`
  - `runs/agent_surface_index.json`
  - `runs/known_agent_passport_index.json`
  - `runs/agent_passport_verification_report.json`
  - `runs/agent_verification_gap_index.json`
  - `runs/agent_runtime_enforcement_evidence_index.json`
  - `runs/agent_runtime_enforcement_evidence/supervisor-executor-adapter-smoke.json`
  - `runs/agent_runtime_enforcement_evidence/supervisor-executor-adapter-redacted-local-summary.json`
- missing Ontology review surfaces required by SpecSpace:
  - `runs/ontology_semantic_review_surface.json`
  - `runs/ontology_review_dashboard.json`
  - `runs/ontology_decision_import_preview.json`
- missing Platform Git Service handoff surfaces required by SpecSpace:
  - `runs/candidate_spec_materialization_report.json`
  - `runs/idea_to_spec_promotion_gate.json`
- unsafe or missing Ontology materialized IR paths declared by
  `runs/ontology_package_index.json`;
- public Ontology review surfaces that contain checked-in demo fixture terms
  instead of a production-safe no-candidates/no-decisions placeholder;
- missing external consumer evidence surfaces required by downstream evidence
  acceptance:
  - `runs/external_consumer_evidence_index.json`
- Agent Passport producer artifacts that were built without successful
  report-only CLI validation:
  - `runs/supervisor_executor_adapter_index.json` summary field
    `agent_passport_cli_status` must be `available`;
  - `runs/agent_passport_verification_report.json` summary field
    `valid_count` must equal `runs/agent_passport_verification_report.json`
    summary field `entry_count`;
  - `runs/agent_verification_gap_index.json` summary fields
    `verification_tool_unavailable_count` and
    `verification_not_attempted_count` must both be `0`.

Junk files such as `.DS_Store` and `.gitkeep` are not published.

Local-only operator diagnostics are also excluded from the public bundle. In
particular, `runs/local_operator_executor_readiness.json` may exist in a local
checkout after `make executor-readiness`, and
`runs/local_operator_executor_smoke.json` may exist after `make executor-smoke`,
and `runs/local_operator_executor_task_smoke.json` may exist after
`make executor-task-smoke`,
`runs/local_operator_executor_report_contract.json` may exist after
`make executor-report-contract`, and
`runs/local_operator_executor_report.json` may exist after
`make executor-report-smoke`, and
`runs/local_operator_executor_report_review_packet.json` may exist after
`make executor-report-review-packet`, and
`runs/local_operator_executor_proposal_draft_candidate.json` may exist after
`make executor-proposal-draft-candidate`, and
`runs/local_operator_executor_followup_proposal_draft_candidate.json` may exist
after `make executor-followup-proposal-draft-candidate`, and
`runs/local_operator_executor_proposal_promotion_packet.json` may exist after
`make executor-proposal-promotion-packet`, and
`runs/local_operator_executor_proposal_materialization_report.json` may exist
after `make executor-proposal-source-materialize`, but they are intentionally
not uploaded to the static host because they describe the current operator
process environment rather than public producer artifacts. The
`local_operator_executor_*` prefix is treated as local-only for future local
operator diagnostics too. `runs/ontology_term_binding_gate_report.json` is also
local-only: it may carry review-mode generated-term evidence that is useful to
an operator but is not a public producer artifact. The
`proposal_draft_candidate_promotion_policy` defines only a local promotion
request and promotion-packet boundary; it does not publish candidates or
promotion packets, write proposal markdown, or mutate proposal registries
during static publishing. The
`deterministic_proposal_draft_materialization_policy` allows a local
materializer to write only `docs/archive/proposal_sources/...` and a local
report; it does not publish materialization state, invoke executors, write
`docs/proposals/`, or mutate proposal registries during static publishing.
`public_proposal_doc_materialization_policy` is only a policy boundary for a
future `docs/proposals/...` materializer; static publishing still must not turn
local materialization reports or source drafts into public proposal docs.
`runs/local_operator_executor_public_proposal_materialization_report.json` may
exist after `make executor-public-proposal-doc-materialize`, but it is a
local-only operator report and must not be uploaded to the static host.

Agent Passport CLI is installed during the publish workflow from the latest
`0al-spec/agent-passport` GitHub Release into runner temp storage and added to
`PATH` before `make publish-bundle`. The CLI binary is not committed or copied
into the static bundle, and generated JSON must not persist the runner-local
binary path. The Python bundle builder defaults to fail-closed verification;
the local Makefile shortcut passes `--allow-unverified-agent-passports` by
default for draft operator builds, and the public publish workflow clears that
local flag with `make publish-bundle PUBLISH_BUNDLE_FLAGS=`.

## Static Host Deployment

The GitHub Actions workflow `.github/workflows/publish-static-artifacts.yml`
builds the bundle on PRs and can upload it from `main` or manual
`workflow_dispatch` runs.

The publish workflow checks out `0al-spec/Metrics` as an external sibling source
under `external/Metrics` before building the bundle. This keeps public artifacts aligned
with local development, where `tools/external_consumers.json` points at the
same Metrics checkout through `local_checkout_hint`. The supervisor also
supports `SPECGRAPH_EXTERNAL_CHECKOUT_ROOT`; when a declared absolute checkout
hint is not available, it can resolve a sibling checkout by repository name
under that root or under the parent directory of the SpecGraph checkout.

The same external Metrics checkout owns the Idea-to-Spec maturity metrics
validator. `make publish-bundle` builds
`runs/idea_maturity_metrics_report.json`, then runs
`make idea-maturity-metrics-validate` through `METRICS_CLI` and publishes
`runs/idea_maturity_metrics_validation_report.json`. SpecGraph does not commit
or publish the Metrics validator binary/script as its own artifact.
The maturity report includes proposal `0180` `readiness_explainers` inline, so
SpecSpace and Platform can explain Pre-SIB, repair-session, promotion-gate,
stale-ref, policy, and invariant blockers without fetching another artifact or
granting write authority.
Proposal `0181` also adds a `contract` object to the maturity report with the
Metrics-owned schema refs, validation-report schema ref, validator id/version,
and compatibility-policy ref. SpecGraph publishes that metadata as producer
evidence; Metrics remains the RFC/schema/validator authority.

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

The production publish workflow also builds the Team Decision Log product
workspace bundle under the same public root:

```text
https://specgraph.tech/workspaces/team-decision-log/artifact_manifest.json
```

That workspace bundle has its own manifest and checksums. It is built after the
Team Decision Log happy-path repair pack so `specgraph.space/team-decision-log`
can consume product workspace artifacts without falling back to the bootstrap
SpecGraph root bundle.

## Consumer Contract

SpecSpace should start from `artifact_manifest.json` and then fetch concrete
paths from the published roots. It should not assume that every historical run
artifact is present forever without checking the manifest and checksums.

For product workspace routes, SpecSpace should start from the workspace-specific
manifest, for example `workspaces/team-decision-log/artifact_manifest.json`,
instead of the root `artifact_manifest.json`.

When SpecSpace reads `runs/ontology_package_index.json`, it may follow each
package `materialized_ir` relative path if and only if that path appears in
`artifact_manifest.json`. The public bundle preserves the declared path instead
of rewriting it.
