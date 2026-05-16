PYTHON ?= python3
SUPERVISOR ?= tools/supervisor.py
PYTEST ?= $(PYTHON) -m pytest
IMPLEMENTATION_TARGET_SCOPE_KIND ?= active_subtree
IMPLEMENTATION_TARGET_SPEC_IDS ?= SG-SPEC-0001
IMPLEMENTATION_OPERATOR_INTENT ?= Build publishable implementation work surface for SpecSpace static artifact consumers.

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
		'  make external-consumers       Refresh external consumer bridge JSON' \
		'  make external-handoffs        Refresh external consumer handoff JSON' \
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
		'  make implementation-delta     Refresh latest implementation delta snapshot' \
		'  make implementation-work      Refresh latest implementation work index' \
		'  make review-feedback          Refresh review feedback index' \
		'  make publish-bundle           Build static specs/ + runs/ publish bundle' \
		'  make test                     Run full Python test suite quietly' \
		'  make test-supervisor          Run supervisor tests quietly'

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

.PHONY: external-consumers
external-consumers:
	@$(PYTHON) $(SUPERVISOR) --build-external-consumer-overlay

.PHONY: external-handoffs
external-handoffs:
	@$(PYTHON) $(SUPERVISOR) --build-external-consumer-handoffs

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

.PHONY: implementation-delta
implementation-delta:
	@$(PYTHON) $(SUPERVISOR) --build-implementation-delta-snapshot --target-scope-kind "$(IMPLEMENTATION_TARGET_SCOPE_KIND)" --target-spec-ids "$(IMPLEMENTATION_TARGET_SPEC_IDS)" --operator-intent "$(IMPLEMENTATION_OPERATOR_INTENT)"

.PHONY: implementation-work
implementation-work:
	@$(PYTHON) $(SUPERVISOR) --build-implementation-work-index

.PHONY: review-feedback
review-feedback:
	@$(PYTHON) $(SUPERVISOR) --build-review-feedback-index

.PHONY: publish-bundle
publish-bundle:
	@$(PYTHON) tools/build_static_artifact_bundle.py --refresh-viewer-surfaces

.PHONY: test
test:
	@$(PYTEST) -q

.PHONY: test-supervisor
test-supervisor:
	@$(PYTEST) -q tests/test_supervisor.py
