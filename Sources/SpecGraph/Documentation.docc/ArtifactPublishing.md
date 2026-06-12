# Artifact Publishing

SpecGraph publishes technical and product-facing surfaces through separate
channels.

## GitHub Pages

GitHub Pages owns the technical surface:

- the repository root technical entrypoint;
- DocC documentation under `documentation/specgraph/`;
- a mixed-case `documentation/SpecGraph/` compatibility redirect for old links;
- future generated technical artifacts that belong next to documentation.

The root page is intentionally not the product landing page.

## Static Host

The specgraph.tech static host owns product-facing landing content and generated
public artifact bundles. Static-host uploads must remain non-destructive so
separate jobs do not delete each other's files.

`make publish-bundle` is the canonical build command for the public artifact
bundle. It refreshes product-facing surfaces before packaging `specs/` and
`runs/`, including the Agent Passport producer artifacts consumed by SpecSpace:
executor adapter index, agent surface index, known passport index, verification
report, verification gap index, runtime evidence index, and runtime evidence
detail artifacts.

The bundle manifest and safety gate must fail closed when required public
surfaces are missing, so a successful static-host deploy means HTTP consumers
can discover the same product-facing surfaces through `artifact_manifest.json`
that local operators see in `runs/`.

Public static publishing also requires successful report-only Agent Passport
CLI validation. The publish workflow downloads the latest
`0al-spec/agent-passport` Linux release into runner temp storage, verifies the
release checksum, and adds the binary to `PATH` before building the bundle. The
CLI is not committed or copied into the static bundle, and generated JSON must
not persist the runner-local binary path.

The public bundle also includes
`runs/external_consumer_evidence_index.json` so downstream consumer evidence
accepted by SpecGraph is HTTP-readable alongside the handoff and Agent surface
producer artifacts.

Local-only operator diagnostics are excluded from the public bundle.
`runs/local_operator_executor_readiness.json` may exist after
`make executor-readiness`, and `runs/local_operator_executor_smoke.json` may
exist after `make executor-smoke`, and
`runs/local_operator_executor_task_smoke.json` may exist after
`make executor-task-smoke`, and
`runs/local_operator_executor_report_contract.json` may exist after
`make executor-report-contract`, and
`runs/local_operator_executor_report.json` may exist after
`make executor-report-smoke`, and
`runs/local_operator_executor_report_review_packet.json` may exist after
`make executor-report-review-packet`, and
`runs/local_operator_executor_proposal_draft_candidate.json` may exist after
`make executor-proposal-draft-candidate`, and
`runs/local_operator_executor_proposal_promotion_packet.json` may exist after
`make executor-proposal-promotion-packet`, and
`runs/local_operator_executor_proposal_materialization_report.json` may exist
after `make executor-proposal-source-materialize`. The
`executor_report_to_proposal_draft_policy` supervisor policy describes the
local-only boundary for proposal draft candidates, and
`proposal_draft_candidate_promotion_policy` describes only a local promotion
request and promotion-packet boundary. The
`deterministic_proposal_draft_materialization_policy` allows a local
materializer to write only `docs/archive/proposal_sources/...` and a local
report; it does not publish materialization state, invoke executors, write
`docs/proposals/`, or mutate proposal registries. These diagnostics remain
private operator artifacts rather than public producer artifacts. Static
publishing must not upload candidates, promotion packets, or materialization
reports, write proposal markdown, or mutate proposal registries.

The public safety gate requires:

- `runs/supervisor_executor_adapter_index.json` summary field
  `agent_passport_cli_status: available`;
- `runs/agent_passport_verification_report.json` summary field `valid_count`
  equal to the same artifact's summary field `entry_count`;
- `runs/agent_verification_gap_index.json` summary fields
  `verification_tool_unavailable_count: 0` and
  `verification_not_attempted_count: 0`.

The Python bundle builder defaults to fail-closed verification. The local
Makefile shortcut passes `--allow-unverified-agent-passports` by default for
draft operator builds, and the public publish workflow clears that local flag
with `make publish-bundle PUBLISH_BUNDLE_FLAGS=`.

## Boundary

Do not deploy `landing/` to GitHub Pages root. That can hide the technical
documentation entrypoint behind product navigation and create loops where
documentation links return to a landing page.
