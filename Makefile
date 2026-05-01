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
		'  make metrics-source-promotion Refresh Metrics source promotion candidates JSON' \
		'  make metric-packs             Refresh metric pack index JSON only' \
		'  make conversation-memory      Refresh conversation memory index JSON only' \
		'  make conversation-memory-map  Refresh conversation memory map JSON only' \
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

.PHONY: metrics-source-promotion
metrics-source-promotion:
	@$(PYTHON) $(SUPERVISOR) --build-metrics-source-promotion-index

.PHONY: metric-packs
metric-packs:
	@$(PYTHON) $(SUPERVISOR) --build-metric-pack-index

.PHONY: conversation-memory
conversation-memory:
	@$(PYTHON) $(SUPERVISOR) --build-conversation-memory-index

.PHONY: conversation-memory-map
conversation-memory-map:
	@$(PYTHON) $(SUPERVISOR) --build-conversation-memory-map

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
