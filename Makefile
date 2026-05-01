PYTHON ?= python3
SUPERVISOR ?= tools/supervisor.py
PYTEST ?= $(PYTHON) -m pytest

.PHONY: help
help:
	@printf '%s\n' \
		'SpecGraph shortcuts:' \
		'  make viewer-surfaces          Refresh common viewer-facing JSON surfaces' \
		'  make dashboard                Refresh graph dashboard JSON only' \
		'  make backlog                  Refresh graph backlog projection JSON only' \
		'  make next-move                Refresh advisory graph next-moves JSON only' \
		'  make proposal-spec-trace      Refresh proposal-to-spec trace index JSON' \
		'  make metrics-source-promotion Refresh Metrics source promotion candidates JSON' \
		'  make metric-packs             Refresh metric pack index JSON only' \
		'  make metric-pack-drift        Refresh metric pack registry drift JSON only' \
		'  make metric-pack-adapters     Refresh metric pack adapter index JSON only' \
		'  make metric-pack-runs         Refresh metric pack run snapshot JSON only' \
		'  make conversation-memory      Refresh conversation memory index JSON only' \
		'  make conversation-memory-map  Refresh conversation memory map JSON only' \
		'  make conversation-memory-pressure Refresh conversation memory promotion pressure JSON' \
		'  make implementation-work      Refresh latest implementation work index' \
		'  make review-feedback          Refresh review feedback index' \
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

.PHONY: proposal-spec-trace
proposal-spec-trace:
	@$(PYTHON) $(SUPERVISOR) --build-proposal-spec-trace-index

.PHONY: metrics-source-promotion
metrics-source-promotion:
	@$(PYTHON) $(SUPERVISOR) --build-metrics-source-promotion-index

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

.PHONY: conversation-memory
conversation-memory:
	@$(PYTHON) $(SUPERVISOR) --build-conversation-memory-index

.PHONY: conversation-memory-map
conversation-memory-map:
	@$(PYTHON) $(SUPERVISOR) --build-conversation-memory-map

.PHONY: conversation-memory-pressure
conversation-memory-pressure:
	@$(PYTHON) $(SUPERVISOR) --build-conversation-memory-promotion-pressure

.PHONY: implementation-work
implementation-work:
	@$(PYTHON) $(SUPERVISOR) --build-implementation-work-index

.PHONY: review-feedback
review-feedback:
	@$(PYTHON) $(SUPERVISOR) --build-review-feedback-index

.PHONY: test
test:
	@$(PYTEST) -q

.PHONY: test-supervisor
test-supervisor:
	@$(PYTEST) -q tests/test_supervisor.py
