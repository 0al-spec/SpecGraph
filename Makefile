PYTHON ?= python3
SUPERVISOR ?= tools/supervisor.py
PYTEST ?= $(PYTHON) -m pytest
CHECK_PYTHON ?= tools/check_python_version.py
PUBLISH_BUNDLE_FLAGS ?= --allow-unverified-agent-passports
PRODUCT_WORKSPACE_PROJECT_ID ?=
PRODUCT_WORKSPACE_DISPLAY_NAME ?=
PRODUCT_WORKSPACE_ROOT ?=
PRODUCT_WORKSPACE_ROOT_INTENT ?=
IMPLEMENTATION_TARGET_SCOPE_KIND ?= active_subtree
IMPLEMENTATION_TARGET_SPEC_IDS ?= SG-SPEC-0001
IMPLEMENTATION_OPERATOR_INTENT ?= Build publishable implementation work surface for SpecSpace static artifact consumers.
SUPERVISOR_RUN_PATH ?=
EXECUTOR_FOLLOWUP_DECISION ?= needs_more_evidence
EXECUTOR_FOLLOWUP_REVIEWER ?= local_operator
EXECUTOR_FOLLOWUP_RATIONALE ?=
ONTOLOGY_TERM_BINDING_ARTIFACT ?= tests/fixtures/ontology_term_binding/generated_artifact_review_required.json
ONTOLOGY_TERM_BINDING_GATE_OUTPUT ?= runs/ontology_term_binding_gate_report.json

.DEFAULT_GOAL := help

PYTHON_TARGETS := viewer-surfaces dashboard backlog next-move spec-activity graph-diagnostics \
	proposal-spec-trace proposal-tracking proposal-tracking-gate external-consumers external-handoffs \
	external-consumer-evidence ontology-imports ontology-imports-public \
	ontology-term-binding-gate \
	proposal-work-claims proposal-work-claims-gate proposal-id \
	metrics-delivery metrics-feedback metrics-source-promotion metric-signals metric-thresholds \
	metric-packs metric-pack-drift metric-pack-adapters metric-pack-runs metric-pricing model-usage \
	conversation-memory conversation-memory-map conversation-memory-pressure pre-spec-semantics \
	implementation-delta implementation-work supervisor-evidence-packet supervisor-stalled-run-salvage \
	factory-architecture swift-typed-tooling project-environment init-product-workspace review-feedback \
	executor-adapters executor-readiness executor-smoke executor-task-smoke \
	executor-report-contract executor-report-smoke executor-report-review-packet \
	executor-analysis-report-review-outcome executor-analysis-report-followup-packet \
	executor-followup-decision executor-proposal-draft-request executor-followup-proposal-draft-candidate \
	executor-proposal-draft-candidate \
	executor-proposal-promotion-packet \
	executor-proposal-source-materialize executor-public-proposal-doc-materialize \
	agent-passports agent-runtime-evidence docc-sync publish-bundle test test-supervisor

$(PYTHON_TARGETS): check-python

.PHONY: help
help:
	@printf '%s\n' \
		'SpecGraph shortcuts:' \
		'  make viewer-surfaces          Refresh common viewer-facing JSON surfaces' \
		'  make dashboard                Refresh graph dashboard JSON only' \
		'  make backlog                  Refresh graph backlog projection JSON only' \
		'  make next-move                Refresh advisory graph next-moves JSON only' \
		'  make spec-activity            Refresh spec activity feed JSON only' \
		'  make graph-diagnostics        Print compact graph diagnostics from runs JSON' \
		'  make proposal-spec-trace      Refresh proposal-to-spec trace index JSON' \
		'  make proposal-tracking        Refresh report-only proposal tracking JSON' \
		'  make proposal-tracking-gate   Fail on proposal docs without tracking' \
		'  make proposal-work-claims     Refresh proposal work claim report JSON' \
		'  make proposal-work-claims-gate Fail on stale or duplicate proposal work claims' \
		'  make proposal-id              Print the next deterministic proposal id' \
		'  make external-consumers       Refresh external consumer bridge JSON' \
		'  make external-handoffs        Refresh external consumer handoff JSON' \
			'  make external-consumer-evidence Refresh external consumer evidence JSON' \
			'  make ontology-imports          Refresh ontology import and semantic-control surfaces' \
			'  make ontology-imports-public   Refresh public-safe ontology review placeholders' \
			'  make ontology-term-binding-gate ONTOLOGY_TERM_BINDING_ARTIFACT=<json>' \
		'  make metrics-delivery         Refresh Metrics delivery workflow JSON' \
		'  make metrics-feedback         Refresh Metrics feedback JSON' \
		'  make metrics-source-promotion Refresh Metrics source promotion candidates JSON' \
		'  make metric-signals           Refresh metric signals JSON only' \
		'  make metric-thresholds        Refresh metric threshold proposals JSON only' \
		'  make metric-packs             Refresh metric pack index JSON only' \
		'  make metric-pack-drift        Refresh metric pack registry drift JSON only' \
		'  make metric-pack-adapters     Refresh metric pack adapter index JSON only' \
		'  make metric-pack-runs         Refresh metric pack run snapshot JSON only' \
		'  make metric-pricing           Refresh pricing provenance + model usage JSON' \
		'  make model-usage              Refresh model usage telemetry JSON only' \
		'  make conversation-memory      Refresh conversation memory index JSON only' \
		'  make conversation-memory-map  Refresh conversation memory map JSON only' \
		'  make conversation-memory-pressure Refresh conversation memory promotion pressure JSON' \
		'  make pre-spec-semantics       Refresh pre-spec semantics index JSON only' \
		'  make implementation-delta     Refresh latest implementation delta snapshot' \
		'  make implementation-work      Refresh latest implementation work index' \
		'  make supervisor-evidence-packet SUPERVISOR_RUN_PATH=<run-id-or-path>' \
		'  make factory-architecture     Refresh multi-service factory architecture index' \
		'  make swift-typed-tooling      Refresh Swift typed tooling lane index' \
		'  make project-environment      Refresh project environment governance profile JSON' \
			'  make init-product-workspace PRODUCT_WORKSPACE_PROJECT_ID=<id> PRODUCT_WORKSPACE_ROOT=<path>' \
			'  make review-feedback          Refresh review feedback index' \
			'  make executor-adapters        Refresh supervisor executor adapter index' \
			'  make executor-readiness       Refresh local operator executor readiness JSON' \
			'  make executor-smoke           Run local operator executor probe smoke' \
			'  make executor-task-smoke      Run local operator bounded executor task smoke' \
			'  make executor-report-contract Refresh local operator executor report contract JSON' \
			'  make executor-report-smoke    Run local operator bounded executor report smoke' \
			'  make executor-report-review-packet Build local operator executor report review packet' \
			'  make executor-analysis-report-review-outcome Build local analysis report review outcome' \
			'  make executor-analysis-report-followup-packet Build local analysis report follow-up packet' \
			'  make executor-followup-decision EXECUTOR_FOLLOWUP_DECISION=<accept|reject|defer|needs_more_evidence>' \
			'  make executor-proposal-draft-request Build local proposal draft request from accepted follow-up' \
			'  make executor-followup-proposal-draft-candidate Build follow-up proposal draft candidate' \
			'  make executor-proposal-draft-candidate Build local operator proposal draft candidate' \
			'  make executor-proposal-promotion-packet Build local operator proposal promotion packet' \
			'  make executor-proposal-source-materialize Materialize local proposal source draft' \
			'  make executor-public-proposal-doc-materialize Materialize local public proposal doc' \
			'  make agent-passports          Refresh Agent Passport derived surfaces' \
			'  make agent-runtime-evidence   Refresh Agent Passport runtime evidence JSON' \
			'  make check-python             Verify selected Python runtime is supported' \
		'  make docc-sync                Validate DocC mirrors against repository docs' \
		'  make publish-bundle           Build static specs/ + runs/ publish bundle' \
		'  make test                     Run full Python test suite quietly' \
		'  make test-supervisor          Run supervisor tests quietly'

.PHONY: check-python
check-python:
	@$(PYTHON) $(CHECK_PYTHON)

.PHONY: viewer-surfaces
viewer-surfaces:
	@$(PYTHON) $(SUPERVISOR) --build-viewer-surfaces

.PHONY: dashboard
dashboard:
	@$(PYTHON) $(SUPERVISOR) --build-graph-dashboard

.PHONY: backlog
backlog:
	@$(PYTHON) $(SUPERVISOR) --build-graph-backlog-projection

.PHONY: next-move
next-move:
	@$(PYTHON) $(SUPERVISOR) --build-graph-next-moves

.PHONY: spec-activity
spec-activity:
	@$(PYTHON) $(SUPERVISOR) --build-spec-activity-feed

.PHONY: graph-diagnostics
graph-diagnostics:
	@$(PYTHON) tools/graph_diagnostics.py --format text

.PHONY: proposal-spec-trace
proposal-spec-trace:
	@$(PYTHON) $(SUPERVISOR) --build-proposal-spec-trace-index

.PHONY: proposal-tracking
proposal-tracking:
	@$(PYTHON) $(SUPERVISOR) --build-proposal-tracking-report

.PHONY: proposal-tracking-gate
proposal-tracking-gate:
	@$(PYTHON) $(SUPERVISOR) --check-proposal-tracking-gate

.PHONY: proposal-work-claims
proposal-work-claims:
	@$(PYTHON) $(SUPERVISOR) --build-proposal-work-claim-report

.PHONY: proposal-work-claims-gate
proposal-work-claims-gate:
	@$(PYTHON) $(SUPERVISOR) --check-proposal-work-claim-gate

.PHONY: proposal-id
proposal-id:
	@$(PYTHON) $(SUPERVISOR) --allocate-proposal-id

.PHONY: external-consumers
external-consumers:
	@$(PYTHON) $(SUPERVISOR) --build-external-consumer-overlay

.PHONY: external-handoffs
external-handoffs:
	@$(PYTHON) $(SUPERVISOR) --build-external-consumer-handoffs

.PHONY: external-consumer-evidence
external-consumer-evidence:
	@$(PYTHON) $(SUPERVISOR) --build-external-consumer-evidence

.PHONY: ontology-imports
ontology-imports:
	@$(PYTHON) tools/ontology_imports.py --write

.PHONY: ontology-imports-public
ontology-imports-public:
	@$(PYTHON) tools/ontology_imports.py --write-public-placeholder

.PHONY: ontology-term-binding-gate
ontology-term-binding-gate:
	@$(PYTHON) tools/ontology_term_binding_gate.py --artifact "$(ONTOLOGY_TERM_BINDING_ARTIFACT)" --output "$(ONTOLOGY_TERM_BINDING_GATE_OUTPUT)"

.PHONY: metrics-delivery
metrics-delivery:
	@$(PYTHON) $(SUPERVISOR) --build-metrics-delivery-workflow

.PHONY: metrics-feedback
metrics-feedback:
	@$(PYTHON) $(SUPERVISOR) --build-metrics-feedback-index

.PHONY: metrics-source-promotion
metrics-source-promotion:
	@$(PYTHON) $(SUPERVISOR) --build-metrics-source-promotion-index

.PHONY: metric-signals
metric-signals:
	@$(PYTHON) $(SUPERVISOR) --build-metric-signal-index

.PHONY: metric-thresholds
metric-thresholds:
	@$(PYTHON) $(SUPERVISOR) --build-metric-threshold-proposals

.PHONY: metric-packs
metric-packs:
	@$(PYTHON) $(SUPERVISOR) --build-metric-pack-index

.PHONY: metric-pack-drift
metric-pack-drift:
	@$(PYTHON) $(SUPERVISOR) --build-metric-pack-registry-drift

.PHONY: metric-pack-adapters
metric-pack-adapters:
	@$(PYTHON) $(SUPERVISOR) --build-metric-pack-adapter-index

.PHONY: metric-pack-runs
metric-pack-runs:
	@$(PYTHON) $(SUPERVISOR) --build-metric-pack-runs

.PHONY: metric-pricing
metric-pricing:
	@$(PYTHON) $(SUPERVISOR) --build-metric-pricing-provenance

.PHONY: model-usage
model-usage:
	@$(PYTHON) $(SUPERVISOR) --build-model-usage-telemetry

.PHONY: conversation-memory
conversation-memory:
	@$(PYTHON) $(SUPERVISOR) --build-conversation-memory-index

.PHONY: conversation-memory-map
conversation-memory-map:
	@$(PYTHON) $(SUPERVISOR) --build-conversation-memory-map

.PHONY: conversation-memory-pressure
conversation-memory-pressure:
	@$(PYTHON) $(SUPERVISOR) --build-conversation-memory-promotion-pressure

.PHONY: pre-spec-semantics
pre-spec-semantics:
	@$(PYTHON) $(SUPERVISOR) --build-pre-spec-semantics-index

.PHONY: implementation-delta
implementation-delta:
	@$(PYTHON) $(SUPERVISOR) --build-implementation-delta-snapshot --target-scope-kind "$(IMPLEMENTATION_TARGET_SCOPE_KIND)" --target-spec-ids "$(IMPLEMENTATION_TARGET_SPEC_IDS)" --operator-intent "$(IMPLEMENTATION_OPERATOR_INTENT)"

.PHONY: implementation-work
implementation-work:
	@$(PYTHON) $(SUPERVISOR) --build-implementation-work-index

.PHONY: supervisor-evidence-packet
supervisor-evidence-packet:
	@test -n "$(SUPERVISOR_RUN_PATH)" || (echo 'SUPERVISOR_RUN_PATH is required' >&2; exit 2)
	@$(PYTHON) $(SUPERVISOR) --build-supervisor-evidence-packet --supervisor-run-path "$(SUPERVISOR_RUN_PATH)"

.PHONY: supervisor-stalled-run-salvage
supervisor-stalled-run-salvage:
	@test -n "$(TARGET_SPEC)" || (echo 'TARGET_SPEC is required' >&2; exit 2)
	@test -n "$(SALVAGE_WORKTREE_PATH)" || (echo 'SALVAGE_WORKTREE_PATH is required' >&2; exit 2)
	@$(PYTHON) $(SUPERVISOR) --build-supervisor-stalled-run-salvage --target-spec "$(TARGET_SPEC)" --salvage-worktree-path "$(SALVAGE_WORKTREE_PATH)" $(if $(SUPERVISOR_RUN_PATH),--supervisor-run-path "$(SUPERVISOR_RUN_PATH)")

.PHONY: factory-architecture
factory-architecture:
	@$(PYTHON) $(SUPERVISOR) --build-factory-architecture-index

.PHONY: swift-typed-tooling
swift-typed-tooling:
	@$(PYTHON) $(SUPERVISOR) --build-swift-typed-tooling-index

.PHONY: project-environment
project-environment:
	@$(PYTHON) $(SUPERVISOR) --build-project-environment

.PHONY: init-product-workspace
init-product-workspace:
	@test -n "$(PRODUCT_WORKSPACE_PROJECT_ID)" || (echo 'PRODUCT_WORKSPACE_PROJECT_ID is required' >&2; exit 2)
	@test -n "$(PRODUCT_WORKSPACE_ROOT)" || (echo 'PRODUCT_WORKSPACE_ROOT is required' >&2; exit 2)
	@$(PYTHON) $(SUPERVISOR) --init-product-workspace --project-id "$(PRODUCT_WORKSPACE_PROJECT_ID)" --workspace-root "$(PRODUCT_WORKSPACE_ROOT)" $(if $(PRODUCT_WORKSPACE_DISPLAY_NAME),--display-name "$(PRODUCT_WORKSPACE_DISPLAY_NAME)") $(if $(PRODUCT_WORKSPACE_ROOT_INTENT),--root-intent "$(PRODUCT_WORKSPACE_ROOT_INTENT)")

.PHONY: review-feedback
review-feedback:
	@$(PYTHON) $(SUPERVISOR) --build-review-feedback-index

.PHONY: executor-adapters
executor-adapters:
	@$(PYTHON) $(SUPERVISOR) --build-supervisor-executor-adapter-index

.PHONY: executor-readiness
executor-readiness:
	@$(PYTHON) $(SUPERVISOR) --build-local-operator-executor-readiness

.PHONY: executor-smoke
executor-smoke:
	@$(PYTHON) $(SUPERVISOR) --build-local-operator-executor-smoke

.PHONY: executor-task-smoke
executor-task-smoke:
	@$(PYTHON) $(SUPERVISOR) --build-local-operator-executor-task-smoke

.PHONY: executor-report-contract
executor-report-contract:
	@$(PYTHON) $(SUPERVISOR) --build-local-operator-executor-report-contract

.PHONY: executor-report-smoke
executor-report-smoke:
	@$(PYTHON) $(SUPERVISOR) --build-local-operator-executor-report-smoke

.PHONY: executor-report-review-packet
executor-report-review-packet:
	@$(PYTHON) $(SUPERVISOR) --build-local-operator-executor-report-review-packet

.PHONY: executor-analysis-report-review-outcome
executor-analysis-report-review-outcome:
	@$(PYTHON) $(SUPERVISOR) --build-local-operator-executor-analysis-report-review-outcome

.PHONY: executor-analysis-report-followup-packet
executor-analysis-report-followup-packet:
	@$(PYTHON) $(SUPERVISOR) --build-local-operator-executor-analysis-report-followup-packet

.PHONY: executor-followup-decision
executor-followup-decision:
	@$(PYTHON) $(SUPERVISOR) --build-local-operator-executor-analysis-report-followup-decision --executor-followup-decision "$(EXECUTOR_FOLLOWUP_DECISION)" --executor-followup-reviewer "$(EXECUTOR_FOLLOWUP_REVIEWER)" $(if $(EXECUTOR_FOLLOWUP_RATIONALE),--executor-followup-rationale "$(EXECUTOR_FOLLOWUP_RATIONALE)")

.PHONY: executor-proposal-draft-request
executor-proposal-draft-request:
	@$(PYTHON) $(SUPERVISOR) --build-local-operator-executor-proposal-draft-request

.PHONY: executor-followup-proposal-draft-candidate
executor-followup-proposal-draft-candidate:
	@$(PYTHON) $(SUPERVISOR) --build-local-operator-executor-followup-proposal-draft-candidate

.PHONY: executor-proposal-draft-candidate
executor-proposal-draft-candidate:
	@$(PYTHON) $(SUPERVISOR) --build-local-operator-executor-proposal-draft-candidate

.PHONY: executor-proposal-promotion-packet
executor-proposal-promotion-packet:
	@$(PYTHON) $(SUPERVISOR) --build-local-operator-executor-proposal-promotion-packet

.PHONY: executor-proposal-source-materialize
executor-proposal-source-materialize:
	@$(PYTHON) $(SUPERVISOR) --build-local-operator-executor-proposal-source-materialization

.PHONY: executor-public-proposal-doc-materialize
executor-public-proposal-doc-materialize:
	@$(PYTHON) $(SUPERVISOR) --build-local-operator-executor-public-proposal-doc-materialization

.PHONY: agent-passports
agent-passports:
	@$(PYTHON) $(SUPERVISOR) --build-agent-passport-derived-surfaces

.PHONY: agent-runtime-evidence
agent-runtime-evidence:
	@$(PYTHON) $(SUPERVISOR) --build-agent-runtime-enforcement-evidence

.PHONY: docc-sync
docc-sync:
	@$(PYTHON) tools/validate_docc_sync.py

.PHONY: publish-bundle
publish-bundle:
	@$(PYTHON) tools/build_static_artifact_bundle.py --refresh-publish-surfaces $(PUBLISH_BUNDLE_FLAGS)

.PHONY: test
test:
	@$(PYTEST) -q

.PHONY: test-supervisor
test-supervisor:
	@$(PYTEST) -q tests/test_supervisor.py
