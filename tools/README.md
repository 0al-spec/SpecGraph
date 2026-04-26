# Tools

For a practical operator/contributor guide to the supervisor, see
[docs/supervisor_manual.md](../docs/supervisor_manual.md).
For a visualizer-facing compact report and overlay guide, see
[docs/metrics_visualization_guide.md](../docs/metrics_visualization_guide.md).
For the dedicated `SpecPM` preview/materialization/import viewer contract, see
[docs/specpm_viewer_contract.md](../docs/specpm_viewer_contract.md).
For the ContextBuilder exploration/assumption-mode viewer contract, see
[docs/exploration_preview_viewer_contract.md](../docs/exploration_preview_viewer_contract.md).
For the planned Implementation Work layer and delta/work-index viewer contract,
see [docs/implementation_work_viewer_contract.md](../docs/implementation_work_viewer_contract.md).

## Minimal Spec-Node Supervisor MVP

This repository includes a local MVP that orchestrates **specification nodes** (not tasks):

- Spec nodes live in `specs/nodes/*.yaml`.
- The supervisor script is `tools/supervisor.py`.
- Run logs are written to `runs/`.

Run locally:

```bash
python tools/supervisor.py
```

The supervisor loop is:

`pick spec gap -> refine spec -> validate -> update state`

Supervisor modes:

- Default: pick the next eligible bounded refinement run.
- `--loop --auto-approve`: keep processing eligible work until the queue is empty.
- `--target-spec SPEC_ID --observe-graph-health`: inspect subtree signals and
  historical-versus-active descendants without mutating canonical specs. This
  now includes breadth pressure such as `refinement_fan_out_pressure` and a
  distinction between healthy multi-child aggregates and broad hubs, with
  regrouping-oriented recommendations when breadth pressure is real.
  Lower-boundary shape and role-legibility pressure can now also collapse into
  an explicit `techspec_handoff_candidate`, backed by
  `tools/techspec_handoff_policy.json`, when the subtree looks semantically
  saturated for canonical SpecGraph and increasingly implementation-facing.
  Queue and proposal flows now carry that signal forward as an explicit
  `handoff_proposal` with `transition_profile: techspec` and `packet_type: handoff`.
- `--resolve-gate SPEC_ID --decision ...`: apply a human review decision.
- `--target-spec SPEC_ID --split-proposal`: run the explicit proposal-first split pass for one
  oversized non-seed spec and emit a structured artifact under `runs/proposals/` without editing
  canonical spec files.
- `--target-spec SPEC_ID --apply-split-proposal`: deterministically materialize one reviewed split
  proposal into canonical parent/child spec files and mark the proposal artifact as applied.
- `--build-graph-health-overlay`: build `runs/graph_health_overlay.json` so current
  oversized, weakly linked, shape-heavy, or handoff-ready regions are visible as
  one derived viewer/report surface without scanning raw run logs.
- `--build-graph-health-trends`: build `runs/graph_health_trends.json` from run
  history plus the current overlay so repeated structural problems show up as
  trends instead of isolated events.
- `--validate-transition-packet PATH`: validate one normalized transition packet JSON file and
  print structured findings. Add `--transition-profile PROFILE` to validate the same packet under
  `specgraph_core`, `product_spec`, `techspec`, or `implementation_trace`.
  Use `--operator-request-packet PATH` when the concern is not artifact movement
  but one bounded mediated execution request that should steer a single
  supervisor run.
  `product_spec` inherits the shared engine through one `product_graph_root`
  binding and the declarative rules in `tools/product_spec_transition_policy.json`
  instead of re-implementing packet semantics per product domain.
  `promotion` packets also expose the semantic boundary from
  `tools/proposal_promotion_policy.json`, which distinguishes exploratory
  `working_draft` material from normalized `reviewable_proposal` artifacts
  without making folder layout the only source of meaning.
  Promotion packets now carry an explicit minimal contract: `source_artifact_class`,
  `target_artifact_class`, `source_refs`, `motivating_concern`,
  `normalized_title`, `bounded_scope`, and `required_provenance_links`
  including `source_draft_ref`.
- `--build-spec-trace-index`: build `runs/spec_trace_index.json` from literal `SG-SPEC-XXXX`
  mentions in `tools/` and `tests/`, then enrich that graph-bound index with weak
  `commit_refs`, `pr_refs`, `verification_basis`, and `acceptance_coverage`.
  `implementation_state` is derived conservatively from explicit contracts in
  `tools/spec_trace_registry.json`, not from weak mentions alone, and `freshness`
  now distinguishes fresh, stale-spec, and drifted verified regions.
- `--build-spec-trace-projection`: build `runs/spec_trace_projection.json` from the
  trace plane, grouped for viewer-style filters and implementation backlog queries.
- `--build-evidence-plane-index`: build `runs/evidence_plane_index.json` from
  canonical specs, `tools/runtime_evidence_registry.json`, and current derived
  runtime artifacts so evidence contracts stay derived instead of leaking raw
  telemetry into canonical YAML.
- `--build-evidence-plane-overlay`: build `runs/evidence_plane_overlay.json`
  from the evidence plane, grouped for viewer-style filters and next evidence
  gaps across observation, outcome, and adoption coverage.
- `--build-external-consumer-index`: build `runs/external_consumer_index.json`
  from `tools/external_consumers.json` and optional local sibling checkouts so
  stable-vs-draft external references such as `Metrics/SIB` can be inspected
  without using a Git submodule.
- `--build-external-consumer-overlay`: build
  `runs/external_consumer_overlay.json` from the bridge index and metric signal
  index so sibling-consumer readiness, metric pressure, and next-gap backlog
  become viewer-facing surfaces.
- `--build-external-consumer-handoffs`: build
  `runs/external_consumer_handoff_packets.json` so stable sibling consumers
  receive explicit reviewable downstream handoff packets while draft references
  remain visible but non-operational.
- `--build-specpm-export-preview`: build `runs/specpm_export_preview.json`
  from the tracked `SpecPM` consumer contract and
  `tools/specpm_export_registry.json`, producing a reviewable package preview
  without pretending that the full `BoundarySpec` is already finalized.
- `--build-specpm-handoff-packets`: build
  `runs/specpm_handoff_packets.json` from the current `SpecPM` export preview
  plus external-consumer identity data, so previewable exports can become
  explicit downstream handoff packets before any real write into `SpecPM`.
- `--materialize-specpm-export-bundles`: build
  `runs/specpm_materialization_report.json` and write local draft export
  bundles into the sibling `SpecPM` checkout under a controlled
  `.specgraph_exports/<package_id>/` inbox, without auto-committing there.
- `--build-specpm-import-preview`: build
  `runs/specpm_import_preview.json` from local bundles in the sibling
  `SpecPM` checkout so import readiness stays review-first and does not mutate
  canonical `SpecGraph` specs.
- `--build-specpm-import-handoff-packets`: build
  `runs/specpm_import_handoff_packets.json` from the current `SpecPM` import
  preview so valid inbound bundles become explicit proposal-lane or handoff
  candidates without mutating canonical specs directly.
- `--build-specpm-delivery-workflow`: build
  `runs/specpm_delivery_workflow.json` from the current `SpecPM`
  materialization report so downstream branch, commit, and PR scaffolding
  becomes reviewable before any real cross-repo write exists.
- `--build-specpm-feedback-index`: build
  `runs/specpm_feedback_index.json` from the current `SpecPM`
  delivery workflow plus downstream checkout observations so local review or
  adoption signals become visible without turning them into canonical truth.
- `--build-specpm-public-registry-index`: build
  `runs/specpm_public_registry_index.json` from the current materialization
  report plus the configured local-dev SpecPM registry, using read-only `/v0`
  probes so registry visibility and drift become observable without publishing.
- `--build-metrics-delivery-workflow`: build
  `runs/metrics_delivery_workflow.json` from current Metrics/SIB handoff
  packets so downstream branch, commit, and PR scaffolding becomes reviewable
  before any real cross-repo write exists.
- `--build-metrics-feedback-index`: build
  `runs/metrics_feedback_index.json` from the current Metrics delivery
  workflow plus downstream checkout observations so review/adoption signals
  feed back into derived surfaces without becoming canonical truth.
- `--build-metrics-source-promotion-index`: build
  `runs/metrics_source_promotion_index.json` so draft Metrics/SIB_FULL sources
  can become reviewable promotion candidates without receiving threshold
  authority automatically.
- `--build-metric-signal-index`: build `runs/metric_signal_index.json` from
  trace, evidence, graph-health, and proposal-runtime surfaces so metric-driven
  advisory signals remain derived rather than canonical facts. `sib` is the
  bridge-native SIB metric family; `sib_proxy` remains an alias-only
  compatibility entry for existing viewers.
- `--build-metric-threshold-proposals`: build
  `runs/metric_threshold_proposals.json` from metric-threshold breaches so the
  next step is a reviewable proposal artifact, not a direct policy mutation.
- `--build-supervisor-performance-index`: build
  `runs/supervisor_performance_index.json` from historical run logs so runtime
  cleanliness, run yield, and graph impact can be inspected separately over
  time.
- `--build-bootstrap-smoke-benchmark`: build
  `runs/bootstrap_smoke_benchmark.json` from the supervisor performance index
  so minimal-seed bootstrap yield can be inspected structurally without
  comparing exact generated spec text.
- `--build-graph-dashboard`: build `runs/graph_dashboard.json` as one
  aggregated viewer-facing dashboard with headline counts from graph health,
  proposal, implementation, evidence, external-consumer, handoff, and metric
  surfaces.
- `--build-graph-backlog-projection`: build
  `runs/graph_backlog_projection.json` as a normalized viewer-facing backlog
  projection from existing derived graph, proposal, implementation, evidence,
  external-consumer, SpecPM, Metrics, and threshold-proposal surfaces.
- `--build-intent-layer-overlay`: build `runs/intent_layer_overlay.json` from
  repository-tracked intent-layer nodes under `intent_layer/nodes/`, so
  pre-canonical user intent and operator-request artifacts can be inspected as
  a separate mediation layer.
- `--build-exploration-preview`: build `runs/exploration_preview.json` from an
  optional inline `--exploration-intent TEXT`, producing a review-only
  assumption-mode placeholder graph without mutating canonical specs or tracked
  intent/proposal artifacts.
- `--build-implementation-delta-snapshot`: build
  `runs/implementation_delta_snapshot.json` from explicit
  `--target-scope-kind`, `--target-spec-ids`, and `--operator-intent` values,
  producing a derived planning snapshot without mutating canonical specs or
  runtime code.
- `--build-implementation-work-index`: build
  `runs/implementation_work_index.json` from the latest implementation delta
  snapshot, turning delta entries into bounded reviewable work items.
- `--build-review-feedback-index`: build `runs/review_feedback_index.json`
  from tracked `tools/review_feedback_records.json`, turning handled review
  comments into grouped root-cause, prevention-action, verification, and
  next-gap process evidence.
- `--build-vocabulary-index`: build `runs/vocabulary_index.json` from
  `tools/specgraph_vocabulary.json`, flattening canonical terms, aliases,
  deprecated aliases, families, and contexts into one shared machine-readable
  ontology surface for specs, policy artifacts, and viewers.
- `--build-vocabulary-drift-report`: build `runs/vocabulary_drift_report.json`
  from canonical specs and governed policy artifacts to flag undefined terms,
  alias collisions, deprecated alias usage outside sanctioned mappings, and
  meaning divergence.
- `--build-pre-spec-semantics-index`: build
  `runs/pre_spec_semantics_index.json` from tracked `intent_layer/nodes/*.json`,
  proposal-lane lineage, and canonical `last_pre_spec_provenance` links.
- `--operator-request-packet PATH`: normalize one bounded `operator_request_packet`
  into a targeted refinement or split-proposal run. The packet is the sole
  steering envelope for that run and is mirrored into repository-tracked
  `intent_layer/nodes/*.json` before execution. Resulting proposal-lane nodes
  or canonical review candidates then carry that request lineage forward
  instead of appearing sky-born. The normalized `OperatorRequest` is now typed:
  it carries explicit authority, mutation budget, stop conditions, and a
  machine-readable execution contract rather than relying on ad hoc CLI flags.
- `--build-proposal-lane-overlay`: build `runs/proposal_lane_overlay.json` from
  repository-tracked proposal-lane nodes under `proposal_lane/nodes/`, so
  draft proposal structure can be inspected as a secondary graph layer without
  confusing it with canonical truth.
- `--build-proposal-runtime-index`: build `runs/proposal_runtime_index.json` from proposal docs,
  the proposal runtime registry, `tasks.md`, and repository markers in `tools/` and `tests/`.
  Entries now also expose `repository_projection` and `semantic_artifact_class`
  from `tools/proposal_promotion_policy.json`, so `docs/proposals/` is treated
  as a repository projection of proposal semantics rather than the sole source
  of lifecycle meaning.
- `--build-proposal-promotion-index`: build `runs/proposal_promotion_index.json` from
  `docs/proposals/`, `tools/proposal_promotion_registry.json`, and
  `tools/proposal_promotion_policy.json` to inspect bounded promotion
  traceability and next provenance gaps for promoted proposals.
- `--list-stale-runtime` / `--clean-stale-runtime`: inspect or clean stale gate/worktree residue.

Key derived artifacts:

- `runs/latest-summary.md`: fastest operator-facing run snapshot
- `runs/<RUN_ID>.json`: full run payload including `graph_health`,
  `decision_inspector`, `validation_findings`, and `validation_summary`
- `runs/decision_inspector/<RUN_ID>.json`: standalone decision explanation artifact for one run
- `runs/graph_health_overlay.json`: canonical graph-health viewer/report overlay grouped by
  signal, recommended action, and named pressure filters
- `runs/graph_health_trends.json`: longitudinal graph-health report grouped by
  recurring signals, current-vs-historical recurrence, and repeated pressure filters
- `runs/proposal_queue.json`: derived proposal-oriented next moves
- `runs/refactor_queue.json`: derived refactor-oriented next moves
- `runs/proposals/*.json`: structured split proposal artifacts
- `intent_layer/nodes/*.json`: repository-tracked intent-layer nodes for
  `user_intent` and `operator_request`, kept pre-canonical and separate from
  proposal-lane and canonical graph truth
- `runs/intent_layer_overlay.json`: intent-layer viewer/report surface grouped
  by artifact kind, mediation state, explicit distinction contracts, and
  invalid query-contract findings
- `runs/exploration_preview.json`: review-only assumption-mode preview graph
  with intent, assumption, hypothesis, proposal, and human-review placeholder
  nodes; no canonical or tracked artifact mutations are allowed by this artifact
- `runs/implementation_delta_snapshot.json`: derived Implementation Work
  planning snapshot that captures baseline, explicit target scope, delta fields,
  source-artifact availability, readiness, and next gap without canonical or
  runtime code mutation
- `runs/implementation_work_index.json`: bounded Implementation Work items
  generated from the latest delta snapshot, grouped by readiness, next gap, and
  viewer filters for review before any coding-agent handoff
- `runs/review_feedback_index.json`: derived review-feedback learning-loop
  surface built from tracked records, grouped by status, root cause, prevention
  action, verification kind, and next gap
- `runs/pre_spec_semantics_index.json`: derived pre-spec semantic index linking
  tracked intent-layer artifacts to downstream proposal-lane nodes and
  canonical specs, with queryability and provenance findings
- `runs/vocabulary_index.json`: flattened shared vocabulary index for canonical
  terms, aliases, deprecated aliases, families, and contexts
- `runs/vocabulary_drift_report.json`: drift report over canonical specs and
  governed policy artifacts, including undefined terms, alias collisions, and
  meaning divergence
- `proposal_lane/nodes/*.json`: repository-tracked proposal-lane nodes with
  stable provisional handles, authority state, target region, lineage, and
  runtime bridge metadata
- `runs/proposal_lane_overlay.json`: proposal-lane viewer/report surface built
  from repository-tracked proposal nodes, grouped by authority state, query
  contract validity, and canonical or runtime lineage edges
- `runs/spec_trace_index.json`: first graph-bound trace artifact with `code_refs`,
  `test_refs`, `commit_refs`, `pr_refs`, `verification_basis`,
  `acceptance_coverage`, `implementation_state`, and `freshness`
- `runs/spec_trace_projection.json`: viewer/backlog projection grouped by
  `implementation_state`, `freshness`, `acceptance_coverage`, and next-gap categories
- `runs/evidence_plane_index.json`: derived evidence-plane index that links
  registry-backed canonical specs to artifact surfaces, runtime entities,
  observations, outcomes, and adoption markers
- `runs/evidence_plane_overlay.json`: viewer/inspection overlay for the
  evidence plane grouped by chain status, stage coverage, and next evidence gap
- `runs/external_consumer_index.json`: derived bridge artifact for declared
  external consumers, including reference state, checkout availability,
  contract status, and metric bindings
- `runs/external_consumer_overlay.json`: viewer/backlog projection for sibling
  consumer bridges, grouped by bridge state, bound metric status, and next-gap
  remediation pressure
- `runs/external_consumer_handoff_packets.json`: reviewable downstream handoff
  artifact for sibling consumers, grouped by handoff status, review state, and
  next-gap backlog
- `runs/specpm_export_preview.json`: reviewable `SpecPM` package preview
  artifact, including manifest preview, boundary-source preview, export
  status, and next-gap backlog for future full package emission
- `runs/specpm_handoff_packets.json`: reviewable `SpecPM` handoff layer
  derived from the current preview, grouped by handoff status, review state,
  and next-gap backlog for downstream transfer readiness
- `runs/specpm_materialization_report.json`: viewer-facing report for local
  `SpecPM` bundle materialization, grouped by materialization status, review
  state, and next-gap backlog after writing draft bundles into the sibling
  checkout inbox
- `runs/specpm_import_preview.json`: reviewable inbound `SpecPM` bundle
  surface, grouped by import status, review state, suggested upstream target
  kind, and next-gap backlog before any import into canonical specs
- `runs/specpm_import_handoff_packets.json`: reviewable inbound `SpecPM`
  handoff surface, grouped by handoff status, review state, route kind, and
  next-gap backlog before any proposal-lane or handoff-node creation
- `runs/specpm_delivery_workflow.json`: reviewable outbound `SpecPM`
  delivery workflow surface, grouped by delivery status, review state, git
  checkout state, and next-gap backlog before any downstream commit or PR
- `runs/specpm_feedback_index.json`: derived `SpecPM` downstream feedback
  surface, grouped by observed review/adoption status, checkout signals, and
  next-gap backlog without auto-accepting that downstream state as canonical
- `runs/specpm_public_registry_index.json`: read-only `SpecPM` public registry
  observation surface, grouped by registry visibility, missing package versions,
  searchable capabilities, and drift against materialized package identities
- `runs/metrics_delivery_workflow.json`: reviewable outbound `Metrics`
  delivery workflow surface, grouped by delivery status, review state, git
  checkout state, metric binding, and next-gap backlog before downstream commit
  or PR
- `runs/metrics_feedback_index.json`: derived `Metrics` downstream feedback
  surface, grouped by observed review/adoption status, checkout signals, metric
  binding, and next-gap backlog without auto-accepting downstream state as
  canonical
- `runs/metrics_source_promotion_index.json`: reviewable `Metrics/SIB_FULL`
  promotion surface, grouped by promotion status, review state, authority
  guardrail, metric binding, and next-gap backlog
- `runs/metric_signal_index.json`: derived metric surface for
  `Specification Verifiability`, `Process Observability`,
  `Structural Observability`, bridge-native `SIB`, and the alias-only
  `sib_proxy` compatibility projection, plus threshold-based advisory signals
- `runs/metric_threshold_proposals.json`: reviewable proposal artifact emitted
  from metric-threshold breaches, grouped by proposal kind, severity, and
  target metric
- `runs/supervisor_performance_index.json`: derived supervisor measurement
  surface grouped by runtime status, yield status, graph impact, per-profile
  throughput, and repeat-hotspot pressure
- `runs/bootstrap_smoke_benchmark.json`: advisory benchmark report that
  evaluates cheap bootstrap-smoke runs from structural yield criteria instead
  of golden text snapshots
- `runs/graph_dashboard.json`: aggregated dashboard artifact with headline
  cards and section counts for graph, health, retrospective refactor candidates,
  proposals, implementation, evidence, external consumers, external handoffs,
  and metric surfaces
- `runs/graph_backlog_projection.json`: normalized work/backlog projection with
  concrete `entries[]` grouped by domain, priority, next gap, source artifact,
  and named filters so viewers do not need `tasks.md` as a work queue
- `tools/spec_trace_registry.json`: explicit strong trace contracts used to
  derive conservative `implementation_state` overlays such as `planned`,
  `implemented`, `verified`, `drifted`, and `blocked`
- `tools/evidence_plane_policy.json`: declarative boundary for the derived
  evidence plane, including its semantic chain and overlay/index contracts
- `tools/specpm_materialization_policy.json`: declarative contract for local
  `SpecPM` bundle materialization, including eligibility checks, inbox layout,
  bundle file paths, and viewer/backlog states
- `tools/specpm_import_policy.json`: declarative contract for `SpecPM`
  import preview, including required bundle files, review states, target-kind
  suggestions, and next-gap defaults
- `tools/specpm_delivery_policy.json`: declarative contract for reviewable
  `SpecGraph -> SpecPM` delivery workflow, including eligibility, checkout git
  state checks, and downstream branch/commit/PR scaffolding
- `tools/specpm_feedback_policy.json`: declarative contract for downstream
  `SpecPM` feedback observation, including status vocabulary, branch/adoption
  heuristics, and review-safe next-gap defaults
- `tools/specpm_public_registry_policy.json`: declarative contract for
  read-only `SpecPM` public registry observation, including local-dev base URL
  rules, endpoint template validation, and drift next-gap defaults
- `tools/metrics_delivery_policy.json`: declarative contract for reviewable
  `SpecGraph -> Metrics` handoff delivery workflow, including eligibility, git
  state checks, and downstream branch/commit/PR scaffolding
- `tools/metrics_feedback_policy.json`: declarative contract for downstream
  `Metrics` feedback observation, including status vocabulary, branch/adoption
  heuristics, metric binding, and review-safe next-gap defaults
- `tools/metrics_source_promotion_policy.json`: declarative contract for
  reviewable promotion of draft sibling metric sources such as `Metrics/SIB_FULL`
  without automatic threshold authority
- `tools/review_feedback_policy.json`: declarative contract for treating
  actionable PR review comments as process evidence, including root-cause
  vocabulary, prevention actions, verification kinds, tracked
  `tools/review_feedback_records.json`, and `runs/review_feedback_index.json`
  semantics
- `tools/metric_signal_policy.json`: declarative thresholds, score mappings,
  metric identities, and proposal-first threshold semantics for the derived
  metric signal layer
- `tools/supervisor_performance_policy.json`: declarative contract for the
  supervisor performance index, including runtime, yield, graph-impact, and
  repeat-hotspot classifications
- `tools/bootstrap_smoke_benchmark_policy.json`: declarative contract for the
  advisory bootstrap smoke benchmark, including seed fixture metadata, run
  selection, fixed budget, and structural pass criteria
- `tools/external_consumers.json`: tracked registry of stable and draft
  external consumers, such as `Metrics/SIB` and `Metrics/SIB_FULL`, used by
  the bridge index and bridge-backed metric derivation
- `tools/external_consumer_overlay_policy.json`: declarative contract for the
  external-consumer overlay, including bridge states, named filters, and
  backlog next-gap defaults
- `tools/external_consumer_handoff_policy.json`: declarative contract for
  sibling-consumer handoff packets, including handoff states, packet
  provenance, and review-state defaults
- `tools/specpm_export_policy.json`: declarative contract for `SpecPM` export
  previews, including review status, next-gap defaults, and required export
  registry fields
- `tools/specpm_export_registry.json`: tracked declaration of which bounded
  `SpecGraph` regions should emit `SpecPM` package previews and under which
  package identity and capability IDs
- `tools/specpm_handoff_policy.json`: declarative contract for `SpecPM`
  handoff packets, including handoff states, provenance links, and next-gap
  defaults on top of the export preview layer
- `tools/runtime_evidence_registry.json`: explicit evidence contracts that bind
  selected canonical specs to artifact refs, runtime entities, and observation,
  outcome, and adoption markers
- `runs/proposal_runtime_index.json`: proposal posture and reflective runtime-closure index
- `runs/proposal_promotion_index.json`: proposal-promotion provenance and
  traceability inspection artifact grouped by status and next gap
- `runs/safe_repairs/<RUN_ID>.json`: standalone safe-repair artifact for
  bounded worktree-candidate repairs
- `runs/evaluator_control/<RUN_ID>.json`: standalone reflective-cycle control
  artifact with chosen intervention, applied rules, improvement basis, stop
  conditions, and escalation reasons
- `tools/evaluator_intervention_policy.json`: declarative evaluator-choice
  policy that maps selection modes, graph-health pressure, and authority
  constraints into `refine/propose/rewrite/merge/handoff/apply`
- `runs/spec_id_reservations.json`: temporary active child-materialization spec-id reservations
- `tools/supervisor_policy.json`: declarative supervisor policy artifact for thresholds, priorities,
  mutation classes, queue defaults, and execution profiles
- `tools/product_spec_transition_policy.json`: declarative inheritance contract for
  `product_spec` transition packets, including `product_graph_root`,
  reviewable source prefixes, and apply-scope rules
- `tools/proposal_promotion_policy.json`: declarative semantic boundary between
  `working_draft` and `reviewable_proposal` artifacts for governed
  draft-to-proposal promotion
- `tools/proposal_lane_policy.json`: declarative repository contract for the
  tracked proposal lane, including proposal-node presence, authority-state
  mapping, and overlay semantics
- `tools/intent_layer_policy.json`: declarative repository contract for the
  tracked intent layer, including kind separation, mediation-state vocabulary,
  and overlay semantics
- `tools/exploration_preview_policy.json`: declarative contract for
  assumption-mode exploration previews, including allowed placeholder node
  kinds, edge kinds, promotion targets, and the preview-only mutation boundary
- `tools/implementation_delta_policy.json`: declarative contract for
  Implementation Work delta snapshots and work indexes, including baseline,
  target, delta, readiness, and derived-only mutation boundaries
- `tools/specgraph_vocabulary.json`: shared machine-readable vocabulary layer
  for canonical terms, aliases, deprecated aliases, and cross-artifact
  ontology families
- `tools/pre_spec_semantics_policy.json`: declarative contract for pre-spec
  semantic artifacts, their axes, repository layout, and downstream lineage
  into proposal-lane or canonical review candidates
- `tools/operator_request_bridge_policy.json`: declarative contract for
  `operator_request_packet`, including admissible source kinds, bounded run
  modes, typed execution-contract fields, and the rule that one request may
  only steer one supervisor run
- `tools/proposal_promotion_registry.json`: explicit promotion provenance
  registry keyed by `proposal_id`, used to backfill source draft refs,
  motivating concern, bounded scope, and related promotion-trace fields
- `tools/techspec_handoff_policy.json`: declarative lower-boundary contract for
  `SpecGraph -> TechSpec` handoff, including the primary
  `techspec_handoff_candidate` signal and downstream handoff packet target

Runtime artifact safety:

- run logs, summaries, queue files, proposal artifacts, and derived indexes are
  now written through atomic replace with short-lived sidecar locks
- run IDs and isolated worktree/branch names now include a nonce so concurrent
  runs do not collide on one-second timestamps alone
- explicit child-materialization runs reserve one `SG-SPEC-XXXX` ID while the
  run is active and require the produced child file to use that reserved path
- malformed `runs/proposal_queue.json` or `runs/refactor_queue.json` now block
  normal supervisor runs instead of being silently treated as empty queues
- recoverable repairs are now recorded as `safe_repair_contract`; the current
  built-in repair kind `yaml_candidate_repair` is restricted to
  `worktree_candidate_only` with `canonical_write: false`
- a child executor success path must emit both `RUN_OUTCOME:` and `BLOCKER:`
  markers; missing markers are treated as protocol failure

Transition-packet validation now reports:

- packet family metadata for `promotion`, `proposal`, `apply`, and `handoff`
- finding families such as `schema`, `provenance`, `authority`, and `diff_scope`
- profile-aware rules for `specgraph_core`, `product_spec`, `techspec`, and
  `implementation_trace`

Decision inspection now reports applied rules from:

- `tools/supervisor_policy.json` for thresholds, selection priorities, queue defaults,
  mutation classes, and execution profiles
- runtime guards when a decision depends on validator failure, mutation-budget overflow,
  or another non-policy blocker

## Supervisor Bootstrap Runtime Troubleshooting

When a `supervisor` run behaves unexpectedly, debug it in this order:

1. Check `runs/latest-summary.md`.
   It is the fastest operator-facing snapshot and shows:
   - `outcome`
   - `gate_state`
   - `validation_findings`
   - `validation_errors`
   - `executor_environment_issues`
   - `executor_environment_primary_failure`
   - `required_human_action`
2. If the summary suggests an environment problem, open the full run log in `runs/<RUN_ID>.json`.
   The run payload preserves:
   - typed `validation_findings`
   - aggregated `validation_summary`
   - raw `stdout`
   - raw `stderr`
   - structured `executor_environment`
   - derived `graph_health`
3. Only treat the run as a spec-quality problem when
   `executor_environment_primary_failure: no`.
   If it is `yes`, fix the runtime first and rerun `supervisor`.

### Expected Child Executor Profiles

Nested `codex exec` runs are intentionally constrained and deterministic. `supervisor` now uses named
execution profiles instead of one implicit child runtime:

- `standard`
  - model: `gpt-5.4`
  - reasoning effort: `xhigh`
  - timeout: `420s` base and effective timeout floor for `xhigh`
- `materialize`
  - model: `gpt-5.4`
  - reasoning effort: `xhigh`
  - timeout: `720s`
  - auto-selected when run authority includes sanctioned child materialization
- `fast`
  - model: `gpt-5.4`
  - reasoning effort: `xhigh`
  - timeout: `420s` effective timeout floor for heuristic ordinary refinement runs

Timeout rule:

- `supervisor` uses the larger of the profile's base timeout and the minimum timeout floor implied by
  the profile's reasoning effort
- this keeps `xhigh` targeted refinements from inheriting the same timeout budget as lighter reasoning
  modes
- `fast` means heuristic profile selection, not low-effort reasoning; it still uses `xhigh` and a bounded
  but non-trivial timeout so useful split signals are not lost to premature executor termination

Shared child-runtime constraints:

- approval policy: `never`
- sandbox mode: `workspace-write`
- disabled features:
  - `shell_snapshot`
  - `multi_agent`
- isolated `CODEX_HOME` with copied `auth.json` and minimal generated `config.toml`
- no inherited MCP startup beyond what the isolated child home explicitly enables

If a nested run reports a different profile or timeout than the selected execution profile, treat that as
runtime drift.

Command-line overrides for nested runs:

- `--child-model` sets an explicit model for the nested codex run (for example `gpt-5.3-codex-spark`).
- `--child-timeout` sets an explicit timeout in seconds for nested child runs.
- Explicitly targeting a seed/root-like spec (`--target-spec`) without `--child-timeout` uses a 1200s default.

### Worktree Fallback Mode

`supervisor` first tries to create an isolated `git worktree`. If local ref creation is blocked by
permission-style errors (for example `cannot lock ref` or `Operation not permitted` under
`.git/refs/heads/...`), it falls back to a copied sandbox worktree under `.worktrees/`.

Interpretation:

- `git worktree` mode is preferred and should be used when the local environment allows it.
- branch/worktree allocation retries on branch/path collision before failing.
- copied worktree mode is an operational fallback, not a canonical storage mode.
- stale `.worktrees/` directories are safe to delete when no run is actively using them.

### Failure Interpretation

Current nested executor environment issues are classified into these kinds:

- `transport_failure`
  - terminal backend connectivity failures such as disconnected streams, request send failures, or DNS lookup failures
- `mcp_startup_failure`
  - one or more MCP servers failed to start in the child runtime
- `state_runtime_failure`
  - child state DB or migration initialization failed
- `sandbox_permission_failure`
  - local permission or sandbox restrictions prevented the child runtime from operating normally

Important distinction:

- websocket fallback warnings by themselves are not treated as `transport_failure`
- a spec run may still end in `blocked` or another non-`done` outcome for legitimate spec reasons even when stderr contains non-terminal warnings

Runtime anomalies that should not be read as spec-quality failures:

- timeout-driven stale tails
  - if an interrupted refinement leaves `gate_state`, `last_run_id`, or similar runtime fields without an
    accepted canonical content change, treat that as runtime residue rather than evidence that the spec
    itself regressed
  - the authoritative incident record is the run log under `runs/`, not the interrupted tail
- partial worktree diffs from interrupted runs
  - edits visible only inside the copied worktree or interrupted sandbox are diagnostic artifacts until a
    canonical writeback is accepted
  - do not classify a spec as low quality merely because a timed-out run produced a partial draft diff
- profile-selection mismatch
  - if observed timeout behavior or logged profile metadata disagree with the intended execution profile,
    treat that as runtime misconfiguration or drift
  - inspect execution profile selection, reasoning-depth timeout floors, and run authority before
    concluding that the target spec is inherently blocked

Productive nonterminal results:

- `completion_status: progressed`
  - use this when the executor produced a valid canonical refinement, but the node still requires the next
    structural step such as `split_required`
  - this is not a runtime failure and should not be grouped with timeout, transport, or invalid-diff cases

### Operator Actions

Use this decision path:

- `executor_environment_primary_failure: yes`
  - repair the runtime and rerun
  - do not treat `graph_health` or queue side effects from that run as authoritative
- `executor_environment_primary_failure: no` and `gate_state: blocked`
  - treat it as a real spec/workflow blocker and follow `required_human_action`
- `executor_environment_primary_failure: no` and `gate_state: split_required`
  - treat it as an atomicity/spec-structure issue, not a runtime issue
- `completion_status: progressed`
  - treat the run as a productive refinement with required follow-up, not as a failed execution
  - use the resulting canonical diff as the new starting point for the next bounded run
- interrupted run with no accepted canonical content change
  - read `runs/latest-summary.md` and the corresponding run log first
  - if the anomaly is timeout-driven stale tail, partial worktree diff, or profile mismatch, repair the
    runtime path and rerun instead of classifying the target spec as poor quality
- `No eligible auto-refinement gaps found.`
  - this means the automatic selector found no runnable non-gated work item
  - if pending gate actions are printed, the graph still has work; resolve or redirect those gates before
    expecting the default selector to continue

### Quick Commands

```bash
python tools/supervisor.py --dry-run
python tools/supervisor.py
cat runs/latest-summary.md
```

Canonical YAML helpers for spec nodes:

```bash
python tools/spec_yaml_format.py
python tools/spec_yaml_lint.py
python tools/python_quality.py
```

Both commands default to `specs/nodes/*.yaml`. The formatter rewrites files into the
repository's canonical YAML style; the linter enforces syntax, rejects duplicate keys,
and fails when a file has drifted from canonical formatting. Canonical spec nodes now
require top-level `created_at` and `updated_at` timestamps immediately after `kind`.

To backfill those fields onto existing specs from git history with filesystem fallback:

```bash
python tools/spec_backfill_timestamps.py
```

`python_quality.py` mirrors the blocking `python-quality` CI job by running:

- `ruff check .`
- `ruff format --check .`
- `python tools/spec_yaml_lint.py`

The same project-wide gate is also installed in `.pre-commit-config.yaml` as the
`python-quality` hook.

Quality tool versions are intentionally pinned to match GitHub Actions:

- `ruff==0.15.9`
- `pytest==9.0.2`
- `pyyaml==6.0.3`


## JSON Knowledge Search MVP

Use `tools/search_kg_json.py` to extract and search structured requirement statements from nested
conversation archives stored as JSON files.

Example:

```bash
python tools/search_kg_json.py "success criteria limitations" --json-dir /path/to/jsons --limit 15
```

The script traverses each JSON tree, extracts requirement-like lines, classifies them (`goal`,
`constraint`, `acceptance`, `risk`, `scope`, `assumption`), and prints ranked matches with:
- filename
- JSON path
- requirement kind
- matched text preview

For machine-readable search output:

```bash
python tools/search_kg_json.py "acceptance evidence" --json-dir /path/to/jsons --format json
```

To dump all extracted requirement records instead of ranked matches:

```bash
python tools/search_kg_json.py --json-dir /path/to/jsons --dump-requirements --format json
```

Filter by kind when needed:

```bash
python tools/search_kg_json.py "acceptance evidence" --json-dir /path/to/jsons --kind acceptance
```

To emit derived projection/provenance artifacts for downstream tooling:

```bash
python tools/search_kg_json.py \
  --json-dir /path/to/jsons \
  --dump-requirements \
  --artifact-dir /path/to/output
```

This writes:
- `requirement_projection.json`
- `requirement_provenance.json`

The tool also stores a request-response cache at `<json-dir>/.search_kg_cache.json` by default for fast repeated queries.
Use `--cache-file` to override location or `--no-cache` to disable it.

## PageIndex Conversation Search

Use `tools/search_pageindex.py` to search indexed ChatGPT conversations through the local PageIndex API.
It is the companion search tool for the PageIndex manual in `tools/docs/PAGEINDEX_SEARCH_MANUAL.md`.

Example:

```bash
python3 tools/search_pageindex.py "agent orchestration" --top-k 10 --context
```

The script expects the PageIndex API to be running on `http://localhost:8765` and uses the
`~/Development/GitHub/PageIndexInstance/results/chatgpt_dialogs/catalog.json` catalog by default.
