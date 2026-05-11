# Supervisor Manual

This document is the practical operator and contributor guide for `tools/supervisor.py`.

Use it when you need to:

- understand what the supervisor is allowed to do
- run bounded refinement safely
- interpret run outcomes and gates
- debug runtime failures versus real spec-quality blockers
- continue work on an existing branch of the graph without losing context

For constitutional limits, see [CONSTITUTION.md](../CONSTITUTION.md).
For repository editing rules, see [AGENTS.md](../AGENTS.md).
For a compact artifact map aimed at dashboards and graph visualizers, see
[metrics_visualization_guide.md](./metrics_visualization_guide.md).
For the dedicated `SpecPM` package/export/import viewer contract, see
[specpm_viewer_contract.md](./specpm_viewer_contract.md).
For the ContextBuilder exploration/assumption-mode viewer contract, see
[exploration_preview_viewer_contract.md](./exploration_preview_viewer_contract.md).
For the ContextBuilder graph backlog drill-down viewer contract, see
[graph_backlog_projection_viewer_contract.md](./graph_backlog_projection_viewer_contract.md).
For the ContextBuilder proposal/spec trace viewer contract, see
[proposal_spec_trace_viewer_contract.md](./proposal_spec_trace_viewer_contract.md).
For the ContextBuilder spec activity feed viewer contract, see
[spec_activity_feed_viewer_contract.md](./spec_activity_feed_viewer_contract.md).
For the planned Implementation Work delta/work-index viewer contract, see
[implementation_work_viewer_contract.md](./implementation_work_viewer_contract.md).

## 1. Supervisor Role

The supervisor is an execution layer, not a governance layer.

It may:

- refine one bounded spec node at a time
- run targeted local graph refactors already allowed by current specs
- emit derived observations, signals, summaries, queues, and proposals
- materialize one bounded child spec when current policy and run authority allow it

It may not:

- silently redefine ontology
- silently redefine policy
- silently expand its own authority
- silently convert proposals into canonical truth

Short formula:

- SpecGraph governs
- supervisor executes
- run artifacts inform
- human approval resolves constitutional change

## 2. Core Working Model

The default loop is:

1. select one bounded target
2. create an isolated worktree
3. run a nested child executor
4. validate changed files and graph reconciliation
5. classify the result
6. sync accepted canonical changes
7. write run artifacts

The supervisor is intentionally narrow:

- one spec node at a time
- one bounded concern per run
- no silent scope expansion
- no broad opportunistic cleanup

## 3. Capability Map

Use this map first when you need to decide what the supervisor is for a
particular task.

- refine one bounded spec: `--target-spec SG-SPEC-XXXX`
- inspect what default selection would do: `--dry-run`
- batch bounded work aggressively: `--loop --auto-approve`
- inspect subtree shape and reflective signals without mutation:
  `--target-spec SG-SPEC-XXXX --observe-graph-health`
- emit one structured split proposal without canonical mutation:
  `--target-spec SG-SPEC-XXXX --split-proposal`
- apply one approved split proposal into canonical parent/child specs:
  `--target-spec SG-SPEC-XXXX --apply-split-proposal`
- resolve a human review gate:
  `--resolve-gate SG-SPEC-XXXX --decision approve`
- validate one normalized transition packet JSON file:
  `--validate-transition-packet path/to/packet.json`
  with optional profile override:
  `--validate-transition-packet path/to/packet.json --transition-profile specgraph_core`
- drive one bounded run from a mediated request packet:
  `--operator-request-packet path/to/request.json`
- build the flattened shared vocabulary layer:
  `--build-vocabulary-index`
- inspect vocabulary drift across specs and governed policy artifacts:
  `--build-vocabulary-drift-report`
- inspect tracked pre-spec semantics and downstream lineage:
  `--build-pre-spec-semantics-index`
- build a derived spec-to-code trace index:
  `--build-spec-trace-index`
- build a derived evidence-plane index:
  `--build-evidence-plane-index`
- build a viewer/inspection overlay from the evidence plane:
  `--build-evidence-plane-overlay`
- build a bridge index for declared external consumers such as `Metrics/SIB`:
  `--build-external-consumer-index`
- build a viewer/backlog overlay for sibling-consumer bridges:
  `--build-external-consumer-overlay`
- build reviewable downstream packets for stable sibling consumers:
  `--build-external-consumer-handoffs`
- build a reviewable `SpecPM` package preview from a declared export contract:
  `--build-specpm-export-preview`
- build reviewable `SpecPM` handoff packets on top of the current preview:
  `--build-specpm-handoff-packets`
- build a reviewable `SpecPM` import preview from local materialized bundles:
  `--build-specpm-import-preview`
- build a reviewable `SpecPM` delivery workflow from local materialized bundles:
  `--build-specpm-delivery-workflow`
- build a review-feedback learning-loop index from tracked records:
  `--build-review-feedback-index`
- build a derived `SpecPM` feedback index from current delivery state and
  downstream checkout observations:
  `--build-specpm-feedback-index`
- build a read-only `SpecPM` public registry observation index from current
  materialization state and the local-dev registry endpoint:
  `--build-specpm-public-registry-index`
- build a reviewable `Metrics` delivery workflow from sibling-consumer handoffs:
  `--build-metrics-delivery-workflow`
- build a derived `Metrics` feedback index from current delivery state and
  downstream checkout observations:
  `--build-metrics-feedback-index`
- build metric-driven derived signals from trace, evidence, graph health, and proposal runtime:
  `--build-metric-signal-index`
- turn metric-threshold breaches into reviewable proposal artifacts:
  `--build-metric-threshold-proposals`
- build supervisor runtime/yield/graph-impact metrics from historical run logs:
  `--build-supervisor-performance-index`
- build an advisory minimal-seed bootstrap smoke benchmark report:
  `--build-bootstrap-smoke-benchmark`
- refresh local viewer-facing generated surfaces in one pass:
  `--build-viewer-surfaces`
- build one aggregated graph dashboard for a viewer or visualizer:
  `--build-graph-dashboard`
- build a normalized backlog projection from existing derived surfaces:
  `--build-graph-backlog-projection`
- build a read-only advisory next-move surface:
  `--build-graph-next-moves`
- build a viewer-facing spec activity feed:
  `--build-spec-activity-feed` or `make spec-activity`
- build a repository-tracked intent-layer overlay:
  `--build-intent-layer-overlay`
- build a review-only assumption-mode exploration preview from root intent text:
  `--build-exploration-preview --exploration-intent "..."`
- build a review-only branch rewrite preview from one bounded active subtree:
  `--build-branch-rewrite-preview --target-spec SG-SPEC-0026`
- build a derived implementation delta snapshot from an explicit target scope:
  `--build-implementation-delta-snapshot --target-scope-kind spec --target-spec-ids SG-SPEC-0001 --operator-intent "..."`
  Use `--target-scope-kind active_subtree` when the selected spec ids are graph
  region roots that should expand through active `refines` descendants.
- build bounded implementation work items from the latest delta snapshot:
  `--build-implementation-work-index`
- build a repository-tracked proposal-lane overlay:
  `--build-proposal-lane-overlay`
- build a derived proposal runtime index:
  `--build-proposal-runtime-index`
- build a derived proposal-to-spec trace index:
  `--build-proposal-spec-trace-index` or `make proposal-spec-trace`
- inspect stale review/runtime residue without refinement:
  `--list-stale-runtime`
- clean stale review/runtime residue:
  `--clean-stale-runtime`

## 4. Main Modes

### Default selection

```bash
python3 tools/supervisor.py
```

Uses selector heuristics to choose the next eligible bounded refinement.

### Explicit targeted refinement

```bash
python3 tools/supervisor.py --target-spec SG-SPEC-0003
```

Use this when the operator already knows which spec to work on.

### Loop mode

```bash
python3 tools/supervisor.py --loop --auto-approve
```

Use only when you want an aggressive autonomous batch. It is effective, but it can stall on repeated no-op or structural blockers if the graph still has unresolved decomposition points.

### Graph-health observation

```bash
python3 tools/supervisor.py --target-spec SG-SPEC-0003 --observe-graph-health
```

Non-mutating subtree inspection. Use this when you want to understand:

- shape pressure such as `depth_without_breadth`
- breadth pressure such as `refinement_fan_out_pressure`
- broad-hub classification versus `healthy_multi_child_aggregate`
- role-legibility signals such as `role_obscured_node`
- whether shape pressure has crossed the explicit `SpecGraph -> TechSpec`
  boundary as `techspec_handoff_candidate`
- cluster-first recommendations such as `regroup_under_intermediate_cluster`
- whether a subtree still contains active versus historical descendants
- what rewrite/merge action the current graph health recommends

When `techspec_handoff_candidate` is present, proposal-oriented flows now
prefer explicit handoff over deeper canonical slicing:

- queue items carry `transition_profile: techspec`
- downstream packet family is `handoff`
- proposal queue emits `handoff_proposal` rather than another generic refactor

### Split proposal mode

```bash
python3 tools/supervisor.py --target-spec SG-SPEC-0003 --split-proposal
```

Generates a structured split artifact under `runs/proposals/` without mutating canonical specs.

### Apply split proposal mode

```bash
python3 tools/supervisor.py --target-spec SG-SPEC-0003 --apply-split-proposal
```

Materializes an approved split proposal into canonical parent/child specs.

### `--build-graph-health-overlay`

```bash
python3 tools/supervisor.py --build-graph-health-overlay
```

Builds `runs/graph_health_overlay.json` from the accepted canonical graph. This
is the compact viewer/report layer for current graph-health pressure, grouped by:

- active signals
- recommended actions
- named filters such as oversized or atomicity pressure, weak linkage, shape
  pressure, role-legibility pressure, clustering pressure, and handoff pressure

Use it when you want to see which regions currently need attention without
opening raw `runs/*.json` one by one.

### `--build-graph-health-trends`

```bash
python3 tools/supervisor.py --build-graph-health-trends
```

Builds `runs/graph_health_trends.json` from historical run logs plus a fresh
`runs/graph_health_overlay.json`. This is the longitudinal reporting layer for:

- recurring structural problems
- signals that are still active now versus only historically recurrent
- repeated split pressure, weak linkage, shape pressure, and handoff pressure

Use it when one bad run is not the question anymore and you need to see whether
the same graph pathology keeps returning over time.

### Transition-packet validation

```bash
python3 tools/supervisor.py --validate-transition-packet transition-packet.json
```

Validates one normalized transition packet JSON file and prints structured
findings. This is a deterministic legality check, not a semantic-quality judge.

The validator now exposes:

- packet families: `promotion`, `proposal`, `apply`, `handoff`
- check families: `schema`, `legality`, `provenance`, `boundedness`,
  `authority`, `reconciliation`, `diff_scope`, `profile`
- validator profiles: `specgraph_core`, `product_spec`, `techspec`,
  `implementation_trace`

Use `--transition-profile ...` when you want to validate the same packet under
another governed artifact family without changing the packet file itself.

`product_spec` now inherits the same deterministic transition engine by binding
one `product_graph_root` rather than redefining promotion/apply semantics per
product domain. The inherited rules live in
`tools/product_spec_transition_policy.json`:

- packets must declare `product_graph_root`
- product-specific provenance must preserve `product_graph_root`
- `apply` packets must source from reviewable proposal/run artifacts
- `apply` mutation surfaces must stay inside `product_graph_root`

`promotion` packets now also expose the governed draft-to-proposal semantic
boundary from `tools/proposal_promotion_policy.json`. That artifact defines:

- `working_draft` as exploratory material
- `reviewable_proposal` as normalized proposal contract
- the rule that promotion is normalization, not a bare repository-folder move

The minimal promotion packet contract is now explicit:

- `source_artifact_class: working_draft`
- `target_artifact_class: reviewable_proposal`
- `source_refs`
- `motivating_concern`
- `normalized_title`

### Operator-request bridge

```bash
python3 tools/supervisor.py --operator-request-packet operator-request.json
```

Use this when the upstream input is already a bounded mediated request and you
want that request, not ad hoc CLI flags, to steer one supervisor run.

The packet is intentionally narrower than the transition engine:

- it is pre-canonical run steering, not artifact promotion/apply
- it may target only one bounded run mode such as `targeted_refine` or
  `split_proposal`
- it may not silently mutate canonical specs by itself

Current bridge behavior:

- validates one `operator_request_packet` against
  `tools/operator_request_bridge_policy.json`
- normalizes the request into a typed `OperatorRequest` with explicit
  `authority`, `mutation_budget`, `stop_conditions`, and `execution_contract`
- mirrors `user_intent` and `operator_request` into tracked
  `intent_layer/nodes/*.json`
- routes the request into one ordinary targeted refinement or explicit
  split-proposal pass
- records the request lineage in run payloads and, when proposals are emitted,
  carries that lineage forward into proposal-lane nodes
- keeps the packet as the sole steering envelope for that run, so
  `--target-spec`, `--operator-note`, `--mutation-budget`, `--run-authority`,
  and `--execution-profile` are not mixed in separately

Lower-boundary handoff is now also governed by
`tools/techspec_handoff_policy.json`. That artifact defines:

- the canonical `SpecGraph -> TechSpec` boundary
- the primary signal `techspec_handoff_candidate`
- the downstream handoff target as `techspec` + `handoff`
- the point where canonical decomposition should stop and proposal-first
  handoff should begin
- `bounded_scope`
- `required_provenance_links` including `source_draft_ref`

### Vocabulary index

```bash
python3 tools/supervisor.py --build-vocabulary-index
```

Builds `runs/vocabulary_index.json` from `tools/specgraph_vocabulary.json`.

Use it when you need one shared ontology surface for:

- canonical terms
- aliases
- deprecated aliases
- term families
- vocabulary contexts and ownership

This is the flattened machine-readable vocabulary layer that specs, policy
artifacts, and viewer/report surfaces should converge on.

### Vocabulary drift report

```bash
python3 tools/supervisor.py --build-vocabulary-drift-report
```

Builds `runs/vocabulary_drift_report.json` from the shared vocabulary,
governed policy artifacts, and canonical spec terminology.

It currently flags:

- undefined terms
- alias collisions
- deprecated alias usage outside sanctioned mapping surfaces
- meaning divergence when a canonical spec defines a shared term outside its
  owning vocabulary boundary

### Pre-spec semantics index

```bash
python3 tools/supervisor.py --build-pre-spec-semantics-index
```

Builds `runs/pre_spec_semantics_index.json` from:

- tracked `intent_layer/nodes/*.json`
- proposal-lane lineage
- canonical `last_pre_spec_provenance` metadata

Use it when you want to inspect the pre-spec semantic layer as its own governed
surface instead of treating user intent, operator requests, proposals, and
canonical candidates as disconnected artifacts.

### Spec trace index

```bash
python3 tools/supervisor.py --build-spec-trace-index
```

Builds `runs/spec_trace_index.json` from literal `SG-SPEC-XXXX` mentions in
`tools/` and `tests/`, then enriches that graph-bound index with weak
`commit_refs`, `pr_refs`, `verification_basis`, and `acceptance_coverage`.

Use it as the first weak derived view of spec-to-code coverage. It is still not
an implementation-state oracle.

`implementation_state` is now derived conservatively from
`tools/spec_trace_registry.json`:

- no explicit trace contract: `unclaimed`
- declared contract with no matched anchors yet: `planned`
- declared contract with local changes on tracked surfaces: `in_progress`
- declared contract with implementation anchors only: `implemented`
- declared contract with both implementation and verification anchors: `verified`
- declared contract whose code moved beyond the last trusted verification anchor: `drifted`
- declared contract blocked by review or unresolved dependencies: `blocked`

`freshness` is derived separately from trusted verification timestamps:

- no explicit trace contract: `not_tracked`
- embodiment not yet meaningful: `not_applicable`
- tracked surfaces currently dirty: `dirty_worktree`
- verification anchors not yet matched: `pending_verification`
- verification anchors exist but timestamps are unavailable: `verification_time_unknown`
- implementation and spec are aligned with the latest trusted verification: `fresh`
- the governing spec moved after the latest trusted verification: `stale_spec`
- implementation changed after the latest trusted verification: `drifted_after_verification`

### Spec trace projection

```bash
python3 tools/supervisor.py --build-spec-trace-projection
```

Builds `runs/spec_trace_projection.json` from a freshly generated
`runs/spec_trace_index.json`.

Use it when you want an operator-facing projection instead of raw trace entries.
The projection groups nodes by:

- `implementation_state`
- `freshness`
- `acceptance_coverage`

and exposes:

- named viewer filters such as `verified_stale_spec`, `drifted`, and
  `implemented_without_verification`
- an `implementation_backlog` grouped by next reflective gap such as
  `attach_trace_contract`, `add_verification_anchors`, `refresh_after_spec_update`,
  or `reverify_after_drift`

### Evidence-plane index

```bash
python3 tools/supervisor.py --build-evidence-plane-index
```

Builds `runs/evidence_plane_index.json` from canonical specs, the explicit
registry in `tools/runtime_evidence_registry.json`, and already-derived runtime
artifacts under `runs/`.

This is intentionally conservative:

- canonical specs remain the truth source
- evidence stays derived
- raw telemetry payloads are still out of scope

Each entry links one canonical `spec_id` to:

- declared artifact refs
- declared runtime entities
- observation markers
- outcome markers
- adoption markers
- one conservative `chain_status`

Use it when you need to answer “does this spec have any runtime-backed evidence
chain yet, and where is that chain still incomplete?”.

### Evidence-plane overlay

```bash
python3 tools/supervisor.py --build-evidence-plane-overlay
```

Builds `runs/evidence_plane_overlay.json` from a freshly generated
`runs/evidence_plane_index.json`.

Use it when you want the operator/report projection instead of raw evidence
entries. The overlay groups nodes by:

- `chain_status`
- artifact-stage status
- observation coverage
- outcome coverage
- adoption coverage

and exposes:

- named filters such as `missing_evidence_contract`, `artifact_gap`,
  `outcome_gap`, and `complete_chain`
- an `evidence_backlog` grouped by next bounded gap such as
  `attach_evidence_contract`, `collect_outcome_evidence`, or
  `collect_adoption_evidence`

### Metric signal index

```bash
python3 tools/supervisor.py --build-metric-signal-index
```

Builds `runs/metric_signal_index.json` from a fresh in-memory pass over the
current trace plane, evidence plane, graph-health overlays/trends, and proposal
runtime index.

This layer stays explicitly derived:

- metric scores are advisory
- thresholds are review inputs
- canonical specs do not store these values

Current bootstrap metric families are:

- `specification_verifiability`
- `process_observability`
- `structural_observability`
- `sib`
- `node_inference_cost`
- `verification_cost`
- `sib_eff_star`
- `defect_balance_at_root`

`sib` is the bridge-native SIB metric family:

- `bridge_backed` when a stable external consumer such as `Metrics/SIB` is
  locally available through the declared bridge registry
- `bootstrap_fallback` when no stable bridge is locally available and the
  metric must fall back to internal SpecGraph-derived surfaces only

`sib_proxy` remains present as a compatibility alias entry in
`metric_signal_index.json`, with `alias_of = "sib"` and
`threshold_authority_state = "alias_only"`. Viewers may keep reading it during
migration, but threshold proposals are emitted only for `sib`.

`node_inference_cost` and `verification_cost` are economic-observability proxy
metrics. They expose observed activity units from model-usage telemetry and
review-feedback verification records. They are proxy activity units until a
monetary spend derivation exists. `price_status` only reports whether a pricing
source is connected, and the metrics do not carry threshold authority.

`sib_eff_star` and `defect_balance_at_root` are SIB_FULL draft proxy metrics.
They exist to make the draft pack inspectable end-to-end; they do not assert
final research formulas or threshold authority.

Each metric entry records:

- current score
- minimum healthy threshold
- threshold gap
- emitted advisory signal when below threshold
- input summary explaining which derived surfaces contributed

### External consumer index

```bash
python3 tools/supervisor.py --build-external-consumer-index
```

Builds `runs/external_consumer_index.json` from
`tools/external_consumers.json`.

This is the first governed bridge surface for sibling repositories such as
`Metrics`.

The index reports:

- declared consumer identity and reference state
- local checkout availability
- declared artifact verification status
- contract readiness
- metric bindings such as the stable `Metrics/SIB` bridge for `sib`

This layer is still derived-only. It does not import external repositories into
canonical truth and does not require Git submodules.

Use it when you want metric-driven pressure to be machine-readable without
turning those metrics into canonical facts or policy by default.

### External consumer overlay

```bash
python3 tools/supervisor.py --build-external-consumer-overlay
```

Builds `runs/external_consumer_overlay.json` from a fresh bridge index and a
fresh metric signal index.

This viewer-facing layer answers:

- which stable bridges are ready
- which stable bridges are blocked by missing checkout or wrong repo identity
- which contracts are partial because declared artifacts drifted
- which draft references are visible but still non-authoritative
- what the next bounded remediation gap is for each sibling consumer

The overlay adds:

- `bridge_state`
- `bound_metric_status`
- named filters such as `stable_ready`, `identity_unverified`, and `metric_pressure`
- `external_consumer_backlog` grouped by `next_gap`

This is the preferred visualizer surface for sibling-consumer bridge state.

### External consumer handoffs

```bash
python3 tools/supervisor.py --build-external-consumer-handoffs
```

Builds `runs/external_consumer_handoff_packets.json` from:

- `runs/external_consumer_index.json`
- `runs/external_consumer_overlay.json`
- `runs/metric_signal_index.json`
- `runs/metric_threshold_proposals.json`

This is the first explicit `SpecGraph -> Metrics` handoff surface.

Each declared external consumer is classified into:

- `ready_for_handoff`
- `blocked_by_bridge_gap`
- `draft_reference_only`

Only stable-ready consumers receive a normalized downstream `handoff` packet.
Today that means `Metrics/SIB` can become reviewable handoff material, while
`Metrics/SIB_FULL` remains visible as draft-only context and next-gap pressure.

### SpecPM export preview

```bash
python3 tools/supervisor.py --build-specpm-export-preview
```

Builds `runs/specpm_export_preview.json` from:

- `tools/specpm_export_registry.json`
- `runs/external_consumer_index.json`
- `runs/external_consumer_overlay.json`
- the canonical source specs named in the export registry

This layer is intentionally preview-first.

It emits:

- a minimal `specpm.yaml`-shaped manifest preview
- a boundary-source preview rooted in canonical `SG-SPEC-*` sources
- explicit missing fields that still block a future full `BoundarySpec`

Use it when you want to review:

- which bounded `SpecGraph` region is being prepared for `SpecPM`
- whether `SpecPM` is only draft-visible or later becomes stable-ready
- which package ID, version, summary, and capability IDs are already declared
- what still needs to be governed before true package export/import can exist

Because the current `SpecPM` RFC remains draft, a valid preview may still land
in `draft_preview_only` rather than `ready_for_review`.

### SpecPM handoff packets

```bash
python3 tools/supervisor.py --build-specpm-handoff-packets
```

Builds `runs/specpm_handoff_packets.json` from:

- a freshly rebuilt `runs/specpm_export_preview.json`
- `runs/external_consumer_index.json`

This layer is intentionally one step beyond preview, but still review-first.

It emits:

- one handoff entry per declared `SpecPM` export entry
- explicit `handoff_status` such as `ready_for_handoff`, `draft_preview_only`,
  `blocked_by_preview_gap`, or `invalid_export_contract`
- target consumer identity, local checkout hint, manifest preview, and
  boundary-source preview
- a normalized transition packet only when the export is actually ready for
  downstream handoff

Use it when you want to review:

- whether a given `SpecPM` export preview is now ready to be handed off
- which package preview and boundary source would be carried downstream
- which preview gaps still block downstream delivery

### SpecPM local export bundle materialization

```bash
python3 tools/supervisor.py --materialize-specpm-export-bundles
```

Builds `runs/specpm_materialization_report.json` from:

- a freshly rebuilt `runs/external_consumer_index.json`
- a freshly rebuilt `runs/specpm_export_preview.json`
- a freshly rebuilt `runs/specpm_handoff_packets.json`

This layer is still review-first, but it goes one step beyond handoff packets:
it writes a local draft export bundle into the sibling `SpecPM` checkout under
its controlled inbox root `.specgraph_exports/<package_id>/`.

It emits:

- one materialization entry per eligible `SpecPM` handoff entry
- explicit `materialization_status` such as `materialized_for_review`,
  `draft_materialized`, `blocked_by_handoff_gap`,
  `blocked_by_checkout_gap`, `blocked_by_consumer_identity`, or
  `invalid_handoff_contract`
- a local bundle containing `specpm.yaml`, `specs/main.spec.yaml`,
  copied source evidence, and `handoff.json`
- a report surface that viewer code can use for export-preview and
  review-readiness states without auto-committing into `SpecPM`

Use it when you want to review:

- whether a given `SpecPM` handoff is now locally materializable
- what exact draft bundle would be placed into the sibling checkout
- which checkout, identity, or handoff gaps still block downstream review

### SpecPM import preview

```bash
python3 tools/supervisor.py --build-specpm-import-preview
```

Builds `runs/specpm_import_preview.json` from:

- a freshly rebuilt `runs/external_consumer_index.json`
- local bundles already present under the sibling `SpecPM` checkout at
  `.specgraph_exports/<package_id>/`

This layer is intentionally import-preview-only.

It emits:

- one entry per discovered local bundle
- explicit `import_status` such as `ready_for_review`, `draft_visible`,
  `blocked_by_bundle_gap`, or `invalid_import_contract`
- per-bundle validation of `specpm.yaml`, `specs/main.spec.yaml`, and
  `handoff.json`
- continuity checks back to the original SpecGraph handoff packet
- a suggested upstream target kind such as `proposal`, `pre_spec`, or
  `handoff_candidate`

Use it when you want to review:

- whether a local `SpecPM` bundle is structurally sound enough for inbound
  discussion
- whether the bundle still preserves continuity with the original export/handoff
- what would be the next reviewable upstream artifact inside `SpecGraph`

This command does **not** import anything into canonical specs and does not
write proposal-lane or intent-layer nodes automatically.

### SpecPM import handoff packets

```bash
python3 tools/supervisor.py --build-specpm-import-handoff-packets
```

Builds `runs/specpm_import_handoff_packets.json` from:

- a freshly rebuilt `runs/external_consumer_index.json`
- a freshly rebuilt `runs/specpm_import_preview.json`

This layer stays review-first, but it goes one step beyond import preview:
valid inbound bundles become explicit upstream routing candidates without
creating proposal-lane nodes or mutating canonical specs directly.

It emits:

- one handoff entry per imported bundle preview
- explicit `handoff_status` such as `ready_for_lane`, `draft_visible_only`,
  `blocked_by_import_gap`, or `invalid_import_contract`
- target-route metadata such as `proposal_lane_candidate`,
  `handoff_candidate`, or `pre_spec_candidate`
- a normalized transition packet only when the bundle is actually ready for a
  proposal-lane style handoff
- grouped backlog by `next_gap` for review-first upstream intake

Use it when you want to review:

- whether an inbound `SpecPM` bundle is ready to become a proposal-lane review
  candidate
- whether it should stay visible only as a draft handoff or pre-spec intake
- which import gaps still block upstream intake

This command does **not** apply imports into canonical specs and does not write
proposal-lane nodes automatically.

### SpecPM delivery workflow

```bash
python3 tools/supervisor.py --build-specpm-delivery-workflow
```

Builds `runs/specpm_delivery_workflow.json` from:

- a freshly rebuilt `runs/external_consumer_index.json`
- a freshly rebuilt `runs/specpm_export_preview.json`
- a freshly rebuilt `runs/specpm_handoff_packets.json`
- a freshly rebuilt `runs/specpm_materialization_report.json`

This layer stays review-first, but it moves one step beyond local
materialization: it inspects the real git state of the sibling `SpecPM`
checkout and turns bundle delivery into an explicit downstream review workflow.

It emits:

- one delivery entry per materialized package bundle
- explicit `delivery_status` such as `ready_for_delivery_review`,
  `draft_delivery_only`, `blocked_by_materialization_gap`,
  `blocked_by_checkout_gap`, `blocked_by_repo_state`, or
  `invalid_materialization_contract`
- git checkout diagnostics such as current branch, upstream, ahead/behind
  counts, bundle-scoped changed paths, and unrelated changed paths
- suggested downstream branch, commit subject, PR title, and ordered workflow
  steps

Use it when you want to review:

- whether a materialized `SpecPM` bundle is actually safe to move into
  downstream review
- whether unrelated dirt in the sibling checkout would contaminate delivery
- what exact branch/commit/PR scaffold should be used for downstream exchange

This command does **not** commit into `SpecPM`, does not push a branch, and
does not create a downstream PR automatically.

### SpecPM feedback index

```bash
python3 tools/supervisor.py --build-specpm-feedback-index
```

Builds `runs/specpm_feedback_index.json` from:

- a freshly rebuilt `runs/specpm_export_preview.json`
- the current `runs/specpm_delivery_workflow.json` when present, otherwise a
  safe rebuild from the existing materialization report
- the observed git state of the sibling `SpecPM` checkout for each package

This layer stays review-first and derived. It does not import anything back
into canonical specs. Instead, it turns downstream checkout observations into
an explicit feedback surface.

It emits:

- one feedback entry per `SpecPM` package under observation
- explicit `feedback_status` such as `downstream_unobserved`,
  `review_activity_observed`, `adoption_observed_locally`,
  `blocked_by_delivery_gap`, or `invalid_feedback_contract`
- observed checkout signals such as tracked bundle paths, latest bundle commit,
  branch/upstream context, and bundle-scoped dirty paths
- source-spec linkage back to the originating `SpecGraph` export contract
- grouped backlog by `next_gap` for follow-up review or adoption collection

Use it when you want to review:

- whether downstream `SpecPM` work has started beyond local draft materialization
- whether a bundle is only tracked on a review branch or appears locally
  adopted on a default branch
- which next follow-up gap should be surfaced without treating downstream
  state as automatic canonical acceptance

### SpecPM public registry observation

```bash
python3 tools/supervisor.py --build-specpm-public-registry-index
```

Builds `runs/specpm_public_registry_index.json` from:

- `tools/external_consumers.json`, specifically the `specpm.registry` contract
- the current `runs/specpm_materialization_report.json`
- `tools/specpm_export_registry.json` for expected capability IDs
- read-only HTTP probes against the configured local-dev registry base URL

The registry base URL is `http://localhost:8081` in dev mode. Do not configure
it as `http://localhost:8081/v0`; endpoint templates carry the `/v0/...`
prefix.

This layer does not publish packages, mutate `SpecPM`, or mutate canonical
`SpecGraph` specs. If the local registry service is unavailable, the artifact
reports `registry_unavailable` as an observation gap rather than a lifecycle
blocker.

It emits:

- one registry entry per materialized SpecPM package identity
- package/version probes for `/v0/packages/{package_id}` and
  `/v0/packages/{package_id}/versions/{version}`
- capability-search probes for `/v0/capabilities/{capability_id}/packages`
- intent-search probes for `/v0/intents/{intent_id}/packages`
- `registry_visible`, `registry_missing`, `registry_drift`, or
  `registry_unavailable` package statuses
- viewer filters for registry visibility/searchability outcomes, including
  `visible_package_versions`, `searchable_capabilities`, `searchable_intents`,
  `missing_package_versions`, `missing_capabilities`, `missing_intents`,
  `registry_drift`, and `dev_observation_only`

Use it when you want to review:

- whether a materialized local draft bundle is visible through the SpecPM
  static registry service
- whether expected package versions, capabilities, or intents are missing from `/v0`
- whether registry payloads drift from the current SpecGraph materialization
  expectations

### Metrics delivery workflow

```bash
python3 tools/supervisor.py --build-metrics-delivery-workflow
```

Builds `runs/metrics_delivery_workflow.json` from a freshly rebuilt external
consumer bridge, metric signal index, threshold proposals, and
`runs/external_consumer_handoff_packets.json`.

This layer is the reviewable `SpecGraph -> Metrics` workflow. It inspects the
real git state of the sibling `Metrics` checkout and turns ready Metrics/SIB
handoff packets into explicit downstream branch, commit, and PR scaffolding.

It emits:

- one delivery entry per sibling metric consumer handoff
- `delivery_status` such as `ready_for_delivery_review`,
  `draft_delivery_only`, `blocked_by_handoff_gap`,
  `blocked_by_checkout_gap`, `blocked_by_repo_state`, or
  `invalid_handoff_contract`
- git checkout diagnostics scoped to `.specgraph_handoffs/<consumer_id>/`
- suggested downstream branch, commit subject, PR title, and ordered workflow
  steps

This command does **not** write into `Metrics`, does not commit, does not push,
and does not create a downstream PR automatically.

### Metrics feedback index

```bash
python3 tools/supervisor.py --build-metrics-feedback-index
```

Builds `runs/metrics_feedback_index.json` from the current
`runs/metrics_delivery_workflow.json` when present, otherwise from the current
external-consumer handoff artifact, plus observed git state in the sibling
`Metrics` checkout.

This layer is the reverse ingestion path for Metrics observations. It keeps
downstream review/adoption signals derived and reviewable rather than treating
them as canonical SpecGraph truth.

It emits:

- one feedback entry per Metrics delivery candidate
- `feedback_status` such as `downstream_unobserved`,
  `review_activity_observed`, `adoption_observed_locally`,
  `blocked_by_delivery_gap`, or `invalid_feedback_contract`
- tracked handoff paths, latest handoff commit, branch/upstream context, and
  handoff-scoped dirty paths
- metric bindings and threshold-proposal links for viewer or dashboard
  grouping

Use it when you want to see whether a Metrics handoff has moved beyond local
SpecGraph artifacts into downstream review or local adoption, without making
that downstream state canonical automatically.

### Metrics source promotion index

```bash
python3 tools/supervisor.py --build-metrics-source-promotion-index
```

Builds `runs/metrics_source_promotion_index.json` from:

- a freshly rebuilt `runs/external_consumer_index.json`
- a freshly rebuilt `runs/metric_signal_index.json`
- a freshly rebuilt `runs/metric_pack_index.json`

This layer defines the review path for `Metrics/SIB_FULL` and later sibling
metric sources. A draft source can become `ready_for_promotion_review`, but it
does not receive threshold authority automatically.

First-class metric pack authority gates that transition. A draft source remains
`draft_visible_only` while its pack entry is still
`pack_authority_state: not_threshold_authority`; it only becomes
`ready_for_promotion_review` after the pack registry marks it
`pack_authority_state: promotion_candidate`.

It emits:

- one promotion entry per draft sibling metric consumer candidate
- `promotion_status` such as `ready_for_promotion_review`,
  `draft_visible_only`, `blocked_by_pack_authority_gap`,
  `blocked_by_contract_gap`,
  `blocked_by_stable_family_gap`, or `invalid_promotion_contract`
- `authority_state`, where draft sources stay `not_threshold_authority` until
  review makes them operational
- explicit guardrails: `requires_human_review = true`,
  `auto_threshold_authority = false`, and `threshold_authority_grant = false`
  for review candidates
- `draft_visible_only` entries remain visible in the source-promotion index and
  viewer projection, but they are not actionable promotion backlog rows until
  the metric pack becomes `promotion_candidate`

Use it when you want to review whether `Metrics/SIB_FULL` is ready to graduate
from draft reference to operational input without silently changing metric
threshold authority.

### Metric-pack registry drift

```bash
python3 tools/supervisor.py --build-metric-pack-registry-drift
```

Builds `runs/metric_pack_registry_drift.json` by comparing:

- `tools/metric_pack_registry.json` in SpecGraph
- `METRIC_PACKS.md` in the sibling Metrics checkout
- the current external-consumer checkout observations

This is an observation surface only. It can report missing checkout, missing
Metrics contract, pack ID drift, source path mismatch, display-name mismatch,
and missing Metrics source artifacts, but it does not rewrite either repository
and does not execute metric packs.

### Metric-pack adapter index

```bash
python3 tools/supervisor.py --build-metric-pack-adapter-index
```

Builds `runs/metric_pack_adapter_index.json` from the current metric-pack index.

This is the computability layer before metric execution:

- declared pack inputs are mapped to existing SpecGraph source artifacts where
  a binding exists;
- missing inputs become `not_computable` adapter gaps;
- adapter backlog items point to the next narrow input-contract work;
- metric packs are not executed and thresholds are not changed.

Use it when `metric_pack_index` shows packs as visible but you need to know
which inputs still block future `metric_pack_runs.json`.

### Metric-pack runs

```bash
python3 tools/supervisor.py --build-metric-pack-runs
```

Builds `runs/metric_pack_runs.json` from:

- the current metric-pack index;
- the current metric-pack adapter index;
- the current metric-signal index.

This is a derived run snapshot only:

- packs with computable inputs and existing metric signals can expose read-only
  `computed_values`;
- packs with missing adapters remain `not_computable`;
- missing metric value adapters become explicit gaps;
- finding/proposal projection remains deferred;
- canonical specs, thresholds, and policies are not changed.

Use it after `metric-pack-adapters` when you want to inspect whether at least
one metric pack can produce a reviewable run surface.

### Metric pricing provenance

```bash
python3 tools/supervisor.py --build-metric-pricing-provenance
```

Builds `runs/metric_pricing_provenance.json`.

This is the economic-observability guardrail before cost-like metric values:

- records provider, model, tool, execution profile, unit convention, currency
  convention, and pricing version;
- records missing observed spend and missing derived proxy explicitly;
- defines missing-price behavior as an observation gap;
- does not compute economic metric values;
- does not mutate thresholds, policy, or canonical specs.

Use it before making `sib_economic_observability` operational. The artifact can
make `pricing_surface` available as an adapter input while model usage is
observed through `runs/model_usage_telemetry_index.json` and node scope is
mapped through `runs/spec_trace_projection.json`. Verification runs are exposed
as a first proxy through `runs/review_feedback_index.json` via
`viewer_projection.verification_kind`; this is enough to make the input contract
reviewable, but it is not yet a full CI/device-farm cost source.

### Metric-threshold proposals

```bash
python3 tools/supervisor.py --build-metric-threshold-proposals
```

Builds `runs/metric_threshold_proposals.json` from a fresh
`runs/metric_signal_index.json`.

This command is the governance boundary for metric thresholds:

- threshold crossings stay derived
- the next step becomes a reviewable proposal artifact
- no supervisor policy file is mutated automatically

Current output groups breaches by:

- proposal kind
- severity
- target metric

Entries carry:

- breached metric and score
- minimum threshold and threshold gap
- recommended actions
- target surfaces
- a proposal-first transition envelope showing that the result is reviewable
  follow-up, not silent policy tuning

### Supervisor performance index

```bash
python3 tools/supervisor.py --build-supervisor-performance-index
```

Builds `runs/supervisor_performance_index.json` from historical run logs.

This measurement layer keeps three questions separate:

- did the runtime operate cleanly
- did the run produce a meaningful bounded result
- did the graph actually improve

Each run entry records:

- `run_kind`, `execution_profile`, and `child_model`
- `started_at_utc`, `finished_at_utc`, and `run_duration_sec`
- `runtime_status`
- `yield_status`
- `graph_impact_status`
- `same_spec_repeat_count`
- `accepted_canonical_diff`, `proposal_emitted`, and
  `productive_split_required`

The artifact also aggregates:

- runtime/yield/graph-impact counts
- per-run-kind and per-profile counts
- median and max run duration
- same-spec repeat hotspots
- daily batch summaries

Use it when you want to inspect supervisor throughput, intervention cost, and
graph effect over time without collapsing those questions into one score.

### Bootstrap smoke benchmark

```bash
python3 tools/supervisor.py --build-bootstrap-smoke-benchmark
```

Builds `runs/bootstrap_smoke_benchmark.json` as an advisory smoke report over
benchmark-tagged supervisor runs.

The report is intentionally structural:

- it selects the latest smoke batch from `runs/supervisor_performance_index.json`
- it checks productive run count, new child materialization, runtime failures,
  low-yield pressure, blocked graph impact, and fixed-budget compliance
- it never compares exact generated node prose
- it emits `not_run` when no smoke batch is present, rather than failing the
  command

The first benchmark contract is `minimal_seed_structural_yield`. It is
advisory and suitable for manual or scheduled observation before becoming a
blocking CI gate.

### Viewer surfaces refresh

```bash
make viewer-surfaces
```

Writes the local viewer-facing generated surfaces that ContextBuilder commonly
reads:

- `runs/graph_backlog_projection.json`
- `runs/graph_dashboard.json`
- `runs/graph_next_moves.json`
- `runs/metrics_source_promotion_index.json`
- `runs/metric_pack_index.json`
- `runs/conversation_memory_index.json`
- `runs/conversation_memory_map.json`
- `runs/conversation_memory_promotion_pressure.json`
- `runs/spec_activity_feed.json`

This mode is intended for local `post-merge` / `post-checkout` hooks, CI smoke
checks, and viewer build buttons. It refreshes existing read models only: it
does not choose an Implementation Work target scope, create new implementation
work items, mutate canonical specs, or stage generated JSON for commit.

Use this when the viewer needs a current local snapshot after the graph or
derived runtime surfaces changed.

Equivalent direct command:

```bash
python3 tools/supervisor.py --build-viewer-surfaces
```

Use the narrower Metrics-only shortcut when only the Source Promotion overlay
needs its drill-down artifact:

```bash
make metrics-source-promotion
```

Use the narrower conversation-memory shortcut when only the Layer 0 structured
memory surface needs refresh:

```bash
make conversation-memory
```

That command reads curated source records from
`conversation_memory/sources/*.json` and structured markdown notes from
`conversation_memory/notes/*.md`. It does not mine PageIndex or promote memory
records into canonical specs.

Use the map shortcut when the viewer needs the derived exploration projection:

```bash
make conversation-memory-map
```

That command refreshes `runs/conversation_memory_index.json` and then writes
`runs/conversation_memory_map.json` with clusters, links, source coverage,
candidate proposal pressure, and review blockers. It remains read-only and does
not promote memory records into proposals or specs.

Use the pressure shortcut when the viewer needs the explicit promotion-review
queue:

```bash
make conversation-memory-pressure
```

That command refreshes the index and map, then writes
`runs/conversation_memory_promotion_pressure.json`. It exposes reviewable
promotion candidates and map blockers, but it does not create proposal files or
mutate canonical specs.

Standalone artifact commands print compact JSON summaries by default. Use
`--output-mode full` only when the full generated artifact is needed on stdout.
The artifact files under `runs/` are written either way.

### Graph dashboard

```bash
make dashboard
```

Builds `runs/graph_dashboard.json` as one aggregated dashboard artifact for a
viewer or visualizer.

The dashboard is explicitly derived-only. It pulls fresh counts from:

- graph health overlay and trends
- intent and proposal-lane overlays
- proposal runtime and promotion indexes
- implementation trace projection
- evidence-plane overlay
- metric signal and threshold-proposal artifacts
- review-feedback learning-loop index

The output includes:

- headline cards for quick counts such as total specs, gated specs, structural
  pressure regions, retrospective refactor candidates, verified specs, complete
  evidence chains, review-feedback gaps, and metrics below threshold
- section-level counts for graph, health, proposals, implementation, evidence,
  metrics, and process feedback
- source artifact references with generated timestamps so a visualizer can show
  provenance for each number

### Graph backlog projection

```bash
python3 tools/supervisor.py --build-graph-backlog-projection
```

Builds `runs/graph_backlog_projection.json` as a normalized work/backlog
projection over existing derived surfaces. This is not a canonical task list:
it is a viewer-facing read model that turns graph health, proposal runtime,
trace, Implementation Work, evidence, external-consumer, SpecPM, Metrics,
threshold-proposal, review-feedback gaps, and ready branch rewrite preview
candidates into concrete rows with `domain`, `subject_id`, `next_gap`,
`priority`, and source artifact links.

Use it when the dashboard count needs to become a clickable work queue without
reintroducing `tasks.md` as the source of truth.

### Graph next moves

```bash
make next-move
```

Builds `runs/graph_next_moves.json` as a read-only advisory surface that
answers "what should I do next?" from current graph-derived state.

The artifact is intentionally game-master-like: it describes the current scene,
selects one bounded recommended move, and keeps alternatives or blocked moves
visible without applying them.

Initial source priority is:

- malformed source artifact repair
- ready branch rewrite preview
- highest-priority graph backlog entry
- proposal runtime realization backlog
- steady state

When several backlog rows share the same priority, the selector keeps review
gates and branch rewrite review first, then prefers concrete runtime adapter
gaps such as `metric_pack_runs` + `define_metric_value_adapter` over broad
`review_draft_reference` rows.

The command never mutates canonical specs, proposal-lane nodes, intent-layer
nodes, queues, or downstream repositories.

### Proposal-lane overlay

```bash
python3 tools/supervisor.py --build-proposal-lane-overlay
```

Builds `runs/proposal_lane_overlay.json` from repository-tracked proposal-lane
nodes under `proposal_lane/nodes/`.

Use it when you want to inspect tracked proposal structure as a secondary graph
layer without confusing it with canonical truth. The overlay exposes:

- stable provisional `proposal_handle` values
- `proposal_authority_state` such as `under_review` or
  `approved_for_application`
- `proposal_target_region` ownership against canonical nodes
- lineage edges to canonical nodes or runtime artifacts
- invalid review-visible nodes whose repository presence exists but whose query
  contract is incomplete or colliding

This layer is intentionally separate from runtime-only proposal artifacts:

- `proposal_lane/nodes/*.json` is repository-tracked review state
- `runs/proposals/*.json` remains runtime-scoped structured support state
- canonical specs remain the accepted graph of record

### Intent-layer overlay

```bash
python3 tools/supervisor.py --build-intent-layer-overlay
```

Builds `runs/intent_layer_overlay.json` from repository-tracked intent-layer
nodes under `intent_layer/nodes/`.

Use it when you want to inspect the pre-canonical mediation surface without
confusing it with either proposal-lane review structure or canonical graph
truth. The overlay exposes:

- `intent_layer_kind` separation between `user_intent` and `operator_request`
- `mediation_state` such as `captured`, `mediated`, or `ready_for_execution`
- explicit distinction contracts showing that these artifacts are neither
  canonical specs nor proposal-lane nodes
- lineage edges back to raw-supporting artifacts or forward to bridge outputs
- invalid query-contract nodes whose tracked presence exists but whose kind
  contract or lineage is incomplete

This layer is intentionally narrower than the later first-class pre-spec
semantic work:

- `intent_layer/nodes/*.json` records bounded mediation and run-bridge state
- `runs/pre_spec_semantics_index.json` is the first derived pre-spec semantic
  surface that links those tracked artifacts to downstream proposal-lane and
  canonical lineage
- proposal-lane and canonical specs remain downstream layers, not peers

### Proposal runtime index

```bash
python3 tools/supervisor.py --build-proposal-runtime-index
```

Builds `runs/proposal_runtime_index.json` from `docs/proposals/`,
`tools/proposal_runtime_registry.json`, `tasks.md`, and repository markers in
`tools/` and `tests/`.

Use it when you want to inspect, for each proposal:

- processing posture
- runtime realization status
- validation closure
- observation coverage
- next reflective backlog gap

Each entry now also carries:

- `repository_projection`
- `semantic_artifact_class`

Those fields come from `tools/proposal_promotion_policy.json`. The repository
path is treated as a projection default such as `reviewable_proposal_surface`,
not as the sole source of semantic meaning.

### Proposal promotion index

```bash
python3 tools/supervisor.py --build-proposal-promotion-index
```

Builds `runs/proposal_promotion_index.json` from `docs/proposals/`,
`tools/proposal_promotion_registry.json`, and the semantic boundary in
`tools/proposal_promotion_policy.json`.

Use it when you want to inspect, for each promoted proposal:

- bounded vs missing promotion traceability
- source draft references and whether they still resolve
- motivating concern, normalized title, and bounded scope coverage
- next promotion-provenance gap such as `attach_promotion_trace`,
  `record_source_refs`, or `record_bounded_scope`

### Proposal spec trace index

```bash
python3 tools/supervisor.py --build-proposal-spec-trace-index
make proposal-spec-trace
```

Builds `runs/proposal_spec_trace_index.json` from proposal markdown references,
proposal-promotion traceability, and proposal-lane target regions. Textual
mentions stay `inferred`; only promotion traces and proposal-lane targets become
bounded or declared relations for viewer overlays.

### Gate resolution

```bash
python3 tools/supervisor.py --resolve-gate SG-SPEC-0003 --decision approve
```

Use this after human review of a gated spec.

### Runtime residue inspection

```bash
python3 tools/supervisor.py --list-stale-runtime
python3 tools/supervisor.py --clean-stale-runtime
```

Use these when gates or worktrees look stale after interrupted runs. Inspect
first; clean second.

## 5. Important Targeted-Run Controls

### Operator note

```bash
python3 tools/supervisor.py \
  --target-spec SG-SPEC-0027 \
  --operator-note "Materialize one new child spec for the remaining bounded concern."
```

`--operator-note` is ephemeral guidance for one run. It does not edit canonical specs.

Use it to:

- constrain scope
- request a narrower interpretation
- direct explicit child materialization
- bias a run toward a specific already-known concern

### Mutation budget

```bash
python3 tools/supervisor.py \
  --target-spec SG-SPEC-0027 \
  --mutation-budget policy_text,schema_required_addition
```

Use `--mutation-budget` when an explicit targeted run should stay inside a
declared change surface. This is especially useful when you want a bounded pass
to tighten a node without allowing broad opportunistic edits.

### Run authority

```bash
python3 tools/supervisor.py \
  --target-spec SG-SPEC-0027 \
  --operator-note "Materialize one new child spec for the remaining bounded concern." \
  --run-authority materialize_one_child
```

Authority matters. If the run asks for a new child but the authority does not grant it, child materialization is rejected.
When `materialize_one_child` is granted, the supervisor reserves exactly one
child spec id and adds that reserved child path to the run-local allowed paths.
The parent spec's canonical `allowed_paths` remains node-local after sync-back;
the child gets its own `allowed_paths` in the materialized child file.

Current high-value authority:

- `materialize_one_child`

### Execution profile

```bash
python3 tools/supervisor.py --target-spec SG-SPEC-0003 --execution-profile standard
python3 tools/supervisor.py --target-spec SG-SPEC-0027 --execution-profile materialize
```

Current profiles:

- `fast`
- `standard`
- `materialize`

Use `materialize` when the run is expected to create a new child or do a heavier structural step.

### Child model and timeout

Default child runs use `gpt-5.5` with `medium` reasoning through the shared
execution profile policy. Use explicit overrides only for bounded comparison
or exceptional runtime diagnosis.

```bash
python3 tools/supervisor.py \
  --target-spec SG-SPEC-0003 \
  --child-timeout 1200
```

Useful when:

- a branch is structurally heavy
- a root or near-root node needs longer bounded reasoning
- you want to compare model speed/quality tradeoffs

## 6. Derived Artifacts And Diagnostic Surfaces

The supervisor writes several different surfaces. They are not all equally
authoritative.

### Fast operator surfaces

- `runs/latest-summary.md`
  - quickest human snapshot of the last run
- `runs/<RUN_ID>.json`
  - full authoritative run payload for that run
- `runs/decision_inspector/<RUN_ID>.json`
  - standalone decision explanation artifact for that run
- `runs/graph_health_overlay.json`
  - current canonical graph-health overlay grouped by signal, recommended
    action, and named pressure filters
- `runs/graph_health_trends.json`
  - longitudinal graph-health report grouped by recurring signals and
    current-vs-historical recurrence

### Queue and proposal surfaces

- `runs/proposal_queue.json`
  - derived queue of proposal-oriented next moves
- `runs/refactor_queue.json`
  - derived queue of refactor-oriented next moves
- `runs/proposals/*.json`
  - structured proposal artifacts emitted by split-proposal mode
- `proposal_lane/nodes/*.json`
  - repository-tracked proposal-lane nodes with stable provisional handles,
    authority state, target region, lineage, and runtime bridge metadata
- `runs/proposal_lane_overlay.json`
  - viewer/report overlay built from tracked proposal nodes and their
    canonical/runtime edges
- `runs/spec_id_reservations.json`
  - temporary in-flight reservations for explicit child-materialization IDs

These runtime artifacts are now written with atomic replace plus a short-lived
sidecar lock. If a queue file is malformed, ordinary supervisor runs stop
instead of silently treating it as an empty queue.
Run logs and isolated worktree identities also carry a nonce so concurrent
runs do not collide on timestamp-only names.

Explicit child-materialization runs now reserve one child `SG-SPEC-XXXX` ID
for the active run and require the produced child file to use that reserved
path.

### Trace and inspection surfaces

- `runs/spec_trace_index.json`
  - first graph-bound spec trace artifact with `code_refs`, `test_refs`,
    `commit_refs`, `pr_refs`, `verification_basis`, `acceptance_coverage`,
    conservative `implementation_state`, and `freshness`
- `runs/spec_trace_projection.json`
  - derived viewer/backlog projection grouped by `implementation_state`,
    `freshness`, `acceptance_coverage`, and reflective next-gap categories
- `tools/spec_trace_registry.json`
  - explicit strong trace contracts for deriving `implementation_state` and
    freshness-aware drift detection
- `runs/proposal_runtime_index.json`
  - derived proposal runtime index with posture, realization, validation, and
    re-observation status
- `runs/external_consumer_index.json`
  - derived bridge surface for declared external consumers, including
    stable-vs-draft references, checkout availability, contract readiness, and
    metric bindings
- `runs/external_consumer_overlay.json`
  - viewer/backlog surface for sibling-consumer bridges, including bridge
    state, metric pressure, and explicit next-gap remediation pressure
- `runs/external_consumer_handoff_packets.json`
  - reviewable downstream handoff packets for sibling consumers, including
    handoff readiness, packet validation, and next-gap backlog
- `runs/specpm_feedback_index.json`
  - derived downstream feedback surface for `SpecPM`, including observed review
    activity, local adoption visibility, and source-spec linkage without
    automatic canonical acceptance
- `runs/specpm_public_registry_index.json`
  - read-only SpecPM static registry observation surface, including
    registry-visible package versions, capability search visibility, and drift
    against current materialization expectations
- `runs/metrics_delivery_workflow.json`
  - reviewable downstream delivery workflow for Metrics/SIB handoff packets,
    including checkout state, metric binding, branch/commit/PR scaffold, and
    next-gap backlog
- `runs/metrics_feedback_index.json`
  - derived downstream feedback surface for Metrics/SIB, including observed
    review activity, local adoption visibility, metric binding, and next-gap
    backlog without automatic canonical acceptance
- `runs/metrics_source_promotion_index.json`
  - reviewable promotion surface for draft sibling metric sources such as
    `Metrics/SIB_FULL`, including authority guardrails and promotion backlog
    without automatic threshold authority
- `runs/metric_pack_registry_drift.json`
  - read-only comparison between SpecGraph's metric-pack registry and the
    sibling Metrics `METRIC_PACKS.md` source contract, without auto-syncing
    either repository
- `runs/metric_pack_adapter_index.json`
  - read-only computability surface for metric-pack inputs, grouped by adapter
    status, input computability, missing inputs, and next-gap backlog before any
    metric-pack execution
- `runs/metric_pack_runs.json`
  - read-only metric-pack run snapshot, grouped by run status and metric values,
    with non-computable gaps and deferred finding/proposal projection
- `runs/metric_pricing_provenance.json`
  - read-only pricing provenance surface for economic observability, including
    model/tool identity, pricing version, unit convention, missing-price
    behavior, and spend/proxy gaps
- `runs/supervisor_performance_index.json`
  - derived measurement surface for runtime cleanliness, run yield, graph
    impact, and same-spec repeat hotspots over time
- `runs/bootstrap_smoke_benchmark.json`
  - advisory smoke benchmark surface for minimal-seed structural yield, based
    on performance-index run signals rather than exact generated text
- `runs/graph_dashboard.json`
  - aggregated dashboard surface with headline cards and numeric section
    summaries for graph, health, proposals, implementation, evidence, external
    consumers, external handoffs, metrics, Implementation Work items, and
    process feedback
- `runs/graph_backlog_projection.json`
  - normalized derived backlog surface with concrete next-gap rows grouped by
    domain, priority, source artifact, and named viewer filters, including
    branch rewrite preview candidates, Implementation Work, and review-feedback
    gaps
- `runs/graph_next_moves.json`
  - advisory derived surface with `current_scene`, one recommended bounded move,
    alternatives, blocked moves, and compact source facts for viewer guidance
- `runs/spec_activity_feed.json`
  - derived activity feed that maps git-observed spec, trace, evidence,
    proposal, implementation, and review-feedback changes back to spec ids
- `tools/proposal_lane_policy.json`
  - declarative proposal-lane contract for repository presence, authority-state
    mapping, and overlay/query semantics
- `tools/supervisor_policy.json`
  - declarative policy layer for thresholds, priorities, queue defaults,
    mutation classes, and execution profiles
- `graph_health` payload in run logs
  - reflective signals, subtree-shape pressure, and recommended actions
- `decision_inspector` payload in run logs
  - compact explanation of how the supervisor classified one run

Use `runs/<RUN_ID>.json` when you need to answer:

- why this spec was selected
- why the gate state ended where it did
- which validators failed
- what queue items were emitted, cleared, or updated
- whether graph-health signals came from accepted canonical state or only from a
  candidate view

## 7. How To Read Outcomes

The supervisor writes authoritative run data to:

- `runs/latest-summary.md`
- `runs/<RUN_ID>.json`

Important fields:

- `outcome`
- `completion_status`
- `gate_state`
- `required_human_action`
- `validation_findings`
- `validation_summary`
- `validation_errors`
- `safe_repair_contract`
- `evaluator_loop_control`
- `executor_environment`
- `refinement_acceptance`
- `reconciliation`
- `graph_health`
- `graph_health_truth_basis`
- `decision_inspector`

Machine-protocol invariant:

- a successful child executor run must emit both `RUN_OUTCOME:` and `BLOCKER:`
  markers on stdout
- missing markers are treated as executor protocol failure, not as an implicit
  `done`

### `done`

The run produced an accepted refinement path. Depending on approval mode, the spec may end in:

- `gate_state: review_pending`
- or directly `gate_state: none` after auto-approve

### `split_required`

This is not automatically a failure.

Interpretation:

- the run found a real decomposition boundary
- the current node still needs structural splitting or an intermediate child
- productive `split_required` may still contain valid canonical refinement

Important nuance:

- productive `split_required` may sync valid content changes
- but source lifecycle fields must remain canonical and coherent
- it must not leave impossible mixed states such as `reviewed + split_required`

### `retry`

Use when the run did not yield a usable refinement and should be attempted again after adjustment.

### `blocked`

There is a real blocker. Read `required_human_action`.

### `escalate`

The supervisor has reached a case that should move to a higher-authority review path.

## 8. Reading `decision_inspector`

`decision_inspector` is the compact operator-facing explanation layer in each
run log, and the same content is also written to
`runs/decision_inspector/<RUN_ID>.json`.

Validation is now dual-surfaced:

- `validation_findings`
  typed findings with `family`, `error_class`, `code`, `severity`, and
  `message`
- `validation_errors`
  backward-compatible rendered strings derived from those findings

Current typed findings cover runtime paths such as YAML/load failures,
relation/reconciliation failures, acceptance or atomicity failures,
authority/scope violations, runtime artifact integrity failures, executor
machine-protocol failures, and executor-environment failures.

Recoverable repairs are explicit too:

- `safe_repair_contract`
  bounded repair metadata attached to the run payload
- `runs/safe_repairs/<RUN_ID>.json`
  standalone repair artifact when a repair was actually applied

The current built-in safe repair kind is intentionally narrow:

- `yaml_candidate_repair`
- scope: `worktree_candidate_only`
- canonical write: always `false`
- every repair still requires normal post-repair validation before any later sync

Reflective cycles are explicit too:

- `evaluator_loop_control`
  compact control record attached to the run payload
- `runs/evaluator_control/<RUN_ID>.json`
  standalone artifact for the same cycle record

Each control artifact records:

- `chosen_intervention`
- `applied_rules`
- `improvement_basis`
- `stop_conditions`
- `escalation_reasons`

It has four slices:

- `selection`
  - which mode selected the spec, and with what rule inputs
- `gate`
  - final `outcome`, `gate_state`, `required_human_action`, `blocker`, and
    failing validators
- `diff_classification`
  - changed files, changed spec files, validation pressure, refinement
    acceptance, and the truth basis used for graph health
- `queue_effects`
  - signals, recommended actions, and queue transitions for proposal/refactor
    items

Each slice now includes `applied_rules`:

- `supervisor_policy` rules point back into `tools/supervisor_policy.json`
- `runtime_guard` rules explain procedural decisions such as validator failure,
  mutation-budget overflow, or blocker propagation

At top level, `policy_reference` records the policy artifact path and SHA-256
used for the run.

When queue state changed, look at:

- `emitted_ids`
- `cleared_ids`
- `updated_ids`

`updated_ids` matters because a queue item can stay present while its payload or
status changes.

## 9. Completion Status

The most important distinction is:

- `completion_status: progressed`
- `completion_status: failed`

`progressed` means the run moved the graph forward, even if it still ended in `split_required`.

Typical examples:

- a useful bounded refinement plus `split_required`
- a child spec materialized but the parent still needs another structural pass

`failed` means the run did not produce an authoritative step forward.

Typical examples:

- invalid worktree YAML with no accepted canonical writeback
- executor environment failure
- validation failure that blocks sync

## 10. Runtime Failure Versus Spec Failure

This distinction is critical.

Treat it as a runtime problem first when you see:

- broken worktree YAML
- transport or startup issues in child executor
- isolated worktree drift only
- timeout residue with no accepted canonical content change
- profile mismatch or child runtime drift

Treat it as a real spec-structure problem when you see:

- `split_required` with clean validation
- repeated no-op tightening on the same node
- reconciliation complaints about missing refinement chain
- persistent atomicity pressure after legitimate narrowing

In practice:

- invalid YAML is usually a runtime repair problem
- repeated clean `split_required` is usually a graph decomposition problem

## 11. Current Best-Practice Workflow

For one branch of the graph:

1. pick one target spec
2. use `--target-spec` instead of broad loop mode
3. if the run returns clean `split_required`, do not keep polishing forever
4. decide whether the next step is:
   - another bounded ordinary refinement
   - explicit child materialization
   - split proposal emission
   - parent/child refinement-chain reconciliation
5. validate canonical YAML
6. commit stable progress in small batches

Recommended validation after meaningful spec edits:

```bash
python3 tools/spec_yaml_format.py specs/nodes/SG-SPEC-XXXX.yaml
python3 tools/spec_yaml_lint.py specs/nodes/SG-SPEC-XXXX.yaml
```

For runtime changes:

```bash
pytest -q tests/test_supervisor.py
ruff check tools/supervisor.py tests/test_supervisor.py
python3 -m compileall tools/supervisor.py
```

## 12. Practical Heuristics

### When to continue ordinary refinement

Keep ordinary refinement when:

- the node still yields new bounded policy text
- validation is clean
- no repeated no-op behavior appears
- no new child is clearly implied yet

### When to switch to child materialization

Switch when:

- the same node repeats clean `split_required`
- the remaining concern is clearly nameable
- the parent has become an integration or gateway node
- one new intermediate spec would reduce direct child pressure or clarify refinement chain

### When to stop and declare plateau

You are likely at plateau when:

- repeated runs only restate the same boundary in different words
- no new child is created
- validation stays clean
- `split_required` persists with small policy-text diffs only

That usually means the next move is structural, not textual.

## 13. Current Known Patterns

These patterns have appeared repeatedly during bootstrap:

### Productive `split_required`

Useful and expected. Do not classify it as failure when:

- validation is clean
- canonical diff is meaningful
- the result narrows the next structural step

### Runtime YAML repair

The supervisor now repairs several recoverable malformed candidate-YAML cases before validation, but this should still be treated as runtime hardening, not as evidence that the target spec is conceptually weak.

### Refinement-chain reconciliation after subtree split

When a new intermediate node is added, the next blocker is often not the new child itself, but stale `refines` edges on its descendants.

Typical example:

- old chain: `A -> C`
- new intended chain: `A -> B -> C`
- required next step: change `C.refines` from `A` to `B`

### Selector plateau

Loop mode can waste time when it keeps selecting:

- already mature linked nodes
- repeated no-op refinements
- nodes that really need explicit split/materialization rather than more ordinary tightening

## 14. Recommended Document Map

Use the documents in this order:

1. [CONSTITUTION.md](../CONSTITUTION.md)
2. [AGENTS.md](../AGENTS.md)
3. this manual
4. [tools/README.md](../tools/README.md)
5. relevant spec nodes and current run artifacts

This manual should stay practical and process-oriented.

It should not replace:

- spec governance in canonical spec nodes
- constitutional rules in `CONSTITUTION.md`
- repository editing rules in `AGENTS.md`
