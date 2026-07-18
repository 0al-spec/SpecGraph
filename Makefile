LOCAL_PYTHON := .venv/bin/python
PYTHON ?= $(if $(wildcard $(LOCAL_PYTHON)),$(LOCAL_PYTHON),python3)
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
ONTOLOGY_GAP_REVIEW_GENERATED_ARTIFACT ?=
ONTOLOGY_GAP_REVIEW_OUTPUT ?= runs/ontology_gap_review_workflow.json
LEGACY_SPEC_ONTOLOGY_BACKFILL_PLAN_OUTPUT ?= runs/legacy_spec_ontology_backfill_plan.json
LEGACY_SPEC_ONTOLOGY_BACKFILL_PLAN_VALIDATION_REPORT ?=
LEGACY_SPEC_ONTOLOGY_BACKFILL_PLAN_GAP_REVIEW ?=
ONTOLOGY_OWNER_DECISION_IMPORT_V2_OUTPUT ?= runs/ontology_owner_decision_import_v2.json
ONTOLOGY_OWNER_DECISION_IMPORT_V2_DECISION_PREVIEW ?= runs/ontology_decision_import_preview.json
ONTOLOGY_OWNER_DECISION_IMPORT_V2_CLOSED_LOOP ?= runs/ontology_closed_loop_evidence.json
ONTOLOGY_OWNER_DECISION_IMPORT_V2_GAP_REVIEW ?=
ONTOLOGY_OWNER_DECISION_IMPORT_V2_VALIDATION_REPORT ?=
ONTOLOGY_OWNER_DECISION_IMPORT_V2_WRITE_GATE_REPORT ?= runs/specauthor_ontology_write_gate_report.json
SPECAUTHOR_GENERATED_ARTIFACT_CONTRACT_ARTIFACT ?= tests/fixtures/specauthor_generated_artifact_contract/generated_spec_ready.json
SPECAUTHOR_GENERATED_ARTIFACT_CONTRACT_OUTPUT ?= runs/specauthor_generated_artifact_contract_report.json
SPECAUTHOR_ONTOLOGY_WRITE_GATE_ARTIFACT ?= tests/fixtures/specauthor_ontology_write_gate/generated_spec_review_required.json
SPECAUTHOR_ONTOLOGY_WRITE_GATE_OUTPUT ?= runs/specauthor_ontology_write_gate_report.json
SPECAUTHOR_INVOCATION_ARTIFACT_CONTRACT_ARTIFACT ?= tests/fixtures/specauthor_invocation_artifact_contract/invocation_ready.json
SPECAUTHOR_INVOCATION_ARTIFACT_CONTRACT_OUTPUT ?= runs/specauthor_invocation_artifact_contract_report.json
SPECAUTHOR_AUTHORING_FLOW_CONTEXT ?= tests/fixtures/specauthor_authoring_flow/active_context_ready.json
SPECAUTHOR_AUTHORING_FLOW_GENERATED_ARTIFACT ?= tests/fixtures/specauthor_generated_artifact_contract/generated_spec_ready.json
SPECAUTHOR_AUTHORING_FLOW_INVOCATION_OUTPUT ?= runs/specauthor_invocation_artifact.json
SPECAUTHOR_AUTHORING_FLOW_CONTRACT_OUTPUT ?= runs/specauthor_invocation_artifact_contract_report.json
SPECAUTHOR_AUTHORING_FLOW_REPORT_OUTPUT ?= runs/specauthor_authoring_flow_report.json
USER_IDEA_INTAKE_INTERVIEW_INPUT ?=
USER_IDEA_INTAKE_INTERVIEW_IDEA_SUMMARY ?=
USER_IDEA_INTAKE_INTERVIEW_CANDIDATE_ID ?=
USER_IDEA_INTAKE_INTERVIEW_DISPLAY_NAME ?=
USER_IDEA_INTAKE_INTERVIEW_PUBLIC_ROUTE ?=
USER_IDEA_INTAKE_INTERVIEW_CLARIFICATION_REQUESTS ?=
USER_IDEA_INTAKE_INTERVIEW_CLARIFICATION_ANSWERS ?=
USER_IDEA_RAW_INPUT_OUTPUT_DEFAULT := runs/local_operator_user_idea_raw_input.json
USER_IDEA_RAW_INPUT_OUTPUT ?= $(USER_IDEA_RAW_INPUT_OUTPUT_DEFAULT)
USER_IDEA_INTAKE_INTERVIEW_REPORT_OUTPUT ?= runs/user_idea_intake_interview_report.json
REAL_IDEA_INTAKE_REFRESH ?=
USER_IDEA_INTAKE_INTERVIEW_INPUT_ARG := $(if $(strip $(USER_IDEA_INTAKE_INTERVIEW_INPUT)),--input "$(USER_IDEA_INTAKE_INTERVIEW_INPUT)",)
USER_IDEA_INTAKE_INTERVIEW_IDEA_SUMMARY_ARG := $(if $(strip $(USER_IDEA_INTAKE_INTERVIEW_IDEA_SUMMARY)),--idea-summary "$(USER_IDEA_INTAKE_INTERVIEW_IDEA_SUMMARY)",)
USER_IDEA_INTAKE_INTERVIEW_CANDIDATE_ID_ARG := $(if $(strip $(USER_IDEA_INTAKE_INTERVIEW_CANDIDATE_ID)),--candidate-id "$(USER_IDEA_INTAKE_INTERVIEW_CANDIDATE_ID)",)
USER_IDEA_INTAKE_INTERVIEW_DISPLAY_NAME_ARG := $(if $(strip $(USER_IDEA_INTAKE_INTERVIEW_DISPLAY_NAME)),--display-name "$(USER_IDEA_INTAKE_INTERVIEW_DISPLAY_NAME)",)
USER_IDEA_INTAKE_INTERVIEW_PUBLIC_ROUTE_ARG := $(if $(strip $(USER_IDEA_INTAKE_INTERVIEW_PUBLIC_ROUTE)),--public-route "$(USER_IDEA_INTAKE_INTERVIEW_PUBLIC_ROUTE)",)
USER_IDEA_INTAKE_INTERVIEW_CLARIFICATION_REQUESTS_ARG := $(if $(strip $(USER_IDEA_INTAKE_INTERVIEW_CLARIFICATION_REQUESTS)),--clarification-requests "$(USER_IDEA_INTAKE_INTERVIEW_CLARIFICATION_REQUESTS)",)
USER_IDEA_INTAKE_INTERVIEW_CLARIFICATION_ANSWERS_ARG := $(if $(strip $(USER_IDEA_INTAKE_INTERVIEW_CLARIFICATION_ANSWERS)),--clarification-answers "$(USER_IDEA_INTAKE_INTERVIEW_CLARIFICATION_ANSWERS)",)
USER_IDEA_INTAKE_SESSION_INPUT ?= tests/fixtures/user_idea_intake_session/raw_idea_ready.json
USER_IDEA_INTAKE_SESSION_OUTPUT_DEFAULT := runs/user_idea_intake_session.json
USER_IDEA_INTAKE_SESSION_OUTPUT ?= $(USER_IDEA_INTAKE_SESSION_OUTPUT_DEFAULT)
USER_IDEA_INTAKE_SESSION_SOURCE_OUTPUT_DEFAULT := runs/user_idea_intake_source.json
USER_IDEA_INTAKE_SESSION_SOURCE_OUTPUT ?= $(USER_IDEA_INTAKE_SESSION_SOURCE_OUTPUT_DEFAULT)
INTAKE_SESSION_CANDIDATE_SOURCE_INPUT ?= $(USER_IDEA_INTAKE_SESSION_OUTPUT)
INTAKE_SESSION_CANDIDATE_SOURCE_OUTPUT ?= $(USER_IDEA_INTAKE_SESSION_SOURCE_OUTPUT)
INTAKE_SESSION_CANDIDATE_SOURCE_REPORT_OUTPUT ?= runs/intake_session_candidate_source_report.json
INTAKE_SESSION_CANDIDATE_SOURCE_STRICT ?=
INTAKE_SESSION_CANDIDATE_SOURCE_STRICT_ARG := $(if $(filter 1 true yes,$(strip $(INTAKE_SESSION_CANDIDATE_SOURCE_STRICT))),--strict,)
INTAKE_SESSION_CANDIDATE_SOURCE_FALLBACK ?=
INTAKE_SESSION_CANDIDATE_SOURCE_FALLBACK_ARG := $(if $(strip $(INTAKE_SESSION_CANDIDATE_SOURCE_FALLBACK)),--fallback-intake-session "$(INTAKE_SESSION_CANDIDATE_SOURCE_FALLBACK)",)
IDEA_INTAKE_CLARIFICATION_REQUESTS_OUTPUT ?= runs/idea_intake_clarification_requests.json
IDEA_INTAKE_CLARIFICATION_ANSWERS_INPUT ?=
IDEA_INTAKE_CLARIFICATION_ANSWERS_OUTPUT ?= runs/idea_intake_clarification_answers.json
IDEA_INTAKE_ANSWER_RERUN_INPUT_OUTPUT ?= runs/idea_intake_answer_rerun_input.json
CLARIFIED_USER_IDEA_RAW_INPUT_OUTPUT ?= runs/local_operator_clarified_user_idea_raw_input.json
CLARIFIED_USER_IDEA_INTAKE_SESSION_OUTPUT ?= runs/clarified_user_idea_intake_session.json
CLARIFIED_USER_IDEA_INTAKE_SOURCE_OUTPUT ?= runs/clarified_user_idea_intake_source.json
IDEA_INTAKE_CLARIFICATION_RERUN_REPORT_OUTPUT ?= runs/idea_intake_clarification_rerun_report.json
REAL_IDEA_INTAKE_READY_SESSION_INPUT = $(if $(wildcard $(CLARIFIED_USER_IDEA_INTAKE_SESSION_OUTPUT)),$(CLARIFIED_USER_IDEA_INTAKE_SESSION_OUTPUT),$(USER_IDEA_INTAKE_SESSION_OUTPUT))
USER_IDEA_INTAKE_SOURCE ?= tests/fixtures/user_idea_intake/source_ready.json
USER_IDEA_EVENT_STORMING_SEED_OUTPUT_DEFAULT := runs/idea_event_storming_seed.json
USER_IDEA_EVENT_STORMING_SEED_OUTPUT ?= $(USER_IDEA_EVENT_STORMING_SEED_OUTPUT_DEFAULT)
REAL_IDEA_SMOKE_RUN_DIR ?= runs/real_idea_smoke
REAL_IDEA_SMOKE_SUMMARY_OUTPUT ?= $(REAL_IDEA_SMOKE_RUN_DIR)/real_idea_smoke_summary.json
REAL_IDEA_SMOKE_DEPTH_REPORT_OUTPUT ?= $(REAL_IDEA_SMOKE_RUN_DIR)/product_demo_depth_report.json
REAL_IDEA_SMOKE_REFRESH ?= 1
REAL_IDEA_SMOKE_REFRESH_ARG := $(if $(filter 0 false no,$(strip $(REAL_IDEA_SMOKE_REFRESH))),--preserve-existing,)
REAL_IDEA_SMOKE_CLARIFICATION_ANSWERS_INPUT ?= $(IDEA_INTAKE_CLARIFICATION_ANSWERS_INPUT)
REAL_IDEA_SMOKE_CLARIFICATION_ANSWERS_ARG := $(if $(strip $(REAL_IDEA_SMOKE_CLARIFICATION_ANSWERS_INPUT)),--clarification-answers-input "$(REAL_IDEA_SMOKE_CLARIFICATION_ANSWERS_INPUT)",)
REAL_IDEA_SMOKE_MATURITY_ABSENT_DIR ?= $(REAL_IDEA_SMOKE_RUN_DIR)/absent-post-approval
REAL_IDEA_SMOKE_CANDIDATE_OVERVIEW_OUTPUT ?= $(REAL_IDEA_SMOKE_RUN_DIR)/candidate_overview.json
REAL_IDEA_ANSWER_AUTHORING_STAGE ?= auto
REAL_IDEA_ANSWER_AUTHORING_REQUESTS ?=
REAL_IDEA_ANSWER_AUTHORING_REQUESTS_ARG := $(if $(strip $(REAL_IDEA_ANSWER_AUTHORING_REQUESTS)),--requests "$(REAL_IDEA_ANSWER_AUTHORING_REQUESTS)",)
REAL_IDEA_ANSWER_TEMPLATE_OUTPUT ?= $(REAL_IDEA_SMOKE_RUN_DIR)/real_idea_answer_template.json
REAL_IDEA_ANSWER_AUTHORING_REPORT_OUTPUT ?= $(REAL_IDEA_SMOKE_RUN_DIR)/real_idea_answer_authoring_report.json
REAL_IDEA_ANSWER_AUTHORING_ANSWERS ?= $(REAL_IDEA_ANSWER_TEMPLATE_OUTPUT)
REAL_IDEA_ANSWER_SET_OUTPUT ?= $(REAL_IDEA_SMOKE_RUN_DIR)/real_idea_answer_set.json
REAL_IDEA_ANSWER_VALIDATED_OUTPUT ?=
REAL_IDEA_ANSWER_VALIDATED_OUTPUT_ARG := $(if $(strip $(REAL_IDEA_ANSWER_VALIDATED_OUTPUT)),--validated-answers-output "$(REAL_IDEA_ANSWER_VALIDATED_OUTPUT)",)
SPECSPACE_REAL_IDEA_ANSWER_STATE ?= $(REAL_IDEA_SMOKE_RUN_DIR)/idea_to_spec_intake_clarification_answers.json
SPECSPACE_REAL_IDEA_ANSWER_REQUESTS ?= $(REAL_IDEA_SMOKE_RUN_DIR)/idea_intake_clarification_requests.json
SPECSPACE_REAL_IDEA_ANSWER_TEMPLATE ?= $(REAL_IDEA_ANSWER_TEMPLATE_OUTPUT)
SPECSPACE_REAL_IDEA_ANSWER_INTAKE_SESSION ?= $(REAL_IDEA_SMOKE_RUN_DIR)/user_idea_intake_session.json
SPECSPACE_REAL_IDEA_ANSWER_IMPORT_PREVIEW_OUTPUT ?= $(REAL_IDEA_SMOKE_RUN_DIR)/specspace_real_idea_answer_import_preview.json
SPECSPACE_REAL_IDEA_VALIDATED_ANSWERS_OUTPUT ?= $(REAL_IDEA_SMOKE_RUN_DIR)/idea_intake_clarification_answers.json
REAL_IDEA_ANSWER_CONTINUATION_REPORT_OUTPUT ?= $(REAL_IDEA_SMOKE_RUN_DIR)/real_idea_answer_continuation_report.json
REAL_IDEA_ANSWER_CONTINUATION_WORKSPACE_ID ?=
SPECSPACE_REAL_IDEA_ENTRY_REQUESTS ?= $(REAL_IDEA_SMOKE_RUN_DIR)/real_idea_entry_requests.json
SPECSPACE_REAL_IDEA_ENTRY_WORKSPACE_ID ?=
SPECSPACE_REAL_IDEA_ENTRY_WORKSPACE_ID_ARG := $(if $(strip $(SPECSPACE_REAL_IDEA_ENTRY_WORKSPACE_ID)),--workspace-id "$(SPECSPACE_REAL_IDEA_ENTRY_WORKSPACE_ID)",)
SPECSPACE_REAL_IDEA_ENTRY_REQUEST_ID ?=
SPECSPACE_REAL_IDEA_ENTRY_REQUEST_ID_ARG := $(if $(strip $(SPECSPACE_REAL_IDEA_ENTRY_REQUEST_ID)),--request-id "$(SPECSPACE_REAL_IDEA_ENTRY_REQUEST_ID)",)
SPECSPACE_REAL_IDEA_ENTRY_IMPORT_PREVIEW_OUTPUT ?= $(REAL_IDEA_SMOKE_RUN_DIR)/specspace_real_idea_entry_request_import_preview.json
REAL_IDEA_ENTRY_INTAKE_REPORT_OUTPUT ?= $(REAL_IDEA_SMOKE_RUN_DIR)/real_idea_entry_request_intake_report.json
IDEA_EVENT_STORMING_INTAKE_SOURCE ?= tests/fixtures/idea_event_storming_intake/idea_ready.json
IDEA_EVENT_STORMING_INTAKE_OUTPUT_DEFAULT := runs/idea_event_storming_intake.json
IDEA_EVENT_STORMING_INTAKE_OUTPUT ?= $(IDEA_EVENT_STORMING_INTAKE_OUTPUT_DEFAULT)
CANDIDATE_SPEC_GRAPH_INTAKE ?= tests/fixtures/candidate_spec_graph/idea_event_storming_intake_ready.json
CANDIDATE_SPEC_GRAPH_SEED ?= tests/fixtures/candidate_spec_graph/candidate_ready.json
CANDIDATE_SPEC_GRAPH_OUTPUT_DEFAULT := runs/candidate_spec_graph.json
CANDIDATE_SPEC_GRAPH_OUTPUT ?= $(CANDIDATE_SPEC_GRAPH_OUTPUT_DEFAULT)
ONTOLOGY_BOUND_CANDIDATE_SEED_INTAKE ?= runs/idea_event_storming_intake.json
ONTOLOGY_BOUND_CANDIDATE_SEED_ONTOLOGY_IR ?= ontology/packages/specgraph-core/generated/ontology.normalized.json
ONTOLOGY_BOUND_CANDIDATE_SEED_OUTPUT_DEFAULT := runs/candidate_spec_graph_seed.json
ONTOLOGY_BOUND_CANDIDATE_SEED_OUTPUT ?= $(ONTOLOGY_BOUND_CANDIDATE_SEED_OUTPUT_DEFAULT)
PRE_SIB_COHERENCE_CANDIDATE_GRAPH ?= tests/fixtures/pre_sib_coherence/candidate_spec_graph_ready.json
PRE_SIB_COHERENCE_OUTPUT_DEFAULT := runs/pre_sib_coherence_report.json
PRE_SIB_COHERENCE_OUTPUT ?= $(PRE_SIB_COHERENCE_OUTPUT_DEFAULT)
CANDIDATE_REPAIR_LOOP_CANDIDATE_GRAPH ?= tests/fixtures/candidate_repair_loop/candidate_graph_repairable.json
CANDIDATE_REPAIR_LOOP_PRE_SIB_REPORT ?= tests/fixtures/candidate_repair_loop/pre_sib_repair_required.json
CANDIDATE_REPAIR_LOOP_OUTPUT_DEFAULT := runs/candidate_repair_loop_report.json
CANDIDATE_REPAIR_LOOP_OUTPUT ?= $(CANDIDATE_REPAIR_LOOP_OUTPUT_DEFAULT)
IDEA_TO_SPEC_CLARIFICATION_SESSION ?= runs/user_idea_intake_session.json
IDEA_TO_SPEC_CLARIFICATION_INTAKE ?= runs/idea_event_storming_intake.json
IDEA_TO_SPEC_CLARIFICATION_CANDIDATE_GRAPH ?= runs/candidate_spec_graph.json
IDEA_TO_SPEC_CLARIFICATION_PRE_SIB ?= runs/pre_sib_coherence_report.json
IDEA_TO_SPEC_CLARIFICATION_REPAIR_LOOP ?= runs/candidate_repair_loop_report.json
IDEA_TO_SPEC_CLARIFICATION_ONTOLOGY_GAP_REVIEW ?=
IDEA_TO_SPEC_CLARIFICATION_ONTOLOGY_GAP_REVIEW_ARG := $(if $(strip $(IDEA_TO_SPEC_CLARIFICATION_ONTOLOGY_GAP_REVIEW)),--ontology-gap-review "$(IDEA_TO_SPEC_CLARIFICATION_ONTOLOGY_GAP_REVIEW)",)
IDEA_TO_SPEC_CLARIFICATION_IDEA_MATURITY ?=
IDEA_TO_SPEC_CLARIFICATION_IDEA_MATURITY_ARG := $(if $(strip $(IDEA_TO_SPEC_CLARIFICATION_IDEA_MATURITY)),--idea-maturity "$(IDEA_TO_SPEC_CLARIFICATION_IDEA_MATURITY)",)
IDEA_TO_SPEC_CLARIFICATION_OUTPUT_DEFAULT := runs/idea_to_spec_clarification_requests.json
IDEA_TO_SPEC_CLARIFICATION_OUTPUT ?= $(IDEA_TO_SPEC_CLARIFICATION_OUTPUT_DEFAULT)
IDEA_TO_SPEC_CLARIFICATION_ANSWERS_REQUESTS ?= $(IDEA_TO_SPEC_CLARIFICATION_OUTPUT)
IDEA_TO_SPEC_CLARIFICATION_ANSWERS_INPUT ?= tests/fixtures/idea_to_spec_clarification_answers/answers_ready.json
IDEA_TO_SPEC_CLARIFICATION_ANSWERS_OUTPUT ?= runs/idea_to_spec_clarification_answers.json
PRODUCT_ONTOLOGY_GAP_REVIEW_DECISIONS_ANSWERS ?= runs/idea_to_spec_clarification_answers.json
PRODUCT_ONTOLOGY_GAP_REVIEW_DECISIONS_OUTPUT ?= runs/product_ontology_gap_review_decisions.json
PROJECT_LOCAL_ONTOLOGY_REVIEW_CANDIDATE_GRAPH ?= runs/candidate_spec_graph.json
PROJECT_LOCAL_ONTOLOGY_REVIEW_DECISIONS ?= runs/product_ontology_gap_review_decisions.json
PROJECT_LOCAL_ONTOLOGY_REVIEW_RERUN_PREVIEW ?= runs/idea_to_spec_rerun_preview.json
PROJECT_LOCAL_ONTOLOGY_REVIEW_ACTIVE_CANDIDATE ?= runs/active_idea_to_spec_candidate.json
PROJECT_LOCAL_ONTOLOGY_REVIEW_REPAIR_SESSION ?= runs/idea_to_spec_repair_session.json
PROJECT_LOCAL_ONTOLOGY_REVIEW_OUTPUT ?= runs/project_local_ontology_review_lane.json
PROJECT_LOCAL_ONTOLOGY_REVIEW_STRICT ?=
PROJECT_LOCAL_ONTOLOGY_REVIEW_STRICT_ARG := $(if $(filter 1 true yes,$(strip $(PROJECT_LOCAL_ONTOLOGY_REVIEW_STRICT))),--strict,)
SPECSPACE_PROJECT_LOCAL_ONTOLOGY_DECISION_IMPORT_STATE ?= runs/project_local_ontology_review_decisions.json
SPECSPACE_PROJECT_LOCAL_ONTOLOGY_DECISION_IMPORT_REVIEW_LANE ?= runs/project_local_ontology_review_lane.json
SPECSPACE_PROJECT_LOCAL_ONTOLOGY_DECISION_IMPORT_WORKSPACE_ID ?=
SPECSPACE_PROJECT_LOCAL_ONTOLOGY_DECISION_IMPORT_WORKSPACE_ID_ARG := $(if $(strip $(SPECSPACE_PROJECT_LOCAL_ONTOLOGY_DECISION_IMPORT_WORKSPACE_ID)),--workspace-id "$(SPECSPACE_PROJECT_LOCAL_ONTOLOGY_DECISION_IMPORT_WORKSPACE_ID)",)
SPECSPACE_PROJECT_LOCAL_ONTOLOGY_DECISION_IMPORT_OUTPUT ?= runs/specspace_project_local_ontology_decision_import_preview.json
SPECSPACE_PROJECT_LOCAL_ONTOLOGY_DECISION_IMPORT_STRICT ?=
SPECSPACE_PROJECT_LOCAL_ONTOLOGY_DECISION_IMPORT_STRICT_ARG := $(if $(filter 1 true yes,$(strip $(SPECSPACE_PROJECT_LOCAL_ONTOLOGY_DECISION_IMPORT_STRICT))),--strict,)
PROJECT_LOCAL_ONTOLOGY_DECISION_EFFECT_REVIEW_LANE ?= runs/project_local_ontology_review_lane.json
PROJECT_LOCAL_ONTOLOGY_DECISION_EFFECT_IMPORT_PREVIEW ?= runs/specspace_project_local_ontology_decision_import_preview.json
PROJECT_LOCAL_ONTOLOGY_DECISION_EFFECT_OUTPUT ?= runs/project_local_ontology_decision_effect_report.json
PROJECT_LOCAL_ONTOLOGY_DECISION_EFFECT_STRICT ?=
PROJECT_LOCAL_ONTOLOGY_DECISION_EFFECT_STRICT_ARG := $(if $(filter 1 true yes,$(strip $(PROJECT_LOCAL_ONTOLOGY_DECISION_EFFECT_STRICT))),--strict,)
IDEA_TO_SPEC_ANSWER_RERUN_INPUT_ANSWERS ?= runs/idea_to_spec_clarification_answers.json
IDEA_TO_SPEC_ANSWER_RERUN_INPUT_ONTOLOGY_DECISIONS ?=
IDEA_TO_SPEC_ANSWER_RERUN_INPUT_ONTOLOGY_DECISIONS_ARG := $(if $(strip $(IDEA_TO_SPEC_ANSWER_RERUN_INPUT_ONTOLOGY_DECISIONS)),--ontology-decisions "$(IDEA_TO_SPEC_ANSWER_RERUN_INPUT_ONTOLOGY_DECISIONS)",)
IDEA_TO_SPEC_ANSWER_RERUN_INPUT_OUTPUT ?= runs/idea_to_spec_answer_rerun_input.json
IDEA_TO_SPEC_RERUN_PREVIEW_INPUT ?= runs/idea_to_spec_answer_rerun_input.json
IDEA_TO_SPEC_RERUN_PREVIEW_INTAKE ?= runs/idea_event_storming_intake.json
IDEA_TO_SPEC_RERUN_PREVIEW_CANDIDATE_GRAPH ?= runs/candidate_spec_graph.json
IDEA_TO_SPEC_RERUN_PREVIEW_OUTPUT ?= runs/idea_to_spec_rerun_preview.json
IDEA_TO_SPEC_RERUN_MATERIALIZATION_PREVIEW ?= runs/idea_to_spec_rerun_preview.json
IDEA_TO_SPEC_RERUN_MATERIALIZATION_CANDIDATE_GRAPH ?= runs/candidate_spec_graph.json
IDEA_TO_SPEC_RERUN_MATERIALIZATION_OUTPUT ?= runs/idea_to_spec_rerun_materialization.json
REPAIRED_CANDIDATE_PROMOTION_HANDOFF_INTAKE ?= runs/idea_event_storming_intake.json
REPAIRED_CANDIDATE_PROMOTION_HANDOFF_CLARIFICATION_REQUESTS ?= runs/idea_to_spec_clarification_requests.json
REPAIRED_CANDIDATE_PROMOTION_HANDOFF_CLARIFICATION_ANSWERS ?= runs/idea_to_spec_clarification_answers.json
REPAIRED_CANDIDATE_PROMOTION_HANDOFF_ONTOLOGY_DECISIONS ?= runs/product_ontology_gap_review_decisions.json
REPAIRED_CANDIDATE_PROMOTION_HANDOFF_RERUN_INPUT ?= runs/idea_to_spec_answer_rerun_input.json
REPAIRED_CANDIDATE_PROMOTION_HANDOFF_RERUN_PREVIEW ?= runs/idea_to_spec_rerun_preview.json
REPAIRED_CANDIDATE_PROMOTION_HANDOFF_RERUN_MATERIALIZATION ?= runs/idea_to_spec_rerun_materialization.json
REPAIRED_CANDIDATE_PROMOTION_HANDOFF_CANDIDATE_GRAPH_OUTPUT ?= runs/repaired_candidate_spec_graph.json
REPAIRED_CANDIDATE_PROMOTION_HANDOFF_PRE_SIB_OUTPUT ?= runs/repaired_pre_sib_coherence_report.json
REPAIRED_CANDIDATE_PROMOTION_HANDOFF_REPAIR_LOOP_OUTPUT ?= runs/repaired_candidate_repair_loop_report.json
REPAIRED_CANDIDATE_PROMOTION_HANDOFF_MATERIALIZATION_OUTPUT_DIR ?= runs/repaired_materialized_candidate_specs
REPAIRED_CANDIDATE_PROMOTION_HANDOFF_MATERIALIZATION_OUTPUT ?= runs/repaired_candidate_spec_materialization_report.json
REPAIRED_CANDIDATE_PROMOTION_HANDOFF_PROMOTION_GATE_OUTPUT ?= runs/repaired_idea_to_spec_promotion_gate.json
REPAIRED_CANDIDATE_PROMOTION_HANDOFF_ACTIVE_CANDIDATE_OUTPUT ?= runs/repaired_active_idea_to_spec_candidate.json
REPAIRED_CANDIDATE_PROMOTION_HANDOFF_REPAIR_SESSION_OUTPUT ?= runs/repaired_idea_to_spec_repair_session.json
REPAIRED_CANDIDATE_PROMOTION_HANDOFF_OUTPUT ?= runs/repaired_candidate_promotion_handoff_report.json
REPAIRED_CANDIDATE_PROMOTION_HANDOFF_SESSION_ID ?=
REPAIRED_CANDIDATE_PROMOTION_HANDOFF_SESSION_ID_ARG := $(if $(strip $(REPAIRED_CANDIDATE_PROMOTION_HANDOFF_SESSION_ID)),--session-id "$(REPAIRED_CANDIDATE_PROMOTION_HANDOFF_SESSION_ID)",)
REPAIRED_CANDIDATE_PROMOTION_HANDOFF_OPERATOR_REF ?= local_operator:unattributed
REPAIRED_CANDIDATE_PROMOTION_HANDOFF_STRICT ?=
REPAIRED_CANDIDATE_PROMOTION_HANDOFF_STRICT_ARG := $(if $(filter 1 true yes,$(strip $(REPAIRED_CANDIDATE_PROMOTION_HANDOFF_STRICT))),--strict,)
# A scoped product flow normally overrides producer outputs. A caller can instead
# supply a direct repaired-handoff input; command-line and environment values win.
product_workspace_repaired_handoff_input = $(if $(filter file,$(origin $(1))),$($(2)),$($(1)))
IDEA_TO_SPEC_REPAIR_SESSION_ACTIVE_CANDIDATE ?= runs/active_idea_to_spec_candidate.json
IDEA_TO_SPEC_REPAIR_SESSION_CLARIFICATION_REQUESTS ?= runs/idea_to_spec_clarification_requests.json
IDEA_TO_SPEC_REPAIR_SESSION_CLARIFICATION_ANSWERS ?= runs/idea_to_spec_clarification_answers.json
IDEA_TO_SPEC_REPAIR_SESSION_ONTOLOGY_DECISIONS ?= runs/product_ontology_gap_review_decisions.json
IDEA_TO_SPEC_REPAIR_SESSION_RERUN_INPUT ?= runs/idea_to_spec_answer_rerun_input.json
IDEA_TO_SPEC_REPAIR_SESSION_RERUN_PREVIEW ?= runs/idea_to_spec_rerun_preview.json
IDEA_TO_SPEC_REPAIR_SESSION_RERUN_MATERIALIZATION ?= runs/idea_to_spec_rerun_materialization.json
IDEA_TO_SPEC_REPAIR_SESSION_PROMOTION_GATE ?= runs/idea_to_spec_promotion_gate.json
IDEA_TO_SPEC_REPAIR_SESSION_OUTPUT ?= runs/idea_to_spec_repair_session.json
IDEA_TO_SPEC_REPAIR_SESSION_ID ?=
IDEA_TO_SPEC_REPAIR_SESSION_ID_ARG := $(if $(strip $(IDEA_TO_SPEC_REPAIR_SESSION_ID)),--session-id "$(IDEA_TO_SPEC_REPAIR_SESSION_ID)",)
IDEA_TO_SPEC_REPAIR_SESSION_OPERATOR_REF ?= local_operator:unattributed
IDEA_TO_SPEC_REPAIR_SESSION_JOURNAL_ARGS := --active-candidate "$(IDEA_TO_SPEC_REPAIR_SESSION_ACTIVE_CANDIDATE)" --clarification-requests "$(IDEA_TO_SPEC_REPAIR_SESSION_CLARIFICATION_REQUESTS)" --clarification-answers "$(IDEA_TO_SPEC_REPAIR_SESSION_CLARIFICATION_ANSWERS)" --ontology-decisions "$(IDEA_TO_SPEC_REPAIR_SESSION_ONTOLOGY_DECISIONS)" --rerun-input "$(IDEA_TO_SPEC_REPAIR_SESSION_RERUN_INPUT)" --rerun-preview "$(IDEA_TO_SPEC_REPAIR_SESSION_RERUN_PREVIEW)" --rerun-materialization "$(IDEA_TO_SPEC_REPAIR_SESSION_RERUN_MATERIALIZATION)" --promotion-gate "$(IDEA_TO_SPEC_REPAIR_SESSION_PROMOTION_GATE)" --operator-ref "$(IDEA_TO_SPEC_REPAIR_SESSION_OPERATOR_REF)" $(IDEA_TO_SPEC_REPAIR_SESSION_ID_ARG) --output "$(IDEA_TO_SPEC_REPAIR_SESSION_OUTPUT)"
SPECSPACE_REPAIR_DRAFT_IMPORT_DRAFTS ?= runs/idea_to_spec_repair_drafts.json
SPECSPACE_REPAIR_DRAFT_IMPORT_REPAIR_SESSION ?= runs/idea_to_spec_repair_session.json
SPECSPACE_REPAIR_DRAFT_IMPORT_CLARIFICATION_REQUESTS ?= runs/idea_to_spec_clarification_requests.json
SPECSPACE_REPAIR_DRAFT_IMPORT_WORKSPACE_ID ?=
SPECSPACE_REPAIR_DRAFT_IMPORT_WORKSPACE_ID_ARG := $(if $(strip $(SPECSPACE_REPAIR_DRAFT_IMPORT_WORKSPACE_ID)),--workspace-id "$(SPECSPACE_REPAIR_DRAFT_IMPORT_WORKSPACE_ID)",)
SPECSPACE_REPAIR_DRAFT_IMPORT_OUTPUT ?= runs/specspace_repair_draft_import_preview.json
SPECSPACE_REPAIR_DRAFT_RERUN_IMPORT_PREVIEW ?= $(SPECSPACE_REPAIR_DRAFT_IMPORT_OUTPUT)
SPECSPACE_REPAIR_DRAFT_RERUN_REPAIR_SESSION ?= runs/idea_to_spec_repair_session.json
SPECSPACE_REPAIR_DRAFT_RERUN_CLARIFICATION_REQUESTS ?= runs/idea_to_spec_clarification_requests.json
SPECSPACE_REPAIR_DRAFT_RERUN_ACTIVE_CANDIDATE ?= runs/active_idea_to_spec_candidate.json
SPECSPACE_REPAIR_DRAFT_RERUN_INTAKE ?= runs/idea_event_storming_intake.json
SPECSPACE_REPAIR_DRAFT_RERUN_CANDIDATE_GRAPH ?= runs/candidate_spec_graph.json
SPECSPACE_REPAIR_DRAFT_RERUN_PROMOTION_GATE ?= runs/idea_to_spec_promotion_gate.json
SPECSPACE_REPAIR_DRAFT_RERUN_REPORT_OUTPUT ?= runs/specspace_repair_draft_rerun_report.json
SPECSPACE_REPAIR_RERUN_REQUEST_STATE ?= runs/idea_to_spec_repair_rerun_requests.json
SPECSPACE_REPAIR_RERUN_REQUEST_IMPORT_PREVIEW ?= $(SPECSPACE_REPAIR_DRAFT_RERUN_IMPORT_PREVIEW)
SPECSPACE_REPAIR_RERUN_REQUEST_REPAIR_SESSION ?= $(SPECSPACE_REPAIR_DRAFT_RERUN_REPAIR_SESSION)
SPECSPACE_REPAIR_RERUN_REQUEST_WORKSPACE_ID ?=
SPECSPACE_REPAIR_RERUN_REQUEST_WORKSPACE_ID_ARG := $(if $(strip $(SPECSPACE_REPAIR_RERUN_REQUEST_WORKSPACE_ID)),--workspace-id "$(SPECSPACE_REPAIR_RERUN_REQUEST_WORKSPACE_ID)",)
SPECSPACE_REPAIR_RERUN_REQUEST_OUTPUT ?= runs/specspace_repair_rerun_request_gate.json
SPECSPACE_REPAIR_RERUN_REQUEST_STRICT ?=
SPECSPACE_REPAIR_RERUN_REQUEST_STRICT_ARG := $(if $(filter 1 true yes,$(strip $(SPECSPACE_REPAIR_RERUN_REQUEST_STRICT))),--strict,)
PRODUCT_WORKSPACE_REPAIR_PACK ?= tests/fixtures/product_workspace_repair_packs/team_decision_log_happy_path_repair_pack.json
PRODUCT_WORKSPACE_REPAIR_PACK_REPAIR_SESSION ?= runs/idea_to_spec_repair_session.json
PRODUCT_WORKSPACE_REPAIR_PACK_CLARIFICATION_REQUESTS ?= runs/idea_to_spec_clarification_requests.json
PRODUCT_WORKSPACE_REPAIR_PACK_DRAFTS_OUTPUT ?= runs/idea_to_spec_repair_drafts.json
PRODUCT_WORKSPACE_REPAIR_PACK_REQUEST_STATE_OUTPUT ?= runs/idea_to_spec_repair_rerun_requests.json
PRODUCT_WORKSPACE_REPAIR_PACK_IMPORT_PREVIEW_REF ?= runs/specspace_repair_draft_import_preview.json
PRODUCT_WORKSPACE_REPAIR_PACK_RERUN_REPORT_REF ?= runs/specspace_repair_draft_rerun_report.json
PRODUCT_WORKSPACE_REPAIR_PACK_REQUEST_GATE_OUTPUT ?= runs/specspace_repair_rerun_request_gate.json
PRODUCT_WORKSPACE_REPAIR_PACK_ABSENT_ARTIFACT_DIR ?= runs/product_workspace_repair_pack_absent
PRODUCT_WORKSPACE_REPAIR_PACK_WORKSPACE_ID ?= team-decision-log
PRODUCT_WORKSPACE_REPAIR_PACK_PROJECT_LOCAL_ONTOLOGY_LANE ?=
PRODUCT_WORKSPACE_REPAIR_PACK_PROJECT_LOCAL_ONTOLOGY_DECISIONS_OUTPUT ?=
PRODUCT_WORKSPACE_REPAIR_PACK_PROJECT_LOCAL_ONTOLOGY_ARGS := $(if $(and $(strip $(PRODUCT_WORKSPACE_REPAIR_PACK_PROJECT_LOCAL_ONTOLOGY_LANE)),$(strip $(PRODUCT_WORKSPACE_REPAIR_PACK_PROJECT_LOCAL_ONTOLOGY_DECISIONS_OUTPUT))),--project-local-ontology-review-lane "$(PRODUCT_WORKSPACE_REPAIR_PACK_PROJECT_LOCAL_ONTOLOGY_LANE)" --project-local-ontology-decisions-output "$(PRODUCT_WORKSPACE_REPAIR_PACK_PROJECT_LOCAL_ONTOLOGY_DECISIONS_OUTPUT)",)
CANDIDATE_SPEC_MATERIALIZATION_CANDIDATE_GRAPH ?= tests/fixtures/candidate_repair_loop/candidate_graph_repairable.json
CANDIDATE_SPEC_MATERIALIZATION_REPAIR_LOOP ?= runs/candidate_repair_loop_report.json
CANDIDATE_SPEC_MATERIALIZATION_OUTPUT_DIR ?= runs/materialized_candidate_specs
CANDIDATE_SPEC_MATERIALIZATION_OUTPUT_DEFAULT := runs/candidate_spec_materialization_report.json
CANDIDATE_SPEC_MATERIALIZATION_OUTPUT ?= $(CANDIDATE_SPEC_MATERIALIZATION_OUTPUT_DEFAULT)
IDEA_TO_SPEC_PROMOTION_GATE_PRE_SIB ?= runs/pre_sib_coherence_report.json
IDEA_TO_SPEC_PROMOTION_GATE_REPAIR_LOOP ?= runs/candidate_repair_loop_report.json
IDEA_TO_SPEC_PROMOTION_GATE_MATERIALIZATION ?= runs/candidate_spec_materialization_report.json
IDEA_TO_SPEC_PROMOTION_GATE_OUTPUT_DEFAULT := runs/idea_to_spec_promotion_gate.json
IDEA_TO_SPEC_PROMOTION_GATE_OUTPUT ?= $(IDEA_TO_SPEC_PROMOTION_GATE_OUTPUT_DEFAULT)
ACTIVE_IDEA_TO_SPEC_CANDIDATE_CONFIG ?=
ACTIVE_IDEA_TO_SPEC_CANDIDATE_CONFIG_ARGS := $(if $(strip $(ACTIVE_IDEA_TO_SPEC_CANDIDATE_CONFIG)),--config "$(ACTIVE_IDEA_TO_SPEC_CANDIDATE_CONFIG)",)
ACTIVE_IDEA_TO_SPEC_CANDIDATE_OUTPUT_DEFAULT := runs/active_idea_to_spec_candidate.json
ACTIVE_IDEA_TO_SPEC_CANDIDATE_OUTPUT ?= $(ACTIVE_IDEA_TO_SPEC_CANDIDATE_OUTPUT_DEFAULT)
CANDIDATE_APPROVAL_ACTIVE_CANDIDATE ?= runs/active_idea_to_spec_candidate.json
CANDIDATE_APPROVAL_PROMOTION_GATE ?= runs/idea_to_spec_promotion_gate.json
CANDIDATE_APPROVAL_OUTPUT ?= runs/candidate_approval_decision.json
CANDIDATE_APPROVAL_DECISION_STATE ?= needs_context
CANDIDATE_APPROVAL_OPERATOR_REF ?= local_operator:unattributed
CANDIDATE_APPROVAL_REASON ?= awaiting explicit operator approval
IDEA_MATURITY_METRICS_INTAKE ?= runs/idea_event_storming_intake.json
IDEA_MATURITY_METRICS_CANDIDATE_GRAPH ?= runs/candidate_spec_graph.json
IDEA_MATURITY_METRICS_PRE_SIB ?= runs/pre_sib_coherence_report.json
IDEA_MATURITY_METRICS_CLARIFICATION_REQUESTS ?= runs/idea_to_spec_clarification_requests.json
IDEA_MATURITY_METRICS_CLARIFICATION_ANSWERS ?= runs/idea_to_spec_clarification_answers.json
IDEA_MATURITY_METRICS_ONTOLOGY_DECISIONS ?= runs/product_ontology_gap_review_decisions.json
IDEA_MATURITY_METRICS_RERUN_INPUT ?= runs/idea_to_spec_answer_rerun_input.json
IDEA_MATURITY_METRICS_RERUN_PREVIEW ?= runs/idea_to_spec_rerun_preview.json
IDEA_MATURITY_METRICS_RERUN_MATERIALIZATION ?= runs/idea_to_spec_rerun_materialization.json
IDEA_MATURITY_METRICS_PROMOTION_GATE ?= runs/idea_to_spec_promotion_gate.json
IDEA_MATURITY_METRICS_REPAIR_SESSION ?= runs/idea_to_spec_repair_session.json
IDEA_MATURITY_METRICS_REPAIRED_HANDOFF ?= runs/repaired_candidate_promotion_handoff_report.json
IDEA_MATURITY_METRICS_REPAIRED_CANDIDATE_GRAPH ?= runs/repaired_candidate_spec_graph.json
IDEA_MATURITY_METRICS_REPAIRED_PRE_SIB ?= runs/repaired_pre_sib_coherence_report.json
IDEA_MATURITY_METRICS_REPAIRED_ACTIVE_CANDIDATE ?= runs/repaired_active_idea_to_spec_candidate.json
IDEA_MATURITY_METRICS_REPAIRED_PROMOTION_GATE ?= runs/repaired_idea_to_spec_promotion_gate.json
IDEA_MATURITY_METRICS_REPAIRED_REPAIR_SESSION ?= runs/repaired_idea_to_spec_repair_session.json
IDEA_MATURITY_METRICS_SPECSPACE_DRAFT_IMPORT_PREVIEW ?= runs/specspace_repair_draft_import_preview.json
IDEA_MATURITY_METRICS_SPECSPACE_RERUN_REQUEST ?= runs/idea_to_spec_repair_rerun_requests.json
IDEA_MATURITY_METRICS_PROJECT_LOCAL_ONTOLOGY_DECISION_EFFECT ?= runs/project_local_ontology_decision_effect_report.json
IDEA_MATURITY_METRICS_APPROVAL_INTENT ?= runs/idea_to_spec_candidate_approval_intents.json
IDEA_MATURITY_METRICS_REPAIR_RERUN_EXECUTION ?= runs/platform_product_repair_rerun_execution_report.json
IDEA_MATURITY_METRICS_REPAIR_RERUN_PUBLICATION ?= runs/platform_product_repair_rerun_publication_report.json
IDEA_MATURITY_METRICS_APPROVAL_EXECUTION ?= runs/platform_candidate_approval_execution_report.json
IDEA_MATURITY_METRICS_CANDIDATE_APPROVAL_DECISION ?= runs/candidate_approval_decision.json
IDEA_MATURITY_METRICS_PROMOTION_REQUEST ?= runs/graph_repository_promotion_request.json
IDEA_MATURITY_METRICS_PROMOTION_EXECUTION ?= runs/product_candidate_promotion_execution_report.json
IDEA_MATURITY_METRICS_REVIEW_STATUS ?= runs/product_candidate_promotion_review_status_report.json
IDEA_MATURITY_METRICS_READ_MODEL_PUBLICATION ?= runs/product_candidate_promotion_read_model_publication_report.json
IDEA_MATURITY_METRICS_OUTPUT ?= runs/idea_maturity_metrics_report.json
IDEA_MATURITY_METRICS_VALIDATION_OUTPUT ?= runs/idea_maturity_metrics_validation_report.json
IDEA_MATURITY_METRICS_STRICT ?=
IDEA_MATURITY_METRICS_STRICT_ARG := $(if $(filter 1 true yes,$(strip $(IDEA_MATURITY_METRICS_STRICT))),--strict,)
CANDIDATE_OVERVIEW_INTAKE ?= runs/idea_event_storming_intake.json
CANDIDATE_OVERVIEW_CANDIDATE_GRAPH ?= runs/candidate_spec_graph.json
CANDIDATE_OVERVIEW_REPAIRED_CANDIDATE_GRAPH ?= runs/repaired_candidate_spec_graph.json
CANDIDATE_OVERVIEW_REPAIR_SESSION ?= runs/idea_to_spec_repair_session.json
CANDIDATE_OVERVIEW_REPAIRED_REPAIR_SESSION ?= runs/repaired_idea_to_spec_repair_session.json
CANDIDATE_OVERVIEW_IDEA_MATURITY ?= runs/idea_maturity_metrics_report.json
CANDIDATE_OVERVIEW_PROJECT_LOCAL_ONTOLOGY_LANE ?= runs/project_local_ontology_review_lane.json
CANDIDATE_OVERVIEW_PROJECT_LOCAL_ONTOLOGY_EFFECT ?= runs/project_local_ontology_decision_effect_report.json
CANDIDATE_OVERVIEW_ONTOLOGY_PACKAGE_INDEX ?= runs/ontology_package_index.json
CANDIDATE_OVERVIEW_ONTOLOGY_COMPATIBILITY_DIFF ?= runs/ontology_compatibility_diff_preview.json
CANDIDATE_OVERVIEW_REPAIRED_HANDOFF ?= runs/repaired_candidate_promotion_handoff_report.json
CANDIDATE_OVERVIEW_OUTPUT ?= runs/candidate_overview.json
CANDIDATE_OVERVIEW_STRICT ?=
CANDIDATE_OVERVIEW_STRICT_ARG := $(if $(filter 1 true yes,$(strip $(CANDIDATE_OVERVIEW_STRICT))),--strict,)
HOSTED_MANAGED_PUBLICATION_RUN_DIR ?= runs/hosted-operation-canary
SPECGRAPH_EXTERNAL_CHECKOUT_ROOT ?=
METRICS_REPO_DEFAULT := $(if $(strip $(SPECGRAPH_EXTERNAL_CHECKOUT_ROOT)),$(SPECGRAPH_EXTERNAL_CHECKOUT_ROOT)/Metrics,../Metrics)
METRICS_REPO ?= $(METRICS_REPO_DEFAULT)
METRICS_CLI ?= $(PYTHON) $(METRICS_REPO)/scripts/metrics.py
PRODUCT_WORKSPACE_IDEA_SOURCE ?= tests/fixtures/product_workspace_active_candidate/raw_idea_source.json
PRODUCT_WORKSPACE_INTAKE_SOURCE_DEFAULT ?= $(USER_IDEA_EVENT_STORMING_SEED_OUTPUT)
PRODUCT_WORKSPACE_INTAKE_SOURCE ?= $(PRODUCT_WORKSPACE_INTAKE_SOURCE_DEFAULT)
PRODUCT_WORKSPACE_INTAKE_SOURCE_MODE := $(if $(filter-out $(PRODUCT_WORKSPACE_INTAKE_SOURCE_DEFAULT),$(strip $(PRODUCT_WORKSPACE_INTAKE_SOURCE))),input,generate)
PRODUCT_WORKSPACE_CANDIDATE_SEED_OUTPUT ?= $(ONTOLOGY_BOUND_CANDIDATE_SEED_OUTPUT)
PRODUCT_WORKSPACE_CANDIDATE_SEED_INPUT ?=
PRODUCT_WORKSPACE_CANDIDATE_SEED ?= $(PRODUCT_WORKSPACE_CANDIDATE_SEED_OUTPUT)
PRODUCT_WORKSPACE_CANDIDATE_SEED_MODE := $(if $(strip $(PRODUCT_WORKSPACE_CANDIDATE_SEED_INPUT)),input,$(if $(filter-out $(PRODUCT_WORKSPACE_CANDIDATE_SEED_OUTPUT),$(strip $(PRODUCT_WORKSPACE_CANDIDATE_SEED))),input,generate))
PRODUCT_WORKSPACE_CANDIDATE_SEED_EFFECTIVE := $(if $(strip $(PRODUCT_WORKSPACE_CANDIDATE_SEED_INPUT)),$(PRODUCT_WORKSPACE_CANDIDATE_SEED_INPUT),$(PRODUCT_WORKSPACE_CANDIDATE_SEED))
PRODUCT_WORKSPACE_ACTIVE_CANDIDATE_CONFIG ?= $(ACTIVE_IDEA_TO_SPEC_CANDIDATE_CONFIG)
PRODUCT_WORKSPACE_ACTIVE_CANDIDATE_CONFIG_ARGS := $(if $(strip $(PRODUCT_WORKSPACE_ACTIVE_CANDIDATE_CONFIG)),--config "$(PRODUCT_WORKSPACE_ACTIVE_CANDIDATE_CONFIG)",)
PRODUCT_WORKSPACE_CLARIFICATION_SESSION_ARG := $(if $(filter generate,$(PRODUCT_WORKSPACE_INTAKE_SOURCE_MODE)),--session "$(USER_IDEA_INTAKE_SESSION_OUTPUT)",--no-session)
PRODUCT_WORKSPACE_ACTIVE_CANDIDATE_ARTIFACT_REFS_CHANGED := $(strip \
	$(if $(filter-out $(IDEA_EVENT_STORMING_INTAKE_OUTPUT_DEFAULT),$(strip $(IDEA_EVENT_STORMING_INTAKE_OUTPUT))),changed,) \
	$(if $(filter-out $(CANDIDATE_SPEC_GRAPH_OUTPUT_DEFAULT),$(strip $(CANDIDATE_SPEC_GRAPH_OUTPUT))),changed,) \
	$(if $(filter-out $(PRE_SIB_COHERENCE_OUTPUT_DEFAULT),$(strip $(PRE_SIB_COHERENCE_OUTPUT))),changed,) \
	$(if $(filter-out $(CANDIDATE_REPAIR_LOOP_OUTPUT_DEFAULT),$(strip $(CANDIDATE_REPAIR_LOOP_OUTPUT))),changed,) \
	$(if $(filter-out $(CANDIDATE_SPEC_MATERIALIZATION_OUTPUT_DEFAULT),$(strip $(CANDIDATE_SPEC_MATERIALIZATION_OUTPUT))),changed,) \
	$(if $(filter-out $(IDEA_TO_SPEC_PROMOTION_GATE_OUTPUT_DEFAULT),$(strip $(IDEA_TO_SPEC_PROMOTION_GATE_OUTPUT))),changed,))
PRODUCT_WORKSPACE_ACTIVE_CANDIDATE_ARTIFACT_ARGS := $(if $(strip $(PRODUCT_WORKSPACE_ACTIVE_CANDIDATE_CONFIG)),,$(if $(PRODUCT_WORKSPACE_ACTIVE_CANDIDATE_ARTIFACT_REFS_CHANGED),--intake "$(IDEA_EVENT_STORMING_INTAKE_OUTPUT)" --candidate-graph "$(CANDIDATE_SPEC_GRAPH_OUTPUT)" --pre-sib "$(PRE_SIB_COHERENCE_OUTPUT)" --repair-loop "$(CANDIDATE_REPAIR_LOOP_OUTPUT)" --materialization "$(CANDIDATE_SPEC_MATERIALIZATION_OUTPUT)" --promotion-gate "$(IDEA_TO_SPEC_PROMOTION_GATE_OUTPUT)",))
PRODUCT_WORKSPACE_ACTIVE_CANDIDATE_REFRESH_VARS := \
	ACTIVE_IDEA_TO_SPEC_CANDIDATE_CONFIG \
	PRODUCT_WORKSPACE_IDEA_SOURCE \
	USER_IDEA_EVENT_STORMING_SEED_OUTPUT \
	PRODUCT_WORKSPACE_INTAKE_SOURCE \
	PRODUCT_WORKSPACE_CANDIDATE_SEED \
	PRODUCT_WORKSPACE_CANDIDATE_SEED_INPUT \
	PRODUCT_WORKSPACE_CANDIDATE_SEED_OUTPUT \
	PRODUCT_WORKSPACE_ACTIVE_CANDIDATE_CONFIG
PRODUCT_WORKSPACE_ACTIVE_CANDIDATE_REFRESH_FORCE := $(strip $(foreach var,$(PRODUCT_WORKSPACE_ACTIVE_CANDIDATE_REFRESH_VARS),$(if $(findstring command line,$(origin $(var))),force,$(if $(findstring environment,$(origin $(var))),force,))))
PRODUCT_WORKSPACE_ACTIVE_CANDIDATE_REFRESH_AUTO := $(if $(PRODUCT_WORKSPACE_ACTIVE_CANDIDATE_REFRESH_FORCE),force,auto)
PRODUCT_WORKSPACE_ACTIVE_CANDIDATE_REFRESH ?= $(PRODUCT_WORKSPACE_ACTIVE_CANDIDATE_REFRESH_AUTO)

.DEFAULT_GOAL := help

PYTHON_TARGETS := viewer-surfaces dashboard backlog next-move spec-activity graph-diagnostics \
	proposal-spec-trace proposal-tracking proposal-tracking-gate spec-evidence-gate architecture-style architecture-metrics external-consumers external-handoffs \
	external-consumer-evidence ontology-imports ontology-imports-public \
	ontology-package-validate ontology-package-preview ontology-package-gaps \
	spec-ontology-bindings spec-ontology-validation \
	ontology-term-binding-gate ontology-gap-review legacy-spec-ontology-backfill-plan \
	ontology-owner-decision-import-v2 \
	specauthor-generated-artifact-contract specauthor-ontology-write-gate \
	specauthor-invocation-artifact-contract specauthor-authoring-flow \
	user-idea-intake-session intake-session-candidate-source \
	real-idea-intake-candidate-source real-idea-intake-clarification-requests \
	real-idea-intake-clarification-answers real-idea-intake-clarification-rerun \
	real-idea-intake-ready-candidate-source real-idea-intake-active-candidate \
	real-idea-smoke real-idea-smoke-continue real-idea-smoke-idea-maturity \
	real-idea-smoke-answer-template real-idea-smoke-validate-answers \
	real-idea-smoke-materialize-answers \
	specspace-real-idea-entry-import-preview real-idea-intake-from-entry-request \
	user-idea-intake-source generic-idea-intake \
	generic-idea-intake-session \
	idea-event-storming-intake ontology-bound-candidate-graph-seed \
	candidate-spec-graph pre-sib-coherence candidate-repair-loop \
	idea-to-spec-clarification-requests \
	idea-to-spec-clarification-answers \
	product-ontology-gap-review-decisions \
	project-local-ontology-review-lane \
	idea-to-spec-answer-rerun-input \
	idea-to-spec-rerun-preview \
	idea-to-spec-rerun-materialization \
	repaired-candidate-promotion-handoff \
	idea-to-spec-initial-repair-session-journal \
	idea-to-spec-repair-session-journal \
	specspace-repair-draft-import-preview \
	specspace-repair-rerun-request-gate \
	specspace-repair-draft-rerun-artifacts \
	specspace-repair-draft-rerun product-workspace-repair-draft-rerun \
	product-workspace-requested-repair-draft-rerun \
	product-workspace-repair-pack-state \
	candidate-spec-materialization idea-to-spec-promotion-gate \
	active-idea-to-spec-candidate-source candidate-approval-decision \
	candidate-overview \
	product-workspace-active-candidate product-workspace-decision-backed-repair-chain \
	product-workspace-repaired-promotion-handoff \
	product-workspace-happy-path-repair-pack \
	product-workspace-team-decision-log-happy-path-repair-pack \
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
		'  make spec-evidence-gate      Fail on logic changes without Spec-ID evidence' \
		'  make architecture-style       Fail on new supervisor package architecture/style violations' \
		'  make architecture-metrics     Print report-only architecture/code-shape metrics JSON' \
		'  make proposal-work-claims     Refresh proposal work claim report JSON' \
		'  make proposal-work-claims-gate Fail on stale or duplicate proposal work claims' \
		'  make proposal-id              Print the next deterministic proposal id' \
		'  make external-consumers       Refresh external consumer bridge JSON' \
		'  make external-handoffs        Refresh external consumer handoff JSON' \
			'  make external-consumer-evidence Refresh external consumer evidence JSON' \
			'  make ontology-imports          Refresh ontology import and semantic-control surfaces' \
			'  make ontology-imports-public   Refresh public-safe ontology review placeholders' \
			'  make ontology-package-validate Validate project-local ontology package authoring state' \
			'  make ontology-package-preview  Preview project-local ontology package refs/diffs' \
			'  make ontology-package-gaps     Preview project-local ontology package gaps' \
			'  make spec-ontology-bindings    Build report-only legacy spec ontology bindings' \
				'  make spec-ontology-validation  Build report-only spec ontology validation report' \
					'  make ontology-term-binding-gate ONTOLOGY_TERM_BINDING_ARTIFACT=<json>' \
					'  make ontology-gap-review ONTOLOGY_GAP_REVIEW_GENERATED_ARTIFACT=<json>' \
					'  make legacy-spec-ontology-backfill-plan Build review-first legacy spec backfill plan JSON' \
					'  make ontology-owner-decision-import-v2 Build read-only owner decision import v2 review JSON' \
			'  make specauthor-generated-artifact-contract SPECAUTHOR_GENERATED_ARTIFACT_CONTRACT_ARTIFACT=<json>' \
			'  make specauthor-ontology-write-gate SPECAUTHOR_ONTOLOGY_WRITE_GATE_ARTIFACT=<json>' \
			'  SPECG_USER_IDEA_INTAKE_INTERVIEW_IDEA_TEXT=<text> make real-idea-intake' \
			'  make real-idea-intake-candidate-source Build source from real intake session' \
			'  make real-idea-intake-clarification-requests Build intake-only clarification requests' \
			'  make real-idea-intake-clarification-rerun IDEA_INTAKE_CLARIFICATION_ANSWERS_INPUT=<json>' \
			'  make real-idea-intake-ready-candidate-source Prefer clarified session when present' \
			'  make real-idea-intake-active-candidate Build active candidate from ready real intake' \
			'  make real-idea-smoke-continue REAL_IDEA_SMOKE_CLARIFICATION_ANSWERS_INPUT=<json>' \
			'  make real-idea-smoke-answer-template Build typed operator answer template' \
			'  make real-idea-smoke-validate-answers REAL_IDEA_ANSWER_AUTHORING_ANSWERS=<json>' \
			'  make real-idea-smoke-materialize-answers REAL_IDEA_ANSWER_AUTHORING_ANSWERS=<json>' \
			'  make real-idea-intake-from-entry-request SPECSPACE_REAL_IDEA_ENTRY_REQUESTS=<json>' \
			'  make user-idea-intake-session USER_IDEA_INTAKE_SESSION_INPUT=<json>' \
			'  make intake-session-candidate-source INTAKE_SESSION_CANDIDATE_SOURCE_INPUT=<json>' \
			'  make user-idea-intake-source USER_IDEA_INTAKE_SOURCE=<json>' \
			'  make generic-idea-intake-session USER_IDEA_INTAKE_SESSION_INPUT=<json>' \
			'  make generic-idea-intake USER_IDEA_INTAKE_SOURCE=<json>' \
			'  make idea-event-storming-intake IDEA_EVENT_STORMING_INTAKE_SOURCE=<json>' \
			'  make ontology-bound-candidate-graph-seed ONTOLOGY_BOUND_CANDIDATE_SEED_INTAKE=<json>' \
			'  make product-workspace-active-candidate PRODUCT_WORKSPACE_CANDIDATE_SEED_INPUT=<json>' \
			'  make candidate-spec-graph CANDIDATE_SPEC_GRAPH_INTAKE=<json> CANDIDATE_SPEC_GRAPH_SEED=<json>' \
			'  make pre-sib-coherence PRE_SIB_COHERENCE_CANDIDATE_GRAPH=<json>' \
			'  make candidate-repair-loop CANDIDATE_REPAIR_LOOP_CANDIDATE_GRAPH=<json> CANDIDATE_REPAIR_LOOP_PRE_SIB_REPORT=<json>' \
			'  make idea-to-spec-clarification-requests IDEA_TO_SPEC_CLARIFICATION_SESSION=<json>' \
			'  make idea-to-spec-clarification-answers IDEA_TO_SPEC_CLARIFICATION_ANSWERS_INPUT=<json>' \
			'  make product-ontology-gap-review-decisions PRODUCT_ONTOLOGY_GAP_REVIEW_DECISIONS_ANSWERS=<json>' \
			'  make project-local-ontology-review-lane PROJECT_LOCAL_ONTOLOGY_REVIEW_CANDIDATE_GRAPH=<json>' \
			'  make idea-to-spec-answer-rerun-input IDEA_TO_SPEC_ANSWER_RERUN_INPUT_ANSWERS=<json>' \
			'  make idea-to-spec-rerun-preview IDEA_TO_SPEC_RERUN_PREVIEW_INPUT=<json>' \
			'  make idea-to-spec-rerun-materialization IDEA_TO_SPEC_RERUN_MATERIALIZATION_PREVIEW=<json>' \
			'  make repaired-candidate-promotion-handoff REPAIRED_CANDIDATE_PROMOTION_HANDOFF_RERUN_MATERIALIZATION=<json>' \
			'  make idea-to-spec-repair-session-journal IDEA_TO_SPEC_REPAIR_SESSION_OUTPUT=<json>' \
			'  make specspace-repair-draft-import-preview SPECSPACE_REPAIR_DRAFT_IMPORT_DRAFTS=<json>' \
			'  make product-workspace-repair-draft-rerun SPECSPACE_REPAIR_DRAFT_IMPORT_DRAFTS=<json>' \
			'  make product-workspace-repair-pack-state PRODUCT_WORKSPACE_REPAIR_PACK=<json>' \
			'  make product-workspace-decision-backed-repair-chain Build product candidate + decision-backed rerun preview' \
			'  make product-workspace-happy-path-repair-pack PRODUCT_WORKSPACE_REPAIR_PACK=<json>' \
			'  make product-workspace-team-decision-log-happy-path-repair-pack Demo alias for the Team Decision Log fixture' \
			'  make idea-maturity-metrics   Build Idea-to-Spec maturity telemetry report' \
			'  make idea-maturity-metrics-validate Validate maturity telemetry with Metrics CLI' \
			'  make candidate-overview       Build public-safe candidate overview narrative JSON' \
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
			'  make candidate-spec-materialization Build review-only candidate spec YAML previews' \
			'  make idea-to-spec-promotion-gate Build final idea-to-spec Platform handoff gate' \
			'  make active-idea-to-spec-candidate-source Build active product candidate source' \
			'  make candidate-approval-decision Build explicit candidate approval decision' \
			'  make idea-maturity-metrics   Build Idea-to-Spec maturity telemetry report' \
			'  make candidate-overview       Build public-safe candidate overview narrative JSON' \
			'  make idea-to-spec-repair-session-journal Build durable review-only repair session journal' \
			'  make repaired-candidate-promotion-handoff Build repaired approval-ready handoff artifacts' \
			'  make specspace-repair-draft-import-preview Build review-only SpecSpace repair draft import preview' \
			'  make product-workspace-active-candidate Build active product workspace candidate artifacts' \
			'  make product-workspace-decision-backed-repair-chain Build product candidate + decision-backed rerun preview' \
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

SPEC_EVIDENCE_BASE_REF ?= origin/main
SPEC_EVIDENCE_HEAD_REF ?= HEAD

.PHONY: spec-evidence-gate
spec-evidence-gate:
	@$(PYTHON) tools/spec_evidence_gate.py --base-ref "$(SPEC_EVIDENCE_BASE_REF)" --head-ref "$(SPEC_EVIDENCE_HEAD_REF)"

.PHONY: architecture-style
architecture-style:
	@$(PYTHON) tools/validate_architecture_style.py

.PHONY: architecture-metrics
architecture-metrics:
	@$(PYTHON) tools/architecture_metrics.py

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

.PHONY: ontology-package-validate
ontology-package-validate:
	@$(PYTHON) tools/ontology_package_authoring.py --mode validate --write

.PHONY: ontology-package-preview
ontology-package-preview:
	@$(PYTHON) tools/ontology_package_authoring.py --mode preview --write

.PHONY: ontology-package-gaps
ontology-package-gaps:
	@$(PYTHON) tools/ontology_package_authoring.py --mode gaps --write

.PHONY: spec-ontology-bindings
spec-ontology-bindings:
	@$(PYTHON) tools/spec_ontology_binding_index.py --write

.PHONY: spec-ontology-validation
spec-ontology-validation:
	@$(PYTHON) tools/spec_ontology_validation_report.py --write

.PHONY: ontology-term-binding-gate
ontology-term-binding-gate:
	@$(PYTHON) tools/ontology_term_binding_gate.py --artifact "$(ONTOLOGY_TERM_BINDING_ARTIFACT)" --output "$(ONTOLOGY_TERM_BINDING_GATE_OUTPUT)"

.PHONY: ontology-gap-review
ontology-gap-review:
	@$(PYTHON) tools/ontology_gap_review_workflow.py --write --output "$(ONTOLOGY_GAP_REVIEW_OUTPUT)" $(if $(ONTOLOGY_GAP_REVIEW_GENERATED_ARTIFACT),--generated-artifact "$(ONTOLOGY_GAP_REVIEW_GENERATED_ARTIFACT)",)

.PHONY: legacy-spec-ontology-backfill-plan
legacy-spec-ontology-backfill-plan:
	@$(PYTHON) tools/legacy_spec_ontology_backfill_plan.py --write --output "$(LEGACY_SPEC_ONTOLOGY_BACKFILL_PLAN_OUTPUT)" $(if $(LEGACY_SPEC_ONTOLOGY_BACKFILL_PLAN_VALIDATION_REPORT),--validation-report "$(LEGACY_SPEC_ONTOLOGY_BACKFILL_PLAN_VALIDATION_REPORT)",) $(if $(LEGACY_SPEC_ONTOLOGY_BACKFILL_PLAN_GAP_REVIEW),--gap-review-workflow "$(LEGACY_SPEC_ONTOLOGY_BACKFILL_PLAN_GAP_REVIEW)",)

.PHONY: ontology-owner-decision-import-v2
ontology-owner-decision-import-v2:
	@$(PYTHON) tools/ontology_owner_decision_import_v2.py --write --output "$(ONTOLOGY_OWNER_DECISION_IMPORT_V2_OUTPUT)" --decision-import-preview "$(ONTOLOGY_OWNER_DECISION_IMPORT_V2_DECISION_PREVIEW)" --closed-loop-evidence "$(ONTOLOGY_OWNER_DECISION_IMPORT_V2_CLOSED_LOOP)" $(if $(ONTOLOGY_OWNER_DECISION_IMPORT_V2_GAP_REVIEW),--gap-review-workflow "$(ONTOLOGY_OWNER_DECISION_IMPORT_V2_GAP_REVIEW)",) $(if $(ONTOLOGY_OWNER_DECISION_IMPORT_V2_VALIDATION_REPORT),--validation-report "$(ONTOLOGY_OWNER_DECISION_IMPORT_V2_VALIDATION_REPORT)",) $(if $(ONTOLOGY_OWNER_DECISION_IMPORT_V2_WRITE_GATE_REPORT),--write-gate-report "$(ONTOLOGY_OWNER_DECISION_IMPORT_V2_WRITE_GATE_REPORT)",)

.PHONY: specauthor-generated-artifact-contract
specauthor-generated-artifact-contract:
	@$(PYTHON) tools/specauthor_generated_artifact_contract.py --artifact "$(SPECAUTHOR_GENERATED_ARTIFACT_CONTRACT_ARTIFACT)" --output "$(SPECAUTHOR_GENERATED_ARTIFACT_CONTRACT_OUTPUT)"

.PHONY: specauthor-ontology-write-gate
specauthor-ontology-write-gate:
	@$(PYTHON) tools/specauthor_ontology_write_gate.py --artifact "$(SPECAUTHOR_ONTOLOGY_WRITE_GATE_ARTIFACT)" --output "$(SPECAUTHOR_ONTOLOGY_WRITE_GATE_OUTPUT)"

.PHONY: specauthor-invocation-artifact-contract
specauthor-invocation-artifact-contract:
	@$(PYTHON) tools/specauthor_invocation_artifact_contract.py --artifact "$(SPECAUTHOR_INVOCATION_ARTIFACT_CONTRACT_ARTIFACT)" --output "$(SPECAUTHOR_INVOCATION_ARTIFACT_CONTRACT_OUTPUT)"

.PHONY: specauthor-authoring-flow
specauthor-authoring-flow:
	@$(PYTHON) tools/specauthor_authoring_flow.py --context "$(SPECAUTHOR_AUTHORING_FLOW_CONTEXT)" --generated-artifact "$(SPECAUTHOR_AUTHORING_FLOW_GENERATED_ARTIFACT)" --invocation-output "$(SPECAUTHOR_AUTHORING_FLOW_INVOCATION_OUTPUT)" --contract-output "$(SPECAUTHOR_AUTHORING_FLOW_CONTRACT_OUTPUT)" --flow-report-output "$(SPECAUTHOR_AUTHORING_FLOW_REPORT_OUTPUT)"

.PHONY: idea-event-storming-intake
idea-event-storming-intake:
	@$(PYTHON) tools/idea_event_storming_intake.py --input "$(IDEA_EVENT_STORMING_INTAKE_SOURCE)" --output "$(IDEA_EVENT_STORMING_INTAKE_OUTPUT)"

.PHONY: real-idea-intake user-idea-intake-interview
real-idea-intake user-idea-intake-interview:
	@$(PYTHON) tools/user_idea_intake_interview.py $(USER_IDEA_INTAKE_INTERVIEW_INPUT_ARG) $(USER_IDEA_INTAKE_INTERVIEW_IDEA_SUMMARY_ARG) $(USER_IDEA_INTAKE_INTERVIEW_CANDIDATE_ID_ARG) $(USER_IDEA_INTAKE_INTERVIEW_DISPLAY_NAME_ARG) $(USER_IDEA_INTAKE_INTERVIEW_PUBLIC_ROUTE_ARG) $(USER_IDEA_INTAKE_INTERVIEW_CLARIFICATION_REQUESTS_ARG) $(USER_IDEA_INTAKE_INTERVIEW_CLARIFICATION_ANSWERS_ARG) --raw-output "$(USER_IDEA_RAW_INPUT_OUTPUT)" --session-output "$(USER_IDEA_INTAKE_SESSION_OUTPUT)" --source-output "$(USER_IDEA_INTAKE_SESSION_SOURCE_OUTPUT)" --report-output "$(USER_IDEA_INTAKE_INTERVIEW_REPORT_OUTPUT)"

.PHONY: user-idea-intake-source
user-idea-intake-source:
	@$(PYTHON) tools/user_idea_intake_source.py --input "$(USER_IDEA_INTAKE_SOURCE)" --output "$(USER_IDEA_EVENT_STORMING_SEED_OUTPUT)"

.PHONY: user-idea-intake-session
user-idea-intake-session:
	@$(PYTHON) tools/user_idea_intake_session.py --input "$(USER_IDEA_INTAKE_SESSION_INPUT)" --session-output "$(USER_IDEA_INTAKE_SESSION_OUTPUT)" --source-output "$(USER_IDEA_INTAKE_SESSION_SOURCE_OUTPUT)"

.PHONY: intake-session-candidate-source
intake-session-candidate-source:
	@$(PYTHON) tools/intake_session_candidate_source.py --intake-session "$(INTAKE_SESSION_CANDIDATE_SOURCE_INPUT)" $(INTAKE_SESSION_CANDIDATE_SOURCE_FALLBACK_ARG) --output "$(INTAKE_SESSION_CANDIDATE_SOURCE_OUTPUT)" --report "$(INTAKE_SESSION_CANDIDATE_SOURCE_REPORT_OUTPUT)" $(INTAKE_SESSION_CANDIDATE_SOURCE_STRICT_ARG)

.PHONY: real-idea-intake-candidate-source
real-idea-intake-candidate-source: real-idea-intake
	@$(MAKE) intake-session-candidate-source INTAKE_SESSION_CANDIDATE_SOURCE_INPUT="$(USER_IDEA_INTAKE_SESSION_OUTPUT)" INTAKE_SESSION_CANDIDATE_SOURCE_OUTPUT="$(USER_IDEA_INTAKE_SESSION_SOURCE_OUTPUT)" INTAKE_SESSION_CANDIDATE_SOURCE_STRICT=1

.PHONY: real-idea-intake-clarification-requests
real-idea-intake-clarification-requests:
	@if test ! -f "$(USER_IDEA_INTAKE_SESSION_OUTPUT)" || test "$(strip $(REAL_IDEA_INTAKE_REFRESH))" = "1"; then \
		$(MAKE) real-idea-intake; \
	fi
	@$(PYTHON) tools/idea_to_spec_clarification_requests.py --session "$(USER_IDEA_INTAKE_SESSION_OUTPUT)" --no-intake --no-candidate-graph --no-pre-sib --no-repair-loop --output "$(IDEA_INTAKE_CLARIFICATION_REQUESTS_OUTPUT)"

.PHONY: real-idea-intake-clarification-answers
real-idea-intake-clarification-answers:
	@test -n "$(strip $(IDEA_INTAKE_CLARIFICATION_ANSWERS_INPUT))" || (printf '%s\n' 'IDEA_INTAKE_CLARIFICATION_ANSWERS_INPUT=<json> is required for real-idea intake clarification answers.' >&2; exit 2)
	@$(PYTHON) tools/idea_to_spec_clarification_answers.py --requests "$(IDEA_INTAKE_CLARIFICATION_REQUESTS_OUTPUT)" --answers "$(IDEA_INTAKE_CLARIFICATION_ANSWERS_INPUT)" --output "$(IDEA_INTAKE_CLARIFICATION_ANSWERS_OUTPUT)" --strict

.PHONY: real-idea-intake-clarification-rerun
real-idea-intake-clarification-rerun:
	@test -n "$(strip $(IDEA_INTAKE_CLARIFICATION_ANSWERS_INPUT))" || (printf '%s\n' 'IDEA_INTAKE_CLARIFICATION_ANSWERS_INPUT=<json> is required for real-idea intake clarification rerun.' >&2; exit 2)
	@$(PYTHON) tools/idea_intake_clarification_rerun.py --raw-input "$(USER_IDEA_RAW_INPUT_OUTPUT)" --clarification-requests "$(IDEA_INTAKE_CLARIFICATION_REQUESTS_OUTPUT)" --answers "$(IDEA_INTAKE_CLARIFICATION_ANSWERS_INPUT)" --validated-answers-output "$(IDEA_INTAKE_CLARIFICATION_ANSWERS_OUTPUT)" --rerun-input-output "$(IDEA_INTAKE_ANSWER_RERUN_INPUT_OUTPUT)" --clarified-raw-output "$(CLARIFIED_USER_IDEA_RAW_INPUT_OUTPUT)" --clarified-session-output "$(CLARIFIED_USER_IDEA_INTAKE_SESSION_OUTPUT)" --clarified-source-output "$(CLARIFIED_USER_IDEA_INTAKE_SOURCE_OUTPUT)" --report-output "$(IDEA_INTAKE_CLARIFICATION_RERUN_REPORT_OUTPUT)" --strict

.PHONY: real-idea-intake-ready-candidate-source
real-idea-intake-ready-candidate-source:
	@ready_session="$(USER_IDEA_INTAKE_SESSION_OUTPUT)"; \
	if test -f "$(CLARIFIED_USER_IDEA_INTAKE_SESSION_OUTPUT)"; then ready_session="$(CLARIFIED_USER_IDEA_INTAKE_SESSION_OUTPUT)"; fi; \
	$(MAKE) intake-session-candidate-source INTAKE_SESSION_CANDIDATE_SOURCE_INPUT="$$ready_session" INTAKE_SESSION_CANDIDATE_SOURCE_FALLBACK="$(USER_IDEA_INTAKE_SESSION_OUTPUT)" INTAKE_SESSION_CANDIDATE_SOURCE_OUTPUT="$(USER_IDEA_INTAKE_SESSION_SOURCE_OUTPUT)" INTAKE_SESSION_CANDIDATE_SOURCE_STRICT=1

.PHONY: real-idea-intake-active-candidate
real-idea-intake-active-candidate:
	@if ! test -f "$(USER_IDEA_INTAKE_SESSION_OUTPUT)" && ! test -f "$(CLARIFIED_USER_IDEA_INTAKE_SESSION_OUTPUT)"; then \
		$(MAKE) real-idea-intake; \
	fi
	@$(MAKE) real-idea-intake-ready-candidate-source
	@$(MAKE) user-idea-intake-source USER_IDEA_INTAKE_SOURCE="$(USER_IDEA_INTAKE_SESSION_SOURCE_OUTPUT)" USER_IDEA_EVENT_STORMING_SEED_OUTPUT="$(USER_IDEA_EVENT_STORMING_SEED_OUTPUT)"
	@$(MAKE) product-workspace-active-candidate \
		PRODUCT_WORKSPACE_INTAKE_SOURCE="$(USER_IDEA_EVENT_STORMING_SEED_OUTPUT)" \
		PRODUCT_WORKSPACE_INTAKE_SOURCE_MODE=input \
		IDEA_EVENT_STORMING_INTAKE_OUTPUT="$(IDEA_EVENT_STORMING_INTAKE_OUTPUT)" \
		PRODUCT_WORKSPACE_CANDIDATE_SEED_OUTPUT="$(PRODUCT_WORKSPACE_CANDIDATE_SEED_OUTPUT)" \
		CANDIDATE_SPEC_GRAPH_OUTPUT="$(CANDIDATE_SPEC_GRAPH_OUTPUT)" \
		PRE_SIB_COHERENCE_OUTPUT="$(PRE_SIB_COHERENCE_OUTPUT)" \
		CANDIDATE_REPAIR_LOOP_OUTPUT="$(CANDIDATE_REPAIR_LOOP_OUTPUT)" \
		IDEA_TO_SPEC_CLARIFICATION_OUTPUT="$(IDEA_TO_SPEC_CLARIFICATION_OUTPUT)" \
		CANDIDATE_SPEC_MATERIALIZATION_OUTPUT_DIR="$(CANDIDATE_SPEC_MATERIALIZATION_OUTPUT_DIR)" \
			CANDIDATE_SPEC_MATERIALIZATION_OUTPUT="$(CANDIDATE_SPEC_MATERIALIZATION_OUTPUT)" \
			IDEA_TO_SPEC_PROMOTION_GATE_OUTPUT="$(IDEA_TO_SPEC_PROMOTION_GATE_OUTPUT)" \
			ACTIVE_IDEA_TO_SPEC_CANDIDATE_OUTPUT="$(ACTIVE_IDEA_TO_SPEC_CANDIDATE_OUTPUT)"

.PHONY: real-idea-smoke
real-idea-smoke:
	@$(PYTHON) tools/real_idea_smoke.py --run-dir "$(REAL_IDEA_SMOKE_RUN_DIR)" --summary-output "$(REAL_IDEA_SMOKE_SUMMARY_OUTPUT)" --python "$(PYTHON)" --interview-input "$(USER_IDEA_INTAKE_INTERVIEW_INPUT)" $(REAL_IDEA_SMOKE_REFRESH_ARG)

.PHONY: real-idea-smoke-continue
real-idea-smoke-continue:
	@$(PYTHON) tools/real_idea_smoke.py --run-dir "$(REAL_IDEA_SMOKE_RUN_DIR)" --summary-output "$(REAL_IDEA_SMOKE_SUMMARY_OUTPUT)" --python "$(PYTHON)" --interview-input "$(USER_IDEA_INTAKE_INTERVIEW_INPUT)" --continue-existing $(REAL_IDEA_SMOKE_CLARIFICATION_ANSWERS_ARG)

.PHONY: real-idea-smoke-answer-template
real-idea-smoke-answer-template:
	@$(PYTHON) tools/real_idea_answer_authoring.py template --run-dir "$(REAL_IDEA_SMOKE_RUN_DIR)" --stage "$(REAL_IDEA_ANSWER_AUTHORING_STAGE)" $(REAL_IDEA_ANSWER_AUTHORING_REQUESTS_ARG) --output "$(REAL_IDEA_ANSWER_TEMPLATE_OUTPUT)" --report "$(REAL_IDEA_ANSWER_AUTHORING_REPORT_OUTPUT)" --strict

.PHONY: real-idea-smoke-validate-answers
real-idea-smoke-validate-answers:
	@test -n "$(strip $(REAL_IDEA_ANSWER_AUTHORING_ANSWERS))" || (printf '%s\n' 'REAL_IDEA_ANSWER_AUTHORING_ANSWERS=<json> is required for answer validation.' >&2; exit 2)
	@$(PYTHON) tools/real_idea_answer_authoring.py validate --run-dir "$(REAL_IDEA_SMOKE_RUN_DIR)" --stage "$(REAL_IDEA_ANSWER_AUTHORING_STAGE)" $(REAL_IDEA_ANSWER_AUTHORING_REQUESTS_ARG) --answers "$(REAL_IDEA_ANSWER_AUTHORING_ANSWERS)" --answer-set-output "$(REAL_IDEA_ANSWER_SET_OUTPUT)" --report "$(REAL_IDEA_ANSWER_AUTHORING_REPORT_OUTPUT)" --strict

.PHONY: real-idea-smoke-materialize-answers
real-idea-smoke-materialize-answers:
	@test -n "$(strip $(REAL_IDEA_ANSWER_AUTHORING_ANSWERS))" || (printf '%s\n' 'REAL_IDEA_ANSWER_AUTHORING_ANSWERS=<json> is required for answer materialization.' >&2; exit 2)
	@$(PYTHON) tools/real_idea_answer_authoring.py materialize --run-dir "$(REAL_IDEA_SMOKE_RUN_DIR)" --stage "$(REAL_IDEA_ANSWER_AUTHORING_STAGE)" $(REAL_IDEA_ANSWER_AUTHORING_REQUESTS_ARG) --answers "$(REAL_IDEA_ANSWER_AUTHORING_ANSWERS)" --answer-set-output "$(REAL_IDEA_ANSWER_SET_OUTPUT)" $(REAL_IDEA_ANSWER_VALIDATED_OUTPUT_ARG) --report "$(REAL_IDEA_ANSWER_AUTHORING_REPORT_OUTPUT)" --strict

.PHONY: specspace-real-idea-entry-import-preview
specspace-real-idea-entry-import-preview:
	@$(PYTHON) tools/real_idea_entry_request_import.py preview \
		--specspace-entry-requests "$(SPECSPACE_REAL_IDEA_ENTRY_REQUESTS)" \
		$(SPECSPACE_REAL_IDEA_ENTRY_WORKSPACE_ID_ARG) \
		$(SPECSPACE_REAL_IDEA_ENTRY_REQUEST_ID_ARG) \
		--output "$(SPECSPACE_REAL_IDEA_ENTRY_IMPORT_PREVIEW_OUTPUT)" \
		--strict

.PHONY: real-idea-intake-from-entry-request
real-idea-intake-from-entry-request:
	@$(MAKE) specspace-real-idea-entry-import-preview
	@$(PYTHON) tools/real_idea_entry_request_import.py materialize \
		--specspace-entry-requests "$(SPECSPACE_REAL_IDEA_ENTRY_REQUESTS)" \
		--import-preview "$(SPECSPACE_REAL_IDEA_ENTRY_IMPORT_PREVIEW_OUTPUT)" \
		--run-dir "$(REAL_IDEA_SMOKE_RUN_DIR)" \
		--raw-output "$(REAL_IDEA_SMOKE_RUN_DIR)/local_operator_user_idea_raw_input.json" \
		--session-output "$(REAL_IDEA_SMOKE_RUN_DIR)/user_idea_intake_session.json" \
		--source-output "$(REAL_IDEA_SMOKE_RUN_DIR)/user_idea_intake_source.json" \
		--interview-report-output "$(REAL_IDEA_SMOKE_RUN_DIR)/user_idea_intake_interview_report.json" \
		--output "$(REAL_IDEA_ENTRY_INTAKE_REPORT_OUTPUT)"
	@$(MAKE) real-idea-intake-clarification-requests \
		REAL_IDEA_INTAKE_REFRESH=0 \
		USER_IDEA_INTAKE_SESSION_OUTPUT="$(REAL_IDEA_SMOKE_RUN_DIR)/user_idea_intake_session.json" \
		IDEA_INTAKE_CLARIFICATION_REQUESTS_OUTPUT="$(REAL_IDEA_SMOKE_RUN_DIR)/idea_intake_clarification_requests.json"
	@$(MAKE) real-idea-smoke-answer-template \
		REAL_IDEA_SMOKE_RUN_DIR="$(REAL_IDEA_SMOKE_RUN_DIR)" \
		REAL_IDEA_ANSWER_AUTHORING_REQUESTS="$(REAL_IDEA_SMOKE_RUN_DIR)/idea_intake_clarification_requests.json" \
		REAL_IDEA_ANSWER_TEMPLATE_OUTPUT="$(REAL_IDEA_ANSWER_TEMPLATE_OUTPUT)" \
		REAL_IDEA_ANSWER_AUTHORING_REPORT_OUTPUT="$(REAL_IDEA_ANSWER_AUTHORING_REPORT_OUTPUT)"

.PHONY: specspace-real-idea-answer-import-preview
specspace-real-idea-answer-import-preview:
	@$(PYTHON) tools/specspace_real_idea_answer_handoff.py preview \
		--run-dir "$(REAL_IDEA_SMOKE_RUN_DIR)" \
		--stage intake \
		--specspace-answers "$(SPECSPACE_REAL_IDEA_ANSWER_STATE)" \
		--template "$(SPECSPACE_REAL_IDEA_ANSWER_TEMPLATE)" \
		--requests "$(SPECSPACE_REAL_IDEA_ANSWER_REQUESTS)" \
		--intake-session "$(SPECSPACE_REAL_IDEA_ANSWER_INTAKE_SESSION)" \
		--output "$(SPECSPACE_REAL_IDEA_ANSWER_IMPORT_PREVIEW_OUTPUT)" \
		--strict

.PHONY: real-idea-intake-materialize-specspace-answers
real-idea-intake-materialize-specspace-answers:
	@$(PYTHON) tools/specspace_real_idea_answer_handoff.py materialize \
		--run-dir "$(REAL_IDEA_SMOKE_RUN_DIR)" \
		--stage intake \
		--import-preview "$(SPECSPACE_REAL_IDEA_ANSWER_IMPORT_PREVIEW_OUTPUT)" \
		--requests "$(SPECSPACE_REAL_IDEA_ANSWER_REQUESTS)" \
		--answer-set-output "$(REAL_IDEA_ANSWER_SET_OUTPUT)" \
		--validated-answers-output "$(SPECSPACE_REAL_IDEA_VALIDATED_ANSWERS_OUTPUT)" \
		--authoring-report "$(REAL_IDEA_ANSWER_AUTHORING_REPORT_OUTPUT)" \
		--output "$(REAL_IDEA_ANSWER_CONTINUATION_REPORT_OUTPUT)" \
		--strict

.PHONY: real-idea-intake-continue-from-specspace-answers
real-idea-intake-continue-from-specspace-answers:
	@$(MAKE) specspace-real-idea-answer-import-preview
	@$(MAKE) real-idea-intake-materialize-specspace-answers
	@$(MAKE) real-idea-intake-active-candidate \
		USER_IDEA_INTAKE_SESSION_OUTPUT="$(REAL_IDEA_SMOKE_RUN_DIR)/user_idea_intake_session.json" \
		CLARIFIED_USER_IDEA_INTAKE_SESSION_OUTPUT="$(REAL_IDEA_SMOKE_RUN_DIR)/clarified_user_idea_intake_session.json" \
		USER_IDEA_INTAKE_SESSION_SOURCE_OUTPUT="$(REAL_IDEA_SMOKE_RUN_DIR)/user_idea_intake_source.json" \
		INTAKE_SESSION_CANDIDATE_SOURCE_REPORT_OUTPUT="$(REAL_IDEA_SMOKE_RUN_DIR)/intake_session_candidate_source_report.json" \
		USER_IDEA_EVENT_STORMING_SEED_OUTPUT="$(REAL_IDEA_SMOKE_RUN_DIR)/idea_event_storming_seed.json" \
		IDEA_EVENT_STORMING_INTAKE_OUTPUT="$(REAL_IDEA_SMOKE_RUN_DIR)/idea_event_storming_intake.json" \
		PRODUCT_WORKSPACE_CANDIDATE_SEED_OUTPUT="$(REAL_IDEA_SMOKE_RUN_DIR)/candidate_spec_graph_seed.json" \
		CANDIDATE_SPEC_GRAPH_OUTPUT="$(REAL_IDEA_SMOKE_RUN_DIR)/candidate_spec_graph.json" \
		PRE_SIB_COHERENCE_OUTPUT="$(REAL_IDEA_SMOKE_RUN_DIR)/pre_sib_coherence_report.json" \
		CANDIDATE_REPAIR_LOOP_OUTPUT="$(REAL_IDEA_SMOKE_RUN_DIR)/candidate_repair_loop_report.json" \
		IDEA_TO_SPEC_CLARIFICATION_OUTPUT="$(REAL_IDEA_SMOKE_RUN_DIR)/idea_to_spec_clarification_requests.json" \
		CANDIDATE_SPEC_MATERIALIZATION_OUTPUT_DIR="$(REAL_IDEA_SMOKE_RUN_DIR)/materialized_candidate_specs" \
		CANDIDATE_SPEC_MATERIALIZATION_OUTPUT="$(REAL_IDEA_SMOKE_RUN_DIR)/candidate_spec_materialization_report.json" \
		IDEA_TO_SPEC_PROMOTION_GATE_OUTPUT="$(REAL_IDEA_SMOKE_RUN_DIR)/idea_to_spec_promotion_gate.json" \
			ACTIVE_IDEA_TO_SPEC_CANDIDATE_OUTPUT="$(REAL_IDEA_SMOKE_RUN_DIR)/active_idea_to_spec_candidate.json"

.PHONY: real-idea-intake-continue-without-answers
real-idea-intake-continue-without-answers:
	@$(PYTHON) tools/real_idea_answer_authoring.py verify-no-clarification \
		--run-dir "$(REAL_IDEA_SMOKE_RUN_DIR)" \
		--template "$(REAL_IDEA_SMOKE_RUN_DIR)/real_idea_answer_template.json" \
		--workspace-id "$(REAL_IDEA_ANSWER_CONTINUATION_WORKSPACE_ID)"
	@$(MAKE) real-idea-intake-active-candidate \
		USER_IDEA_INTAKE_SESSION_OUTPUT="$(REAL_IDEA_SMOKE_RUN_DIR)/user_idea_intake_session.json" \
		CLARIFIED_USER_IDEA_INTAKE_SESSION_OUTPUT="$(REAL_IDEA_SMOKE_RUN_DIR)/.no_clarified_intake_session.json" \
		USER_IDEA_INTAKE_SESSION_SOURCE_OUTPUT="$(REAL_IDEA_SMOKE_RUN_DIR)/user_idea_intake_source.json" \
		INTAKE_SESSION_CANDIDATE_SOURCE_REPORT_OUTPUT="$(REAL_IDEA_SMOKE_RUN_DIR)/intake_session_candidate_source_report.json" \
		USER_IDEA_EVENT_STORMING_SEED_OUTPUT="$(REAL_IDEA_SMOKE_RUN_DIR)/idea_event_storming_seed.json" \
		IDEA_EVENT_STORMING_INTAKE_OUTPUT="$(REAL_IDEA_SMOKE_RUN_DIR)/idea_event_storming_intake.json" \
		PRODUCT_WORKSPACE_CANDIDATE_SEED_OUTPUT="$(REAL_IDEA_SMOKE_RUN_DIR)/candidate_spec_graph_seed.json" \
		CANDIDATE_SPEC_GRAPH_OUTPUT="$(REAL_IDEA_SMOKE_RUN_DIR)/candidate_spec_graph.json" \
		PRE_SIB_COHERENCE_OUTPUT="$(REAL_IDEA_SMOKE_RUN_DIR)/pre_sib_coherence_report.json" \
		CANDIDATE_REPAIR_LOOP_OUTPUT="$(REAL_IDEA_SMOKE_RUN_DIR)/candidate_repair_loop_report.json" \
		IDEA_TO_SPEC_CLARIFICATION_OUTPUT="$(REAL_IDEA_SMOKE_RUN_DIR)/idea_to_spec_clarification_requests.json" \
		CANDIDATE_SPEC_MATERIALIZATION_OUTPUT_DIR="$(REAL_IDEA_SMOKE_RUN_DIR)/materialized_candidate_specs" \
		CANDIDATE_SPEC_MATERIALIZATION_OUTPUT="$(REAL_IDEA_SMOKE_RUN_DIR)/candidate_spec_materialization_report.json" \
		IDEA_TO_SPEC_PROMOTION_GATE_OUTPUT="$(REAL_IDEA_SMOKE_RUN_DIR)/idea_to_spec_promotion_gate.json" \
		ACTIVE_IDEA_TO_SPEC_CANDIDATE_OUTPUT="$(REAL_IDEA_SMOKE_RUN_DIR)/active_idea_to_spec_candidate.json"

.PHONY: real-idea-smoke-idea-maturity
real-idea-smoke-idea-maturity:
	@$(PYTHON) -c 'import shutil, sys; from pathlib import Path; root=Path.cwd(); run=(root / sys.argv[1]).resolve(); absent=(root / sys.argv[2]).resolve(); \
(absent != run and run in absent.parents) or (_ for _ in ()).throw(SystemExit("REAL_IDEA_SMOKE_MATURITY_ABSENT_DIR must be a child of REAL_IDEA_SMOKE_RUN_DIR")); \
shutil.rmtree(absent, ignore_errors=True)' "$(REAL_IDEA_SMOKE_RUN_DIR)" "$(REAL_IDEA_SMOKE_MATURITY_ABSENT_DIR)"
	@$(MAKE) product-workspace-idea-maturity \
		IDEA_MATURITY_METRICS_INTAKE="$(REAL_IDEA_SMOKE_RUN_DIR)/idea_event_storming_intake.json" \
		IDEA_MATURITY_METRICS_CANDIDATE_GRAPH="$(REAL_IDEA_SMOKE_RUN_DIR)/candidate_spec_graph.json" \
		IDEA_MATURITY_METRICS_PRE_SIB="$(REAL_IDEA_SMOKE_RUN_DIR)/pre_sib_coherence_report.json" \
		IDEA_MATURITY_METRICS_CLARIFICATION_REQUESTS="$(REAL_IDEA_SMOKE_RUN_DIR)/idea_to_spec_clarification_requests.json" \
		IDEA_MATURITY_METRICS_CLARIFICATION_ANSWERS="$(REAL_IDEA_SMOKE_RUN_DIR)/idea_to_spec_clarification_answers.json" \
		IDEA_MATURITY_METRICS_ONTOLOGY_DECISIONS="$(REAL_IDEA_SMOKE_RUN_DIR)/product_ontology_gap_review_decisions.json" \
		IDEA_MATURITY_METRICS_RERUN_INPUT="$(REAL_IDEA_SMOKE_RUN_DIR)/idea_to_spec_answer_rerun_input.json" \
		IDEA_MATURITY_METRICS_RERUN_PREVIEW="$(REAL_IDEA_SMOKE_RUN_DIR)/idea_to_spec_rerun_preview.json" \
		IDEA_MATURITY_METRICS_RERUN_MATERIALIZATION="$(REAL_IDEA_SMOKE_RUN_DIR)/idea_to_spec_rerun_materialization.json" \
		IDEA_MATURITY_METRICS_PROMOTION_GATE="$(REAL_IDEA_SMOKE_RUN_DIR)/idea_to_spec_promotion_gate.json" \
		IDEA_MATURITY_METRICS_REPAIR_SESSION="$(REAL_IDEA_SMOKE_RUN_DIR)/idea_to_spec_repair_session.json" \
		IDEA_MATURITY_METRICS_REPAIRED_HANDOFF="$(REAL_IDEA_SMOKE_RUN_DIR)/repaired_candidate_promotion_handoff_report.json" \
		IDEA_MATURITY_METRICS_REPAIRED_CANDIDATE_GRAPH="$(REAL_IDEA_SMOKE_RUN_DIR)/repaired_candidate_spec_graph.json" \
		IDEA_MATURITY_METRICS_REPAIRED_PRE_SIB="$(REAL_IDEA_SMOKE_RUN_DIR)/repaired_pre_sib_coherence_report.json" \
		IDEA_MATURITY_METRICS_REPAIRED_ACTIVE_CANDIDATE="$(REAL_IDEA_SMOKE_RUN_DIR)/repaired_active_idea_to_spec_candidate.json" \
		IDEA_MATURITY_METRICS_REPAIRED_PROMOTION_GATE="$(REAL_IDEA_SMOKE_RUN_DIR)/repaired_idea_to_spec_promotion_gate.json" \
		IDEA_MATURITY_METRICS_REPAIRED_REPAIR_SESSION="$(REAL_IDEA_SMOKE_RUN_DIR)/repaired_idea_to_spec_repair_session.json" \
		IDEA_MATURITY_METRICS_SPECSPACE_DRAFT_IMPORT_PREVIEW="$(REAL_IDEA_SMOKE_RUN_DIR)/specspace_repair_draft_import_preview.json" \
		IDEA_MATURITY_METRICS_SPECSPACE_RERUN_REQUEST="$(REAL_IDEA_SMOKE_RUN_DIR)/idea_to_spec_repair_rerun_requests.json" \
		IDEA_MATURITY_METRICS_PROJECT_LOCAL_ONTOLOGY_DECISION_EFFECT="$(REAL_IDEA_SMOKE_RUN_DIR)/project_local_ontology_decision_effect_report.json" \
		IDEA_MATURITY_METRICS_APPROVAL_INTENT="$(REAL_IDEA_SMOKE_MATURITY_ABSENT_DIR)/idea_to_spec_candidate_approval_intents.json" \
		IDEA_MATURITY_METRICS_REPAIR_RERUN_EXECUTION="$(REAL_IDEA_SMOKE_MATURITY_ABSENT_DIR)/platform_product_repair_rerun_execution_report.json" \
		IDEA_MATURITY_METRICS_REPAIR_RERUN_PUBLICATION="$(REAL_IDEA_SMOKE_MATURITY_ABSENT_DIR)/platform_product_repair_rerun_publication_report.json" \
		IDEA_MATURITY_METRICS_APPROVAL_EXECUTION="$(REAL_IDEA_SMOKE_MATURITY_ABSENT_DIR)/platform_candidate_approval_execution_report.json" \
		IDEA_MATURITY_METRICS_CANDIDATE_APPROVAL_DECISION="$(REAL_IDEA_SMOKE_MATURITY_ABSENT_DIR)/candidate_approval_decision.json" \
		IDEA_MATURITY_METRICS_PROMOTION_REQUEST="$(REAL_IDEA_SMOKE_MATURITY_ABSENT_DIR)/graph_repository_promotion_request.json" \
		IDEA_MATURITY_METRICS_PROMOTION_EXECUTION="$(REAL_IDEA_SMOKE_MATURITY_ABSENT_DIR)/product_candidate_promotion_execution_report.json" \
		IDEA_MATURITY_METRICS_REVIEW_STATUS="$(REAL_IDEA_SMOKE_MATURITY_ABSENT_DIR)/product_candidate_promotion_review_status_report.json" \
		IDEA_MATURITY_METRICS_READ_MODEL_PUBLICATION="$(REAL_IDEA_SMOKE_MATURITY_ABSENT_DIR)/product_candidate_promotion_read_model_publication_report.json" \
		IDEA_MATURITY_METRICS_OUTPUT="$(REAL_IDEA_SMOKE_RUN_DIR)/idea_maturity_metrics_report.json" \
		IDEA_MATURITY_METRICS_VALIDATION_OUTPUT="$(REAL_IDEA_SMOKE_RUN_DIR)/idea_maturity_metrics_validation_report.json"

.PHONY: real-idea-smoke-depth-baseline
real-idea-smoke-depth-baseline:
	@$(PYTHON) -c 'from pathlib import Path; import sys; root=Path.cwd().resolve(); path=Path(sys.argv[1]); resolved=path.resolve() if path.is_absolute() else (root / path).resolve(); rel=resolved.relative_to(root); (rel.as_posix() != "runs") or (_ for _ in ()).throw(SystemExit("REAL_IDEA_SMOKE_RUN_DIR=runs is reserved for shared SpecGraph runs. Use a child directory such as runs/real_idea_smoke or runs/<id>."))' "$(REAL_IDEA_SMOKE_RUN_DIR)"
	@$(MAKE) real-idea-smoke-idea-maturity \
		REAL_IDEA_SMOKE_RUN_DIR="$(REAL_IDEA_SMOKE_RUN_DIR)" \
		REAL_IDEA_SMOKE_MATURITY_ABSENT_DIR="$(REAL_IDEA_SMOKE_MATURITY_ABSENT_DIR)"
	@$(MAKE) candidate-overview \
		CANDIDATE_OVERVIEW_INTAKE="$(REAL_IDEA_SMOKE_RUN_DIR)/idea_event_storming_intake.json" \
		CANDIDATE_OVERVIEW_CANDIDATE_GRAPH="$(REAL_IDEA_SMOKE_RUN_DIR)/candidate_spec_graph.json" \
		CANDIDATE_OVERVIEW_REPAIRED_CANDIDATE_GRAPH="$(REAL_IDEA_SMOKE_RUN_DIR)/repaired_candidate_spec_graph.json" \
		CANDIDATE_OVERVIEW_REPAIR_SESSION="$(REAL_IDEA_SMOKE_RUN_DIR)/idea_to_spec_repair_session.json" \
		CANDIDATE_OVERVIEW_REPAIRED_REPAIR_SESSION="$(REAL_IDEA_SMOKE_RUN_DIR)/repaired_idea_to_spec_repair_session.json" \
		CANDIDATE_OVERVIEW_IDEA_MATURITY="$(REAL_IDEA_SMOKE_RUN_DIR)/idea_maturity_metrics_report.json" \
		CANDIDATE_OVERVIEW_PROJECT_LOCAL_ONTOLOGY_LANE="$(REAL_IDEA_SMOKE_RUN_DIR)/project_local_ontology_review_lane.json" \
		CANDIDATE_OVERVIEW_PROJECT_LOCAL_ONTOLOGY_EFFECT="$(REAL_IDEA_SMOKE_RUN_DIR)/project_local_ontology_decision_effect_report.json" \
		CANDIDATE_OVERVIEW_ONTOLOGY_PACKAGE_INDEX="$(REAL_IDEA_SMOKE_RUN_DIR)/ontology_package_index.json" \
		CANDIDATE_OVERVIEW_ONTOLOGY_COMPATIBILITY_DIFF="$(REAL_IDEA_SMOKE_RUN_DIR)/ontology_compatibility_diff_preview.json" \
		CANDIDATE_OVERVIEW_REPAIRED_HANDOFF="$(REAL_IDEA_SMOKE_RUN_DIR)/repaired_candidate_promotion_handoff_report.json" \
		CANDIDATE_OVERVIEW_OUTPUT="$(REAL_IDEA_SMOKE_CANDIDATE_OVERVIEW_OUTPUT)"
	@$(PYTHON) tools/product_demo_depth_report.py \
		--run-dir "$(REAL_IDEA_SMOKE_RUN_DIR)" \
		--intake "$(REAL_IDEA_SMOKE_RUN_DIR)/idea_event_storming_intake.json" \
		--candidate-graph "$(REAL_IDEA_SMOKE_RUN_DIR)/candidate_spec_graph.json" \
		--repaired-candidate-graph "$(REAL_IDEA_SMOKE_RUN_DIR)/repaired_candidate_spec_graph.json" \
		--candidate-overview "$(REAL_IDEA_SMOKE_CANDIDATE_OVERVIEW_OUTPUT)" \
		--idea-maturity "$(REAL_IDEA_SMOKE_RUN_DIR)/idea_maturity_metrics_report.json" \
		--output "$(REAL_IDEA_SMOKE_DEPTH_REPORT_OUTPUT)" \
		--strict

.PHONY: generic-idea-intake
generic-idea-intake: user-idea-intake-source
	@$(PYTHON) tools/idea_event_storming_intake.py --input "$(USER_IDEA_EVENT_STORMING_SEED_OUTPUT)" --output "$(IDEA_EVENT_STORMING_INTAKE_OUTPUT)"

.PHONY: generic-idea-intake-session
generic-idea-intake-session:
	@$(PYTHON) tools/user_idea_intake_session.py --input "$(USER_IDEA_INTAKE_SESSION_INPUT)" --session-output "$(USER_IDEA_INTAKE_SESSION_OUTPUT)" --source-output "$(USER_IDEA_INTAKE_SESSION_SOURCE_OUTPUT)" --strict
	@$(PYTHON) tools/user_idea_intake_source.py --input "$(USER_IDEA_INTAKE_SESSION_SOURCE_OUTPUT)" --output "$(USER_IDEA_EVENT_STORMING_SEED_OUTPUT)"
	@$(PYTHON) tools/idea_event_storming_intake.py --input "$(USER_IDEA_EVENT_STORMING_SEED_OUTPUT)" --output "$(IDEA_EVENT_STORMING_INTAKE_OUTPUT)"

.PHONY: candidate-spec-graph
candidate-spec-graph:
	@$(PYTHON) tools/candidate_spec_graph.py --intake "$(CANDIDATE_SPEC_GRAPH_INTAKE)" --candidate-seed "$(CANDIDATE_SPEC_GRAPH_SEED)" --output "$(CANDIDATE_SPEC_GRAPH_OUTPUT)"

.PHONY: ontology-bound-candidate-graph-seed
ifeq ($(strip $(ONTOLOGY_BOUND_CANDIDATE_SEED_INTAKE)),$(strip $(IDEA_EVENT_STORMING_INTAKE_OUTPUT)))
ontology-bound-candidate-graph-seed: generic-idea-intake
endif
ontology-bound-candidate-graph-seed:
	@$(PYTHON) tools/ontology_bound_candidate_graph_seed.py --intake "$(ONTOLOGY_BOUND_CANDIDATE_SEED_INTAKE)" --ontology-ir "$(ONTOLOGY_BOUND_CANDIDATE_SEED_ONTOLOGY_IR)" --output "$(ONTOLOGY_BOUND_CANDIDATE_SEED_OUTPUT)"

.PHONY: pre-sib-coherence
pre-sib-coherence:
	@$(PYTHON) tools/pre_sib_coherence_report.py --candidate-graph "$(PRE_SIB_COHERENCE_CANDIDATE_GRAPH)" --output "$(PRE_SIB_COHERENCE_OUTPUT)"

.PHONY: candidate-repair-loop
candidate-repair-loop:
	@$(PYTHON) tools/candidate_repair_loop.py --candidate-graph "$(CANDIDATE_REPAIR_LOOP_CANDIDATE_GRAPH)" --pre-sib-report "$(CANDIDATE_REPAIR_LOOP_PRE_SIB_REPORT)" --output "$(CANDIDATE_REPAIR_LOOP_OUTPUT)"

.PHONY: idea-to-spec-clarification-requests
idea-to-spec-clarification-requests:
	@$(PYTHON) tools/idea_to_spec_clarification_requests.py --session "$(IDEA_TO_SPEC_CLARIFICATION_SESSION)" --intake "$(IDEA_TO_SPEC_CLARIFICATION_INTAKE)" --candidate-graph "$(IDEA_TO_SPEC_CLARIFICATION_CANDIDATE_GRAPH)" --pre-sib "$(IDEA_TO_SPEC_CLARIFICATION_PRE_SIB)" --repair-loop "$(IDEA_TO_SPEC_CLARIFICATION_REPAIR_LOOP)" $(IDEA_TO_SPEC_CLARIFICATION_ONTOLOGY_GAP_REVIEW_ARG) $(IDEA_TO_SPEC_CLARIFICATION_IDEA_MATURITY_ARG) --output "$(IDEA_TO_SPEC_CLARIFICATION_OUTPUT)"

.PHONY: idea-to-spec-clarification-answers
idea-to-spec-clarification-answers:
	@$(PYTHON) tools/idea_to_spec_clarification_answers.py --requests "$(IDEA_TO_SPEC_CLARIFICATION_ANSWERS_REQUESTS)" --answers "$(IDEA_TO_SPEC_CLARIFICATION_ANSWERS_INPUT)" --output "$(IDEA_TO_SPEC_CLARIFICATION_ANSWERS_OUTPUT)"

.PHONY: product-ontology-gap-review-decisions
product-ontology-gap-review-decisions:
	@$(PYTHON) tools/product_ontology_gap_review_decisions.py --answers "$(PRODUCT_ONTOLOGY_GAP_REVIEW_DECISIONS_ANSWERS)" --output "$(PRODUCT_ONTOLOGY_GAP_REVIEW_DECISIONS_OUTPUT)"

.PHONY: project-local-ontology-review-lane
project-local-ontology-review-lane:
	@$(PYTHON) tools/project_local_ontology_review_lane.py \
		--candidate-graph "$(PROJECT_LOCAL_ONTOLOGY_REVIEW_CANDIDATE_GRAPH)" \
		--ontology-decisions "$(PROJECT_LOCAL_ONTOLOGY_REVIEW_DECISIONS)" \
		--rerun-preview "$(PROJECT_LOCAL_ONTOLOGY_REVIEW_RERUN_PREVIEW)" \
		--active-candidate "$(PROJECT_LOCAL_ONTOLOGY_REVIEW_ACTIVE_CANDIDATE)" \
		--repair-session "$(PROJECT_LOCAL_ONTOLOGY_REVIEW_REPAIR_SESSION)" \
		--output "$(PROJECT_LOCAL_ONTOLOGY_REVIEW_OUTPUT)" \
		$(PROJECT_LOCAL_ONTOLOGY_REVIEW_STRICT_ARG)

.PHONY: specspace-project-local-ontology-decision-import-preview
specspace-project-local-ontology-decision-import-preview:
	@$(PYTHON) tools/specspace_project_local_ontology_decision_import_preview.py \
		--decisions "$(SPECSPACE_PROJECT_LOCAL_ONTOLOGY_DECISION_IMPORT_STATE)" \
		--review-lane "$(SPECSPACE_PROJECT_LOCAL_ONTOLOGY_DECISION_IMPORT_REVIEW_LANE)" \
		$(SPECSPACE_PROJECT_LOCAL_ONTOLOGY_DECISION_IMPORT_WORKSPACE_ID_ARG) \
		--output "$(SPECSPACE_PROJECT_LOCAL_ONTOLOGY_DECISION_IMPORT_OUTPUT)" \
		$(SPECSPACE_PROJECT_LOCAL_ONTOLOGY_DECISION_IMPORT_STRICT_ARG)

.PHONY: project-local-ontology-decision-effect-report
project-local-ontology-decision-effect-report:
	@$(PYTHON) tools/project_local_ontology_decision_effect_report.py \
		--review-lane "$(PROJECT_LOCAL_ONTOLOGY_DECISION_EFFECT_REVIEW_LANE)" \
		--import-preview "$(PROJECT_LOCAL_ONTOLOGY_DECISION_EFFECT_IMPORT_PREVIEW)" \
		--output "$(PROJECT_LOCAL_ONTOLOGY_DECISION_EFFECT_OUTPUT)" \
		$(PROJECT_LOCAL_ONTOLOGY_DECISION_EFFECT_STRICT_ARG)

.PHONY: idea-to-spec-answer-rerun-input
idea-to-spec-answer-rerun-input:
	@$(PYTHON) tools/idea_to_spec_answer_rerun_input.py --answers "$(IDEA_TO_SPEC_ANSWER_RERUN_INPUT_ANSWERS)" $(IDEA_TO_SPEC_ANSWER_RERUN_INPUT_ONTOLOGY_DECISIONS_ARG) --output "$(IDEA_TO_SPEC_ANSWER_RERUN_INPUT_OUTPUT)"

.PHONY: idea-to-spec-rerun-preview
idea-to-spec-rerun-preview:
	@$(PYTHON) tools/idea_to_spec_rerun_preview.py --rerun-input "$(IDEA_TO_SPEC_RERUN_PREVIEW_INPUT)" --intake "$(IDEA_TO_SPEC_RERUN_PREVIEW_INTAKE)" --candidate-graph "$(IDEA_TO_SPEC_RERUN_PREVIEW_CANDIDATE_GRAPH)" --output "$(IDEA_TO_SPEC_RERUN_PREVIEW_OUTPUT)"

.PHONY: idea-to-spec-rerun-materialization
idea-to-spec-rerun-materialization:
	@$(PYTHON) tools/idea_to_spec_rerun_materialization.py --rerun-preview "$(IDEA_TO_SPEC_RERUN_MATERIALIZATION_PREVIEW)" --candidate-graph "$(IDEA_TO_SPEC_RERUN_MATERIALIZATION_CANDIDATE_GRAPH)" --output "$(IDEA_TO_SPEC_RERUN_MATERIALIZATION_OUTPUT)"

.PHONY: repaired-candidate-promotion-handoff
repaired-candidate-promotion-handoff:
	@$(PYTHON) tools/repaired_candidate_promotion_handoff.py --intake "$(REPAIRED_CANDIDATE_PROMOTION_HANDOFF_INTAKE)" --clarification-requests "$(REPAIRED_CANDIDATE_PROMOTION_HANDOFF_CLARIFICATION_REQUESTS)" --clarification-answers "$(REPAIRED_CANDIDATE_PROMOTION_HANDOFF_CLARIFICATION_ANSWERS)" --ontology-decisions "$(REPAIRED_CANDIDATE_PROMOTION_HANDOFF_ONTOLOGY_DECISIONS)" --rerun-input "$(REPAIRED_CANDIDATE_PROMOTION_HANDOFF_RERUN_INPUT)" --rerun-preview "$(REPAIRED_CANDIDATE_PROMOTION_HANDOFF_RERUN_PREVIEW)" --rerun-materialization "$(REPAIRED_CANDIDATE_PROMOTION_HANDOFF_RERUN_MATERIALIZATION)" --repaired-candidate-graph-output "$(REPAIRED_CANDIDATE_PROMOTION_HANDOFF_CANDIDATE_GRAPH_OUTPUT)" --repaired-pre-sib-output "$(REPAIRED_CANDIDATE_PROMOTION_HANDOFF_PRE_SIB_OUTPUT)" --repaired-repair-loop-output "$(REPAIRED_CANDIDATE_PROMOTION_HANDOFF_REPAIR_LOOP_OUTPUT)" --repaired-materialization-output-dir "$(REPAIRED_CANDIDATE_PROMOTION_HANDOFF_MATERIALIZATION_OUTPUT_DIR)" --repaired-materialization-output "$(REPAIRED_CANDIDATE_PROMOTION_HANDOFF_MATERIALIZATION_OUTPUT)" --repaired-promotion-gate-output "$(REPAIRED_CANDIDATE_PROMOTION_HANDOFF_PROMOTION_GATE_OUTPUT)" --repaired-active-candidate-output "$(REPAIRED_CANDIDATE_PROMOTION_HANDOFF_ACTIVE_CANDIDATE_OUTPUT)" --repaired-repair-session-output "$(REPAIRED_CANDIDATE_PROMOTION_HANDOFF_REPAIR_SESSION_OUTPUT)" --operator-ref "$(REPAIRED_CANDIDATE_PROMOTION_HANDOFF_OPERATOR_REF)" $(REPAIRED_CANDIDATE_PROMOTION_HANDOFF_SESSION_ID_ARG) --output "$(REPAIRED_CANDIDATE_PROMOTION_HANDOFF_OUTPUT)" $(REPAIRED_CANDIDATE_PROMOTION_HANDOFF_STRICT_ARG)

.PHONY: idea-to-spec-repair-session-journal
idea-to-spec-repair-session-journal:
	@$(PYTHON) tools/idea_to_spec_repair_session_journal.py $(IDEA_TO_SPEC_REPAIR_SESSION_JOURNAL_ARGS)

.PHONY: idea-to-spec-initial-repair-session-journal
idea-to-spec-initial-repair-session-journal:
	@$(PYTHON) tools/idea_to_spec_repair_session_journal.py $(IDEA_TO_SPEC_REPAIR_SESSION_JOURNAL_ARGS) --allow-missing-repair-artifacts

.PHONY: specspace-repair-draft-import-preview
specspace-repair-draft-import-preview:
	@$(PYTHON) tools/specspace_repair_draft_import_preview.py --drafts "$(SPECSPACE_REPAIR_DRAFT_IMPORT_DRAFTS)" --repair-session "$(SPECSPACE_REPAIR_DRAFT_IMPORT_REPAIR_SESSION)" --clarification-requests "$(SPECSPACE_REPAIR_DRAFT_IMPORT_CLARIFICATION_REQUESTS)" $(SPECSPACE_REPAIR_DRAFT_IMPORT_WORKSPACE_ID_ARG) --output "$(SPECSPACE_REPAIR_DRAFT_IMPORT_OUTPUT)"

.PHONY: specspace-repair-rerun-request-gate
specspace-repair-rerun-request-gate:
	@$(PYTHON) tools/specspace_repair_rerun_request_gate.py --request-state "$(SPECSPACE_REPAIR_RERUN_REQUEST_STATE)" --import-preview "$(SPECSPACE_REPAIR_RERUN_REQUEST_IMPORT_PREVIEW)" --repair-session "$(SPECSPACE_REPAIR_RERUN_REQUEST_REPAIR_SESSION)" $(SPECSPACE_REPAIR_RERUN_REQUEST_WORKSPACE_ID_ARG) --output "$(SPECSPACE_REPAIR_RERUN_REQUEST_OUTPUT)" $(SPECSPACE_REPAIR_RERUN_REQUEST_STRICT_ARG)

.PHONY: specspace-repair-draft-rerun-artifacts
specspace-repair-draft-rerun-artifacts:
	@$(PYTHON) tools/specspace_repair_drafts_to_rerun_artifacts.py --import-preview "$(SPECSPACE_REPAIR_DRAFT_RERUN_IMPORT_PREVIEW)" --repair-session "$(SPECSPACE_REPAIR_DRAFT_RERUN_REPAIR_SESSION)" --clarification-requests "$(SPECSPACE_REPAIR_DRAFT_RERUN_CLARIFICATION_REQUESTS)" --active-candidate "$(SPECSPACE_REPAIR_DRAFT_RERUN_ACTIVE_CANDIDATE)" --intake "$(SPECSPACE_REPAIR_DRAFT_RERUN_INTAKE)" --candidate-graph "$(SPECSPACE_REPAIR_DRAFT_RERUN_CANDIDATE_GRAPH)" --promotion-gate "$(SPECSPACE_REPAIR_DRAFT_RERUN_PROMOTION_GATE)" --clarification-answers-output "$(IDEA_TO_SPEC_CLARIFICATION_ANSWERS_OUTPUT)" --ontology-decisions-output "$(PRODUCT_ONTOLOGY_GAP_REVIEW_DECISIONS_OUTPUT)" --rerun-input-output "$(IDEA_TO_SPEC_ANSWER_RERUN_INPUT_OUTPUT)" --rerun-preview-output "$(IDEA_TO_SPEC_RERUN_PREVIEW_OUTPUT)" --rerun-materialization-output "$(IDEA_TO_SPEC_RERUN_MATERIALIZATION_OUTPUT)" --repair-session-output "$(IDEA_TO_SPEC_REPAIR_SESSION_OUTPUT)" --report-output "$(SPECSPACE_REPAIR_DRAFT_RERUN_REPORT_OUTPUT)" --operator-ref "$(IDEA_TO_SPEC_REPAIR_SESSION_OPERATOR_REF)"

.PHONY: product-workspace-repair-draft-rerun
product-workspace-repair-draft-rerun:
	@$(MAKE) specspace-repair-draft-import-preview SPECSPACE_REPAIR_DRAFT_IMPORT_OUTPUT="$(SPECSPACE_REPAIR_DRAFT_RERUN_IMPORT_PREVIEW)"
	@$(MAKE) specspace-repair-draft-rerun-artifacts

.PHONY: product-workspace-requested-repair-draft-rerun
product-workspace-requested-repair-draft-rerun:
	@$(MAKE) specspace-repair-draft-import-preview SPECSPACE_REPAIR_DRAFT_IMPORT_OUTPUT="$(SPECSPACE_REPAIR_RERUN_REQUEST_IMPORT_PREVIEW)" SPECSPACE_REPAIR_DRAFT_IMPORT_REPAIR_SESSION="$(SPECSPACE_REPAIR_RERUN_REQUEST_REPAIR_SESSION)" SPECSPACE_REPAIR_DRAFT_IMPORT_WORKSPACE_ID="$(SPECSPACE_REPAIR_RERUN_REQUEST_WORKSPACE_ID)"
	@$(MAKE) specspace-repair-rerun-request-gate SPECSPACE_REPAIR_RERUN_REQUEST_STRICT=1
	@$(MAKE) specspace-repair-draft-rerun-artifacts SPECSPACE_REPAIR_DRAFT_RERUN_IMPORT_PREVIEW="$(SPECSPACE_REPAIR_RERUN_REQUEST_IMPORT_PREVIEW)" SPECSPACE_REPAIR_DRAFT_RERUN_REPAIR_SESSION="$(SPECSPACE_REPAIR_RERUN_REQUEST_REPAIR_SESSION)"

.PHONY: product-workspace-repair-pack-state
product-workspace-repair-pack-state:
	@$(PYTHON) tools/product_workspace_repair_pack.py --pack "$(PRODUCT_WORKSPACE_REPAIR_PACK)" --repair-session "$(PRODUCT_WORKSPACE_REPAIR_PACK_REPAIR_SESSION)" --clarification-requests "$(PRODUCT_WORKSPACE_REPAIR_PACK_CLARIFICATION_REQUESTS)" --drafts-output "$(PRODUCT_WORKSPACE_REPAIR_PACK_DRAFTS_OUTPUT)" --request-state-output "$(PRODUCT_WORKSPACE_REPAIR_PACK_REQUEST_STATE_OUTPUT)" --import-preview-ref "$(PRODUCT_WORKSPACE_REPAIR_PACK_IMPORT_PREVIEW_REF)" --rerun-report-ref "$(PRODUCT_WORKSPACE_REPAIR_PACK_RERUN_REPORT_REF)" $(PRODUCT_WORKSPACE_REPAIR_PACK_PROJECT_LOCAL_ONTOLOGY_ARGS)

.PHONY: product-workspace-happy-path-repair-pack
product-workspace-happy-path-repair-pack:
	@$(MAKE) product-workspace-decision-backed-repair-chain \
		IDEA_MATURITY_METRICS_REPAIRED_HANDOFF="$(PRODUCT_WORKSPACE_REPAIR_PACK_ABSENT_ARTIFACT_DIR)/repaired_candidate_promotion_handoff_report.json" \
		IDEA_MATURITY_METRICS_REPAIRED_CANDIDATE_GRAPH="$(PRODUCT_WORKSPACE_REPAIR_PACK_ABSENT_ARTIFACT_DIR)/repaired_candidate_spec_graph.json" \
		IDEA_MATURITY_METRICS_REPAIRED_PRE_SIB="$(PRODUCT_WORKSPACE_REPAIR_PACK_ABSENT_ARTIFACT_DIR)/repaired_pre_sib_coherence_report.json" \
		IDEA_MATURITY_METRICS_REPAIRED_ACTIVE_CANDIDATE="$(PRODUCT_WORKSPACE_REPAIR_PACK_ABSENT_ARTIFACT_DIR)/repaired_active_idea_to_spec_candidate.json" \
		IDEA_MATURITY_METRICS_REPAIRED_PROMOTION_GATE="$(PRODUCT_WORKSPACE_REPAIR_PACK_ABSENT_ARTIFACT_DIR)/repaired_idea_to_spec_promotion_gate.json" \
		IDEA_MATURITY_METRICS_REPAIRED_REPAIR_SESSION="$(PRODUCT_WORKSPACE_REPAIR_PACK_ABSENT_ARTIFACT_DIR)/repaired_idea_to_spec_repair_session.json" \
		IDEA_MATURITY_METRICS_SPECSPACE_DRAFT_IMPORT_PREVIEW="$(PRODUCT_WORKSPACE_REPAIR_PACK_ABSENT_ARTIFACT_DIR)/specspace_repair_draft_import_preview.json" \
		IDEA_MATURITY_METRICS_SPECSPACE_RERUN_REQUEST="$(PRODUCT_WORKSPACE_REPAIR_PACK_ABSENT_ARTIFACT_DIR)/idea_to_spec_repair_rerun_requests.json" \
		IDEA_MATURITY_METRICS_APPROVAL_INTENT="$(PRODUCT_WORKSPACE_REPAIR_PACK_ABSENT_ARTIFACT_DIR)/idea_to_spec_candidate_approval_intents.json" \
		IDEA_MATURITY_METRICS_REPAIR_RERUN_EXECUTION="$(PRODUCT_WORKSPACE_REPAIR_PACK_ABSENT_ARTIFACT_DIR)/platform_product_repair_rerun_execution_report.json" \
		IDEA_MATURITY_METRICS_REPAIR_RERUN_PUBLICATION="$(PRODUCT_WORKSPACE_REPAIR_PACK_ABSENT_ARTIFACT_DIR)/platform_product_repair_rerun_publication_report.json" \
		IDEA_MATURITY_METRICS_PROJECT_LOCAL_ONTOLOGY_DECISION_EFFECT="$(PRODUCT_WORKSPACE_REPAIR_PACK_ABSENT_ARTIFACT_DIR)/project_local_ontology_decision_effect_report.json" \
		IDEA_MATURITY_METRICS_APPROVAL_EXECUTION="$(PRODUCT_WORKSPACE_REPAIR_PACK_ABSENT_ARTIFACT_DIR)/platform_candidate_approval_execution_report.json" \
		IDEA_MATURITY_METRICS_CANDIDATE_APPROVAL_DECISION="$(PRODUCT_WORKSPACE_REPAIR_PACK_ABSENT_ARTIFACT_DIR)/candidate_approval_decision.json" \
		IDEA_MATURITY_METRICS_PROMOTION_REQUEST="$(PRODUCT_WORKSPACE_REPAIR_PACK_ABSENT_ARTIFACT_DIR)/graph_repository_promotion_request.json" \
		IDEA_MATURITY_METRICS_PROMOTION_EXECUTION="$(PRODUCT_WORKSPACE_REPAIR_PACK_ABSENT_ARTIFACT_DIR)/product_candidate_promotion_execution_report.json" \
		IDEA_MATURITY_METRICS_REVIEW_STATUS="$(PRODUCT_WORKSPACE_REPAIR_PACK_ABSENT_ARTIFACT_DIR)/product_candidate_promotion_review_status_report.json" \
		IDEA_MATURITY_METRICS_READ_MODEL_PUBLICATION="$(PRODUCT_WORKSPACE_REPAIR_PACK_ABSENT_ARTIFACT_DIR)/product_candidate_promotion_read_model_publication_report.json"
	@$(MAKE) product-workspace-repair-pack-state PRODUCT_WORKSPACE_REPAIR_PACK_PROJECT_LOCAL_ONTOLOGY_LANE="$(PROJECT_LOCAL_ONTOLOGY_REVIEW_OUTPUT)" PRODUCT_WORKSPACE_REPAIR_PACK_PROJECT_LOCAL_ONTOLOGY_DECISIONS_OUTPUT="$(SPECSPACE_PROJECT_LOCAL_ONTOLOGY_DECISION_IMPORT_STATE)"
	@$(MAKE) specspace-project-local-ontology-decision-import-preview SPECSPACE_PROJECT_LOCAL_ONTOLOGY_DECISION_IMPORT_REVIEW_LANE="$(PROJECT_LOCAL_ONTOLOGY_REVIEW_OUTPUT)" SPECSPACE_PROJECT_LOCAL_ONTOLOGY_DECISION_IMPORT_WORKSPACE_ID="$(PRODUCT_WORKSPACE_REPAIR_PACK_WORKSPACE_ID)"
	@$(MAKE) project-local-ontology-decision-effect-report PROJECT_LOCAL_ONTOLOGY_DECISION_EFFECT_REVIEW_LANE="$(PROJECT_LOCAL_ONTOLOGY_REVIEW_OUTPUT)" PROJECT_LOCAL_ONTOLOGY_DECISION_EFFECT_IMPORT_PREVIEW="$(SPECSPACE_PROJECT_LOCAL_ONTOLOGY_DECISION_IMPORT_OUTPUT)"
	@$(MAKE) product-workspace-requested-repair-draft-rerun \
		SPECSPACE_REPAIR_DRAFT_IMPORT_DRAFTS="$(PRODUCT_WORKSPACE_REPAIR_PACK_DRAFTS_OUTPUT)" \
		SPECSPACE_REPAIR_RERUN_REQUEST_STATE="$(PRODUCT_WORKSPACE_REPAIR_PACK_REQUEST_STATE_OUTPUT)" \
		SPECSPACE_REPAIR_RERUN_REQUEST_IMPORT_PREVIEW="$(PRODUCT_WORKSPACE_REPAIR_PACK_IMPORT_PREVIEW_REF)" \
		SPECSPACE_REPAIR_RERUN_REQUEST_OUTPUT="$(PRODUCT_WORKSPACE_REPAIR_PACK_REQUEST_GATE_OUTPUT)" \
		SPECSPACE_REPAIR_DRAFT_RERUN_REPORT_OUTPUT="$(PRODUCT_WORKSPACE_REPAIR_PACK_RERUN_REPORT_REF)" \
		SPECSPACE_REPAIR_RERUN_REQUEST_WORKSPACE_ID="$(PRODUCT_WORKSPACE_REPAIR_PACK_WORKSPACE_ID)"
	@$(MAKE) product-workspace-repaired-promotion-handoff
	@$(MAKE) product-workspace-idea-maturity IDEA_MATURITY_METRICS_PROJECT_LOCAL_ONTOLOGY_DECISION_EFFECT="$(PROJECT_LOCAL_ONTOLOGY_DECISION_EFFECT_OUTPUT)" IDEA_MATURITY_METRICS_APPROVAL_INTENT="$(PRODUCT_WORKSPACE_REPAIR_PACK_ABSENT_ARTIFACT_DIR)/idea_to_spec_candidate_approval_intents.json" IDEA_MATURITY_METRICS_REPAIR_RERUN_EXECUTION="$(PRODUCT_WORKSPACE_REPAIR_PACK_ABSENT_ARTIFACT_DIR)/platform_product_repair_rerun_execution_report.json" IDEA_MATURITY_METRICS_REPAIR_RERUN_PUBLICATION="$(PRODUCT_WORKSPACE_REPAIR_PACK_ABSENT_ARTIFACT_DIR)/platform_product_repair_rerun_publication_report.json" IDEA_MATURITY_METRICS_APPROVAL_EXECUTION="$(PRODUCT_WORKSPACE_REPAIR_PACK_ABSENT_ARTIFACT_DIR)/platform_candidate_approval_execution_report.json" IDEA_MATURITY_METRICS_CANDIDATE_APPROVAL_DECISION="$(PRODUCT_WORKSPACE_REPAIR_PACK_ABSENT_ARTIFACT_DIR)/candidate_approval_decision.json" IDEA_MATURITY_METRICS_PROMOTION_REQUEST="$(PRODUCT_WORKSPACE_REPAIR_PACK_ABSENT_ARTIFACT_DIR)/graph_repository_promotion_request.json" IDEA_MATURITY_METRICS_PROMOTION_EXECUTION="$(PRODUCT_WORKSPACE_REPAIR_PACK_ABSENT_ARTIFACT_DIR)/product_candidate_promotion_execution_report.json" IDEA_MATURITY_METRICS_REVIEW_STATUS="$(PRODUCT_WORKSPACE_REPAIR_PACK_ABSENT_ARTIFACT_DIR)/product_candidate_promotion_review_status_report.json" IDEA_MATURITY_METRICS_READ_MODEL_PUBLICATION="$(PRODUCT_WORKSPACE_REPAIR_PACK_ABSENT_ARTIFACT_DIR)/product_candidate_promotion_read_model_publication_report.json"
	@$(MAKE) candidate-overview

.PHONY: product-workspace-team-decision-log-happy-path-repair-pack
product-workspace-team-decision-log-happy-path-repair-pack:
	@$(MAKE) product-workspace-happy-path-repair-pack

.PHONY: specspace-repair-draft-rerun
specspace-repair-draft-rerun: product-workspace-repair-draft-rerun

.PHONY: candidate-spec-materialization
candidate-spec-materialization:
	@$(PYTHON) tools/candidate_spec_materialization.py --candidate-graph "$(CANDIDATE_SPEC_MATERIALIZATION_CANDIDATE_GRAPH)" --repair-loop "$(CANDIDATE_SPEC_MATERIALIZATION_REPAIR_LOOP)" --output-dir "$(CANDIDATE_SPEC_MATERIALIZATION_OUTPUT_DIR)" --output "$(CANDIDATE_SPEC_MATERIALIZATION_OUTPUT)"

.PHONY: idea-to-spec-promotion-gate
idea-to-spec-promotion-gate:
	@$(PYTHON) tools/idea_to_spec_promotion_gate.py --pre-sib "$(IDEA_TO_SPEC_PROMOTION_GATE_PRE_SIB)" --repair-loop "$(IDEA_TO_SPEC_PROMOTION_GATE_REPAIR_LOOP)" --materialization "$(IDEA_TO_SPEC_PROMOTION_GATE_MATERIALIZATION)" --output "$(IDEA_TO_SPEC_PROMOTION_GATE_OUTPUT)"

.PHONY: active-idea-to-spec-candidate-source
active-idea-to-spec-candidate-source:
	@$(PYTHON) tools/active_idea_to_spec_candidate_source.py $(ACTIVE_IDEA_TO_SPEC_CANDIDATE_CONFIG_ARGS) --output "$(ACTIVE_IDEA_TO_SPEC_CANDIDATE_OUTPUT)"

.PHONY: candidate-approval-decision
candidate-approval-decision:
	@$(PYTHON) tools/candidate_approval_decision.py --active-candidate "$(CANDIDATE_APPROVAL_ACTIVE_CANDIDATE)" --promotion-gate "$(CANDIDATE_APPROVAL_PROMOTION_GATE)" --decision "$(CANDIDATE_APPROVAL_DECISION_STATE)" --operator-ref "$(CANDIDATE_APPROVAL_OPERATOR_REF)" --reason "$(CANDIDATE_APPROVAL_REASON)" --output "$(CANDIDATE_APPROVAL_OUTPUT)"

.PHONY: idea-maturity-metrics
idea-maturity-metrics:
	@$(PYTHON) tools/idea_maturity_metrics_report.py --intake "$(IDEA_MATURITY_METRICS_INTAKE)" --candidate-graph "$(IDEA_MATURITY_METRICS_CANDIDATE_GRAPH)" --pre-sib "$(IDEA_MATURITY_METRICS_PRE_SIB)" --clarification-requests "$(IDEA_MATURITY_METRICS_CLARIFICATION_REQUESTS)" --clarification-answers "$(IDEA_MATURITY_METRICS_CLARIFICATION_ANSWERS)" --ontology-decisions "$(IDEA_MATURITY_METRICS_ONTOLOGY_DECISIONS)" --rerun-input "$(IDEA_MATURITY_METRICS_RERUN_INPUT)" --rerun-preview "$(IDEA_MATURITY_METRICS_RERUN_PREVIEW)" --rerun-materialization "$(IDEA_MATURITY_METRICS_RERUN_MATERIALIZATION)" --promotion-gate "$(IDEA_MATURITY_METRICS_PROMOTION_GATE)" --repair-session "$(IDEA_MATURITY_METRICS_REPAIR_SESSION)" --repaired-handoff "$(IDEA_MATURITY_METRICS_REPAIRED_HANDOFF)" --repaired-candidate-graph "$(IDEA_MATURITY_METRICS_REPAIRED_CANDIDATE_GRAPH)" --repaired-pre-sib "$(IDEA_MATURITY_METRICS_REPAIRED_PRE_SIB)" --repaired-active-candidate "$(IDEA_MATURITY_METRICS_REPAIRED_ACTIVE_CANDIDATE)" --repaired-promotion-gate "$(IDEA_MATURITY_METRICS_REPAIRED_PROMOTION_GATE)" --repaired-repair-session "$(IDEA_MATURITY_METRICS_REPAIRED_REPAIR_SESSION)" --specspace-draft-import-preview "$(IDEA_MATURITY_METRICS_SPECSPACE_DRAFT_IMPORT_PREVIEW)" --specspace-rerun-request "$(IDEA_MATURITY_METRICS_SPECSPACE_RERUN_REQUEST)" --project-local-ontology-decision-effect "$(IDEA_MATURITY_METRICS_PROJECT_LOCAL_ONTOLOGY_DECISION_EFFECT)" --approval-intent "$(IDEA_MATURITY_METRICS_APPROVAL_INTENT)" --repair-rerun-execution "$(IDEA_MATURITY_METRICS_REPAIR_RERUN_EXECUTION)" --repair-rerun-publication "$(IDEA_MATURITY_METRICS_REPAIR_RERUN_PUBLICATION)" --approval-execution "$(IDEA_MATURITY_METRICS_APPROVAL_EXECUTION)" --candidate-approval-decision "$(IDEA_MATURITY_METRICS_CANDIDATE_APPROVAL_DECISION)" --promotion-request "$(IDEA_MATURITY_METRICS_PROMOTION_REQUEST)" --promotion-execution "$(IDEA_MATURITY_METRICS_PROMOTION_EXECUTION)" --review-status "$(IDEA_MATURITY_METRICS_REVIEW_STATUS)" --read-model-publication "$(IDEA_MATURITY_METRICS_READ_MODEL_PUBLICATION)" --output "$(IDEA_MATURITY_METRICS_OUTPUT)" $(IDEA_MATURITY_METRICS_STRICT_ARG)

.PHONY: idea-maturity-metrics-validate
idea-maturity-metrics-validate:
	@$(METRICS_CLI) validate idea-maturity "$(IDEA_MATURITY_METRICS_OUTPUT)" --output "$(IDEA_MATURITY_METRICS_VALIDATION_OUTPUT)"

.PHONY: product-workspace-idea-maturity
product-workspace-idea-maturity:
	@$(MAKE) idea-maturity-metrics
	@$(MAKE) idea-maturity-metrics-validate

.PHONY: candidate-overview
candidate-overview:
	@$(PYTHON) tools/candidate_overview.py --intake "$(CANDIDATE_OVERVIEW_INTAKE)" --candidate-graph "$(CANDIDATE_OVERVIEW_CANDIDATE_GRAPH)" --repaired-candidate-graph "$(CANDIDATE_OVERVIEW_REPAIRED_CANDIDATE_GRAPH)" --repair-session "$(CANDIDATE_OVERVIEW_REPAIR_SESSION)" --repaired-repair-session "$(CANDIDATE_OVERVIEW_REPAIRED_REPAIR_SESSION)" --idea-maturity "$(CANDIDATE_OVERVIEW_IDEA_MATURITY)" --project-local-ontology-lane "$(CANDIDATE_OVERVIEW_PROJECT_LOCAL_ONTOLOGY_LANE)" --project-local-ontology-effect "$(CANDIDATE_OVERVIEW_PROJECT_LOCAL_ONTOLOGY_EFFECT)" --ontology-package-index "$(CANDIDATE_OVERVIEW_ONTOLOGY_PACKAGE_INDEX)" --ontology-compatibility-diff "$(CANDIDATE_OVERVIEW_ONTOLOGY_COMPATIBILITY_DIFF)" --repaired-handoff "$(CANDIDATE_OVERVIEW_REPAIRED_HANDOFF)" --output "$(CANDIDATE_OVERVIEW_OUTPUT)" $(CANDIDATE_OVERVIEW_STRICT_ARG)

.PHONY: hosted-managed-publication-lifecycle-refresh
hosted-managed-publication-lifecycle-refresh:
	@$(MAKE) product-workspace-idea-maturity \
		IDEA_MATURITY_METRICS_INTAKE="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/idea_event_storming_intake.json" \
		IDEA_MATURITY_METRICS_CANDIDATE_GRAPH="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/candidate_spec_graph.json" \
		IDEA_MATURITY_METRICS_PRE_SIB="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/pre_sib_coherence_report.json" \
		IDEA_MATURITY_METRICS_CLARIFICATION_REQUESTS="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/idea_to_spec_clarification_requests.json" \
		IDEA_MATURITY_METRICS_CLARIFICATION_ANSWERS="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/idea_to_spec_clarification_answers.json" \
		IDEA_MATURITY_METRICS_ONTOLOGY_DECISIONS="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/product_ontology_gap_review_decisions.json" \
		IDEA_MATURITY_METRICS_RERUN_INPUT="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/idea_to_spec_answer_rerun_input.json" \
		IDEA_MATURITY_METRICS_RERUN_PREVIEW="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/idea_to_spec_rerun_preview.json" \
		IDEA_MATURITY_METRICS_RERUN_MATERIALIZATION="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/idea_to_spec_rerun_materialization.json" \
		IDEA_MATURITY_METRICS_PROMOTION_GATE="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/idea_to_spec_promotion_gate.json" \
		IDEA_MATURITY_METRICS_REPAIR_SESSION="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/idea_to_spec_repair_session.json" \
		IDEA_MATURITY_METRICS_REPAIRED_HANDOFF="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/repaired_candidate_promotion_handoff_report.json" \
		IDEA_MATURITY_METRICS_REPAIRED_CANDIDATE_GRAPH="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/repaired_candidate_spec_graph.json" \
		IDEA_MATURITY_METRICS_REPAIRED_PRE_SIB="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/repaired_pre_sib_coherence_report.json" \
		IDEA_MATURITY_METRICS_REPAIRED_ACTIVE_CANDIDATE="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/repaired_active_idea_to_spec_candidate.json" \
		IDEA_MATURITY_METRICS_REPAIRED_PROMOTION_GATE="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/repaired_idea_to_spec_promotion_gate.json" \
		IDEA_MATURITY_METRICS_REPAIRED_REPAIR_SESSION="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/repaired_idea_to_spec_repair_session.json" \
		IDEA_MATURITY_METRICS_SPECSPACE_DRAFT_IMPORT_PREVIEW="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/specspace_repair_draft_import_preview.json" \
		IDEA_MATURITY_METRICS_SPECSPACE_RERUN_REQUEST="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/idea_to_spec_repair_rerun_requests.json" \
		IDEA_MATURITY_METRICS_PROJECT_LOCAL_ONTOLOGY_DECISION_EFFECT="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/project_local_ontology_decision_effect_report.json" \
		IDEA_MATURITY_METRICS_APPROVAL_INTENT="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/idea_to_spec_candidate_approval_intents.json" \
		IDEA_MATURITY_METRICS_REPAIR_RERUN_EXECUTION="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/platform_product_repair_rerun_execution_report.json" \
		IDEA_MATURITY_METRICS_REPAIR_RERUN_PUBLICATION="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/platform_product_repair_rerun_publication_report.json" \
		IDEA_MATURITY_METRICS_APPROVAL_EXECUTION="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/platform_candidate_approval_execution_report.json" \
		IDEA_MATURITY_METRICS_CANDIDATE_APPROVAL_DECISION="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/candidate_approval_decision.json" \
		IDEA_MATURITY_METRICS_PROMOTION_REQUEST="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/graph_repository_promotion_request.json" \
		IDEA_MATURITY_METRICS_PROMOTION_EXECUTION="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/product_candidate_promotion_execution_report.json" \
		IDEA_MATURITY_METRICS_REVIEW_STATUS="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/product_candidate_promotion_review_status_report.json" \
		IDEA_MATURITY_METRICS_READ_MODEL_PUBLICATION="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/product_candidate_promotion_read_model_publication_report.json" \
		IDEA_MATURITY_METRICS_OUTPUT="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/idea_maturity_metrics_report.json" \
		IDEA_MATURITY_METRICS_VALIDATION_OUTPUT="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/idea_maturity_metrics_validation_report.json"
	@$(MAKE) candidate-overview \
		CANDIDATE_OVERVIEW_INTAKE="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/idea_event_storming_intake.json" \
		CANDIDATE_OVERVIEW_CANDIDATE_GRAPH="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/candidate_spec_graph.json" \
		CANDIDATE_OVERVIEW_REPAIRED_CANDIDATE_GRAPH="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/repaired_candidate_spec_graph.json" \
		CANDIDATE_OVERVIEW_REPAIR_SESSION="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/idea_to_spec_repair_session.json" \
		CANDIDATE_OVERVIEW_REPAIRED_REPAIR_SESSION="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/repaired_idea_to_spec_repair_session.json" \
		CANDIDATE_OVERVIEW_IDEA_MATURITY="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/idea_maturity_metrics_report.json" \
		CANDIDATE_OVERVIEW_PROJECT_LOCAL_ONTOLOGY_LANE="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/project_local_ontology_review_lane.json" \
		CANDIDATE_OVERVIEW_PROJECT_LOCAL_ONTOLOGY_EFFECT="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/project_local_ontology_decision_effect_report.json" \
		CANDIDATE_OVERVIEW_ONTOLOGY_PACKAGE_INDEX="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/ontology_package_index.json" \
		CANDIDATE_OVERVIEW_ONTOLOGY_COMPATIBILITY_DIFF="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/ontology_compatibility_diff_preview.json" \
		CANDIDATE_OVERVIEW_REPAIRED_HANDOFF="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/repaired_candidate_promotion_handoff_report.json" \
		CANDIDATE_OVERVIEW_OUTPUT="$(HOSTED_MANAGED_PUBLICATION_RUN_DIR)/candidate_overview.json"

.PHONY: product-workspace-active-candidate
product-workspace-active-candidate:
ifeq ($(PRODUCT_WORKSPACE_INTAKE_SOURCE_MODE),generate)
	@$(PYTHON) tools/user_idea_intake_session.py --input "$(PRODUCT_WORKSPACE_IDEA_SOURCE)" --session-output "$(USER_IDEA_INTAKE_SESSION_OUTPUT)" --source-output "$(USER_IDEA_INTAKE_SESSION_SOURCE_OUTPUT)"
	@test -f "$(USER_IDEA_INTAKE_SESSION_SOURCE_OUTPUT)" || ($(PYTHON) tools/idea_to_spec_clarification_requests.py --session "$(USER_IDEA_INTAKE_SESSION_OUTPUT)" --no-intake --no-candidate-graph --no-pre-sib --no-repair-loop $(IDEA_TO_SPEC_CLARIFICATION_ONTOLOGY_GAP_REVIEW_ARG) --output "$(IDEA_TO_SPEC_CLARIFICATION_OUTPUT)" && exit 1)
	@$(PYTHON) tools/user_idea_intake_source.py --input "$(USER_IDEA_INTAKE_SESSION_SOURCE_OUTPUT)" --output "$(PRODUCT_WORKSPACE_INTAKE_SOURCE)"
endif
	@if [ -f "$(PRODUCT_WORKSPACE_INTAKE_SOURCE)" ]; then $(PYTHON) -m json.tool "$(PRODUCT_WORKSPACE_INTAKE_SOURCE)" >/dev/null || (printf '%s\n' 'PRODUCT_WORKSPACE_INTAKE_SOURCE is not valid JSON.' >&2; exit 1); fi
	@$(PYTHON) -c 'import json,sys; from pathlib import Path; p=Path(sys.argv[1]); data=json.loads(p.read_text()) if p.exists() else {}; kind=data.get("artifact_kind") if isinstance(data, dict) else None; kind=="user_idea_intake_source" and (print("PRODUCT_WORKSPACE_INTAKE_SOURCE points to user_idea_intake_source. Build an event-storming seed first with `make user-idea-intake-source USER_IDEA_INTAKE_SOURCE=<source>` or use `make real-idea-intake-active-candidate`.", file=sys.stderr), sys.exit(2))' "$(PRODUCT_WORKSPACE_INTAKE_SOURCE)"
	@$(PYTHON) tools/idea_event_storming_intake.py --input "$(PRODUCT_WORKSPACE_INTAKE_SOURCE)" --output "$(IDEA_EVENT_STORMING_INTAKE_OUTPUT)"
ifeq ($(PRODUCT_WORKSPACE_CANDIDATE_SEED_MODE),generate)
	@$(PYTHON) tools/ontology_bound_candidate_graph_seed.py --intake "$(IDEA_EVENT_STORMING_INTAKE_OUTPUT)" --ontology-ir "$(ONTOLOGY_BOUND_CANDIDATE_SEED_ONTOLOGY_IR)" --output "$(PRODUCT_WORKSPACE_CANDIDATE_SEED_OUTPUT)"
endif
	@$(PYTHON) tools/candidate_spec_graph.py --intake "$(IDEA_EVENT_STORMING_INTAKE_OUTPUT)" --candidate-seed "$(PRODUCT_WORKSPACE_CANDIDATE_SEED_EFFECTIVE)" --output "$(CANDIDATE_SPEC_GRAPH_OUTPUT)"
	@$(PYTHON) tools/pre_sib_coherence_report.py --candidate-graph "$(CANDIDATE_SPEC_GRAPH_OUTPUT)" --output "$(PRE_SIB_COHERENCE_OUTPUT)"
	@$(PYTHON) tools/candidate_repair_loop.py --candidate-graph "$(CANDIDATE_SPEC_GRAPH_OUTPUT)" --pre-sib-report "$(PRE_SIB_COHERENCE_OUTPUT)" --output "$(CANDIDATE_REPAIR_LOOP_OUTPUT)"
	@$(PYTHON) tools/idea_to_spec_clarification_requests.py $(PRODUCT_WORKSPACE_CLARIFICATION_SESSION_ARG) --intake "$(IDEA_EVENT_STORMING_INTAKE_OUTPUT)" --candidate-graph "$(CANDIDATE_SPEC_GRAPH_OUTPUT)" --pre-sib "$(PRE_SIB_COHERENCE_OUTPUT)" --repair-loop "$(CANDIDATE_REPAIR_LOOP_OUTPUT)" $(IDEA_TO_SPEC_CLARIFICATION_ONTOLOGY_GAP_REVIEW_ARG) $(IDEA_TO_SPEC_CLARIFICATION_IDEA_MATURITY_ARG) --output "$(IDEA_TO_SPEC_CLARIFICATION_OUTPUT)"
	@$(PYTHON) tools/candidate_spec_materialization.py --candidate-graph "$(CANDIDATE_SPEC_GRAPH_OUTPUT)" --repair-loop "$(CANDIDATE_REPAIR_LOOP_OUTPUT)" --output-dir "$(CANDIDATE_SPEC_MATERIALIZATION_OUTPUT_DIR)" --output "$(CANDIDATE_SPEC_MATERIALIZATION_OUTPUT)"
	@$(PYTHON) tools/idea_to_spec_promotion_gate.py --pre-sib "$(PRE_SIB_COHERENCE_OUTPUT)" --repair-loop "$(CANDIDATE_REPAIR_LOOP_OUTPUT)" --materialization "$(CANDIDATE_SPEC_MATERIALIZATION_OUTPUT)" --output "$(IDEA_TO_SPEC_PROMOTION_GATE_OUTPUT)"
	@$(PYTHON) tools/active_idea_to_spec_candidate_source.py $(PRODUCT_WORKSPACE_ACTIVE_CANDIDATE_CONFIG_ARGS) $(PRODUCT_WORKSPACE_ACTIVE_CANDIDATE_ARTIFACT_ARGS) --output "$(ACTIVE_IDEA_TO_SPEC_CANDIDATE_OUTPUT)"

.PHONY: product-workspace-decision-backed-repair-chain
product-workspace-decision-backed-repair-chain:
	@$(MAKE) product-workspace-active-candidate
	@$(MAKE) idea-to-spec-clarification-answers
	@$(MAKE) product-ontology-gap-review-decisions PRODUCT_ONTOLOGY_GAP_REVIEW_DECISIONS_ANSWERS="$(IDEA_TO_SPEC_CLARIFICATION_ANSWERS_OUTPUT)"
	@$(MAKE) idea-to-spec-answer-rerun-input IDEA_TO_SPEC_ANSWER_RERUN_INPUT_ANSWERS="$(IDEA_TO_SPEC_CLARIFICATION_ANSWERS_OUTPUT)" IDEA_TO_SPEC_ANSWER_RERUN_INPUT_ONTOLOGY_DECISIONS="$(PRODUCT_ONTOLOGY_GAP_REVIEW_DECISIONS_OUTPUT)"
	@$(MAKE) idea-to-spec-rerun-preview IDEA_TO_SPEC_RERUN_PREVIEW_INPUT="$(IDEA_TO_SPEC_ANSWER_RERUN_INPUT_OUTPUT)" IDEA_TO_SPEC_RERUN_PREVIEW_INTAKE="$(IDEA_EVENT_STORMING_INTAKE_OUTPUT)" IDEA_TO_SPEC_RERUN_PREVIEW_CANDIDATE_GRAPH="$(CANDIDATE_SPEC_GRAPH_OUTPUT)"
	@$(MAKE) idea-to-spec-rerun-materialization IDEA_TO_SPEC_RERUN_MATERIALIZATION_PREVIEW="$(IDEA_TO_SPEC_RERUN_PREVIEW_OUTPUT)" IDEA_TO_SPEC_RERUN_MATERIALIZATION_CANDIDATE_GRAPH="$(CANDIDATE_SPEC_GRAPH_OUTPUT)"
	@$(MAKE) idea-to-spec-repair-session-journal IDEA_TO_SPEC_REPAIR_SESSION_ACTIVE_CANDIDATE="$(ACTIVE_IDEA_TO_SPEC_CANDIDATE_OUTPUT)" IDEA_TO_SPEC_REPAIR_SESSION_CLARIFICATION_REQUESTS="$(IDEA_TO_SPEC_CLARIFICATION_OUTPUT)" IDEA_TO_SPEC_REPAIR_SESSION_CLARIFICATION_ANSWERS="$(IDEA_TO_SPEC_CLARIFICATION_ANSWERS_OUTPUT)" IDEA_TO_SPEC_REPAIR_SESSION_ONTOLOGY_DECISIONS="$(PRODUCT_ONTOLOGY_GAP_REVIEW_DECISIONS_OUTPUT)" IDEA_TO_SPEC_REPAIR_SESSION_RERUN_INPUT="$(IDEA_TO_SPEC_ANSWER_RERUN_INPUT_OUTPUT)" IDEA_TO_SPEC_REPAIR_SESSION_RERUN_PREVIEW="$(IDEA_TO_SPEC_RERUN_PREVIEW_OUTPUT)" IDEA_TO_SPEC_REPAIR_SESSION_RERUN_MATERIALIZATION="$(IDEA_TO_SPEC_RERUN_MATERIALIZATION_OUTPUT)" IDEA_TO_SPEC_REPAIR_SESSION_PROMOTION_GATE="$(IDEA_TO_SPEC_PROMOTION_GATE_OUTPUT)"
	@$(MAKE) project-local-ontology-review-lane PROJECT_LOCAL_ONTOLOGY_REVIEW_CANDIDATE_GRAPH="$(CANDIDATE_SPEC_GRAPH_OUTPUT)" PROJECT_LOCAL_ONTOLOGY_REVIEW_DECISIONS="$(PRODUCT_ONTOLOGY_GAP_REVIEW_DECISIONS_OUTPUT)" PROJECT_LOCAL_ONTOLOGY_REVIEW_RERUN_PREVIEW="$(IDEA_TO_SPEC_RERUN_PREVIEW_OUTPUT)" PROJECT_LOCAL_ONTOLOGY_REVIEW_ACTIVE_CANDIDATE="$(ACTIVE_IDEA_TO_SPEC_CANDIDATE_OUTPUT)" PROJECT_LOCAL_ONTOLOGY_REVIEW_REPAIR_SESSION="$(IDEA_TO_SPEC_REPAIR_SESSION_OUTPUT)"
	@$(MAKE) product-workspace-idea-maturity

.PHONY: product-workspace-repaired-promotion-handoff
product-workspace-repaired-promotion-handoff:
	@$(MAKE) repaired-candidate-promotion-handoff \
		REPAIRED_CANDIDATE_PROMOTION_HANDOFF_INTAKE="$(call product_workspace_repaired_handoff_input,REPAIRED_CANDIDATE_PROMOTION_HANDOFF_INTAKE,IDEA_EVENT_STORMING_INTAKE_OUTPUT)" \
		REPAIRED_CANDIDATE_PROMOTION_HANDOFF_CLARIFICATION_REQUESTS="$(call product_workspace_repaired_handoff_input,REPAIRED_CANDIDATE_PROMOTION_HANDOFF_CLARIFICATION_REQUESTS,IDEA_TO_SPEC_CLARIFICATION_OUTPUT)" \
		REPAIRED_CANDIDATE_PROMOTION_HANDOFF_CLARIFICATION_ANSWERS="$(call product_workspace_repaired_handoff_input,REPAIRED_CANDIDATE_PROMOTION_HANDOFF_CLARIFICATION_ANSWERS,IDEA_TO_SPEC_CLARIFICATION_ANSWERS_OUTPUT)" \
		REPAIRED_CANDIDATE_PROMOTION_HANDOFF_ONTOLOGY_DECISIONS="$(call product_workspace_repaired_handoff_input,REPAIRED_CANDIDATE_PROMOTION_HANDOFF_ONTOLOGY_DECISIONS,PRODUCT_ONTOLOGY_GAP_REVIEW_DECISIONS_OUTPUT)" \
		REPAIRED_CANDIDATE_PROMOTION_HANDOFF_RERUN_INPUT="$(call product_workspace_repaired_handoff_input,REPAIRED_CANDIDATE_PROMOTION_HANDOFF_RERUN_INPUT,IDEA_TO_SPEC_ANSWER_RERUN_INPUT_OUTPUT)" \
		REPAIRED_CANDIDATE_PROMOTION_HANDOFF_RERUN_PREVIEW="$(call product_workspace_repaired_handoff_input,REPAIRED_CANDIDATE_PROMOTION_HANDOFF_RERUN_PREVIEW,IDEA_TO_SPEC_RERUN_PREVIEW_OUTPUT)" \
		REPAIRED_CANDIDATE_PROMOTION_HANDOFF_RERUN_MATERIALIZATION="$(call product_workspace_repaired_handoff_input,REPAIRED_CANDIDATE_PROMOTION_HANDOFF_RERUN_MATERIALIZATION,IDEA_TO_SPEC_RERUN_MATERIALIZATION_OUTPUT)"
	@$(MAKE) product-workspace-idea-maturity \
		IDEA_MATURITY_METRICS_INTAKE="$(call product_workspace_repaired_handoff_input,REPAIRED_CANDIDATE_PROMOTION_HANDOFF_INTAKE,IDEA_EVENT_STORMING_INTAKE_OUTPUT)" \
		IDEA_MATURITY_METRICS_CANDIDATE_GRAPH="$(CANDIDATE_SPEC_GRAPH_OUTPUT)" \
		IDEA_MATURITY_METRICS_PRE_SIB="$(PRE_SIB_COHERENCE_OUTPUT)" \
		IDEA_MATURITY_METRICS_CLARIFICATION_REQUESTS="$(call product_workspace_repaired_handoff_input,REPAIRED_CANDIDATE_PROMOTION_HANDOFF_CLARIFICATION_REQUESTS,IDEA_TO_SPEC_CLARIFICATION_OUTPUT)" \
		IDEA_MATURITY_METRICS_CLARIFICATION_ANSWERS="$(call product_workspace_repaired_handoff_input,REPAIRED_CANDIDATE_PROMOTION_HANDOFF_CLARIFICATION_ANSWERS,IDEA_TO_SPEC_CLARIFICATION_ANSWERS_OUTPUT)" \
		IDEA_MATURITY_METRICS_ONTOLOGY_DECISIONS="$(call product_workspace_repaired_handoff_input,REPAIRED_CANDIDATE_PROMOTION_HANDOFF_ONTOLOGY_DECISIONS,PRODUCT_ONTOLOGY_GAP_REVIEW_DECISIONS_OUTPUT)" \
		IDEA_MATURITY_METRICS_RERUN_INPUT="$(call product_workspace_repaired_handoff_input,REPAIRED_CANDIDATE_PROMOTION_HANDOFF_RERUN_INPUT,IDEA_TO_SPEC_ANSWER_RERUN_INPUT_OUTPUT)" \
		IDEA_MATURITY_METRICS_RERUN_PREVIEW="$(call product_workspace_repaired_handoff_input,REPAIRED_CANDIDATE_PROMOTION_HANDOFF_RERUN_PREVIEW,IDEA_TO_SPEC_RERUN_PREVIEW_OUTPUT)" \
		IDEA_MATURITY_METRICS_RERUN_MATERIALIZATION="$(call product_workspace_repaired_handoff_input,REPAIRED_CANDIDATE_PROMOTION_HANDOFF_RERUN_MATERIALIZATION,IDEA_TO_SPEC_RERUN_MATERIALIZATION_OUTPUT)" \
		IDEA_MATURITY_METRICS_PROMOTION_GATE="$(IDEA_TO_SPEC_PROMOTION_GATE_OUTPUT)" \
		IDEA_MATURITY_METRICS_REPAIR_SESSION="$(IDEA_TO_SPEC_REPAIR_SESSION_OUTPUT)" \
		IDEA_MATURITY_METRICS_REPAIRED_HANDOFF="$(REPAIRED_CANDIDATE_PROMOTION_HANDOFF_OUTPUT)" \
		IDEA_MATURITY_METRICS_REPAIRED_CANDIDATE_GRAPH="$(REPAIRED_CANDIDATE_PROMOTION_HANDOFF_CANDIDATE_GRAPH_OUTPUT)" \
		IDEA_MATURITY_METRICS_REPAIRED_PRE_SIB="$(REPAIRED_CANDIDATE_PROMOTION_HANDOFF_PRE_SIB_OUTPUT)" \
		IDEA_MATURITY_METRICS_REPAIRED_ACTIVE_CANDIDATE="$(REPAIRED_CANDIDATE_PROMOTION_HANDOFF_ACTIVE_CANDIDATE_OUTPUT)" \
		IDEA_MATURITY_METRICS_REPAIRED_PROMOTION_GATE="$(REPAIRED_CANDIDATE_PROMOTION_HANDOFF_PROMOTION_GATE_OUTPUT)" \
		IDEA_MATURITY_METRICS_REPAIRED_REPAIR_SESSION="$(REPAIRED_CANDIDATE_PROMOTION_HANDOFF_REPAIR_SESSION_OUTPUT)"

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
	@PRODUCT_WORKSPACE_IDEA_SOURCE="$(PRODUCT_WORKSPACE_IDEA_SOURCE)" USER_IDEA_EVENT_STORMING_SEED_OUTPUT="$(USER_IDEA_EVENT_STORMING_SEED_OUTPUT)" PRODUCT_WORKSPACE_INTAKE_SOURCE="$(PRODUCT_WORKSPACE_INTAKE_SOURCE)" PRODUCT_WORKSPACE_CANDIDATE_SEED="$(PRODUCT_WORKSPACE_CANDIDATE_SEED)" PRODUCT_WORKSPACE_CANDIDATE_SEED_INPUT="$(PRODUCT_WORKSPACE_CANDIDATE_SEED_INPUT)" PRODUCT_WORKSPACE_CANDIDATE_SEED_OUTPUT="$(PRODUCT_WORKSPACE_CANDIDATE_SEED_OUTPUT)" PRODUCT_WORKSPACE_ACTIVE_CANDIDATE_CONFIG="$(PRODUCT_WORKSPACE_ACTIVE_CANDIDATE_CONFIG)" PRODUCT_WORKSPACE_ACTIVE_CANDIDATE_REFRESH="$(PRODUCT_WORKSPACE_ACTIVE_CANDIDATE_REFRESH)" $(PYTHON) tools/build_static_artifact_bundle.py --refresh-publish-surfaces $(PUBLISH_BUNDLE_FLAGS)

.PHONY: test
test:
	@$(PYTEST) -q

.PHONY: test-supervisor
test-supervisor:
	@$(PYTEST) -q tests/test_supervisor.py
