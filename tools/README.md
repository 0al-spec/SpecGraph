# Tools

For a practical operator/contributor guide to the supervisor, see
[docs/supervisor_manual.md](../docs/supervisor_manual.md).
For a visualizer-facing compact report and overlay guide, see
[docs/metrics_visualization_guide.md](../docs/metrics_visualization_guide.md).
For the dedicated `SpecPM` preview/materialization/import viewer contract, see
[docs/specpm_viewer_contract.md](../docs/specpm_viewer_contract.md).
For the ContextBuilder exploration/assumption-mode viewer contract, see
[docs/exploration_preview_viewer_contract.md](../docs/exploration_preview_viewer_contract.md).
For the ContextBuilder graph backlog drill-down viewer contract, see
[docs/graph_backlog_projection_viewer_contract.md](../docs/graph_backlog_projection_viewer_contract.md).
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
  remain visible but non-operational. The same packet plane also carries
  SpecSpace-oriented artifact contract handoffs when graph-operator consumer
  contracts are declared.
- `--build-external-consumer-evidence`: build
  `runs/external_consumer_evidence_index.json` from curated downstream
  implementation evidence and current handoff packets so consumer adoption can
  be accepted, blocked, or marked contract-mismatched without mutating the
  downstream repository.
- `tools/ontology_imports.py --write`: build the proposal 0060 ontology import
  derived surfaces from `tools/ontology_import_policy.json` and the
  project-local SpecGraph Core ontology package under
  `ontology/packages/specgraph-core/`: `runs/ontology_package_index.json`,
  `runs/ontology_import_gap_index.json`,
  `runs/ontology_compatibility_diff_preview.json`,
  `runs/ontology_governance_evidence_index.json`,
  `runs/ontology_binding_preview.json`, and
  `runs/ontology_prompt_invocation_index.json`. It also validates the
  `ontologyc_adapter_report` fixture and emits
  `runs/ontologyc_adapter_report_smoke.json`, preserving source/version/digest
  checks for `ontologyc validate-specgraph` output. It also projects the
  `ontologyc diff` compatibility report as a read-only preview of ontology
  additions, removals, breaking changes, and required SpecGraph review actions
  without updating lockfiles or canonical specs. The same command consumes
  `tools/ontology_semantic_control_policy.json` and emits
  `runs/ontology_semantic_context_pack.json`, packaging accepted terms,
  accepted relations, aliases, deprecated terms, relation conflicts, unresolved
  gaps, package metadata, and governance evidence for supervisor/SpecSpace
  consumers. It also upgrades `runs/ontology_prompt_invocation_index.json` into
  the 0118 context-only prompt-agent ontology boundary, carrying package refs,
  accepted terms, aliases, deprecated terms, relation conflicts, unresolved
  gaps, prompt input/output refs, evidence refs, and failure modes without
  running prompt agents or persisting raw prompts/responses. It also emits
  `runs/ontology_semantic_lint_input.json`, extracting
  declared semantic terms from tracked proposal/supervisor output sources with
  source digests and spans, then `runs/ontology_semantic_lint_report.json`,
  deriving review findings, blocking findings, candidate delta terms, and
  recommended actions from that context pack and lint input, then
  `runs/ontology_delta_candidate_review_packet.json` for explicit ontology-owner
  review actions and `runs/ontology_semantic_review_surface.json` as the
  SpecSpace/supervisor-facing review surface,
  `runs/ontology_supervisor_semantic_gate.json` as typed supervisor gate
  evidence derived from that surface,
  `runs/ontology_delta_draft_intake.json` as a review-only Ontology owner
  draft-intake handoff for delta candidates,
  `runs/ontology_closed_loop_evidence.json` as the SpecGraph-facing evidence
  loop surface for those intake requests,
  `runs/ontology_review_dashboard.json` as the richer read-only
  SpecGraph/SpecSpace dashboard projection over semantic review, gate, intake,
  and closed-loop evidence,
  `runs/ontology_owner_decision_report.json` as the typed read-only
  accepted/rejected Ontology owner decision report for later import previews,
  `runs/ontology_decision_import_preview.json` as the read-only preview that
  matches owner decisions back to closed-loop evidence and recommends operator
  review without applying imports,
  plus
  `runs/ontology_semantic_lint_smoke.json`,
  classifying accepted, alias, unknown, deprecated, and relation-conflict terms
  against the imported ontology fixture. These surfaces resolve known imported
  refs and preserve unresolved refs as reviewable ontology gaps without
  mutating canonical `specs/nodes/*.yaml`.
- `tools/ontology_package_authoring.py`: review-only project-local ontology
  package authoring helper introduced by proposal 0133. Use
  `make ontology-package-validate`, `make ontology-package-preview`, and
  `make ontology-package-gaps` to emit typed `runs/` artifacts for package
  validation, ref/diff previews, and gap review. These commands do not mutate
  canonical specs, update ontology lockfiles, accept terms, or write to
  SpecSpace.
- `tools/spec_ontology_binding_index.py`: report-only legacy spec binding
  index introduced by proposal 0134. Use `make spec-ontology-bindings` to emit
  `runs/spec_ontology_binding_index.json`, mapping obvious existing spec
  structure to current ontology refs and surfacing unknown legacy terminology as
  ontology gaps without rewriting `specs/nodes/*.yaml`.
- `tools/spec_ontology_validation_report.py`: typed report-only validation
  surface introduced by proposal 0135. Use `make spec-ontology-validation` to
  emit `runs/spec_ontology_validation_report.json`, checking required structural
  bindings, relation existence, relation domain/range compatibility, and legacy
  terminology gaps while keeping existing specs in report-only mode.
- `tools/ontology_term_binding_policy.json`: review-first policy for treating
  accepted Ontology entities as canonical type symbols, requiring unknown
  generated terms to become `ontology_gap` records, and keeping practical
  observations, topology edges, and proposal references non-authoritative.
- `tools/ontology_term_binding_gate.py`: local review-mode gate for generated
  artifacts. It reads `tools/ontology_term_binding_policy.json`, emits
  `runs/ontology_term_binding_gate_report.json`, and reports whether the
  artifact would fail a future hard gate without mutating canonical specs.
- `tools/ontology_gap_review_workflow.py`: read-only grouped review workflow for
  ontology gaps introduced by proposal 0138. Use `make ontology-gap-review` to
  emit `runs/ontology_gap_review_workflow.json` from package gap preview and
  spec ontology validation findings. Pass
  `ONTOLOGY_GAP_REVIEW_GENERATED_ARTIFACT=<json>` to attach affected generated
  artifacts that contain `ontology_gaps`. The workflow recommends owner review
  actions but does not import decisions, write ontology packages, or mutate
  specs.
- `tools/legacy_spec_ontology_backfill_plan.py`: review-first legacy spec
  backfill planner introduced by proposal 0140. Use `make
  legacy-spec-ontology-backfill-plan` to emit
  `runs/legacy_spec_ontology_backfill_plan.json`, classifying clean specs,
  warning-only specs, new-term/alias decision needs, relation review needs, and
  small PR batch candidates without mutating legacy specs or ontology packages.
- `tools/ontology_owner_decision_import_v2.py`: read-only owner-decision import
  v2 review surface introduced by proposal 0139. Use `make
  ontology-owner-decision-import-v2` to emit
  `runs/ontology_owner_decision_import_v2.json`, linking accepted/rejected owner
  decisions to gap-review groups, closed-loop evidence, compliance findings,
  write-gate findings, and before/after semantic status without importing
  decisions or mutating ontology packages/specs.
- `tools/specauthor_generated_artifact_contract.py`: producer-side contract
  validator for `generated_spec_artifact` drafts introduced by proposal 0137.
  Use `make specauthor-generated-artifact-contract
  SPECAUTHOR_GENERATED_ARTIFACT_CONTRACT_ARTIFACT=<json>` to require
  SpecAuthorAgent producer metadata, active ontology/domain/context, review-only
  target artifact metadata, draft payload, and downstream write-gate
  materialization intent before the artifact reaches the ontology write gate.
  The report is written to
  `runs/specauthor_generated_artifact_contract_report.json`.
- `tools/specauthor_ontology_write_gate.py`: deterministic write gate for
  SpecAuthor-generated graph artifacts introduced by proposal 0136. Use
  `make specauthor-ontology-write-gate
  SPECAUTHOR_ONTOLOGY_WRITE_GATE_ARTIFACT=<json>` to require active
  ontology/domain/context, compose with the term binding gate, require F/G/R on
  strong claims, and emit `runs/specauthor_ontology_write_gate_report.json`
  without mutating canonical specs or Ontology packages.
- `tools/specauthor_invocation_artifact_contract.py`: typed invocation boundary
  validator introduced by proposal 0145. Use
  `make specauthor-invocation-artifact-contract
  SPECAUTHOR_INVOCATION_ARTIFACT_CONTRACT_ARTIFACT=<json>` to link operator
  intent, active ontology/domain/context/layer/applicability frame,
  generated artifact contract report, write-gate report, and operator decision
  state without executing prompt agents or mutating canonical specs.
  The report is written to
  `runs/specauthor_invocation_artifact_contract_report.json`.
- `tools/specauthor_authoring_flow.py`: deterministic prompt-side authoring
  wrapper introduced by proposal 0146. Use `make specauthor-authoring-flow` to
  assemble an already-produced `generated_spec_artifact`, active
  ontology/domain/context/layer/applicability data, the generated artifact
  contract report, and the ontology write-gate report into
  `runs/specauthor_invocation_artifact.json` and
  `runs/specauthor_invocation_artifact_contract_report.json`. The wrapper does
  not execute prompt agents, publish raw prompts, mutate canonical specs, or
  write Ontology packages.
- `tools/user_idea_intake_session.py`: deterministic generic user-idea intake
  session builder introduced by proposal 0162. Use
  `make user-idea-intake-session USER_IDEA_INTAKE_SESSION_INPUT=<json>` to turn
  raw idea/session data into `runs/user_idea_intake_session.json` and, when
  enough ontology/domain/context/layer/applicability and event-storming context
  exists, `runs/user_idea_intake_source.json`. Use
  `make generic-idea-intake-session` to feed the ready source into the existing
  event-storming intake chain. Missing context becomes clarification questions;
  the builder does not execute prompt agents, infer missing domain models,
  mutate canonical specs, write Ontology packages, create branches, or publish
  read models.
- `tools/user_idea_intake_interview.py`: operator-facing real idea intake
  wrapper introduced by proposal 0184. Use
  `SPECG_USER_IDEA_INTAKE_INTERVIEW_IDEA_TEXT=<text> make real-idea-intake` to
  pass arbitrary raw idea text through the process environment, write a local-only
  `runs/local_operator_user_idea_raw_input.json`, run the existing
  intake-session gate, and emit
  `runs/user_idea_intake_interview_report.json`. The wrapper can also consume a
  matching clarification request/answer-set pair and apply accepted intake
  answers to the raw input before validation. It does not execute prompt agents,
  infer missing product semantics, mutate candidate/canonical specs, write
  Ontology packages, accept ontology terms, create Git branches, or publish raw
  idea text.
- `tools/intake_session_candidate_source.py`: review-only bridge introduced by
  proposal 0185. Use `make intake-session-candidate-source` after
  `real-idea-intake` or `user-idea-intake-session` to validate a ready
  `runs/user_idea_intake_session.json` and materialize the standard
  `runs/user_idea_intake_source.json` from the session's embedded public-safe
  `candidate_source_input`. The bridge writes
  `runs/intake_session_candidate_source_report.json`, leaves any pre-existing
  source output untouched when the session is not ready, rewrites source provenance to the intake
  session rather than the local raw-input artifact, and does not execute prompt
  agents, mutate candidate/canonical specs, write Ontology packages, accept
  ontology terms, create Git branches, or publish raw idea text.
- `tools/idea_intake_clarification_rerun.py`: review-only real-intake
  clarification rerun wrapper introduced by proposal 0186. Use
  `make real-idea-intake-clarification-requests`, then validate answers with
  `make real-idea-intake-clarification-answers`, then run
  `make real-idea-intake-clarification-rerun` to produce
  `runs/idea_intake_answer_rerun_input.json`,
  `runs/clarified_user_idea_intake_session.json`, and
  `runs/idea_intake_clarification_rerun_report.json`. Use
  `make real-idea-intake-ready-candidate-source` to prefer the clarified session
  when present and materialize the standard `runs/user_idea_intake_source.json`.
  The loop does not execute prompt agents, infer missing semantics with an LLM,
  mutate specs, write Ontology packages, create Git branches, or publish raw idea
  text.
- Proposal 0187 adds `make real-idea-intake-active-candidate`, which converts
  the ready real-intake `user_idea_intake_source` into an
  `idea_event_storming_seed` before running `product-workspace-active-candidate`.
  Passing a `user_idea_intake_source` directly to
  `product-workspace-active-candidate` now fails with an actionable message.
- Proposal 0188 hardens `make real-idea-intake-clarification-requests`: an
  existing `USER_IDEA_INTAKE_SESSION_OUTPUT` is preserved and used as the source
  for clarification requests. The target still creates a session when missing;
  use `REAL_IDEA_INTAKE_REFRESH=1` to intentionally rebuild it.
- Proposal 0189 appends the candidate-local domain ref derived from
  `candidate_id` while preserving broader product domain refs, so real ideas can
  carry both `domain.<candidate>` and contextual domain refs into the active
  candidate pipeline. Auto-appended domain refs carry derivation metadata and
  are not marked owner-confirmed.
- Proposal 0190 adds `make real-idea-smoke
  REAL_IDEA_SMOKE_RUN_DIR=runs/<id>`, which routes the real-intake
  active-candidate chain into an isolated run directory and writes
  `real_idea_smoke_summary.json`. The wrapper normalizes repository-local
  absolute run dirs, rejects external absolute paths, clears ambient
  active-candidate config, writes the summary even for blocked intake runs, and
  whitelists upstream summary fields before publishing smoke telemetry.
- Proposal 0191 adds conservative `decomposes_to` topology edges from
  `candidate-spec.product-boundary` to each ontology-bound candidate node. This
  prevents real idea candidates from looking topology-empty in pre-SIB reports
  without inferring domain causality or event ordering. This is a temporary flat
  anti-orphan topology layer, not ontology-validated event-storming topology.
  Clean pre-SIB pass-through now produces a ready no-op repair loop instead of a
  false `repair_loop_not_ready` blocker.
- Proposal 0200 adds additive event-storming workflow topology evidence on top
  of the 0191 fallback. The ontology-bound candidate graph seed now emits
  review-only relations such as `actor_triggers_command`,
  `command_emits_event`, `event_informs_policy`,
  `constraint_applies_to_command`, and `policy_applies_to_command` while keeping
  candidate-node endpoints compatible with existing graph validation and
  Pre-SIB metrics. The seed generation report also includes non-blocking
  `topology_quality` warnings for incomplete workflow topology.
- Proposal 0192 makes real-idea smoke runs iteration-safe. By default,
  `make real-idea-smoke` clears only wrapper-owned derived outputs inside
  `REAL_IDEA_SMOKE_RUN_DIR` before rebuilding, so repeated runs do not silently
  reuse stale intake sessions. Set `REAL_IDEA_SMOKE_REFRESH=0` to preserve
  existing managed outputs intentionally. Operator-authored answer input files
  are preserved, but generated answer/rerun/repair/maturity outputs and the
  default `absent-post-approval` directory are cleared. Use
  `make real-idea-smoke-idea-maturity` to build Idea Maturity from the same
  run directory; `REAL_IDEA_SMOKE_RUN_DIR=runs` is rejected because it is the
  shared artifact directory, not a smoke run directory. Optional post-approval
  Platform/Git artifacts are routed to `REAL_IDEA_SMOKE_MATURITY_ABSENT_DIR` by
  default so unrelated canonical `runs/*.json` reports cannot leak into custom
  smoke metrics. The absent-dir must be a child of the smoke run directory and
  is cleared again immediately before maturity generation, while SpecSpace
  repair-stage artifacts such as draft import previews and rerun requests are
  read from the smoke run directory.
- Proposal 0193 adds session-aware real-idea smoke continuation. After
  `make real-idea-smoke` stops at `needs_clarification`, run
  `make real-idea-smoke-continue
  REAL_IDEA_SMOKE_CLARIFICATION_ANSWERS_INPUT=<json>` to preserve the existing
  intake session, apply accepted intake clarification answers, clear downstream
  generated outputs, and continue to active-candidate generation without
  manually setting `REAL_IDEA_SMOKE_REFRESH=0`. When answers are missing, the
  wrapper writes `real_idea_smoke_session_state_report.json` with blockers and
  the next safe action.
- Proposal 0194 adds first-class real-idea answer authoring. Use
  `make real-idea-smoke-answer-template` to build
  `real_idea_answer_template.json` from the current smoke run directory's
  clarification requests, then fill the template and run
  `make real-idea-smoke-validate-answers
  REAL_IDEA_ANSWER_AUTHORING_ANSWERS=<json>`. When ready, run
  `make real-idea-smoke-materialize-answers
  REAL_IDEA_ANSWER_AUTHORING_ANSWERS=<json>` to write the compatible
  intake or repair answer artifacts. The helper validates required typed
  fields, `may_*` authority expansion, raw trace fields, and private/local text
  markers before any downstream rerun artifact is written.
- Proposal 0195 adds SpecSpace real-idea answer continuation handoff. Use
  `make specspace-real-idea-answer-import-preview` to validate
  SpecSpace-owned intake clarification answer state against the current answer
  template, clarification requests, and intake session. When ready, use
  `make real-idea-intake-materialize-specspace-answers` to materialize safe
  answer artifacts, or `make real-idea-intake-continue-from-specspace-answers`
  to continue through the existing active-candidate pipeline. The handoff keeps
  SpecSpace as the owner of mutable operator intent only; it does not grant
  SpecSpace execution, ontology, spec mutation, approval, Git, or publication
  authority.
- Proposal 0202 adds SpecSpace raw idea entry import. Use
  `make real-idea-intake-from-entry-request
  SPECSPACE_REAL_IDEA_ENTRY_REQUESTS=<json>` to validate a submitted
  SpecSpace-owned raw idea entry request, write a sanitized
  `specspace_real_idea_entry_request_import_preview.json`, materialize the
  existing real-idea intake artifacts under `REAL_IDEA_SMOKE_RUN_DIR`, and
  prepare clarification requests plus `real_idea_answer_template.json`. Raw
  idea text remains local-only and appears only in the local operator raw input
  artifact, not in preview or report artifacts.
- Proposal 0204 adds a product demo depth baseline for UI-started real-idea
  smoke runs. Use `make real-idea-smoke-depth-baseline
  REAL_IDEA_SMOKE_RUN_DIR=runs/<id>` after a real-idea candidate run to build
  Idea Maturity, `candidate_overview.json`, and
  `product_demo_depth_report.json` for the same run directory. The strict report
  fails shallow demos that lack actors, commands, domain events, policies,
  constraints, workflow topology, requirements, acceptance criteria, candidate
  overview, or non-missing Idea Maturity. The target is report-only and does
  not execute prompt agents, mutate specs, write ontology packages, approve
  candidates, create Git artifacts, or publish read models.
- Proposal 0205 adds reusable structural depth observations to the Metrics-owned
  Idea Maturity report. `groups.candidate_structure_depth` records actor,
  command, domain event, policy, constraint, topology edge, workflow edge,
  requirement, and acceptance-criteria counts from existing intake and candidate
  graph artifacts. These counts explain candidate depth without replacing the
  stricter product demo depth report or becoming a promotion gate.
- Proposal 0206 adds producer-side readiness explainers over those raw structural
  observations. Shallow counts can surface candidate-structure next steps under
  the existing `pre_sib_review` block while the Metrics counts remain objective
  telemetry rather than a score, approval gate, promotion gate, Git authority, or
  Ontology authority.
- Proposal 0207 adds depth-driven clarification requests from the same raw
  structural observations. Pass `--idea-maturity` to
  `tools/idea_to_spec_clarification_requests.py` or set
  `IDEA_TO_SPEC_CLARIFICATION_IDEA_MATURITY=<report>` to emit review-required
  `event_storming_hints.*` questions. Accepted `entries[]` answers are converted
  into review-only event-storming rerun hints by
  `tools/idea_to_spec_answer_rerun_input.py`.
- Proposal 0208 adds safe workflow-topology repair for flat candidates. When
  `workflow_edge_count = 0`, clarification requests can target
  `event_storming_hints.workflow_relations` with typed `relations[]` answers.
  Rerun preview validates source/target refs and relation kinds before emitting
  review-only workflow topology edges; materialization copies only
  `review_only` / non-dependency edges into candidate graph preview.
- Proposal 0209 adds `structural_depth_delta` to rerun preview and
  materialization so downstream surfaces can show depth repair impact:
  before/after counts, added event-storming refs, added workflow relation
  evidence, remaining shallow dimensions, and an effect status. This is
  report-only visibility, not a Metrics schema change, score, gate, or authority
  expansion.
- Proposal 0210 makes real-intake clarification templates fallback-free.
  Clarification requests and answer templates carry workspace identity and a
  stable source digest, publish `answers_required`,
  `clarification_not_required`, or `clarification_blocked`, and treat
  missing policy context as an ordinary typed intake question. Strict blocked
  generation preserves an existing ready template.
- `tools/user_idea_intake_source.py`: deterministic generic user-idea source
  builder introduced by proposal 0158. Use `make user-idea-intake-source
  USER_IDEA_INTAKE_SOURCE=<json>` to normalize product workspace identity,
  root intent, ontology/domain/context hints, and event-storming hints into a
  local `runs/idea_event_storming_seed.json`. Use `make generic-idea-intake` to
  immediately feed that seed into `tools/idea_event_storming_intake.py`. The
  builder keeps Team Decision Log as data, not code, and does not execute
  prompt agents, infer missing domain models, mutate canonical specs, write
  Ontology packages, create branches, or publish raw prompt/model traces.
- `tools/idea_event_storming_intake.py`: deterministic idea-to-spec intake
  builder introduced by proposal 0149. Use `make idea-event-storming-intake
  IDEA_EVENT_STORMING_INTAKE_SOURCE=<json>` to normalize structured
  event-storming seed data into `runs/idea_event_storming_intake.json` with
  actors, domain events, commands, policies, external systems, constraints,
  vocabulary questions, active ontology/domain/context frame, and
  context-completion questions. The builder digests raw intent text and does
  not execute prompt agents, infer missing concepts with an LLM, create a
  candidate graph, mutate canonical specs, write Ontology packages, or create
  Git branches.
- `tools/ontology_bound_candidate_graph_seed.py`: deterministic ontology-bound
  candidate graph seed builder introduced by proposal 0159. Use `make
  ontology-bound-candidate-graph-seed ONTOLOGY_BOUND_CANDIDATE_SEED_INTAKE=<json>`
  to read approved event-storming intake plus the normalized project-local
  SpecGraph core ontology IR, then write `runs/candidate_spec_graph_seed.json`.
  The builder requires ontology/domain/context refs, ontology layer refs, and
  model applicability refs; binds generated structural nodes to core ontology
  classes such as `Spec`, `Node`, `Requirement`, `AcceptanceCriterion`, and
  `Constraint`; and emits product-domain terms as ontology gaps instead of
  accepting them into the ontology. It does not execute prompt agents, mutate
  canonical specs, write Ontology packages, accept ontology terms, or create
  Git branches.
  `make product-workspace-active-candidate` generates this seed to
  `PRODUCT_WORKSPACE_CANDIDATE_SEED_OUTPUT` by default. To provide a prebuilt
  seed without overwriting it, set `PRODUCT_WORKSPACE_CANDIDATE_SEED_INPUT=<json>`
  or the legacy explicit `PRODUCT_WORKSPACE_CANDIDATE_SEED=<json>` input.
  The standalone `make ontology-bound-candidate-graph-seed` target builds the
  default generic event-storming intake first when it reads from
  `runs/idea_event_storming_intake.json`.
- `tools/candidate_spec_graph.py`: deterministic candidate graph contract
  builder introduced by proposal 0150. Use `make candidate-spec-graph
  CANDIDATE_SPEC_GRAPH_INTAKE=<json> CANDIDATE_SPEC_GRAPH_SEED=<json>` to
  normalize review-only candidate nodes, edges, requirements, acceptance
  criteria, claims, and gaps from an event-storming intake. The builder
  validates intake readiness, seed generation findings, node/edge refs,
  requirement-to-acceptance-criteria refs, and F/G/R calibration for strong
  candidate claims without mutating canonical specs, running pre-SIB metrics,
  writing Ontology packages, or creating Git branches.
- `tools/pre_sib_coherence_report.py`: deterministic pre-SIB/coherence report
  builder introduced by proposal 0151. Use `make pre-sib-coherence
  PRE_SIB_COHERENCE_CANDIDATE_GRAPH=<json>` to compute candidate graph counts,
  acceptance-criteria coverage, ontology coverage, orphan-node findings,
  duplicate-title warnings, unresolved-gap warnings, and unsupported
  strong-claim warnings without defining final SIB formulas, mutating candidate
  artifacts, mutating canonical specs, or creating Git branches.
- `tools/candidate_repair_loop.py`: deterministic candidate repair loop
  preview introduced by proposal 0152. Use `make candidate-repair-loop
  CANDIDATE_REPAIR_LOOP_CANDIDATE_GRAPH=<json>
  CANDIDATE_REPAIR_LOOP_PRE_SIB_REPORT=<json>` to build review-only repair
  actions, a revised candidate graph preview, and metric delta projections from
  a candidate graph plus pre-SIB/coherence report. The loop only applies safe
  deterministic changes to the preview and records ontology/context-dependent
  work as review-required actions; it does not execute prompt agents, mutate
  canonical specs, write Ontology packages, create branches, or create commits.
- `tools/idea_to_spec_clarification_requests.py`: unified read-only
  clarification request builder introduced by proposal 0163. Use
  `make idea-to-spec-clarification-requests` to aggregate available
  idea-to-spec intake, candidate graph, pre-SIB, repair-loop, and explicitly
  supplied ontology-gap review artifacts into
  `runs/idea_to_spec_clarification_requests.json`.
  Requests expose stable ids, target refs, source findings, suggested answer
  shapes, and suggested actions for future user/agent answers. The builder does
  not execute prompt agents, accept answers, mutate canonical specs, write
  Ontology packages, approve candidates, create branches, or publish read
  models.
- `tools/idea_to_spec_clarification_answers.py`: typed clarification answer
  validator introduced by proposal 0164. Use
  `make idea-to-spec-clarification-answers` to validate an
  `idea_to_spec_clarification_answer_set` against clarification request ids and
  write `runs/idea_to_spec_clarification_answers.json`. Accepted answers can
  resolve blocking requests for a future deterministic rerun, but the builder
  does not apply answers, mutate candidate artifacts, mutate canonical specs,
  write Ontology packages, approve candidates, create branches, or publish read
  models.
- `tools/idea_to_spec_answer_rerun_input.py`: accepted-answer rerun input
  overlay builder introduced by proposal 0165. Use
  `make idea-to-spec-answer-rerun-input` to convert a ready
  `idea_to_spec_clarification_answers` report into
  `runs/idea_to_spec_answer_rerun_input.json`. The overlay exposes
  active-frame, event-storming, ontology review, and candidate review hints for
  the next deterministic run without applying answers, mutating candidate
  artifacts, mutating canonical specs, writing Ontology packages, approving
  candidates, creating branches, or publishing read models. Proposal 0169 adds
  optional
  `IDEA_TO_SPEC_ANSWER_RERUN_INPUT_ONTOLOGY_DECISIONS=<json>` support so typed
  product ontology decisions can provide ontology review hints instead of raw
  ontology-gap clarification answers.
- `tools/idea_to_spec_rerun_preview.py`: accepted-answer rerun preview builder
  introduced by proposal 0166. Use `make idea-to-spec-rerun-preview` to preview
  a ready `idea_to_spec_answer_rerun_input` against the current
  `idea_event_storming_intake` and `candidate_spec_graph`. The report shows
  active-frame merge effects, event-storming additions, preview-resolved
  ontology gaps, unresolved ontology gaps, candidate review hints, and the
  proposal 0169 `candidate_quality_preview` without applying answers, mutating
  candidate artifacts, accepting ontology terms, writing Ontology packages,
  approving candidates, creating branches, or publishing read models. Proposal
  0175 adds conservative normalized ontology gap matching and emits
  `match_kind`, `confidence`, `gap_term`, and `decision_term` evidence for
  resolved gaps. The preview ranks matching decisions by match strength before
  falling back to source order for ties, and `safe_phrase_match` is directional
  with exactly one safe suffix rather than a general fuzzy/synonym rule.
  Proposal 0176 adds `candidate_gap_preview`: accepted `candidate_gap` answers
  can preview-resolve explicitly targeted product/spec gaps, while deferred
  candidate answers remain unresolved and no fuzzy candidate-gap matching is
  performed.
- `tools/idea_to_spec_rerun_materialization.py`: review-only rerun
  materialization builder introduced by proposal 0167. Use
  `make idea-to-spec-rerun-materialization` to consume a ready
  `idea_to_spec_rerun_preview` and current `candidate_spec_graph`, then nest a
  materialized candidate graph preview inside
  `runs/idea_to_spec_rerun_materialization.json`. Preview-resolved ontology
  gaps are removed from node `gaps` and preserved as
  `ontology_gap_resolutions`; proposal 0175 preserves matching provenance in
  those resolution records. Proposal 0176 also moves preview-resolved
  non-ontology candidate gaps into `candidate_gap_resolutions`, so product
  repair answers can improve the nested graph preview without rewriting
  `runs/candidate_spec_graph.json`, accepting ontology terms, writing Ontology
  packages, approving candidates, creating branches, or publishing read models.
- `tools/repaired_candidate_promotion_handoff.py`: repaired promotion handoff
  builder introduced by proposal 0177. Use
  `make repaired-candidate-promotion-handoff` after
  `idea_to_spec_rerun_materialization` to extract the repaired candidate graph
  preview, recompute pre-SIB, repair-loop preview, candidate spec
  materialization, promotion gate, active candidate, and repair-session journal
  as separate `repaired_*` artifacts. The handoff can make the repair session
  ready for candidate approval review while keeping Platform promotion blocked
  until a separate `candidate_approval_decision`, and it does not mutate source
  artifacts, canonical specs, ontology packages, Git branches, or read models.
- `tools/candidate_overview.py`: public-safe candidate overview producer
  introduced by proposal 0201. Use `make candidate-overview` to write
  `runs/candidate_overview.json` from the event-storming intake, candidate
  graph, repaired graph when present, repair session, Idea Maturity report,
  project-local ontology review/effect artifacts, and repaired handoff. The
  overview is a narrative/navigation surface for SpecSpace: it summarizes
  product intent, understood scope, event-storming groups, topology relation
  counts, repair readiness, project-local ontology state, and the next safe
  action without executing prompt agents, applying answers, mutating specs,
  accepting ontology terms, creating Git state, or publishing read models.
- `tools/product_workspace_repair_pack.py`: product workspace repair-pack
  materializer introduced by proposal 0182. Use
  `make product-workspace-repair-pack-state` to convert a
  `product_workspace_repair_pack` fixture plus the current repair session and
  clarification requests into standard SpecSpace-owned
  `runs/idea_to_spec_repair_drafts.json` and
  `runs/idea_to_spec_repair_rerun_requests.json`. When supplied with a
  project-local ontology review lane, the same materializer can also write
  SpecSpace-owned `runs/project_local_ontology_review_decisions.json` for the
  selected demo pack. Use
  `make product-workspace-happy-path-repair-pack` to replay the selected pack
  through the existing import preview, rerun request gate, repair-draft rerun,
  project-local ontology decision import/effect reports, repaired handoff, Idea
  Maturity validation, and candidate overview chain. The default fixture is Team
  Decision Log, and
  `make product-workspace-team-decision-log-happy-path-repair-pack` is only a
  documented demo alias. The pack is demo input data and does not make drafts
  authoritative, apply answers, accept ontology terms, mutate specs, approve
  candidates, or create Git state.
- The `Publish Static Artifacts` workflow builds the ordinary public bundle and
  then builds a Team Decision Log product workspace bundle under
  `dist/specgraph-public/workspaces/team-decision-log`. That workspace bundle
  has its own `artifact_manifest.json`, so SpecSpace can route
  `/team-decision-log` to product artifacts instead of the bootstrap root
  bundle.
- `tools/product_ontology_gap_review_decisions.py`: product-scoped ontology
  gap decision builder introduced by proposal 0168. Use
  `make product-ontology-gap-review-decisions` to consume a ready
  `idea_to_spec_clarification_answers` report and write
  `runs/product_ontology_gap_review_decisions.json` with typed decisions for
  existing-term bindings, aliases, project-local terms, rejected non-domain
  terms, and owner-review deferrals. The report is review-only and does not
  accept ontology terms, write Ontology packages, mutate candidate artifacts,
  approve candidates, create branches, or publish read models.
- `tools/project_local_ontology_review_lane.py`: read-only project-local
  ontology review lane introduced by proposal 0197. Use
  `make project-local-ontology-review-lane` to group candidate ontology gaps by
  product term, attach product ontology decision evidence, show rerun preview
  effects, and emit operator next actions such as keep project-local, bind,
  alias, reject, defer, or request workspace promotion. The lane is report-only
  and does not write Ontology packages, accept ontology terms, mutate source
  artifacts, approve candidates, create branches, or publish read models.
- `tools/specspace_project_local_ontology_decision_import_preview.py`:
  SpecSpace-owned project-local ontology decision import preview introduced by
  proposal 0198. Use
  `make specspace-project-local-ontology-decision-import-preview` to validate
  `runs/project_local_ontology_review_decisions.json` against
  `runs/project_local_ontology_review_lane.json` and write
  `runs/specspace_project_local_ontology_decision_import_preview.json` with
  accepted, invalid, missing, and non-resolving decisions. The preview is
  report-only and does not apply decisions, write Ontology packages, accept
  terms, mutate candidate artifacts, or execute Platform/Git Service.
- `make product-workspace-decision-backed-repair-chain`: convenience wrapper
  introduced by proposal 0170. It runs the standard
  `product-workspace-active-candidate` flow, then validates clarification
  answers, derives `product_ontology_gap_review_decisions`, feeds those typed
  decisions into `idea_to_spec_answer_rerun_input`, and builds rerun preview
  plus rerun materialization. The wrapper forwards custom output paths between
  steps and does not grant any additional write authority.
- `tools/idea_to_spec_repair_session_journal.py`: durable repair-session
  journal builder introduced by proposal 0171. Use
  `make idea-to-spec-repair-session-journal` to aggregate active candidate,
  clarification request/answer, product ontology decision, rerun input,
  preview, materialization, and promotion-gate artifacts into
  `runs/idea_to_spec_repair_session.json`. The journal records source refs,
  digests, ordered repair stages, accepted answers, ontology decisions,
  resolved/unresolved ontology gap counts, and approval/promotion readiness
  without applying answers, accepting ontology terms, mutating candidate
  artifacts, creating branches, or publishing read models.
- `tools/specspace_repair_draft_import_preview.py`: review-only SpecSpace
  repair draft import preview builder introduced by proposal 0172. Use
  `make specspace-repair-draft-import-preview` to consume
  `runs/idea_to_spec_repair_drafts.json`,
  `runs/idea_to_spec_repair_session.json`, and
  `runs/idea_to_spec_clarification_requests.json`, then write
  `runs/specspace_repair_draft_import_preview.json`. The preview validates
  SpecSpace-owned draft state, source refs, allowed actions, answer shapes, and
  authority flags before exposing sanitized clarification answer candidates and
  product ontology decision candidates. It does not apply drafts, mutate
  candidate artifacts, accept ontology terms, write Ontology packages, create
  branches, or publish read models.
- `tools/specspace_repair_drafts_to_rerun_artifacts.py`: review-only
  SpecSpace repair draft rerun builder introduced by proposal 0173. Use
  `make product-workspace-repair-draft-rerun` or
  `make specspace-repair-draft-rerun` to consume a ready
  `runs/specspace_repair_draft_import_preview.json` and write the standard
  `idea_to_spec_clarification_answers`,
  `product_ontology_gap_review_decisions`,
  `idea_to_spec_answer_rerun_input`, `idea_to_spec_rerun_preview`,
  `idea_to_spec_rerun_materialization`, and
  `idea_to_spec_repair_session` artifacts plus
  `runs/specspace_repair_draft_rerun_report.json`. The builder reuses existing
  review-only artifact contracts and does not apply drafts, mutate source
  artifacts, accept ontology terms, write canonical specs, create branches, or
  publish read models. If the import preview is not ready, it writes only the
  rerun report and leaves existing shared rerun artifacts untouched.
- `tools/specspace_repair_rerun_request_gate.py`: review-only SpecSpace
  repair rerun request gate introduced by proposal 0174. Use
  `make specspace-repair-rerun-request-gate` to validate
  `runs/idea_to_spec_repair_rerun_requests.json` against a ready import
  preview and repair-session journal, or
  `make product-workspace-requested-repair-draft-rerun` to refresh the import
  preview, gate the request in strict mode, and then run the existing proposal
  0173 rerun builder. The gate treats SpecSpace request state as operator
  intent only; it rejects `may_execute_specgraph`, `may_run_make_target`,
  ontology, Git, or canonical mutation authority claims.
- `tools/candidate_spec_materialization.py`: deterministic candidate spec YAML
  preview materializer introduced by proposal 0153. Use
  `make candidate-spec-materialization
  CANDIDATE_SPEC_MATERIALIZATION_CANDIDATE_GRAPH=<json>
  CANDIDATE_SPEC_MATERIALIZATION_REPAIR_LOOP=<json>` to write review-only spec
  shaped YAML files under `runs/materialized_candidate_specs/` and
  `runs/candidate_spec_materialization_report.json`. The report exposes paths
  that Platform can pass to `graph-repository promotion-request` while keeping
  canonical spec mutation, branches, commits, PRs, and Ontology writes outside
  this tool's authority.
- `tools/idea_to_spec_promotion_gate.py`: final deterministic idea-to-spec
  promotion gate introduced by proposal 0154. Use
  `make idea-to-spec-promotion-gate` after pre-SIB, repair-loop, and
  materialization artifacts exist. The gate writes
  `runs/idea_to_spec_promotion_gate.json` and exposes Platform promotion paths
  only when repair context is resolved, materialization is ready, and paths are
  safe.
- `tools/active_idea_to_spec_candidate_source.py`: active candidate source
  builder introduced by proposal 0155, made generic by proposal 0160, and made
  artifact-derived by default in proposal 0161. Proposal 0162 moves the normal
  product runner entry point one step earlier through
  `user_idea_intake_session`. Use
  `make product-workspace-active-candidate
  PRODUCT_WORKSPACE_IDEA_SOURCE=<json>` to build the `product_idea_to_spec`
  artifact chain from generic raw/session idea data and
  `runs/active_idea_to_spec_candidate.json`. The artifact proves that
  materialization and promotion-gate surfaces come from a product workspace
  active candidate rather than fixture/demo leakage or public placeholders.
  By default the builder reads the standard generated `runs/*` artifacts,
  derives candidate id, display name, and route from
  `idea_event_storming_intake.source_intake`, and uses the standard active
  product workspace governance defaults. An explicit active candidate config is
  now optional and should be treated as a compatibility/debug override for
  nonstandard artifact paths or legacy prepared-seed flows. The default
  `PRODUCT_WORKSPACE_IDEA_SOURCE` is Team Decision Log as data for the public
  product pilot, while tests can pass other source JSON files through the same
  target.
- `tools/candidate_approval_decision.py`: explicit candidate approval decision
  builder introduced by proposal 0157. Use `make candidate-approval-decision`
  after the active candidate source and promotion gate exist. The default state
  is `needs_context`; set `CANDIDATE_APPROVAL_DECISION_STATE=approved` only for
  an explicit operator approval. The artifact writes
  `runs/candidate_approval_decision.json` and does not create branches, commits,
  pull requests, merges, read models, canonical spec mutations, or Ontology
  writes.
- `--build-ontology-supervisor-semantic-gate`: refresh the same ontology
  semantic surfaces through the supervisor entrypoint and print a compact gate
  report for `runs/ontology_supervisor_semantic_gate.json` without running
  prompt agents or mutating canonical specs.
- ordinary targeted supervisor runs read
  `runs/ontology_supervisor_semantic_gate.json` as soft review evidence; a
  `blocked` or `review_pending` gate suppresses silent `--auto-approve`
  canonical sync while still leaving executor invocation non-blocking.
- `--build-supervisor-executor-adapter-index`: build
  `runs/supervisor_executor_adapter_index.json` from the 0056 policy so
  executor backend availability, capability gaps, and Agent Passport CLI
  diagnostics are visible without launching nested executors.
- `--build-local-operator-executor-readiness`: build local-only
  `runs/local_operator_executor_readiness.json` so an operator can see whether
  the current checkout is ready for the next bounded executor smoke step. This
  does not launch Codex, does not claim runtime enforcement, and is excluded
  from public static publishing.
- `--build-local-operator-executor-smoke`: build local-only
  `runs/local_operator_executor_smoke.json` by consuming
  `runs/local_operator_executor_readiness.json` and running only a bounded
  backend probe such as `codex --version`. This does not run an agent task, does
  not claim runtime enforcement, and is excluded from public static publishing.
- `--build-local-operator-executor-task-smoke`: build local-only
  `runs/local_operator_executor_task_smoke.json` by consuming both
  `runs/local_operator_executor_readiness.json` and
  `runs/local_operator_executor_smoke.json`, then running a bounded executor
  task with a strict JSON response contract. The artifact stores only sanitized
  status, response shape, and mutation guard results; it does not persist raw
  executor logs, raw responses, absolute executable paths, or public static
  output.
- `--build-local-operator-executor-report-contract`: build local-only
  `runs/local_operator_executor_report_contract.json` from the generic
  executor/producer report contract after task smoke. The contract supports
  `coding_agent`, `harvester`, `operator_tool`, and `external_harness`
  producers, validates sample report shape without running a new executor task,
  and keeps report contract diagnostics out of public static publishing.
- `--build-local-operator-executor-report-smoke`: build local-only
  `runs/local_operator_executor_report.json` by consuming the task smoke and
  report contract artifacts, running a bounded report-only executor task,
  validating the returned report through the generic report validator, and
  recording sanitized smoke and mutation metadata without publishing the
  artifact.
- `--build-local-operator-executor-report-review-packet`: build local-only
  `runs/local_operator_executor_report_review_packet.json` by consuming a valid
  local executor report and the `executor_report_consumption_policy`, producing
  a reviewable packet that requires human/operator review without creating
  proposals, applying patches, mutating canonical specs, or publishing local
  artifacts.
- `--build-local-operator-executor-analysis-report-review-outcome`: build
  local-only `runs/local_operator_executor_analysis_report_review_outcome.json`
  by consuming a human-review-ready `analysis_report` review packet and the
  `executor_analysis_report_consumption_policy`, preserving operator review
  evidence without creating proposal drafts, applying patches, mutating
  canonical specs, changing proposal status, or publishing local artifacts.
- `--build-local-operator-executor-analysis-report-followup-packet`: build
  local-only `runs/local_operator_executor_analysis_report_followup_packet.json`
  by consuming a ready analysis report review outcome and the
  `executor_analysis_report_followup_policy`, carrying sanitized findings,
  safe evidence refs, and governed decision options without invoking executors,
  creating proposal drafts, applying patches, mutating canonical specs,
  changing proposal status, or publishing local artifacts.
- `--build-local-operator-executor-analysis-report-followup-decision`: build
  local-only `runs/local_operator_executor_analysis_report_followup_decision.json`
  by consuming a ready analysis report follow-up packet and recording an
  explicit human/operator decision (`accept`, `reject`, `defer`, or
  `needs_more_evidence`). Accepted decisions only authorize the next governed
  request-building step; they do not write proposals, invoke executors, mutate
  canonical specs, apply patches, close gaps, or publish local artifacts.
- `--build-local-operator-executor-proposal-draft-request`: build local-only
  `runs/local_operator_executor_proposal_draft_request.json` by consuming an
  accepted executor follow-up decision and producing only a request for a future
  proposal-draft workflow. The request does not create draft candidates, write
  proposal markdown, invoke executors, mutate registries/status, mutate
  canonical specs, apply patches, close gaps, or publish local artifacts.
- `--build-local-operator-executor-followup-proposal-draft-candidate`: build
  local-only
  `runs/local_operator_executor_followup_proposal_draft_candidate.json` by
  consuming a ready proposal draft request and producing a draft candidate that
  still requires explicit downstream promotion policy and human review. It does
  not write proposal markdown, invoke executors, mutate registries/status,
  mutate canonical specs, apply patches, close gaps, or publish local artifacts.
- `--build-local-operator-executor-proposal-draft-candidate`: build local-only
  `runs/local_operator_executor_proposal_draft_candidate.json` by consuming a
  valid `proposal_draft` review packet and the
  `executor_report_to_proposal_draft_policy`, producing a draft candidate that
  still requires explicit human promotion without writing proposal markdown,
  mutating proposal registries, changing proposal status, applying patches, or
  publishing local artifacts.
- `--build-local-operator-executor-proposal-promotion-packet`: build
  local-only `runs/local_operator_executor_proposal_promotion_packet.json` by
  consuming a valid proposal draft candidate and the
  `proposal_draft_candidate_promotion_policy`, recording authorization and safe
  target provenance without writing proposal markdown, mutating proposal
  registries, changing proposal status, applying patches, or publishing local
  artifacts.
- `--build-local-operator-executor-proposal-source-materialization`: build
  local-only `runs/local_operator_executor_proposal_materialization_report.json`
  by consuming a valid promotion packet and the deterministic materialization
  policy, writing exactly one safe `docs/archive/proposal_sources/...` draft
  target, and recording mutation guard results without writing
  `docs/proposals/`, mutating proposal registries, changing proposal status,
  applying patches, invoking executors, or publishing local artifacts.
- `--build-local-operator-executor-public-proposal-doc-materialization`: build
  local-only `runs/local_operator_executor_public_proposal_materialization_report.json`
  by consuming a valid source materialization report and the public proposal doc
  materialization policy, writing exactly one matching `docs/proposals/...`
  document, and recording mutation guard results without mutating proposal
  registries, changing proposal status, applying patches, invoking executors,
  or publishing local artifacts.
- `public_proposal_doc_materialization_policy` in
  `tools/supervisor_executor_adapter_policy.json`: defines the policy-only
  boundary for turning a valid local proposal source materialization report into
  a future `docs/proposals/...` materialization request. It requires explicit
  human authorization, matching source/target ids and filenames, and the current
  deterministic proposal id while rejecting executor invocation, registry/status
  mutation, canonical mutation, patch application, gap closure, and static
  publication of local materialization state.
- `executor_report_consumption_policy` in
  `tools/supervisor_executor_adapter_policy.json`: defines which supervisor or
  downstream surfaces may consume a valid local executor report, which
  transformations/effects are allowed, and which effects remain forbidden. This
  is a policy/validator surface rather than a new executor command; reports are
  admissible input/evidence, not authority.
- `executor_report_to_proposal_draft_policy` in
  `tools/supervisor_executor_adapter_policy.json`: defines the policy-only
  boundary for turning a human-review-ready executor report review packet into a
  future proposal draft candidate. It accepts only `proposal_draft` review
  packets and keeps executor reports/review packets as input rather than
  authority; it does not create proposal drafts or run a new executor task.
- `executor_analysis_report_consumption_policy` in
  `tools/supervisor_executor_adapter_policy.json`: defines the policy-only
  boundary for consuming human-review-ready `analysis_report` review packets as
  future analysis review outcome input. It keeps analysis reports separate from
  the proposal-draft path and rejects proposal draft candidate production,
  authority expansion, canonical mutation, patch application, gap closure,
  proposal status mutation, and public static publication.
- `executor_analysis_report_followup_policy` in
  `tools/supervisor_executor_adapter_policy.json`: defines the policy-only
  boundary for consuming a valid local analysis report review outcome before a
  future follow-up packet exists. It accepts only `ready_for_operator_review`
  `analysis_report_review_outcome` input and allows only a future
  `analysis_report_followup_packet` effect while rejecting executor invocation,
  proposal draft production, proposal writes, registry/status mutation,
  canonical mutation, patch application, gap closure, authority expansion, and
  public static publication of local outcome state.
- `proposal_draft_candidate_promotion_policy` in
  `tools/supervisor_executor_adapter_policy.json`: defines the policy-only
  boundary for turning a valid local-only proposal draft candidate into a future
  promotion packet request. It requires explicit human authorization, accepts
  only proposal source draft target paths under `docs/archive/proposal_sources/`,
  and rejects direct proposal markdown writes, proposal registry mutation,
  proposal status mutation, canonical mutation, patch application, and gap
  closure.
- `deterministic_proposal_draft_materialization_policy` in
  `tools/supervisor_executor_adapter_policy.json`: defines the policy-only
  boundary for turning a ready local promotion packet into a deterministic
  proposal source draft materialization request. It requires the current
  deterministic `make proposal-id` target, explicit human authorization, and a
  safe `docs/archive/proposal_sources/` path while rejecting executor
  invocation, direct `docs/proposals/` writes, proposal registry/status
  mutation, canonical mutation, patch application, gap closure, and static
  publication of local materialization state.
- `--build-agent-passport-derived-surfaces`: build Agent Passport derived
  surfaces from `tools/agent_passport_adoption_policy.json` and the 0056
  executor adapter index, including report-only Agent Passport CLI validation
  when the CLI and repository-local passport documents are available. This does
  not verify signatures or enforce passports.
- `--build-agent-runtime-enforcement-evidence`: build report-only Agent
  Passport runtime enforcement evidence artifacts and
  `runs/agent_runtime_enforcement_evidence_index.json` for current
  runtime-smoke declarations. This records safe evidence refs and the
  supervisor executor adapter invocation-boundary smoke plus redacted local
  executor evidence summaries for review without claiming observed runtime
  enforcement.
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
- `--build-metric-pack-index`: build `runs/metric_pack_index.json` from
  `tools/metric_pack_registry.json` and external-consumer observations so
  metric-pack source availability, authority state, missing inputs, and next
  gaps become visible without executing metric packs.
- `--build-metric-pack-registry-drift`: build
  `runs/metric_pack_registry_drift.json` by comparing
  `tools/metric_pack_registry.json` with the sibling Metrics
  `METRIC_PACKS.md` contract so source registry drift is observable without
  auto-syncing either repository.
- `--build-metric-pack-adapter-index`: build
  `runs/metric_pack_adapter_index.json` from the current metric-pack index so
  declared pack inputs are mapped to existing SpecGraph source artifacts or
  surfaced as computability gaps without executing metric packs.
- `--build-metric-pack-runs`: build `runs/metric_pack_runs.json` from the
  current metric-pack index, adapter index, and metric-signal index so already
  computable pack values are visible as read-only snapshots without promoting
  findings.
- `--build-metric-pricing-provenance`: build
  `runs/metric_pricing_provenance.json` so economic observability has a
  versioned pricing surface before cost-like metric values are calculated. This
  command also refreshes `runs/model_usage_telemetry_index.json` because pricing
  provenance binds to that source artifact.
- `--build-model-usage-telemetry`: build
  `runs/model_usage_telemetry_index.json` from supervisor run logs so model
  usage becomes a reviewable metric-pack input adapter before token-level spend
  is available.
- `--build-conversation-memory-index`: build
  `runs/conversation_memory_index.json` from
  `tools/conversation_memory_policy.json`,
  `conversation_memory/sources/*.json`, and `conversation_memory/notes/*.md`
  so structured exploration memory has a read-only viewer surface before any
  archive mining or proposal promotion.
- `--build-conversation-memory-map`: build
  `runs/conversation_memory_map.json` from the current conversation-memory
  index so clusters, links, source coverage, promotion candidates, and review
  blockers become inspectable without mutating canonical specs.
- `--build-conversation-memory-promotion-pressure`: build
  `runs/conversation_memory_promotion_pressure.json` from the current
  conversation-memory map so reviewable promotion candidates are visible
  without creating proposals or mutating canonical specs.
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
- `--build-viewer-surfaces`: refresh local viewer-facing generated artifacts by
  writing the dashboard/backlog/next-move artifacts plus their viewer-facing
  source artifacts in one standalone pass. This includes graph health, intent,
  proposal, trace, evidence, external-consumer, handoff, Metrics delivery,
  Metrics feedback, SpecPM export/delivery/feedback, metric signal, metric
  threshold, metric pack, model usage, pricing, conversation-memory,
  review-feedback, and spec-activity surfaces. The command keeps `runs/*`
  internally consistent for ContextBuilder because dashboard and feedback
  `source_artifacts` point at freshly written files rather than stale local JSON.
  This is safe for local hooks, CI smoke checks, or ContextBuilder build buttons because it does not
  choose implementation target scope or create new implementation work items.
  Successful refinement and gate-resolution supervisor steps also invoke this
  builder as a non-blocking post-step refresh and record compact diagnostics
  under `runs/viewer_surfaces_refresh/`.
- Standalone artifact commands print compact JSON summaries by default. Use
  `--output-mode full` only when the complete artifact is needed on stdout; the
  canonical generated artifact is still written under `runs/`.
- `--build-graph-dashboard`: build `runs/graph_dashboard.json` as one
  aggregated viewer-facing dashboard with headline counts from graph health,
  proposal, implementation, evidence, external-consumer, handoff, and metric
  surfaces, including review-feedback learning-loop health.
- `--build-graph-backlog-projection`: build
  `runs/graph_backlog_projection.json` as a normalized viewer-facing backlog
  projection from existing derived graph, proposal, implementation, evidence,
  external-consumer, SpecPM, Metrics, threshold-proposal, and review-feedback
  surfaces, including reviewable branch rewrite preview candidates when a
  current preview is ready.
- `--build-graph-next-moves`: build `runs/graph_next_moves.json` as a
  read-only advisory "next move" surface that selects one bounded recommended
  operator move from branch rewrite preview, graph backlog, and proposal
  runtime state.
- `--build-spec-activity-feed`: build `runs/spec_activity_feed.json` as a
  viewer-facing activity feed that maps git-observed canonical, trace,
  evidence, proposal, implementation, and review-feedback changes back to
  spec ids. See
  [docs/spec_activity_feed_viewer_contract.md](../docs/spec_activity_feed_viewer_contract.md).
- `--build-intent-layer-overlay`: build `runs/intent_layer_overlay.json` from
  repository-tracked intent-layer nodes under `intent_layer/nodes/`, so
  pre-canonical user intent and operator-request artifacts can be inspected as
  a separate mediation layer.
- `--build-exploration-preview`: build `runs/exploration_preview.json` from an
  optional inline `--exploration-intent TEXT`, producing a review-only
  assumption-mode placeholder graph without mutating canonical specs or tracked
  intent/proposal artifacts.
- `--build-branch-rewrite-preview --target-spec SG-SPEC-XXXX`: build
  `runs/branch_rewrite_preview.json` for one bounded active `refines` subtree,
  surfacing topology-prose and role-legibility rewrite pressure without
  mutating canonical specs or tracked proposal/intent artifacts.
- `--build-implementation-delta-snapshot`: build
  `runs/implementation_delta_snapshot.json` from explicit
  `--target-scope-kind`, `--target-spec-ids`, and `--operator-intent` values,
  producing a derived planning snapshot without mutating canonical specs or
  runtime code. Supported scope kinds are `spec` for an exact spec list and
  `active_subtree` for an active `refines` graph-region expansion from the
  selected root specs.
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
- `--build-proposal-spec-trace-index`: build `runs/proposal_spec_trace_index.json` from
  proposal markdown references, proposal-promotion traceability, and
  proposal-lane target regions. The artifact is read-only and normalizes
  textual mentions separately from bounded promotion traces.
- `--build-proposal-tracking-report`: build `runs/proposal_tracking_report.json`
  as a report-only check that every proposal doc is either linked to a tracking
  surface or explicitly classified as no-runtime-required.
- `--check-proposal-tracking-gate`: build the proposal tracking report and fail
  if proposal docs are not represented by runtime registry, promotion trace,
  proposal-spec trace, or an explicit no-runtime classification.
- `--build-proposal-work-claim-report`: build
  `runs/proposal_work_claim_report.json` from `tools/proposal_work_claims.json`
  to show active, released, expired, malformed, and duplicate proposal work
  claims.
- `--check-proposal-work-claim-gate`: build the proposal work claim report and
  fail on malformed, expired, or duplicate active claims. The gate does not
  require every proposal PR to have a claim.
- `--allocate-proposal-id`: print the next deterministic four-digit proposal ID
  from proposal docs, source drafts, runtime/promotion registries, and work
  claims. The command is read-only and fails on active proposal/draft slug
  conflicts or malformed registry IDs; historical source-draft slug collisions
  are reported as warnings.
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
- `runs/branch_rewrite_preview.json`: review-only branch rewrite preview for
  one active `refines` subtree, including branch-story summary, per-node
  rewrite candidates, status mapping, risk, explicit mutation boundary, and
  backlog/dashboard projection when candidates are ready for review
- `runs/implementation_delta_snapshot.json`: derived Implementation Work
  planning snapshot that captures baseline, explicit target scope, delta fields,
  source-artifact availability, readiness, and next gap without canonical or
  runtime code mutation
- `runs/implementation_work_index.json`: bounded Implementation Work items
  generated from the latest delta snapshot, grouped by readiness, next gap, and
  viewer filters for review before any coding-agent handoff; its
  `implementation_backlog.items[]` rows also feed the graph backlog/dashboard
  surfaces
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
  next-gap backlog; includes SpecSpace-oriented artifact contract handoffs and
  report-only evidence contract shapes when declared by the consumer registry
- `runs/external_consumer_evidence_index.json`: report-only evidence acceptance
  surface for downstream consumer implementations, grouped by acceptance status,
  result, named filters, and next evidence gaps while rejecting local-only path
  leakage
- `runs/supervisor_executor_adapter_index.json`: read-only executor adapter
  surface for proposal 0056, including backend availability, declared
  capabilities, Agent Passport CLI diagnostics, capability gaps, and safe next
  actions without publishing absolute executable paths or raw logs
- `runs/local_operator_executor_readiness.json`: local-only readiness report for
  operator executor smoke preparation, including sanitized executable
  availability, invocation-boundary, and report-only Agent Passport checks;
  this artifact is intentionally not published in the static bundle
- `runs/local_operator_executor_smoke.json`: local-only executor probe result
  that consumes the readiness artifact, runs only the policy-declared probe, and
  records sanitized status without raw logs, absolute executable paths, canonical
  mutations, or public static publication
- `runs/local_operator_executor_task_smoke.json`: local-only bounded executor
  task result that consumes readiness and smoke artifacts, asks the configured
  backend for a strict `bounded_executor_task_smoke` JSON acknowledgement, and
  records sanitized response and mutation guard evidence without raw logs, raw
  responses, absolute executable paths, canonical mutations, or public static
  publication
- `runs/local_operator_executor_report_contract.json`: local-only contract
  preview for future bounded executor/producer reports, including allowed
  producer kinds, authority levels, report kinds, sanitized sample validation,
  and next-gap guidance without persisting raw report bodies or public static
  publication
- `runs/local_operator_executor_report.json`: local-only bounded executor
  report smoke artifact that contains a contract-valid report when the smoke
  passes, or a sanitized `invalid_report` fallback when validation fails, with
  `smoke_summary`, source validations, execution metadata, and mutation guard
  checks excluded from public static publishing
- `runs/local_operator_executor_report_review_packet.json`: local-only review
  packet built from a valid executor report and the report consumption policy,
  preserving findings/evidence as review input while requiring human/operator
  review and forbidding canonical mutation, proposal status mutation, patch
  application, gap closure, and public static publication
- `runs/local_operator_executor_analysis_report_review_outcome.json`:
  local-only outcome built from a valid `analysis_report` review packet and the
  analysis report consumption policy, preserving sanitized findings/evidence as
  operator review input while forbidding proposal draft candidate production,
  canonical mutation, proposal status mutation, patch application, gap closure,
  and public static publication
- `runs/local_operator_executor_proposal_draft_candidate.json`: local-only
  proposal draft candidate built from a valid `proposal_draft` review packet,
  requiring explicit human promotion into the proposal lane while forbidding
  proposal markdown writes, proposal registry mutation, proposal status
  mutation, canonical mutation, patch application, gap closure, and public
  static publication
- `runs/local_operator_executor_followup_proposal_draft_candidate.json`:
  local-only proposal draft candidate built from a ready accepted follow-up
  proposal draft request, requiring explicit downstream promotion policy and
  human review while forbidding proposal markdown writes, proposal registry
  mutation, proposal status mutation, canonical mutation, patch application,
  gap closure, executor invocation, and public static publication
- `runs/local_operator_executor_proposal_promotion_packet.json`: local-only
  promotion packet built from a valid proposal draft candidate and explicit
  promotion authorization, recording safe target provenance while forbidding
  proposal markdown writes, proposal registry mutation, proposal status
  mutation, canonical mutation, patch application, gap closure, and public
  static publication
- `runs/local_operator_executor_proposal_materialization_report.json`:
  local-only materialization report built from a valid promotion packet and
  deterministic materialization request, recording the safe source draft target
  and mutation guard result while forbidding `docs/proposals/` writes,
  proposal registry/status mutation, canonical mutation, patch application, gap
  closure, executor invocation, and public static publication
- `executor_report_consumption_policy`: policy-only surface that allows valid
  local executor reports to become review packet, proposal draft candidate,
  implementation planning, evidence reference, or handoff input while rejecting
  direct canonical mutation, patch application, gap closure, proposal status
  mutation, static publication, and canonical fact assertion effects
- `executor_report_to_proposal_draft_policy`: policy-only surface that allows
  only human-review-ready `proposal_draft` review packets to become future
  proposal draft candidates while rejecting analysis reports, forbidden effects,
  authority expansion, direct canonical mutation, patch application, gap
  closure, and proposal status mutation
- `executor_analysis_report_consumption_policy`: policy-only surface that
  allows only human-review-ready `analysis_report` review packets to become
  future analysis review outcome input while rejecting proposal draft candidate
  production, forbidden effects, authority expansion, direct canonical
  mutation, patch application, gap closure, proposal status mutation, and static
  publication
- `executor_analysis_report_review_outcome_contract`: local-only outcome
  contract for turning a valid `analysis_report` review packet into operator
  review input while keeping executor report, review packet, and outcome
  non-authoritative
- `proposal_draft_candidate_promotion_policy`: policy-only surface that allows
  only valid local proposal draft candidates plus explicit human authorization
  to request a future promotion packet, while rejecting direct proposal markdown
  writes, proposal registry mutation, proposal status mutation, canonical
  mutation, patch application, gap closure, and unsafe target paths
- `deterministic_proposal_draft_materialization_policy`: policy-only surface
  that allows only valid local promotion packets plus explicit human
  authorization to request deterministic proposal source draft materialization,
  while rejecting non-next proposal ids, unsafe or registry targets, executor
  invocation, direct proposal writes, proposal registry/status mutation,
  canonical mutation, patch application, gap closure, and static publication
- `public_proposal_doc_materialization_policy`: policy-only surface that allows
  only valid local proposal source materialization reports plus explicit human
  authorization to request future public proposal doc materialization, while
  rejecting source report authority, non-next proposal ids, mismatched
  source/target filenames, unsafe targets, executor invocation,
  registry/status mutation, canonical mutation, patch application, gap closure,
  and static publication
- `runs/local_operator_executor_public_proposal_materialization_report.json`:
  local-only materialization report emitted by
  `--build-local-operator-executor-public-proposal-doc-materialization`; it
  records the source report, source/target relative paths, request validation,
  mutation guard result, and checks without persisting source draft text, raw
  logs, absolute paths, secrets, or static-publish state
- `runs/agent_surface_index.json`: read-only Agent Passport adoption surface
  index for graph-facing agents, including policy-declared surfaces and
  executor backends derived from the 0056 adapter index
- `runs/known_agent_passport_index.json`: read-only graph-side Agent Passport
  reference index that distinguishes known surfaces, referenced passports, and
  report-only schema-valid passports
- `runs/agent_passport_verification_report.json`: sanitized report-only Agent
  Passport CLI validation output for repository-local draft passport documents,
  grouped by verification status without storing raw passport material or local
  machine paths
- `runs/agent_verification_gap_index.json`: read-only verification gap index
  for missing passports, unavailable validator tooling, invalid or unavailable
  passport documents, unattempted verification, and classified runtime
  enforcement posture, including runtime enforcement evidence plan metadata for
  future observed-enforcement promotion
- `runs/agent_runtime_enforcement_evidence_index.json`: report-only Agent
  Passport runtime enforcement evidence registry that summarizes safe
  runtime-smoke evidence refs by surface, status, evidence kind, and viewer
  filters without claiming observed enforcement
- `runs/agent_runtime_enforcement_evidence/*.json`: curated report-only runtime
  evidence detail artifacts. The initial supervisor executor adapter smoke
  proves derived adapter/passport surfaces are internally consistent, safe to
  reference, and constrained to declarative CLI executable lookup without shell
  command persistence. Redacted local executor summaries may reference
  local-only executor artifacts without publishing their payloads. These
  artifacts do not prove sandbox or runtime policy enforcement.
- `runs/specauthor_invocation_artifact.json`: public-safe, review-only
  SpecAuthor invocation artifact assembled by `make specauthor-authoring-flow`.
- `runs/specauthor_invocation_artifact_contract_report.json`: public-safe
  contract validation report for the SpecAuthor invocation artifact.
- `runs/specauthor_authoring_flow_report.json`: compact public-safe summary for
  the deterministic SpecAuthor authoring flow.
- `runs/idea_event_storming_intake.json`: review-only idea-to-spec intake
  artifact containing structured event-storming context, public-safe source
  workspace metadata, and candidate-graph readiness state without raw intent
  text or canonical graph mutation.
- `runs/candidate_spec_graph_seed.json`: review-only ontology-bound seed for
  candidate graph generation, including core ontology bindings, product-domain
  ontology gaps, source-generation status, and no canonical write authority.
- `runs/candidate_spec_graph.json`: review-only candidate specification graph
  artifact containing candidate nodes, edges, requirements, acceptance
  criteria, claims, gaps, source-intake refs, and pre-SIB readiness state.
- `runs/pre_sib_coherence_report.json`: review-only metric and coherence report
  over a candidate graph, including structural counts, coverage ratios,
  findings, warnings, and readiness for the future repair loop.
- `runs/idea_to_spec_clarification_requests.json`: public-safe, review-only
  request surface over intake questions, candidate graph gaps, pre-SIB findings,
  repair-loop actions, and ontology gap review groups. It carries stable request
  ids for the future clarification answer contract without granting mutation
  authority.
- `runs/idea_to_spec_clarification_answers.json`: public-safe, review-only
  answer validation report over clarification requests. It records accepted and
  unresolved answers for future rerun input without applying mutations.
- `runs/idea_to_spec_answer_rerun_input.json`: public-safe, review-only overlay
  that maps accepted clarification answers into intake, ontology review, and
  candidate review hints for a later deterministic rerun without applying
  mutations.
- `runs/idea_intake_answer_rerun_input.json`: public-safe, review-only overlay
  that maps accepted real-intake clarification answers onto active-frame and
  event-storming target refs before rebuilding a clarified intake session.
- `runs/clarified_user_idea_intake_session.json`: review-only clarified intake
  session produced after accepted real-intake answers are applied. It can feed
  the candidate-source bridge when ready, while raw idea text remains local-only.
- `runs/idea_intake_clarification_rerun_report.json`: public-safe report over
  the real-intake clarification rerun, including accepted target counts,
  clarified session readiness, source/output refs, and explicit false authority
  boundary flags.
- `runs/real_idea_answer_template.json`: operator-editable, public-safe answer
  template introduced by proposal 0194. It records typed answer targets,
  accepted actions, required fields, evidence refs, and false authority flags
  for the current real-idea smoke run directory. Proposal 0210 adds workspace
  identity, source digest binding, and explicit fallback-free clarification
  outcomes.
- `runs/real_idea_answer_authoring_report.json`: review-only validation or
  materialization report for first-class real-idea answer authoring. It records
  source request refs, answer-set digest, validation status, output refs, and
  findings without publishing raw idea text.
- `runs/real_idea_answer_set.json`: generated compatible
  `idea_to_spec_clarification_answer_set` emitted from a filled first-class
  answer template. Existing clarification answer validators and rerun tools
  consume this artifact without a new protocol.
- `runs/idea_to_spec_rerun_preview.json`: public-safe, review-only preview that
  evaluates accepted-answer overlay effects against current intake and
  candidate graph state, including ontology gap resolution previews and
  candidate quality preview state. Proposal 0175 adds normalized ontology gap
  match provenance such as `match_kind` and `confidence`; proposal 0176 adds
  `candidate_gap_preview` for explicitly targeted product/spec repair answers,
  without applying mutations.
- `runs/idea_to_spec_rerun_materialization.json`: public-safe, review-only
  materialization report that nests a candidate graph preview with resolved
  ontology gaps moved into explicit `ontology_gap_resolutions` and resolved
  non-ontology product/spec gaps moved into `candidate_gap_resolutions`,
  without rewriting candidate graph source artifacts. Proposal 0175 preserves
  ontology gap matching provenance; proposal 0176 preserves candidate repair
  answer evidence in those resolution records.
- `runs/product_ontology_gap_review_decisions.json`: public-safe, review-only
  product ontology decision report derived from accepted ontology-gap
  clarification answers, without accepting ontology terms or writing Ontology
  packages.
- `runs/project_local_ontology_review_lane.json`: public-safe, review-only
  project-local ontology term lane derived from candidate ontology gaps,
  product ontology decisions, and optional rerun preview evidence. It is the
  stable downstream surface for SpecSpace project-local ontology review.
- `runs/specspace_project_local_ontology_decision_import_preview.json`:
  public-safe, review-only preview for SpecSpace-owned project-local ontology
  decisions. It validates workspace/candidate/session identity, stale lane refs,
  allowed actions, and authority boundaries before later flows may treat the
  decisions as evidence.
- `runs/project_local_ontology_decision_effect_report.json`: public-safe,
  review-only maturity evidence report for imported project-local ontology
  decisions. It counts accepted keep-local/bind/alias/reject/promotion
  decisions, keeps missing/invalid/deferred decisions visible as blockers or
  follow-up items, and does not write Ontology packages or accept terms.
- `runs/candidate_spec_materialization_report.json`: review-only report for
  local candidate spec YAML previews under `runs/materialized_candidate_specs/`,
  including materialized paths for Platform promotion-request handoff without
  canonical spec mutation.
- `runs/idea_to_spec_promotion_gate.json`: final review-only go/no-go surface
  before Platform promotion-request handoff, aggregating pre-SIB findings,
  repair-loop context requirements, materialization readiness, and promotion
  paths.
- `runs/active_idea_to_spec_candidate.json`: public-safe active candidate source
  for the configured product workspace, linking event-storming intake,
  candidate graph, pre-SIB report, repair-loop preview, materialization report,
  and promotion gate under `product_spec_workspace` authority. In the generic
  active path, candidate identity derives from the intake source, standard
  artifact refs derive from the generated `runs/*` chain, and readiness can be
  `active_candidate_review_required` when pre-SIB or promotion-gate blockers
  remain.
- `runs/candidate_approval_decision.json`: public-safe candidate approval
  decision artifact for CLI-mode product workspace promotion. It records the
  requested and effective decision state, operator ref, public-safe rationale,
  source refs, digests, findings, and authority boundary without treating the
  decision as a Git Service execution, repository review, merge, read-model
  publication, canonical spec mutation, or Ontology write.
- `runs/idea_maturity_metrics_report.json`: public-safe, read-only
  Idea-to-Spec lifecycle telemetry report for the Metrics RFC
  `idea_to_spec_maturity`. Build it with `make idea-maturity-metrics`. It
  normalizes clarification load, answer materialization, ontology grounding,
  candidate gap closure, workflow friction, promotion/readiness state, and
  optional downstream review/publication state from the selected lifecycle
  artifacts. The report also includes typed `readiness_explainers` for
  Pre-SIB findings, repair-session blockers, promotion-gate blockers, stale
  refs, policy failures, and invariant failures. These explain why readiness is
  blocked without granting approval, Git, ontology, prompt-agent, canonical
  mutation, or publication authority. The report also carries a `contract`
  object with Metrics-owned schema refs, validation-report schema refs,
  validator id/version, compatibility-policy refs, and RFC refs so downstream
  consumers can display the exact Metrics contract evidence.
  Proposal 0196 adds aggregate repair-answer accounting so answers consumed as
  rerun overlay closure evidence do not appear as ordinary unmaterialized answer
  debt.
- `runs/idea_maturity_metrics_validation_report.json`: public-safe validation
  evidence for the maturity metrics report. Build it with
  `make idea-maturity-metrics-validate`. The target invokes the Metrics
  repository CLI configured by `METRICS_CLI`/`METRICS_REPO`; SpecGraph does not
  copy the Metrics validator or become the metrics contract authority.
  `make product-workspace-idea-maturity` runs both steps, and the
  dashboard-ready product review targets
  `make product-workspace-decision-backed-repair-chain` and
  `make product-workspace-repaired-promotion-handoff` invoke that wrapper after
  their review-only outputs.
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
- `runs/metric_pack_index.json`: read-only metric-pack registry projection,
  grouped by pack status, review state, source reference state, authority state,
  missing inputs, and viewer-friendly named filters. See
  `docs/metric_pack_viewer_contract.md` for the ContextBuilder-facing contract
- `runs/metric_pack_registry_drift.json`: read-only drift report comparing the
  SpecGraph metric-pack registry with the sibling Metrics `METRIC_PACKS.md`
  contract, including missing checkout/contract, pack-id drift, source-path
  mismatches, and missing source artifacts
- `runs/metric_pack_adapter_index.json`: read-only adapter/computability report
  for metric-pack inputs, including available source-artifact bindings,
  not-computable inputs, and adapter backlog items before any metric execution
- `runs/metric_pack_runs.json`: read-only metric-pack run snapshot, including
  computed values from existing metric signals, not-computable gaps, source
  snapshots, and deferred finding/proposal projection
- `runs/metric_pricing_provenance.json`: read-only pricing provenance surface
  for economic observability, including model/tool identity, unit convention,
  pricing version, model-usage binding, missing-price behavior, and
  observed-spend gaps
- `runs/model_usage_telemetry_index.json`: read-only model usage telemetry
  surface, grouped by supervisor execution profile, observed run-log proxy
  counts, token-usage capture status, and next gaps for economic observability
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
  metric surfaces, Implementation Work items, and review-feedback learning-loop
  health
- `runs/graph_backlog_projection.json`: normalized work/backlog projection with
  concrete `entries[]` grouped by domain, priority, next gap, source artifact,
  and named filters, including branch rewrite candidates, Implementation Work,
  and process-feedback gaps, so viewers do not need `tasks.md` as a work queue.
  See
  [docs/graph_backlog_projection_viewer_contract.md](../docs/graph_backlog_projection_viewer_contract.md)
  for the stable viewer-facing field subset.
- `runs/graph_next_moves.json`: advisory game-master surface with
  `current_scene`, one `recommended_next_move`, alternatives, blocked moves, and
  compact source facts for a viewer "what should I do next?" panel. It is
  derived-only and cannot mutate canonical specs.
- `runs/proposal_tracking_report.json`: report-only proposal tracking surface
  that flags proposal markdown without runtime registry, promotion trace, or an
  explicit no-runtime classification. Use `make proposal-tracking` after adding
  proposal docs to see whether the graph will keep them visible as follow-up
  work.
- `make proposal-tracking-gate`: CI-enforced proposal tracking check. Run it
  before opening a PR that adds or changes proposal markdown.
- `runs/proposal_work_claim_report.json`: report-only proposal work ownership
  surface derived from `tools/proposal_work_claims.json`. Use
  `make proposal-work-claims-gate` before merging branches that add active work
  claims or change proposal ownership policy.
- `make proposal-id`: read-only deterministic proposal ID allocator. Run it
  before creating a new proposal or source draft instead of choosing the next
  number manually.
- `tools/graph_diagnostics.py`: read-only operator diagnostic that summarizes
  the current `runs/*.json` surfaces without relying on ad hoc `jq` assumptions.
  Use `make graph-diagnostics` after `make viewer-surfaces` to print the compact
  diagnosis.
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
- `tools/metric_pack_registry.json`: declarative metric-pack registry for
  plugin-style metric lenses such as `sib`, `sib_full`, and
  `sib_economic_observability`; this is source metadata, not runtime policy
  authority
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
  external consumers, such as `Metrics/SIB`, `Metrics/SIB_FULL`, and
  `SpecSpace`, used by the bridge index, bridge-backed metric derivation, and
  external handoff packet emission; the SpecSpace contract includes the Agent
  Passport posture artifacts and the report-only runtime enforcement evidence
  index
- `tools/external_consumer_overlay_policy.json`: declarative contract for the
  external-consumer overlay, including bridge states, named filters, and
  backlog next-gap defaults
- `tools/external_consumer_handoff_policy.json`: declarative contract for
  sibling-consumer handoff packets, including handoff states, packet
  provenance, review-state defaults, SpecSpace artifact/evidence contract
  defaults, and evidence acceptance status defaults
- `tools/external_consumer_evidence_registry.json`: operator-curated downstream
  implementation evidence records, initially binding the SpecSpace agent
  surface visibility PR, CI smoke, and Platform Timeweb publish run to the
  matching external-consumer handoff packet
- `tools/supervisor_executor_adapter_policy.json`: declarative contract for the
  supervisor executor adapter gateway, including request/report contracts,
  backend registry metadata, index contract fields, and Agent Passport CLI
  availability diagnostics
- `tools/agent_passport_adoption_policy.json`: declarative contract for
  report-only Agent Passport adoption surfaces, declared Agent Passport
  references, classified runtime enforcement posture, and verification gap
  indexes consumed by SpecSpace-oriented handoff planning, including the Agent
  Passport posture consumer contract for SpecSpace UI surfaces, a report-only
  runtime enforcement evidence contract, the runtime enforcement evidence index
  consumer contract, and runtime-smoke declarations including the supervisor
  executor adapter invocation-boundary check
- `tools/agent_passports/*.passport.yaml`: repository-local draft Agent
  Passport documents used by `make agent-passports` for report-only CLI
  validation; these are schema/content validation fixtures, not trusted signed
  runtime credentials. The public static publish requires successful
  report-only Agent Passport CLI validation and installs the CLI from the
  `0al-spec/agent-passport` release before `make publish-bundle`; local draft
  bundles must explicitly opt out if they are built without the CLI
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
- `tools/branch_rewrite_preview_policy.json`: declarative contract for
  branch rewrite previews, including selection limits, preview statuses,
  candidate classes, suggested actions, and viewer fields
- `tools/implementation_delta_policy.json`: declarative contract for
  Implementation Work delta snapshots and work indexes, including baseline,
  target, delta, readiness, and derived-only mutation boundaries
- `tools/specgraph_vocabulary.json`: shared machine-readable vocabulary layer
  for canonical terms, aliases, deprecated aliases, and cross-artifact
  ontology families
- `tools/ontology_term_binding_policy.json`: declarative review-first contract
  for binding generated terms to accepted ontology entities or emitting
  `ontology_gap` records, without granting practical ontology observations or
  SpecGraph topology edges semantic authority
- `tools/ontology_term_binding_gate.py`: executable review-first checker for
  generated artifact term bindings, including optional strict mode for local
  experiments that should fail on future hard-gate findings
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
  - model: `gpt-5.5`
  - reasoning effort: `medium`
  - timeout: `420s`
- `materialize`
  - model: `gpt-5.5`
  - reasoning effort: `medium`
  - timeout: `720s`
  - auto-selected when run authority includes sanctioned child materialization
- `fast`
  - model: `gpt-5.5`
  - reasoning effort: `medium`
  - timeout: `420s` for heuristic ordinary refinement runs

Timeout rule:

- `supervisor` uses the larger of the profile's base timeout and the minimum timeout floor implied by
  the profile's reasoning effort
- this keeps heavier reasoning modes from inheriting the same timeout budget as lighter reasoning modes
- `medium` and `xhigh` runs retain progress/quiet grace windows after the base timeout so a still-advancing
  child executor is not killed immediately at the timeout boundary
- `fast` means heuristic profile selection, not low-quality reasoning; it still uses the shared `medium`
  reasoning default with a bounded but non-trivial timeout so useful split signals are not lost to
  premature executor termination

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

- `--child-model` sets an explicit model for the nested codex run when an operator intentionally
  compares a bounded run against the default profile model.
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
python tools/validate_architecture_style.py
python tools/architecture_metrics.py
```

The spec YAML formatter and linter default to `specs/nodes/*.yaml`. The formatter
rewrites files into the repository's canonical YAML style; the linter enforces
syntax, rejects duplicate keys, and fails when a file has drifted from canonical
formatting. Canonical spec nodes now require top-level `created_at` and
`updated_at` timestamps immediately after `kind`.

To backfill those fields onto existing specs from git history with filesystem fallback:

```bash
python tools/spec_backfill_timestamps.py
```

`python_quality.py` mirrors the blocking `python-quality` CI job by running:

- `ruff check .`
- `ruff format --check .`
- `python tools/spec_yaml_lint.py`
- `python tools/validate_architecture_style.py`

The same project-wide gate is also installed in `.pre-commit-config.yaml` as the
`python-quality` hook.

`validate_architecture_style.py` is intentionally baseline-friendly. It does not
try to grade the legacy `tools/supervisor.py` monolith; it applies architecture
style rules to new package code under `src/specgraph/supervisor/`. The gate
forbids procedural class suffixes, `@staticmethod`, setter-style methods,
`dict[str, Any]` in package signatures, forbidden dependencies back into
legacy tools/tests/docs, and import-time I/O or subprocess work.
The CLI prints the checked file count so a zero-file baseline pass is visible in
CI logs.

`architecture_metrics.py` is report-only and prints JSON for trend tracking. It
includes `architecture_gate.findings_total` and code-shape metrics for both the
new supervisor package scope and the legacy supervisor baseline: files, lines,
classes, functions, top-level functions, function length thresholds, parameter
count thresholds, `dict[str, Any]` signatures, `isinstance` calls, static
methods, setters, syntax errors, and procedural class suffixes.

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
## Durable product workspace binding evidence

Proposal 0211 adds digest-bound `workspace_binding_evidence` to
`runs/product_workspace_initialization.json`. Platform can use it as
producer-owned initialization evidence while retaining ownership of artifact
routing, state namespaces, execution roots, and repository operations.
