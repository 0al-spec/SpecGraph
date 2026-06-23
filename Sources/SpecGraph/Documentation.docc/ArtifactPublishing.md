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
public-safe `runs/`, including the Agent Passport producer artifacts consumed
by SpecSpace: executor adapter index, agent surface index, known passport
index, verification report, verification gap index, runtime evidence index, and
runtime evidence detail artifacts. It also refreshes the compiler-backed
Ontology package, binding, gap, compatibility-diff, governance, and
adapter-smoke artifacts consumed by SpecSpace.

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

The public bundle publishes `runs/*.json` by default after redaction and safety
scanning. Local-only operator diagnostics are excluded by denylist rather than
requiring every public artifact to be allowlisted.

The public bundle must include the Ontology package and review surfaces that
SpecSpace reads over HTTP: `runs/ontology_package_index.json`,
`runs/ontology_binding_preview.json`, `runs/ontology_import_gap_index.json`,
`runs/ontology_compatibility_diff_preview.json`,
`runs/ontology_semantic_review_surface.json`,
`runs/ontology_review_dashboard.json`, and
`runs/ontology_decision_import_preview.json`. Static publishing runs
`make ontology-imports` first so the compiler-backed SpecGraph Core package
artifacts are present, then runs `make ontology-imports-public` so the
public-unsafe review/lint-context surfaces become valid no-candidates or
no-decisions placeholders and tombstones. When
`runs/ontology_package_index.json` declares `packages[].materialized_ir`, the
referenced JSON file is copied into the bundle at the same relative path and is
listed in `artifact_manifest.json`.

The public bundle also includes the review-only SpecAuthor invocation surfaces
produced by `make specauthor-authoring-flow`:
`runs/specauthor_invocation_artifact.json`,
`runs/specauthor_invocation_artifact_contract_report.json`, and
`runs/specauthor_authoring_flow_report.json`. These artifacts publish sanitized
refs, validation status, findings, warnings, and authority boundaries for the
authoring invocation chain. They must not publish raw prompts, raw model output,
canonical spec mutations, ontology package writes, or owner-decision imports.

The public bundle exposes stable Platform Git Service handoff names through
`artifact_manifest.json` under `platform_handoff_surfaces`:
`runs/candidate_spec_materialization_report.json` and
`runs/idea_to_spec_promotion_gate.json`. Until a real idea-to-spec candidate
publish source exists, static publishing writes public-safe placeholders with
`source_mode: public_placeholder` and `placeholder_reason: no_active_candidate`.
Those placeholders preserve the HTTP contract without publishing fixture-based
promotion paths, materialized files, branches, commits, pull requests, or
canonical spec mutations.

When `runs/candidate_approval_decision.json` exists, it is published as an
ordinary public-safe run artifact. It is not generated as a placeholder:
absence means no explicit operator approval has been recorded. The artifact
records refs, digests, decision state, findings, and authority metadata without
publishing raw prompts, private operator notes, branches, commits, pull
requests, merges, read models, canonical spec mutations, or Ontology writes.

Project-local ontology package data should materialize below the owning
SpecGraph checkout, for example `ontology/packages/specgraph-core/`, not under
the sibling Ontology repository or `tests/fixtures/`. The sibling Ontology
repository remains the tooling, schema, compiler, stdlib primitive, and example
authority rather than the default storage location for every product ontology.

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
`runs/local_operator_executor_followup_proposal_draft_candidate.json` may exist
after `make executor-followup-proposal-draft-candidate`, and
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
`docs/proposals/`, or mutate proposal registries. The
`public_proposal_doc_materialization_policy` is only a policy boundary for a
future `docs/proposals/...` materializer; static publishing still must not turn
local materialization reports or source drafts into public proposal docs.
`runs/local_operator_executor_public_proposal_materialization_report.json` may
exist after `make executor-public-proposal-doc-materialize`, but it is a
local-only operator report and must not be uploaded to the static host. These
diagnostics remain private operator artifacts rather than public producer
artifacts. Static publishing must not upload candidates, promotion packets, or
materialization reports, write proposal markdown, or mutate proposal
registries. The `local_operator_executor_*` prefix is treated as local-only for
future local operator diagnostics too. `runs/ontology_term_binding_gate_report.json`
is also local-only because it may carry review-mode generated-term evidence
that is useful to an operator but is not a public producer artifact.

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
