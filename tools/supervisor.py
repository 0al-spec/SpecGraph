#!/usr/bin/env python3
"""Run the local SpecGraph supervisor.

The supervisor is a bootstrap orchestration tool for evolving spec nodes under
`specs/nodes/*.yaml`. It is intentionally policy-constrained:

- Canonical governance lives in spec nodes such as `SG-SPEC-0002` and
  `SG-SPEC-0003`.
- The supervisor executes bounded refinement and graph-maintenance work inside
  those rules.
- Human approval remains the authority for constitutional or governance-level
  changes.

Execution modes:
- default single-pass refinement: pick the next eligible node or queued
  graph_refactor and run one bounded pass
- explicit operator-targeted refinement: run one bounded pass for the exact
  `--target-spec` node, bypassing heuristic selection without bypassing
  validation or gate policy
- loop mode: repeat the same bounded pass selection until no eligible work
  remains
- gate resolution: apply a human decision to a previously queued review gate
- explicit split proposal mode: analyze one oversized non-seed spec and emit a
  structured proposal artifact under `runs/proposals/` without mutating
  canonical spec files
- explicit split proposal application: deterministically materialize one
  reviewed split proposal into canonical parent/child spec files

Derived artifacts:
- run logs: `runs/<RUN_ID>.json`
- latest summary: `runs/latest-summary.md`
- graph refactor queue: `runs/refactor_queue.json`
- proposal queue index: `runs/proposal_queue.json`
- structured proposal artifacts: `runs/proposals/*.json`
- intent-layer overlay: `runs/intent_layer_overlay.json`
- proposal-lane overlay: `runs/proposal_lane_overlay.json`
- graph health overlay: `runs/graph_health_overlay.json`
- spec trace index: `runs/spec_trace_index.json`
- spec trace projection: `runs/spec_trace_projection.json`
- proposal runtime index: `runs/proposal_runtime_index.json`
"""

from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import importlib.util
import inspect
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from types import ModuleType
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None

ROOT = Path.cwd()
TOOLS_DIR = Path(__file__).resolve().parent
SPECS_DIR = ROOT / "specs" / "nodes"
RUNS_DIR = ROOT / "runs"
WORKTREES_DIR = ROOT / ".worktrees"
AGENTS_FILE = ROOT / "AGENTS.md"
ARTIFACT_LOCK_TIMEOUT_SECONDS = 5.0
ARTIFACT_LOCK_POLL_SECONDS = 0.05
RUNTIME_ID_COLLISION_RETRY_LIMIT = 8
SUPERVISOR_POLICY_RELATIVE_PATH = "tools/supervisor_policy.json"
TECHSPEC_HANDOFF_POLICY_RELATIVE_PATH = "tools/techspec_handoff_policy.json"
PROPOSAL_LANE_POLICY_RELATIVE_PATH = "tools/proposal_lane_policy.json"
INTENT_LAYER_POLICY_RELATIVE_PATH = "tools/intent_layer_policy.json"


def supervisor_policy_path() -> Path:
    return TOOLS_DIR / "supervisor_policy.json"


def techspec_handoff_policy_path() -> Path:
    return TOOLS_DIR / "techspec_handoff_policy.json"


def proposal_lane_policy_path() -> Path:
    return TOOLS_DIR / "proposal_lane_policy.json"


def intent_layer_policy_path() -> Path:
    return TOOLS_DIR / "intent_layer_policy.json"


def load_supervisor_policy() -> tuple[dict[str, Any], str]:
    path = supervisor_policy_path()
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(
            f"failed to read supervisor policy artifact: {path.as_posix()} ({exc})"
        ) from exc
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"malformed supervisor policy artifact: {path.as_posix()} ({exc})"
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeError(
            f"malformed supervisor policy artifact: {path.as_posix()} must contain a JSON object"
        )
    required_sections = (
        "thresholds",
        "selection_priorities",
        "change_classification",
        "mutation_classes",
        "queue_policy",
        "execution_profiles",
    )
    missing = [section for section in required_sections if section not in payload]
    if missing:
        raise RuntimeError(
            "malformed supervisor policy artifact: missing top-level section(s): "
            + ", ".join(missing)
        )
    return payload, hashlib.sha256(raw_text.encode("utf-8")).hexdigest()


SUPERVISOR_POLICY, SUPERVISOR_POLICY_SHA256 = load_supervisor_policy()


def load_techspec_handoff_policy() -> tuple[dict[str, Any], str]:
    path = techspec_handoff_policy_path()
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(
            f"failed to read techspec handoff policy artifact: {path.as_posix()} ({exc})"
        ) from exc
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"malformed techspec handoff policy artifact: {path.as_posix()} ({exc})"
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeError(
            "malformed techspec handoff policy artifact: "
            f"{path.as_posix()} must contain a JSON object"
        )
    required_sections = ("boundary_model", "signal_contract", "handoff_packet")
    missing = [section for section in required_sections if section not in payload]
    if missing:
        raise RuntimeError(
            "malformed techspec handoff policy artifact: missing top-level section(s): "
            + ", ".join(missing)
        )
    return payload, hashlib.sha256(raw_text.encode("utf-8")).hexdigest()


TECHSPEC_HANDOFF_POLICY, TECHSPEC_HANDOFF_POLICY_SHA256 = load_techspec_handoff_policy()


def load_proposal_lane_policy() -> tuple[dict[str, Any], str]:
    path = proposal_lane_policy_path()
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(
            f"failed to read proposal lane policy artifact: {path.as_posix()} ({exc})"
        ) from exc
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"malformed proposal lane policy artifact: {path.as_posix()} ({exc})"
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeError(
            f"malformed proposal lane policy artifact: {path.as_posix()} must contain a JSON object"
        )
    required_sections = (
        "repository_layout",
        "node_contract",
        "authority_state_mapping",
        "overlay_contract",
    )
    missing = [section for section in required_sections if section not in payload]
    if missing:
        raise RuntimeError(
            "malformed proposal lane policy artifact: missing top-level section(s): "
            + ", ".join(missing)
        )
    return payload, hashlib.sha256(raw_text.encode("utf-8")).hexdigest()


PROPOSAL_LANE_POLICY, PROPOSAL_LANE_POLICY_SHA256 = load_proposal_lane_policy()


def load_intent_layer_policy() -> tuple[dict[str, Any], str]:
    path = intent_layer_policy_path()
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(
            f"failed to read intent layer policy artifact: {path.as_posix()} ({exc})"
        ) from exc
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"malformed intent layer policy artifact: {path.as_posix()} ({exc})"
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeError(
            f"malformed intent layer policy artifact: {path.as_posix()} must contain a JSON object"
        )
    required_sections = ("repository_layout", "node_contract", "overlay_contract")
    missing = [section for section in required_sections if section not in payload]
    if missing:
        raise RuntimeError(
            "malformed intent layer policy artifact: missing top-level section(s): "
            + ", ".join(missing)
        )
    return payload, hashlib.sha256(raw_text.encode("utf-8")).hexdigest()


INTENT_LAYER_POLICY, INTENT_LAYER_POLICY_SHA256 = load_intent_layer_policy()


def policy_lookup(policy_path: str) -> Any:
    current: Any = SUPERVISOR_POLICY
    for part in policy_path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(policy_path)
        current = current[part]
    return copy.deepcopy(current)


def techspec_handoff_policy_lookup(policy_path: str) -> Any:
    current: Any = TECHSPEC_HANDOFF_POLICY
    for part in policy_path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(policy_path)
        current = current[part]
    return copy.deepcopy(current)


def proposal_lane_policy_lookup(policy_path: str) -> Any:
    current: Any = PROPOSAL_LANE_POLICY
    for part in policy_path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(policy_path)
        current = current[part]
    return copy.deepcopy(current)


def intent_layer_policy_lookup(policy_path: str) -> Any:
    current: Any = INTENT_LAYER_POLICY
    for part in policy_path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(policy_path)
        current = current[part]
    return copy.deepcopy(current)


def policy_rule(
    policy_path: str,
    *,
    reason: str,
    matched_value: Any | None = None,
    inputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if matched_value is None:
        try:
            matched_value = policy_lookup(policy_path)
        except KeyError:
            matched_value = None
    return {
        "rule_source": "supervisor_policy",
        "rule_id": policy_path,
        "policy_path": policy_path,
        "reason": reason,
        "matched_value": matched_value,
        "inputs": copy.deepcopy(inputs or {}),
    }


def runtime_rule(
    rule_id: str,
    *,
    reason: str,
    matched_value: Any | None = None,
    inputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "rule_source": "runtime_guard",
        "rule_id": rule_id,
        "reason": reason,
        "matched_value": copy.deepcopy(matched_value),
        "inputs": copy.deepcopy(inputs or {}),
    }


def supervisor_policy_reference() -> dict[str, Any]:
    return {
        "artifact_path": SUPERVISOR_POLICY_RELATIVE_PATH,
        "artifact_sha256": SUPERVISOR_POLICY_SHA256,
        "version": SUPERVISOR_POLICY.get("version"),
    }


def techspec_handoff_policy_reference() -> dict[str, Any]:
    return {
        "artifact_path": TECHSPEC_HANDOFF_POLICY_RELATIVE_PATH,
        "artifact_sha256": TECHSPEC_HANDOFF_POLICY_SHA256,
        "version": TECHSPEC_HANDOFF_POLICY.get("version"),
    }


def proposal_lane_policy_reference() -> dict[str, Any]:
    return {
        "artifact_path": PROPOSAL_LANE_POLICY_RELATIVE_PATH,
        "artifact_sha256": PROPOSAL_LANE_POLICY_SHA256,
        "version": PROPOSAL_LANE_POLICY.get("version"),
    }


def intent_layer_policy_reference() -> dict[str, Any]:
    return {
        "artifact_path": INTENT_LAYER_POLICY_RELATIVE_PATH,
        "artifact_sha256": INTENT_LAYER_POLICY_SHA256,
        "version": INTENT_LAYER_POLICY.get("version"),
    }


READY_DEP_STATUSES = {"reviewed", "frozen"}
WORKABLE_STATUSES = {"outlined", "specified"}
CONTINUATION_STATUSES = {"linked"}
VALID_STATUSES = {"idea", "stub", "outlined", "specified", "linked", "reviewed", "frozen"}
ATOMICITY_MAX_ACCEPTANCE = int(policy_lookup("thresholds.atomicity_max_acceptance"))
ATOMICITY_MAX_BLOCKING_CHILDREN = int(policy_lookup("thresholds.atomicity_max_blocking_children"))
RECURRING_REFACTOR_PROPOSAL_THRESHOLD = int(policy_lookup("thresholds.recurring_refactor_proposal"))
SPLIT_REFACTOR_SIGNAL = "oversized_spec"
SPLIT_REFACTOR_KIND = "split_oversized_spec"
RETROSPECTIVE_REFACTOR_SIGNAL = "retrospective_refactor_candidate"
SUBTREE_SHAPE_SIGNALS = set(policy_lookup("queue_policy.subtree_shape_signals"))
LOWER_BOUNDARY_HANDOFF_SIGNALS = set(policy_lookup("queue_policy.lower_boundary_handoff_signals"))
TECHSPEC_HANDOFF_PRIMARY_SIGNAL = str(
    techspec_handoff_policy_lookup("signal_contract.primary_signal")
)
TECHSPEC_HANDOFF_REQUIRED_LOWER_BOUNDARY_SIGNALS = set(
    techspec_handoff_policy_lookup("signal_contract.required_lower_boundary_signals")
)
TECHSPEC_HANDOFF_SEMANTIC_SATURATION_SIGNALS = set(
    techspec_handoff_policy_lookup("signal_contract.semantic_saturation_signals")
)
TECHSPEC_HANDOFF_MIN_SEMANTIC_SATURATION_SIGNAL_COUNT = int(
    techspec_handoff_policy_lookup("signal_contract.minimum_semantic_saturation_signal_count")
)
TECHSPEC_HANDOFF_TARGET_LAYER = str(techspec_handoff_policy_lookup("boundary_model.target_layer"))
TECHSPEC_HANDOFF_RECOMMENDED_ACTION = str(
    techspec_handoff_policy_lookup("handoff_packet.recommended_action")
)
TECHSPEC_HANDOFF_TARGET_TRANSITION_PROFILE = str(
    techspec_handoff_policy_lookup("handoff_packet.transition_profile")
)
TECHSPEC_HANDOFF_TARGET_PACKET_TYPE = str(
    techspec_handoff_policy_lookup("handoff_packet.packet_type")
)
TECHSPEC_HANDOFF_TARGET_ARTIFACT_CLASS = str(
    techspec_handoff_policy_lookup("handoff_packet.target_artifact_class")
)
PROPOSAL_LANE_NODES_RELATIVE_DIR = str(proposal_lane_policy_lookup("repository_layout.nodes_dir"))
PROPOSAL_LANE_OVERLAY_FILENAME = Path(
    str(proposal_lane_policy_lookup("repository_layout.overlay_artifact"))
).name
PROPOSAL_LANE_NODE_ARTIFACT_KIND = str(proposal_lane_policy_lookup("node_contract.artifact_kind"))
PROPOSAL_LANE_NODE_SCHEMA_VERSION = int(proposal_lane_policy_lookup("node_contract.schema_version"))
PROPOSAL_LANE_PRESENCE_CONTRACT = proposal_lane_policy_lookup("node_contract.presence_contract")
PROPOSAL_LANE_REQUIRED_QUERY_FIELDS = list(
    proposal_lane_policy_lookup("node_contract.required_query_fields")
)
PROPOSAL_LANE_AUTHORITY_STATE_MAPPING = proposal_lane_policy_lookup("authority_state_mapping")
PROPOSAL_LANE_OVERLAY_ARTIFACT_KIND = str(
    proposal_lane_policy_lookup("overlay_contract.artifact_kind")
)
PROPOSAL_LANE_OVERLAY_SCHEMA_VERSION = int(
    proposal_lane_policy_lookup("overlay_contract.schema_version")
)
PROPOSAL_LANE_LAYER_NAME = str(proposal_lane_policy_lookup("overlay_contract.layer_name"))
PROPOSAL_LANE_NAMED_FILTERS = list(proposal_lane_policy_lookup("overlay_contract.named_filters"))
INTENT_LAYER_NODES_RELATIVE_DIR = str(intent_layer_policy_lookup("repository_layout.nodes_dir"))
INTENT_LAYER_OVERLAY_FILENAME = Path(
    str(intent_layer_policy_lookup("repository_layout.overlay_artifact"))
).name
INTENT_LAYER_NODE_ARTIFACT_KIND = str(intent_layer_policy_lookup("node_contract.artifact_kind"))
INTENT_LAYER_NODE_SCHEMA_VERSION = int(intent_layer_policy_lookup("node_contract.schema_version"))
INTENT_LAYER_PRESENCE_CONTRACT = intent_layer_policy_lookup("node_contract.presence_contract")
INTENT_LAYER_REQUIRED_QUERY_FIELDS = list(
    intent_layer_policy_lookup("node_contract.required_query_fields")
)
INTENT_LAYER_ALLOWED_KINDS = set(
    intent_layer_policy_lookup("node_contract.kind_contract.allowed_kinds")
)
INTENT_LAYER_REQUIRED_SECTIONS_BY_KIND = intent_layer_policy_lookup(
    "node_contract.kind_contract.required_sections_by_kind"
)
INTENT_LAYER_CANONICAL_SPEC_FORBIDDEN_FIELDS = set(
    intent_layer_policy_lookup(
        "node_contract.cross_layer_distinction.canonical_spec_forbidden_fields"
    )
)
INTENT_LAYER_PROPOSAL_LANE_FORBIDDEN_FIELDS = set(
    intent_layer_policy_lookup(
        "node_contract.cross_layer_distinction.proposal_lane_forbidden_fields"
    )
)
INTENT_LAYER_ALLOWED_STATES = set(
    intent_layer_policy_lookup("node_contract.state_contract.allowed_states")
)
INTENT_LAYER_OVERLAY_ARTIFACT_KIND = str(
    intent_layer_policy_lookup("overlay_contract.artifact_kind")
)
INTENT_LAYER_OVERLAY_SCHEMA_VERSION = int(
    intent_layer_policy_lookup("overlay_contract.schema_version")
)
INTENT_LAYER_LAYER_NAME = str(intent_layer_policy_lookup("overlay_contract.layer_name"))
INTENT_LAYER_NAMED_FILTERS = list(intent_layer_policy_lookup("overlay_contract.named_filters"))
SUBTREE_SHAPE_ONE_CHILD_CHAIN_THRESHOLD = int(
    policy_lookup("thresholds.subtree_shape_one_child_chain")
)
REFINEMENT_FAN_OUT_DIRECT_CHILDREN_THRESHOLD = int(
    policy_lookup("thresholds.refinement_fan_out_direct_children")
)
REFINEMENT_FAN_OUT_GROUPED_CHILD_COVERAGE_THRESHOLD = float(
    policy_lookup("thresholds.refinement_fan_out_grouped_child_coverage")
)
REFINEMENT_FAN_OUT_PARENT_AGGREGATE_FLOOR = float(
    policy_lookup("thresholds.refinement_fan_out_parent_aggregate_floor")
)
GRAPH_LAYER_EXHAUSTED_CHAIN_THRESHOLD = int(policy_lookup("thresholds.graph_layer_exhausted_chain"))
SUBTREE_SHAPE_MIN_SINGLE_CHILD_RATIO = float(
    policy_lookup("thresholds.subtree_shape_min_single_child_ratio")
)
OVER_ATOMIZED_ACCEPTANCE_MAX = int(policy_lookup("thresholds.over_atomized_acceptance_max"))
TEXT_MARKER_RATIO_THRESHOLD = float(policy_lookup("thresholds.text_marker_ratio"))
ROLE_OBSCURED_BOOKKEEPING_RATIO_THRESHOLD = float(
    policy_lookup("thresholds.role_obscured_bookkeeping_ratio")
)
BOOKKEEPING_ONLY_RATIO_THRESHOLD = float(policy_lookup("thresholds.bookkeeping_only_ratio"))
BOOKKEEPING_ONLY_CONTEXT_RATIO_THRESHOLD = float(
    policy_lookup("thresholds.bookkeeping_only_context_ratio")
)
ROLE_OBSCURED_SPEC_REFERENCE_THRESHOLD = int(
    policy_lookup("thresholds.role_obscured_spec_reference_count")
)
SPEC_ID_TEXT_RE = re.compile(r"\bsg-spec-\d{4}\b")
SPEC_ID_CANONICAL_RE = re.compile(r"\bSG-SPEC-\d{4}\b")
ROLE_OBSCURED_TITLE_MARKERS = ("edge", "segment", "slice", "topology")
BOOKKEEPING_TEXT_MARKERS = (
    "owns",
    "own",
    "consumes",
    "consume",
    "delegates",
    "delegate",
    "delegated",
    "handoff",
    "boundary",
    "child",
    "parent",
    "dependency",
    "depends on",
    "depends_on",
    "edge",
    "segment",
    "slice",
    "topology",
    "gateway",
)
ROLE_LEGIBILITY_MARKERS = (
    "semantic",
    "meaning",
    "role",
    "function",
    "invariant",
    "reviewable",
    "readable",
    "inspectable",
    "implementation-agnostic",
    "aggregate",
    "forbid",
    "forbids",
    "require",
    "requires",
    "must",
    "only allowed",
    "explains why",
    "governs",
)
AGGREGATE_ROLE_MARKERS = (
    "aggregate",
    "cluster",
    "group",
    "family",
    "suite",
    "coordination",
    "coordinator",
)
CHILD_CONCERN_TOKEN_RE = re.compile(r"[a-z][a-z0-9_]*")
CHILD_CONCERN_STOPWORDS = {
    "a",
    "an",
    "and",
    "for",
    "in",
    "of",
    "on",
    "the",
    "to",
    "with",
    "without",
    "under",
    "specgraph",
    "spec",
}
VALID_TRANSITION_PACKET_TYPES = {"promotion", "proposal", "apply", "handoff"}
DEFAULT_TRANSITION_VALIDATOR_PROFILE = "specgraph_core"
PRODUCT_SPEC_TRANSITION_POLICY_RELATIVE_PATH = "tools/product_spec_transition_policy.json"
PROPOSAL_PROMOTION_POLICY_RELATIVE_PATH = "tools/proposal_promotion_policy.json"
VALID_TRANSITION_VALIDATOR_PROFILES = {
    "specgraph_core",
    "product_spec",
    "techspec",
    "implementation_trace",
}
TRANSITION_CHECK_FAMILIES = (
    "schema",
    "legality",
    "provenance",
    "boundedness",
    "authority",
    "reconciliation",
    "diff_scope",
    "profile",
)
TRANSITION_PACKET_FAMILY_DEFINITIONS = {
    "promotion": {
        "description": "Promote one bounded pre-canonical artifact into a reviewable proposal.",
        "required_fields": [
            "bounded_scope",
            "normalized_title",
            "source_artifact_class",
            "target_artifact_class",
        ],
    },
    "proposal": {
        "description": "Normalize a governed proposal artifact without mutating canonical truth.",
        "required_fields": ["target_artifact_class"],
    },
    "apply": {
        "description": "Apply a reviewed transition into a bounded canonical mutation surface.",
        "required_fields": ["target_scope"],
    },
    "handoff": {
        "description": (
            "Emit a downstream handoff artifact once semantic saturation has been reached."
        ),
        "required_fields": ["target_artifact_class"],
    },
}
TRANSITION_VALIDATOR_PROFILE_DEFINITIONS = {
    "specgraph_core": {
        "description": (
            "Self-governance rules for SpecGraph repository artifacts and canonical specs."
        ),
        "allowed_packet_types": ["promotion", "proposal", "apply", "handoff"],
    },
    "product_spec": {
        "description": (
            "Reusable transition profile for future product-spec graphs governed inside SpecGraph."
        ),
        "allowed_packet_types": ["promotion", "proposal", "apply", "handoff"],
        "inheritance_mode": "root_bound_shared_engine",
        "required_binding_fields": ["product_graph_root"],
    },
    "techspec": {
        "description": (
            "Transition profile for implementation-facing tech-spec or handoff artifacts."
        ),
        "allowed_packet_types": ["promotion", "proposal", "apply", "handoff"],
    },
    "implementation_trace": {
        "description": (
            "Transition profile for derived implementation-trace and runtime-evidence artifacts."
        ),
        "allowed_packet_types": ["proposal", "apply", "handoff"],
    },
}
TRANSITION_PACKET_TYPE_REQUIRED_FIELDS = {
    packet_type: set(definition["required_fields"])
    for packet_type, definition in TRANSITION_PACKET_FAMILY_DEFINITIONS.items()
}
SPECGRAPH_CANONICAL_SURFACE_PREFIXES = ("specs/nodes/", "specs/history/")
GRAPH_HEALTH_OVERLAY_FILENAME = "graph_health_overlay.json"
GRAPH_HEALTH_TRENDS_FILENAME = "graph_health_trends.json"
SPEC_TRACE_INDEX_FILENAME = "spec_trace_index.json"
SPEC_TRACE_PROJECTION_FILENAME = "spec_trace_projection.json"
PROPOSAL_RUNTIME_INDEX_FILENAME = "proposal_runtime_index.json"
PROPOSAL_PROMOTION_INDEX_FILENAME = "proposal_promotion_index.json"
PROPOSAL_DOC_FILENAME_RE = re.compile(r"^(?P<proposal_id>\d{4})_(?P<slug>.+)\.md$")
TASK_LINE_RE = re.compile(r"^(?P<task_id>\d+)\.\s+\[(?P<status>[a-z_]+)\]\s+(?P<body>.+)$")
PR_NUMBER_FROM_SUBJECT_RE = re.compile(
    r"(?:\(#|PR\s+#|pull request\s+#)(?P<number>\d+)\b",
    re.IGNORECASE,
)
PROPOSAL_PROCESSING_POSTURES = {
    "document_only": (
        "Proposal is reviewable as design material, but no immediate bounded runtime slice is "
        "required."
    ),
    "bounded_runtime_followup": (
        "Proposal touches an active runtime surface and should produce a bounded follow-up slice, "
        "but not necessarily in the same change."
    ),
    "synchronous_runtime_slice": (
        "Proposal touches an active runtime surface and should be paired with "
        "a bounded tools/tests slice now."
    ),
    "deferred_until_canonicalized": (
        "Runtime realization should wait until the proposal is first anchored in canonical graph "
        "semantics."
    ),
}
IMPLEMENTATION_RELEVANT_PROPOSAL_POSTURES = {
    "bounded_runtime_followup",
    "synchronous_runtime_slice",
}
PROPOSAL_POSTURE_RUNTIME_RELEVANT_HINTS = (
    "supervisor",
    "validator",
    "tools/",
    "tests/",
    "tooling",
    "runtime surface",
    "runtime behavior",
    "inspection",
    "decision inspector",
    "trace artifact",
)
PROPOSAL_POSTURE_DEFERRED_HINTS = (
    "deferred until canonicalized",
    "before runtime changes would be legitimate",
    "first needs acceptance into canonical graph semantics",
    "runtime changes would be premature",
)
PROPOSAL_RUNTIME_SURFACE_HINTS = {
    "tools/supervisor.py": (
        "supervisor",
        "graph-health",
        "decision inspector",
        "validator",
        "transition packet",
        "trace artifact",
    ),
    "tests/test_supervisor.py": (
        "tests/",
        "test surface",
        "validation",
        "validator",
        "decision inspector",
        "transition packet",
        "trace plane",
    ),
}
ROLE_OBSCURED_CONTEXT_PHRASES = (
    "materialize one bounded",
    "materialize a single bounded",
    "owns only",
    "topology-only",
    "delegation topology",
    "direct-edge governance only",
)
BOOKKEEPING_ONLY_CONTEXT_PHRASES = (
    "edge slice",
    "child slice",
    "gateway segment",
    "direct-edge governance only",
    "delegation topology",
    "topology-only",
    "only constrains the gateway-segment edges",
)
SEMANTIC_ACCEPTANCE_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "be",
    "by",
    "do",
    "for",
    "from",
    "how",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "use",
    "uses",
    "using",
    "via",
    "with",
    "without",
    "define",
    "defines",
    "defined",
    "keep",
    "keeps",
    "kept",
    "ensure",
    "ensures",
    "ensured",
    "require",
    "requires",
    "required",
    "support",
    "supports",
    "supported",
    "allow",
    "allows",
    "allowed",
    "remain",
    "remains",
    "remaining",
    "provide",
    "provides",
    "provided",
    "spec",
    "specs",
    "node",
    "nodes",
    "child",
    "children",
    "parent",
}
APPLICABLE_PROPOSAL_STATUSES = {"proposed", "review_pending", "pending_review", "approved"}
BLOCKING_GATE_STATES = {
    "review_pending",
    "blocked",
    "split_required",
    "redirected",
    "escalated",
}
GATE_ACTION_PRIORITY = {
    str(key): int(value)
    for key, value in policy_lookup("selection_priorities.gate_action_priority").items()
}
ALLOWED_OUTCOMES = {"done", "retry", "split_required", "blocked", "escalate"}
COMPLETION_STATUS_OK = "ok"
COMPLETION_STATUS_PROGRESSED = "progressed"
COMPLETION_STATUS_FAILED = "failed"
SPEC_ID_PATTERN = re.compile(r"^SG-SPEC-(\d+)$")
SEMANTIC_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")
BACKTICK_TOKEN_RE = re.compile(r"`([^`]+)`")
UPPER_IDENTIFIER_RE = re.compile(r"\b[A-Z]{2,}(?:-[A-Z0-9]+)+\b")
CHILD_EXECUTOR_MODEL = str(policy_lookup("execution_profiles.shared.model"))
CHILD_EXECUTOR_APPROVAL_POLICY = str(policy_lookup("execution_profiles.shared.approval_policy"))
CHILD_EXECUTOR_SANDBOX = str(policy_lookup("execution_profiles.shared.sandbox"))
CHILD_EXECUTOR_DISABLED_FEATURES = tuple(
    policy_lookup("execution_profiles.shared.disabled_features")
)
DEFAULT_EXECUTION_PROFILE_NAME = str(policy_lookup("execution_profiles.default_profile"))
AUTO_HEURISTIC_PROFILE_NAME = str(policy_lookup("execution_profiles.auto_heuristic_profile"))
AUTO_CHILD_MATERIALIZATION_PROFILE_NAME = str(
    policy_lookup("execution_profiles.auto_child_materialization_profile")
)
CHILD_EXECUTOR_REASONING_EFFORT = str(
    policy_lookup(f"execution_profiles.profiles.{DEFAULT_EXECUTION_PROFILE_NAME}.reasoning_effort")
)
ROOT_REFACTOR_TIMEOUT_SECONDS = int(
    policy_lookup("execution_profiles.special_timeouts.root_refactor_timeout_seconds")
)
EXECUTOR_PROGRESS_POLL_SECONDS = 30
XHIGH_QUIET_PROGRESS_WINDOWS = 3
LINKED_CONTINUATION_MATURITY_THRESHOLD = float(
    policy_lookup("thresholds.linked_continuation_maturity")
)
REFINEMENT_ACCEPT_DECISION_APPROVE = "approve"
REFINEMENT_ACCEPT_DECISION_REJECT = "reject"
REFINEMENT_ACCEPT_DECISION_REVIEW_REQUIRED = "review_required"
REFINEMENT_CLASS_LOCAL = "local_refinement"


def emit(
    message: str,
    *,
    file: Any | None = None,
    verbose: bool = False,
    enabled: bool = True,
) -> None:
    if not enabled:
        return
    target = sys.stdout if file is None else file
    print(message, file=target)


def emit_run_footer(
    *,
    log_path: Path,
    completion_status: str,
    stdout: str,
    stderr: str,
    validation_errors: list[str],
    verbose: bool,
) -> None:
    emit(f"Run log: {log_path.as_posix()}")
    emit(f"Finished status: {completion_status}")
    if verbose and stdout.strip():
        emit("\n=== codex stdout ===")
        emit(stdout.strip())
    if verbose and stderr.strip():
        emit("\n=== codex stderr ===", file=sys.stderr)
        emit(stderr.strip(), file=sys.stderr)
    if validation_errors:
        emit("\n=== validation errors ===", file=sys.stderr)
        for error in validation_errors:
            emit(f"- {error}", file=sys.stderr)


REFINEMENT_CLASS_GRAPH_REFACTOR = "graph_refactor"
REFINEMENT_CLASS_CONSTITUTIONAL = "constitutional_change"
MUTATION_CLASS_POLICY_TEXT = "policy_text"
MUTATION_CLASS_SCHEMA_REQUIRED_ADDITION = "schema_required_addition"
MUTATION_CLASS_SCHEMA_OPTIONAL_ADDITION = "schema_optional_addition"
RUN_AUTHORITY_MATERIALIZE_ONE_CHILD = "materialize_one_child"
KNOWN_MUTATION_CLASSES = set(policy_lookup("mutation_classes").keys())
KNOWN_RUN_AUTHORITIES = {
    RUN_AUTHORITY_MATERIALIZE_ONE_CHILD,
}


@dataclass(frozen=True)
class ExecutionProfile:
    name: str
    model: str
    reasoning_effort: str
    timeout_seconds: int
    disabled_features: tuple[str, ...]
    approval_policy: str = CHILD_EXECUTOR_APPROVAL_POLICY
    sandbox: str = CHILD_EXECUTOR_SANDBOX


EXECUTION_PROFILES: dict[str, ExecutionProfile] = {
    name: ExecutionProfile(
        name=name,
        model=str(definition.get("model", CHILD_EXECUTOR_MODEL)),
        reasoning_effort=str(definition["reasoning_effort"]),
        timeout_seconds=int(definition["timeout_seconds"]),
        disabled_features=tuple(
            definition.get("disabled_features", CHILD_EXECUTOR_DISABLED_FEATURES)
        ),
        approval_policy=str(definition.get("approval_policy", CHILD_EXECUTOR_APPROVAL_POLICY)),
        sandbox=str(definition.get("sandbox", CHILD_EXECUTOR_SANDBOX)),
    )
    for name, definition in policy_lookup("execution_profiles.profiles").items()
}
FAST_EXECUTION_PROFILE_TIMEOUT_SECONDS = EXECUTION_PROFILES["fast"].timeout_seconds
CHILD_EXECUTOR_TIMEOUT_SECONDS = EXECUTION_PROFILES["standard"].timeout_seconds
CHILD_MATERIALIZATION_TIMEOUT_SECONDS = EXECUTION_PROFILES["materialize"].timeout_seconds
REASONING_TIMEOUT_FLOORS: dict[str, int] = {
    str(key): int(value)
    for key, value in policy_lookup("execution_profiles.reasoning_timeout_floors").items()
}
HIGH_REASONING_TIMEOUT_FLOOR_SECONDS = REASONING_TIMEOUT_FLOORS["high"]
XHIGH_REASONING_TIMEOUT_FLOOR_SECONDS = REASONING_TIMEOUT_FLOORS["xhigh"]
GRAPH_REFACTOR_DIFF_PREFIXES = tuple(
    policy_lookup(
        f"change_classification.change_classes.{REFINEMENT_CLASS_GRAPH_REFACTOR}.diff_prefixes"
    )
)
CONSTITUTIONAL_DIFF_PREFIXES = tuple(
    policy_lookup(
        f"change_classification.change_classes.{REFINEMENT_CLASS_CONSTITUTIONAL}.diff_prefixes"
    )
)
IMMUTABLE_DIFF_PREFIXES = tuple(policy_lookup("change_classification.immutable_diff_prefixes"))
SYNC_STRIPPED_SPEC_KEYS = {
    "RUN_OUTCOME",
    "BLOCKER",
    "gate_state",
    "proposed_status",
    "proposed_maturity",
    "required_human_action",
    "last_outcome",
    "last_blocker",
    "last_run_id",
    "last_exit_code",
    "last_changed_files",
    "last_run_at",
    "last_worktree_path",
    "last_branch",
    "last_validator_results",
    "last_refinement_acceptance",
    "last_reconciliation",
    "last_requested_child_materialization",
    "last_materialized_child_paths",
    "last_errors",
    "last_gate_decision",
    "last_gate_note",
    "last_gate_at",
    "pending_sync_paths",
    "pending_base_digests",
    "pending_candidate_digests",
    "pending_run_id",
}
DERIVED_SPEC_TRACKING_KEYS = {"created_at", "updated_at"}
DEFAULT_CODEX_HOME = Path(os.environ.get("CODEX_HOME", "~/.codex")).expanduser()

STATUS_PROGRESSION: dict[str, str] = {
    "idea": "stub",
    "stub": "outlined",
    "outlined": "specified",
    "specified": "linked",
    "linked": "reviewed",
    "reviewed": "frozen",
}


def get_yaml_module() -> ModuleType:
    if yaml is None:
        raise RuntimeError("Missing dependency: pyyaml. Install with: pip install pyyaml")
    return yaml


def get_spec_yaml_module() -> ModuleType:
    module_name = "_specgraph_spec_yaml_runtime"
    existing = sys.modules.get(module_name)
    if isinstance(existing, ModuleType):
        return existing

    module_path = Path(__file__).resolve().with_name("spec_yaml.py")
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Failed to load canonical YAML helper from {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def dump_yaml_text(data: dict[str, Any]) -> str:
    return str(get_spec_yaml_module().dump_canonical_yaml(data))


def canonical_spec_timestamp_now() -> str:
    return str(get_spec_yaml_module().canonical_timestamp_text(utc_now_iso()))


def prepare_spec_data_for_write(
    *,
    path: Path,
    data: dict[str, Any],
    touch_updated_at: bool = True,
) -> dict[str, Any]:
    spec_yaml = get_spec_yaml_module()
    existing_created_at = ""
    existing_updated_at = ""
    existing_data: dict[str, Any] = {}
    if path.exists():
        try:
            existing_data = spec_yaml.load_yaml_text(path.read_text(encoding="utf-8"))
        except Exception:
            existing_data = {}
        if isinstance(existing_data, dict):
            existing_created_at = str(existing_data.get("created_at", "")).strip()
            existing_updated_at = str(existing_data.get("updated_at", "")).strip()

    should_touch_updated_at = touch_updated_at
    if should_touch_updated_at and existing_data:
        should_touch_updated_at = canonical_spec_snapshot(existing_data) != canonical_spec_snapshot(
            data
        )

    now = canonical_spec_timestamp_now()
    created_at = str(data.get("created_at", "")).strip() or existing_created_at or now
    updated_at = (
        now
        if should_touch_updated_at
        else str(data.get("updated_at", "")).strip() or existing_updated_at or created_at
    )
    return spec_yaml.with_spec_timestamps(
        dict(data),
        created_at=created_at,
        updated_at=updated_at,
    )


def write_spec_yaml(
    path: Path,
    data: dict[str, Any],
    *,
    touch_updated_at: bool = True,
) -> dict[str, Any]:
    prepared = prepare_spec_data_for_write(
        path=path,
        data=data,
        touch_updated_at=touch_updated_at,
    )
    path.write_text(dump_yaml_text(prepared), encoding="utf-8")
    return prepared


def atomic_write_spec_yaml(
    path: Path,
    data: dict[str, Any],
    *,
    touch_updated_at: bool = True,
) -> dict[str, Any]:
    prepared = prepare_spec_data_for_write(
        path=path,
        data=data,
        touch_updated_at=touch_updated_at,
    )
    atomic_write_text(path, dump_yaml_text(prepared))
    return prepared


def strip_runtime_spec_data(value: Any) -> Any:
    """Return spec data with derived runtime/tracking metadata removed recursively."""
    if isinstance(value, dict):
        return {
            key: strip_runtime_spec_data(item)
            for key, item in value.items()
            if key not in SYNC_STRIPPED_SPEC_KEYS and key not in DERIVED_SPEC_TRACKING_KEYS
        }
    if isinstance(value, list):
        return [strip_runtime_spec_data(item) for item in value]
    return value


def strip_runtime_sync_data(value: Any) -> Any:
    """Return spec data with runtime-only metadata removed recursively."""
    if isinstance(value, dict):
        return {
            key: strip_runtime_sync_data(item)
            for key, item in value.items()
            if key not in SYNC_STRIPPED_SPEC_KEYS
        }
    if isinstance(value, list):
        return [strip_runtime_sync_data(item) for item in value]
    return value


def canonical_spec_snapshot(data: dict[str, Any]) -> dict[str, Any]:
    """Normalize spec data for deterministic before/after refinement checks."""
    normalized = strip_runtime_spec_data(data)
    if not isinstance(normalized, dict):
        raise ValueError("top-level YAML document must be a mapping")
    return normalized


@dataclass
class SpecNode:
    path: Path
    data: dict[str, Any]

    @property
    def id(self) -> str:
        return str(self.data.get("id", "")).strip()

    @property
    def title(self) -> str:
        return str(self.data.get("title", "")).strip()

    @property
    def status(self) -> str:
        return str(self.data.get("status", "stub")).strip()

    @property
    def gate_state(self) -> str:
        return str(self.data.get("gate_state", "none")).strip() or "none"

    @property
    def maturity(self) -> float:
        try:
            return float(self.data.get("maturity", 0.0))
        except Exception:
            return 0.0

    @property
    def depends_on(self) -> list[str]:
        return list(self.data.get("depends_on", []))

    @property
    def prompt(self) -> str:
        return str(self.data.get("prompt", "")).strip()

    @property
    def outputs(self) -> list[str]:
        return list(self.data.get("outputs", []))

    @property
    def inputs(self) -> list[str]:
        return list(self.data.get("inputs", []))

    @property
    def allowed_paths(self) -> list[str]:
        return list(self.data.get("allowed_paths", []))

    def save(self) -> None:
        self.data = write_spec_yaml(self.path, self.data)

    def reload(self) -> None:
        yaml_module = get_yaml_module()
        with self.path.open("r", encoding="utf-8") as file:
            self.data = yaml_module.safe_load(file) or {}


def load_specs() -> list[SpecNode]:
    return load_specs_from_dir(SPECS_DIR)


def load_specs_from_dir(specs_dir: Path) -> list[SpecNode]:
    yaml_module = get_yaml_module()
    if not specs_dir.exists():
        return []

    nodes: list[SpecNode] = []
    for path in sorted(specs_dir.glob("*.yaml")):
        with path.open("r", encoding="utf-8") as file:
            data = yaml_module.safe_load(file) or {}
        nodes.append(SpecNode(path=path, data=data))
    return nodes


def index_specs(specs: list[SpecNode]) -> dict[str, SpecNode]:
    return {spec.id: spec for spec in specs if spec.id}


def relation_ids(node_data: dict[str, Any], field: str) -> list[str]:
    value = node_data.get(field)
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text = str(value).strip()
    return [text] if text else []


def presence_state(node_data: dict[str, Any]) -> str:
    value = node_data.get("presence")
    if isinstance(value, dict):
        state = str(value.get("state", "")).strip().lower()
        return state
    if isinstance(value, str):
        return value.strip().lower()
    return ""


def is_historical_spec(node_data: dict[str, Any]) -> bool:
    state = presence_state(node_data)
    if state == "active":
        return False
    if state in {"historical", "historical_lineage_only"}:
        return True
    return bool(relation_ids(node_data, "superseded_by"))


def superseded_spec_ids(specs: list[SpecNode]) -> set[str]:
    superseded: set[str] = set()
    for spec in specs:
        if spec.id and is_historical_spec(spec.data):
            superseded.add(spec.id)
        superseded.update(relation_ids(spec.data, "supersedes"))
    return superseded


def refining_child_specs(node: SpecNode, specs: list[SpecNode]) -> list[SpecNode]:
    children: list[SpecNode] = []
    for spec in specs:
        refines = spec.data.get("refines")
        if not isinstance(refines, list):
            continue
        if node.id in {str(item).strip() for item in refines}:
            children.append(spec)
    return children


def active_refining_child_specs(node: SpecNode, specs: list[SpecNode]) -> list[SpecNode]:
    excluded_ids = superseded_spec_ids(specs)
    return [child for child in refining_child_specs(node, specs) if child.id not in excluded_ids]


def accepted_child_spec_ids(node: SpecNode, specs: list[SpecNode]) -> list[str]:
    accepted: list[str] = []
    for child in active_refining_child_specs(node, specs):
        evidence = child.data.get("acceptance_evidence")
        if isinstance(evidence, list) and evidence and child.id:
            accepted.append(child.id)
    return accepted


def subtree_nodes(node: SpecNode, specs: list[SpecNode]) -> list[SpecNode]:
    index = index_specs(specs)
    seen: set[str] = set()
    ordered: list[SpecNode] = []
    stack = [node]

    while stack:
        current = stack.pop()
        if not current.id or current.id in seen:
            continue
        seen.add(current.id)
        ordered.append(current)
        children = refining_child_specs(current, specs)
        for child in reversed(children):
            indexed_child = index.get(child.id, child)
            stack.append(indexed_child)
    return ordered


def active_subtree_nodes(node: SpecNode, specs: list[SpecNode]) -> list[SpecNode]:
    index = index_specs(specs)
    seen: set[str] = set()
    ordered: list[SpecNode] = []
    stack = [node]

    while stack:
        current = stack.pop()
        if not current.id or current.id in seen:
            continue
        seen.add(current.id)
        ordered.append(current)
        children = active_refining_child_specs(current, specs)
        for child in reversed(children):
            indexed_child = index.get(child.id, child)
            stack.append(indexed_child)
    return ordered


def subtree_children_map(node: SpecNode, specs: list[SpecNode]) -> dict[str, list[SpecNode]]:
    descendants = subtree_nodes(node, specs)
    descendant_ids = {spec.id for spec in descendants if spec.id}
    children_map: dict[str, list[SpecNode]] = {}
    for spec in descendants:
        if not spec.id:
            continue
        children_map[spec.id] = [
            child for child in refining_child_specs(spec, specs) if child.id in descendant_ids
        ]
    return children_map


def active_subtree_children_map(node: SpecNode, specs: list[SpecNode]) -> dict[str, list[SpecNode]]:
    descendants = active_subtree_nodes(node, specs)
    descendant_ids = {spec.id for spec in descendants if spec.id}
    children_map: dict[str, list[SpecNode]] = {}
    for spec in descendants:
        if not spec.id:
            continue
        children_map[spec.id] = [
            child
            for child in active_refining_child_specs(spec, specs)
            if child.id in descendant_ids
        ]
    return children_map


def node_acceptance_count(node: SpecNode) -> int:
    acceptance = node.data.get("acceptance")
    if not isinstance(acceptance, list):
        return 0
    return len(acceptance)


def median_int(values: list[int]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return float(ordered[midpoint])
    return (ordered[midpoint - 1] + ordered[midpoint]) / 2.0


def node_text_for_shape_analysis(node: SpecNode) -> str:
    parts: list[str] = [node.title, node.prompt]
    acceptance = node.data.get("acceptance")
    if isinstance(acceptance, list):
        parts.extend(str(item) for item in acceptance)
    specification = node.data.get("specification")
    if isinstance(specification, dict):
        parts.append(json.dumps(specification, ensure_ascii=False, sort_keys=True))
    return " ".join(part for part in parts if part).lower()


def bounded_marker_pattern(marker: str) -> re.Pattern[str]:
    words = [re.escape(part) for part in marker.split()]
    pattern = r"(?<!\w)" + r"\s+".join(words) + r"(?!\w)"
    return re.compile(pattern)


def text_marker_hits(text: str, markers: tuple[str, ...]) -> int:
    return sum(len(bounded_marker_pattern(marker).findall(text)) for marker in markers)


def unique_spec_reference_count(text: str) -> int:
    return len(set(SPEC_ID_TEXT_RE.findall(text)))


def node_role_legibility_profile(node: SpecNode) -> dict[str, Any]:
    text = node_text_for_shape_analysis(node)
    title = str(node.title).lower()
    bookkeeping_hits = text_marker_hits(text, BOOKKEEPING_TEXT_MARKERS)
    role_hits = text_marker_hits(text, ROLE_LEGIBILITY_MARKERS)
    bookkeeping_ratio = bookkeeping_hits / max(role_hits, 1)
    unique_spec_refs = unique_spec_reference_count(text)
    has_structural_title = any(marker in title for marker in ROLE_OBSCURED_TITLE_MARKERS)
    has_role_obscured_context = any(phrase in text for phrase in ROLE_OBSCURED_CONTEXT_PHRASES)
    has_bookkeeping_only_context = any(
        phrase in text for phrase in BOOKKEEPING_ONLY_CONTEXT_PHRASES
    )
    role_obscured = (
        bookkeeping_ratio >= ROLE_OBSCURED_BOOKKEEPING_RATIO_THRESHOLD
        and unique_spec_refs >= ROLE_OBSCURED_SPEC_REFERENCE_THRESHOLD
        and (has_structural_title or (has_role_obscured_context and bookkeeping_ratio >= 8.0))
    )
    bookkeeping_only = (
        bookkeeping_ratio >= BOOKKEEPING_ONLY_RATIO_THRESHOLD
        and unique_spec_refs >= ROLE_OBSCURED_SPEC_REFERENCE_THRESHOLD
        and (
            has_structural_title
            or (
                has_bookkeeping_only_context
                and bookkeeping_ratio >= BOOKKEEPING_ONLY_CONTEXT_RATIO_THRESHOLD
            )
        )
    )
    return {
        "spec_id": node.id,
        "title": node.title,
        "bookkeeping_hits": bookkeeping_hits,
        "role_hits": role_hits,
        "bookkeeping_ratio": round(float(bookkeeping_ratio), 3),
        "unique_spec_references": unique_spec_refs,
        "role_obscured": role_obscured,
        "bookkeeping_only": bookkeeping_only,
    }


def subtree_role_legibility_profiles(node: SpecNode, specs: list[SpecNode]) -> list[dict[str, Any]]:
    return [node_role_legibility_profile(spec) for spec in active_subtree_nodes(node, specs)]


def child_concern_tokens(node: SpecNode) -> set[str]:
    title = str(node.title).lower()
    return {
        token
        for token in CHILD_CONCERN_TOKEN_RE.findall(title)
        if token not in CHILD_CONCERN_STOPWORDS and not token.startswith("sg")
    }


def fan_out_legibility_profile(node: SpecNode, specs: list[SpecNode]) -> dict[str, Any]:
    children = active_refining_child_specs(node, specs)
    direct_child_count = len(children)
    child_token_sets = [child_concern_tokens(child) for child in children]
    token_frequency: dict[str, int] = {}
    for token_set in child_token_sets:
        for token in token_set:
            token_frequency[token] = token_frequency.get(token, 0) + 1
    dominant_token = ""
    dominant_token_count = 0
    for token, count in token_frequency.items():
        if count > dominant_token_count or (
            count == dominant_token_count and token and token < dominant_token
        ):
            dominant_token = token
            dominant_token_count = count
    dominant_token_coverage = (
        dominant_token_count / direct_child_count if direct_child_count else 0.0
    )
    aggregate_text = f"{node.title} {node.prompt}".lower()
    parent_reads_as_aggregate = any(marker in aggregate_text for marker in AGGREGATE_ROLE_MARKERS)
    classification = "not_applicable"
    if direct_child_count >= REFINEMENT_FAN_OUT_DIRECT_CHILDREN_THRESHOLD:
        if dominant_token_coverage >= REFINEMENT_FAN_OUT_GROUPED_CHILD_COVERAGE_THRESHOLD or (
            parent_reads_as_aggregate
            and dominant_token_coverage >= REFINEMENT_FAN_OUT_PARENT_AGGREGATE_FLOOR
        ):
            classification = "healthy_multi_child_aggregate"
        else:
            classification = "broad_hub_missing_cluster"
    return {
        "direct_child_count": direct_child_count,
        "dominant_child_token": dominant_token,
        "dominant_child_token_coverage": round(float(dominant_token_coverage), 3),
        "parent_reads_as_aggregate": parent_reads_as_aggregate,
        "classification": classification,
    }


def subtree_shape_metrics(node: SpecNode, specs: list[SpecNode]) -> dict[str, Any]:
    descendants = active_subtree_nodes(node, specs)
    children_map = active_subtree_children_map(node, specs)
    index = {spec.id: spec for spec in descendants if spec.id}

    level_widths: dict[int, int] = {}

    def walk_depth(spec_id: str, depth: int, active: frozenset[str]) -> int:
        if spec_id in active:
            return depth - 1
        level_widths[depth] = level_widths.get(depth, 0) + 1
        child_depths = [
            walk_depth(child.id, depth + 1, active | {spec_id})
            for child in children_map.get(spec_id, [])
            if child.id in index
        ]
        return max([depth, *child_depths])

    def one_child_chain(spec_id: str, active: frozenset[str]) -> int:
        if spec_id in active:
            return 0
        children = [child for child in children_map.get(spec_id, []) if child.id in index]
        if len(children) != 1:
            return 1
        return 1 + one_child_chain(children[0].id, active | {spec_id})

    max_depth = walk_depth(node.id, 0, frozenset()) if node.id in index else 0
    longest_chain = (
        max(one_child_chain(spec_id, frozenset()) for spec_id in index)
        if node.id in index and index
        else 1
    )
    internal_nodes = [spec_id for spec_id, children in children_map.items() if children]
    single_child_internal_count = sum(
        1 for spec_id in internal_nodes if len(children_map.get(spec_id, [])) == 1
    )
    max_width = max(level_widths.values(), default=1)
    acceptance_median = median_int([node_acceptance_count(spec) for spec in descendants])
    delegation_markers = (
        "delegate",
        "delegation",
        "handoff",
        "boundary",
        "descendant",
        "child",
        "parent",
        "integration",
        "gateway",
    )
    execution_markers = (
        "execution",
        "payload",
        "field",
        "runtime",
        "queue",
        "retry",
        "artifact",
        "surface",
        "sequencing",
        "routing",
        "topology",
        "consumer",
        "producer",
    )
    texts = [node_text_for_shape_analysis(spec) for spec in descendants]
    delegation_ratio = (
        sum(1 for text in texts if any(marker in text for marker in delegation_markers))
        / len(texts)
        if texts
        else 0.0
    )
    execution_ratio = (
        sum(1 for text in texts if any(marker in text for marker in execution_markers)) / len(texts)
        if texts
        else 0.0
    )

    return {
        "subtree_node_count": len(descendants),
        "descendant_count": max(0, len(descendants) - 1),
        "direct_child_count": len(children_map.get(node.id, [])),
        "max_depth": max_depth,
        "max_width": max_width,
        "longest_one_child_chain": longest_chain,
        "internal_node_count": len(internal_nodes),
        "single_child_internal_ratio": (
            single_child_internal_count / len(internal_nodes) if internal_nodes else 0.0
        ),
        "median_acceptance_count": acceptance_median,
        "delegation_marker_ratio": delegation_ratio,
        "execution_marker_ratio": execution_ratio,
    }


def techspec_handoff_profile(*, metrics: dict[str, Any], signals: list[str]) -> dict[str, Any]:
    present_signals = {str(signal).strip() for signal in signals if str(signal).strip()}
    lower_boundary_signals = sorted(
        signal
        for signal in present_signals
        if signal in TECHSPEC_HANDOFF_REQUIRED_LOWER_BOUNDARY_SIGNALS
    )
    semantic_saturation_signals = sorted(
        signal
        for signal in present_signals
        if signal in TECHSPEC_HANDOFF_SEMANTIC_SATURATION_SIGNALS
    )
    execution_marker_ratio = round(float(metrics.get("execution_marker_ratio", 0.0)), 3)
    candidate = (
        bool(lower_boundary_signals)
        and execution_marker_ratio >= TEXT_MARKER_RATIO_THRESHOLD
        and len(semantic_saturation_signals)
        >= TECHSPEC_HANDOFF_MIN_SEMANTIC_SATURATION_SIGNAL_COUNT
    )
    return {
        "candidate": candidate,
        "source_layer": str(
            TECHSPEC_HANDOFF_POLICY.get("boundary_model", {}).get("source_layer", "")
        ),
        "target_layer": TECHSPEC_HANDOFF_TARGET_LAYER,
        "lower_boundary_signals": lower_boundary_signals,
        "semantic_saturation_signals": semantic_saturation_signals,
        "execution_marker_ratio": execution_marker_ratio,
        "target_transition_profile": TECHSPEC_HANDOFF_TARGET_TRANSITION_PROFILE,
        "target_packet_type": TECHSPEC_HANDOFF_TARGET_PACKET_TYPE,
        "target_artifact_class": TECHSPEC_HANDOFF_TARGET_ARTIFACT_CLASS,
        "boundary_reference": techspec_handoff_policy_reference(),
    }


def merge_unique_strings(*groups: list[str]) -> list[str]:
    merged: list[str] = []
    for group in groups:
        for value in group:
            normalized = str(value).strip()
            if normalized and normalized not in merged:
                merged.append(normalized)
    return merged


def reverse_dependents_count(specs: list[SpecNode]) -> dict[str, int]:
    counts: dict[str, int] = {spec.id: 0 for spec in specs if spec.id}
    for spec in specs:
        for dep_id in spec.depends_on:
            if dep_id in counts:
                counts[dep_id] += 1
    return counts


def semantic_dependencies_resolved(node: SpecNode, index: dict[str, SpecNode]) -> bool:
    for dep_id in node.depends_on:
        if index.get(dep_id) is None:
            return False
    return True


def work_dependencies_ready(node: SpecNode, index: dict[str, SpecNode]) -> bool:
    for dep_id in node.depends_on:
        dep = index.get(dep_id)
        if dep is None or dep.status not in READY_DEP_STATUSES:
            return False
    return True


def dependencies_ready(node: SpecNode, index: dict[str, SpecNode]) -> bool:
    return work_dependencies_ready(node, index)


def transitive_dependency_count(
    node: SpecNode,
    index: dict[str, SpecNode],
) -> int:
    seen: set[str] = set()
    stack = list(node.depends_on)

    while stack:
        dep_id = stack.pop()
        if dep_id in seen:
            continue
        seen.add(dep_id)
        dep = index.get(dep_id)
        if dep is not None:
            stack.extend(dep.depends_on)

    return len(seen)


def is_ancestor_reconcile_candidate(node: SpecNode, index: dict[str, SpecNode]) -> bool:
    return (
        node.status == "specified"
        and bool(node.depends_on)
        and semantic_dependencies_resolved(node, index)
    )


def selection_mode_for_node(
    node: SpecNode,
    specs: list[SpecNode] | None = None,
    refactor_work_item: dict[str, Any] | None = None,
    operator_target: bool = False,
) -> str:
    if refactor_work_item is not None:
        if str(refactor_work_item.get("refactor_kind", "")).strip() == SPLIT_REFACTOR_KIND:
            return "split_refactor_proposal"
        return "graph_refactor"
    if operator_target:
        return "explicit_target_refine"
    local_specs = specs or load_specs()
    index = index_specs(local_specs)
    if is_ancestor_reconcile_candidate(node, index) and not is_gate_blocking(node):
        return "ancestor_reconcile"
    if linked_continuation_reasons(node, index):
        return "linked_continuation"
    return "default_refine"


def is_seed_like_spec(node_data: dict[str, Any]) -> bool:
    refines = node_data.get("refines")
    if isinstance(refines, list) and any(str(item).strip() for item in refines):
        return False

    texts: list[str] = [
        str(node_data.get("title", "")),
        str(node_data.get("prompt", "")),
    ]
    specification = node_data.get("specification")
    if isinstance(specification, dict):
        texts.append(str(specification.get("objective", "")))
        scope = specification.get("scope")
        if isinstance(scope, dict):
            in_scope = scope.get("in")
            if isinstance(in_scope, list):
                texts.extend(str(item) for item in in_scope)

    combined = " ".join(texts).lower()
    return any(
        term in combined
        for term in (
            "seed ontology",
            "seed spec",
            "root spec",
            "overview spec",
        )
    )


def is_gate_blocking(node: SpecNode) -> bool:
    return node.gate_state in BLOCKING_GATE_STATES


def parse_iso_datetime(value: object) -> dt.datetime | None:
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = dt.datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed


def has_fresh_gate_approval_without_new_run(spec: SpecNode) -> bool:
    if str(spec.data.get("last_gate_decision", "")).strip().lower() != "approve":
        return False
    gate_at = parse_iso_datetime(spec.data.get("last_gate_at", ""))
    run_at = parse_iso_datetime(spec.data.get("last_run_at", ""))
    if gate_at is None or run_at is None:
        return False
    return gate_at >= run_at


def linked_continuation_reasons(
    spec: SpecNode,
    index: dict[str, SpecNode],
) -> list[str]:
    """Return derived continuation reasons for already-linked graph regions.

    Low maturity alone is not enough. Continuation requires low maturity plus
    some already-defined signal pressure such as stalled refinement or weak
    structural linkage.
    """
    if spec.status not in CONTINUATION_STATUSES or is_gate_blocking(spec):
        return []

    reasons: list[str] = []
    last_outcome = str(spec.data.get("last_outcome", "")).strip()
    if last_outcome in {"retry", "blocked", "split_required"}:
        reasons.append("stalled_maturity_candidate")

    unresolved_dependencies = [
        dep_id
        for dep_id in spec.depends_on
        if dep_id not in index or index[dep_id].status not in READY_DEP_STATUSES
    ]
    if unresolved_dependencies:
        reasons.append("weak_structural_linkage_candidate")

    if has_fresh_gate_approval_without_new_run(spec) and reasons == [
        "weak_structural_linkage_candidate"
    ]:
        return []

    if spec.maturity >= 1.0 and reasons == ["weak_structural_linkage_candidate"]:
        return []

    if spec.maturity < LINKED_CONTINUATION_MATURITY_THRESHOLD and reasons:
        reasons.insert(0, "latent_graph_improvement_candidate")
    return reasons


def active_signal_items_for_spec(
    spec_id: str,
    *,
    signals: set[str],
    refactor_items: list[dict[str, Any]] | None = None,
    proposal_items: list[dict[str, Any]] | None = None,
) -> bool:
    local_refactor_items = refactor_items if refactor_items is not None else load_refactor_queue()
    local_proposal_items = proposal_items if proposal_items is not None else load_proposal_queue()

    for item in local_refactor_items:
        if str(item.get("spec_id", "")).strip() != spec_id:
            continue
        if str(item.get("signal", "")).strip() not in signals:
            continue
        if str(item.get("status", "proposed")).strip() in {"proposed", "retry_pending"}:
            return True

    for item in local_proposal_items:
        if str(item.get("spec_id", "")).strip() != spec_id:
            continue
        if str(item.get("signal", "")).strip() not in signals:
            continue
        if proposal_is_active(item):
            return True
    return False


def pick_next_spec_gap(specs: list[SpecNode]) -> SpecNode | None:
    index = index_specs(specs)
    dependents = reverse_dependents_count(specs)
    ancestor_candidates = [
        spec
        for spec in specs
        if is_ancestor_reconcile_candidate(spec, index) and not is_gate_blocking(spec)
    ]
    if ancestor_candidates:
        ancestor_candidates.sort(
            key=lambda spec: (transitive_dependency_count(spec, index), spec.maturity, spec.id)
        )
        return ancestor_candidates[0]

    candidates = [
        spec
        for spec in specs
        if spec.status in WORKABLE_STATUSES
        and work_dependencies_ready(spec, index)
        and not is_gate_blocking(spec)
    ]
    if not candidates:
        refactor_items = load_refactor_queue()
        proposal_items = load_proposal_queue()
        continuation_candidates = [
            spec
            for spec in specs
            if linked_continuation_reasons(spec, index)
            and not active_signal_items_for_spec(
                spec.id,
                signals=SUBTREE_SHAPE_SIGNALS | LOWER_BOUNDARY_HANDOFF_SIGNALS,
                refactor_items=refactor_items,
                proposal_items=proposal_items,
            )
        ]
        if not continuation_candidates:
            return None
        continuation_candidates.sort(
            key=lambda spec: (
                0 if spec.status == "linked" else 1,
                transitive_dependency_count(spec, index),
                spec.maturity,
                spec.id,
            )
        )
        return continuation_candidates[0]

    candidates.sort(key=lambda spec: (dependents.get(spec.id, 0), spec.maturity, spec.id))
    return candidates[0]


def load_refactor_queue() -> list[dict[str, Any]]:
    path = refactor_queue_path()
    if not path.exists():
        return []
    data, _error = load_json_list_report(path, artifact_kind="refactor queue artifact")
    return data or []


def load_proposal_queue() -> list[dict[str, Any]]:
    path = proposal_queue_path()
    if not path.exists():
        return []
    data, _error = load_json_list_report(path, artifact_kind="proposal queue artifact")
    return data or []


def runtime_artifact_integrity_errors() -> list[str]:
    errors: list[str] = []
    for path, artifact_kind in (
        (proposal_queue_path(), "proposal queue artifact"),
        (refactor_queue_path(), "refactor queue artifact"),
    ):
        if not path.exists():
            continue
        _data, error = load_json_list_report(path, artifact_kind=artifact_kind)
        if error:
            errors.append(error)
    return errors


def refactor_signal_priority(signal: str) -> int:
    priorities = policy_lookup("selection_priorities.refactor_signal_priority")
    return int(priorities.get(signal, 9))


def pick_next_refactor_work_item(
    specs: list[SpecNode],
    queue_items: list[dict[str, Any]] | None = None,
    proposal_items: list[dict[str, Any]] | None = None,
) -> tuple[SpecNode, dict[str, Any]] | None:
    items = queue_items if queue_items is not None else load_refactor_queue()
    active_proposals = proposal_items if proposal_items is not None else load_proposal_queue()
    index = index_specs(specs)

    candidates: list[tuple[SpecNode, dict[str, Any]]] = []
    for item in items:
        if str(item.get("work_item_type", "")).strip() != "graph_refactor":
            continue
        status = str(item.get("status", "proposed")).strip()
        if status not in {"proposed", "retry_pending"}:
            continue
        execution_policy = refactor_execution_policy(item, active_proposals)
        if execution_policy != "direct_graph_update":
            continue
        spec_id = str(item.get("spec_id", "")).strip()
        node = index.get(spec_id)
        if node is None or is_gate_blocking(node):
            continue
        item = dict(item)
        item["execution_policy"] = execution_policy
        candidates.append((node, item))

    if not candidates:
        return None

    candidates.sort(
        key=lambda candidate: (
            refactor_signal_priority(str(candidate[1].get("signal", ""))),
            transitive_dependency_count(candidate[0], index),
            candidate[0].maturity,
            candidate[0].id,
            str(candidate[1].get("id", "")),
        )
    )
    return candidates[0]


def pick_next_work_item(specs: list[SpecNode]) -> tuple[SpecNode | None, dict[str, Any] | None]:
    """Return the next executable work item.

    Selection order is intentionally asymmetric:
    1. queued graph_refactor items that are still allowed as direct updates
    2. ordinary spec refinement selected by the default heuristic

    Governance proposals are visible in derived artifacts but are not
    auto-executed from here.
    """
    proposal_items = load_proposal_queue()
    refactor_candidate = pick_next_refactor_work_item(specs, proposal_items=proposal_items)
    if refactor_candidate is not None:
        return refactor_candidate
    node = pick_next_spec_gap(specs)
    return node, None


def pending_gate_actions(specs: list[SpecNode]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for spec in specs:
        gate_state = spec.gate_state
        if gate_state not in BLOCKING_GATE_STATES:
            continue
        actions.append(
            {
                "spec_id": spec.id,
                "title": spec.title,
                "status": spec.status,
                "maturity": spec.maturity,
                "gate_state": gate_state,
                "required_human_action": str(spec.data.get("required_human_action", "-")).strip()
                or "-",
            }
        )

    actions.sort(
        key=lambda action: (
            GATE_ACTION_PRIORITY.get(str(action["gate_state"]), 9),
            float(action["maturity"]),
            str(action["spec_id"]),
        )
    )
    return actions


def format_pending_gate_actions(actions: list[dict[str, Any]], *, limit: int = 10) -> str:
    if not actions:
        return "No eligible spec gaps found."

    visible = actions[:limit]
    lines = [
        "No eligible auto-refinement gaps found.",
        "Pending gate actions block automatic selection:",
    ]
    for action in visible:
        lines.append(
            "- "
            f"{action['spec_id']} | gate={action['gate_state']} | "
            f"status={action['status']} | maturity={float(action['maturity']):.2f} | "
            f"action={action['required_human_action']}"
        )
    remaining = len(actions) - len(visible)
    if remaining > 0:
        lines.append(f"- ... {remaining} more pending gate action(s)")
    lines.append(
        "Resolve a gate with `tools/supervisor.py --resolve-gate <SPEC_ID> --decision <decision>` "
        "or use an explicit targeted run when the gate requires more spec work."
    )
    return "\n".join(lines)


def detect_cycles(specs: list[SpecNode]) -> list[list[str]]:
    """Detect dependency cycles via DFS. Returns list of cycles found."""
    index = index_specs(specs)
    visited: set[str] = set()
    in_stack: set[str] = set()
    stack: list[str] = []
    cycles: list[list[str]] = []

    def dfs(node_id: str) -> None:
        if node_id in in_stack:
            cycle_start = stack.index(node_id)
            cycles.append(stack[cycle_start:] + [node_id])
            return
        if node_id in visited:
            return
        visited.add(node_id)
        in_stack.add(node_id)
        stack.append(node_id)
        node = index.get(node_id)
        if node:
            for dep_id in node.depends_on:
                dfs(dep_id)
        stack.pop()
        in_stack.remove(node_id)

    for spec in specs:
        if spec.id and spec.id not in visited:
            dfs(spec.id)
    return cycles


def git_changed_files(cwd: Path = ROOT) -> list[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []

    changed: list[str] = []
    for line in result.stdout.splitlines():
        if len(line) >= 4:
            changed.append(line[3:].strip())
    return changed


def git_status_changed_files(cwd: Path = ROOT) -> list[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []

    changed: list[str] = []
    for line in result.stdout.splitlines():
        if len(line) >= 4:
            candidate = line[3:].strip()
            if " -> " in candidate:
                candidate = candidate.split(" -> ", 1)[1].strip()
            changed.append(candidate)
    return changed


def snapshot_file_digests(paths: list[str], base_dir: Path) -> dict[str, str | None]:
    digests: dict[str, str | None] = {}
    for rel_path in paths:
        file_path = base_dir / rel_path
        if not file_path.exists() or not file_path.is_file():
            digests[rel_path] = None
            continue
        digest = hashlib.sha256(file_path.read_bytes()).hexdigest()
        digests[rel_path] = digest
    return digests


def snapshot_sync_digests(paths: list[str], base_dir: Path) -> dict[str, str | None]:
    digests: dict[str, str | None] = {}
    for rel_path in paths:
        file_path = base_dir / rel_path
        if not file_path.exists() or not file_path.is_file():
            digests[rel_path] = None
            continue
        if is_spec_node_path(rel_path):
            sync_text = sanitize_spec_sync_text(file_path.read_text(encoding="utf-8"))
            digests[rel_path] = hashlib.sha256(sync_text.encode("utf-8")).hexdigest()
            continue
        digests[rel_path] = hashlib.sha256(file_path.read_bytes()).hexdigest()
    return digests


def next_sequential_spec_id(specs: list[SpecNode]) -> str:
    max_number = 0
    for spec in specs:
        match = SPEC_ID_PATTERN.match(spec.id)
        if match:
            max_number = max(max_number, int(match.group(1)))
    return f"SG-SPEC-{max_number + 1:04d}"


def spec_id_from_relpath(rel_path: str) -> str:
    path_text = rel_path.strip()
    if not path_text:
        return ""
    stem = Path(path_text).stem
    return stem if SPEC_ID_PATTERN.match(stem) else ""


def pending_review_reserved_spec_ids(specs: list[SpecNode]) -> set[str]:
    reserved: set[str] = set()
    for spec in specs:
        if spec.gate_state != "review_pending":
            continue
        raw_paths = spec.data.get("last_materialized_child_paths", [])
        if not isinstance(raw_paths, list):
            continue
        for rel_path in raw_paths:
            spec_id = spec_id_from_relpath(str(rel_path).strip())
            if spec_id:
                reserved.add(spec_id)
    return reserved


def spec_id_reservations_path() -> Path:
    return RUNS_DIR / "spec_id_reservations.json"


def load_spec_id_reservations() -> list[dict[str, str]]:
    path = spec_id_reservations_path()
    if not path.exists():
        return []
    payload, error = load_json_object_report(path, artifact_kind="spec-id reservation registry")
    if payload is None:
        raise RuntimeError(error or "Malformed spec-id reservation registry")
    raw_items = payload.get("reservations", [])
    if not isinstance(raw_items, list):
        raise RuntimeError("Malformed spec-id reservation registry: reservations must be a list")
    reservations: list[dict[str, str]] = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            raise RuntimeError(
                "Malformed spec-id reservation registry: reservation entries must be objects"
            )
        spec_id = str(raw.get("spec_id", "")).strip()
        spec_path = str(raw.get("spec_path", "")).strip()
        run_id = str(raw.get("run_id", "")).strip()
        source_spec_id = str(raw.get("source_spec_id", "")).strip()
        reserved_at = str(raw.get("reserved_at", "")).strip()
        if not spec_id or not SPEC_ID_PATTERN.match(spec_id):
            raise RuntimeError(
                "Malformed spec-id reservation registry: reservation spec_id must be SG-SPEC-XXXX"
            )
        if spec_path != f"specs/nodes/{spec_id}.yaml":
            raise RuntimeError(
                "Malformed spec-id reservation registry: reservation spec_path must match spec_id"
            )
        if not run_id or not source_spec_id or not reserved_at:
            raise RuntimeError(
                "Malformed spec-id reservation registry: reservation entries require "
                "run_id, source_spec_id, and reserved_at"
            )
        reservations.append(
            {
                "spec_id": spec_id,
                "spec_path": spec_path,
                "run_id": run_id,
                "source_spec_id": source_spec_id,
                "reserved_at": reserved_at,
            }
        )
    return reservations


def reserve_child_materialization_spec_id(
    *,
    specs: list[SpecNode],
    source_spec_id: str,
    run_id: str,
) -> dict[str, str]:
    path = spec_id_reservations_path()
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    with artifact_lock(path):
        reservations = load_spec_id_reservations()
        canonical_ids = {spec.id for spec in specs if SPEC_ID_PATTERN.match(spec.id)}
        pending_ids = pending_review_reserved_spec_ids(specs)
        active_ids = {
            str(item.get("spec_id", "")).strip()
            for item in reservations
            if str(item.get("spec_id", "")).strip()
        }
        used_numbers = {
            int(match.group(1))
            for spec_id in canonical_ids | pending_ids | active_ids
            if (match := SPEC_ID_PATTERN.match(spec_id))
        }
        next_number = max(used_numbers, default=0) + 1
        child_id = f"SG-SPEC-{next_number:04d}"
        child_path = f"specs/nodes/{child_id}.yaml"
        reservations.append(
            {
                "spec_id": child_id,
                "spec_path": child_path,
                "run_id": run_id,
                "source_spec_id": source_spec_id,
                "reserved_at": utc_now_iso(),
            }
        )
        atomic_write_json(path, {"reservations": reservations})
    return {"id": child_id, "path": child_path}


def release_child_materialization_spec_id(*, spec_id: str, run_id: str) -> None:
    path = spec_id_reservations_path()
    if not path.exists():
        return
    with artifact_lock(path):
        reservations = load_spec_id_reservations()
        retained = [
            item
            for item in reservations
            if not (
                str(item.get("spec_id", "")).strip() == spec_id
                and str(item.get("run_id", "")).strip() == run_id
            )
        ]
        atomic_write_json(path, {"reservations": retained})


def implicit_source_allowed_paths(node: SpecNode) -> list[str]:
    try:
        return [node.path.relative_to(ROOT).as_posix()]
    except ValueError:
        return [node.path.as_posix()]


def can_create_new_spec_files(node: SpecNode, rel_path: str | None = None) -> bool:
    if not node.allowed_paths:
        return False
    sample_path = PurePosixPath(rel_path or "specs/nodes/SG-SPEC-9999.yaml")
    return any(sample_path.match(pattern) for pattern in node.allowed_paths)


def node_supports_child_delegation(node: SpecNode) -> bool:
    """Return True when the node semantically reads like a delegating parent."""
    parts: list[str] = [node.title, node.prompt]
    acceptance = node.data.get("acceptance", [])
    if isinstance(acceptance, list):
        parts.extend(str(item) for item in acceptance)
    specification = node.data.get("specification")
    if isinstance(specification, dict):
        parts.append(json.dumps(specification, ensure_ascii=False, sort_keys=True))
    seed_text = " ".join(parts).lower()
    delegation_markers = (
        "child",
        "child spec",
        "child refinement",
        "delegate",
        "delegation",
        "descendant",
        "split",
        "decompose",
        "bounded child",
    )
    return any(marker in seed_text for marker in delegation_markers)


def run_authority_grants_child_materialization(run_authority: tuple[str, ...]) -> bool:
    return RUN_AUTHORITY_MATERIALIZE_ONE_CHILD in run_authority


def resolve_execution_profile_name(
    *,
    requested_profile: str | None,
    run_authority: tuple[str, ...],
    operator_target: bool = False,
) -> str:
    candidate = str(requested_profile or "").strip()
    if candidate:
        if candidate not in EXECUTION_PROFILES:
            allowed = ", ".join(sorted(EXECUTION_PROFILES))
            raise ValueError(f"Unknown execution profile '{candidate}'. Known profiles: {allowed}")
        return candidate
    if run_authority_grants_child_materialization(run_authority):
        return AUTO_CHILD_MATERIALIZATION_PROFILE_NAME
    if not operator_target:
        return AUTO_HEURISTIC_PROFILE_NAME
    return DEFAULT_EXECUTION_PROFILE_NAME


def resolve_execution_profile(
    *,
    requested_profile: str | None,
    run_authority: tuple[str, ...],
    operator_target: bool = False,
) -> ExecutionProfile:
    return EXECUTION_PROFILES[
        resolve_execution_profile_name(
            requested_profile=requested_profile,
            run_authority=run_authority,
            operator_target=operator_target,
        )
    ]


def infer_ordinary_execution_profile_name(
    *,
    node: SpecNode,
    specs: list[SpecNode],
    requested_profile: str | None,
    operator_target: bool,
    run_authority: tuple[str, ...],
) -> str:
    """Choose the execution profile for an ordinary refinement run.

    Heuristic ordinary runs default to `fast`, but seed-like nodes that already
    carry bootstrap child guidance need the longer materialization budget even
    without an explicit operator authority grant.
    """
    resolved = resolve_execution_profile_name(
        requested_profile=requested_profile,
        run_authority=run_authority,
        operator_target=operator_target,
    )
    if requested_profile or operator_target or run_authority:
        return resolved
    if bootstrap_child_hint(node, specs) is not None:
        return AUTO_CHILD_MATERIALIZATION_PROFILE_NAME
    return resolved


def reasoning_effort_timeout_floor_seconds(reasoning_effort: str) -> int:
    return REASONING_TIMEOUT_FLOORS.get(reasoning_effort, CHILD_EXECUTOR_TIMEOUT_SECONDS)


def classify_completion_status(
    *,
    success: bool,
    productive_split_required: bool,
) -> str:
    if success:
        return COMPLETION_STATUS_OK
    if productive_split_required:
        return COMPLETION_STATUS_PROGRESSED
    return COMPLETION_STATUS_FAILED


def normalize_executor_stderr(stderr: str) -> str:
    """Collapse known transport/runtime noise tails without hiding real errors."""
    if not stderr.strip():
        return stderr

    rules: tuple[tuple[str, Callable[[str], bool], str], ...] = (
        (
            "model_refresh_timeout",
            lambda low: (
                "failed to refresh available models: timeout waiting for child process to exit"
                in low
            ),
            "suppressed model refresh timeout warning",
        ),
        (
            "app_server_queue_full",
            lambda low: (
                "dropping in-process app-server event because consumer queue is full" in low
            ),
            "suppressed app-server queue-full warning",
        ),
        (
            "app_server_stream_lag",
            lambda low: "in-process app-server event stream lagged; dropped" in low,
            "suppressed app-server stream lag warning",
        ),
    )

    kept_lines: list[str] = []
    suppressed_counts = {name: 0 for name, _predicate, _summary in rules}
    for line in stderr.splitlines():
        lowered = line.lower()
        matched_rule = False
        for name, predicate, _summary in rules:
            if predicate(lowered):
                suppressed_counts[name] += 1
                matched_rule = True
                break
        if not matched_rule:
            kept_lines.append(line)

    for name, _predicate, summary in rules:
        count = suppressed_counts[name]
        if count:
            kept_lines.append(f"[executor-noise] {summary} ({count} occurrence(s))")

    normalized = "\n".join(kept_lines)
    if stderr.endswith("\n"):
        normalized += "\n"
    return normalized


YAML_KEY_LINE_RE = re.compile(r"^(?P<indent>\s*)(?P<key>[A-Za-z0-9_][A-Za-z0-9_-]*):(?:\s|$)")
YAML_SEQUENCE_ITEM_RE = re.compile(r"^(?P<indent>\s*)-\s+(?P<content>.*)$")
YAML_MAPPING_SEQUENCE_CONTENT_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_-]*:\s")
YAML_QUOTED_KEY_LINE_RE = re.compile(r"^\s*[\"'][^\"']+[\"']:\s")
YAML_SEQUENCE_MAPPING_SCALAR_RE = re.compile(
    r"^(?P<indent>\s*)-\s+(?P<key>[A-Za-z0-9_][A-Za-z0-9_-]*):\s+(?P<value>.+)$"
)
YAML_MAPPING_SCALAR_RE = re.compile(
    r"^(?P<indent>\s*)(?P<key>[A-Za-z0-9_][A-Za-z0-9_-]*):\s+(?P<value>.+)$"
)


def _yaml_single_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _yaml_plain_scalar_needs_quote(value: str) -> bool:
    return value.startswith("`") or ":" in value


def build_yaml_key_indent_map(text: str) -> dict[str, tuple[int, ...]]:
    indents: dict[str, set[int]] = {}
    for line in text.splitlines():
        match = YAML_KEY_LINE_RE.match(line)
        if match is None:
            continue
        key = match.group("key")
        indent = len(match.group("indent"))
        indents.setdefault(key, set()).add(indent)
    return {key: tuple(sorted(values)) for key, values in indents.items()}


def build_yaml_line_indent_map(text: str) -> dict[str, tuple[int, ...]]:
    indents: dict[str, set[int]] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        indent = len(line) - len(line.lstrip(" "))
        indents.setdefault(stripped, set()).add(indent)
    return {line: tuple(sorted(values)) for line, values in indents.items()}


def repair_candidate_yaml_text(candidate_text: str, original_text: str | None = None) -> str:
    lines = [
        line
        for line in candidate_text.splitlines()
        if line.strip()
        not in {
            "*** Begin Patch",
            "*** End Patch",
            "*** End of File",
        }
        and not line.startswith("*** Update File: ")
        and not line.startswith("*** Add File: ")
        and not line.startswith("*** Delete File: ")
        and not line.startswith("*** Move to: ")
        and line.strip() != "@@"
        and not line.startswith("@@ ")
    ]
    original_indent_map = (
        build_yaml_key_indent_map(original_text) if original_text is not None else {}
    )
    original_line_indent_map = (
        build_yaml_line_indent_map(original_text) if original_text is not None else {}
    )

    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            continue
        current_indent = len(line) - len(line.lstrip(" "))
        original_indents = original_line_indent_map.get(stripped, ())
        if len(set(original_indents)) != 1:
            continue
        if current_indent in original_indents:
            continue
        target_indent = min(
            original_indents,
            key=lambda indent: abs(indent - current_indent),
            default=None,
        )
        if target_indent is None or abs(target_indent - current_indent) > 4:
            continue
        lines[index] = (" " * target_indent) + line.lstrip()

    for index, line in enumerate(lines):
        match = YAML_KEY_LINE_RE.match(line)
        if match is None:
            continue
        key = match.group("key")
        current_indent = len(match.group("indent"))
        previous_nonempty_index = index - 1
        while previous_nonempty_index >= 0 and not lines[previous_nonempty_index].strip():
            previous_nonempty_index -= 1
        if previous_nonempty_index >= 0:
            previous_nonempty = lines[previous_nonempty_index]
            previous_key_match = YAML_KEY_LINE_RE.match(previous_nonempty)
            if previous_key_match is not None and previous_nonempty.rstrip().endswith(":"):
                previous_indent = len(previous_key_match.group("indent"))
                if current_indent > previous_indent:
                    continue
        original_indents = original_indent_map.get(key, ())
        if len(original_indents) != 1:
            continue
        target_indent = original_indents[0]
        if target_indent == current_indent or abs(target_indent - current_indent) > 8:
            continue
        lines[index] = (" " * target_indent) + line.lstrip()

    index = 0
    while index < len(lines):
        line = lines[index]
        key_match = YAML_KEY_LINE_RE.match(line)
        if key_match is None or line.rstrip().endswith(":") is False:
            index += 1
            continue
        key_indent = len(key_match.group("indent"))
        if key_indent == 0:
            index += 1
            continue
        next_index = index + 1
        while next_index < len(lines) and not lines[next_index].strip():
            next_index += 1
        if next_index >= len(lines):
            break
        first_child = lines[next_index]
        child_match = YAML_SEQUENCE_ITEM_RE.match(first_child)
        if child_match is None:
            index += 1
            continue
        child_indent = len(child_match.group("indent"))
        if child_indent != key_indent:
            index += 1
            continue
        target_indent = key_indent + 2
        while next_index < len(lines):
            current_line = lines[next_index]
            if not current_line.strip():
                next_index += 1
                continue
            current_indent = len(current_line) - len(current_line.lstrip(" "))
            if current_indent < child_indent:
                break
            if current_indent == child_indent and YAML_KEY_LINE_RE.match(current_line):
                break
            adjusted_indent = target_indent + (current_indent - child_indent)
            lines[next_index] = (" " * adjusted_indent) + current_line.lstrip()
            next_index += 1
        index = next_index

    index = 0
    while index < len(lines):
        line = lines[index]
        key_match = YAML_KEY_LINE_RE.match(line)
        if key_match is None or line.rstrip().endswith(":") is False:
            index += 1
            continue
        key_indent = len(key_match.group("indent"))
        next_index = index + 1
        while next_index < len(lines) and not lines[next_index].strip():
            next_index += 1
        if next_index >= len(lines):
            break
        first_child_match = YAML_SEQUENCE_ITEM_RE.match(lines[next_index])
        if first_child_match is None:
            index += 1
            continue
        sequence_indent = len(first_child_match.group("indent"))
        scan_index = next_index + 1
        while scan_index < len(lines):
            current_line = lines[scan_index]
            if not current_line.strip():
                scan_index += 1
                continue
            current_indent = len(current_line) - len(current_line.lstrip(" "))
            current_key_match = YAML_KEY_LINE_RE.match(current_line)
            current_sequence_match = YAML_SEQUENCE_ITEM_RE.match(current_line)
            if current_sequence_match is not None and current_indent > sequence_indent:
                previous_nonempty_index = scan_index - 1
                while (
                    previous_nonempty_index > index and not lines[previous_nonempty_index].strip()
                ):
                    previous_nonempty_index -= 1
                previous_nonempty = lines[previous_nonempty_index].rstrip()
                previous_nonempty_sequence_match = YAML_SEQUENCE_ITEM_RE.match(previous_nonempty)
                if previous_nonempty_sequence_match is None and not previous_nonempty.endswith(":"):
                    lines[scan_index] = (" " * sequence_indent) + current_line.lstrip()
                    scan_index += 1
                    continue
            if current_sequence_match is not None and current_indent < sequence_indent:
                lines[scan_index] = (" " * sequence_indent) + current_line.lstrip()
                scan_index += 1
                continue
            if current_key_match is not None and current_indent <= key_indent:
                break
            if current_indent < sequence_indent and current_sequence_match is None:
                break
            scan_index += 1
        index = scan_index

    repaired_lines: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        sequence_mapping_match = YAML_SEQUENCE_MAPPING_SCALAR_RE.match(line)
        if sequence_mapping_match is not None:
            indent = len(sequence_mapping_match.group("indent"))
            key = sequence_mapping_match.group("key")
            value = sequence_mapping_match.group("value").strip()
            if value and value[0] not in "\"'[{|>":
                continuation_index = index + 1
                continuation_parts: list[str] = []
                while continuation_index < len(lines):
                    continuation_line = lines[continuation_index]
                    if not continuation_line.strip():
                        break
                    continuation_indent = len(continuation_line) - len(
                        continuation_line.lstrip(" ")
                    )
                    if continuation_indent <= indent:
                        break
                    if YAML_KEY_LINE_RE.match(continuation_line) is not None:
                        break
                    if YAML_QUOTED_KEY_LINE_RE.match(continuation_line) is not None:
                        break
                    sequence_match = YAML_SEQUENCE_ITEM_RE.match(continuation_line)
                    if sequence_match is not None:
                        continuation_parts.append(sequence_match.group("content").strip())
                        continuation_index += 1
                        continue
                    continuation_parts.append(continuation_line.strip())
                    continuation_index += 1
                if continuation_parts:
                    flattened = " ".join([value, *continuation_parts]).strip()
                    repaired_lines.append(
                        (" " * indent) + f"- {key}: " + _yaml_single_quote(flattened)
                    )
                    index = continuation_index
                    continue

        mapping_match = YAML_MAPPING_SCALAR_RE.match(line)
        if mapping_match is not None:
            indent = len(mapping_match.group("indent"))
            value = mapping_match.group("value").strip()
            if value and value[0] not in "\"'[{|>":
                continuation_index = index + 1
                continuation_parts: list[str] = []
                while continuation_index < len(lines):
                    continuation_line = lines[continuation_index]
                    if not continuation_line.strip():
                        break
                    continuation_indent = len(continuation_line) - len(
                        continuation_line.lstrip(" ")
                    )
                    if continuation_indent < indent:
                        break
                    if YAML_KEY_LINE_RE.match(continuation_line) is not None:
                        break
                    if YAML_SEQUENCE_ITEM_RE.match(continuation_line) is not None:
                        break
                    continuation_parts.append(continuation_line.strip())
                    continuation_index += 1
                if continuation_parts:
                    flattened = " ".join([value, *continuation_parts]).strip()
                    repaired_lines.append(
                        (" " * indent)
                        + f"{mapping_match.group('key')}: "
                        + _yaml_single_quote(flattened)
                    )
                    index = continuation_index
                    continue

        match = YAML_SEQUENCE_ITEM_RE.match(line)
        if match is None:
            repaired_lines.append(line)
            index += 1
            continue

        indent = len(match.group("indent"))
        content = match.group("content").strip()
        if (
            not content
            or YAML_MAPPING_SEQUENCE_CONTENT_RE.match(content) is not None
            or content[0] in "\"'[{|>"
        ):
            repaired_lines.append(line)
            index += 1
            continue

        continuation_index = index + 1
        continuation_parts: list[str] = []
        while continuation_index < len(lines):
            continuation_line = lines[continuation_index]
            if not continuation_line.strip():
                break
            continuation_indent = len(continuation_line) - len(continuation_line.lstrip(" "))
            if continuation_indent <= indent:
                break
            continuation_parts.append(continuation_line.strip())
            continuation_index += 1

        flattened = " ".join([content, *continuation_parts]).strip()
        needs_quote = _yaml_plain_scalar_needs_quote(flattened)
        if continuation_parts and needs_quote:
            repaired_lines.append((" " * indent) + "- " + _yaml_single_quote(flattened))
            index = continuation_index
            continue

        if needs_quote:
            repaired_lines.append((" " * indent) + "- " + _yaml_single_quote(content))
            index += 1
            continue

        repaired_lines.append(line)
        index += 1

    repaired = "\n".join(repaired_lines)
    if candidate_text.endswith("\n"):
        repaired += "\n"
    return repaired


def repair_worktree_changed_spec_yaml(
    *,
    repo_root: Path,
    worktree_path: Path,
    changed_files: list[str],
) -> list[str]:
    yaml_module = get_yaml_module()
    repair_notes: list[str] = []

    for rel_path in changed_files:
        if not is_spec_node_path(rel_path):
            continue
        candidate_path = worktree_path / rel_path
        if not candidate_path.exists():
            continue
        original_path = repo_root / rel_path
        original_text = (
            original_path.read_text(encoding="utf-8") if original_path.exists() else None
        )
        candidate_text = candidate_path.read_text(encoding="utf-8")
        try:
            candidate_data = yaml_module.safe_load(candidate_text)
        except Exception:
            candidate_data = None
        else:
            if isinstance(candidate_data, dict):
                acceptance = candidate_data.get("acceptance")
                acceptance_evidence = candidate_data.get("acceptance_evidence")
                if not (
                    isinstance(acceptance, list)
                    and isinstance(acceptance_evidence, list)
                    and len(acceptance) != len(acceptance_evidence)
                ):
                    continue
            else:
                continue
        repaired_text = repair_candidate_yaml_text(candidate_text, original_text)
        if repaired_text == candidate_text:
            continue
        try:
            repaired_data = yaml_module.safe_load(repaired_text)
        except Exception:
            continue
        if not isinstance(repaired_data, dict):
            continue
        candidate_path.write_text(dump_yaml_text(repaired_data), encoding="utf-8")
        repair_notes.append(rel_path)

    return repair_notes


def effective_child_executor_timeout_seconds(
    run_authority: tuple[str, ...],
    requested_profile: str | None = None,
    operator_target: bool = False,
    requested_timeout_seconds: int | None = None,
) -> int:
    profile = resolve_execution_profile(
        requested_profile=requested_profile,
        run_authority=run_authority,
        operator_target=operator_target,
    )
    if requested_timeout_seconds is not None:
        return requested_timeout_seconds
    return max(
        profile.timeout_seconds,
        reasoning_effort_timeout_floor_seconds(profile.reasoning_effort),
    )


def quiet_progress_windows_for_reasoning(reasoning_effort: str) -> int:
    """Allow extra quiet windows for long-form deliberation on heavier reasoning modes."""
    if reasoning_effort == "xhigh":
        return XHIGH_QUIET_PROGRESS_WINDOWS
    return 0


def capture_nested_executor_progress(
    worktree_path: Path,
    stdout_chunks: list[str],
    stderr_chunks: list[str],
) -> tuple[int, int, int]:
    """Capture coarse progress signals without inspecting semantic content."""
    newest_mtime_ns = 0
    for root, dirs, files in os.walk(worktree_path):
        dirs[:] = [name for name in dirs if name != ".git"]
        for filename in files:
            path = Path(root) / filename
            try:
                newest_mtime_ns = max(newest_mtime_ns, path.stat().st_mtime_ns)
            except FileNotFoundError:
                continue
    return (
        sum(len(chunk) for chunk in stdout_chunks),
        sum(len(chunk) for chunk in stderr_chunks),
        newest_mtime_ns,
    )


def bootstrap_child_hint(node: SpecNode, specs: list[SpecNode]) -> dict[str, str] | None:
    if not is_seed_like_spec(node.data):
        return None

    seed_text_parts = [node.prompt]
    acceptance = node.data.get("acceptance", [])
    if isinstance(acceptance, list):
        seed_text_parts.extend(str(item) for item in acceptance)
    seed_text = " ".join(seed_text_parts).lower()
    if not any(
        term in seed_text
        for term in ("seed", "child spec", "child specs", "descendant", "refine unresolved")
    ):
        return None

    child_id = next_sequential_spec_id(specs)
    child_path = f"specs/nodes/{child_id}.yaml"
    if not can_create_new_spec_files(node, child_path):
        return None
    return {
        "id": child_id,
        "path": child_path,
    }


def operator_requests_child_materialization(operator_note: str) -> bool:
    """Return True when the operator note explicitly asks for one new child spec.

    This keeps child-spec creation as an explicit, operator-directed action for
    non-seed parents rather than an implicit side effect of ordinary refinement.
    """
    if not operator_note.strip():
        return False
    note = operator_note.lower()
    creation_markers = (
        "child spec",
        "child node",
        "new spec",
        "new child",
        "materialize",
        "create",
        "delegate",
        "delegation",
        "bounded child",
    )
    return any(marker in note for marker in creation_markers)


def targeted_child_materialization_hint(
    node: SpecNode,
    specs: list[SpecNode],
    *,
    operator_target: bool = False,
    operator_note: str = "",
    run_authority: tuple[str, ...] = (),
    reserved_hint: dict[str, str] | None = None,
) -> dict[str, str] | None:
    """Suggest one new child spec for explicit targeted child-creation runs."""
    if not operator_target or not operator_requests_child_materialization(operator_note):
        return None
    if not run_authority_grants_child_materialization(run_authority):
        return None
    if not node_supports_child_delegation(node):
        return None

    hint = reserved_hint
    if hint is None:
        child_id = next_sequential_spec_id(specs)
        child_path = f"specs/nodes/{child_id}.yaml"
        hint = {"id": child_id, "path": child_path}
    child_id = str(hint.get("id", "")).strip()
    child_path = str(hint.get("path", "")).strip()
    if not can_create_new_spec_files(node, child_path):
        return None
    return {
        "id": child_id,
        "path": child_path,
    }


def targeted_child_materialization_requested(
    *,
    node: SpecNode,
    operator_target: bool = False,
    operator_note: str = "",
    run_authority: tuple[str, ...] = (),
) -> bool:
    return (
        operator_target
        and operator_requests_child_materialization(operator_note)
        and run_authority_grants_child_materialization(run_authority)
        and node_supports_child_delegation(node)
    )


def effective_allowed_paths_for_run(
    node: SpecNode,
    *,
    child_materialization_hint: dict[str, str] | None = None,
) -> list[str]:
    _ = child_materialization_hint
    return list(node.allowed_paths) or implicit_source_allowed_paths(node)


def effective_outputs_for_run(
    node: SpecNode,
    *,
    child_materialization_hint: dict[str, str] | None = None,
) -> list[str]:
    outputs = list(node.outputs)
    if child_materialization_hint is None:
        return outputs
    child_path = str(child_materialization_hint.get("path", "")).strip()
    if child_path and child_path not in outputs:
        outputs.append(child_path)
    return outputs


def child_materialization_preflight_errors(
    *,
    node: SpecNode,
    specs: list[SpecNode],
    operator_target: bool = False,
    operator_note: str = "",
    run_authority: tuple[str, ...] = (),
    child_materialization_hint: dict[str, str] | None = None,
) -> list[str]:
    if not operator_target or not operator_requests_child_materialization(operator_note):
        return []

    errors: list[str] = []
    if not run_authority_grants_child_materialization(run_authority):
        errors.append(
            "Child materialization was requested, but the run authority does not grant "
            "'materialize_one_child'."
        )
    if not node_supports_child_delegation(node):
        errors.append(
            "Child materialization was requested, but the selected node does not expose "
            "semantic delegation constraints compatible with creating a bounded child."
        )
    hint = child_materialization_hint or {"id": next_sequential_spec_id(specs)}
    child_id = str(hint.get("id", "")).strip()
    child_path = str(hint.get("path", "")).strip() or f"specs/nodes/{child_id}.yaml"
    if not can_create_new_spec_files(node, child_path):
        errors.append(
            "Child materialization was requested, but allowed_paths do not explicitly "
            f"authorize the proposed child spec path: {child_path}"
        )
    return errors


def sanitize_source_after_child_materialization(
    *,
    before_data: dict[str, Any],
    after_data: dict[str, Any],
    requested: bool,
) -> dict[str, Any]:
    """Keep run-level child authority ephemeral on the parent source spec."""
    if not requested:
        return after_data
    sanitized = copy.deepcopy(after_data)
    sanitized["outputs"] = copy.deepcopy(before_data.get("outputs", []))
    sanitized["allowed_paths"] = copy.deepcopy(before_data.get("allowed_paths", []))
    return sanitized


def restore_ephemeral_child_authority_fields(
    *,
    node: SpecNode,
    before_data: dict[str, Any],
    requested: bool,
) -> None:
    if not requested:
        return
    if "outputs" in before_data:
        node.data["outputs"] = copy.deepcopy(before_data["outputs"])
    else:
        node.data.pop("outputs", None)
    if "allowed_paths" in before_data:
        node.data["allowed_paths"] = copy.deepcopy(before_data["allowed_paths"])
    else:
        node.data.pop("allowed_paths", None)


def restore_source_lifecycle_fields_after_split_sync(
    *,
    node: SpecNode,
    before_data: dict[str, Any],
) -> None:
    """Keep source lifecycle fields canonical during split-required sync."""

    for field in ("status", "maturity", "gate_state", "required_human_action"):
        if field in before_data:
            node.data[field] = copy.deepcopy(before_data[field])
        else:
            node.data.pop(field, None)
    node.data["proposed_status"] = None
    node.data["proposed_maturity"] = None


def normalize_materialized_child_specs(child_relpaths: list[str]) -> None:
    yaml_module = get_yaml_module()
    for child_relpath in child_relpaths:
        child_path = ROOT / child_relpath
        if not child_path.exists():
            continue
        child_data = yaml_module.safe_load(child_path.read_text(encoding="utf-8")) or {}
        if not isinstance(child_data, dict):
            continue
        normalized = canonical_spec_snapshot(child_data)
        normalized["outputs"] = [child_relpath]
        normalized["allowed_paths"] = [child_relpath]
        write_spec_yaml(child_path, normalized)


def build_prompt(
    node: SpecNode,
    refactor_work_item: dict[str, Any] | None = None,
    *,
    operator_target: bool = False,
    operator_note: str = "",
    mutation_budget: tuple[str, ...] = (),
    run_authority: tuple[str, ...] = (),
    child_materialization_hint: dict[str, str] | None = None,
) -> str:
    """Build the operator/agent prompt for one bounded run.

    The prompt always includes the generic refinement policy and may add one
    specialized mode section:
    - `explicit_target_refine`
    - `ancestor_reconcile`
    - `graph_refactor`
    - `split_refactor_proposal`

    Prompt shaping is part of supervisor behavior, but the allowed modes and
    their authority boundaries are governed by canonical specs.
    """
    agents_hint = ""
    if AGENTS_FILE.exists():
        agents_hint = "Read and follow AGENTS.md before editing anything.\n\n"

    all_specs = load_specs()
    bootstrap_hint = bootstrap_child_hint(node, all_specs)
    effective_child_materialization_hint = targeted_child_materialization_hint(
        node,
        all_specs,
        operator_target=operator_target,
        operator_note=operator_note,
        run_authority=run_authority,
        reserved_hint=child_materialization_hint,
    )
    effective_allowed_paths = effective_allowed_paths_for_run(
        node,
        child_materialization_hint=effective_child_materialization_hint,
    )
    effective_outputs = effective_outputs_for_run(
        node,
        child_materialization_hint=effective_child_materialization_hint,
    )
    allowed_paths = (
        "\n".join(f"- {path}" for path in effective_allowed_paths) or "- (not specified)"
    )
    outputs = "\n".join(f"- {path}" for path in effective_outputs) or "- (not specified)"
    selection_mode = selection_mode_for_node(
        node,
        refactor_work_item=refactor_work_item,
        operator_target=operator_target,
    )
    acceptance_listing = (
        "\n".join(
            f"- [{idx}] {criterion}"
            for idx, criterion in enumerate(node.data.get("acceptance", []), start=1)
        )
        or "- (not specified)"
    )
    refinement_section = """

Refinement policy:
- Treat the current spec as one bounded piece of a larger puzzle graph.
- Aim for one bounded concern per spec node, not one large document.
- Prefer the smallest honest change that can advance this node by one status step.
- Do not try to make the current spec complete in one run.
- Resolve at most one concrete unresolved area per run.
- If multiple independent refinement paths are possible, choose one and leave the others unchanged.
- Prefer creating or refining one child spec over expanding the parent when the topic is separable.
- If decomposition is clearly needed, you may create multiple sibling child specs in one run.
- If the node remains non-atomic after your edits, end with RUN_OUTCOME: split_required.
""".rstrip()
    mode_section = ""
    operator_section = ""
    if operator_note.strip():
        operator_section = f"""

Operator intent:
- The operator supplied this one-run note to steer the refinement.
- Treat it as ephemeral run context, not as canonical policy or spec content by itself.
- Use it to choose one bounded concern within the current node's allowed scope.
{operator_note.strip()}
""".rstrip()
    mutation_budget_section = ""
    if mutation_budget:
        mutation_budget_lines = "\n".join(f"- {item}" for item in mutation_budget)
        mutation_budget_section = f"""

Mutation budget:
- This run is expected to stay within these mutation classes
  unless review or escalation is warranted.
{mutation_budget_lines}
- If the smallest honest refinement needs a class outside
  this budget, do not smuggle it in silently.
""".rstrip()
    run_authority_section = ""
    if run_authority:
        run_authority_lines = "\n".join(f"- {item}" for item in run_authority)
        run_authority_section = f"""

Run authority grant:
{run_authority_lines}
""".rstrip()
    if selection_mode == "explicit_target_refine":
        mode_section = """

Refinement mode: explicit_target_refine
- This run was explicitly targeted by the operator.
- Bypass heuristic selector priority and focus only on this one spec node.
- Respect the existing scope, ontology, and gate contracts; explicit targeting
  does not authorize unrelated graph changes.
- If the node is already in review_pending or another gate state, treat this as
  an intentional rerun to improve or narrow the node rather than as a request
  to bypass review.
""".rstrip()
    elif selection_mode == "ancestor_reconcile":
        mode_section = """

Refinement mode: ancestor_reconcile
- This spec appears semantically unlocked by descendant specs that already exist.
- Focus on reconciling this ancestor with the current graph state.
- Prefer updating links, acceptance_evidence, blockers,
  and status-readiness over expanding scope.
- Do not open new independent refinement branches unless
  the current node is still structurally blocked.
- Keep the change narrow enough that further unlocked ancestors can be handled in later runs.
""".rstrip()
    elif selection_mode == "split_refactor_proposal":
        artifact_relpath = (
            str(refactor_work_item.get("proposal_artifact_relpath", "")).strip()
            if refactor_work_item
            else ""
        )
        planned_run_id = (
            str(refactor_work_item.get("planned_run_id", "")).strip() if refactor_work_item else ""
        )
        live_child_ids = refactor_work_item.get("live_child_ids", []) if refactor_work_item else []
        accepted_child_ids = (
            refactor_work_item.get("accepted_child_ids", []) if refactor_work_item else []
        )
        live_children_text = ", ".join(
            str(item).strip() for item in live_child_ids if str(item).strip()
        )
        accepted_children_text = ", ".join(
            str(item).strip() for item in accepted_child_ids if str(item).strip()
        )
        retrospective_section = ""
        if refactor_work_item and refactor_work_item.get("retrospective_target"):
            retrospective_section = f"""
- This target already sits inside a live graph region with existing child specs.
- Preserve stable IDs and lineage for surviving child specs whenever possible.
- Accepted child work must remain traceable and must not be silently invalidated.
- Live child spec IDs: {live_children_text or "(none)"}
- Accepted child spec IDs: {accepted_children_text or "(none)"}
""".rstrip()
        mode_section = f"""

Refinement mode: split_refactor_proposal
- This run was explicitly targeted by the operator for {SPLIT_REFACTOR_KIND}.
- Analyze this one oversized non-seed spec and emit a structured proposal artifact only.
- Current run ID: {planned_run_id or "(unspecified)"}
- Proposal artifact path: {artifact_relpath or "(unspecified)"}
- Do not edit canonical spec files under specs/nodes/.
- Keep the parent as an overview or integration node with the same stable ID and domain terminology.
- Each suggested child must represent one bounded concern.
- Every current parent acceptance criterion must be mapped exactly once
  to parent_retained or one child slot.
- Cross-cutting acceptance stays on the parent and must not be duplicated across children.
- parent_after_split.intended_depends_on must not exceed {ATOMICITY_MAX_BLOCKING_CHILDREN}
  blocking child slots; if a clean split needs more, end with RUN_OUTCOME: escalate.
{retrospective_section}
- Suggested child IDs and paths are advisory snapshot outputs only;
  they do not reserve canonical IDs.
- If the split cannot be proposed cleanly without governance change, end with RUN_OUTCOME: escalate.
- Write JSON to the proposal artifact path with these top-level fields:
  id, proposal_type, refactor_kind, target_spec_id, source_signal, source_run_ids,
  execution_policy, parent_after_split, suggested_children, acceptance_mapping,
  lineage_updates, status.
- Use these exact literal values:
  - id = refactor_proposal::{node.id}::{SPLIT_REFACTOR_SIGNAL}
  - proposal_type = refactor_proposal
  - refactor_kind = {SPLIT_REFACTOR_KIND}
  - target_spec_id = {node.id}
  - source_signal = {SPLIT_REFACTOR_SIGNAL}
  - execution_policy = emit_proposal
- source_run_ids must include the current run ID above.
- parent_after_split must include narrowed_role_summary,
  retained_acceptance, and intended_depends_on.
- Each suggested_children entry must include slot_key, suggested_id, suggested_path,
  bounded_concern_summary, suggested_title, suggested_prompt, and assigned_acceptance.
- acceptance_mapping entries should use acceptance_index, acceptance_text, and target.
- lineage_updates must include parent_depends_on_add and child_refines_add.
- Do not use plain strings for acceptance or lineage references.
- Use objects with these exact shapes:
  - parent_after_split.retained_acceptance[] =
    {{ "acceptance_index": <int>, "acceptance_text": "<exact source text>" }}
  - parent_after_split.intended_depends_on[] =
    {{ "slot_key": "<child slot>", "suggested_id": "<child id>" }}
  - suggested_children[].assigned_acceptance[] =
    {{ "acceptance_index": <int>, "acceptance_text": "<exact source text>" }}
  - lineage_updates.parent_depends_on_add[] =
    {{ "slot_key": "<child slot>", "suggested_id": "<child id>" }}
  - lineage_updates.child_refines_add[] =
    {{
      "slot_key": "<child slot>",
      "suggested_id": "<child id>",
      "refines": ["{node.id}"]
    }}
- Example JSON skeleton:
  {{
    "id": "refactor_proposal::{node.id}::{SPLIT_REFACTOR_SIGNAL}",
    "proposal_type": "refactor_proposal",
    "refactor_kind": "{SPLIT_REFACTOR_KIND}",
    "target_spec_id": "{node.id}",
    "source_signal": "{SPLIT_REFACTOR_SIGNAL}",
    "source_run_ids": ["{planned_run_id or "CURRENT-RUN-ID"}"],
    "execution_policy": "emit_proposal",
    "parent_after_split": {{
      "narrowed_role_summary": "...",
        "retained_acceptance": [
          {{
            "acceptance_index": 1,
            "acceptance_text": "<exact source text>"
          }}
        ],
      "intended_depends_on": [
        {{
          "slot_key": "child_slot",
          "suggested_id": "SG-SPEC-XXXX"
        }}
      ]
    }},
    "suggested_children": [
      {{
        "slot_key": "child_slot",
        "suggested_id": "SG-SPEC-XXXX",
        "suggested_path": "specs/nodes/SG-SPEC-XXXX.yaml",
        "bounded_concern_summary": "...",
        "suggested_title": "...",
        "suggested_prompt": "...",
        "assigned_acceptance": [
          {{
            "acceptance_index": 2,
            "acceptance_text": "..."
          }}
        ]
      }}
    ],
    "acceptance_mapping": [
      {{
        "acceptance_index": 1,
        "acceptance_text": "...",
        "target": "parent_retained"
      }},
      {{
        "acceptance_index": 2,
        "acceptance_text": "...",
        "target": "child_slot"
      }}
    ],
    "lineage_updates": {{
      "parent_depends_on_add": [
        {{
          "slot_key": "child_slot",
          "suggested_id": "SG-SPEC-XXXX"
        }}
      ],
      "child_refines_add": [
        {{
          "slot_key": "child_slot",
          "suggested_id": "SG-SPEC-XXXX",
          "refines": ["{node.id}"]
        }}
      ]
    }},
    "status": "proposed"
  }}

Current parent acceptance criteria:
{acceptance_listing}
""".rstrip()
    elif selection_mode == "graph_refactor":
        signal = str(refactor_work_item.get("signal", "")).strip() if refactor_work_item else ""
        recommended_action = (
            str(refactor_work_item.get("recommended_action", "")).strip()
            if refactor_work_item
            else ""
        )
        details = refactor_work_item.get("details") if refactor_work_item else None
        details_text = json.dumps(details, ensure_ascii=False) if details is not None else "none"
        mode_section = f"""

Refinement mode: graph_refactor
- This run was selected from the derived refactor queue.
- Focus on the queued local graph refactor for this spec rather than broadening product scope.
- Signal: {signal or "(unspecified)"}
- Recommended action: {recommended_action or "(unspecified)"}
- Details: {details_text}
- Stay within current governance rules; do not modify ontology,
  approval boundaries, or supervisor authority.
- Prefer repairing structure, narrowing scope, or fixing canonical
  links over adding new unrelated content.
- If the issue cannot be resolved locally without governance change, end with RUN_OUTCOME: escalate.
""".rstrip()
    bootstrap_section = ""
    if bootstrap_hint is not None:
        bootstrap_section = f"""

Bootstrap guidance:
- You may create one or more new child specs in this run
  if decomposition is the right way to refine the current seed spec.
- Suggested first child spec ID: {bootstrap_hint["id"]}
- Suggested child spec path: {bootstrap_hint["path"]}
- If you create additional siblings, continue with the next sequential spec IDs.
- Prefer creating the child specs in this run rather than only describing them in prose.
- Each child spec should own one concrete unresolved refinement area from the current node.
- Give each child its own acceptance criteria, prompt, outputs, and allowed_paths.
- Update the current node so each blocking child is part of
  its refinement path. Prefer `depends_on` entries for children
  that must be completed before the parent can advance.
- Do not mark the current node `linked` unless concrete
  descendant specs now exist and the dependency/refinement
  chain is explicit.
""".rstrip()
    child_materialization_section = ""
    if effective_child_materialization_hint is not None:
        child_materialization_section = f"""

Child materialization guidance:
- This operator-targeted run may materialize exactly one new child spec
  if the current node already implies a delegated bounded concern.
- Suggested child spec ID: {effective_child_materialization_hint["id"]}
- Suggested child spec path: {effective_child_materialization_hint["path"]}
- Keep the parent update minimal and reviewable.
- Make the child explicit in the parent refinement/dependency chain only if
  the delegated concern is concrete enough to become a standalone spec now.
- Prefer one child over multiple siblings in this mode.
- Give the child its own acceptance criteria, prompt, outputs, and allowed_paths.
- Do not silently widen this into a broad graph refactor.
""".rstrip()

    return f"""
You are refining a specification node in SpecGraph.

{agents_hint}Spec node ID: {node.id}
Title: {node.title}
Current status: {node.status}
Current maturity: {node.maturity:.2f}

Goal:
{node.prompt}
{operator_section}
{mutation_budget_section}
{run_authority_section}

Allowed paths:
{allowed_paths}

Expected outputs:
{outputs}
{refinement_section}
{mode_section}
{bootstrap_section}
{child_materialization_section}

Rules:
- Refine specification only.
- Do not implement runtime code.
- Use repository files and declared project memory as the primary context for this run.
- Do not browse the web or external sources unless the operator explicitly
  requested external research.
- Preserve stable IDs and terminology.
- Do not edit files outside allowed paths.
- Keep acceptance_evidence aligned 1:1 with acceptance criteria.
- Ground each acceptance_evidence item in the matching criterion using the same
  concrete terms, identifiers, or outcome; avoid placeholder evidence text.
- If blocked, stop and explain blocker clearly.
- Print RUN_OUTCOME and BLOCKER to stdout only; never write them into edited files.
- End with exactly two machine-readable lines:
  RUN_OUTCOME: done|retry|split_required|blocked|escalate
  BLOCKER: <text or none>
""".strip()


def validate_yaml(path: Path) -> list[str]:
    yaml_module = get_yaml_module()
    errors: list[str] = []
    try:
        with path.open("r", encoding="utf-8") as file:
            yaml_module.safe_load(file)
    except Exception as exc:
        errors.append(f"Invalid YAML in {path.as_posix()}: {exc}")
    return errors


def validate_outputs(node: SpecNode, base_dir: Path) -> list[str]:
    errors: list[str] = []
    for rel_path in node.outputs:
        output_path = base_dir / rel_path
        if not output_path.exists():
            errors.append(f"Missing expected output: {rel_path}")
            continue
        if output_path.suffix.lower() in {".yaml", ".yml"}:
            errors.extend(validate_yaml(output_path))
    return errors


def validate_changed_files_against_allowed_paths(
    allowed_paths: list[str],
    changed_files: list[str],
) -> list[str]:
    if not allowed_paths:
        return [f"Changed file outside allowed_paths: {changed}" for changed in changed_files]

    errors: list[str] = []
    for changed in changed_files:
        changed_path = PurePosixPath(changed)
        if not any(changed_path.match(pattern) for pattern in allowed_paths):
            errors.append(f"Changed file outside allowed_paths: {changed}")
    return errors


def validate_allowed_paths(node: SpecNode, changed_files: list[str]) -> list[str]:
    return validate_changed_files_against_allowed_paths(
        effective_allowed_paths_for_run(node),
        changed_files,
    )


def select_sync_paths(allowed_paths: list[str], changed_files: list[str]) -> list[str]:
    """Return changed paths eligible for sync back to root.

    Callers should pass effective allowed paths after applying default-deny
    fallback semantics for the selected source node.
    """
    if not allowed_paths:
        return []
    return [
        path
        for path in changed_files
        if any(PurePosixPath(path).match(pattern) for pattern in allowed_paths)
    ]


def coerce_pending_digest_map(value: Any) -> dict[str, str | None]:
    if not isinstance(value, dict):
        return {}
    coerced: dict[str, str | None] = {}
    for key, digest in value.items():
        rel_path = str(key).strip()
        if not rel_path:
            continue
        if digest is None:
            coerced[rel_path] = None
            continue
        digest_text = str(digest).strip()
        coerced[rel_path] = digest_text or None
    return coerced


def pending_review_sync_paths(node: SpecNode) -> list[str]:
    raw_paths = node.data.get("pending_sync_paths")
    if isinstance(raw_paths, list):
        paths = [str(path).strip() for path in raw_paths if str(path).strip()]
        return sorted(dict.fromkeys(paths))
    changed_files = list(node.data.get("last_changed_files", []))
    return select_sync_paths(effective_allowed_paths_for_run(node), changed_files)


def pending_review_base_divergence_paths(node: SpecNode, rel_paths: list[str]) -> list[str]:
    recorded = coerce_pending_digest_map(node.data.get("pending_base_digests"))
    if not recorded:
        return []
    current = snapshot_sync_digests(rel_paths, base_dir=ROOT)
    return [
        f"{rel_path}:<canonical-base-mismatch>"
        for rel_path in rel_paths
        if current.get(rel_path) != recorded.get(rel_path)
    ]


def pending_review_candidate_divergence_paths(
    node: SpecNode, worktree_path: Path, rel_paths: list[str]
) -> list[str]:
    recorded = coerce_pending_digest_map(node.data.get("pending_candidate_digests"))
    if not recorded:
        return []
    current = snapshot_sync_digests(rel_paths, base_dir=worktree_path)
    return [
        f"{rel_path}:<staged-candidate-mismatch>"
        for rel_path in rel_paths
        if current.get(rel_path) != recorded.get(rel_path)
    ]


def clear_pending_review_state(node: SpecNode) -> None:
    node.data.pop("pending_sync_paths", None)
    node.data.pop("pending_base_digests", None)
    node.data.pop("pending_candidate_digests", None)
    node.data.pop("pending_run_id", None)


def validate_status_format(node_data: dict[str, Any]) -> list[str]:
    status = str(node_data.get("status", "stub")).strip()
    if status not in VALID_STATUSES:
        return [f"Unknown status: {status}"]
    acceptance = node_data.get("acceptance")
    if not isinstance(acceptance, list):
        return ["acceptance list must be present"]
    return []


def validate_acceptance_evidence(node_data: dict[str, Any]) -> list[str]:
    acceptance = node_data.get("acceptance")
    if not isinstance(acceptance, list):
        return ["acceptance list must be present"]

    evidence = node_data.get("acceptance_evidence")
    if not isinstance(evidence, list):
        return ["acceptance_evidence list must be present"]
    if len(evidence) != len(acceptance):
        return [
            "acceptance_evidence size must match acceptance size "
            f"({len(evidence)} != {len(acceptance)})"
        ]

    errors: list[str] = []
    for idx, item in enumerate(evidence, start=1):
        if isinstance(item, dict):
            criterion_text = str(item.get("criterion", "")).strip()
            evidence_text = str(item.get("evidence", "")).strip()
            if not criterion_text:
                errors.append(f"acceptance_evidence[{idx}].criterion must be non-empty")
            if not evidence_text:
                errors.append(f"acceptance_evidence[{idx}].evidence must be non-empty")
            continue
        if not str(item).strip():
            errors.append(f"acceptance_evidence[{idx}] must be non-empty")
    return errors


def semantic_text_tokens(text: str, *, min_len: int = 4) -> set[str]:
    lowered = str(text).lower()
    tokens = {
        token
        for token in SEMANTIC_WORD_RE.findall(lowered)
        if len(token) >= min_len and token not in SEMANTIC_ACCEPTANCE_STOPWORDS
    }
    for token in BACKTICK_TOKEN_RE.findall(str(text)):
        normalized = token.strip().lower()
        if normalized:
            tokens.add(normalized)
    for token in UPPER_IDENTIFIER_RE.findall(str(text)):
        normalized = token.strip().lower()
        if normalized:
            tokens.add(normalized)
    return tokens


def acceptance_evidence_text(item: Any) -> tuple[str, str]:
    if isinstance(item, dict):
        return (
            str(item.get("criterion", "")).strip(),
            str(item.get("evidence", "")).strip(),
        )
    return "", str(item).strip()


def acceptance_evidence_semantically_grounded(
    *,
    criterion: str,
    evidence_item: Any,
) -> bool:
    evidence_criterion, evidence_text = acceptance_evidence_text(evidence_item)
    if not evidence_text:
        return False

    criterion_text = str(criterion).strip()
    if not criterion_text:
        return True

    if evidence_criterion and evidence_criterion != criterion_text:
        return False

    criterion_tokens = semantic_text_tokens(criterion_text)
    if not criterion_tokens:
        criterion_tokens = semantic_text_tokens(criterion_text, min_len=2)
        if not criterion_tokens:
            normalized_criterion = " ".join(SEMANTIC_WORD_RE.findall(criterion_text.lower()))
            normalized_evidence = " ".join(SEMANTIC_WORD_RE.findall(evidence_text.lower()))
            return bool(normalized_criterion and normalized_criterion in normalized_evidence)

    evidence_tokens = semantic_text_tokens(evidence_text)
    if not evidence_tokens:
        evidence_tokens = semantic_text_tokens(evidence_text, min_len=2)
    return bool(criterion_tokens & evidence_tokens)


def validate_acceptance_evidence_semantics(node_data: dict[str, Any]) -> list[str]:
    acceptance = node_data.get("acceptance")
    evidence = node_data.get("acceptance_evidence")
    if not isinstance(acceptance, list) or not isinstance(evidence, list):
        return []
    if len(acceptance) != len(evidence):
        return []

    errors: list[str] = []
    for idx, criterion in enumerate(acceptance, start=1):
        criterion_text = str(criterion).strip()
        evidence_item = evidence[idx - 1]
        evidence_criterion, _evidence_text = acceptance_evidence_text(evidence_item)
        if evidence_criterion and evidence_criterion != criterion_text:
            errors.append(
                f"acceptance_evidence[{idx}].criterion must match acceptance[{idx}] exactly"
            )
            continue
        if not acceptance_evidence_semantically_grounded(
            criterion=criterion_text,
            evidence_item=evidence_item,
        ):
            errors.append(
                f"acceptance_evidence[{idx}] must semantically ground acceptance[{idx}] "
                "using criterion terms, identifiers, or a concrete outcome"
            )
    return errors


def validate_relation_semantics(node_data: dict[str, Any]) -> list[str]:
    """Reject redundant weak relations when a stronger edge already exists."""
    errors: list[str] = []
    relation_lists: dict[str, set[str]] = {}

    for field in ("depends_on", "relates_to", "refines"):
        value = node_data.get(field, [])
        if value is None:
            relation_lists[field] = set()
            continue
        if not isinstance(value, list):
            errors.append(f"{field} must be a list when present")
            relation_lists[field] = set()
            continue
        relation_lists[field] = {str(item).strip() for item in value if str(item).strip()}

    for target in sorted(relation_lists["relates_to"] & relation_lists["refines"]):
        errors.append(
            f"relates_to MUST NOT include {target} when refines already targets the same spec"
        )

    for target in sorted(relation_lists["relates_to"] & relation_lists["depends_on"]):
        errors.append(
            f"relates_to MUST NOT include {target} when depends_on already targets the same spec"
        )

    return errors


def validate_atomicity(node: SpecNode) -> list[str]:
    if str(node.data.get("kind", "")).strip() != "spec":
        return []
    if is_seed_like_spec(node.data):
        return []

    errors: list[str] = []
    acceptance = node.data.get("acceptance")
    if isinstance(acceptance, list) and len(acceptance) > ATOMICITY_MAX_ACCEPTANCE:
        errors.append(
            "Atomicity gate exceeded: "
            f"{len(acceptance)} acceptance criteria > {ATOMICITY_MAX_ACCEPTANCE}. "
            "Split independent concerns into child specs."
        )

    depends_on = node.data.get("depends_on")
    if isinstance(depends_on, list) and len(depends_on) > ATOMICITY_MAX_BLOCKING_CHILDREN:
        errors.append(
            "Atomicity gate exceeded: "
            f"{len(depends_on)} blocking children > {ATOMICITY_MAX_BLOCKING_CHILDREN}. "
            "Prefer smaller sibling specs or an intermediate overview node."
        )

    return errors


def validate_split_refactor_target(node: SpecNode) -> list[str]:
    errors: list[str] = []
    if str(node.data.get("kind", "")).strip() != "spec":
        errors.append("split_oversized_spec requires kind: spec")
    if is_seed_like_spec(node.data):
        errors.append("split_oversized_spec cannot target a seed-like or root overview spec")
    atomicity_errors = validate_atomicity(node)
    if not atomicity_errors:
        errors.append("split_oversized_spec requires an oversized non-seed spec target")
    return errors


def build_split_refactor_work_item(
    node: SpecNode,
    specs: list[SpecNode] | None = None,
) -> dict[str, Any]:
    local_specs = specs or load_specs()
    live_child_ids = [
        child.id for child in active_refining_child_specs(node, local_specs) if child.id
    ]
    accepted_child_ids = accepted_child_spec_ids(node, local_specs)
    proposal_type = "refactor_proposal"
    proposal_id = f"{proposal_type}::{node.id}::{SPLIT_REFACTOR_SIGNAL}"
    artifact_relpath = proposal_artifact_relpath(
        proposal_type=proposal_type,
        spec_id=node.id,
        signal=SPLIT_REFACTOR_SIGNAL,
    )
    return {
        "id": proposal_id,
        "proposal_type": proposal_type,
        "work_item_type": proposal_type,
        "signal": SPLIT_REFACTOR_SIGNAL,
        "source_signal": SPLIT_REFACTOR_SIGNAL,
        "refactor_kind": SPLIT_REFACTOR_KIND,
        "recommended_action": "emit_split_proposal",
        "execution_policy": "emit_proposal",
        "target_spec_id": node.id,
        "proposal_artifact_relpath": artifact_relpath,
        "retrospective_target": bool(live_child_ids),
        "live_child_ids": live_child_ids,
        "accepted_child_ids": accepted_child_ids,
    }


def validate_transition(from_status: str, to_status: str | None) -> list[str]:
    if from_status not in VALID_STATUSES:
        return [f"Unknown source status: {from_status}"]

    expected = STATUS_PROGRESSION.get(from_status)
    if expected is None:
        if to_status is not None and to_status != from_status:
            return [f"No valid forward transition from {from_status} to {to_status}"]
        return []

    if to_status != expected:
        return [f"Invalid transition: expected {from_status}->{expected}, got {to_status}"]
    return []


def collect_value_paths(value: Any, prefix: str) -> list[str]:
    """Return stable paths for every leaf below a newly added or removed value."""
    if isinstance(value, dict):
        paths: list[str] = [prefix]
        for key, item in value.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            paths.extend(collect_value_paths(item, child_prefix))
        return paths
    if isinstance(value, list):
        paths: list[str] = [prefix]
        for idx, item in enumerate(value):
            child_prefix = f"{prefix}[{idx}]"
            paths.extend(collect_value_paths(item, child_prefix))
        return paths
    return [prefix or "<root>"]


def collect_changed_paths(before: Any, after: Any, prefix: str = "") -> list[str]:
    """Return stable dot-paths describing semantic changes between two values."""
    if type(before) is not type(after):
        merged = collect_value_paths(before, prefix or "<root>") + collect_value_paths(
            after, prefix or "<root>"
        )
        return sorted(set(merged))

    if isinstance(before, dict):
        paths: list[str] = []
        keys = sorted(set(before) | set(after))
        for key in keys:
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            if key not in before or key not in after:
                missing_value = before.get(key) if key in before else after.get(key)
                paths.extend(collect_value_paths(missing_value, child_prefix))
                continue
            paths.extend(collect_changed_paths(before[key], after[key], child_prefix))
        return paths

    if isinstance(before, list):
        paths: list[str] = []
        max_len = max(len(before), len(after))
        for idx in range(max_len):
            child_prefix = f"{prefix}[{idx}]"
            if idx >= len(before) or idx >= len(after):
                missing_value = before[idx] if idx < len(before) else after[idx]
                paths.extend(collect_value_paths(missing_value, child_prefix))
                continue
            paths.extend(collect_changed_paths(before[idx], after[idx], child_prefix))
        return paths

    if before != after:
        return [prefix or "<root>"]
    return []


def path_matches_prefix(path: str, prefixes: tuple[str, ...]) -> bool:
    """Return True when a diff path matches one of the semantic prefixes."""
    normalized = path.replace("[", ".[").split(".[", maxsplit=1)[0]
    return any(
        path == prefix or path.startswith(f"{prefix}.") or normalized == prefix
        for prefix in prefixes
    )


def classify_refinement_change(
    *,
    node_data: dict[str, Any],
    diff_paths: list[str],
    changed_spec_files: list[str],
    source_spec_relpath: str,
    is_graph_refactor_run: bool,
    atomicity_errors: list[str],
) -> tuple[str, list[str]]:
    """Classify the semantic scope of an accepted canonical spec change."""
    review_reasons: list[str] = []
    foreign_spec_changes = [path for path in changed_spec_files if path != source_spec_relpath]
    if foreign_spec_changes:
        review_reasons.append("run changed additional spec files beyond the selected source node")

    if any(path_matches_prefix(path, IMMUTABLE_DIFF_PREFIXES) for path in diff_paths):
        review_reasons.append("run attempted to modify immutable spec identity fields")
        return REFINEMENT_CLASS_CONSTITUTIONAL, review_reasons

    if any(path_matches_prefix(path, CONSTITUTIONAL_DIFF_PREFIXES) for path in diff_paths):
        review_reasons.append("run changed governance-sensitive specification sections")
        return REFINEMENT_CLASS_CONSTITUTIONAL, review_reasons

    if is_seed_like_spec(node_data):
        if atomicity_errors:
            review_reasons.append("atomicity gate still requires follow-up decomposition work")
            return REFINEMENT_CLASS_GRAPH_REFACTOR, review_reasons
        return REFINEMENT_CLASS_LOCAL, review_reasons

    if is_graph_refactor_run:
        review_reasons.append("run executed in explicit graph_refactor mode")

    if any(path_matches_prefix(path, GRAPH_REFACTOR_DIFF_PREFIXES) for path in diff_paths):
        review_reasons.append("run changed graph structure or spec contract paths")

    if atomicity_errors:
        review_reasons.append("atomicity gate still requires follow-up decomposition work")

    if review_reasons:
        return REFINEMENT_CLASS_GRAPH_REFACTOR, review_reasons
    return REFINEMENT_CLASS_LOCAL, review_reasons


def parse_mutation_budget(budget_text: str) -> tuple[str, ...]:
    """Parse a comma-separated mutation budget into canonical class names."""
    if not budget_text.strip():
        return ()
    items = [item.strip() for item in budget_text.split(",")]
    normalized = tuple(item for item in items if item)
    unknown = sorted(set(normalized) - KNOWN_MUTATION_CLASSES)
    if unknown:
        raise ValueError(
            "Unknown mutation class(es): "
            + ", ".join(unknown)
            + ". Known classes: "
            + ", ".join(sorted(KNOWN_MUTATION_CLASSES))
        )
    return tuple(dict.fromkeys(normalized))


def parse_run_authority(authority_text: str) -> tuple[str, ...]:
    """Parse a comma-separated run-authority grant list."""
    if not authority_text.strip():
        return ()
    items = [item.strip() for item in authority_text.split(",")]
    normalized = tuple(item for item in items if item)
    unknown = sorted(set(normalized) - KNOWN_RUN_AUTHORITIES)
    if unknown:
        raise ValueError(
            "Unknown run authority grant(s): "
            + ", ".join(unknown)
            + ". Known run authority grants: "
            + ", ".join(sorted(KNOWN_RUN_AUTHORITIES))
        )
    return tuple(dict.fromkeys(normalized))


def component_requiredness(cardinality: str) -> str:
    normalized = cardinality.strip().lower()
    optional_markers = ("optional", "zero or one", "0 or 1", "zero-to-one")
    if any(marker in normalized for marker in optional_markers):
        return MUTATION_CLASS_SCHEMA_OPTIONAL_ADDITION
    required_markers = (
        "exactly 1",
        "exactly one",
        "at least 1",
        "at least one",
        "one or more",
        "1 or more",
    )
    if any(marker in normalized for marker in required_markers):
        return MUTATION_CLASS_SCHEMA_REQUIRED_ADDITION
    return MUTATION_CLASS_SCHEMA_REQUIRED_ADDITION


def collect_mutation_classes(
    *,
    before_snapshot: dict[str, Any],
    after_snapshot: dict[str, Any],
    diff_paths: list[str],
) -> list[str]:
    """Classify high-impact mutation classes for deterministic review gating."""
    classes: set[str] = set()

    if diff_paths:
        classes.add(MUTATION_CLASS_POLICY_TEXT)

    before_terms = (
        before_snapshot.get("specification", {}).get("terminology", {})
        if isinstance(before_snapshot.get("specification"), dict)
        else {}
    )
    after_terms = (
        after_snapshot.get("specification", {}).get("terminology", {})
        if isinstance(after_snapshot.get("specification"), dict)
        else {}
    )

    if isinstance(before_terms, dict) and isinstance(after_terms, dict):
        for term_name, after_term in after_terms.items():
            if not isinstance(after_term, dict):
                continue
            before_term = before_terms.get(term_name)
            if not isinstance(before_term, dict):
                before_term = {}
            before_components = {
                str(component.get("component", "")).strip(): component
                for component in before_term.get("required_components", [])
                if isinstance(component, dict) and str(component.get("component", "")).strip()
            }
            after_components = {
                str(component.get("component", "")).strip(): component
                for component in after_term.get("required_components", [])
                if isinstance(component, dict) and str(component.get("component", "")).strip()
            }
            for component_name, component_data in after_components.items():
                if component_name in before_components:
                    continue
                cardinality = str(component_data.get("cardinality", ""))
                classes.add(component_requiredness(cardinality))

    return sorted(classes)


def validate_refinement_acceptance(
    *,
    node: SpecNode,
    before_data: dict[str, Any],
    after_data: dict[str, Any],
    changed_files: list[str],
    is_graph_refactor_run: bool,
    output_errors: list[str],
    allowed_path_errors: list[str],
    reconciliation_errors: list[str],
    transition_errors: list[str],
    atomicity_errors: list[str],
    mutation_budget: tuple[str, ...] = (),
) -> dict[str, Any]:
    """Deterministically classify whether a refinement may be accepted as valid.

    This validator is intentionally narrower than "good writing" judgment. It
    answers only whether the run produced a canonical spec change that is valid
    under the current structural contract, and whether that change can be
    treated as a bounded local refinement or still requires explicit review.
    """
    before_snapshot = canonical_spec_snapshot(before_data)
    after_snapshot = canonical_spec_snapshot(after_data)
    diff_paths = collect_changed_paths(before_snapshot, after_snapshot)
    mutation_classes = collect_mutation_classes(
        before_snapshot=before_snapshot,
        after_snapshot=after_snapshot,
        diff_paths=diff_paths,
    )
    budget_exceeded_classes = sorted(set(mutation_classes) - set(mutation_budget))
    if not mutation_budget:
        budget_exceeded_classes = []

    try:
        source_spec_relpath = node.path.relative_to(ROOT).as_posix()
    except ValueError:
        source_spec_relpath = node.path.as_posix()
    changed_spec_files = sorted(path for path in changed_files if is_spec_node_path(path))
    hard_errors = (
        list(output_errors)
        + list(allowed_path_errors)
        + list(reconciliation_errors)
        + list(transition_errors)
    )
    change_class, review_reasons = classify_refinement_change(
        node_data=after_snapshot,
        diff_paths=diff_paths,
        changed_spec_files=changed_spec_files,
        source_spec_relpath=source_spec_relpath,
        is_graph_refactor_run=is_graph_refactor_run,
        atomicity_errors=atomicity_errors,
    )

    errors: list[str] = []
    warnings: list[str] = []
    decision = REFINEMENT_ACCEPT_DECISION_APPROVE

    if hard_errors:
        decision = REFINEMENT_ACCEPT_DECISION_REJECT
        errors.extend(hard_errors)
    elif not diff_paths:
        decision = REFINEMENT_ACCEPT_DECISION_REJECT
        errors.append("No canonical spec change detected after the refinement run")
    elif any(path_matches_prefix(path, IMMUTABLE_DIFF_PREFIXES) for path in diff_paths):
        decision = REFINEMENT_ACCEPT_DECISION_REJECT
        errors.append("Refinement run attempted to change immutable spec identity fields")
    elif budget_exceeded_classes:
        decision = REFINEMENT_ACCEPT_DECISION_REVIEW_REQUIRED
        review_reasons.append(
            "run exceeded requested mutation budget: " + ", ".join(budget_exceeded_classes)
        )
    elif change_class != REFINEMENT_CLASS_LOCAL:
        decision = REFINEMENT_ACCEPT_DECISION_REVIEW_REQUIRED

    if atomicity_errors:
        warnings.extend(atomicity_errors)

    return {
        "decision": decision,
        "change_class": change_class,
        "checks": {
            "content_changed": bool(diff_paths),
            "hard_validation": not hard_errors,
            "single_spec_scope": all(path == source_spec_relpath for path in changed_spec_files)
            if changed_spec_files
            else True,
            "constitutional_diff": change_class == REFINEMENT_CLASS_CONSTITUTIONAL,
            "graph_refactor_diff": change_class == REFINEMENT_CLASS_GRAPH_REFACTOR,
            "atomicity_clear": not atomicity_errors,
            "within_mutation_budget": not budget_exceeded_classes,
        },
        "diff_paths": diff_paths,
        "mutation_classes": mutation_classes,
        "mutation_budget": list(mutation_budget),
        "budget_exceeded_classes": budget_exceeded_classes,
        "changed_spec_files": changed_spec_files,
        "review_reasons": review_reasons,
        "errors": errors,
        "warnings": warnings,
    }


def is_spec_node_path(rel_path: str) -> bool:
    path = PurePosixPath(rel_path)
    return path.match("specs/nodes/*.yaml") or path.match("specs/nodes/*.yml")


def changed_spec_nodes(
    *,
    changed_files: list[str],
    worktree_specs: list[SpecNode],
    worktree_path: Path,
) -> list[SpecNode]:
    changed_paths = {
        (worktree_path / rel_path).resolve()
        for rel_path in changed_files
        if is_spec_node_path(rel_path)
    }
    return [spec for spec in worktree_specs if spec.path.resolve() in changed_paths]


def specs_requiring_validation(
    *,
    source_node_id: str,
    changed_files: list[str],
    worktree_specs: list[SpecNode],
    worktree_path: Path,
) -> list[SpecNode]:
    selected: dict[str, SpecNode] = {
        spec.id: spec
        for spec in changed_spec_nodes(
            changed_files=changed_files,
            worktree_specs=worktree_specs,
            worktree_path=worktree_path,
        )
        if spec.id
    }
    for spec in worktree_specs:
        if spec.id == source_node_id:
            selected[spec.id] = spec
            break
    return list(selected.values())


def validate_changed_spec_nodes(
    *,
    source_node_id: str,
    changed_files: list[str],
    worktree_specs: list[SpecNode],
    worktree_path: Path,
) -> list[str]:
    errors: list[str] = []
    for spec in specs_requiring_validation(
        source_node_id=source_node_id,
        changed_files=changed_files,
        worktree_specs=worktree_specs,
        worktree_path=worktree_path,
    ):
        status_errors = validate_status_format(spec.data)
        relation_errors = validate_relation_semantics(spec.data)
        acceptance_errors: list[str] = []
        requires_acceptance_evidence = spec.id == source_node_id or spec.status not in {
            "idea",
            "stub",
            "outlined",
        }
        if requires_acceptance_evidence:
            acceptance_errors = validate_acceptance_evidence(spec.data)
            if not acceptance_errors:
                acceptance_errors.extend(validate_acceptance_evidence_semantics(spec.data))
        output_errors = validate_outputs(spec, base_dir=worktree_path)
        rel_path = spec.path.relative_to(worktree_path).as_posix()
        errors.extend(f"{rel_path}: {error}" for error in status_errors)
        errors.extend(f"{rel_path}: {error}" for error in relation_errors)
        errors.extend(f"{rel_path}: {error}" for error in acceptance_errors)
        errors.extend(output_errors)
    return errors


def validate_changed_spec_atomicity(
    *,
    source_node_id: str,
    changed_files: list[str],
    worktree_specs: list[SpecNode],
    worktree_path: Path,
) -> list[str]:
    errors: list[str] = []
    for spec in specs_requiring_validation(
        source_node_id=source_node_id,
        changed_files=changed_files,
        worktree_specs=worktree_specs,
        worktree_path=worktree_path,
    ):
        rel_path = spec.path.relative_to(worktree_path).as_posix()
        errors.extend(f"{rel_path}: {error}" for error in validate_atomicity(spec))
    return errors


def validate_linkage_semantics(
    *,
    source_node: SpecNode,
    reconciled_node: SpecNode,
    index: dict[str, SpecNode],
) -> list[str]:
    errors: list[str] = []
    proposed_status = STATUS_PROGRESSION.get(source_node.status)
    if proposed_status != "linked":
        return errors
    if not semantic_dependencies_resolved(reconciled_node, index):
        missing = [dep_id for dep_id in reconciled_node.depends_on if dep_id not in index]
        errors.append(
            "Cannot advance to linked: missing declared dependency nodes "
            + ", ".join(sorted(missing))
        )
        return errors

    for dep_id in reconciled_node.depends_on:
        dep = index.get(dep_id)
        if dep is None:
            continue
        refines = dep.data.get("refines", [])
        if not isinstance(refines, list) or source_node.id not in {str(item) for item in refines}:
            errors.append(
                f"Cannot advance to linked: dependency {dep_id} must declare "
                f"refines: [{source_node.id}] to make the refinement chain explicit"
            )
    return errors


def reconcile_graph(
    *,
    source_node: SpecNode,
    worktree_path: Path,
    changed_files: list[str],
) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    try:
        worktree_specs = load_specs_from_dir(worktree_path / "specs" / "nodes")
    except Exception as exc:
        return (
            {
                "worktree_spec_count": 0,
                "changed_spec_ids": [],
                "semantic_dependencies_resolved": False,
                "work_dependencies_ready": False,
                "cycles": [],
            },
            [f"Failed to load worktree specs: {exc}"],
        )

    index = index_specs(worktree_specs)
    reconciled_node = index.get(source_node.id)
    if reconciled_node is None:
        return (
            {
                "worktree_spec_count": len(worktree_specs),
                "changed_spec_ids": [],
                "semantic_dependencies_resolved": False,
                "work_dependencies_ready": False,
                "cycles": [],
            },
            [f"Reconciled node missing from worktree graph: {source_node.id}"],
        )

    changed_nodes = changed_spec_nodes(
        changed_files=changed_files,
        worktree_specs=worktree_specs,
        worktree_path=worktree_path,
    )
    errors.extend(
        validate_changed_spec_nodes(
            source_node_id=source_node.id,
            changed_files=changed_files,
            worktree_specs=worktree_specs,
            worktree_path=worktree_path,
        )
    )

    cycles = detect_cycles(worktree_specs)
    if cycles:
        for cycle in cycles:
            errors.append("Dependency cycle detected in worktree graph: " + " -> ".join(cycle))

    errors.extend(
        validate_linkage_semantics(
            source_node=source_node,
            reconciled_node=reconciled_node,
            index=index,
        )
    )

    result = {
        "worktree_spec_count": len(worktree_specs),
        "changed_spec_ids": [spec.id for spec in changed_nodes if spec.id],
        "semantic_dependencies_resolved": semantic_dependencies_resolved(reconciled_node, index),
        "work_dependencies_ready": work_dependencies_ready(reconciled_node, index),
        "cycles": cycles,
    }
    return result, errors


def observe_graph_health(
    *,
    source_node: SpecNode,
    worktree_specs: list[SpecNode],
    reconciliation: dict[str, Any],
    atomicity_errors: list[str],
    outcome: str,
) -> dict[str, Any]:
    """Derive graph-health observations and signals for the current run.

    This is intentionally diagnostic, not canonical. The returned payload is
    written into run artifacts and then projected into refactor/proposal queues.
    It must not write back into spec nodes by itself.
    """
    index = index_specs(worktree_specs)
    observations: list[dict[str, Any]] = []
    signals: list[str] = []
    recommended_actions: list[str] = []

    reconciled_node = index.get(source_node.id)
    if reconciled_node is not None:
        local_atomicity = validate_atomicity(reconciled_node)
        if local_atomicity:
            live_child_ids = [
                child.id
                for child in active_refining_child_specs(reconciled_node, worktree_specs)
                if child.id
            ]
            accepted_child_ids = accepted_child_spec_ids(reconciled_node, worktree_specs)
            observations.append(
                {
                    "kind": "oversized_spec",
                    "spec_id": source_node.id,
                    "details": local_atomicity,
                }
            )
            if live_child_ids:
                observations.append(
                    {
                        "kind": RETROSPECTIVE_REFACTOR_SIGNAL,
                        "spec_id": source_node.id,
                        "details": {
                            "atomicity": local_atomicity,
                            "live_child_ids": live_child_ids,
                            "accepted_child_ids": accepted_child_ids,
                        },
                    }
                )
                signals.append(RETROSPECTIVE_REFACTOR_SIGNAL)
                recommended_actions.append("propose_retrospective_refactor")
            else:
                signals.append("oversized_spec")
                recommended_actions.append("split_or_narrow_spec")

        missing_dependencies = [
            dep_id for dep_id in reconciled_node.depends_on if dep_id not in index
        ]
        if missing_dependencies:
            observations.append(
                {
                    "kind": "missing_dependency_target",
                    "spec_id": source_node.id,
                    "details": missing_dependencies,
                }
            )
            signals.append("missing_dependency_target")
            recommended_actions.append("repair_canonical_dependencies")

        if source_node.data.get("last_outcome") == "split_required" and outcome == "split_required":
            observations.append(
                {
                    "kind": "repeated_split_required_candidate",
                    "spec_id": source_node.id,
                    "details": (
                        "Consecutive split_required outcomes suggest persistent non-atomic scope."
                    ),
                }
            )
            signals.append("repeated_split_required_candidate")
            recommended_actions.append("schedule_decomposition_pass")

        if (
            outcome in {"retry", "blocked", "split_required"}
            and reconciled_node.maturity <= source_node.maturity
        ):
            observations.append(
                {
                    "kind": "stalled_maturity_candidate",
                    "spec_id": source_node.id,
                    "details": {
                        "before": source_node.maturity,
                        "after": reconciled_node.maturity,
                        "outcome": outcome,
                    },
                }
            )
            signals.append("stalled_maturity_candidate")
            recommended_actions.append("review_refinement_strategy")

        if reconciled_node.status in {"specified", "linked"} and not reconciliation.get(
            "semantic_dependencies_resolved", True
        ):
            observations.append(
                {
                    "kind": "weak_structural_linkage_candidate",
                    "spec_id": source_node.id,
                    "details": "Declared dependency chain is not semantically resolved.",
                }
            )
            signals.append("weak_structural_linkage_candidate")
            recommended_actions.append("repair_refinement_chain")

        metrics = subtree_shape_metrics(reconciled_node, worktree_specs)
        if metrics["descendant_count"] > 0:
            role_legibility_profiles = subtree_role_legibility_profiles(
                reconciled_node,
                worktree_specs,
            )
            shape_details = {
                "longest_one_child_chain": metrics["longest_one_child_chain"],
                "max_depth": metrics["max_depth"],
                "max_width": metrics["max_width"],
                "single_child_internal_ratio": round(
                    float(metrics["single_child_internal_ratio"]), 3
                ),
                "median_acceptance_count": metrics["median_acceptance_count"],
                "delegation_marker_ratio": round(float(metrics["delegation_marker_ratio"]), 3),
                "execution_marker_ratio": round(float(metrics["execution_marker_ratio"]), 3),
                "direct_child_count": metrics["direct_child_count"],
                "subtree_node_count": metrics["subtree_node_count"],
            }
            shape_pressure = False
            fan_out_profile = fan_out_legibility_profile(reconciled_node, worktree_specs)
            shape_details.update(fan_out_profile)
            if (
                fan_out_profile["classification"] == "healthy_multi_child_aggregate"
                and metrics["direct_child_count"] >= REFINEMENT_FAN_OUT_DIRECT_CHILDREN_THRESHOLD
            ):
                observations.append(
                    {
                        "kind": "healthy_multi_child_aggregate",
                        "spec_id": source_node.id,
                        "details": {
                            **shape_details,
                            "summary": (
                                "The node has many direct children, but they still read as a "
                                "coherent aggregate rather than as a broad hub."
                            ),
                        },
                    }
                )
            elif fan_out_profile["classification"] == "broad_hub_missing_cluster":
                observations.append(
                    {
                        "kind": "refinement_fan_out_pressure",
                        "spec_id": source_node.id,
                        "details": {
                            **shape_details,
                            "summary": (
                                "The node is accumulating enough direct child breadth that "
                                "intermediate grouping should be reviewed."
                            ),
                        },
                    }
                )
                signals.append("refinement_fan_out_pressure")
                recommended_actions.append("regroup_under_intermediate_cluster")
                recommended_actions.append("introduce_semantic_cluster_parent")
                shape_pressure = True

            if metrics["longest_one_child_chain"] >= SUBTREE_SHAPE_ONE_CHILD_CHAIN_THRESHOLD:
                observations.append(
                    {
                        "kind": "serial_refinement_ladder",
                        "spec_id": source_node.id,
                        "details": {
                            **shape_details,
                            "summary": (
                                "A long one-child refines chain is forming in the same bounded "
                                "subtree."
                            ),
                        },
                    }
                )
                signals.append("serial_refinement_ladder")
                recommended_actions.append("rebalance_subtree_shape")
                shape_pressure = True

            if (
                metrics["max_depth"] >= SUBTREE_SHAPE_ONE_CHILD_CHAIN_THRESHOLD
                and metrics["max_width"] <= 2
                and metrics["single_child_internal_ratio"] >= SUBTREE_SHAPE_MIN_SINGLE_CHILD_RATIO
            ):
                observations.append(
                    {
                        "kind": "depth_without_breadth",
                        "spec_id": source_node.id,
                        "details": {
                            **shape_details,
                            "summary": "Subtree depth is growing faster than meaningful breadth.",
                        },
                    }
                )
                signals.append("depth_without_breadth")
                recommended_actions.append("rebalance_subtree_shape")
                shape_pressure = True

            if (
                metrics["longest_one_child_chain"] >= SUBTREE_SHAPE_ONE_CHILD_CHAIN_THRESHOLD
                and metrics["median_acceptance_count"] <= OVER_ATOMIZED_ACCEPTANCE_MAX
                and metrics["single_child_internal_ratio"] >= SUBTREE_SHAPE_MIN_SINGLE_CHILD_RATIO
            ):
                observations.append(
                    {
                        "kind": "over_atomized_subtree",
                        "spec_id": source_node.id,
                        "details": {
                            **shape_details,
                            "summary": (
                                "The subtree is becoming deep while each node carries only a very "
                                "small payload."
                            ),
                        },
                    }
                )
                signals.append("over_atomized_subtree")
                recommended_actions.append("rebalance_subtree_shape")
                shape_pressure = True

            if (
                metrics["longest_one_child_chain"] >= SUBTREE_SHAPE_ONE_CHILD_CHAIN_THRESHOLD
                and metrics["max_width"] == 1
            ):
                observations.append(
                    {
                        "kind": "missing_aggregate_node",
                        "spec_id": source_node.id,
                        "details": {
                            **shape_details,
                            "summary": (
                                "The subtree reads like a serial ladder and lacks an aggregate "
                                "grouping node."
                            ),
                        },
                    }
                )
                signals.append("missing_aggregate_node")
                recommended_actions.append("materialize_aggregate_node")
                shape_pressure = True

            if (
                metrics["longest_one_child_chain"] >= SUBTREE_SHAPE_ONE_CHILD_CHAIN_THRESHOLD
                and metrics["delegation_marker_ratio"] >= TEXT_MARKER_RATIO_THRESHOLD
            ):
                observations.append(
                    {
                        "kind": "delegation_only_chain",
                        "spec_id": source_node.id,
                        "details": {
                            **shape_details,
                            "summary": (
                                "Consecutive nodes mostly restate delegation or boundary language."
                            ),
                        },
                    }
                )
                signals.append("delegation_only_chain")
                recommended_actions.append("compress_delegation_chain")
                shape_pressure = True

            role_obscured_profiles = [
                profile for profile in role_legibility_profiles if profile["role_obscured"]
            ]
            if role_obscured_profiles:
                observations.append(
                    {
                        "kind": "role_obscured_node",
                        "spec_id": source_node.id,
                        "details": {
                            **shape_details,
                            "affected_count": len(role_obscured_profiles),
                            "affected_nodes": role_obscured_profiles,
                            "summary": (
                                "Some nodes in the subtree read more like decomposition "
                                "bookkeeping than like clear system roles."
                            ),
                        },
                    }
                )
                signals.append("role_obscured_node")
                recommended_actions.append("rewrite_node_role_boundary")
                shape_pressure = True

            bookkeeping_only_profiles = [
                profile for profile in role_legibility_profiles if profile["bookkeeping_only"]
            ]
            if bookkeeping_only_profiles:
                observations.append(
                    {
                        "kind": "bookkeeping_only_node",
                        "spec_id": source_node.id,
                        "details": {
                            **shape_details,
                            "affected_count": len(bookkeeping_only_profiles),
                            "affected_nodes": bookkeeping_only_profiles,
                            "summary": (
                                "Some nodes mostly restate ownership or edge-placement "
                                "bookkeeping without adding a clearer graph-native role."
                            ),
                        },
                    }
                )
                signals.append("bookkeeping_only_node")
                recommended_actions.append("merge_bookkeeping_slice")
                shape_pressure = True

            if (
                shape_pressure
                and outcome == "split_required"
                and metrics["execution_marker_ratio"] >= TEXT_MARKER_RATIO_THRESHOLD
            ):
                observations.append(
                    {
                        "kind": "lower_boundary_handoff_candidate",
                        "spec_id": source_node.id,
                        "details": {
                            **shape_details,
                            "summary": (
                                "Shape pressure now coexists with execution-facing unresolved "
                                "detail."
                            ),
                        },
                    }
                )
                signals.append("lower_boundary_handoff_candidate")
                recommended_actions.append("review_lower_boundary_handoff")

            if (
                outcome == "split_required"
                and metrics["longest_one_child_chain"] >= GRAPH_LAYER_EXHAUSTED_CHAIN_THRESHOLD
                and metrics["max_width"] == 1
                and metrics["execution_marker_ratio"] >= TEXT_MARKER_RATIO_THRESHOLD
            ):
                observations.append(
                    {
                        "kind": "graph_layer_exhausted_for_subtree",
                        "spec_id": source_node.id,
                        "details": {
                            **shape_details,
                            "summary": (
                                "Further canonical decomposition is unlikely to restore readable "
                                "grouping in this region."
                            ),
                        },
                    }
                )
                signals.append("graph_layer_exhausted_for_subtree")
                recommended_actions.append("review_lower_boundary_handoff")

            handoff_profile = techspec_handoff_profile(metrics=metrics, signals=signals)
            if handoff_profile["candidate"]:
                observations.append(
                    {
                        "kind": TECHSPEC_HANDOFF_PRIMARY_SIGNAL,
                        "spec_id": source_node.id,
                        "details": {
                            **shape_details,
                            **handoff_profile,
                            "summary": (
                                "The subtree appears semantically saturated for canonical "
                                "SpecGraph and is ready for TechSpec-oriented handoff."
                            ),
                        },
                    }
                )
                signals.append(TECHSPEC_HANDOFF_PRIMARY_SIGNAL)
                recommended_actions.append(TECHSPEC_HANDOFF_RECOMMENDED_ACTION)

    return {
        "source_spec_id": source_node.id,
        "observations": observations,
        "signals": sorted(set(signals)),
        "recommended_actions": sorted(set(recommended_actions)),
    }


def derive_accepted_graph_health(
    *,
    source_node: SpecNode,
    current_specs: list[SpecNode],
    outcome: str | None = None,
) -> dict[str, Any]:
    index = index_specs(current_specs)
    reconciled_node = index.get(source_node.id)
    if reconciled_node is None:
        return empty_graph_health(source_node.id)
    accepted_outcome = outcome or graph_health_outcome_basis(reconciled_node)
    return observe_graph_health(
        source_node=source_node,
        worktree_specs=current_specs,
        reconciliation={
            "semantic_dependencies_resolved": semantic_dependencies_resolved(
                reconciled_node, index
            ),
            "work_dependencies_ready": work_dependencies_ready(reconciled_node, index),
        },
        atomicity_errors=validate_atomicity(reconciled_node),
        outcome=accepted_outcome,
    )


def empty_graph_health(source_spec_id: str) -> dict[str, Any]:
    return {
        "source_spec_id": source_spec_id,
        "observations": [],
        "signals": [],
        "recommended_actions": [],
    }


def graph_health_outcome_basis(node: SpecNode) -> str:
    last_outcome = str(node.data.get("last_outcome", "")).strip()
    if last_outcome:
        return last_outcome
    gate_state = node.gate_state
    if gate_state in {"split_required", "blocked"}:
        return gate_state
    if gate_state == "retry_pending":
        return "retry"
    return "done"


def inspect_canonical_graph_health(*, node: SpecNode, specs: list[SpecNode]) -> dict[str, Any]:
    index = index_specs(specs)
    outcome = graph_health_outcome_basis(node)
    graph_health = observe_graph_health(
        source_node=node,
        worktree_specs=specs,
        reconciliation={
            "semantic_dependencies_resolved": semantic_dependencies_resolved(node, index),
        },
        atomicity_errors=[],
        outcome=outcome,
    )
    active_subtree_ids = [spec.id for spec in active_subtree_nodes(node, specs) if spec.id]
    raw_subtree_ids = [spec.id for spec in subtree_nodes(node, specs) if spec.id]
    historical_descendant_ids = [
        spec_id
        for spec_id in raw_subtree_ids
        if spec_id and spec_id != node.id and spec_id not in set(active_subtree_ids)
    ]
    return {
        "source_spec_id": node.id,
        "source_title": node.title,
        "diagnostic_outcome": outcome,
        "subtree_spec_ids": active_subtree_ids,
        "historical_descendant_ids": historical_descendant_ids,
        "graph_health": graph_health,
    }


def graph_health_overlay_path() -> Path:
    return RUNS_DIR / GRAPH_HEALTH_OVERLAY_FILENAME


def graph_health_trends_path() -> Path:
    return RUNS_DIR / GRAPH_HEALTH_TRENDS_FILENAME


def build_graph_health_overlay(specs: list[SpecNode]) -> dict[str, Any]:
    signal_groups: dict[str, list[str]] = {}
    action_groups: dict[str, list[str]] = {}
    named_filters = {
        "oversized_or_atomicity_pressure": [],
        "weakly_linked_regions": [],
        "shape_pressure": [],
        "role_legibility_pressure": [],
        "clustering_pressure": [],
        "handoff_boundary_pressure": [],
        "techspec_ready_regions": [],
        "gated_specs": [],
    }
    entries: list[dict[str, Any]] = []
    affected_spec_ids: list[str] = []

    for spec in specs:
        snapshot = inspect_canonical_graph_health(node=spec, specs=specs)
        graph_health = snapshot.get("graph_health", {})
        if not isinstance(graph_health, dict):
            continue
        signals = sorted(
            {str(item).strip() for item in graph_health.get("signals", []) if str(item).strip()}
        )
        recommended_actions = sorted(
            {
                str(item).strip()
                for item in graph_health.get("recommended_actions", [])
                if str(item).strip()
            }
        )
        gate_state = str(spec.gate_state or "none").strip() or "none"
        if not signals and gate_state == "none":
            continue

        affected_spec_ids.append(spec.id)
        for signal in signals:
            signal_groups.setdefault(signal, []).append(spec.id)
        for action in recommended_actions:
            action_groups.setdefault(action, []).append(spec.id)

        if any(
            signal in {"oversized_spec", "repeated_split_required_candidate"} for signal in signals
        ):
            named_filters["oversized_or_atomicity_pressure"].append(spec.id)
        if any(
            signal in {"weak_structural_linkage_candidate", "missing_dependency_target"}
            for signal in signals
        ):
            named_filters["weakly_linked_regions"].append(spec.id)
        if any(signal in SUBTREE_SHAPE_SIGNALS for signal in signals):
            named_filters["shape_pressure"].append(spec.id)
        if any(signal in {"role_obscured_node", "bookkeeping_only_node"} for signal in signals):
            named_filters["role_legibility_pressure"].append(spec.id)
        if any(
            signal in {"refinement_fan_out_pressure", "missing_aggregate_node"}
            for signal in signals
        ):
            named_filters["clustering_pressure"].append(spec.id)
        if any(signal in LOWER_BOUNDARY_HANDOFF_SIGNALS for signal in signals):
            named_filters["handoff_boundary_pressure"].append(spec.id)
        if TECHSPEC_HANDOFF_PRIMARY_SIGNAL in signals:
            named_filters["techspec_ready_regions"].append(spec.id)
        if gate_state != "none":
            named_filters["gated_specs"].append(spec.id)

        subtree_spec_ids = list(snapshot.get("subtree_spec_ids", []))
        historical_descendant_ids = list(snapshot.get("historical_descendant_ids", []))
        entries.append(
            {
                "spec_id": spec.id,
                "title": spec.title,
                "gate_state": gate_state,
                "diagnostic_outcome": str(snapshot.get("diagnostic_outcome", "")).strip(),
                "subtree_spec_ids": subtree_spec_ids,
                "historical_descendant_ids": historical_descendant_ids,
                "signals": signals,
                "recommended_actions": recommended_actions,
                "problem_score": len(signals) + (1 if gate_state != "none" else 0),
                "active_subtree_size": len(subtree_spec_ids),
                "historical_descendant_count": len(historical_descendant_ids),
            }
        )

    hotspot_regions = sorted(
        entries,
        key=lambda item: (
            -int(item.get("problem_score", 0)),
            -int(item.get("active_subtree_size", 0)),
            str(item.get("spec_id", "")),
        ),
    )

    return {
        "artifact_kind": "graph_health_overlay",
        "schema_version": 1,
        "generated_at": utc_now_iso(),
        "source": {
            "truth_basis": "accepted_canonical",
            "spec_count": len(specs),
            "affected_spec_count": len(entries),
        },
        "entries": entries,
        "viewer_projection": {
            "signals": {key: sorted(value) for key, value in sorted(signal_groups.items())},
            "recommended_actions": {
                key: sorted(value) for key, value in sorted(action_groups.items())
            },
            "named_filters": {key: sorted(value) for key, value in sorted(named_filters.items())},
            "affected_spec_ids": sorted(affected_spec_ids),
        },
        "hotspot_regions": hotspot_regions,
    }


def write_graph_health_overlay(overlay: dict[str, Any]) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = graph_health_overlay_path()
    with artifact_lock(path):
        atomic_write_json(path, overlay)
    return path


def graph_health_event_timestamp(payload: dict[str, Any], path: Path) -> dt.datetime | None:
    timestamp = parse_iso_datetime(payload.get("timestamp_utc", ""))
    if timestamp is not None:
        return timestamp
    run_id = str(payload.get("run_id", "")).strip() or path.stem
    prefix = run_id.split("-", 1)[0]
    try:
        return dt.datetime.strptime(prefix, "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.timezone.utc)
    except ValueError:
        pass
    try:
        return dt.datetime.fromtimestamp(path.stat().st_mtime, tz=dt.timezone.utc)
    except OSError:
        return None


def graph_health_surfaces_from_payload(payload: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    surfaces: list[tuple[str, dict[str, Any]]] = []
    primary = payload.get("graph_health")
    primary_basis = str(payload.get("graph_health_truth_basis", "")).strip() or "unknown"
    if isinstance(primary, dict):
        surfaces.append((primary_basis, primary))
    candidate = payload.get("candidate_graph_health")
    candidate_basis = str(payload.get("candidate_graph_health_truth_basis", "")).strip()
    if isinstance(candidate, dict):
        surfaces.append((candidate_basis or "review_candidate", candidate))
    return surfaces


def build_graph_health_trends(
    specs: list[SpecNode],
    *,
    overlay: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if overlay is None:
        overlay = build_graph_health_overlay(specs)

    current_signal_map = {
        str(entry.get("spec_id", "")).strip(): {
            str(signal).strip() for signal in entry.get("signals", []) if str(signal).strip()
        }
        for entry in overlay.get("entries", [])
        if isinstance(entry, dict)
    }
    spec_titles = {spec.id: spec.title for spec in specs if spec.id}
    spec_signal_runs: dict[tuple[str, str], dict[str, Any]] = {}
    signal_history: dict[str, dict[str, Any]] = {}
    observed_run_ids: set[str] = set()
    observed_timestamps: list[dt.datetime] = []

    for path in run_log_paths():
        payload = load_json_object(path)
        if not isinstance(payload, dict):
            continue
        run_id = str(payload.get("run_id", "")).strip() or path.stem
        timestamp = graph_health_event_timestamp(payload, path)
        surfaces = graph_health_surfaces_from_payload(payload)
        if not surfaces:
            continue

        for truth_basis, graph_health in surfaces:
            spec_id = str(graph_health.get("source_spec_id", "")).strip()
            if not spec_id:
                continue
            raw_signals = graph_health.get("signals", [])
            if not isinstance(raw_signals, list):
                continue
            signals = {str(item).strip() for item in raw_signals if str(item).strip()}
            if not signals:
                continue

            observed_run_ids.add(run_id)
            if timestamp is not None:
                observed_timestamps.append(timestamp)

            for signal in signals:
                spec_key = (spec_id, signal)
                bucket = spec_signal_runs.setdefault(
                    spec_key,
                    {
                        "spec_id": spec_id,
                        "title": spec_titles.get(spec_id, str(payload.get("title", "")).strip()),
                        "signal": signal,
                        "runs": {},
                    },
                )
                run_bucket = bucket["runs"].setdefault(
                    run_id,
                    {
                        "timestamp": timestamp,
                        "truth_bases": set(),
                    },
                )
                if timestamp is not None and (
                    run_bucket["timestamp"] is None or timestamp > run_bucket["timestamp"]
                ):
                    run_bucket["timestamp"] = timestamp
                run_bucket["truth_bases"].add(truth_basis)

                signal_bucket = signal_history.setdefault(
                    signal,
                    {
                        "signal": signal,
                        "runs": set(),
                        "spec_ids": set(),
                    },
                )
                signal_bucket["runs"].add(run_id)
                signal_bucket["spec_ids"].add(spec_id)

    def _iso_or_empty(value: dt.datetime | None) -> str:
        if value is None:
            return ""
        return value.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")

    entries: list[dict[str, Any]] = []
    recurring_signal_groups: dict[str, list[str]] = {}
    named_filters = {
        "persistent_recurrence": [],
        "historical_recurrence": [],
        "repeated_split_pressure": [],
        "repeated_weak_linkage": [],
        "repeated_shape_pressure": [],
        "repeated_handoff_pressure": [],
    }

    for (_spec_id, _signal), bucket in spec_signal_runs.items():
        runs = bucket["runs"]
        sorted_runs = sorted(
            runs.items(),
            key=lambda item: (
                item[1]["timestamp"] is None,
                item[1]["timestamp"] or dt.datetime.min.replace(tzinfo=dt.timezone.utc),
                item[0],
            ),
        )
        occurrence_count = len(sorted_runs)
        current_signals = current_signal_map.get(bucket["spec_id"], set())
        currently_active = bucket["signal"] in current_signals
        if currently_active and occurrence_count >= 2:
            trend_status = "persistent"
            named_filters["persistent_recurrence"].append(bucket["spec_id"])
        elif occurrence_count >= 2:
            trend_status = "historical_recurrence"
            named_filters["historical_recurrence"].append(bucket["spec_id"])
        else:
            trend_status = "isolated"

        if occurrence_count >= 2:
            recurring_signal_groups.setdefault(bucket["signal"], []).append(bucket["spec_id"])
            if bucket["signal"] in {"oversized_spec", "repeated_split_required_candidate"}:
                named_filters["repeated_split_pressure"].append(bucket["spec_id"])
            if bucket["signal"] in {
                "weak_structural_linkage_candidate",
                "missing_dependency_target",
            }:
                named_filters["repeated_weak_linkage"].append(bucket["spec_id"])
            if bucket["signal"] in SUBTREE_SHAPE_SIGNALS:
                named_filters["repeated_shape_pressure"].append(bucket["spec_id"])
            if bucket["signal"] in LOWER_BOUNDARY_HANDOFF_SIGNALS:
                named_filters["repeated_handoff_pressure"].append(bucket["spec_id"])

        first_seen = sorted_runs[0][1]["timestamp"] if sorted_runs else None
        last_seen = sorted_runs[-1][1]["timestamp"] if sorted_runs else None
        truth_bases = sorted(
            {
                basis
                for _run_id, run_data in sorted_runs
                for basis in run_data["truth_bases"]
                if str(basis).strip()
            }
        )
        entries.append(
            {
                "spec_id": bucket["spec_id"],
                "title": bucket["title"],
                "signal": bucket["signal"],
                "occurrence_count": occurrence_count,
                "trend_status": trend_status,
                "currently_active": currently_active,
                "first_seen_at": _iso_or_empty(first_seen),
                "last_seen_at": _iso_or_empty(last_seen),
                "run_ids": [run_id for run_id, _run_data in sorted_runs],
                "truth_bases": truth_bases,
            }
        )

    entries.sort(
        key=lambda item: (
            -int(item.get("occurrence_count", 0)),
            str(item.get("spec_id", "")),
            str(item.get("signal", "")),
        )
    )
    signal_summary = {
        signal: {
            "occurrence_count": len(data["runs"]),
            "spec_ids": sorted(data["spec_ids"]),
        }
        for signal, data in sorted(signal_history.items())
    }
    observed_timestamps = sorted(observed_timestamps)

    return {
        "artifact_kind": "graph_health_trends",
        "schema_version": 1,
        "generated_at": utc_now_iso(),
        "source_overlay_path": graph_health_overlay_path().relative_to(ROOT).as_posix(),
        "source_overlay_generated_at": overlay.get("generated_at"),
        "history_window": {
            "observed_run_count": len(observed_run_ids),
            "first_observed_at": _iso_or_empty(
                observed_timestamps[0] if observed_timestamps else None
            ),
            "last_observed_at": _iso_or_empty(
                observed_timestamps[-1] if observed_timestamps else None
            ),
        },
        "signal_summary": signal_summary,
        "entries": entries,
        "viewer_projection": {
            "recurring_signal_groups": {
                key: sorted(set(value)) for key, value in sorted(recurring_signal_groups.items())
            },
            "named_filters": {
                key: sorted(set(value)) for key, value in sorted(named_filters.items())
            },
        },
    }


def write_graph_health_trends(trends: dict[str, Any]) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = graph_health_trends_path()
    with artifact_lock(path):
        atomic_write_json(path, trends)
    return path


def classify_executor_environment(stderr: str) -> dict[str, Any]:
    """Classify runtime/environment issues from nested executor stderr.

    These signals are operational diagnostics about the child executor runtime,
    not graph-health findings about the current spec.
    """
    lines = [line.strip() for line in stderr.splitlines() if line.strip()]
    lowered = [line.lower() for line in lines]
    issues: list[dict[str, Any]] = []

    def add_issue(kind: str, summary: str, predicate: Callable[[str], bool]) -> None:
        evidence = [
            line
            for line, low in zip(lines, lowered)  # noqa: B905 - local runner uses Python 3.9
            if predicate(low)
        ]
        if evidence:
            issues.append(
                {
                    "kind": kind,
                    "summary": summary,
                    "evidence": evidence[:3],
                }
            )

    add_issue(
        "executor_timeout_failure",
        "Nested executor timed out before producing a bounded result.",
        lambda low: "supervisor timeout:" in low or "nested executor timed out after" in low,
    )
    add_issue(
        "transport_failure",
        "Nested executor could not reach or maintain a stable backend connection.",
        lambda low: any(
            fragment in low
            for fragment in (
                "failed to connect to websocket",
                "stream disconnected before completion",
                "error sending request for url",
                "failed to lookup address information",
                "unexpected status 401 unauthorized",
                "http error:",
            )
        ),
    )
    add_issue(
        "mcp_startup_failure",
        "Nested executor failed to start one or more MCP servers.",
        lambda low: (
            ("mcp startup:" in low and "failed:" in low)
            or (low.startswith("mcp:") and " failed:" in low)
            or "mcp client for" in low
        ),
    )
    add_issue(
        "state_runtime_failure",
        "Nested executor runtime state or migration setup failed.",
        lambda low: any(
            fragment in low
            for fragment in (
                "failed to open state db",
                "failed to initialize state runtime",
                "migration ",
                "state db discrepancy",
            )
        ),
    )
    add_issue(
        "sandbox_permission_failure",
        "Nested executor hit local permission or sandbox restrictions.",
        lambda low: "operation not permitted" in low or "permission denied" in low,
    )
    add_issue(
        "usage_limit_failure",
        "Nested executor was rejected by the provider because the current account "
        "hit a usage or quota limit.",
        lambda low: any(
            fragment in low
            for fragment in (
                "you've hit your usage limit",
                "purchase more credits",
                "upgrade to pro",
                "usage to purchase more credits",
            )
        ),
    )

    return {
        "issues": issues,
        "issue_kinds": [str(issue["kind"]) for issue in issues],
        "primary_failure": False,
    }


def is_primary_executor_environment_failure(
    *,
    executor_environment: dict[str, Any],
    returncode: int,
    changed_files: list[str],
    outcome: str,
) -> bool:
    return (
        bool(executor_environment.get("issues"))
        and returncode != 0
        and not changed_files
        and outcome != "done"
    )


def executor_environment_validation_errors(executor_environment: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for issue in executor_environment.get("issues", []):
        if not isinstance(issue, dict):
            continue
        summary = str(issue.get("summary", "")).strip() or "Executor environment failure"
        evidence = issue.get("evidence", [])
        if isinstance(evidence, list) and evidence:
            errors.append(f"{summary} Evidence: {evidence[0]}")
        else:
            errors.append(summary)
    return errors


def executor_environment_required_action(executor_environment: dict[str, Any]) -> str:
    issue_kinds = {
        str(kind).strip()
        for kind in executor_environment.get("issue_kinds", [])
        if str(kind).strip()
    }
    if "usage_limit_failure" in issue_kinds:
        return "wait for usage reset or add credits and rerun supervisor"
    return "repair executor environment and rerun supervisor"


def validate_requested_child_materialization(
    *,
    requested: bool,
    source_spec_relpath: str,
    changed_files: list[str],
    reserved_child_path: str = "",
) -> list[str]:
    """Require one additional spec node file when child materialization was requested."""
    if not requested:
        return []
    child_spec_changes = [
        path for path in changed_files if is_spec_node_path(path) and path != source_spec_relpath
    ]
    if not child_spec_changes:
        return [
            "Explicit child materialization was requested but no new child spec file was produced"
        ]
    if reserved_child_path and reserved_child_path not in child_spec_changes:
        return [
            "Explicit child materialization must use the reserved child spec path: "
            f"{reserved_child_path}"
        ]
    return []


def parse_executor_protocol(stdout: str, returncode: int) -> tuple[str, str, list[str]]:
    default_outcome = "done" if returncode == 0 else "escalate"

    outcome = default_outcome
    protocol_errors: list[str] = []
    outcome_match = re.search(r"^RUN_OUTCOME:\s*([a-z_]+)\s*$", stdout, flags=re.MULTILINE)
    if outcome_match:
        candidate = outcome_match.group(1).strip().lower()
        if candidate in ALLOWED_OUTCOMES:
            outcome = candidate
        else:
            outcome = "escalate"
            protocol_errors.append(
                f"Invalid executor machine protocol marker RUN_OUTCOME: {candidate}"
            )
    else:
        protocol_errors.append("Missing executor machine protocol marker RUN_OUTCOME")

    blocker = ""
    blocker_match = re.search(r"^BLOCKER:\s*(.+)\s*$", stdout, flags=re.MULTILINE)
    if blocker_match:
        blocker = blocker_match.group(1).strip()
        if blocker.lower() == "none":
            blocker = ""
    else:
        protocol_errors.append("Missing executor machine protocol marker BLOCKER")

    if protocol_errors and returncode == 0:
        outcome = "blocked"
        if not blocker:
            blocker = "executor machine protocol failure"

    return outcome, blocker, protocol_errors


def parse_outcome(stdout: str, returncode: int) -> tuple[str, str]:
    outcome, blocker, _protocol_errors = parse_executor_protocol(stdout, returncode)
    return outcome, blocker


def utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def utc_compact_timestamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def runtime_nonce() -> str:
    return secrets.token_hex(4)


def make_run_id(spec_id: str) -> str:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    for _attempt in range(RUNTIME_ID_COLLISION_RETRY_LIMIT):
        run_id = f"{utc_compact_timestamp()}-{spec_id}-{runtime_nonce()}"
        if not (RUNS_DIR / f"{run_id}.json").exists():
            return run_id
    raise RuntimeError(f"failed to allocate unique run_id for {spec_id}")


def write_run_log(run_id: str, payload: dict[str, Any]) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = RUNS_DIR / f"{run_id}.json"
    with artifact_lock(path):
        if path.exists():
            raise RuntimeError(f"run log already exists for run_id: {run_id}")
        atomic_write_json(path, payload)
    return path


def decision_inspector_dir_path() -> Path:
    return RUNS_DIR / "decision_inspector"


def decision_inspector_artifact_path(run_id: str) -> Path:
    return decision_inspector_dir_path() / f"{run_id}.json"


def write_decision_inspector_artifact(run_id: str, payload: dict[str, Any]) -> Path:
    path = decision_inspector_artifact_path(run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with artifact_lock(path):
        atomic_write_json(path, payload)
    return path


def refactor_queue_path() -> Path:
    return RUNS_DIR / "refactor_queue.json"


def proposal_queue_path() -> Path:
    return RUNS_DIR / "proposal_queue.json"


def proposals_dir_path() -> Path:
    return RUNS_DIR / "proposals"


def intent_layer_nodes_dir_path() -> Path:
    return ROOT / INTENT_LAYER_NODES_RELATIVE_DIR


def intent_layer_overlay_path() -> Path:
    return RUNS_DIR / INTENT_LAYER_OVERLAY_FILENAME


def intent_layer_node_filename(handle_value: str) -> str:
    normalized = sanitize_for_git(handle_value).replace("/", "-").strip("-")
    if not normalized:
        normalized = "intent"
    digest = hashlib.sha256(handle_value.encode("utf-8")).hexdigest()[:8]
    return f"{normalized}--{digest}.json"


def intent_layer_node_path(handle_value: str) -> Path:
    return intent_layer_nodes_dir_path() / intent_layer_node_filename(handle_value)


def proposal_lane_nodes_dir_path() -> Path:
    return ROOT / PROPOSAL_LANE_NODES_RELATIVE_DIR


def proposal_lane_overlay_path() -> Path:
    return RUNS_DIR / PROPOSAL_LANE_OVERLAY_FILENAME


def proposal_lane_node_filename(handle_value: str) -> str:
    normalized = sanitize_for_git(handle_value).replace("/", "-").strip("-")
    if not normalized:
        normalized = "proposal"
    digest = hashlib.sha256(handle_value.encode("utf-8")).hexdigest()[:8]
    return f"{normalized}--{digest}.json"


def proposal_lane_node_path(handle_value: str) -> Path:
    return proposal_lane_nodes_dir_path() / proposal_lane_node_filename(handle_value)


def proposal_artifact_filename(*, proposal_type: str, spec_id: str, signal: str) -> str:
    safe_spec_id = sanitize_for_git(spec_id).replace("/", "-")
    safe_signal = sanitize_for_git(signal).replace("/", "-")
    safe_type = sanitize_for_git(proposal_type).replace("/", "-")
    return f"{safe_type}--{safe_spec_id}--{safe_signal}.json"


def proposal_artifact_path(*, proposal_type: str, spec_id: str, signal: str) -> Path:
    return proposals_dir_path() / proposal_artifact_filename(
        proposal_type=proposal_type,
        spec_id=spec_id,
        signal=signal,
    )


def proposal_artifact_relpath(*, proposal_type: str, spec_id: str, signal: str) -> str:
    return (
        proposal_artifact_path(
            proposal_type=proposal_type,
            spec_id=spec_id,
            signal=signal,
        )
        .relative_to(ROOT)
        .as_posix()
    )


def split_proposal_allowed_changed_paths(artifact_relpath: str) -> set[str]:
    """Allow the proposal artifact file plus any untracked parent dirs.

    `git status --porcelain` may surface a newly created artifact as
    `runs/proposals/` instead of the concrete JSON file. Split proposal mode
    should treat those parent directories as part of the single allowed write.
    """

    normalized = artifact_relpath.strip().rstrip("/")
    allowed = {normalized}
    current = PurePosixPath(normalized)
    for parent in current.parents:
        parent_text = parent.as_posix().rstrip("/")
        if not parent_text or parent_text == ".":
            continue
        allowed.add(parent_text)
        allowed.add(f"{parent_text}/")
    return allowed


def proposal_item_path(item: dict[str, Any]) -> Path:
    path_value = str(item.get("proposal_artifact_path", "")).strip()
    if not path_value:
        path_value = proposal_artifact_relpath(
            proposal_type=str(item.get("proposal_type", "")).strip() or "refactor_proposal",
            spec_id=str(item.get("target_spec_id", "")).strip()
            or str(item.get("spec_id", "")).strip(),
            signal=str(item.get("source_signal", "")).strip()
            or str(item.get("signal", "")).strip(),
        )
    return ROOT / path_value


def run_log_paths() -> list[Path]:
    return sorted(RUNS_DIR.glob("*-SG-SPEC-*.json"))


def classify_refactor_work_item(signal: str) -> str:
    governance_signals = set(policy_lookup("queue_policy.governance_proposal_signals"))
    if signal in governance_signals:
        return "governance_proposal"
    return "graph_refactor"


def default_action_for_signal(signal: str) -> str:
    default_actions = policy_lookup("queue_policy.default_actions")
    return str(default_actions.get(signal, "review_graph_health_signal"))


def proposal_is_active(item: dict[str, Any]) -> bool:
    status = str(item.get("status", "proposed")).strip()
    return status in {"proposed", "review_pending", "pending_review"}


def proposal_is_applicable(item: dict[str, Any]) -> bool:
    status = str(item.get("status", "proposed")).strip()
    return status in APPLICABLE_PROPOSAL_STATUSES


def has_active_proposal_for_signal(
    *,
    spec_id: str,
    signal: str,
    proposal_items: list[dict[str, Any]],
) -> bool:
    for item in proposal_items:
        if str(item.get("spec_id", "")).strip() != spec_id:
            continue
        if str(item.get("signal", "")).strip() != signal:
            continue
        if proposal_is_active(item):
            return True
    return False


def refactor_execution_policy(
    item: dict[str, Any],
    proposal_items: list[dict[str, Any]] | None = None,
) -> str:
    work_item_type = str(item.get("work_item_type", "")).strip()
    if work_item_type == "governance_proposal":
        return "emit_proposal"
    if work_item_type != "graph_refactor":
        return "review_graph_health_signal"

    proposal_items = proposal_items or []
    spec_id = str(item.get("spec_id", "")).strip()
    signal = str(item.get("signal", "")).strip()
    if has_active_proposal_for_signal(
        spec_id=spec_id,
        signal=signal,
        proposal_items=proposal_items,
    ):
        return "defer_to_active_proposal"
    if signal == RETROSPECTIVE_REFACTOR_SIGNAL:
        return "emit_proposal"
    if signal in SUBTREE_SHAPE_SIGNALS:
        return "emit_proposal"
    return "direct_graph_update"


def classify_proposal_type(work_item_type: str) -> str:
    if work_item_type == "governance_proposal":
        return "governance_proposal"
    return "refactor_proposal"


def handoff_metadata_for_signal(signal: str) -> dict[str, Any]:
    if str(signal).strip() != TECHSPEC_HANDOFF_PRIMARY_SIGNAL:
        return {}
    return {
        "target_layer": TECHSPEC_HANDOFF_TARGET_LAYER,
        "transition_profile": TECHSPEC_HANDOFF_TARGET_TRANSITION_PROFILE,
        "packet_type": TECHSPEC_HANDOFF_TARGET_PACKET_TYPE,
        "target_artifact_class": TECHSPEC_HANDOFF_TARGET_ARTIFACT_CLASS,
        "handoff_policy_reference": techspec_handoff_policy_reference(),
    }


def proposal_threshold_for_signal(*, signal: str, work_item_type: str) -> int:
    threshold_policy = policy_lookup("queue_policy.proposal_thresholds")
    if signal == RETROSPECTIVE_REFACTOR_SIGNAL:
        return int(threshold_policy["retrospective_refactor_candidate"])
    if work_item_type == "governance_proposal":
        return int(threshold_policy["governance_proposal"])
    return int(threshold_policy["default_graph_refactor"])


def signal_supporting_run_ids(spec_id: str, signal: str) -> list[str]:
    run_ids: list[str] = []
    for path in run_log_paths():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        if str(payload.get("graph_health_truth_basis", "")).strip() != "accepted_canonical":
            continue
        graph_health = payload.get("graph_health")
        if not isinstance(graph_health, dict):
            continue
        if str(graph_health.get("source_spec_id", "")).strip() != spec_id:
            continue
        signals = graph_health.get("signals")
        if not isinstance(signals, list):
            continue
        if signal not in {str(item) for item in signals}:
            continue
        run_id = str(payload.get("run_id", "")).strip()
        if run_id:
            run_ids.append(run_id)
    return run_ids


def build_refactor_queue_items(
    *,
    graph_health: dict[str, Any],
    run_id: str,
    proposal_items: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    observation_by_kind = {
        str(observation.get("kind", "")): observation
        for observation in graph_health.get("observations", [])
        if isinstance(observation, dict)
    }
    source_spec_id = str(graph_health.get("source_spec_id", "")).strip()
    items: list[dict[str, Any]] = []
    for signal in graph_health.get("signals", []):
        item_type = classify_refactor_work_item(signal)
        base_item = {
            "id": f"{item_type}::{source_spec_id}::{signal}",
            "work_item_type": item_type,
            "spec_id": source_spec_id,
            "signal": signal,
            "recommended_action": default_action_for_signal(signal),
            "status": "proposed",
            "source_run_id": run_id,
            "details": observation_by_kind.get(signal, {}).get("details"),
        }
        items.append(
            {
                **base_item,
                **handoff_metadata_for_signal(signal),
                "execution_policy": refactor_execution_policy(base_item, proposal_items),
            }
        )
    return items


def update_refactor_queue(
    *,
    graph_health: dict[str, Any],
    run_id: str,
    proposal_items: list[dict[str, Any]] | None = None,
) -> Path:
    """Refresh the derived refactor queue for one source spec.

    The queue is overwritten per source spec so the latest run owns the
    currently visible local graph-refactor suggestions for that node.
    """
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = refactor_queue_path()
    with artifact_lock(path):
        if path.exists():
            existing, error = load_json_list_report(path, artifact_kind="refactor queue artifact")
            if error:
                raise RuntimeError(error)
        else:
            existing = []

        source_spec_id = str(graph_health.get("source_spec_id", "")).strip()
        preserved = [
            item
            for item in (existing or [])
            if isinstance(item, dict) and str(item.get("spec_id", "")).strip() != source_spec_id
        ]
        updated = preserved + build_refactor_queue_items(
            graph_health=graph_health,
            run_id=run_id,
            proposal_items=proposal_items,
        )
        atomic_write_json(path, updated)
    return path


def build_proposal_queue_items(
    *,
    graph_health: dict[str, Any],
    run_id: str,
) -> list[dict[str, Any]]:
    observation_by_kind = {
        str(observation.get("kind", "")): observation
        for observation in graph_health.get("observations", [])
        if isinstance(observation, dict)
    }
    source_spec_id = str(graph_health.get("source_spec_id", "")).strip()
    items: list[dict[str, Any]] = []

    for signal in graph_health.get("signals", []):
        signal_name = str(signal).strip()
        work_item_type = classify_refactor_work_item(signal_name)
        supporting_run_ids = signal_supporting_run_ids(source_spec_id, signal_name)
        occurrence_count = len(supporting_run_ids) + 1
        if run_id not in supporting_run_ids:
            supporting_run_ids.append(run_id)
        threshold = proposal_threshold_for_signal(signal=signal_name, work_item_type=work_item_type)
        if occurrence_count < threshold:
            continue

        if signal_name == TECHSPEC_HANDOFF_PRIMARY_SIGNAL:
            proposal_type = "handoff_proposal"
        else:
            proposal_type = classify_proposal_type(work_item_type)
        if signal_name == TECHSPEC_HANDOFF_PRIMARY_SIGNAL:
            trigger = "handoff_boundary_signal"
        elif work_item_type == "governance_proposal":
            trigger = "governance_class_signal"
        elif signal_name == RETROSPECTIVE_REFACTOR_SIGNAL:
            trigger = "retrospective_signal"
        else:
            trigger = "recurring_signal"
        items.append(
            {
                "id": f"{proposal_type}::{source_spec_id}::{signal_name}",
                "proposal_type": proposal_type,
                "spec_id": source_spec_id,
                "signal": signal_name,
                "recommended_action": default_action_for_signal(signal_name),
                "status": "proposed",
                "trigger": trigger,
                "occurrence_count": occurrence_count,
                "threshold": threshold,
                "supporting_run_ids": supporting_run_ids,
                "source_work_item_type": work_item_type,
                "execution_policy": "emit_proposal",
                "details": observation_by_kind.get(signal_name, {}).get("details"),
                **handoff_metadata_for_signal(signal_name),
            }
        )
    return items


def update_proposal_queue(
    *,
    graph_health: dict[str, Any],
    run_id: str,
) -> tuple[Path, list[dict[str, Any]]]:
    """Refresh the derived proposal queue index for one source spec.

    The queue remains a lightweight index. Detailed split-refactor content
    lives in separate structured proposal artifacts under `runs/proposals/`.
    """
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = proposal_queue_path()
    with artifact_lock(path):
        if path.exists():
            existing, error = load_json_list_report(path, artifact_kind="proposal queue artifact")
            if error:
                raise RuntimeError(error)
        else:
            existing = []

        source_spec_id = str(graph_health.get("source_spec_id", "")).strip()
        preserved = [
            item
            for item in (existing or [])
            if isinstance(item, dict) and str(item.get("spec_id", "")).strip() != source_spec_id
        ]
        updated = preserved + build_proposal_queue_items(graph_health=graph_health, run_id=run_id)
        atomic_write_json(path, updated)
    sync_tracked_proposal_lane_from_queue(updated, spec_id=source_spec_id)
    return path, updated


def summarize_queue_transition(
    *,
    source_spec_id: str,
    before_items: list[dict[str, Any]] | None,
    after_items: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Summarize how one source spec's queue items changed across a run."""

    def scoped_by_id(items: list[dict[str, Any]] | None) -> dict[str, dict[str, Any]]:
        scoped: dict[str, dict[str, Any]] = {}
        for item in items or []:
            if not isinstance(item, dict):
                continue
            if str(item.get("spec_id", "")).strip() != source_spec_id:
                continue
            item_id = str(item.get("id", "")).strip()
            if not item_id:
                continue
            scoped[item_id] = item
        return scoped

    before_by_id = scoped_by_id(before_items)
    after_by_id = scoped_by_id(after_items)
    before_ids = set(before_by_id)
    after_ids = set(after_by_id)
    retained_ids = before_ids & after_ids
    updated_ids = sorted(
        item_id for item_id in retained_ids if before_by_id[item_id] != after_by_id[item_id]
    )
    return {
        "before_ids": sorted(before_ids),
        "after_ids": sorted(after_ids),
        "emitted_ids": sorted(after_ids - before_ids),
        "cleared_ids": sorted(before_ids - after_ids),
        "retained_ids": sorted(retained_ids),
        "updated_ids": updated_ids,
    }


def dedupe_decision_rules(rules: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for rule in rules:
        token = json.dumps(rule, ensure_ascii=False, sort_keys=True)
        if token in seen:
            continue
        seen.add(token)
        unique.append(rule)
    return unique


def build_selection_decision_rules(selected_by_rule: dict[str, Any]) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    sort_order = list(selected_by_rule.get("sort_order", []))
    if sort_order == policy_lookup("selection_priorities.explicit_target_sort_order"):
        rules.append(
            policy_rule(
                "selection_priorities.explicit_target_sort_order",
                reason="explicit operator targeting bypassed heuristic selector ordering",
                inputs={"selection_mode": selected_by_rule.get("selection_mode")},
            )
        )
    elif sort_order == policy_lookup("selection_priorities.ordinary_sort_order"):
        rules.append(
            policy_rule(
                "selection_priorities.ordinary_sort_order",
                reason="ordinary selector ordering determined the candidate ranking for this run",
                inputs={"selection_mode": selected_by_rule.get("selection_mode")},
            )
        )

    signal = str(selected_by_rule.get("refactor_work_item", {}).get("signal", "")).strip()
    if signal:
        rules.append(
            policy_rule(
                f"selection_priorities.refactor_signal_priority.{signal}",
                reason=(
                    "queued graph-refactor candidates were ranked by declarative signal priority"
                ),
                matched_value=refactor_signal_priority(signal),
                inputs={"signal": signal},
            )
        )

    profile_name = str(selected_by_rule.get("execution_profile", "")).strip()
    if profile_name in EXECUTION_PROFILES:
        rules.append(
            policy_rule(
                f"execution_profiles.profiles.{profile_name}",
                reason="selected execution profile provided the nested executor configuration",
                matched_value=asdict(EXECUTION_PROFILES[profile_name]),
                inputs={"profile_name": profile_name},
            )
        )
        run_authorities = {str(value) for value in selected_by_rule.get("run_authority", [])}
        if (
            profile_name == AUTO_CHILD_MATERIALIZATION_PROFILE_NAME
            and RUN_AUTHORITY_MATERIALIZE_ONE_CHILD in run_authorities
        ):
            rules.append(
                policy_rule(
                    "execution_profiles.auto_child_materialization_profile",
                    reason=(
                        "explicit child-materialization authority promoted the materialize profile"
                    ),
                    inputs={"run_authority": selected_by_rule.get("run_authority", [])},
                )
            )
        elif profile_name == AUTO_HEURISTIC_PROFILE_NAME and not selected_by_rule.get(
            "operator_target"
        ):
            rules.append(
                policy_rule(
                    "execution_profiles.auto_heuristic_profile",
                    reason="ordinary heuristic runs default to the fast execution profile",
                    inputs={"selection_mode": selected_by_rule.get("selection_mode")},
                )
            )
        elif profile_name == DEFAULT_EXECUTION_PROFILE_NAME and selected_by_rule.get(
            "operator_target"
        ):
            rules.append(
                policy_rule(
                    "execution_profiles.default_profile",
                    reason="explicit operator-targeted runs default to the standard profile",
                    inputs={"selection_mode": selected_by_rule.get("selection_mode")},
                )
            )

    if str(selected_by_rule.get("selection_mode", "")).strip() == "linked_continuation":
        rules.append(
            policy_rule(
                "thresholds.linked_continuation_maturity",
                reason="linked-continuation eligibility consults the declarative maturity floor",
                inputs={"continuation_reasons": selected_by_rule.get("continuation_reasons", [])},
            )
        )
    return dedupe_decision_rules(rules)


def build_gate_decision_rules(
    *,
    gate_state: str,
    blocker: str,
    failing_validators: list[str],
    refinement_acceptance: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    if gate_state in GATE_ACTION_PRIORITY:
        rules.append(
            policy_rule(
                f"selection_priorities.gate_action_priority.{gate_state}",
                reason="pending gate ordering uses the declarative gate-state priority map",
                matched_value=GATE_ACTION_PRIORITY.get(gate_state),
                inputs={"gate_state": gate_state},
            )
        )
    if refinement_acceptance is not None:
        change_class = str(refinement_acceptance.get("change_class", "")).strip()
        decision = str(refinement_acceptance.get("decision", "")).strip()
        if change_class:
            rules.append(
                policy_rule(
                    f"change_classification.change_classes.{change_class}",
                    reason="gate outcome used the classified semantic change scope",
                    inputs={"decision": decision, "change_class": change_class},
                )
            )
        for mutation_class in refinement_acceptance.get("mutation_classes", []):
            if mutation_class in KNOWN_MUTATION_CLASSES:
                rules.append(
                    policy_rule(
                        f"mutation_classes.{mutation_class}",
                        reason="detected mutation classes contributed to gate evaluation",
                        inputs={"decision": decision},
                    )
                )
        budget_exceeded = list(refinement_acceptance.get("budget_exceeded_classes", []))
        if budget_exceeded:
            rules.append(
                runtime_rule(
                    "gate.review_required_due_to_mutation_budget",
                    reason=(
                        "manual review was required because the requested mutation "
                        "budget was exceeded"
                    ),
                    matched_value=budget_exceeded,
                    inputs={"decision": decision},
                )
            )
        elif decision == REFINEMENT_ACCEPT_DECISION_REVIEW_REQUIRED:
            rules.append(
                runtime_rule(
                    "gate.review_required_due_to_non_local_change",
                    reason=(
                        "manual review was required because the change was not a local refinement"
                    ),
                    matched_value=change_class,
                )
            )
        elif decision == REFINEMENT_ACCEPT_DECISION_REJECT:
            rules.append(
                runtime_rule(
                    "gate.reject_due_to_refinement_acceptance",
                    reason=(
                        "refinement acceptance rejected the candidate change before gate promotion"
                    ),
                    matched_value=list(refinement_acceptance.get("errors", [])),
                )
            )
    if failing_validators:
        rules.append(
            runtime_rule(
                "gate.failing_validators",
                reason="failing validators contributed to the final gate state or blocker",
                matched_value=failing_validators,
            )
        )
    if blocker and blocker != "none":
        rules.append(
            runtime_rule(
                "gate.blocker",
                reason="a concrete runtime or validation blocker propagated into the gate result",
                matched_value=blocker,
            )
        )
    return dedupe_decision_rules(rules)


def build_diff_classification_rules(
    *,
    refinement_acceptance: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if refinement_acceptance is None:
        return []
    rules: list[dict[str, Any]] = []
    change_class = str(refinement_acceptance.get("change_class", "")).strip()
    if change_class:
        rules.append(
            policy_rule(
                f"change_classification.change_classes.{change_class}",
                reason="canonical diff paths were classified under this semantic change class",
                inputs={"diff_paths": refinement_acceptance.get("diff_paths", [])},
            )
        )
        if change_class in {REFINEMENT_CLASS_GRAPH_REFACTOR, REFINEMENT_CLASS_CONSTITUTIONAL}:
            rules.append(
                policy_rule(
                    f"change_classification.change_classes.{change_class}.diff_prefixes",
                    reason=(
                        "named diff-prefix families were consulted when classifying "
                        "the accepted change"
                    ),
                )
            )
    for mutation_class in refinement_acceptance.get("mutation_classes", []):
        if mutation_class in KNOWN_MUTATION_CLASSES:
            rules.append(
                policy_rule(
                    f"mutation_classes.{mutation_class}",
                    reason=(
                        "detected mutation classes summarize the accepted canonical change surface"
                    ),
                )
            )
    if any(
        path_matches_prefix(path, IMMUTABLE_DIFF_PREFIXES)
        for path in refinement_acceptance.get("diff_paths", [])
    ):
        rules.append(
            policy_rule(
                "change_classification.immutable_diff_prefixes",
                reason=(
                    "immutable identity prefixes were checked while classifying the canonical diff"
                ),
            )
        )
    return dedupe_decision_rules(rules)


def build_queue_effect_rules(
    *,
    graph_health: dict[str, Any],
    proposal_queue_transition: dict[str, Any],
    refactor_queue_transition: dict[str, Any],
) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    governance_signals = set(policy_lookup("queue_policy.governance_proposal_signals"))
    subtree_shape_signals = set(policy_lookup("queue_policy.subtree_shape_signals"))
    lower_boundary_signals = set(policy_lookup("queue_policy.lower_boundary_handoff_signals"))
    for signal_value in graph_health.get("signals", []):
        signal = str(signal_value).strip()
        if not signal:
            continue
        rules.append(
            policy_rule(
                f"queue_policy.default_actions.{signal}",
                reason=(
                    "each graph-health signal emits its default recommended action "
                    "from the policy layer"
                ),
                inputs={"signal": signal},
            )
        )
        if signal in governance_signals:
            rules.append(
                policy_rule(
                    "queue_policy.governance_proposal_signals",
                    reason="this signal is handled proposal-first as a governance concern",
                    matched_value=signal,
                )
            )
        if signal in subtree_shape_signals:
            rules.append(
                policy_rule(
                    "queue_policy.subtree_shape_signals",
                    reason=(
                        "this signal belongs to the subtree-shape family that prefers "
                        "rewrite/merge proposals"
                    ),
                    matched_value=signal,
                )
            )
        if signal in lower_boundary_signals:
            rules.append(
                policy_rule(
                    "queue_policy.lower_boundary_handoff_signals",
                    reason="this signal belongs to the lower-boundary handoff family",
                    matched_value=signal,
                )
            )
        work_item_type = classify_refactor_work_item(signal)
        threshold_policy_path = "queue_policy.proposal_thresholds.default_graph_refactor"
        if signal == RETROSPECTIVE_REFACTOR_SIGNAL:
            threshold_policy_path = (
                "queue_policy.proposal_thresholds.retrospective_refactor_candidate"
            )
        elif work_item_type == "governance_proposal":
            threshold_policy_path = "queue_policy.proposal_thresholds.governance_proposal"
        rules.append(
            policy_rule(
                threshold_policy_path,
                reason=(
                    "proposal emission consulted the declarative supporting-run "
                    "threshold for this signal family"
                ),
                matched_value=proposal_threshold_for_signal(
                    signal=signal,
                    work_item_type=work_item_type,
                ),
                inputs={"signal": signal, "work_item_type": work_item_type},
            )
        )

    if proposal_queue_transition["emitted_ids"] or proposal_queue_transition["updated_ids"]:
        rules.append(
            runtime_rule(
                "queue.proposal_queue_transition",
                reason="proposal queue changed after applying graph-health signal rules",
                matched_value=proposal_queue_transition,
            )
        )
    if refactor_queue_transition["emitted_ids"] or refactor_queue_transition["updated_ids"]:
        rules.append(
            runtime_rule(
                "queue.refactor_queue_transition",
                reason="refactor queue changed after applying graph-health signal rules",
                matched_value=refactor_queue_transition,
            )
        )
    return dedupe_decision_rules(rules)


def build_decision_inspector(
    *,
    run_id: str,
    spec_id: str,
    selected_by_rule: dict[str, Any],
    outcome: str,
    gate_state: str,
    required_human_action: str,
    blocker: str,
    changed_files: list[str],
    validation_errors: list[str],
    validator_results: dict[str, bool] | None,
    graph_health: dict[str, Any],
    graph_health_truth_basis: str,
    proposal_queue_before: list[dict[str, Any]] | None,
    proposal_queue_after: list[dict[str, Any]] | None,
    refactor_queue_before: list[dict[str, Any]] | None,
    refactor_queue_after: list[dict[str, Any]] | None,
    refinement_acceptance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    failing_validators = sorted(
        name for name, ok in (validator_results or {}).items() if not bool(ok)
    )
    proposal_queue_transition = summarize_queue_transition(
        source_spec_id=spec_id,
        before_items=proposal_queue_before,
        after_items=proposal_queue_after,
    )
    refactor_queue_transition = summarize_queue_transition(
        source_spec_id=spec_id,
        before_items=refactor_queue_before,
        after_items=refactor_queue_after,
    )
    diff_classification = {
        "changed_files": list(changed_files),
        "changed_spec_files": [path for path in changed_files if is_spec_node_path(path)],
        "validation_error_count": len(validation_errors),
        "graph_health_truth_basis": graph_health_truth_basis,
    }
    if refinement_acceptance is not None:
        diff_classification.update(
            {
                "refinement_decision": str(refinement_acceptance.get("decision", "")).strip(),
                "change_class": str(refinement_acceptance.get("change_class", "")).strip(),
                "mutation_classes": list(refinement_acceptance.get("mutation_classes", [])),
                "review_reasons": list(refinement_acceptance.get("review_reasons", [])),
                "budget_exceeded_classes": list(
                    refinement_acceptance.get("budget_exceeded_classes", [])
                ),
            }
        )
    diff_classification["applied_rules"] = build_diff_classification_rules(
        refinement_acceptance=refinement_acceptance,
    )
    return {
        "artifact_kind": "decision_inspector",
        "run_id": run_id,
        "policy_reference": supervisor_policy_reference(),
        "selection": {
            "spec_id": spec_id,
            "mode": str(selected_by_rule.get("selection_mode", "")).strip(),
            "rule_inputs": copy.deepcopy(selected_by_rule),
            "applied_rules": build_selection_decision_rules(selected_by_rule),
        },
        "gate": {
            "outcome": outcome,
            "gate_state": gate_state,
            "required_human_action": required_human_action,
            "blocker": blocker,
            "failing_validators": failing_validators,
            "applied_rules": build_gate_decision_rules(
                gate_state=gate_state,
                blocker=blocker,
                failing_validators=failing_validators,
                refinement_acceptance=refinement_acceptance,
            ),
        },
        "diff_classification": diff_classification,
        "queue_effects": {
            "signals": list(graph_health.get("signals", [])),
            "recommended_actions": list(graph_health.get("recommended_actions", [])),
            "proposal_queue": proposal_queue_transition,
            "refactor_queue": refactor_queue_transition,
            "applied_rules": build_queue_effect_rules(
                graph_health=graph_health,
                proposal_queue_transition=proposal_queue_transition,
                refactor_queue_transition=refactor_queue_transition,
            ),
        },
    }


def artifact_lock_path(path: Path) -> Path:
    return path.with_name(f"{path.name}.lock")


@contextmanager
def artifact_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = artifact_lock_path(path)
    deadline = time.monotonic() + ARTIFACT_LOCK_TIMEOUT_SECONDS
    acquired = False
    while not acquired:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except FileExistsError as exc:
            if time.monotonic() >= deadline:
                raise RuntimeError(
                    f"Timed out waiting for artifact lock: {lock_path.relative_to(ROOT).as_posix()}"
                ) from exc
            time.sleep(ARTIFACT_LOCK_POLL_SECONDS)
            continue
        with os.fdopen(fd, "w", encoding="utf-8") as lock_file:
            lock_file.write(
                json.dumps(
                    {
                        "pid": os.getpid(),
                        "thread": threading.get_ident(),
                        "locked_at": utc_now_iso(),
                    },
                    ensure_ascii=False,
                )
            )
        acquired = True
    try:
        yield
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def atomic_write_text(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        tmp_path.write_text(text, encoding="utf-8")
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
    return path


def atomic_write_json(path: Path, payload: Any) -> Path:
    return atomic_write_text(path, json.dumps(payload, ensure_ascii=False, indent=2))


def display_artifact_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_json_object_report(path: Path, *, artifact_kind: str) -> tuple[dict[str, Any] | None, str]:
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, f"Failed to read {artifact_kind}: {display_artifact_path(path)} ({exc})"
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        return (
            None,
            f"Malformed {artifact_kind}: {display_artifact_path(path)} ({exc})",
        )
    if not isinstance(data, dict):
        return (
            None,
            f"Malformed {artifact_kind}: {display_artifact_path(path)} must contain a JSON object",
        )
    return data, ""


def load_json_list_report(
    path: Path,
    *,
    artifact_kind: str,
) -> tuple[list[dict[str, Any]] | None, str]:
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, f"Failed to read {artifact_kind}: {display_artifact_path(path)} ({exc})"
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        return (
            None,
            f"Malformed {artifact_kind}: {display_artifact_path(path)} ({exc})",
        )
    if not isinstance(data, list):
        return (
            None,
            f"Malformed {artifact_kind}: {display_artifact_path(path)} must contain a JSON list",
        )
    if not all(isinstance(item, dict) for item in data):
        return (
            None,
            (
                f"Malformed {artifact_kind}: {display_artifact_path(path)} must contain only "
                "JSON objects"
            ),
        )
    return list(data), ""


def load_json_object(path: Path) -> dict[str, Any] | None:
    data, _error = load_json_object_report(path, artifact_kind="JSON artifact")
    return data


def intent_layer_valid_kinds() -> set[str]:
    return set(INTENT_LAYER_ALLOWED_KINDS)


def intent_layer_valid_states() -> set[str]:
    return set(INTENT_LAYER_ALLOWED_STATES)


def intent_layer_kind_required_sections(kind: str) -> tuple[str, ...]:
    raw_sections = INTENT_LAYER_REQUIRED_SECTIONS_BY_KIND.get(str(kind).strip(), [])
    return tuple(str(section).strip() for section in raw_sections if str(section).strip())


def build_intent_layer_overlay() -> dict[str, Any]:
    nodes_dir = intent_layer_nodes_dir_path()
    entries: list[dict[str, Any]] = []
    artifact_warnings: list[dict[str, str]] = []
    raw_nodes: list[dict[str, Any]] = []

    if nodes_dir.exists():
        for path in sorted(nodes_dir.glob("*.json")):
            data, error = load_json_object_report(path, artifact_kind="intent layer node artifact")
            if data is None:
                artifact_warnings.append(
                    {
                        "tracked_path": display_artifact_path(path),
                        "error": error,
                    }
                )
                continue
            raw_nodes.append({"tracked_path": display_artifact_path(path), "node": data})

    handle_counts: dict[str, int] = {}
    for raw in raw_nodes:
        node = raw["node"]
        presence = node.get("intent_repository_presence")
        handle = node.get("intent_handle")
        if (
            isinstance(presence, dict)
            and all(
                str(presence.get(key, "")).strip() == str(value)
                for key, value in INTENT_LAYER_PRESENCE_CONTRACT.items()
            )
            and isinstance(handle, dict)
            and str(handle.get("handle_status", "")).strip() == "active"
        ):
            handle_value = str(handle.get("handle_value", "")).strip()
            if handle_value:
                handle_counts[handle_value] = handle_counts.get(handle_value, 0) + 1

    by_kind: dict[str, list[str]] = {}
    by_state: dict[str, list[str]] = {}
    named_filters = {name: [] for name in INTENT_LAYER_NAMED_FILTERS}
    edges: list[dict[str, str]] = []

    for raw in raw_nodes:
        tracked_path = str(raw["tracked_path"])
        node = raw["node"]
        presence = node.get("intent_repository_presence")
        if not (
            isinstance(presence, dict)
            and all(
                str(presence.get(key, "")).strip() == str(value)
                for key, value in INTENT_LAYER_PRESENCE_CONTRACT.items()
            )
        ):
            continue

        handle = node.get("intent_handle", {})
        handle_value = str(handle.get("handle_value", "")).strip()
        intent_kind = str(node.get("intent_layer_kind", "")).strip()
        mediation_state = str(node.get("mediation_state", "")).strip()
        lineage_links = node.get("intent_lineage_link", [])
        runtime_bridge = node.get("runtime_bridge", {})
        request_bridge = node.get("request_bridge", {})
        query_findings: list[str] = []
        if not handle_value or str(handle.get("handle_status", "")).strip() != "active":
            query_findings.append("missing_active_handle")
        if intent_kind not in intent_layer_valid_kinds():
            query_findings.append("invalid_intent_layer_kind")
        if mediation_state not in intent_layer_valid_states():
            query_findings.append("invalid_mediation_state")
        if not (
            isinstance(lineage_links, list)
            and any(
                isinstance(link, dict)
                and str(link.get("lineage_role", "")).strip()
                and str(link.get("source_kind", "")).strip()
                and str(link.get("source_reference", "")).strip()
                for link in lineage_links
            )
        ):
            query_findings.append("missing_lineage_link")
        if handle_value and handle_counts.get(handle_value, 0) > 1:
            query_findings.append("colliding_active_handle")

        required_sections = intent_layer_kind_required_sections(intent_kind)
        for section_name in required_sections:
            if not isinstance(node.get(section_name), dict):
                query_findings.append(f"missing_kind_section::{section_name}")
        if intent_kind == "user_intent" and isinstance(request_bridge, dict) and request_bridge:
            query_findings.append("kind_contract_mismatch::user_intent_has_request_bridge")
        if intent_kind == "operator_request":
            if not (
                isinstance(request_bridge, dict)
                and str(request_bridge.get("run_mode", "")).strip()
                and str(request_bridge.get("target_spec_id", "")).strip()
            ):
                query_findings.append("missing_request_bridge_target")
        if any(field in node for field in INTENT_LAYER_CANONICAL_SPEC_FORBIDDEN_FIELDS):
            query_findings.append("masquerades_as_canonical_spec")
        if any(field in node for field in INTENT_LAYER_PROPOSAL_LANE_FORBIDDEN_FIELDS):
            query_findings.append("masquerades_as_proposal_lane")
        entry = {
            "tracked_path": tracked_path,
            "title": str(node.get("title", "")).strip(),
            "intent_handle": handle_value,
            "intent_layer_kind": intent_kind,
            "mediation_state": mediation_state,
            "distinction_contract": {
                "semantic_artifact_class": intent_kind or "unknown",
                "canonical_equivalence": False,
                "proposal_lane_equivalence": False,
                "pre_canonical_runtime_mediation": True,
            },
            "query_contract": {
                "status": "invalid_review_state" if query_findings else "ok",
                "findings": sorted(set(query_findings)),
            },
            "lineage_links": (
                copy.deepcopy(lineage_links) if isinstance(lineage_links, list) else []
            ),
            "runtime_bridge": (
                copy.deepcopy(runtime_bridge) if isinstance(runtime_bridge, dict) else {}
            ),
        }
        if isinstance(request_bridge, dict) and request_bridge:
            entry["request_bridge"] = copy.deepcopy(request_bridge)
        entries.append(entry)

        by_kind.setdefault(intent_kind or "unknown", []).append(handle_value or tracked_path)
        by_state.setdefault(mediation_state or "unknown", []).append(handle_value or tracked_path)
        if intent_kind in named_filters:
            named_filters[intent_kind].append(handle_value or tracked_path)
        if mediation_state in named_filters:
            named_filters[mediation_state].append(handle_value or tracked_path)
        if query_findings:
            named_filters["invalid_query_contract"].append(handle_value or tracked_path)

        for link in lineage_links if isinstance(lineage_links, list) else []:
            if not isinstance(link, dict):
                continue
            source_reference = str(link.get("source_reference", "")).strip()
            if not source_reference:
                continue
            edges.append(
                {
                    "source": handle_value or tracked_path,
                    "target": source_reference,
                    "edge_kind": (
                        f"lineage::{str(link.get('lineage_role', '')).strip()}::"
                        f"{str(link.get('source_kind', '')).strip()}"
                    ),
                }
            )

    for key, values in list(named_filters.items()):
        named_filters[key] = sorted(set(values))
    entries.sort(
        key=lambda item: (
            item["intent_layer_kind"],
            item["intent_handle"],
            item["tracked_path"],
        )
    )
    return {
        "artifact_kind": INTENT_LAYER_OVERLAY_ARTIFACT_KIND,
        "schema_version": INTENT_LAYER_OVERLAY_SCHEMA_VERSION,
        "layer_name": INTENT_LAYER_LAYER_NAME,
        "generated_at": utc_now_iso(),
        "policy_reference": intent_layer_policy_reference(),
        "source_dir": INTENT_LAYER_NODES_RELATIVE_DIR,
        "entry_count": len(entries),
        "entries": entries,
        "by_kind": {key: sorted(set(values)) for key, values in sorted(by_kind.items())},
        "by_mediation_state": {
            key: sorted(set(values)) for key, values in sorted(by_state.items())
        },
        "named_filters": named_filters,
        "edges": edges,
        "artifact_warnings": artifact_warnings,
    }


def write_intent_layer_overlay(overlay: dict[str, Any]) -> Path:
    path = intent_layer_overlay_path()
    with artifact_lock(path):
        atomic_write_json(path, overlay)
    return path


def proposal_lane_valid_authority_states() -> set[str]:
    return {str(value).strip() for value in PROPOSAL_LANE_AUTHORITY_STATE_MAPPING.values()}


def proposal_lane_authority_state_for_status(status: str) -> str:
    normalized = str(status).strip()
    return str(PROPOSAL_LANE_AUTHORITY_STATE_MAPPING.get(normalized, "draft"))


def proposal_lane_target_reference(proposal_item: dict[str, Any]) -> str:
    return str(
        proposal_item.get("target_spec_id")
        or proposal_item.get("spec_id")
        or proposal_item.get("target_reference")
        or ""
    ).strip()


def proposal_lane_target_region(proposal_item: dict[str, Any]) -> dict[str, str]:
    target_reference = proposal_lane_target_reference(proposal_item)
    target_kind = "canonical_node" if target_reference else "draft_target_area"
    change_scope = str(
        proposal_item.get("signal") or proposal_item.get("proposal_type") or ""
    ).strip()
    if not change_scope:
        change_scope = str(proposal_item.get("id", "")).strip()
    return {
        "target_kind": target_kind,
        "target_reference": target_reference or str(proposal_item.get("id", "")).strip(),
        "change_scope": change_scope,
    }


def proposal_lane_lineage_links(proposal_item: dict[str, Any]) -> list[dict[str, str]]:
    lineage_links: list[dict[str, str]] = []
    target_reference = proposal_lane_target_reference(proposal_item)
    if target_reference:
        lineage_links.append(
            {
                "lineage_role": "motivated_by",
                "source_kind": "canonical_node",
                "source_reference": target_reference,
            }
        )
    proposal_artifact_path_value = str(proposal_item.get("proposal_artifact_path", "")).strip()
    if proposal_artifact_path_value:
        lineage_links.append(
            {
                "lineage_role": "derived_from",
                "source_kind": "runtime_artifact",
                "source_reference": proposal_artifact_path_value,
            }
        )
    return lineage_links


def proposal_lane_artifact_links(proposal_item: dict[str, Any]) -> list[dict[str, str]]:
    proposal_artifact_path_value = str(proposal_item.get("proposal_artifact_path", "")).strip()
    if not proposal_artifact_path_value:
        return []
    return [
        {
            "artifact_role": "supporting_runtime_artifact",
            "reference_kind": "runtime_artifact",
            "reference_value": proposal_artifact_path_value,
        }
    ]


def proposal_lane_node_title(proposal_item: dict[str, Any]) -> str:
    proposal_type = str(proposal_item.get("proposal_type", "proposal")).strip().replace("_", " ")
    target_reference = proposal_lane_target_reference(proposal_item) or "unscoped target"
    signal = str(proposal_item.get("signal", "")).strip()
    suffix = f" ({signal})" if signal else ""
    return f"{proposal_type.title()} for {target_reference}{suffix}"


def sync_tracked_proposal_lane_node(
    proposal_item: dict[str, Any],
) -> tuple[Path, dict[str, Any]] | None:
    handle_value = str(proposal_item.get("id", "")).strip()
    if not handle_value:
        return None

    path = proposal_lane_node_path(handle_value)
    tracked_path = path.relative_to(ROOT).as_posix()
    existing = load_json_object(path) if path.exists() else None
    created_at = str((existing or {}).get("created_at", "")).strip() or utc_now_iso()
    authority_state = proposal_lane_authority_state_for_status(
        str(proposal_item.get("status", "")).strip() or "proposed"
    )
    node = dict(existing or {})
    node.update(
        {
            "artifact_kind": PROPOSAL_LANE_NODE_ARTIFACT_KIND,
            "schema_version": PROPOSAL_LANE_NODE_SCHEMA_VERSION,
            "title": proposal_lane_node_title(proposal_item),
            "created_at": created_at,
            "updated_at": utc_now_iso(),
            "policy_reference": proposal_lane_policy_reference(),
            "proposal_repository_presence": {
                **copy.deepcopy(PROPOSAL_LANE_PRESENCE_CONTRACT),
                "tracked_path": tracked_path,
            },
            "proposal_handle": {
                "handle_value": handle_value,
                "handle_status": "active",
            },
            "proposal_authority_state": authority_state,
            "proposal_target_region": proposal_lane_target_region(proposal_item),
            "proposal_lineage_link": proposal_lane_lineage_links(proposal_item),
            "proposal_artifact_link": proposal_lane_artifact_links(proposal_item),
            "proposal_payload": {
                "proposal_type": str(proposal_item.get("proposal_type", "")).strip(),
                "trigger": str(proposal_item.get("trigger", "")).strip(),
                "recommended_action": str(proposal_item.get("recommended_action", "")).strip(),
                "signal": str(proposal_item.get("signal", "")).strip(),
                "source_work_item_type": str(
                    proposal_item.get("source_work_item_type", "")
                ).strip(),
                "execution_policy": str(proposal_item.get("execution_policy", "")).strip(),
                "transition_profile": str(proposal_item.get("transition_profile", "")).strip(),
                "packet_type": str(proposal_item.get("packet_type", "")).strip(),
                "target_artifact_class": str(
                    proposal_item.get("target_artifact_class", "")
                ).strip(),
            },
            "runtime_bridge": {
                "proposal_queue_status": str(proposal_item.get("status", "")).strip(),
                "supporting_run_ids": list(proposal_item.get("supporting_run_ids", [])),
                "occurrence_count": proposal_item.get("occurrence_count"),
                "threshold": proposal_item.get("threshold"),
                "proposal_artifact_path": str(
                    proposal_item.get("proposal_artifact_path", "")
                ).strip(),
                "applied_run_id": str(proposal_item.get("applied_run_id", "")).strip(),
                "applied_at": str(proposal_item.get("applied_at", "")).strip(),
            },
        }
    )
    if str(proposal_item.get("status", "")).strip() == "applied":
        node["canonical_application_event"] = {
            "event_status": "canonical_materialization_recorded",
            "applied_run_id": str(proposal_item.get("applied_run_id", "")).strip(),
            "applied_at": str(proposal_item.get("applied_at", "")).strip(),
        }
    else:
        node.pop("canonical_application_event", None)

    path.parent.mkdir(parents=True, exist_ok=True)
    with artifact_lock(path):
        atomic_write_json(path, node)
    return path, node


def retire_stale_tracked_proposal_lane_nodes(
    *,
    spec_id: str,
    active_item_ids: set[str],
) -> list[Path]:
    nodes_dir = proposal_lane_nodes_dir_path()
    if not nodes_dir.exists():
        return []

    retired_paths: list[Path] = []
    for path in sorted(nodes_dir.glob("*.json")):
        node = load_json_object(path)
        if not isinstance(node, dict):
            continue
        handle = node.get("proposal_handle")
        handle_value = (
            str(handle.get("handle_value", "")).strip() if isinstance(handle, dict) else ""
        )
        if not handle_value or handle_value in active_item_ids:
            continue
        target_region = node.get("proposal_target_region")
        target_reference = (
            str(target_region.get("target_reference", "")).strip()
            if isinstance(target_region, dict)
            else ""
        )
        if target_reference != spec_id:
            continue
        runtime_bridge = node.get("runtime_bridge")
        if not isinstance(runtime_bridge, dict):
            continue
        if not str(runtime_bridge.get("proposal_queue_status", "")).strip():
            continue
        if str(node.get("proposal_authority_state", "")).strip() in {"rejected", "superseded"}:
            continue

        updated_runtime_bridge = dict(runtime_bridge)
        updated_runtime_bridge["proposal_queue_status"] = "superseded"
        updated_runtime_bridge["queue_presence"] = "retired_after_queue_refresh"
        updated_runtime_bridge["last_queue_sync_at"] = utc_now_iso()
        node["proposal_authority_state"] = "superseded"
        node["runtime_bridge"] = updated_runtime_bridge
        node["updated_at"] = utc_now_iso()
        with artifact_lock(path):
            atomic_write_json(path, node)
        retired_paths.append(path)
    return retired_paths


def sync_tracked_proposal_lane_from_queue(
    queue_items: list[dict[str, Any]],
    *,
    spec_id: str | None = None,
    item_ids: set[str] | None = None,
) -> list[Path]:
    written_paths: list[Path] = []
    active_item_ids: set[str] = set()
    for item in queue_items:
        if not isinstance(item, dict):
            continue
        item_id = str(item.get("id", "")).strip()
        if item_ids is not None and item_id not in item_ids:
            continue
        if spec_id is not None and str(item.get("spec_id", "")).strip() != spec_id:
            continue
        if item_id:
            active_item_ids.add(item_id)
        synced = sync_tracked_proposal_lane_node(item)
        if synced is None:
            continue
        path, _node = synced
        written_paths.append(path)
    retired_paths: list[Path] = []
    if spec_id is not None:
        retired_paths = retire_stale_tracked_proposal_lane_nodes(
            spec_id=spec_id,
            active_item_ids=active_item_ids,
        )
    if written_paths or retired_paths:
        write_proposal_lane_overlay(build_proposal_lane_overlay())
    return written_paths + retired_paths


def build_proposal_lane_overlay() -> dict[str, Any]:
    nodes_dir = proposal_lane_nodes_dir_path()
    entries: list[dict[str, Any]] = []
    artifact_warnings: list[dict[str, str]] = []
    raw_nodes: list[dict[str, Any]] = []

    if nodes_dir.exists():
        for path in sorted(nodes_dir.glob("*.json")):
            data, error = load_json_object_report(path, artifact_kind="proposal lane node artifact")
            if data is None:
                artifact_warnings.append(
                    {
                        "tracked_path": display_artifact_path(path),
                        "error": error,
                    }
                )
                continue
            raw_nodes.append({"tracked_path": display_artifact_path(path), "node": data})

    handle_counts: dict[str, int] = {}
    for raw in raw_nodes:
        node = raw["node"]
        presence = node.get("proposal_repository_presence")
        handle = node.get("proposal_handle")
        if (
            isinstance(presence, dict)
            and all(
                str(presence.get(key, "")).strip() == str(value)
                for key, value in PROPOSAL_LANE_PRESENCE_CONTRACT.items()
            )
            and isinstance(handle, dict)
            and str(handle.get("handle_status", "")).strip() == "active"
        ):
            handle_value = str(handle.get("handle_value", "")).strip()
            if handle_value:
                handle_counts[handle_value] = handle_counts.get(handle_value, 0) + 1

    by_authority: dict[str, list[str]] = {}
    named_filters = {name: [] for name in PROPOSAL_LANE_NAMED_FILTERS}
    edges: list[dict[str, str]] = []

    for raw in raw_nodes:
        tracked_path = str(raw["tracked_path"])
        node = raw["node"]
        presence = node.get("proposal_repository_presence")
        if not (
            isinstance(presence, dict)
            and all(
                str(presence.get(key, "")).strip() == str(value)
                for key, value in PROPOSAL_LANE_PRESENCE_CONTRACT.items()
            )
        ):
            continue

        handle = node.get("proposal_handle", {})
        handle_value = str(handle.get("handle_value", "")).strip()
        authority_state = str(node.get("proposal_authority_state", "")).strip()
        target_region = node.get("proposal_target_region", {})
        lineage_links = node.get("proposal_lineage_link", [])
        query_findings: list[str] = []
        if not handle_value or str(handle.get("handle_status", "")).strip() != "active":
            query_findings.append("missing_active_handle")
        if authority_state not in proposal_lane_valid_authority_states():
            query_findings.append("invalid_authority_state")
        if not (
            isinstance(target_region, dict)
            and str(target_region.get("target_kind", "")).strip()
            and str(target_region.get("target_reference", "")).strip()
            and str(target_region.get("change_scope", "")).strip()
        ):
            query_findings.append("missing_target_region")
        if not (
            isinstance(lineage_links, list)
            and any(
                isinstance(link, dict)
                and str(link.get("lineage_role", "")).strip()
                and str(link.get("source_kind", "")).strip()
                and str(link.get("source_reference", "")).strip()
                for link in lineage_links
            )
        ):
            query_findings.append("missing_lineage_link")
        if handle_value and handle_counts.get(handle_value, 0) > 1:
            query_findings.append("colliding_active_handle")

        entry = {
            "tracked_path": tracked_path,
            "title": str(node.get("title", "")).strip(),
            "proposal_handle": handle_value,
            "proposal_authority_state": authority_state,
            "proposal_type": str(node.get("proposal_payload", {}).get("proposal_type", "")).strip(),
            "target_region": (
                copy.deepcopy(target_region) if isinstance(target_region, dict) else {}
            ),
            "lineage_links": (
                copy.deepcopy(lineage_links) if isinstance(lineage_links, list) else []
            ),
            "query_contract": {
                "required_fields": list(PROPOSAL_LANE_REQUIRED_QUERY_FIELDS),
                "status": "queryable" if not query_findings else "invalid_review_state",
                "findings": query_findings,
            },
        }
        entries.append(entry)

        by_authority.setdefault(authority_state or "unknown", []).append(
            handle_value or tracked_path
        )
        if authority_state == "under_review":
            named_filters["under_review"].append(handle_value or tracked_path)
        if authority_state == "approved_for_application":
            named_filters["approved_for_application"].append(handle_value or tracked_path)
        if authority_state in {"rejected", "superseded"}:
            named_filters["rejected_or_superseded"].append(handle_value or tracked_path)
        if query_findings:
            named_filters["invalid_query_contract"].append(handle_value or tracked_path)
        if str(target_region.get("target_kind", "")).strip() == "canonical_node":
            named_filters["canonical_node_targets"].append(handle_value or tracked_path)
            edges.append(
                {
                    "source": handle_value or tracked_path,
                    "target": str(target_region.get("target_reference", "")).strip(),
                    "edge_kind": "proposal_targets_canonical_node",
                }
            )
        for link in lineage_links if isinstance(lineage_links, list) else []:
            if not isinstance(link, dict):
                continue
            source_kind = str(link.get("source_kind", "")).strip()
            source_reference = str(link.get("source_reference", "")).strip()
            if source_kind == "runtime_artifact":
                named_filters["runtime_artifact_lineage"].append(handle_value or tracked_path)
            if source_reference:
                edges.append(
                    {
                        "source": handle_value or tracked_path,
                        "target": source_reference,
                        "edge_kind": (
                            f"lineage::{str(link.get('lineage_role', '')).strip()}::{source_kind}"
                        ),
                    }
                )

    return {
        "artifact_kind": PROPOSAL_LANE_OVERLAY_ARTIFACT_KIND,
        "schema_version": PROPOSAL_LANE_OVERLAY_SCHEMA_VERSION,
        "layer_name": PROPOSAL_LANE_LAYER_NAME,
        "generated_at": utc_now_iso(),
        "policy_reference": proposal_lane_policy_reference(),
        "source_dir": PROPOSAL_LANE_NODES_RELATIVE_DIR,
        "entry_count": len(entries),
        "entries": entries,
        "edges": edges,
        "by_authority_state": {key: sorted(value) for key, value in sorted(by_authority.items())},
        "named_filters": {key: sorted(set(value)) for key, value in sorted(named_filters.items())},
        "artifact_warnings": artifact_warnings,
    }


def write_proposal_lane_overlay(overlay: dict[str, Any]) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = proposal_lane_overlay_path()
    with artifact_lock(path):
        atomic_write_json(path, overlay)
    return path


def transition_packet_finding(
    *,
    code: str,
    message: str,
    field: str = "",
    severity: str = "error",
    family: str = "schema",
    profile: str = "",
) -> dict[str, str]:
    finding = {
        "code": code,
        "message": message,
        "severity": severity,
        "family": family,
    }
    if field:
        finding["field"] = field
    if profile:
        finding["profile"] = profile
    return finding


def product_spec_transition_policy_path() -> Path:
    return TOOLS_DIR / "product_spec_transition_policy.json"


def proposal_promotion_policy_path() -> Path:
    return TOOLS_DIR / "proposal_promotion_policy.json"


def load_product_spec_transition_policy_report() -> tuple[
    dict[str, Any] | None, list[dict[str, str]]
]:
    path = product_spec_transition_policy_path()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return None, [
            transition_packet_finding(
                code="product_spec_transition_policy_unavailable",
                family="profile",
                profile="product_spec",
                message=(
                    "failed to read product_spec transition policy artifact: "
                    f"{path.as_posix()} ({exc})"
                ),
            )
        ]
    except json.JSONDecodeError as exc:
        return None, [
            transition_packet_finding(
                code="malformed_product_spec_transition_policy",
                family="profile",
                profile="product_spec",
                message=(
                    f"malformed product_spec transition policy artifact: {path.as_posix()} ({exc})"
                ),
            )
        ]
    if not isinstance(payload, dict):
        return None, [
            transition_packet_finding(
                code="malformed_product_spec_transition_policy",
                family="profile",
                profile="product_spec",
                message=(
                    "malformed product_spec transition policy artifact: "
                    f"{path.as_posix()} must contain a JSON object"
                ),
            )
        ]

    required_sections = (
        "inherits_transition_profile",
        "required_binding_fields",
        "required_provenance_links",
        "reviewable_source_prefixes",
        "forbidden_source_prefixes",
        "apply_scope_rule",
    )
    missing = [section for section in required_sections if section not in payload]
    if missing:
        return None, [
            transition_packet_finding(
                code="malformed_product_spec_transition_policy",
                family="profile",
                profile="product_spec",
                message=(
                    "malformed product_spec transition policy artifact: missing top-level "
                    f"section(s): {', '.join(missing)}"
                ),
            )
        ]

    return payload, []


def load_proposal_promotion_policy_report() -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    path = proposal_promotion_policy_path()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        return None, [
            transition_packet_finding(
                code="proposal_promotion_policy_unavailable",
                family="profile",
                profile="specgraph_core",
                message=(
                    f"failed to read proposal promotion policy artifact: {path.as_posix()} ({exc})"
                ),
            )
        ]
    except json.JSONDecodeError as exc:
        return None, [
            transition_packet_finding(
                code="malformed_proposal_promotion_policy",
                family="profile",
                profile="specgraph_core",
                message=(
                    f"malformed proposal promotion policy artifact: {path.as_posix()} ({exc})"
                ),
            )
        ]
    if not isinstance(payload, dict):
        return None, [
            transition_packet_finding(
                code="malformed_proposal_promotion_policy",
                family="profile",
                profile="specgraph_core",
                message=(
                    "malformed proposal promotion policy artifact: "
                    f"{path.as_posix()} must contain a JSON object"
                ),
            )
        ]

    required_sections = (
        "semantic_boundary_principle",
        "semantic_artifact_classes",
        "repository_projection_defaults",
    )
    missing = [section for section in required_sections if section not in payload]
    if missing:
        return None, [
            transition_packet_finding(
                code="malformed_proposal_promotion_policy",
                family="profile",
                profile="specgraph_core",
                message=(
                    "malformed proposal promotion policy artifact: missing top-level "
                    f"section(s): {', '.join(missing)}"
                ),
            )
        ]

    if not isinstance(payload.get("semantic_artifact_classes"), dict):
        return None, [
            transition_packet_finding(
                code="malformed_proposal_promotion_policy",
                family="profile",
                profile="specgraph_core",
                message=(
                    "malformed proposal promotion policy artifact: "
                    "semantic_artifact_classes must be an object"
                ),
            )
        ]
    if not isinstance(payload.get("repository_projection_defaults"), list):
        return None, [
            transition_packet_finding(
                code="malformed_proposal_promotion_policy",
                family="profile",
                profile="specgraph_core",
                message=(
                    "malformed proposal promotion policy artifact: "
                    "repository_projection_defaults must be a list"
                ),
            )
        ]

    return payload, []


def _transition_packet_string_list(
    *,
    field_name: str,
    value: Any,
) -> tuple[list[str], list[dict[str, str]]]:
    if not isinstance(value, list):
        return [], [
            transition_packet_finding(
                code="invalid_string_list",
                field=field_name,
                message=f"{field_name} must be a list of non-empty strings",
            )
        ]

    normalized: list[str] = []
    findings: list[dict[str, str]] = []
    for index, item in enumerate(value, start=1):
        if not isinstance(item, str):
            findings.append(
                transition_packet_finding(
                    code="invalid_string_list_item",
                    field=field_name,
                    message=f"{field_name}[{index}] must be a non-empty string",
                )
            )
            continue
        normalized_item = item.strip()
        if not normalized_item:
            findings.append(
                transition_packet_finding(
                    code="invalid_string_list_item",
                    field=field_name,
                    message=f"{field_name}[{index}] must be a non-empty string",
                )
            )
            continue
        normalized.append(normalized_item)
    return normalized, findings


def _transition_packet_optional_string(
    *,
    field_name: str,
    value: Any,
) -> tuple[str, list[dict[str, str]]]:
    if value is None:
        return "", []
    if not isinstance(value, str):
        return "", [
            transition_packet_finding(
                code="invalid_string",
                field=field_name,
                message=f"{field_name} must be a non-empty string when provided",
            )
        ]
    normalized = value.strip()
    if not normalized:
        return "", [
            transition_packet_finding(
                code="invalid_string",
                field=field_name,
                message=f"{field_name} must be a non-empty string when provided",
            )
        ]
    return normalized, []


def _transition_packet_duplicate_list_findings(
    *,
    field_name: str,
    values: list[str],
    family: str,
) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    seen: set[str] = set()
    duplicates: list[str] = []
    for value in values:
        if value in seen and value not in duplicates:
            duplicates.append(value)
        seen.add(value)
    for duplicate in duplicates:
        findings.append(
            transition_packet_finding(
                code="duplicate_list_item",
                field=field_name,
                family=family,
                message=f"{field_name} contains duplicate item: {duplicate}",
            )
        )
    return findings


def _looks_like_repo_path(value: str) -> bool:
    if not value:
        return False
    return "/" in value or value.endswith((".md", ".yaml", ".yml", ".json", ".toml"))


def _normalize_transition_repo_path(value: str) -> str:
    if not _looks_like_repo_path(value):
        return value
    return PurePosixPath(value).as_posix()


def _validate_transition_surface_path(
    *,
    field_name: str,
    value: str,
) -> list[dict[str, str]]:
    if not value or not _looks_like_repo_path(value):
        return []
    path = PurePosixPath(value)
    findings: list[dict[str, str]] = []
    if path.is_absolute():
        findings.append(
            transition_packet_finding(
                code="absolute_path_not_allowed",
                field=field_name,
                family="diff_scope",
                message=f"{field_name} must use repo-relative paths, not absolute paths",
            )
        )
    if ".." in path.parts:
        findings.append(
            transition_packet_finding(
                code="parent_traversal_not_allowed",
                field=field_name,
                family="diff_scope",
                message=f"{field_name} must not use parent traversal",
            )
        )
    return findings


def _normalize_transition_packet_context(
    packet: Any,
    *,
    validator_profile: str | None = None,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    if not isinstance(packet, dict):
        return {}, [
            transition_packet_finding(
                code="packet_not_object",
                field="packet",
                family="schema",
                message="transition packet must be a JSON object",
            )
        ]

    findings: list[dict[str, str]] = []
    packet_type, packet_type_findings = _transition_packet_optional_string(
        field_name="packet_type",
        value=packet.get("packet_type"),
    )
    findings.extend(packet_type_findings)
    if packet_type and packet_type not in VALID_TRANSITION_PACKET_TYPES:
        findings.append(
            transition_packet_finding(
                code="invalid_packet_type",
                field="packet_type",
                family="schema",
                message=(
                    "packet_type must be one of: "
                    + ", ".join(sorted(VALID_TRANSITION_PACKET_TYPES))
                ),
            )
        )

    transition_profile_source = (
        validator_profile if validator_profile is not None else packet.get("transition_profile")
    )
    transition_profile, transition_profile_findings = _transition_packet_optional_string(
        field_name="transition_profile",
        value=transition_profile_source,
    )
    findings.extend(transition_profile_findings)
    if not transition_profile:
        transition_profile = DEFAULT_TRANSITION_VALIDATOR_PROFILE
    if transition_profile not in VALID_TRANSITION_VALIDATOR_PROFILES:
        findings.append(
            transition_packet_finding(
                code="invalid_transition_profile",
                field="transition_profile",
                family="schema",
                message=(
                    "transition_profile must be one of: "
                    + ", ".join(sorted(VALID_TRANSITION_VALIDATOR_PROFILES))
                ),
            )
        )

    transition_intent, transition_intent_findings = _transition_packet_optional_string(
        field_name="transition_intent",
        value=packet.get("transition_intent"),
    )
    findings.extend(transition_intent_findings)
    actor_class, actor_class_findings = _transition_packet_optional_string(
        field_name="actor_class",
        value=packet.get("actor_class"),
    )
    findings.extend(actor_class_findings)
    authority_class, authority_class_findings = _transition_packet_optional_string(
        field_name="authority_class",
        value=packet.get("authority_class"),
    )
    findings.extend(authority_class_findings)
    target_artifact_class, target_artifact_class_findings = _transition_packet_optional_string(
        field_name="target_artifact_class",
        value=packet.get("target_artifact_class"),
    )
    findings.extend(target_artifact_class_findings)
    source_artifact_class, source_artifact_class_findings = _transition_packet_optional_string(
        field_name="source_artifact_class",
        value=packet.get("source_artifact_class"),
    )
    findings.extend(source_artifact_class_findings)
    target_scope, target_scope_findings = _transition_packet_optional_string(
        field_name="target_scope",
        value=packet.get("target_scope"),
    )
    findings.extend(target_scope_findings)
    motivating_concern, motivating_concern_findings = _transition_packet_optional_string(
        field_name="motivating_concern",
        value=packet.get("motivating_concern"),
    )
    findings.extend(motivating_concern_findings)
    lineage_root, lineage_root_findings = _transition_packet_optional_string(
        field_name="lineage_root",
        value=packet.get("lineage_root"),
    )
    findings.extend(lineage_root_findings)
    product_graph_root, product_graph_root_findings = _transition_packet_optional_string(
        field_name="product_graph_root",
        value=packet.get("product_graph_root"),
    )
    findings.extend(product_graph_root_findings)
    normalized_title, normalized_title_findings = _transition_packet_optional_string(
        field_name="normalized_title",
        value=packet.get("normalized_title"),
    )
    findings.extend(normalized_title_findings)
    bounded_scope, bounded_scope_findings = _transition_packet_optional_string(
        field_name="bounded_scope",
        value=packet.get("bounded_scope"),
    )
    findings.extend(bounded_scope_findings)

    source_refs, source_ref_findings = _transition_packet_string_list(
        field_name="source_refs",
        value=packet.get("source_refs"),
    )
    findings.extend(source_ref_findings)
    declared_change_surface, declared_change_findings = _transition_packet_string_list(
        field_name="declared_change_surface",
        value=packet.get("declared_change_surface"),
    )
    findings.extend(declared_change_findings)
    required_provenance_links, provenance_link_findings = _transition_packet_string_list(
        field_name="required_provenance_links",
        value=packet.get("required_provenance_links"),
    )
    findings.extend(provenance_link_findings)

    normalized_source_refs = [_normalize_transition_repo_path(item) for item in source_refs]
    normalized_declared_change_surface = [
        _normalize_transition_repo_path(item) for item in declared_change_surface
    ]
    normalized_target_scope = _normalize_transition_repo_path(target_scope)
    normalized_product_graph_root = _normalize_transition_repo_path(product_graph_root)

    return {
        "packet": packet,
        "packet_type": packet_type,
        "transition_profile": transition_profile,
        "transition_intent": transition_intent,
        "source_refs": normalized_source_refs,
        "actor_class": actor_class,
        "authority_class": authority_class,
        "target_artifact_class": target_artifact_class,
        "source_artifact_class": source_artifact_class,
        "target_scope": normalized_target_scope,
        "motivating_concern": motivating_concern,
        "lineage_root": lineage_root,
        "product_graph_root": normalized_product_graph_root,
        "normalized_title": normalized_title,
        "bounded_scope": bounded_scope,
        "declared_change_surface": normalized_declared_change_surface,
        "required_provenance_links": required_provenance_links,
    }, findings


def _validate_transition_packet_schema(context: dict[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    packet_type = str(context.get("packet_type", "")).strip()
    transition_intent = str(context.get("transition_intent", "")).strip()
    if not packet_type:
        findings.append(
            transition_packet_finding(
                code="missing_packet_type",
                field="packet_type",
                family="schema",
                message="packet_type must be declared",
            )
        )
    if not transition_intent:
        findings.append(
            transition_packet_finding(
                code="missing_transition_intent",
                field="transition_intent",
                family="schema",
                message="transition_intent must be a non-empty string",
            )
        )
    if packet_type in TRANSITION_PACKET_TYPE_REQUIRED_FIELDS:
        for field_name in sorted(TRANSITION_PACKET_TYPE_REQUIRED_FIELDS[packet_type]):
            if not str(context.get(field_name, "")).strip():
                findings.append(
                    transition_packet_finding(
                        code="missing_packet_type_required_field",
                        field=field_name,
                        family="schema",
                        message=(f"{field_name} is required for packet_type={packet_type}"),
                    )
                )
    return findings


def _validate_transition_packet_legality(context: dict[str, Any]) -> list[dict[str, str]]:
    packet_type = str(context.get("packet_type", "")).strip()
    transition_profile = str(context.get("transition_profile", "")).strip()
    findings: list[dict[str, str]] = []
    if (
        not packet_type
        or transition_profile not in TRANSITION_VALIDATOR_PROFILE_DEFINITIONS
        or packet_type not in VALID_TRANSITION_PACKET_TYPES
    ):
        return findings
    allowed_packet_types = TRANSITION_VALIDATOR_PROFILE_DEFINITIONS[transition_profile][
        "allowed_packet_types"
    ]
    if packet_type not in allowed_packet_types:
        findings.append(
            transition_packet_finding(
                code="packet_type_not_allowed_for_profile",
                field="packet_type",
                family="legality",
                message=(
                    f"packet_type={packet_type} is not allowed for "
                    f"transition_profile={transition_profile}"
                ),
            )
        )
        return findings

    if packet_type == "promotion":
        if str(context.get("source_artifact_class", "")).strip() != "working_draft":
            findings.append(
                transition_packet_finding(
                    code="promotion_source_must_be_working_draft",
                    field="source_artifact_class",
                    family="legality",
                    message=(
                        "promotion packets must declare source_artifact_class=working_draft "
                        "for draft-to-proposal promotion"
                    ),
                )
            )
        if str(context.get("target_artifact_class", "")).strip() != "reviewable_proposal":
            findings.append(
                transition_packet_finding(
                    code="promotion_target_must_be_reviewable_proposal",
                    field="target_artifact_class",
                    family="legality",
                    message=(
                        "promotion packets must target target_artifact_class=reviewable_proposal"
                    ),
                )
            )
    return findings


def _validate_transition_packet_provenance(context: dict[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    if not context.get("source_refs"):
        findings.append(
            transition_packet_finding(
                code="missing_source_refs",
                field="source_refs",
                family="provenance",
                message="source_refs must be a non-empty list of source artifact references",
            )
        )
    if not context.get("required_provenance_links"):
        findings.append(
            transition_packet_finding(
                code="missing_required_provenance_links",
                field="required_provenance_links",
                family="provenance",
                message=(
                    "required_provenance_links must be a non-empty list of provenance link "
                    "requirements"
                ),
            )
        )
    if not (context.get("motivating_concern") or context.get("lineage_root")):
        findings.append(
            transition_packet_finding(
                code="missing_motivating_concern_or_lineage_root",
                family="provenance",
                message="packet must declare motivating_concern or lineage_root",
            )
        )
    if str(context.get("packet_type", "")).strip() == "promotion":
        required_links = {
            str(item).strip()
            for item in context.get("required_provenance_links", [])
            if str(item).strip()
        }
        if "source_draft_ref" not in required_links:
            findings.append(
                transition_packet_finding(
                    code="promotion_requires_source_draft_ref",
                    field="required_provenance_links",
                    family="provenance",
                    message=(
                        "promotion packets must preserve source_draft_ref in "
                        "required_provenance_links"
                    ),
                )
            )
    return findings


def _validate_transition_packet_boundedness(context: dict[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    if not context.get("declared_change_surface"):
        findings.append(
            transition_packet_finding(
                code="missing_declared_change_surface",
                field="declared_change_surface",
                family="boundedness",
                message=(
                    "declared_change_surface must be a non-empty list describing the intended "
                    "mutation surface"
                ),
            )
        )
    for field_name in ("source_refs", "declared_change_surface", "required_provenance_links"):
        findings.extend(
            _transition_packet_duplicate_list_findings(
                field_name=field_name,
                values=list(context.get(field_name, [])),
                family="boundedness",
            )
        )
    return findings


def _validate_transition_packet_authority(context: dict[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    actor_class = str(context.get("actor_class", "")).strip()
    authority_class = str(context.get("authority_class", "")).strip()
    if not (actor_class or authority_class):
        findings.append(
            transition_packet_finding(
                code="missing_actor_or_authority_class",
                family="authority",
                message="packet must declare actor_class or authority_class",
            )
        )
    if str(context.get("packet_type", "")).strip() == "apply" and not authority_class:
        findings.append(
            transition_packet_finding(
                code="apply_requires_authority_class",
                field="authority_class",
                family="authority",
                message="apply packets must declare authority_class",
            )
        )
    return findings


def _validate_transition_packet_reconciliation(context: dict[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    target_artifact_class = str(context.get("target_artifact_class", "")).strip()
    target_scope = str(context.get("target_scope", "")).strip()
    declared_change_surface = list(context.get("declared_change_surface", []))
    if not (target_artifact_class or target_scope):
        findings.append(
            transition_packet_finding(
                code="missing_target_binding",
                family="reconciliation",
                message="packet must declare target_artifact_class or target_scope",
            )
        )
    if target_scope and _looks_like_repo_path(target_scope):
        normalized_surface = {
            PurePosixPath(item).as_posix() if _looks_like_repo_path(item) else item
            for item in declared_change_surface
        }
        if PurePosixPath(target_scope).as_posix() not in normalized_surface:
            findings.append(
                transition_packet_finding(
                    code="target_scope_outside_declared_change_surface",
                    field="target_scope",
                    family="reconciliation",
                    message="target_scope must be included in declared_change_surface",
                )
            )
        return findings
    return findings


def _validate_transition_packet_diff_scope(context: dict[str, Any]) -> list[dict[str, str]]:
    findings: list[dict[str, str]] = []
    for field_name in ("source_refs", "declared_change_surface"):
        for value in context.get(field_name, []):
            findings.extend(
                _validate_transition_surface_path(
                    field_name=field_name,
                    value=value,
                )
            )
    findings.extend(
        _validate_transition_surface_path(
            field_name="target_scope",
            value=str(context.get("target_scope", "")).strip(),
        )
    )
    findings.extend(
        _validate_transition_surface_path(
            field_name="product_graph_root",
            value=str(context.get("product_graph_root", "")).strip(),
        )
    )
    return findings


def _transition_path_within_root(path_text: str, root_text: str) -> bool:
    normalized_path = _normalize_transition_repo_path(path_text).rstrip("/")
    normalized_root = _normalize_transition_repo_path(root_text).rstrip("/")
    if not normalized_path or not normalized_root:
        return False
    return normalized_path == normalized_root or normalized_path.startswith(normalized_root + "/")


def _transition_path_matches_any_prefix(path_text: str, prefixes: list[str]) -> bool:
    normalized_path = _normalize_transition_repo_path(path_text).rstrip("/")
    for prefix in prefixes:
        normalized_prefix = _normalize_transition_repo_path(prefix).rstrip("/")
        if not normalized_prefix:
            continue
        if normalized_path == normalized_prefix or normalized_path.startswith(
            normalized_prefix + "/"
        ):
            return True
    return False


def _validate_transition_packet_profile(context: dict[str, Any]) -> list[dict[str, str]]:
    transition_profile = str(context.get("transition_profile", "")).strip()
    packet_type = str(context.get("packet_type", "")).strip()
    declared_change_surface = list(context.get("declared_change_surface", []))
    findings: list[dict[str, str]] = []

    if transition_profile == "specgraph_core":
        canonical_surface_hits = [
            path
            for path in declared_change_surface
            if any(path.startswith(prefix) for prefix in SPECGRAPH_CANONICAL_SURFACE_PREFIXES)
        ]
        if packet_type in {"promotion", "proposal"} and canonical_surface_hits:
            findings.append(
                transition_packet_finding(
                    code="profile_forbidden_canonical_mutation_surface",
                    field="declared_change_surface",
                    family="profile",
                    profile=transition_profile,
                    message=(
                        "specgraph_core promotion/proposal packets may not declare canonical "
                        "spec mutation surfaces; use an apply packet for canonical writeback"
                    ),
                )
            )
        if packet_type == "apply" and any(
            ref.startswith("docs/proposals_drafts/") for ref in context.get("source_refs", [])
        ):
            findings.append(
                transition_packet_finding(
                    code="profile_apply_requires_reviewable_source",
                    field="source_refs",
                    family="profile",
                    profile=transition_profile,
                    message=(
                        "specgraph_core apply packets must source from reviewable proposal or "
                        "run artifacts, not raw proposal drafts"
                    ),
                )
            )
    if transition_profile == "product_spec":
        policy, policy_findings = load_product_spec_transition_policy_report()
        findings.extend(policy_findings)
        if policy is None:
            return findings

        product_graph_root = str(context.get("product_graph_root", "")).strip()
        required_binding_fields = [
            str(item).strip()
            for item in policy.get("required_binding_fields", [])
            if str(item).strip()
        ]
        if "product_graph_root" in required_binding_fields and not product_graph_root:
            findings.append(
                transition_packet_finding(
                    code="profile_missing_product_graph_root",
                    field="product_graph_root",
                    family="profile",
                    profile=transition_profile,
                    message=(
                        "product_spec packets must declare product_graph_root so product graphs "
                        "inherit one shared transition engine without redefining packet semantics"
                    ),
                )
            )
            return findings

        if product_graph_root:
            forbidden_source_prefixes = [
                str(item).strip()
                for item in policy.get("forbidden_source_prefixes", [])
                if str(item).strip()
            ]
            if packet_type == "apply" and any(
                _looks_like_repo_path(path)
                and _transition_path_matches_any_prefix(path, forbidden_source_prefixes)
                for path in context.get("source_refs", [])
            ):
                findings.append(
                    transition_packet_finding(
                        code="profile_apply_requires_reviewable_source",
                        field="source_refs",
                        family="profile",
                        profile=transition_profile,
                        message=(
                            "product_spec apply packets must source from reviewable proposal or "
                            "run artifacts, not raw drafts"
                        ),
                    )
                )

            required_provenance_links = {
                str(item).strip()
                for item in context.get("required_provenance_links", [])
                if str(item).strip()
            }
            for required_link in (
                str(item).strip()
                for item in policy.get("required_provenance_links", [])
                if str(item).strip()
            ):
                if required_link not in required_provenance_links:
                    findings.append(
                        transition_packet_finding(
                            code="profile_missing_required_product_provenance_link",
                            field="required_provenance_links",
                            family="profile",
                            profile=transition_profile,
                            message=(
                                "product_spec packets must preserve inherited provenance link: "
                                f"{required_link}"
                            ),
                        )
                    )

            reviewable_source_prefixes = [
                str(item).strip()
                for item in policy.get("reviewable_source_prefixes", [])
                if str(item).strip()
            ]
            if packet_type == "apply" and not any(
                _looks_like_repo_path(path)
                and _transition_path_matches_any_prefix(path, reviewable_source_prefixes)
                for path in context.get("source_refs", [])
            ):
                findings.append(
                    transition_packet_finding(
                        code="profile_apply_requires_reviewable_source",
                        field="source_refs",
                        family="profile",
                        profile=transition_profile,
                        message=(
                            "product_spec apply packets must inherit from reviewable proposal or "
                            "run artifacts before mutating a product graph"
                        ),
                    )
                )

            if (
                packet_type == "apply"
                and str(policy.get("apply_scope_rule", "")).strip() == "inside_product_graph_root"
            ):
                scoped_paths = [
                    path
                    for path in [
                        *context.get("declared_change_surface", []),
                        str(context.get("target_scope", "")).strip(),
                    ]
                    if str(path).strip() and _looks_like_repo_path(str(path).strip())
                ]
                outside_root = [
                    path
                    for path in scoped_paths
                    if not _transition_path_within_root(str(path), product_graph_root)
                ]
                if outside_root:
                    findings.append(
                        transition_packet_finding(
                            code="profile_apply_scope_outside_product_graph_root",
                            field="declared_change_surface",
                            family="profile",
                            profile=transition_profile,
                            message=(
                                "product_spec apply surfaces must remain inside "
                                "product_graph_root; "
                                f"outside paths: {', '.join(sorted(set(outside_root)))}"
                            ),
                        )
                    )
    return findings


def validate_transition_packet_report(
    packet: Any,
    *,
    validator_profile: str | None = None,
) -> dict[str, Any]:
    """Build a structured validation report for one normalized transition packet."""

    context, findings = _normalize_transition_packet_context(
        packet,
        validator_profile=validator_profile,
    )
    if not context:
        return {
            "ok": False,
            "packet_type": "",
            "packet_family": "",
            "packet_family_definition": {},
            "transition_profile": validator_profile or DEFAULT_TRANSITION_VALIDATOR_PROFILE,
            "validator_profile_definition": {},
            "proposal_promotion_policy_definition": {},
            "families_checked": list(TRANSITION_CHECK_FAMILIES),
            "finding_count": len(findings),
            "findings_by_family": {"schema": len(findings)},
            "findings": findings,
        }

    family_validators = {
        "schema": _validate_transition_packet_schema,
        "legality": _validate_transition_packet_legality,
        "provenance": _validate_transition_packet_provenance,
        "boundedness": _validate_transition_packet_boundedness,
        "authority": _validate_transition_packet_authority,
        "reconciliation": _validate_transition_packet_reconciliation,
        "diff_scope": _validate_transition_packet_diff_scope,
        "profile": _validate_transition_packet_profile,
    }
    for family in TRANSITION_CHECK_FAMILIES:
        findings.extend(family_validators[family](context))

    findings_by_family: dict[str, int] = {}
    for finding in findings:
        family = str(finding.get("family", "schema")).strip() or "schema"
        findings_by_family[family] = findings_by_family.get(family, 0) + 1

    packet_type = str(context.get("packet_type", "")).strip()
    transition_profile = str(context.get("transition_profile", "")).strip()
    product_spec_policy_definition = {}
    proposal_promotion_policy_definition = {}
    if transition_profile == "product_spec":
        policy, _findings = load_product_spec_transition_policy_report()
        if policy is not None:
            product_spec_policy_definition = policy
    if packet_type == "promotion":
        policy, _findings = load_proposal_promotion_policy_report()
        if policy is not None:
            proposal_promotion_policy_definition = policy
    return {
        "ok": not findings,
        "packet_type": packet_type,
        "packet_family": packet_type,
        "packet_family_definition": TRANSITION_PACKET_FAMILY_DEFINITIONS.get(packet_type, {}),
        "transition_profile": transition_profile,
        "validator_profile_definition": TRANSITION_VALIDATOR_PROFILE_DEFINITIONS.get(
            transition_profile, {}
        ),
        "product_spec_policy_definition": product_spec_policy_definition,
        "proposal_promotion_policy_definition": proposal_promotion_policy_definition,
        "families_checked": list(TRANSITION_CHECK_FAMILIES),
        "finding_count": len(findings),
        "findings_by_family": findings_by_family,
        "findings": findings,
    }


def validate_transition_packet(
    packet: Any,
    *,
    validator_profile: str | None = None,
) -> list[dict[str, str]]:
    """Validate one normalized transition packet.

    This validator is intentionally structural. It checks bounded transition
    legality and does not attempt to judge semantic quality.
    """

    return validate_transition_packet_report(
        packet,
        validator_profile=validator_profile,
    )["findings"]


def validate_transition_packet_file(
    path: Path,
    *,
    validator_profile: str | None = None,
) -> dict[str, Any]:
    packet, packet_error = load_json_object_report(path, artifact_kind="transition packet")
    if packet is None:
        findings = [
            transition_packet_finding(
                code="invalid_packet_file",
                field="path",
                family="schema",
                message=packet_error or "packet file must exist and contain a JSON object",
            )
        ]
        return {
            "ok": False,
            "path": path.as_posix(),
            "packet_type": "",
            "packet_family": "",
            "packet_family_definition": {},
            "transition_profile": validator_profile or DEFAULT_TRANSITION_VALIDATOR_PROFILE,
            "validator_profile_definition": {},
            "families_checked": list(TRANSITION_CHECK_FAMILIES),
            "finding_count": len(findings),
            "findings_by_family": {"schema": len(findings)},
            "findings": findings,
        }
    report = validate_transition_packet_report(
        packet,
        validator_profile=validator_profile,
    )
    report["path"] = path.as_posix()
    return report


def spec_trace_index_path() -> Path:
    return RUNS_DIR / SPEC_TRACE_INDEX_FILENAME


def spec_trace_projection_path() -> Path:
    return RUNS_DIR / SPEC_TRACE_PROJECTION_FILENAME


def spec_trace_registry_path() -> Path:
    return ROOT / "tools" / "spec_trace_registry.json"


def load_spec_trace_registry() -> dict[str, dict[str, Any]]:
    path = spec_trace_registry_path()
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise RuntimeError(
            f"failed to read spec trace registry: {path.as_posix()} ({exc})"
        ) from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"malformed spec trace registry: {path.as_posix()} ({exc})") from exc
    if not isinstance(payload, list):
        raise RuntimeError(
            f"malformed spec trace registry: {path.as_posix()} must contain a JSON list"
        )

    registry: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            raise RuntimeError(
                "malformed spec trace registry: "
                f"entry {index} in {path.as_posix()} must be an object"
            )
        spec_id = str(item.get("spec_id", "")).strip()
        if not spec_id:
            raise RuntimeError(
                f"malformed spec trace registry: entry {index} in {path.as_posix()} missing spec_id"
            )
        registry[spec_id] = item
    return registry


def trace_surface_matches(path_text: str, surface: str) -> bool:
    normalized_path = PurePosixPath(path_text)
    normalized_surface = surface.strip()
    if not normalized_surface:
        return False
    if normalized_surface == path_text:
        return True
    if any(marker in normalized_surface for marker in ("*", "?", "[")):
        return normalized_path.match(normalized_surface)
    return path_text.startswith(normalized_surface.rstrip("/") + "/")


def declared_trace_surfaces(entry: dict[str, Any], field: str) -> list[str]:
    raw_value = entry.get(field, [])
    if not isinstance(raw_value, list):
        return []
    return [str(item).strip() for item in raw_value if str(item).strip()]


def matching_trace_refs(
    refs: list[dict[str, Any]],
    declared_surfaces: list[str],
) -> list[dict[str, Any]]:
    if not declared_surfaces:
        return []
    matched: list[dict[str, Any]] = []
    for ref in refs:
        path_text = str(ref.get("path", "")).strip()
        if not path_text:
            continue
        if any(trace_surface_matches(path_text, surface) for surface in declared_surfaces):
            matched.append(ref)
    return matched


def trace_ref_paths(refs: list[dict[str, Any]]) -> list[str]:
    return sorted(
        {str(ref.get("path", "")).strip() for ref in refs if str(ref.get("path", "")).strip()}
    )


def trace_surface_commit_paths(declared_surfaces: list[str]) -> list[str]:
    paths: set[str] = set()
    for surface in declared_surfaces:
        normalized = str(surface).strip()
        if not normalized:
            continue
        if any(marker in normalized for marker in ("*", "?", "[")):
            matches = list(ROOT.glob(normalized))
            if not matches:
                paths.add(normalized)
                continue
            for match in matches:
                if match.is_file():
                    paths.add(match.relative_to(ROOT).as_posix())
                elif match.is_dir():
                    paths.add(match.relative_to(ROOT).as_posix())
            continue
        paths.add(normalized)
    return sorted(paths)


def blocked_trace_dependencies(spec: SpecNode, index: dict[str, SpecNode]) -> list[str]:
    blocked: list[str] = []
    for dep_id in spec.depends_on:
        dep = index.get(dep_id)
        if (
            dep is None
            or dep.status not in READY_DEP_STATUSES
            or dep.gate_state in BLOCKING_GATE_STATES
        ):
            blocked.append(dep_id)
    return blocked


def latest_trace_commit_ref(
    ref_paths: list[str],
    *,
    repo_root: Path | None = None,
) -> dict[str, str] | None:
    latest_refs = collect_trace_commit_refs(ref_paths, repo_root=repo_root, limit=1)
    if not latest_refs:
        return None
    return latest_refs[0]


def iso_datetime_text(value: dt.datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt.timezone.utc)
    return value.isoformat().replace("+00:00", "Z")


def derive_implementation_state(
    spec: SpecNode,
    *,
    trace_contract: dict[str, Any] | None,
    matched_code_refs: list[dict[str, Any]],
    matched_test_refs: list[dict[str, Any]],
    changed_paths: set[str],
    spec_index: dict[str, SpecNode],
) -> dict[str, Any]:
    available_statuses = [
        "unclaimed",
        "planned",
        "in_progress",
        "implemented",
        "verified",
        "blocked",
        "drifted",
    ]
    if trace_contract is None:
        return {
            "status": "unclaimed",
            "confidence": "weak",
            "available_statuses": available_statuses,
            "basis": (
                "No explicit trace contract is registered for this spec. Weak mentions alone do "
                "not claim embodiment."
            ),
        }

    blocked_dependencies = blocked_trace_dependencies(spec, spec_index)
    if spec.gate_state in BLOCKING_GATE_STATES or blocked_dependencies:
        return {
            "status": "blocked",
            "confidence": "strong",
            "available_statuses": available_statuses,
            "basis": (
                "Trace contract exists, but implementation is blocked by review or dependency "
                "state."
            ),
            "blocked_dependencies": blocked_dependencies,
            "blocking_gate_state": (
                spec.gate_state if spec.gate_state in BLOCKING_GATE_STATES else "none"
            ),
        }

    tracked_surfaces = [
        *trace_contract["declared_code_surfaces"],
        *trace_contract["declared_test_surfaces"],
    ]
    if changed_paths and any(
        any(trace_surface_matches(path_text, surface) for surface in tracked_surfaces)
        for path_text in changed_paths
    ):
        return {
            "status": "in_progress",
            "confidence": "strong",
            "available_statuses": available_statuses,
            "basis": "Tracked implementation surfaces currently have local changes.",
        }

    if not matched_code_refs and not matched_test_refs:
        return {
            "status": "planned",
            "confidence": "strong",
            "available_statuses": available_statuses,
            "basis": (
                "Trace contract is declared, but no matching implementation anchors are observed "
                "yet."
            ),
        }

    if matched_code_refs and matched_test_refs:
        return {
            "status": "verified",
            "confidence": "strong",
            "available_statuses": available_statuses,
            "basis": "Declared code and test surfaces are both observed for this spec.",
        }

    return {
        "status": "implemented",
        "confidence": "strong",
        "available_statuses": available_statuses,
        "basis": (
            "Declared implementation anchors are observed, but verification anchors are incomplete."
        ),
    }


def derive_trace_freshness(
    spec: SpecNode,
    *,
    preliminary_state: dict[str, Any],
    trace_contract: dict[str, Any] | None,
    matched_test_refs: list[dict[str, Any]],
    latest_code_commit_ref: dict[str, str] | None,
    latest_test_commit_ref: dict[str, str] | None,
) -> dict[str, Any]:
    available_statuses = [
        "not_tracked",
        "not_applicable",
        "dirty_worktree",
        "pending_verification",
        "verification_time_unknown",
        "fresh",
        "stale_spec",
        "drifted_after_verification",
    ]
    preliminary_status = str(preliminary_state.get("status", "")).strip()
    spec_updated_at = parse_iso_datetime(spec.data.get("updated_at", ""))
    latest_code_change_at = parse_iso_datetime(
        latest_code_commit_ref.get("committed_at", "") if latest_code_commit_ref else ""
    )
    latest_test_change_at = parse_iso_datetime(
        latest_test_commit_ref.get("committed_at", "") if latest_test_commit_ref else ""
    )

    common = {
        "available_statuses": available_statuses,
        "spec_updated_at": iso_datetime_text(spec_updated_at),
        "latest_code_change_at": iso_datetime_text(latest_code_change_at),
        "latest_test_change_at": iso_datetime_text(latest_test_change_at),
        "trusted_verification_at": iso_datetime_text(latest_test_change_at),
    }

    if trace_contract is None:
        return {
            "status": "not_tracked",
            "confidence": "weak",
            "basis": "No explicit trace contract is registered for this spec.",
            **common,
        }

    if preliminary_status in {"unclaimed", "planned", "blocked"}:
        return {
            "status": "not_applicable",
            "confidence": "strong",
            "basis": (
                "Freshness is not yet meaningful because implementation embodiment is not "
                "currently in a verified or active state."
            ),
            **common,
        }

    if preliminary_status == "in_progress":
        return {
            "status": "dirty_worktree",
            "confidence": "strong",
            "basis": (
                "Tracked implementation surfaces currently have local changes, so any previous "
                "verification snapshot is stale until the worktree settles."
            ),
            **common,
        }

    if not matched_test_refs:
        return {
            "status": "pending_verification",
            "confidence": "strong",
            "basis": (
                "No matched verification anchors are observed for the declared trace contract."
            ),
            **common,
        }

    if latest_test_change_at is None:
        return {
            "status": "verification_time_unknown",
            "confidence": "weak",
            "basis": (
                "Matched verification anchors exist, but commit history did not yield a trusted "
                "verification timestamp."
            ),
            **common,
        }

    if spec_updated_at is not None and spec_updated_at > latest_test_change_at:
        return {
            "status": "stale_spec",
            "confidence": "strong",
            "basis": (
                "The governing spec was updated after the latest trusted verification anchor."
            ),
            **common,
        }

    if latest_code_change_at is not None and latest_code_change_at > latest_test_change_at:
        return {
            "status": "drifted_after_verification",
            "confidence": "strong",
            "basis": (
                "Declared implementation surfaces changed after the latest trusted verification "
                "anchor."
            ),
            **common,
        }

    return {
        "status": "fresh",
        "confidence": "strong",
        "basis": (
            "Declared verification anchors are at least as recent as traced implementation "
            "surfaces and the spec itself."
        ),
        **common,
    }


def apply_trace_freshness_to_implementation_state(
    implementation_state: dict[str, Any],
    freshness: dict[str, Any],
) -> dict[str, Any]:
    adjusted = copy.deepcopy(implementation_state)
    freshness_status = str(freshness.get("status", "")).strip()
    adjusted["freshness_status"] = freshness_status
    if (
        str(adjusted.get("status", "")).strip() == "verified"
        and freshness_status == "drifted_after_verification"
    ):
        adjusted["status"] = "drifted"
        adjusted["basis"] = (
            "Declared code and verification anchors were observed, but implementation changed "
            "after the last trusted verification."
        )
    return adjusted


def collect_spec_trace_mentions(
    base_dirs: tuple[Path, ...] | None = None,
) -> dict[str, dict[str, list[dict[str, Any]]]]:
    if base_dirs is None:
        base_dirs = (ROOT / "tools", ROOT / "tests")
    field_by_dir = {
        "tools": "code_refs",
        "tests": "test_refs",
    }
    mentions: dict[str, dict[str, list[dict[str, Any]]]] = {}
    for base_dir in base_dirs:
        if not base_dir.exists():
            continue
        field_name = field_by_dir.get(base_dir.name, f"{base_dir.name}_refs")
        for path in sorted(base_dir.rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except OSError:
                continue
            relpath = path.relative_to(ROOT).as_posix()
            for lineno, line in enumerate(lines, start=1):
                for spec_id in sorted(set(SPEC_ID_CANONICAL_RE.findall(line))):
                    bucket = mentions.setdefault(spec_id, {"code_refs": [], "test_refs": []})
                    bucket.setdefault(field_name, []).append(
                        {
                            "path": relpath,
                            "line": lineno,
                        }
                    )
    return mentions


def collect_trace_commit_refs(
    ref_paths: list[str],
    *,
    repo_root: Path | None = None,
    limit: int = 5,
) -> list[dict[str, str]]:
    local_root = repo_root or ROOT
    unique_paths = [path for path in sorted(set(ref_paths)) if str(path).strip()]
    if limit <= 0 or not unique_paths or shutil.which("git") is None:
        return []

    probe = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=local_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if probe.returncode != 0 or probe.stdout.strip() != "true":
        return []

    result = subprocess.run(
        ["git", "log", f"--max-count={limit}", "--format=%H%x09%cI%x09%s", "--", *unique_paths],
        cwd=local_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []

    commit_refs: list[dict[str, str]] = []
    seen_shas: set[str] = set()
    for line in result.stdout.splitlines():
        sha, separator, remainder = line.partition("\t")
        if not separator or not sha or sha in seen_shas:
            continue
        committed_at, separator, subject = remainder.partition("\t")
        if not separator:
            continue
        seen_shas.add(sha)
        commit_refs.append(
            {
                "sha": sha,
                "short_sha": sha[:7],
                "committed_at": committed_at.strip(),
                "subject": subject.strip(),
            }
        )
        if len(commit_refs) >= limit:
            break
    return commit_refs


def collect_trace_pr_refs(commit_refs: list[dict[str, str]]) -> list[dict[str, Any]]:
    pr_refs: list[dict[str, Any]] = []
    seen_numbers: set[int] = set()
    for commit_ref in commit_refs:
        subject = str(commit_ref.get("subject", "")).strip()
        for match in PR_NUMBER_FROM_SUBJECT_RE.finditer(subject):
            number = int(match.group("number"))
            if number in seen_numbers:
                continue
            seen_numbers.add(number)
            pr_refs.append(
                {
                    "number": number,
                    "source": "commit_subject",
                    "commit": str(commit_ref.get("short_sha", "")).strip(),
                }
            )
    return pr_refs


def acceptance_criteria_count(spec: SpecNode) -> int:
    acceptance = spec.data.get("acceptance", [])
    if not isinstance(acceptance, list):
        return 0
    return len([item for item in acceptance if str(item).strip()])


def derive_trace_verification_basis(
    code_refs: list[dict[str, Any]],
    test_refs: list[dict[str, Any]],
    commit_refs: list[dict[str, str]],
) -> dict[str, Any]:
    if test_refs:
        return {
            "status": "test_linked",
            "basis_kinds": ["test_refs", "commit_history"] if commit_refs else ["test_refs"],
            "basis_ref_count": len(test_refs) + len(commit_refs),
            "notes": [
                (
                    "Verification is weakly grounded by linked tests that mention the spec id. "
                    "Criterion-level mapping is not yet encoded in the trace plane."
                )
            ],
        }
    if code_refs:
        return {
            "status": "code_linked_without_tests",
            "basis_kinds": ["code_refs", "commit_history"] if commit_refs else ["code_refs"],
            "basis_ref_count": len(code_refs) + len(commit_refs),
            "notes": [
                "Implementation anchors exist, but no linked tests currently mention the spec id."
            ],
        }
    return {
        "status": "unlinked",
        "basis_kinds": [],
        "basis_ref_count": 0,
        "notes": ["No code or test references currently mention this spec id."],
    }


def derive_acceptance_coverage(
    spec: SpecNode,
    *,
    test_refs: list[dict[str, Any]],
) -> dict[str, Any]:
    criterion_count = acceptance_criteria_count(spec)
    if criterion_count <= 0:
        return {
            "status": "not_defined",
            "criterion_count": 0,
            "mapped_criterion_count": 0,
            "evidence_ref_count": len(test_refs),
            "confidence": "none",
            "basis": "The spec does not define acceptance criteria to map.",
        }
    if test_refs:
        return {
            "status": "evidence_linked_unmapped",
            "criterion_count": criterion_count,
            "mapped_criterion_count": 0,
            "evidence_ref_count": len(test_refs),
            "confidence": "weak",
            "basis": (
                "Linked tests mention the spec id, but the first trace index does not yet map "
                "individual acceptance criteria to verification evidence."
            ),
        }
    return {
        "status": "no_linked_evidence",
        "criterion_count": criterion_count,
        "mapped_criterion_count": 0,
        "evidence_ref_count": 0,
        "confidence": "none",
        "basis": "No linked tests currently mention the spec id.",
    }


def trace_strength_for_refs(
    code_refs: list[dict[str, Any]],
    test_refs: list[dict[str, Any]],
) -> str:
    if code_refs and test_refs:
        return "code_and_tests"
    if code_refs:
        return "code_only"
    if test_refs:
        return "tests_only"
    return "unobserved"


def build_spec_trace_index(specs: list[SpecNode]) -> dict[str, Any]:
    mentions = collect_spec_trace_mentions()
    registry = load_spec_trace_registry()
    changed_paths = set(git_status_changed_files(ROOT))
    known_ids = {spec.id for spec in specs}
    spec_index = index_specs(specs)
    entries: list[dict[str, Any]] = []
    for spec in sorted(specs, key=lambda item: item.id):
        bucket = mentions.get(spec.id, {})
        code_refs = list(bucket.get("code_refs", []))
        test_refs = list(bucket.get("test_refs", []))
        registry_entry = registry.get(spec.id)
        declared_code_surfaces = (
            declared_trace_surfaces(registry_entry, "code_surfaces") if registry_entry else []
        )
        declared_test_surfaces = (
            declared_trace_surfaces(registry_entry, "test_surfaces") if registry_entry else []
        )
        matched_code_refs = matching_trace_refs(code_refs, declared_code_surfaces)
        matched_test_refs = matching_trace_refs(test_refs, declared_test_surfaces)
        latest_code_commit_ref = latest_trace_commit_ref(
            trace_surface_commit_paths(declared_code_surfaces)
        )
        latest_test_commit_ref = latest_trace_commit_ref(
            trace_surface_commit_paths(declared_test_surfaces)
        )
        commit_refs = collect_trace_commit_refs(
            [str(ref.get("path", "")).strip() for ref in [*code_refs, *test_refs]]
        )
        pr_refs = collect_trace_pr_refs(commit_refs)
        verification_basis = derive_trace_verification_basis(code_refs, test_refs, commit_refs)
        acceptance_coverage = derive_acceptance_coverage(spec, test_refs=test_refs)
        trace_strength = trace_strength_for_refs(code_refs, test_refs)
        trace_contract = None
        if registry_entry is not None:
            trace_contract = {
                "source": "registry",
                "declared_code_surfaces": declared_code_surfaces,
                "declared_test_surfaces": declared_test_surfaces,
                "matched_code_paths": trace_ref_paths(matched_code_refs),
                "matched_test_paths": trace_ref_paths(matched_test_refs),
                "matched_code_ref_count": len(matched_code_refs),
                "matched_test_ref_count": len(matched_test_refs),
            }
        preliminary_implementation_state = derive_implementation_state(
            spec,
            trace_contract=trace_contract,
            matched_code_refs=matched_code_refs,
            matched_test_refs=matched_test_refs,
            changed_paths=changed_paths,
            spec_index=spec_index,
        )
        freshness = derive_trace_freshness(
            spec,
            preliminary_state=preliminary_implementation_state,
            trace_contract=trace_contract,
            matched_test_refs=matched_test_refs,
            latest_code_commit_ref=latest_code_commit_ref,
            latest_test_commit_ref=latest_test_commit_ref,
        )
        implementation_state = apply_trace_freshness_to_implementation_state(
            preliminary_implementation_state,
            freshness,
        )
        entries.append(
            {
                "spec_id": spec.id,
                "title": spec.title,
                "code_refs": code_refs,
                "test_refs": test_refs,
                "commit_refs": commit_refs,
                "pr_refs": pr_refs,
                "trace_contract": trace_contract,
                "implementation_state": implementation_state,
                "freshness": freshness,
                "verification_basis": verification_basis,
                "acceptance_coverage": acceptance_coverage,
                "trace_summary": {
                    "code_ref_count": len(code_refs),
                    "test_ref_count": len(test_refs),
                    "commit_ref_count": len(commit_refs),
                    "pr_ref_count": len(pr_refs),
                    "trace_strength": trace_strength,
                },
            }
        )
    unknown_spec_mentions = [
        {
            "spec_id": spec_id,
            "code_refs": list(mentions[spec_id].get("code_refs", [])),
            "test_refs": list(mentions[spec_id].get("test_refs", [])),
        }
        for spec_id in sorted(set(mentions) - known_ids)
    ]
    return {
        "artifact_kind": "spec_trace_index",
        "schema_version": 4,
        "implementation_state_model": {
            "derivation_mode": "registry_backed_conservative_overlay",
            "available_statuses": [
                "unclaimed",
                "planned",
                "in_progress",
                "implemented",
                "verified",
                "blocked",
                "drifted",
            ],
            "notes": [
                (
                    "Only explicit registry-backed trace contracts may promote a spec beyond "
                    "unclaimed. Weak mentions remain observational context."
                ),
                (
                    "Freshness-aware derivation may keep a node verified but stale when the spec "
                    "moves beyond the latest trusted verification, or mark it drifted when code "
                    "moves beyond that verification."
                ),
            ],
        },
        "freshness_model": {
            "available_statuses": [
                "not_tracked",
                "not_applicable",
                "dirty_worktree",
                "pending_verification",
                "verification_time_unknown",
                "fresh",
                "stale_spec",
                "drifted_after_verification",
            ],
            "notes": [
                (
                    "Freshness is derived only from registry-backed surfaces plus weak git "
                    "timestamps; it does not yet provide criterion-level verification mapping."
                )
            ],
        },
        "generated_at": utc_now_iso(),
        "source_dirs": ["tools", "tests"],
        "registry_path": spec_trace_registry_path().relative_to(ROOT).as_posix(),
        "entries": entries,
        "entry_count": len(entries),
        "unknown_spec_mentions": unknown_spec_mentions,
    }


def write_spec_trace_index(index: dict[str, Any]) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = spec_trace_index_path()
    with artifact_lock(path):
        atomic_write_json(path, index)
    return path


def build_spec_trace_projection(index: dict[str, Any]) -> dict[str, Any]:
    entries = list(index.get("entries", []))

    implementation_groups: dict[str, list[str]] = {}
    freshness_groups: dict[str, list[str]] = {}
    acceptance_groups: dict[str, list[str]] = {}
    named_filters = {
        "missing_trace_contract": [],
        "planned_without_anchors": [],
        "implementation_in_progress": [],
        "implemented_without_verification": [],
        "verified_fresh": [],
        "verified_stale_spec": [],
        "drifted": [],
        "blocked": [],
        "acceptance_gap": [],
    }
    backlog_items: list[dict[str, Any]] = []

    for entry in entries:
        spec_id = str(entry.get("spec_id", "")).strip()
        title = str(entry.get("title", "")).strip()
        implementation_state = entry.get("implementation_state", {})
        freshness = entry.get("freshness", {})
        acceptance_coverage = entry.get("acceptance_coverage", {})
        impl_status = str(implementation_state.get("status", "unknown")).strip() or "unknown"
        freshness_status = str(freshness.get("status", "unknown")).strip() or "unknown"
        acceptance_status = str(acceptance_coverage.get("status", "unknown")).strip() or "unknown"

        implementation_groups.setdefault(impl_status, []).append(spec_id)
        freshness_groups.setdefault(freshness_status, []).append(spec_id)
        acceptance_groups.setdefault(acceptance_status, []).append(spec_id)

        next_gap = "none"
        if impl_status == "unclaimed":
            named_filters["missing_trace_contract"].append(spec_id)
            next_gap = "attach_trace_contract"
        elif impl_status == "planned":
            named_filters["planned_without_anchors"].append(spec_id)
            next_gap = "materialize_declared_surfaces"
        elif impl_status == "in_progress":
            named_filters["implementation_in_progress"].append(spec_id)
        elif impl_status == "implemented":
            named_filters["implemented_without_verification"].append(spec_id)
            next_gap = "add_verification_anchors"
        elif impl_status == "verified" and freshness_status == "fresh":
            named_filters["verified_fresh"].append(spec_id)
        elif impl_status == "verified" and freshness_status == "stale_spec":
            named_filters["verified_stale_spec"].append(spec_id)
            next_gap = "refresh_after_spec_update"
        elif impl_status == "drifted":
            named_filters["drifted"].append(spec_id)
            next_gap = "reverify_after_drift"
        elif impl_status == "blocked":
            named_filters["blocked"].append(spec_id)
            next_gap = "clear_blocking_dependency"

        if (
            next_gap == "none"
            and impl_status in {"implemented", "verified", "drifted"}
            and acceptance_status != "not_defined"
            and acceptance_status != "covered"
        ):
            named_filters["acceptance_gap"].append(spec_id)
            if acceptance_status == "no_linked_evidence":
                next_gap = "link_acceptance_evidence"
            elif acceptance_status == "evidence_linked_unmapped":
                next_gap = "map_acceptance_evidence"

        if next_gap != "none":
            backlog_items.append(
                {
                    "spec_id": spec_id,
                    "title": title,
                    "implementation_state": impl_status,
                    "freshness_status": freshness_status,
                    "acceptance_coverage_status": acceptance_status,
                    "next_gap": next_gap,
                }
            )

    grouped_backlog: dict[str, list[str]] = {}
    for item in backlog_items:
        grouped_backlog.setdefault(str(item["next_gap"]), []).append(str(item["spec_id"]))

    return {
        "artifact_kind": "spec_trace_projection",
        "schema_version": 1,
        "generated_at": utc_now_iso(),
        "source_trace_index": spec_trace_index_path().relative_to(ROOT).as_posix(),
        "source_trace_generated_at": index.get("generated_at"),
        "entry_count": len(entries),
        "viewer_projection": {
            "implementation_state": {
                key: sorted(value) for key, value in sorted(implementation_groups.items())
            },
            "freshness": {key: sorted(value) for key, value in sorted(freshness_groups.items())},
            "acceptance_coverage": {
                key: sorted(value) for key, value in sorted(acceptance_groups.items())
            },
            "named_filters": {key: sorted(value) for key, value in sorted(named_filters.items())},
        },
        "implementation_backlog": {
            "entry_count": len(backlog_items),
            "items": backlog_items,
            "grouped_by_next_gap": {
                key: sorted(value) for key, value in sorted(grouped_backlog.items())
            },
        },
    }


def write_spec_trace_projection(projection: dict[str, Any]) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = spec_trace_projection_path()
    with artifact_lock(path):
        atomic_write_json(path, projection)
    return path


def proposal_runtime_registry_path() -> Path:
    return ROOT / "tools" / "proposal_runtime_registry.json"


def proposal_promotion_registry_path() -> Path:
    return ROOT / "tools" / "proposal_promotion_registry.json"


def proposal_runtime_index_path() -> Path:
    return RUNS_DIR / PROPOSAL_RUNTIME_INDEX_FILENAME


def proposal_promotion_index_path() -> Path:
    return RUNS_DIR / PROPOSAL_PROMOTION_INDEX_FILENAME


def proposal_docs_dir() -> Path:
    return ROOT / "docs" / "proposals"


def proposal_drafts_dir() -> Path:
    return ROOT / "docs" / "proposals_drafts"


def tasks_file_path() -> Path:
    return ROOT / "tasks.md"


def load_json_list(path: Path) -> list[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def load_proposal_runtime_registry() -> dict[str, dict[str, Any]]:
    registry: dict[str, dict[str, Any]] = {}
    for item in load_json_list(proposal_runtime_registry_path()):
        proposal_id = str(item.get("proposal_id", "")).strip()
        if not proposal_id:
            continue
        registry[proposal_id] = item
    return registry


def load_proposal_promotion_registry() -> dict[str, dict[str, Any]]:
    registry: dict[str, dict[str, Any]] = {}
    for item in load_json_list(proposal_promotion_registry_path()):
        proposal_id = str(item.get("proposal_id", "")).strip()
        if not proposal_id:
            continue
        registry[proposal_id] = item
    return registry


def load_task_status_index() -> dict[int, dict[str, str]]:
    path = tasks_file_path()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}

    tasks: dict[int, dict[str, str]] = {}
    for line in lines:
        match = TASK_LINE_RE.match(line.strip())
        if not match:
            continue
        task_id = int(match.group("task_id"))
        tasks[task_id] = {
            "status": match.group("status"),
            "body": match.group("body").strip(),
        }
    return tasks


def parse_proposal_document(path: Path) -> dict[str, Any] | None:
    match = PROPOSAL_DOC_FILENAME_RE.match(path.name)
    if not match:
        return None
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None

    lines = text.splitlines()
    title = ""
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("# "):
            title = stripped[2:].strip()
            break

    status = ""
    for index, line in enumerate(lines):
        if line.strip() != "## Status":
            continue
        for following in lines[index + 1 :]:
            stripped = following.strip()
            if stripped:
                status = stripped
                break
        break

    promotion_policy, _findings = load_proposal_promotion_policy_report()
    repository_projection = classify_proposal_repository_projection(
        path,
        policy=promotion_policy,
    )

    return {
        "proposal_id": match.group("proposal_id"),
        "slug": match.group("slug"),
        "path": path.relative_to(ROOT).as_posix(),
        "title": title or path.stem,
        "status": status,
        "repository_projection": repository_projection,
        "semantic_artifact_class": str(
            repository_projection.get("default_semantic_artifact_class", "reviewable_proposal")
        ),
        "text": text,
    }


def iter_proposal_documents() -> list[dict[str, Any]]:
    docs_dir = proposal_docs_dir()
    if not docs_dir.exists():
        return []
    documents: list[dict[str, Any]] = []
    for path in sorted(docs_dir.glob("*.md")):
        parsed = parse_proposal_document(path)
        if parsed is not None:
            documents.append(parsed)
    return documents


def classify_proposal_repository_projection(
    path: Path,
    *,
    policy: dict[str, Any] | None,
) -> dict[str, Any]:
    try:
        relpath = path.relative_to(ROOT).as_posix()
    except ValueError:
        relpath = path.as_posix()

    defaults = []
    if isinstance(policy, dict):
        defaults = [
            item
            for item in policy.get("repository_projection_defaults", [])
            if isinstance(item, dict)
        ]

    for item in defaults:
        prefix = str(item.get("path_prefix", "")).strip().rstrip("/")
        if not prefix:
            continue
        if relpath == prefix or relpath.startswith(prefix + "/"):
            return {
                "path": relpath,
                "path_prefix": prefix,
                "projection_role": str(item.get("projection_role", "")).strip()
                or "repository_projection",
                "default_semantic_artifact_class": str(
                    item.get("default_semantic_artifact_class", "")
                ).strip()
                or "unclassified",
                "semantic_source": "repository_projection_default",
                "layout_is_sole_source_of_meaning": False,
            }

    return {
        "path": relpath,
        "path_prefix": "",
        "projection_role": "unclassified",
        "default_semantic_artifact_class": "unclassified",
        "semantic_source": "unknown",
        "layout_is_sole_source_of_meaning": False,
    }


def infer_proposal_runtime_surfaces(text: str) -> list[str]:
    normalized = text.lower()
    surfaces = [
        path
        for path, hints in PROPOSAL_RUNTIME_SURFACE_HINTS.items()
        if any(hint in normalized for hint in hints)
    ]
    return sorted(set(surfaces))


def infer_proposal_posture(*, text: str, runtime_surfaces: list[str]) -> str:
    normalized = text.lower()
    if any(hint in normalized for hint in PROPOSAL_POSTURE_DEFERRED_HINTS):
        return "deferred_until_canonicalized"
    if runtime_surfaces or any(
        hint in normalized for hint in PROPOSAL_POSTURE_RUNTIME_RELEVANT_HINTS
    ):
        return "bounded_runtime_followup"
    return "document_only"


def evaluate_path_markers(markers: list[dict[str, Any]]) -> dict[str, Any]:
    checked_markers: list[dict[str, Any]] = []
    satisfied_count = 0
    for marker in markers:
        relpath = str(marker.get("path", "")).strip()
        pattern = str(marker.get("pattern", "")).strip()
        path = ROOT / relpath if relpath else ROOT
        try:
            text = path.read_text(encoding="utf-8")
            exists = True
        except OSError:
            text = ""
            exists = False
        satisfied = bool(exists and pattern and pattern in text)
        if satisfied:
            satisfied_count += 1
        checked_markers.append(
            {
                "path": relpath,
                "pattern": pattern,
                "exists": exists,
                "satisfied": satisfied,
            }
        )

    missing_markers = [marker for marker in checked_markers if not marker["satisfied"]]
    status = "not_configured"
    if checked_markers:
        if satisfied_count == len(checked_markers):
            status = "covered"
        elif satisfied_count == 0:
            status = "missing"
        else:
            status = "partial"
    return {
        "status": status,
        "required_count": len(checked_markers),
        "satisfied_count": satisfied_count,
        "markers": checked_markers,
        "missing_markers": missing_markers,
    }


def derive_runtime_realization_status(
    *,
    posture: str,
    runtime_markers: dict[str, Any],
    runtime_surfaces: list[str],
) -> str:
    if posture == "document_only":
        return "not_required"
    if posture == "deferred_until_canonicalized":
        return "deferred"
    if runtime_markers["required_count"] == 0:
        return "untracked" if runtime_surfaces else "missing"
    if runtime_markers["status"] == "covered":
        return "implemented"
    if runtime_markers["status"] == "partial":
        return "partial"
    return "missing"


def derive_reflective_followup_status(
    *,
    posture: str,
    runtime_status: str,
    marker_report: dict[str, Any],
) -> str:
    if posture == "document_only":
        return "not_required"
    if posture == "deferred_until_canonicalized":
        return "deferred"
    if (
        runtime_status in {"missing", "partial", "untracked"}
        and marker_report["required_count"] == 0
    ):
        return "pending_runtime"
    if marker_report["required_count"] == 0:
        return "untracked"
    if marker_report["status"] == "covered":
        return "covered"
    if marker_report["status"] == "partial":
        return "partial"
    return "missing"


def reflective_next_gap(
    *,
    posture: str,
    runtime_status: str,
    validation_status: str,
    observation_status: str,
) -> str:
    if posture == "document_only":
        return "none"
    if posture == "deferred_until_canonicalized":
        return "canonicalization"
    if runtime_status in {"missing", "partial", "untracked"}:
        return "runtime_realization"
    if validation_status in {"missing", "partial", "untracked", "pending_runtime"}:
        return "validation_closure"
    if observation_status in {"missing", "partial", "untracked", "pending_runtime"}:
        return "reobservation"
    return "none"


def build_reflective_backlog(entries: list[dict[str, Any]]) -> dict[str, Any]:
    backlog_items: list[dict[str, Any]] = []
    for entry in entries:
        chain = entry["reflective_chain"]
        next_gap = str(chain.get("next_gap", "none"))
        if next_gap == "none":
            continue
        backlog_items.append(
            {
                "proposal_id": entry["proposal_id"],
                "title": entry["title"],
                "posture": entry["posture"],
                "next_gap": next_gap,
                "runtime_realization_status": entry["runtime_realization"]["status"],
                "validation_closure_status": entry["validation_closure"]["status"],
                "observation_coverage_status": entry["observation_coverage"]["status"],
            }
        )

    grouped: dict[str, list[str]] = {}
    for item in backlog_items:
        grouped.setdefault(str(item["next_gap"]), []).append(str(item["proposal_id"]))

    return {
        "entry_count": len(backlog_items),
        "items": backlog_items,
        "grouped_by_next_gap": {key: sorted(value) for key, value in sorted(grouped.items())},
    }


def build_proposal_runtime_index() -> dict[str, Any]:
    registry = load_proposal_runtime_registry()
    task_status_index = load_task_status_index()
    entries: list[dict[str, Any]] = []

    for proposal in iter_proposal_documents():
        proposal_id = str(proposal["proposal_id"])
        registry_entry = registry.get(proposal_id, {})
        inferred_runtime_surfaces = infer_proposal_runtime_surfaces(str(proposal["text"]))
        runtime_surfaces = list(
            registry_entry.get("runtime_surfaces", inferred_runtime_surfaces)
            or inferred_runtime_surfaces
        )
        posture = str(
            registry_entry.get(
                "posture",
                infer_proposal_posture(
                    text=str(proposal["text"]),
                    runtime_surfaces=runtime_surfaces,
                ),
            )
        ).strip()
        if posture not in PROPOSAL_PROCESSING_POSTURES:
            posture = "document_only"

        runtime_markers = evaluate_path_markers(
            [
                marker
                for marker in registry_entry.get("runtime_markers", [])
                if isinstance(marker, dict)
            ]
        )
        validation_markers = evaluate_path_markers(
            [
                marker
                for marker in registry_entry.get("validation_markers", [])
                if isinstance(marker, dict)
            ]
        )
        observation_markers = evaluate_path_markers(
            [
                marker
                for marker in registry_entry.get("observation_markers", [])
                if isinstance(marker, dict)
            ]
        )

        runtime_status = derive_runtime_realization_status(
            posture=posture,
            runtime_markers=runtime_markers,
            runtime_surfaces=runtime_surfaces,
        )
        validation_status = derive_reflective_followup_status(
            posture=posture,
            runtime_status=runtime_status,
            marker_report=validation_markers,
        )
        observation_status = derive_reflective_followup_status(
            posture=posture,
            runtime_status=runtime_status,
            marker_report=observation_markers,
        )
        next_gap = reflective_next_gap(
            posture=posture,
            runtime_status=runtime_status,
            validation_status=validation_status,
            observation_status=observation_status,
        )

        task_ids = [
            int(task_id)
            for task_id in registry_entry.get("task_ids", [])
            if isinstance(task_id, int) or (isinstance(task_id, str) and str(task_id).isdigit())
        ]
        related_tasks = [
            {
                "task_id": task_id,
                "status": str(task_status_index.get(task_id, {}).get("status", "untracked")),
                "body": str(task_status_index.get(task_id, {}).get("body", "")),
            }
            for task_id in task_ids
        ]

        entries.append(
            {
                "proposal_id": proposal_id,
                "title": str(proposal["title"]),
                "status": str(proposal["status"]),
                "path": str(proposal["path"]),
                "repository_projection": copy.deepcopy(proposal["repository_projection"]),
                "semantic_artifact_class": str(proposal["semantic_artifact_class"]),
                "posture": posture,
                "posture_description": PROPOSAL_PROCESSING_POSTURES[posture],
                "posture_source": "registry" if proposal_id in registry else "heuristic",
                "runtime_surfaces": runtime_surfaces,
                "runtime_realization": {
                    **runtime_markers,
                    "status": runtime_status,
                },
                "validation_closure": {
                    **validation_markers,
                    "status": validation_status,
                },
                "observation_coverage": {
                    **observation_markers,
                    "status": observation_status,
                },
                "related_tasks": related_tasks,
                "reflective_chain": {
                    "proposal_normalization": "present",
                    "runtime_realization": runtime_status,
                    "validation_closure": validation_status,
                    "observation_coverage": observation_status,
                    "next_gap": next_gap,
                },
            }
        )

    backlog = build_reflective_backlog(entries)
    return {
        "generated_at": utc_now_iso(),
        "posture_vocabulary": copy.deepcopy(PROPOSAL_PROCESSING_POSTURES),
        "entry_count": len(entries),
        "entries": entries,
        "reflective_backlog": backlog,
    }


def write_proposal_runtime_index(index: dict[str, Any]) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = proposal_runtime_index_path()
    with artifact_lock(path):
        atomic_write_json(path, index)
    return path


def proposal_promotion_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def proposal_source_ref_records(
    source_refs: list[str],
    *,
    policy: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    root_resolved = ROOT.resolve()
    for ref in source_refs:
        if _looks_like_repo_path(ref):
            normalized = _normalize_transition_repo_path(ref)
            candidate = (ROOT / normalized).resolve(strict=False)
            within_repo_root = candidate == root_resolved or root_resolved in candidate.parents
            records.append(
                {
                    "ref": normalized,
                    "ref_kind": "repo_path",
                    "within_repo_root": within_repo_root,
                    "exists": candidate.exists() if within_repo_root else False,
                    "repository_projection": (
                        classify_proposal_repository_projection(
                            candidate,
                            policy=policy,
                        )
                        if within_repo_root
                        else {}
                    ),
                }
            )
        else:
            records.append(
                {
                    "ref": ref,
                    "ref_kind": "external_reference",
                    "within_repo_root": None,
                    "exists": None,
                    "repository_projection": {},
                }
            )
    return records


def derive_promotion_traceability(
    *,
    registry_entry: dict[str, Any],
    proposal: dict[str, Any],
    policy: dict[str, Any] | None,
) -> dict[str, Any]:
    source_artifact_class = str(registry_entry.get("source_artifact_class", "")).strip()
    source_refs = proposal_promotion_string_list(registry_entry.get("source_refs", []))
    required_provenance_links = proposal_promotion_string_list(
        registry_entry.get("required_provenance_links", [])
    )
    motivating_concern = str(registry_entry.get("motivating_concern", "")).strip()
    normalized_title = str(registry_entry.get("normalized_title", "")).strip()
    bounded_scope = str(registry_entry.get("bounded_scope", "")).strip()
    source_ref_records = proposal_source_ref_records(source_refs, policy=policy)
    outside_repo_source_refs = sorted(
        record["ref"]
        for record in source_ref_records
        if record["ref_kind"] == "repo_path" and not record["within_repo_root"]
    )
    missing_source_artifacts = sorted(
        record["ref"]
        for record in source_ref_records
        if record["ref_kind"] == "repo_path"
        and record["within_repo_root"]
        and record["exists"] is False
    )

    missing_fields: list[str] = []
    if not registry_entry:
        status = "missing_trace"
        next_gap = "attach_promotion_trace"
    else:
        if source_artifact_class != "working_draft":
            missing_fields.append("source_artifact_class")
        if not source_refs:
            missing_fields.append("source_refs")
        if outside_repo_source_refs:
            missing_fields.append("source_ref_outside_repo_root")
        if not motivating_concern:
            missing_fields.append("motivating_concern")
        if not normalized_title:
            missing_fields.append("normalized_title")
        if not bounded_scope:
            missing_fields.append("bounded_scope")
        if "source_draft_ref" not in required_provenance_links:
            missing_fields.append("source_draft_ref")
        if missing_source_artifacts:
            missing_fields.append("missing_source_artifact")

        if not missing_fields:
            status = "bounded"
            next_gap = "none"
        elif "source_artifact_class" in missing_fields:
            status = "invalid"
            next_gap = "repair_source_artifact_class"
        elif "source_ref_outside_repo_root" in missing_fields:
            status = "invalid"
            next_gap = "repair_source_refs"
        elif "source_refs" in missing_fields:
            status = "incomplete"
            next_gap = "record_source_refs"
        elif "missing_source_artifact" in missing_fields:
            status = "incomplete"
            next_gap = "restore_source_artifact"
        elif "motivating_concern" in missing_fields:
            status = "incomplete"
            next_gap = "record_motivating_concern"
        elif "normalized_title" in missing_fields:
            status = "incomplete"
            next_gap = "record_normalized_title"
        elif "bounded_scope" in missing_fields:
            status = "incomplete"
            next_gap = "record_bounded_scope"
        elif "source_draft_ref" in missing_fields:
            status = "incomplete"
            next_gap = "preserve_source_draft_ref"
        else:
            status = "incomplete"
            next_gap = "complete_promotion_trace"

    return {
        "status": status,
        "next_gap": next_gap,
        "source_artifact_class": source_artifact_class,
        "source_refs": source_refs,
        "source_ref_records": source_ref_records,
        "outside_repo_source_refs": outside_repo_source_refs,
        "motivating_concern": motivating_concern,
        "normalized_title": normalized_title,
        "bounded_scope": bounded_scope,
        "required_provenance_links": required_provenance_links,
        "missing_fields": missing_fields,
    }


def build_proposal_promotion_index() -> dict[str, Any]:
    promotion_policy, policy_findings = load_proposal_promotion_policy_report()
    registry = load_proposal_promotion_registry()
    entries: list[dict[str, Any]] = []
    grouped_by_status: dict[str, list[str]] = {}
    grouped_by_next_gap: dict[str, list[str]] = {}

    for proposal in iter_proposal_documents():
        proposal_id = str(proposal["proposal_id"])
        traceability = derive_promotion_traceability(
            registry_entry=registry.get(proposal_id, {}),
            proposal=proposal,
            policy=promotion_policy,
        )
        grouped_by_status.setdefault(str(traceability["status"]), []).append(proposal_id)
        grouped_by_next_gap.setdefault(str(traceability["next_gap"]), []).append(proposal_id)
        entries.append(
            {
                "proposal_id": proposal_id,
                "title": str(proposal["title"]),
                "path": str(proposal["path"]),
                "status": str(proposal["status"]),
                "repository_projection": copy.deepcopy(proposal["repository_projection"]),
                "semantic_artifact_class": str(proposal["semantic_artifact_class"]),
                "promotion_traceability": traceability,
            }
        )

    return {
        "artifact_kind": "proposal_promotion_index",
        "generated_at": utc_now_iso(),
        "semantic_boundary_principle": str(
            (promotion_policy or {}).get("semantic_boundary_principle", "")
        ),
        "policy_findings": policy_findings,
        "entry_count": len(entries),
        "entries": entries,
        "viewer_projection": {
            "traceability_status": {
                key: sorted(value) for key, value in sorted(grouped_by_status.items())
            },
            "next_gap": {key: sorted(value) for key, value in sorted(grouped_by_next_gap.items())},
        },
        "promotion_backlog": {
            "entry_count": sum(
                1 for entry in entries if entry["promotion_traceability"]["next_gap"] != "none"
            ),
            "grouped_by_next_gap": {
                key: sorted(value)
                for key, value in sorted(grouped_by_next_gap.items())
                if key != "none"
            },
        },
    }


def write_proposal_promotion_index(index: dict[str, Any]) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = proposal_promotion_index_path()
    with artifact_lock(path):
        atomic_write_json(path, index)
    return path


def acceptance_reference_indexes(
    references: Any,
    *,
    source_acceptance: list[str],
    field_name: str,
) -> tuple[list[int], list[str]]:
    if not isinstance(references, list):
        return [], [f"{field_name} must be a list"]

    indexes: list[int] = []
    errors: list[str] = []
    for idx, item in enumerate(references, start=1):
        if not isinstance(item, dict):
            errors.append(f"{field_name}[{idx}] must be an object")
            continue
        acceptance_index = item.get("acceptance_index")
        acceptance_text = str(item.get("acceptance_text", "")).strip()
        if not isinstance(acceptance_index, int):
            errors.append(f"{field_name}[{idx}].acceptance_index must be an integer")
            continue
        if acceptance_index < 1 or acceptance_index > len(source_acceptance):
            errors.append(
                f"{field_name}[{idx}].acceptance_index {acceptance_index} is out of range"
            )
            continue
        expected_text = source_acceptance[acceptance_index - 1]
        if acceptance_text != expected_text:
            errors.append(
                f"{field_name}[{idx}].acceptance_text must match source acceptance "
                f"[{acceptance_index}]"
            )
            continue
        indexes.append(acceptance_index)
    return indexes, errors


def validate_split_proposal_artifact(
    *,
    artifact: dict[str, Any],
    node: SpecNode,
    run_id: str | None,
) -> list[str]:
    errors: list[str] = []
    expected_id = f"refactor_proposal::{node.id}::{SPLIT_REFACTOR_SIGNAL}"
    expected_acceptance = node.data.get("acceptance")
    if not isinstance(expected_acceptance, list):
        return ["Target spec acceptance must be a list before split proposal validation"]
    source_acceptance = [str(item) for item in expected_acceptance]

    if str(artifact.get("id", "")).strip() != expected_id:
        errors.append(f"proposal id must be {expected_id}")
    if str(artifact.get("proposal_type", "")).strip() != "refactor_proposal":
        errors.append("proposal_type must be refactor_proposal")
    if str(artifact.get("refactor_kind", "")).strip() != SPLIT_REFACTOR_KIND:
        errors.append(f"refactor_kind must be {SPLIT_REFACTOR_KIND}")
    if str(artifact.get("target_spec_id", "")).strip() != node.id:
        errors.append(f"target_spec_id must be {node.id}")
    if str(artifact.get("source_signal", "")).strip() != SPLIT_REFACTOR_SIGNAL:
        errors.append(f"source_signal must be {SPLIT_REFACTOR_SIGNAL}")
    if str(artifact.get("execution_policy", "")).strip() != "emit_proposal":
        errors.append("execution_policy must be emit_proposal")
    if not str(artifact.get("status", "")).strip():
        errors.append("status must be non-empty")

    source_run_ids = artifact.get("source_run_ids")
    if not isinstance(source_run_ids, list) or not source_run_ids:
        errors.append("source_run_ids must be a non-empty list")
    elif run_id is not None:
        normalized_source_run_ids = [
            str(item).strip() for item in source_run_ids if str(item).strip()
        ]
        if run_id not in normalized_source_run_ids:
            errors.append("source_run_ids must include the current run_id")

    parent_after_split = artifact.get("parent_after_split")
    if not isinstance(parent_after_split, dict):
        errors.append("parent_after_split must be an object")
        parent_after_split = {}
    elif not str(parent_after_split.get("narrowed_role_summary", "")).strip():
        errors.append("parent_after_split.narrowed_role_summary must be non-empty")

    retained_indexes, retained_errors = acceptance_reference_indexes(
        parent_after_split.get("retained_acceptance", []),
        source_acceptance=source_acceptance,
        field_name="parent_after_split.retained_acceptance",
    )
    errors.extend(retained_errors)

    intended_depends_on = parent_after_split.get("intended_depends_on", [])
    if not isinstance(intended_depends_on, list):
        errors.append("parent_after_split.intended_depends_on must be a list")
        intended_depends_on = []
    elif len(intended_depends_on) > ATOMICITY_MAX_BLOCKING_CHILDREN:
        errors.append(
            "parent_after_split.intended_depends_on must not exceed "
            f"{ATOMICITY_MAX_BLOCKING_CHILDREN} blocking child slots"
        )

    suggested_children = artifact.get("suggested_children")
    child_slot_keys: list[str] = []
    child_index_map: dict[str, list[int]] = {}
    if not isinstance(suggested_children, list) or not suggested_children:
        errors.append("suggested_children must be a non-empty list")
        suggested_children = []
    else:
        for idx, child in enumerate(suggested_children, start=1):
            if not isinstance(child, dict):
                errors.append(f"suggested_children[{idx}] must be an object")
                continue
            slot_key = str(child.get("slot_key", "")).strip()
            if not slot_key:
                errors.append(f"suggested_children[{idx}].slot_key must be non-empty")
                continue
            if slot_key in child_slot_keys:
                errors.append(f"suggested_children[{idx}].slot_key must be unique")
                continue
            child_slot_keys.append(slot_key)
            for key_name in (
                "suggested_id",
                "suggested_path",
                "bounded_concern_summary",
                "suggested_title",
                "suggested_prompt",
            ):
                if not str(child.get(key_name, "")).strip():
                    errors.append(f"suggested_children[{idx}].{key_name} must be non-empty")
            assigned_indexes, assigned_errors = acceptance_reference_indexes(
                child.get("assigned_acceptance", []),
                source_acceptance=source_acceptance,
                field_name=f"suggested_children[{idx}].assigned_acceptance",
            )
            errors.extend(assigned_errors)
            child_index_map[slot_key] = assigned_indexes

    acceptance_mapping = artifact.get("acceptance_mapping")
    seen_indexes: set[int] = set()
    mapping_targets: dict[str, list[int]] = {"parent_retained": []}
    if not isinstance(acceptance_mapping, list):
        errors.append("acceptance_mapping must be a list")
        acceptance_mapping = []
    else:
        for idx, entry in enumerate(acceptance_mapping, start=1):
            if not isinstance(entry, dict):
                errors.append(f"acceptance_mapping[{idx}] must be an object")
                continue
            acceptance_index = entry.get("acceptance_index")
            acceptance_text = str(entry.get("acceptance_text", "")).strip()
            target = str(entry.get("target", "")).strip()
            if not isinstance(acceptance_index, int):
                errors.append(f"acceptance_mapping[{idx}].acceptance_index must be an integer")
                continue
            if acceptance_index < 1 or acceptance_index > len(source_acceptance):
                errors.append(
                    f"acceptance_mapping[{idx}].acceptance_index {acceptance_index} is out of range"
                )
                continue
            if acceptance_text != source_acceptance[acceptance_index - 1]:
                errors.append(
                    f"acceptance_mapping[{idx}].acceptance_text must match source acceptance "
                    f"[{acceptance_index}]"
                )
                continue
            if acceptance_index in seen_indexes:
                errors.append(
                    f"acceptance_mapping assigns acceptance [{acceptance_index}] more than once"
                )
                continue
            if target != "parent_retained" and target not in child_slot_keys:
                errors.append(
                    f"acceptance_mapping[{idx}].target must be parent_retained or one child slot"
                )
                continue
            seen_indexes.add(acceptance_index)
            mapping_targets.setdefault(target, []).append(acceptance_index)

    expected_indexes = set(range(1, len(source_acceptance) + 1))
    if seen_indexes != expected_indexes:
        missing = sorted(expected_indexes - seen_indexes)
        extra = sorted(seen_indexes - expected_indexes)
        if missing:
            errors.append(
                "acceptance_mapping must cover every current parent acceptance criterion "
                "exactly once; "
                f"missing indexes: {missing}"
            )
        if extra:
            errors.append(f"acceptance_mapping contains invalid indexes: {extra}")

    if sorted(retained_indexes) != sorted(mapping_targets.get("parent_retained", [])):
        errors.append(
            "parent_after_split.retained_acceptance must match acceptance_mapping "
            "target=parent_retained"
        )

    for slot_key in child_slot_keys:
        if sorted(child_index_map.get(slot_key, [])) != sorted(mapping_targets.get(slot_key, [])):
            errors.append(
                f"suggested_children slot {slot_key} must match acceptance_mapping assignments"
            )

    for idx, item in enumerate(intended_depends_on, start=1):
        if not isinstance(item, dict):
            errors.append(f"parent_after_split.intended_depends_on[{idx}] must be an object")
            continue
        slot_key = str(item.get("slot_key", "")).strip()
        suggested_id = str(item.get("suggested_id", "")).strip()
        if slot_key not in child_slot_keys:
            errors.append(
                f"parent_after_split.intended_depends_on[{idx}].slot_key "
                "must reference a child slot"
            )
        if not suggested_id:
            errors.append(
                f"parent_after_split.intended_depends_on[{idx}].suggested_id must be non-empty"
            )

    lineage_updates = artifact.get("lineage_updates")
    if not isinstance(lineage_updates, dict):
        errors.append("lineage_updates must be an object")
        lineage_updates = {}

    parent_depends_on_add = lineage_updates.get("parent_depends_on_add", [])
    if not isinstance(parent_depends_on_add, list):
        errors.append("lineage_updates.parent_depends_on_add must be a list")
        parent_depends_on_add = []
    for idx, item in enumerate(parent_depends_on_add, start=1):
        if not isinstance(item, dict):
            errors.append(f"lineage_updates.parent_depends_on_add[{idx}] must be an object")
            continue
        if str(item.get("slot_key", "")).strip() not in child_slot_keys:
            errors.append(
                f"lineage_updates.parent_depends_on_add[{idx}].slot_key must reference a child slot"
            )
        if not str(item.get("suggested_id", "")).strip():
            errors.append(
                f"lineage_updates.parent_depends_on_add[{idx}].suggested_id must be non-empty"
            )

    child_refines_add = lineage_updates.get("child_refines_add", [])
    if not isinstance(child_refines_add, list):
        errors.append("lineage_updates.child_refines_add must be a list")
        child_refines_add = []
    for idx, item in enumerate(child_refines_add, start=1):
        if not isinstance(item, dict):
            errors.append(f"lineage_updates.child_refines_add[{idx}] must be an object")
            continue
        if str(item.get("slot_key", "")).strip() not in child_slot_keys:
            errors.append(
                f"lineage_updates.child_refines_add[{idx}].slot_key must reference a child slot"
            )
        if not str(item.get("suggested_id", "")).strip():
            errors.append(
                f"lineage_updates.child_refines_add[{idx}].suggested_id must be non-empty"
            )
        refines = item.get("refines")
        if refines != [node.id]:
            errors.append(
                f"lineage_updates.child_refines_add[{idx}].refines must equal [{node.id}]"
            )

    return errors


def find_split_proposal_queue_item(spec_id: str) -> dict[str, Any] | None:
    for item in load_proposal_queue():
        if str(item.get("spec_id", "")).strip() != spec_id:
            continue
        if str(item.get("proposal_type", "")).strip() != "refactor_proposal":
            continue
        if str(item.get("refactor_kind", "")).strip() != SPLIT_REFACTOR_KIND:
            continue
        if str(item.get("signal", "")).strip() != SPLIT_REFACTOR_SIGNAL:
            continue
        if not proposal_is_applicable(item):
            continue
        return item
    return None


def proposal_evidence_for_index(
    evidence_items: list[Any],
    *,
    acceptance_index: int,
    proposal_id: str,
    acceptance_text: str,
) -> Any:
    if 0 < acceptance_index <= len(evidence_items):
        existing = evidence_items[acceptance_index - 1]
        if acceptance_evidence_semantically_grounded(
            criterion=acceptance_text,
            evidence_item=existing,
        ):
            return existing
    criterion_text = str(acceptance_text).strip()
    return {
        "criterion": criterion_text,
        "evidence": (
            f"Applied split proposal {proposal_id} mapped acceptance [{acceptance_index}] "
            f"for {criterion_text} into this canonical node."
        ),
    }


def validate_split_proposal_application_target(
    *,
    node: SpecNode,
    proposal_item: dict[str, Any],
    proposal_artifact: dict[str, Any],
    current_index: dict[str, SpecNode],
) -> list[str]:
    errors = validate_split_refactor_target(node)
    if str(proposal_item.get("proposal_type", "")).strip() != "refactor_proposal":
        errors.append("split proposal application requires proposal_type refactor_proposal")
    if str(proposal_item.get("refactor_kind", "")).strip() != SPLIT_REFACTOR_KIND:
        errors.append(f"split proposal application requires refactor_kind {SPLIT_REFACTOR_KIND}")
    if str(proposal_item.get("signal", "")).strip() != SPLIT_REFACTOR_SIGNAL:
        errors.append(f"split proposal application requires signal {SPLIT_REFACTOR_SIGNAL}")
    errors.extend(
        validate_split_proposal_artifact(
            artifact=proposal_artifact,
            node=node,
            run_id=None,
        )
    )
    if not errors:
        for child in proposal_artifact.get("suggested_children", []):
            if not isinstance(child, dict):
                continue
            child_id = str(child.get("suggested_id", "")).strip()
            child_path = str(child.get("suggested_path", "")).strip()
            existing_child = current_index.get(child_id)
            if existing_child is not None:
                existing_relpath = existing_child.path.relative_to(ROOT).as_posix()
                if existing_relpath != child_path:
                    errors.append(
                        "split proposal application cannot reuse existing spec id "
                        f"{child_id} at a different path: {existing_relpath}"
                    )
                existing_refines = existing_child.data.get("refines", [])
                if not isinstance(existing_refines, list) or node.id not in {
                    str(item).strip() for item in existing_refines
                }:
                    errors.append(
                        "split proposal application can reuse existing child "
                        f"{child_id} only when it already refines {node.id}"
                    )
                continue
            if child_path and (ROOT / child_path).exists():
                errors.append(
                    "split proposal application cannot overwrite existing child spec path: "
                    f"{child_path}"
                )
    return errors


def apply_split_proposal_to_worktree(
    *,
    node: SpecNode,
    proposal_artifact: dict[str, Any],
    worktree_path: Path,
) -> list[str]:
    evidence_items = list(node.data.get("acceptance_evidence", []))
    parent_relpath = node.path.relative_to(ROOT).as_posix()
    specs_dir = worktree_path / "specs" / "nodes"
    worktree_specs = load_specs_from_dir(specs_dir)
    index = index_specs(worktree_specs)

    child_specs: list[dict[str, Any]] = []
    child_ids: list[str] = []
    child_paths: list[str] = []
    child_existing_data: list[dict[str, Any] | None] = []
    for child in proposal_artifact["suggested_children"]:
        child_id = str(child["suggested_id"]).strip()
        child_path = str(child["suggested_path"]).strip()
        if child_id in index:
            existing_child = index[child_id]
            existing_relpath = existing_child.path.relative_to(worktree_path).as_posix()
            if existing_relpath != child_path:
                raise ValueError(
                    "split proposal application cannot reuse existing spec id "
                    f"{child_id} at a different path: {existing_relpath}"
                )
            existing_refines = existing_child.data.get("refines", [])
            if not isinstance(existing_refines, list) or node.id not in {
                str(item).strip() for item in existing_refines
            }:
                raise ValueError(
                    "split proposal application can reuse existing child "
                    f"{child_id} only when it already refines {node.id}"
                )
            child_specs.append(child)
            child_ids.append(child_id)
            child_paths.append(child_path)
            child_existing_data.append(existing_child.data)
            continue
        absolute_child_path = worktree_path / child_path
        if absolute_child_path.exists():
            raise ValueError(
                f"Cannot apply split proposal: child spec path already exists: {child_path}"
            )
        child_ids.append(child_id)
        child_paths.append(child_path)
        child_specs.append(child)
        child_existing_data.append(None)

    parent_retained = proposal_artifact["parent_after_split"]["retained_acceptance"]
    retained_texts = [str(item["acceptance_text"]).strip() for item in parent_retained]
    retained_evidence = [
        proposal_evidence_for_index(
            evidence_items,
            acceptance_index=int(item["acceptance_index"]),
            proposal_id=str(proposal_artifact["id"]),
            acceptance_text=str(item["acceptance_text"]).strip(),
        )
        for item in parent_retained
    ]

    current_depends_on = [str(dep).strip() for dep in node.depends_on if str(dep).strip()]
    proposed_depends_on = [
        str(item["suggested_id"]).strip()
        for item in proposal_artifact["parent_after_split"]["intended_depends_on"]
    ]
    node.data["prompt"] = str(
        proposal_artifact["parent_after_split"]["narrowed_role_summary"]
    ).strip()
    node.data["depends_on"] = merge_unique_strings(current_depends_on, proposed_depends_on)
    node.data["acceptance"] = retained_texts
    node.data["acceptance_evidence"] = retained_evidence
    worktree_parent_path = worktree_path / parent_relpath
    node.data = atomic_write_spec_yaml(worktree_parent_path, node.data)

    for child, child_id, child_path, existing_data in zip(
        child_specs, child_ids, child_paths, child_existing_data, strict=True
    ):
        assigned_acceptance = child["assigned_acceptance"]
        child_acceptance = [str(item["acceptance_text"]).strip() for item in assigned_acceptance]
        child_evidence = [
            proposal_evidence_for_index(
                evidence_items,
                acceptance_index=int(item["acceptance_index"]),
                proposal_id=str(proposal_artifact["id"]),
                acceptance_text=str(item["acceptance_text"]).strip(),
            )
            for item in assigned_acceptance
        ]
        absolute_child_path = worktree_path / child_path
        if existing_data is None:
            child_data = {
                "id": child_id,
                "title": str(child["suggested_title"]).strip(),
                "kind": "spec",
                "status": "outlined",
                "maturity": 0.2,
                "depends_on": [],
                "relates_to": [],
                "refines": [node.id],
                "inputs": [parent_relpath],
                "outputs": [child_path],
                "allowed_paths": [child_path],
                "acceptance": child_acceptance,
                "acceptance_evidence": child_evidence,
                "prompt": str(child["suggested_prompt"]).strip(),
            }
        else:
            child_data = dict(existing_data)
            child_data["acceptance"] = child_acceptance
            child_data["acceptance_evidence"] = child_evidence
        absolute_child_path.parent.mkdir(parents=True, exist_ok=True)
        child_data = atomic_write_spec_yaml(absolute_child_path, child_data)

    return [parent_relpath, *child_paths]


def mark_split_proposal_applied(
    *,
    proposal_item: dict[str, Any],
    proposal_artifact_path: Path,
    proposal_artifact: dict[str, Any],
    run_id: str,
) -> tuple[Path, Path]:
    proposal_artifact["status"] = "applied"
    proposal_artifact["applied_run_id"] = run_id
    proposal_artifact["applied_at"] = utc_now_iso()
    proposal_artifact_path.parent.mkdir(parents=True, exist_ok=True)
    with artifact_lock(proposal_artifact_path):
        atomic_write_json(proposal_artifact_path, proposal_artifact)

    queue_path = proposal_queue_path()
    with artifact_lock(queue_path):
        updated_items: list[dict[str, Any]] = []
        if queue_path.exists():
            existing_items, error = load_json_list_report(
                queue_path,
                artifact_kind="proposal queue artifact",
            )
            if error:
                raise RuntimeError(error)
        else:
            existing_items = []
        for item in existing_items or []:
            if str(item.get("id", "")).strip() == str(proposal_item.get("id", "")).strip():
                updated_item = dict(item)
                updated_item["status"] = "applied"
                updated_item["applied_run_id"] = run_id
                updated_item["applied_at"] = proposal_artifact["applied_at"]
                updated_items.append(updated_item)
                continue
            updated_items.append(item)
        atomic_write_json(queue_path, updated_items)
    return proposal_artifact_path, queue_path


def upsert_split_proposal_queue(
    *,
    node: SpecNode,
    run_id: str,
    artifact: dict[str, Any],
    artifact_path: Path,
) -> tuple[Path, list[dict[str, Any]]]:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = proposal_queue_path()
    with artifact_lock(path):
        if path.exists():
            existing_items, error = load_json_list_report(
                path,
                artifact_kind="proposal queue artifact",
            )
            if error:
                raise RuntimeError(error)
        else:
            existing_items = []
        proposal_id = f"refactor_proposal::{node.id}::{SPLIT_REFACTOR_SIGNAL}"
        existing_item = next(
            (
                item
                for item in (existing_items or [])
                if str(item.get("id", "")).strip() == proposal_id
            ),
            None,
        )
        source_run_ids = merge_unique_strings(
            signal_supporting_run_ids(node.id, SPLIT_REFACTOR_SIGNAL),
            list(existing_item.get("supporting_run_ids", [])) if existing_item else [],
            [run_id],
            list(artifact.get("source_run_ids", [])),
        )

        updated_item = {
            "id": proposal_id,
            "proposal_type": "refactor_proposal",
            "spec_id": node.id,
            "target_spec_id": node.id,
            "signal": SPLIT_REFACTOR_SIGNAL,
            "source_signal": SPLIT_REFACTOR_SIGNAL,
            "refactor_kind": SPLIT_REFACTOR_KIND,
            "recommended_action": "emit_split_proposal",
            "status": (
                str(existing_item.get("status", "")).strip()
                if existing_item and str(existing_item.get("status", "")).strip()
                else str(artifact.get("status", "")).strip() or "proposed"
            ),
            "trigger": "explicit_operator_target",
            "occurrence_count": len(source_run_ids),
            "threshold": 1,
            "supporting_run_ids": source_run_ids,
            "source_work_item_type": "graph_refactor",
            "execution_policy": "emit_proposal",
            "proposal_artifact_path": artifact_path.relative_to(ROOT).as_posix(),
        }

        preserved = [
            item
            for item in (existing_items or [])
            if isinstance(item, dict) and str(item.get("id", "")).strip() != proposal_id
        ]
        updated = preserved + [updated_item]
        atomic_write_json(path, updated)
    sync_tracked_proposal_lane_from_queue(updated, item_ids={proposal_id})
    return path, updated


def write_latest_summary(payload: dict[str, Any]) -> None:
    executor_environment = payload.get("executor_environment", {})
    issues = (
        executor_environment.get("issues", []) if isinstance(executor_environment, dict) else []
    )
    primary_failure = (
        bool(executor_environment.get("primary_failure"))
        if isinstance(executor_environment, dict)
        else False
    )
    completion_status = payload.get("completion_status")
    if completion_status is None:
        completion_status = (
            COMPLETION_STATUS_OK if payload.get("exit_code", 1) == 0 else COMPLETION_STATUS_FAILED
        )
    summary = (
        f"# Latest Supervisor Run\n\n"
        f"- run_id: {payload['run_id']}\n"
        f"- spec_id: {payload['spec_id']}\n"
        f"- title: {payload['title']}\n"
        f"- completion_status: {completion_status}\n"
        f"- outcome: {payload['outcome']}\n"
        f"- gate_state: {payload['gate_state']}\n"
        f"- before_status: {payload['before_status']}\n"
        f"- proposed_status: {payload.get('proposed_status') or '-'}\n"
        f"- final_status: {payload['final_status']}\n"
        f"- validation_errors: {len(payload['validation_errors'])}\n"
        f"- executor_environment_issues: {len(issues)}\n"
        f"- executor_environment_primary_failure: {'yes' if primary_failure else 'no'}\n"
        f"- required_human_action: {payload.get('required_human_action', '-')}\n"
    )
    summary_path = RUNS_DIR / "latest-summary.md"
    with artifact_lock(summary_path):
        atomic_write_text(summary_path, summary)


def refresh_latest_summary_for_gate_resolution(node: SpecNode) -> None:
    """Rewrite the latest summary to reflect the current gate decision state."""
    run_id = str(node.data.get("last_run_id", "")).strip()
    title = str(node.title).strip() or str(node.data.get("title", "")).strip() or node.id
    before_status = str(node.data.get("proposed_status") or node.status)
    payload = {
        "run_id": run_id or "gate-resolution",
        "spec_id": node.id,
        "title": title,
        "completion_status": COMPLETION_STATUS_OK,
        "outcome": str(node.data.get("last_outcome", "")).strip() or "done",
        "gate_state": str(node.data.get("gate_state", "")).strip() or "none",
        "before_status": before_status,
        "proposed_status": node.data.get("proposed_status"),
        "final_status": node.status,
        "validation_errors": list(node.data.get("last_errors", [])),
        "executor_environment": {},
        "required_human_action": str(node.data.get("required_human_action", "")).strip() or "-",
        "exit_code": 0,
    }
    write_latest_summary(payload)


def sanitize_for_git(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]", "-", value).strip("-._").lower()
    return slug or "spec"


def should_fallback_to_copied_worktree(stderr: str) -> bool:
    """Return True when branch/worktree creation is blocked by local ref locking.

    This fallback is intentionally narrow: it is used only for permission-style
    failures while creating refs/worktree metadata in the current environment.
    Ordinary git errors (for example, not being in a repository) should still
    surface as hard failures.
    """
    message = stderr.lower()
    return "cannot lock ref" in message or (
        "operation not permitted" in message
        and (".git/refs/heads" in message or "refs/heads/" in message)
    )


def create_sandbox_worktree_copy(*, safe_id: str, timestamp: str) -> tuple[Path, str]:
    """Create an isolated fallback workspace by copying the current repo tree.

    The copy lives under `.worktrees/` but avoids recursive copying of that same
    directory. It preserves the current working tree content so the executor can
    still run in isolation even when git cannot create a new branch/worktree.
    """
    worktree_path = WORKTREES_DIR / f"{safe_id}-{timestamp}"
    sandbox_branch = f"sandbox/{safe_id}/{timestamp}"
    if worktree_path.exists():
        shutil.rmtree(worktree_path)
    shutil.copytree(
        ROOT,
        worktree_path,
        ignore=shutil.ignore_patterns(".worktrees"),
    )
    return worktree_path, sandbox_branch


def create_isolated_worktree(node_id: str) -> tuple[Path, str]:
    safe_id = sanitize_for_git(node_id)
    WORKTREES_DIR.mkdir(parents=True, exist_ok=True)
    for _attempt in range(RUNTIME_ID_COLLISION_RETRY_LIMIT):
        suffix = f"{utc_compact_timestamp()}-{runtime_nonce()}"
        branch = f"codex/{safe_id}/{suffix}"
        worktree_path = WORKTREES_DIR / f"{safe_id}-{suffix}"
        if worktree_path.exists():
            continue
        result = subprocess.run(
            ["git", "worktree", "add", "-b", branch, worktree_path.as_posix(), "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            return worktree_path, branch
        if should_fallback_to_copied_worktree(result.stderr):
            return create_sandbox_worktree_copy(safe_id=safe_id, timestamp=suffix)
        low = result.stderr.lower()
        if (
            "already exists" in low
            or "already checked out" in low
            or "already used by worktree" in low
            or "a branch named" in low
        ):
            continue
        raise RuntimeError(result.stderr.strip() or "failed to create worktree")
    raise RuntimeError(f"failed to allocate unique worktree for {node_id}")


def is_supervisor_managed_worktree_path(worktree_path: Path) -> bool:
    candidate = Path(worktree_path).expanduser()
    try:
        candidate_resolved = candidate.resolve()
        worktrees_root = WORKTREES_DIR.expanduser().resolve()
        candidate_resolved.relative_to(worktrees_root)
    except (FileNotFoundError, ValueError):
        return False
    return True


def cleanup_isolated_worktree(worktree_path: Path, branch: str) -> None:
    """Remove one supervisor-created isolated worktree and its ephemeral branch.

    Review gates keep a worktree temporarily so approval can replay the accepted
    diff. All other paths should clean up their isolated workspace once the run
    is logged and canonical state is updated.
    """

    worktree = Path(worktree_path).expanduser()
    branch_name = branch.strip()

    if not is_supervisor_managed_worktree_path(worktree):
        return

    if branch_name.startswith("sandbox/"):
        shutil.rmtree(worktree, ignore_errors=True)
        return

    if worktree.exists():
        subprocess.run(
            ["git", "worktree", "remove", "--force", worktree.as_posix()],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    if worktree.exists():
        shutil.rmtree(worktree, ignore_errors=True)

    if branch_name.startswith("codex/"):
        subprocess.run(
            ["git", "branch", "-D", branch_name],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )


def sync_current_node_into_worktree(node: SpecNode, worktree_path: Path) -> Path:
    worktree_node_path = worktree_path / node.path.relative_to(ROOT)
    worktree_node_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(node.path, worktree_node_path)
    return worktree_node_path


def dirty_local_input_spec_paths(
    node: SpecNode,
    *,
    changed_files: list[str] | None = None,
) -> list[str]:
    changed = set(changed_files if changed_files is not None else git_status_changed_files(ROOT))
    synced: list[str] = []
    source_relpath = node.path.relative_to(ROOT).as_posix()
    for rel_path in node.inputs:
        if rel_path == source_relpath or not is_spec_node_path(rel_path):
            continue
        if rel_path not in changed:
            continue
        src = ROOT / rel_path
        if src.exists() and src.is_file():
            synced.append(rel_path)
    return sorted(set(synced))


def sync_local_input_specs_into_worktree(
    node: SpecNode,
    worktree_path: Path,
    *,
    changed_files: list[str] | None = None,
) -> list[Path]:
    synced_paths: list[Path] = []
    for rel_path in dirty_local_input_spec_paths(node, changed_files=changed_files):
        src = ROOT / rel_path
        dst = worktree_path / rel_path
        dst.parent.mkdir(parents=True, exist_ok=True)
        sanitized_text = sanitize_spec_sync_text(src.read_text(encoding="utf-8"))
        dst.write_text(sanitized_text, encoding="utf-8")
        synced_paths.append(dst)
    return synced_paths


def sanitize_spec_sync_text(text: str) -> str:
    """Remove runtime-only contamination before syncing a spec back to root.

    Child agents edit draft spec files inside an isolated worktree, but runtime
    markers such as RUN_OUTCOME/BLOCKER must never become canonical spec data.
    The gatekeeper therefore strips reserved runtime keys and re-renders the file
    canonically before the root copy is updated.
    """
    yaml_module = get_yaml_module()
    data = yaml_module.safe_load(text) or {}
    if not isinstance(data, dict):
        raise ValueError("top-level YAML document must be a mapping")
    cleaned = strip_runtime_sync_data(data)
    return dump_yaml_text(cleaned)


def sync_files_from_worktree(worktree_path: Path, rel_paths: list[str]) -> None:
    for rel_path in rel_paths:
        src = worktree_path / rel_path
        dst = ROOT / rel_path
        if src.exists() and src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            if is_spec_node_path(rel_path):
                sanitized_text = sanitize_spec_sync_text(src.read_text(encoding="utf-8"))
                dst.write_text(sanitized_text, encoding="utf-8")
            else:
                shutil.copy2(src, dst)
            continue
        if dst.exists() and dst.is_file():
            dst.unlink()


def gate_worktree_divergence_paths(
    node: SpecNode, worktree_path: Path, rel_paths: list[str]
) -> list[str]:
    """Return semantic paths that differ between current gate content and worktree copies."""
    yaml_module = get_yaml_module()
    divergence_paths: list[str] = []
    for rel_path in rel_paths:
        if not is_spec_node_path(rel_path):
            continue

        worktree_node_path = worktree_path / rel_path
        current_node_path = ROOT / rel_path
        if not worktree_node_path.exists() or not worktree_node_path.is_file():
            if current_node_path.exists():
                divergence_paths.append(f"{rel_path}:<missing-worktree-file>")
            continue
        if not current_node_path.exists() or not current_node_path.is_file():
            divergence_paths.append(f"{rel_path}:<missing-canonical-file>")
            continue

        worktree_data = yaml_module.safe_load(worktree_node_path.read_text(encoding="utf-8")) or {}
        current_data = yaml_module.safe_load(current_node_path.read_text(encoding="utf-8")) or {}
        if not isinstance(worktree_data, dict) or not isinstance(current_data, dict):
            divergence_paths.append(f"{rel_path}:<root>")
            continue

        current_snapshot = canonical_spec_snapshot(current_data)
        worktree_snapshot = canonical_spec_snapshot(worktree_data)
        divergence_paths.extend(
            f"{rel_path}:{path}"
            for path in collect_changed_paths(current_snapshot, worktree_snapshot)
        )
    return divergence_paths


def list_registered_worktrees() -> dict[Path, str]:
    result = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return {}

    entries: dict[Path, str] = {}
    current_path: Path | None = None
    current_branch = ""
    for line in result.stdout.splitlines():
        if not line.strip():
            if current_path is not None:
                entries[current_path] = current_branch
            current_path = None
            current_branch = ""
            continue
        if line.startswith("worktree "):
            current_path = Path(line.removeprefix("worktree ").strip()).resolve()
            continue
        if line.startswith("branch "):
            branch_ref = line.removeprefix("branch ").strip()
            current_branch = branch_ref.removeprefix("refs/heads/")
    if current_path is not None:
        entries[current_path] = current_branch
    return entries


def gate_worktree_freshness_issue(
    node: SpecNode,
    *,
    registered_worktrees: dict[Path, str] | None = None,
) -> str | None:
    worktree_value = str(node.data.get("last_worktree_path", "")).strip()
    changed_files = list(node.data.get("last_changed_files", []))
    materialized_child_paths = list(node.data.get("last_materialized_child_paths", []))
    branch = str(node.data.get("last_branch", "")).strip()
    has_pending_worktree_content = bool(changed_files or materialized_child_paths)

    if not worktree_value:
        if node.gate_state == "review_pending" and has_pending_worktree_content:
            return "missing last_worktree_path for review gate with pending worktree content"
        return None

    worktree_path = Path(worktree_value).expanduser()
    if not worktree_path.exists():
        return f"recorded last_worktree_path does not exist: {worktree_path.as_posix()}"

    if not branch:
        return None

    if branch.startswith("sandbox/"):
        return None

    worktree_key = worktree_path.resolve()
    registered = (
        registered_worktrees if registered_worktrees is not None else list_registered_worktrees()
    )
    registered_branch = registered.get(worktree_key)
    if registered_branch is None:
        return (
            "recorded last_worktree_path is not a currently registered git worktree: "
            f"{worktree_path.as_posix()}"
        )
    if registered_branch != branch:
        return (
            f"recorded last_branch {branch} does not match current worktree branch "
            f"{registered_branch or '<detached>'}"
        )
    return None


def stale_gate_entries(
    specs: list[SpecNode],
    *,
    registered_worktrees: dict[Path, str] | None = None,
) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    registered = (
        registered_worktrees if registered_worktrees is not None else list_registered_worktrees()
    )
    for node in specs:
        if node.gate_state != "review_pending":
            continue
        issue = gate_worktree_freshness_issue(node, registered_worktrees=registered)
        if not issue:
            continue
        entries.append(
            {
                "spec_id": node.id,
                "gate_state": node.gate_state,
                "worktree_path": str(node.data.get("last_worktree_path", "")).strip(),
                "branch": str(node.data.get("last_branch", "")).strip(),
                "issue": issue,
            }
        )
    entries.sort(
        key=lambda item: (
            GATE_ACTION_PRIORITY.get(item["gate_state"], 9),
            item["spec_id"],
        )
    )
    return entries


def stale_worktree_entries(
    specs: list[SpecNode],
    *,
    registered_worktrees: dict[Path, str] | None = None,
) -> list[dict[str, Any]]:
    if not WORKTREES_DIR.exists():
        return []

    referenced = {
        Path(str(node.data.get("last_worktree_path", "")).strip()).expanduser().resolve()
        for node in specs
        if str(node.data.get("last_worktree_path", "")).strip()
    }
    registered = (
        registered_worktrees if registered_worktrees is not None else list_registered_worktrees()
    )
    entries: list[dict[str, Any]] = []
    for child in sorted(WORKTREES_DIR.iterdir()):
        if not child.is_dir():
            continue
        child_resolved = child.resolve()
        if child_resolved in referenced:
            continue
        entries.append(
            {
                "path": child.as_posix(),
                "branch": registered.get(child_resolved, ""),
            }
        )
    return entries


def format_stale_runtime_report(
    *,
    stale_gates: list[dict[str, Any]],
    stale_worktrees: list[dict[str, Any]],
) -> str:
    if not stale_gates and not stale_worktrees:
        return "No stale gate states or worktrees found."

    lines: list[str] = []
    if stale_gates:
        lines.append("Stale gate states:")
        for item in stale_gates:
            lines.append(
                "- "
                f"{item['spec_id']} | gate={item['gate_state']} | "
                f"branch={item['branch'] or '-'} | "
                f"worktree={item['worktree_path'] or '-'} | "
                f"issue={item['issue']}"
            )
    if stale_worktrees:
        lines.append("Stale worktrees:")
        for item in stale_worktrees:
            lines.append(f"- {item['path']} | branch={item['branch'] or '-'}")
    return "\n".join(lines)


def clear_stale_gate(node: SpecNode, *, issue: str) -> None:
    node.data["gate_state"] = "retry_pending"
    node.data["required_human_action"] = "rerun supervisor"
    node.data["proposed_status"] = None
    node.data["proposed_maturity"] = None
    node.data["last_changed_files"] = []
    node.data["last_materialized_child_paths"] = []
    node.data["last_requested_child_materialization"] = False
    node.data["last_worktree_path"] = ""
    node.data["last_branch"] = ""
    node.data["last_gate_decision"] = "stale_cleanup"
    node.data["last_gate_note"] = issue
    node.data["last_gate_at"] = utc_now_iso()
    node.save()


def remove_stale_worktree(path: str, *, branch: str = "") -> None:
    cleanup_isolated_worktree(Path(path), branch)


def handle_stale_runtime(*, specs: list[SpecNode], clean: bool) -> int:
    registered = list_registered_worktrees()
    stale_gates = stale_gate_entries(specs, registered_worktrees=registered)
    stale_worktrees = stale_worktree_entries(specs, registered_worktrees=registered)

    if not clean:
        print(format_stale_runtime_report(stale_gates=stale_gates, stale_worktrees=stale_worktrees))
        return 0

    for item in stale_gates:
        node = next((spec for spec in specs if spec.id == item["spec_id"]), None)
        if node is None:
            continue
        clear_stale_gate(node, issue=item["issue"])

    for item in stale_worktrees:
        remove_stale_worktree(item["path"], branch=item.get("branch", ""))

    refreshed_specs = load_specs()
    refreshed_registered = list_registered_worktrees()
    print(
        format_stale_runtime_report(
            stale_gates=stale_gate_entries(
                refreshed_specs,
                registered_worktrees=refreshed_registered,
            ),
            stale_worktrees=stale_worktree_entries(
                refreshed_specs,
                registered_worktrees=refreshed_registered,
            ),
        )
    )
    return 0


def format_gate_worktree_divergence(paths: list[str], *, limit: int = 8) -> str:
    preview = paths[:limit]
    suffix = "" if len(paths) <= limit else f", ... (+{len(paths) - limit} more)"
    return ", ".join(preview) + suffix


def executor_supports_work_item(
    executor: Callable[..., subprocess.CompletedProcess[str]],
) -> bool:
    try:
        signature = inspect.signature(executor)
    except (TypeError, ValueError):
        return False

    positional = [
        parameter
        for parameter in signature.parameters.values()
        if parameter.kind
        in {
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.VAR_POSITIONAL,
        }
    ]
    has_varargs = any(
        parameter.kind == inspect.Parameter.VAR_POSITIONAL for parameter in positional
    )
    return has_varargs or len(positional) >= 3


def callable_supports_keyword(func: Callable[..., Any], keyword: str) -> bool:
    try:
        signature = inspect.signature(func)
    except (TypeError, ValueError):
        return False

    for parameter in signature.parameters.values():
        if parameter.kind == inspect.Parameter.VAR_KEYWORD:
            return True
    return keyword in signature.parameters


def invoke_executor(
    executor: Callable[..., subprocess.CompletedProcess[str]],
    node: SpecNode,
    worktree_path: Path,
    refactor_work_item: dict[str, Any] | None = None,
    *,
    operator_target: bool = False,
    operator_note: str = "",
    mutation_budget: tuple[str, ...] = (),
    run_authority: tuple[str, ...] = (),
    execution_profile: str | None = None,
    child_model: str | None = None,
    child_timeout_seconds: int | None = None,
    worktree_branch: str = "",
    child_materialization_hint: dict[str, str] | None = None,
    verbose: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Call the executor with optional work-item context when supported.

    `run_codex` and test executors for specialized modes may accept a third
    positional argument carrying refactor/proposal context. Simpler executors
    keep the legacy `(node, worktree_path)` signature.
    """
    if executor is run_codex:
        return executor(
            node,
            worktree_path,
            refactor_work_item,
            operator_target=operator_target,
            operator_note=operator_note,
            mutation_budget=mutation_budget,
            run_authority=run_authority,
            execution_profile=execution_profile,
            child_model=child_model,
            child_timeout_seconds=child_timeout_seconds,
            worktree_branch=worktree_branch,
            child_materialization_hint=child_materialization_hint,
            verbose=verbose,
        )
    if refactor_work_item is not None and (
        executor is run_codex or executor_supports_work_item(executor)
    ):
        return executor(node, worktree_path, refactor_work_item)
    return executor(node, worktree_path)


def child_executor_should_bypass_inner_sandbox(*, branch: str) -> bool:
    _ = branch
    return False


def isolation_mode_for_branch(branch: str) -> str:
    if branch.startswith("sandbox/"):
        return "copied_fallback"
    return "git_worktree"


def codex_cli_reasoning_effort(reasoning_effort: str) -> str:
    """Map supervisor reasoning presets onto the current Codex CLI surface."""
    if reasoning_effort == "xhigh":
        return "high"
    return reasoning_effort


def build_codex_exec_command(
    *,
    prompt: str,
    profile: ExecutionProfile | None = None,
    bypass_inner_sandbox: bool = False,
) -> list[str]:
    """Build a deterministic nested `codex exec` command for spec refinement.

    The supervisor must not silently inherit the operator's global Codex config
    for approval, sandboxing, or optional runtime features. Nested runs should
    stay in a narrow, repeatable bootstrap profile tailored for spec work.
    """
    if profile is None:
        profile = EXECUTION_PROFILES[DEFAULT_EXECUTION_PROFILE_NAME]
    cmd = [
        "codex",
        "exec",
        "--model",
        profile.model,
        "-c",
        f'approval_policy="{profile.approval_policy}"',
        "-c",
        f'model_reasoning_effort="{codex_cli_reasoning_effort(profile.reasoning_effort)}"',
    ]
    _ = bypass_inner_sandbox
    cmd.extend(["--sandbox", profile.sandbox])
    cmd.append(prompt)
    return cmd


def render_child_codex_config(
    *,
    profile: ExecutionProfile | None = None,
    bypass_inner_sandbox: bool = False,
) -> str:
    """Render the minimal isolated Codex config used by nested supervisor runs."""
    if profile is None:
        profile = EXECUTION_PROFILES[DEFAULT_EXECUTION_PROFILE_NAME]
    disabled = "\n".join(f"{feature} = false" for feature in profile.disabled_features)
    _ = bypass_inner_sandbox
    sandbox_line = f'sandbox_mode = "{profile.sandbox}"\n'
    return (
        f'model = "{profile.model}"\n'
        f'model_reasoning_effort = "{codex_cli_reasoning_effort(profile.reasoning_effort)}"\n'
        f'approval_policy = "{profile.approval_policy}"\n'
        f"{sandbox_line}"
        "\n"
        "[features]\n"
        f"{disabled}\n"
    )


def create_child_codex_home(
    *,
    source_codex_home: Path = DEFAULT_CODEX_HOME,
    profile: ExecutionProfile | None = None,
    bypass_inner_sandbox: bool = False,
) -> Path:
    """Create an isolated CODEX_HOME for nested executor runs.

    The child runtime gets a minimal config and only the auth material needed to
    talk to the backend. This avoids inheriting the operator's full state DB,
    MCP server set, and long-lived runtime noise.
    """
    child_home = Path(tempfile.mkdtemp(prefix="codex-child-home-"))
    child_home.mkdir(parents=True, exist_ok=True)
    (child_home / "config.toml").write_text(
        render_child_codex_config(
            profile=profile,
            bypass_inner_sandbox=bypass_inner_sandbox,
        ),
        encoding="utf-8",
    )

    auth_path = source_codex_home / "auth.json"
    if auth_path.exists():
        shutil.copy2(auth_path, child_home / "auth.json")

    return child_home


def run_codex(
    node: SpecNode,
    worktree_path: Path,
    refactor_work_item: dict[str, Any] | None = None,
    *,
    operator_target: bool = False,
    operator_note: str = "",
    mutation_budget: tuple[str, ...] = (),
    run_authority: tuple[str, ...] = (),
    execution_profile: str | None = None,
    child_model: str | None = None,
    child_timeout_seconds: int | None = None,
    worktree_branch: str = "",
    child_materialization_hint: dict[str, str] | None = None,
    verbose: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run the Codex executor in the isolated worktree and stream logs live."""
    bypass_inner_sandbox = child_executor_should_bypass_inner_sandbox(branch=worktree_branch)
    profile = resolve_execution_profile(
        requested_profile=execution_profile,
        run_authority=run_authority,
        operator_target=operator_target,
    )
    if child_model and child_model.strip():
        profile = ExecutionProfile(
            name=profile.name,
            model=child_model.strip(),
            reasoning_effort=profile.reasoning_effort,
            timeout_seconds=profile.timeout_seconds,
            disabled_features=profile.disabled_features,
            approval_policy=profile.approval_policy,
            sandbox=profile.sandbox,
        )
    timeout_seconds = effective_child_executor_timeout_seconds(
        run_authority,
        requested_profile=execution_profile,
        operator_target=operator_target,
        requested_timeout_seconds=child_timeout_seconds,
    )
    cmd = build_codex_exec_command(
        prompt=build_prompt(
            node,
            refactor_work_item,
            operator_target=operator_target,
            operator_note=operator_note,
            mutation_budget=mutation_budget,
            run_authority=run_authority,
            child_materialization_hint=child_materialization_hint,
        ),
        profile=profile,
        bypass_inner_sandbox=bypass_inner_sandbox,
    )
    emit(
        f"Launching codex exec for {node.id} in {worktree_path} "
        "("
        f"profile={profile.name}, "
        f"reasoning={profile.reasoning_effort}, "
        f"model={profile.model}, "
        f"timeout={timeout_seconds}s"
        ")",
        enabled=verbose,
    )
    child_codex_home = create_child_codex_home(
        profile=profile,
        bypass_inner_sandbox=bypass_inner_sandbox,
    )
    env = os.environ.copy()
    env["CODEX_HOME"] = str(child_codex_home)
    try:
        process = subprocess.Popen(
            cmd,
            cwd=worktree_path,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
        )
    except Exception:
        shutil.rmtree(child_codex_home, ignore_errors=True)
        raise

    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []

    def _forward(
        stream: Any,
        sink: list[str],
        prefix: str,
        target: Any,
        *,
        enabled: bool,
    ) -> None:
        try:
            for line in iter(stream.readline, ""):
                sink.append(line)
                if enabled:
                    print(f"{prefix}{line}", end="", file=target)
        finally:
            stream.close()

    stdout_thread = threading.Thread(
        target=_forward,
        args=(process.stdout, stdout_chunks, "[codex stdout] ", sys.stdout),
        kwargs={"enabled": verbose},
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=_forward,
        args=(process.stderr, stderr_chunks, "[codex stderr] ", sys.stderr),
        kwargs={"enabled": verbose},
        daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()
    poll_seconds = max(1, min(EXECUTOR_PROGRESS_POLL_SECONDS, timeout_seconds))
    quiet_progress_windows_allowed = quiet_progress_windows_for_reasoning(profile.reasoning_effort)
    base_timeout_remaining = timeout_seconds
    quiet_windows_without_progress = 0
    last_progress_state = capture_nested_executor_progress(
        worktree_path, stdout_chunks, stderr_chunks
    )
    try:
        while True:
            wait_timeout = (
                poll_seconds
                if base_timeout_remaining <= 0
                else min(poll_seconds, base_timeout_remaining)
            )
            try:
                returncode = process.wait(timeout=wait_timeout)
                break
            except subprocess.TimeoutExpired:
                if base_timeout_remaining > 0:
                    base_timeout_remaining = max(0, base_timeout_remaining - wait_timeout)
                current_progress_state = capture_nested_executor_progress(
                    worktree_path,
                    stdout_chunks,
                    stderr_chunks,
                )
                if base_timeout_remaining <= 0:
                    if quiet_progress_windows_allowed <= 0:
                        raise
                    if current_progress_state != last_progress_state:
                        last_progress_state = current_progress_state
                        quiet_windows_without_progress = 0
                        emit(
                            "[codex stderr] supervisor progress grace: "
                            "nested executor still shows progress after the base timeout; "
                            "continuing to wait",
                            file=sys.stderr,
                            enabled=verbose,
                        )
                        continue
                    if quiet_windows_without_progress < quiet_progress_windows_allowed:
                        quiet_windows_without_progress += 1
                        emit(
                            "[codex stderr] supervisor quiet grace: "
                            f"no new progress detected after base timeout "
                            f"({quiet_windows_without_progress}/{quiet_progress_windows_allowed}); "
                            "allowing more deliberation",
                            file=sys.stderr,
                            enabled=verbose,
                        )
                        continue
                    raise
                if current_progress_state != last_progress_state:
                    last_progress_state = current_progress_state
                    quiet_windows_without_progress = 0
                    continue
                continue
    except subprocess.TimeoutExpired:
        process.kill()
        returncode = 124
        timeout_message = (
            f"supervisor timeout: nested executor timed out after {timeout_seconds} seconds\n"
        )
        stderr_chunks.append(timeout_message)
        emit(f"[codex stderr] {timeout_message.rstrip()}", file=sys.stderr)
        process.wait()
        stdout_thread.join()
        stderr_thread.join()
    finally:
        shutil.rmtree(child_codex_home, ignore_errors=True)

    return subprocess.CompletedProcess(
        args=cmd,
        returncode=returncode,
        stdout="".join(stdout_chunks),
        stderr="".join(stderr_chunks),
    )


def resolve_gate_decision(
    *,
    specs: list[SpecNode],
    spec_id: str,
    decision: str,
    note: str,
) -> int:
    decision = decision.strip().lower()
    allowed = {"approve", "retry", "split", "block", "redirect", "escalate"}
    if decision not in allowed:
        print(f"Unsupported decision: {decision}", file=sys.stderr)
        return 1

    index = index_specs(specs)
    node = index.get(spec_id)
    if node is None:
        print(f"Spec not found: {spec_id}", file=sys.stderr)
        return 1

    retained_worktree_value = str(node.data.get("last_worktree_path", "")).strip()
    retained_worktree_path = (
        Path(retained_worktree_value).expanduser() if retained_worktree_value else None
    )
    retained_branch = str(node.data.get("last_branch", "")).strip()

    if decision == "approve":
        if node.gate_state != "review_pending":
            print(f"Spec {spec_id} is not in review_pending gate.", file=sys.stderr)
            return 1

        proposed_status = node.data.get("proposed_status")
        proposed_maturity = node.data.get("proposed_maturity")
        before_node_data = copy.deepcopy(node.data)
        if proposed_status is not None and proposed_status != node.status:
            transition_errors = validate_transition(node.status, proposed_status)
            if transition_errors:
                print("\n".join(transition_errors), file=sys.stderr)
                return 1

        freshness_issue = gate_worktree_freshness_issue(node)
        if freshness_issue:
            print(
                f"Spec {spec_id} review gate is stale: {freshness_issue}. "
                "Rerun supervisor or clean stale runtime state before approval.",
                file=sys.stderr,
            )
            return 1

        worktree_path = Path(str(node.data.get("last_worktree_path", ""))).expanduser()
        pending_sync_paths = pending_review_sync_paths(node)
        changed_files = list(node.data.get("last_changed_files", []))
        materialized_child_paths = list(node.data.get("last_materialized_child_paths", []))
        if worktree_path.as_posix() and worktree_path.exists():
            allowed_changes = pending_sync_paths or select_sync_paths(
                node.allowed_paths, changed_files
            )
            has_pending_candidate_digests = bool(
                coerce_pending_digest_map(node.data.get("pending_candidate_digests"))
            )
            has_pending_base_digests = bool(
                coerce_pending_digest_map(node.data.get("pending_base_digests"))
            )
            candidate_divergence_paths = pending_review_candidate_divergence_paths(
                node, worktree_path, allowed_changes
            )
            base_divergence_paths = pending_review_base_divergence_paths(node, allowed_changes)
            if has_pending_candidate_digests or has_pending_base_digests:
                divergence_paths = candidate_divergence_paths + base_divergence_paths
            else:
                divergence_paths = gate_worktree_divergence_paths(
                    node, worktree_path, allowed_changes
                )
            if divergence_paths:
                print(
                    (
                        f"Spec {spec_id} review gate is stale: current canonical content differs "
                        "from last_worktree_path at "
                        f"{format_gate_worktree_divergence(divergence_paths)}. "
                        "Rerun supervisor or reconcile the gate before approval."
                    ),
                    file=sys.stderr,
                )
                return 1
            sync_files_from_worktree(worktree_path, allowed_changes)
            normalize_materialized_child_specs(materialized_child_paths)
            # Keep approved content from the worktree while attaching gate metadata in root.
            node.reload()
            restore_ephemeral_child_authority_fields(
                node=node,
                before_data=before_node_data,
                requested=bool(before_node_data.get("last_requested_child_materialization", False)),
            )

        if proposed_status:
            node.data["status"] = proposed_status
        if proposed_maturity is not None:
            node.data["maturity"] = proposed_maturity

        node.data["gate_state"] = "none"
        node.data["proposed_status"] = None
        node.data["proposed_maturity"] = None
        node.data["required_human_action"] = "-"
        clear_pending_review_state(node)
    else:
        gate_map = {
            "retry": ("retry_pending", "rerun supervisor"),
            "split": ("split_required", "split spec scope before rerun"),
            "block": ("blocked", "resolve blocker"),
            "redirect": ("redirected", "update prompt/scope and rerun"),
            "escalate": ("escalated", "manual escalation"),
        }
        gate_state, required_action = gate_map[decision]
        node.data["gate_state"] = gate_state
        node.data["required_human_action"] = required_action
        node.data["proposed_status"] = None
        node.data["proposed_maturity"] = None
        clear_pending_review_state(node)

    node.data["last_worktree_path"] = ""
    node.data["last_branch"] = ""
    node.data["last_gate_decision"] = decision
    node.data["last_gate_note"] = note
    node.data["last_gate_at"] = utc_now_iso()
    node.save()
    refresh_latest_summary_for_gate_resolution(node)

    if retained_worktree_path is not None:
        cleanup_isolated_worktree(retained_worktree_path, retained_branch)

    print(f"Resolved gate for {spec_id}: {decision}")
    return 0


def _apply_split_proposal(
    *,
    node: SpecNode,
    specs: list[SpecNode],
) -> int:
    """Apply one reviewed split proposal into canonical spec files.

    This path is deterministic by design. It does not ask an agent to invent a
    new split; it materializes the already structured proposal artifact.
    """
    proposal_item = find_split_proposal_queue_item(node.id)
    if proposal_item is None:
        print(
            f"No applicable {SPLIT_REFACTOR_KIND} proposal found for {node.id}",
            file=sys.stderr,
        )
        return 1

    proposal_artifact_path = proposal_item_path(proposal_item)
    proposal_artifact, artifact_error = load_json_object_report(
        proposal_artifact_path,
        artifact_kind="split proposal artifact",
    )
    if proposal_artifact is None:
        print(
            (
                artifact_error
                or f"Missing or invalid proposal artifact: {proposal_artifact_path.as_posix()}"
            ),
            file=sys.stderr,
        )
        return 1

    eligibility_errors = validate_split_proposal_application_target(
        node=node,
        proposal_item=proposal_item,
        proposal_artifact=proposal_artifact,
        current_index=index_specs(specs),
    )
    if eligibility_errors:
        for error in eligibility_errors:
            print(error, file=sys.stderr)
        return 1

    run_id = make_run_id(node.id)
    proposal_queue_before = load_proposal_queue()
    refactor_queue_before = load_refactor_queue()
    selected_by_rule = {
        "selection_mode": "apply_split_proposal",
        "operator_target": node.id,
        "sort_order": policy_lookup("selection_priorities.explicit_target_sort_order"),
        "proposal_item": {
            "id": str(proposal_item.get("id", "")),
            "proposal_type": str(proposal_item.get("proposal_type", "")),
            "signal": str(proposal_item.get("signal", "")),
            "refactor_kind": str(proposal_item.get("refactor_kind", "")),
            "status": str(proposal_item.get("status", "")),
            "proposal_artifact_path": proposal_artifact_path.as_posix(),
        },
    }

    try:
        worktree_path, branch = create_isolated_worktree(node.id)
    except RuntimeError as exc:
        print(f"Failed to create worktree: {exc}", file=sys.stderr)
        return 1
    print(f"Created worktree: {worktree_path}")
    print(f"Branch: {branch}")
    synced_node_path = sync_current_node_into_worktree(node, worktree_path)
    print(f"Seeded worktree node from current tree: {synced_node_path}")
    supporting_inputs = sync_local_input_specs_into_worktree(node, worktree_path)
    if supporting_inputs:
        print(
            "Seeded supporting input specs from current tree: "
            + ", ".join(path.as_posix() for path in supporting_inputs)
        )

    before_status = node.status
    validation_errors: list[str] = []
    artifact_io_errors: list[str] = []
    try:
        changed = apply_split_proposal_to_worktree(
            node=node,
            proposal_artifact=proposal_artifact,
            worktree_path=worktree_path,
        )
        worktree_specs = load_specs_from_dir(worktree_path / "specs" / "nodes")
    except Exception as exc:
        changed = []
        worktree_specs = []
        validation_errors.append(str(exc))
    else:
        output_errors = validate_changed_spec_nodes(
            source_node_id=node.id,
            changed_files=changed,
            worktree_specs=worktree_specs,
            worktree_path=worktree_path,
        )
        atomicity_errors = validate_changed_spec_atomicity(
            source_node_id=node.id,
            changed_files=changed,
            worktree_specs=worktree_specs,
            worktree_path=worktree_path,
        )
        reconciliation, reconciliation_errors = reconcile_graph(
            source_node=node,
            worktree_path=worktree_path,
            changed_files=changed,
        )
        validation_errors.extend(output_errors)
        validation_errors.extend(atomicity_errors)
        validation_errors.extend(reconciliation_errors)
        if not validation_errors:
            sync_files_from_worktree(worktree_path, changed)
            node.reload()
            try:
                mark_split_proposal_applied(
                    proposal_item=proposal_item,
                    proposal_artifact_path=proposal_artifact_path,
                    proposal_artifact=proposal_artifact,
                    run_id=run_id,
                )
            except RuntimeError as exc:
                artifact_io_errors.append(str(exc))
                validation_errors.append(str(exc))
            current_specs = load_specs()
            current_index = index_specs(current_specs)
            reconciled_node = current_index.get(node.id) or node
            graph_health = observe_graph_health(
                source_node=node,
                worktree_specs=current_specs,
                reconciliation={
                    "semantic_dependencies_resolved": semantic_dependencies_resolved(
                        reconciled_node, current_index
                    ),
                    "work_dependencies_ready": work_dependencies_ready(
                        reconciled_node, current_index
                    ),
                },
                atomicity_errors=validate_atomicity(reconciled_node),
                outcome="done",
            )
            proposal_queue_artifact = proposal_queue_path()
            proposal_items = load_proposal_queue()
            sync_tracked_proposal_lane_from_queue(
                proposal_items,
                item_ids={str(proposal_item.get("id", "")).strip()},
            )
            if not validation_errors:
                try:
                    refactor_queue_artifact = update_refactor_queue(
                        graph_health=graph_health,
                        run_id=run_id,
                        proposal_items=proposal_items,
                    )
                except RuntimeError as exc:
                    artifact_io_errors.append(str(exc))
                    validation_errors.append(str(exc))
                    refactor_queue_artifact = refactor_queue_path()
            else:
                refactor_queue_artifact = refactor_queue_path()
        else:
            graph_health = {
                "source_spec_id": node.id,
                "observations": [],
                "signals": [],
                "recommended_actions": [],
            }
            proposal_queue_artifact = proposal_queue_path()
            refactor_queue_artifact = refactor_queue_path()

    if validation_errors:
        graph_health = {
            "source_spec_id": node.id,
            "observations": [],
            "signals": [],
            "recommended_actions": [],
        }
        proposal_queue_artifact = proposal_queue_path()
        refactor_queue_artifact = refactor_queue_path()

    success = not validation_errors
    proposal_queue_after = load_proposal_queue()
    refactor_queue_after = load_refactor_queue()
    decision_inspector = build_decision_inspector(
        run_id=run_id,
        spec_id=node.id,
        selected_by_rule=selected_by_rule,
        outcome="done" if success else "blocked",
        gate_state="none",
        required_human_action="-" if success else "repair proposal before retry",
        blocker="none" if success else "split proposal application failed",
        changed_files=changed,
        validation_errors=validation_errors,
        validator_results={
            "proposal_artifact": not validation_errors,
            "canonical_writeback": success,
            "runtime_artifacts": not artifact_io_errors,
        },
        graph_health=graph_health,
        graph_health_truth_basis="accepted_canonical",
        proposal_queue_before=proposal_queue_before,
        proposal_queue_after=proposal_queue_after,
        refactor_queue_before=refactor_queue_before,
        refactor_queue_after=refactor_queue_after,
    )
    decision_inspector_artifact = write_decision_inspector_artifact(run_id, decision_inspector)
    payload = {
        "run_id": run_id,
        "timestamp_utc": utc_now_iso(),
        "spec_id": node.id,
        "title": node.title,
        "completion_status": COMPLETION_STATUS_OK if success else COMPLETION_STATUS_FAILED,
        "selected_by_rule": selected_by_rule,
        "before_status": before_status,
        "proposed_status": None,
        "final_status": node.status,
        "outcome": "done" if success else "blocked",
        "blocker": "none" if success else "split proposal application failed",
        "gate_state": "none",
        "required_human_action": "-" if success else "repair proposal before retry",
        "exit_code": 0 if success else 1,
        "auto_approved": False,
        "worktree_path": worktree_path.as_posix(),
        "isolation_mode": isolation_mode_for_branch(branch),
        "branch": branch,
        "changed_files": changed,
        "validation_errors": validation_errors,
        "validator_results": {
            "proposal_artifact": not validation_errors,
            "canonical_writeback": success,
            "runtime_artifacts": not artifact_io_errors,
        },
        "reconciliation": {},
        "graph_health": graph_health,
        "graph_health_truth_basis": "accepted_canonical",
        "decision_inspector": decision_inspector,
        "decision_inspector_artifact": decision_inspector_artifact.as_posix(),
        "refactor_queue_artifact": refactor_queue_artifact.as_posix(),
        "proposal_queue_artifact": proposal_queue_artifact.as_posix(),
        "proposal_artifact_path": proposal_artifact_path.as_posix(),
        "stdout": "",
        "stderr": "",
    }
    log_path = write_run_log(run_id, payload)
    write_latest_summary(payload)
    print(f"Run log: {log_path.as_posix()}")
    print("Finished status:", payload["completion_status"])
    if validation_errors:
        print("\n=== validation errors ===", file=sys.stderr)
        for error in validation_errors:
            print(f"- {error}", file=sys.stderr)
    cleanup_isolated_worktree(worktree_path, branch)
    return 0 if success else 1


def _process_split_refactor_proposal(
    *,
    node: SpecNode,
    executor: Callable[[SpecNode, Path], subprocess.CompletedProcess[str]],
    operator_note: str = "",
    execution_profile: str | None = None,
    child_model: str | None = None,
    child_timeout_seconds: int | None = None,
    verbose: bool = False,
) -> tuple[int, str]:
    """Run the explicit proposal-first split pass for one oversized non-seed spec.

    This path is intentionally more restrictive than ordinary refinement:
    - explicit operator target only
    - no canonical spec writeback
    - no status or maturity promotion
    - exactly one structured proposal artifact written under `runs/proposals/`
    - proposal queue refreshed as an index, not as the full payload store
    """
    run_id = make_run_id(node.id)
    proposal_queue_before = load_proposal_queue()
    refactor_queue_before = load_refactor_queue()
    refactor_work_item = build_split_refactor_work_item(node)
    refactor_work_item["planned_run_id"] = run_id
    selected_by_rule = {
        "selection_mode": "split_refactor_proposal",
        "operator_target": node.id,
        "sort_order": policy_lookup("selection_priorities.explicit_target_sort_order"),
        "refactor_work_item": {
            "id": str(refactor_work_item.get("id", "")),
            "proposal_type": str(refactor_work_item.get("proposal_type", "")),
            "signal": str(refactor_work_item.get("signal", "")),
            "refactor_kind": str(refactor_work_item.get("refactor_kind", "")),
            "execution_policy": str(refactor_work_item.get("execution_policy", "")),
            "proposal_artifact_relpath": str(
                refactor_work_item.get("proposal_artifact_relpath", "")
            ),
        },
    }
    if operator_note.strip():
        selected_by_rule["operator_note"] = operator_note.strip()
    selected_by_rule["execution_profile"] = resolve_execution_profile_name(
        requested_profile=execution_profile,
        run_authority=(),
        operator_target=True,
    )
    before_status = node.status

    try:
        worktree_path, branch = create_isolated_worktree(node.id)
    except RuntimeError as exc:
        print(f"Failed to create worktree: {exc}", file=sys.stderr)
        return 1, "escalate"
    emit(f"Created worktree: {worktree_path}", enabled=verbose)
    emit(f"Branch: {branch}", enabled=verbose)
    synced_node_path = sync_current_node_into_worktree(node, worktree_path)
    emit(f"Seeded worktree node from current tree: {synced_node_path}", enabled=verbose)
    supporting_inputs = sync_local_input_specs_into_worktree(node, worktree_path)
    if supporting_inputs:
        emit(
            "Seeded supporting input specs from current tree: "
            + ", ".join(path.as_posix() for path in supporting_inputs),
            enabled=verbose,
        )

    before = git_changed_files(worktree_path)
    tracked_paths = sorted(set(before))
    before_digests = snapshot_file_digests(tracked_paths, base_dir=worktree_path)
    emit(f"Starting executor for {node.id}...", enabled=verbose)
    invoke_kwargs: dict[str, Any] = {
        "operator_target": True,
        "operator_note": operator_note,
        "execution_profile": execution_profile,
        "child_model": child_model,
        "child_timeout_seconds": child_timeout_seconds,
        "worktree_branch": branch,
    }
    if callable_supports_keyword(invoke_executor, "verbose"):
        invoke_kwargs["verbose"] = verbose
    result = invoke_executor(
        executor,
        node,
        worktree_path,
        refactor_work_item,
        **invoke_kwargs,
    )
    result = subprocess.CompletedProcess(
        args=result.args,
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=normalize_executor_stderr(result.stderr),
    )
    emit(f"Executor finished for {node.id} with exit_code={result.returncode}", enabled=verbose)
    after = git_changed_files(worktree_path)
    tracked_paths = sorted(set(before) | set(after))
    after_digests = snapshot_file_digests(tracked_paths, base_dir=worktree_path)
    before_set = set(before)
    after_set = set(after)
    changed = sorted(
        path
        for path in tracked_paths
        if before_digests.get(path) != after_digests.get(path)
        or (path in (after_set - before_set) and not is_spec_node_path(path))
    )
    emit(f"Detected changed files: {changed or ['(none)']}", enabled=verbose)
    outcome, blocker, executor_protocol_errors = parse_executor_protocol(
        result.stdout,
        result.returncode,
    )
    executor_environment = classify_executor_environment(result.stderr)
    primary_executor_failure = is_primary_executor_environment_failure(
        executor_environment=executor_environment,
        returncode=result.returncode,
        changed_files=changed,
        outcome=outcome,
    )
    executor_environment["primary_failure"] = primary_executor_failure
    if primary_executor_failure and outcome == "escalate":
        outcome = "blocked"
        if not blocker:
            blocker = "executor environment failure"

    if primary_executor_failure:
        worktree_specs = []
        graph_health = empty_graph_health(node.id)
        validation_errors = executor_environment_validation_errors(executor_environment)
    else:
        try:
            worktree_specs = load_specs_from_dir(worktree_path / "specs" / "nodes")
        except Exception as exc:
            worktree_specs = []
            graph_health = empty_graph_health(node.id)
            validation_errors = [
                f"Failed to load worktree specs for split proposal validation: {exc}"
            ]
        else:
            index = index_specs(worktree_specs)
            reconciled_node = index.get(node.id) or node
            graph_health = observe_graph_health(
                source_node=node,
                worktree_specs=worktree_specs,
                reconciliation={
                    "semantic_dependencies_resolved": semantic_dependencies_resolved(
                        reconciled_node, index
                    ),
                    "work_dependencies_ready": work_dependencies_ready(reconciled_node, index),
                },
                atomicity_errors=validate_atomicity(reconciled_node),
                outcome=outcome,
            )
            validation_errors: list[str] = []
    validation_errors.extend(executor_protocol_errors)

    artifact_relpath = str(refactor_work_item["proposal_artifact_relpath"])
    artifact_worktree_path = worktree_path / artifact_relpath
    proposal_artifact_root_path = ROOT / artifact_relpath
    allowed_changed_paths = split_proposal_allowed_changed_paths(artifact_relpath)
    changed_spec_files = [path for path in changed if is_spec_node_path(path)]
    extra_changed_files = [path for path in changed if path not in allowed_changed_paths]
    if changed_spec_files:
        validation_errors.append(
            "split proposal mode must not modify canonical spec files: "
            + ", ".join(changed_spec_files)
        )
    if extra_changed_files:
        validation_errors.append(
            "split proposal mode must only write the structured proposal artifact: "
            + ", ".join(extra_changed_files)
        )

    artifact_io_errors: list[str] = []
    proposal_artifact_data: dict[str, Any] | None = None
    if outcome == "done":
        proposal_artifact_data, artifact_error = load_json_object_report(
            artifact_worktree_path,
            artifact_kind="structured split proposal artifact",
        )
        if proposal_artifact_data is None:
            validation_errors.append(
                artifact_error
                or f"Missing or invalid structured split proposal artifact: {artifact_relpath}"
            )
        else:
            existing_queue_item = next(
                (
                    item
                    for item in load_proposal_queue()
                    if str(item.get("id", "")).strip()
                    == f"refactor_proposal::{node.id}::{SPLIT_REFACTOR_SIGNAL}"
                ),
                None,
            )
            proposal_artifact_data["source_run_ids"] = merge_unique_strings(
                signal_supporting_run_ids(node.id, SPLIT_REFACTOR_SIGNAL),
                (
                    list(existing_queue_item.get("supporting_run_ids", []))
                    if existing_queue_item
                    else []
                ),
                [run_id],
                list(proposal_artifact_data.get("source_run_ids", [])),
            )
            validation_errors.extend(
                validate_split_proposal_artifact(
                    artifact=proposal_artifact_data,
                    node=node,
                    run_id=run_id,
                )
            )

    success = result.returncode == 0 and not validation_errors and outcome == "done"
    proposal_queue_artifact = proposal_queue_path()
    refactor_queue_artifact = refactor_queue_path()

    if success and proposal_artifact_data is not None:
        sync_files_from_worktree(worktree_path, [artifact_relpath])
        with artifact_lock(proposal_artifact_root_path):
            atomic_write_json(proposal_artifact_root_path, proposal_artifact_data)
        try:
            proposal_queue_artifact, _proposal_items = upsert_split_proposal_queue(
                node=node,
                run_id=run_id,
                artifact=proposal_artifact_data,
                artifact_path=proposal_artifact_root_path,
            )
        except RuntimeError as exc:
            artifact_io_errors.append(str(exc))
            validation_errors.append(str(exc))
            success = False
            outcome = "blocked"
            blocker = blocker or "runtime artifact failure"

    required_human_action = (
        "review structured split proposal"
        if success
        else "fix split proposal or rerun with a different operator target"
    )
    proposal_queue_after = load_proposal_queue()
    refactor_queue_after = load_refactor_queue()
    decision_inspector = build_decision_inspector(
        run_id=run_id,
        spec_id=node.id,
        selected_by_rule=selected_by_rule,
        outcome=outcome,
        gate_state="none",
        required_human_action=required_human_action,
        blocker=blocker,
        changed_files=changed,
        validation_errors=validation_errors,
        validator_results={
            "target_eligibility": True,
            "proposal_artifact": success,
            "canonical_writeback": not changed_spec_files,
            "artifact_scope": not extra_changed_files,
            "executor_environment": not primary_executor_failure,
            "runtime_artifacts": not artifact_io_errors,
        },
        graph_health=graph_health,
        graph_health_truth_basis="review_candidate",
        proposal_queue_before=proposal_queue_before,
        proposal_queue_after=proposal_queue_after,
        refactor_queue_before=refactor_queue_before,
        refactor_queue_after=refactor_queue_after,
    )
    decision_inspector_artifact = write_decision_inspector_artifact(run_id, decision_inspector)
    payload = {
        "run_id": run_id,
        "timestamp_utc": utc_now_iso(),
        "spec_id": node.id,
        "title": node.title,
        "completion_status": COMPLETION_STATUS_OK if success else COMPLETION_STATUS_FAILED,
        "selected_by_rule": selected_by_rule,
        "before_status": before_status,
        "proposed_status": None,
        "final_status": before_status,
        "outcome": outcome,
        "blocker": blocker,
        "gate_state": "none",
        "required_human_action": required_human_action,
        "exit_code": result.returncode,
        "auto_approved": False,
        "worktree_path": worktree_path.as_posix(),
        "isolation_mode": isolation_mode_for_branch(branch),
        "branch": branch,
        "changed_files": changed,
        "validation_errors": validation_errors,
        "validator_results": {
            "target_eligibility": True,
            "proposal_artifact": success,
            "canonical_writeback": not changed_spec_files,
            "artifact_scope": not extra_changed_files,
            "executor_environment": not primary_executor_failure,
            "runtime_artifacts": not artifact_io_errors,
        },
        "reconciliation": {
            "semantic_dependencies_resolved": graph_health["source_spec_id"] == node.id,
            "work_dependencies_ready": False,
        },
        "graph_health": graph_health,
        "graph_health_truth_basis": "review_candidate",
        "decision_inspector": decision_inspector,
        "decision_inspector_artifact": decision_inspector_artifact.as_posix(),
        "executor_environment": executor_environment,
        "refactor_queue_artifact": refactor_queue_artifact.as_posix(),
        "proposal_queue_artifact": proposal_queue_artifact.as_posix(),
        "proposal_artifact_path": proposal_artifact_root_path.as_posix(),
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
    log_path = write_run_log(run_id, payload)
    write_latest_summary(payload)

    cleanup_isolated_worktree(worktree_path, branch)
    emit_run_footer(
        log_path=log_path,
        completion_status=payload["completion_status"],
        stdout=result.stdout,
        stderr=result.stderr,
        validation_errors=validation_errors,
        verbose=verbose,
    )

    return (0 if success else 1), outcome


def _process_one_spec(
    *,
    node: SpecNode,
    specs: list[SpecNode],
    executor: Callable[[SpecNode, Path], subprocess.CompletedProcess[str]],
    auto_approve: bool,
    refactor_work_item: dict[str, Any] | None = None,
    operator_target: bool = False,
    operator_note: str = "",
    mutation_budget: tuple[str, ...] = (),
    run_authority: tuple[str, ...] = (),
    execution_profile: str | None = None,
    child_model: str | None = None,
    child_timeout_seconds: int | None = None,
    verbose: bool = False,
) -> tuple[int, str, str, str]:
    """Process one ordinary supervisor run.

    This is the main path for:
    - default refinement
    - explicit operator-targeted refinement
    - ancestor reconciliation
    - queue-selected graph_refactor direct updates

    The function owns worktree creation, executor invocation, validation,
    graph-health derivation, queue refresh, and optional auto-approval.
    """
    is_graph_refactor_run = (
        refactor_work_item is not None
        and str(refactor_work_item.get("work_item_type", "")).strip() == "graph_refactor"
    )
    dependents = reverse_dependents_count(specs)
    selection_mode = selection_mode_for_node(
        node,
        specs,
        refactor_work_item=refactor_work_item,
        operator_target=operator_target,
    )
    effective_execution_profile = infer_ordinary_execution_profile_name(
        node=node,
        specs=specs,
        requested_profile=execution_profile,
        operator_target=operator_target,
        run_authority=run_authority,
    )
    selected_by_rule = {
        "status_filter": sorted(WORKABLE_STATUSES),
        "dependency_required_statuses": sorted(READY_DEP_STATUSES),
        "selection_mode": selection_mode,
        "sort_order": policy_lookup("selection_priorities.ordinary_sort_order"),
        "dependents_count": dependents.get(node.id, 0),
    }
    if operator_target:
        selected_by_rule["operator_target"] = node.id
        selected_by_rule["sort_order"] = policy_lookup(
            "selection_priorities.explicit_target_sort_order"
        )
    if operator_note.strip():
        selected_by_rule["operator_note"] = operator_note.strip()
    if mutation_budget:
        selected_by_rule["mutation_budget"] = list(mutation_budget)
    if run_authority:
        selected_by_rule["run_authority"] = list(run_authority)
    selected_by_rule["execution_profile"] = effective_execution_profile
    if refactor_work_item is not None:
        selected_by_rule["refactor_work_item"] = {
            "id": str(refactor_work_item.get("id", "")),
            "work_item_type": str(refactor_work_item.get("work_item_type", "")),
            "signal": str(refactor_work_item.get("signal", "")),
            "recommended_action": str(refactor_work_item.get("recommended_action", "")),
            "source_run_id": str(refactor_work_item.get("source_run_id", "")),
        }

    before_status = node.status
    proposal_queue_before = load_proposal_queue()
    refactor_queue_before = load_refactor_queue()
    before_source_text = node.path.read_text(encoding="utf-8")
    before_node_data = copy.deepcopy(node.data)
    before_canonical = canonical_spec_snapshot(node.data)
    source_spec_relpath = node.path.relative_to(ROOT).as_posix()
    run_id = make_run_id(node.id)
    child_materialization_requested = targeted_child_materialization_requested(
        node=node,
        operator_target=operator_target,
        operator_note=operator_note,
        run_authority=run_authority,
    )
    reserved_child_materialization_hint: dict[str, str] | None = None
    if child_materialization_requested:
        try:
            reserved_child_materialization_hint = reserve_child_materialization_spec_id(
                specs=specs,
                source_spec_id=node.id,
                run_id=run_id,
            )
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 1, "blocked"
    child_materialization_preflight = child_materialization_preflight_errors(
        node=node,
        specs=specs,
        operator_target=operator_target,
        operator_note=operator_note,
        run_authority=run_authority,
        child_materialization_hint=reserved_child_materialization_hint,
    )
    if child_materialization_preflight:
        if reserved_child_materialization_hint is not None:
            release_child_materialization_spec_id(
                spec_id=reserved_child_materialization_hint["id"],
                run_id=run_id,
            )
        for error in child_materialization_preflight:
            print(error, file=sys.stderr)
        return 1, "blocked"
    child_materialization_hint = targeted_child_materialization_hint(
        node,
        specs,
        operator_target=operator_target,
        operator_note=operator_note,
        run_authority=run_authority,
        reserved_hint=reserved_child_materialization_hint,
    )
    effective_allowed_paths = effective_allowed_paths_for_run(
        node,
        child_materialization_hint=child_materialization_hint,
    )
    if child_materialization_hint is not None:
        selected_by_rule["reserved_child_spec"] = dict(child_materialization_hint)

    try:
        worktree_path, branch = create_isolated_worktree(node.id)
    except RuntimeError as exc:
        if child_materialization_hint is not None:
            release_child_materialization_spec_id(
                spec_id=child_materialization_hint["id"],
                run_id=run_id,
            )
        print(f"Failed to create worktree: {exc}", file=sys.stderr)
        return 1, "escalate"
    emit(f"Created worktree: {worktree_path}", enabled=verbose)
    emit(f"Branch: {branch}", enabled=verbose)
    synced_node_path = sync_current_node_into_worktree(node, worktree_path)
    emit(f"Seeded worktree node from current tree: {synced_node_path}", enabled=verbose)
    supporting_inputs = sync_local_input_specs_into_worktree(node, worktree_path)
    if supporting_inputs:
        emit(
            "Seeded supporting input specs from current tree: "
            + ", ".join(path.as_posix() for path in supporting_inputs),
            enabled=verbose,
        )

    before = git_changed_files(worktree_path)
    tracked_paths = sorted(set(before))
    before_digests = snapshot_file_digests(tracked_paths, base_dir=worktree_path)
    emit(f"Starting executor for {node.id}...", enabled=verbose)
    invoke_kwargs: dict[str, Any] = {
        "operator_target": operator_target,
        "operator_note": operator_note,
        "mutation_budget": mutation_budget,
        "run_authority": run_authority,
        "execution_profile": effective_execution_profile,
        "child_model": child_model,
        "child_timeout_seconds": child_timeout_seconds,
        "worktree_branch": branch,
    }
    if callable_supports_keyword(invoke_executor, "child_materialization_hint"):
        invoke_kwargs["child_materialization_hint"] = child_materialization_hint
    if callable_supports_keyword(invoke_executor, "verbose"):
        invoke_kwargs["verbose"] = verbose
    result = invoke_executor(
        executor,
        node,
        worktree_path,
        refactor_work_item,
        **invoke_kwargs,
    )
    emit(f"Executor finished for {node.id} with exit_code={result.returncode}", enabled=verbose)
    after = git_changed_files(worktree_path)
    tracked_paths = sorted(set(before) | set(after))
    after_digests = snapshot_file_digests(tracked_paths, base_dir=worktree_path)
    before_set = set(before)
    after_set = set(after)
    changed = sorted(
        path
        for path in tracked_paths
        if before_digests.get(path) != after_digests.get(path)
        or (path in (after_set - before_set) and not is_spec_node_path(path))
    )
    outcome, blocker, executor_protocol_errors = parse_executor_protocol(
        result.stdout,
        result.returncode,
    )
    yaml_repair_paths: list[str] = []
    if result.returncode == 0 and outcome in {"done", "split_required"} and changed:
        yaml_repair_paths = repair_worktree_changed_spec_yaml(
            repo_root=ROOT,
            worktree_path=worktree_path,
            changed_files=changed,
        )
        if yaml_repair_paths:
            emit(
                f"Repaired worktree YAML candidates: {yaml_repair_paths}",
                enabled=verbose,
            )
            after = git_changed_files(worktree_path)
            tracked_paths = sorted(set(before) | set(after))
            after_digests = snapshot_file_digests(tracked_paths, base_dir=worktree_path)
            after_set = set(after)
            changed = sorted(
                path
                for path in tracked_paths
                if before_digests.get(path) != after_digests.get(path)
                or (path in (after_set - before_set) and not is_spec_node_path(path))
            )
    emit(f"Detected changed files: {changed or ['(none)']}", enabled=verbose)
    materialized_child_paths = (
        [path for path in changed if is_spec_node_path(path) and path != source_spec_relpath]
        if child_materialization_requested
        else []
    )

    executor_environment = classify_executor_environment(result.stderr)
    primary_executor_failure = is_primary_executor_environment_failure(
        executor_environment=executor_environment,
        returncode=result.returncode,
        changed_files=changed,
        outcome=outcome,
    )
    executor_environment["primary_failure"] = primary_executor_failure
    if primary_executor_failure and outcome == "escalate":
        outcome = "blocked"
        if not blocker:
            blocker = "executor environment failure"

    refinement_acceptance = {
        "decision": REFINEMENT_ACCEPT_DECISION_REJECT,
        "change_class": REFINEMENT_CLASS_LOCAL,
        "checks": {
            "content_changed": False,
            "hard_validation": False,
            "single_spec_scope": True,
            "constitutional_diff": False,
            "graph_refactor_diff": False,
            "atomicity_clear": True,
            "within_mutation_budget": True,
        },
        "diff_paths": [],
        "mutation_classes": [],
        "mutation_budget": list(mutation_budget),
        "budget_exceeded_classes": [],
        "changed_spec_files": [],
        "review_reasons": [],
        "errors": ["refinement acceptance was not evaluated"],
        "warnings": [],
    }
    executor_requested_split_required = False

    if primary_executor_failure:
        worktree_specs = []
        worktree_load_errors = []
        output_errors = []
        allowed_path_errors = []
        reconciliation = {
            "worktree_spec_count": 0,
            "changed_spec_ids": [],
            "semantic_dependencies_resolved": False,
            "work_dependencies_ready": False,
            "cycles": [],
        }
        reconciliation_errors = []
        atomicity_errors = []
        proposed_status = None if is_graph_refactor_run else STATUS_PROGRESSION.get(node.status)
        transition_errors = []
        validation_errors = executor_environment_validation_errors(executor_environment)
        validation_errors.extend(executor_protocol_errors)
        candidate_graph_health = empty_graph_health(node.id)
        proposal_queue_artifact = proposal_queue_path()
        refactor_queue_artifact = refactor_queue_path()
        candidate_after_data = before_canonical
    else:
        try:
            worktree_specs = load_specs_from_dir(worktree_path / "specs" / "nodes")
        except Exception as exc:
            worktree_specs = []
            worktree_load_errors = [f"Failed to load worktree specs for validation: {exc}"]
        else:
            worktree_load_errors = []

        output_errors = validate_outputs(node, base_dir=worktree_path)
        allowed_path_errors = validate_changed_files_against_allowed_paths(
            effective_allowed_paths, changed
        )
        child_materialization_errors = validate_requested_child_materialization(
            requested=child_materialization_requested,
            source_spec_relpath=source_spec_relpath,
            changed_files=changed,
            reserved_child_path=(
                str(child_materialization_hint.get("path", "")).strip()
                if child_materialization_hint is not None
                else ""
            ),
        )
        reconciliation, reconciliation_errors = reconcile_graph(
            source_node=node,
            worktree_path=worktree_path,
            changed_files=changed,
        )
        if worktree_load_errors:
            atomicity_errors = list(worktree_load_errors)
        else:
            atomicity_errors = validate_changed_spec_atomicity(
                source_node_id=node.id,
                changed_files=changed,
                worktree_specs=worktree_specs,
                worktree_path=worktree_path,
            )

        proposed_status = None if is_graph_refactor_run else STATUS_PROGRESSION.get(node.status)
        if proposed_status == "reviewed" and not reconciliation.get("work_dependencies_ready"):
            proposed_status = node.status
        transition_errors = (
            []
            if is_graph_refactor_run or proposed_status == node.status
            else validate_transition(node.status, proposed_status)
        )

        validation_errors = []
        validation_errors.extend(output_errors)
        validation_errors.extend(allowed_path_errors)
        validation_errors.extend(child_materialization_errors)
        validation_errors.extend(reconciliation_errors)
        validation_errors.extend(atomicity_errors)
        validation_errors.extend(transition_errors)
        validation_errors.extend(executor_protocol_errors)

        executor_requested_split_required = outcome == "split_required"

        if child_materialization_errors and outcome == "done":
            outcome = "blocked"
            if not blocker:
                blocker = "child materialization requested but no child spec was produced"

        if atomicity_errors and outcome == "done":
            outcome = "split_required"
            if not blocker:
                blocker = "spec exceeds atomicity quality gate"

        candidate_graph_health = observe_graph_health(
            source_node=node,
            worktree_specs=worktree_specs,
            reconciliation=reconciliation,
            atomicity_errors=atomicity_errors,
            outcome=outcome,
        )
        candidate_after_node = next((spec for spec in worktree_specs if spec.id == node.id), None)
        candidate_after_data = sanitize_source_after_child_materialization(
            before_data=before_canonical,
            after_data=(
                candidate_after_node.data if candidate_after_node is not None else before_canonical
            ),
            requested=child_materialization_requested,
        )
    if not primary_executor_failure:
        refinement_acceptance = validate_refinement_acceptance(
            node=node,
            before_data=before_canonical,
            after_data=candidate_after_data,
            changed_files=changed,
            is_graph_refactor_run=is_graph_refactor_run,
            output_errors=output_errors,
            allowed_path_errors=allowed_path_errors,
            reconciliation_errors=reconciliation_errors,
            transition_errors=transition_errors,
            atomicity_errors=atomicity_errors,
            mutation_budget=mutation_budget,
        )

    structural_success = result.returncode == 0 and not validation_errors and outcome == "done"
    accepted_refinement = refinement_acceptance["decision"] != REFINEMENT_ACCEPT_DECISION_REJECT
    success = structural_success
    if structural_success and not accepted_refinement:
        success = False
        outcome = "retry"
        blocker = blocker or "refinement acceptance rejected"
        validation_errors = validation_errors + list(refinement_acceptance["errors"])

    required_human_action = "resolve gate: approve|retry|split|block|redirect|escalate"
    node.data["proposed_status"] = None
    node.data["proposed_maturity"] = None

    productive_split_required = (
        outcome == "split_required"
        and result.returncode == 0
        and not primary_executor_failure
        and not output_errors
        and not allowed_path_errors
        and not child_materialization_errors
        and not reconciliation_errors
        and not transition_errors
        and not worktree_load_errors
        and accepted_refinement
        and bool(changed)
    )
    allowed_changes = select_sync_paths(effective_allowed_paths, changed)
    split_sync_allowed = productive_split_required and (
        not atomicity_errors
        or executor_requested_split_required
        or bool(materialized_child_paths)
        or child_materialization_requested
        or any(path != source_spec_relpath for path in changed)
    )
    if split_sync_allowed:
        sync_files_from_worktree(worktree_path, allowed_changes)
        normalize_materialized_child_specs(materialized_child_paths)
        node.reload()
        restore_source_lifecycle_fields_after_split_sync(
            node=node,
            before_data=before_node_data,
        )
        restore_ephemeral_child_authority_fields(
            node=node,
            before_data=before_node_data,
            requested=child_materialization_requested,
        )
        clear_pending_review_state(node)

    if success:
        proposed_maturity = (
            None if is_graph_refactor_run else min(1.0, round(node.maturity + 0.2, 2))
        )
        node.data["proposed_status"] = proposed_status
        node.data["proposed_maturity"] = proposed_maturity
        acceptance_decision = refinement_acceptance["decision"]
        if auto_approve and acceptance_decision == REFINEMENT_ACCEPT_DECISION_APPROVE:
            sync_files_from_worktree(worktree_path, allowed_changes)
            normalize_materialized_child_specs(materialized_child_paths)
            node.reload()
            restore_ephemeral_child_authority_fields(
                node=node,
                before_data=before_node_data,
                requested=child_materialization_requested,
            )
            if proposed_status:
                node.data["status"] = proposed_status
            node.data["maturity"] = proposed_maturity
            node.data["gate_state"] = "none"
            node.data["proposed_status"] = None
            node.data["proposed_maturity"] = None
            required_human_action = "-"
            clear_pending_review_state(node)
        else:
            node.data["gate_state"] = "review_pending"
            if acceptance_decision == REFINEMENT_ACCEPT_DECISION_APPROVE:
                required_human_action = "approve or retry refinement"
            else:
                required_human_action = "review refinement impact before approval"
            node.data["pending_sync_paths"] = allowed_changes
            node.data["pending_base_digests"] = snapshot_sync_digests(
                allowed_changes, base_dir=ROOT
            )
            node.data["pending_candidate_digests"] = snapshot_sync_digests(
                allowed_changes, base_dir=worktree_path
            )
            node.data["pending_run_id"] = run_id
    else:
        if primary_executor_failure:
            node.data["gate_state"] = "blocked"
            required_human_action = executor_environment_required_action(executor_environment)
        elif outcome == "blocked":
            node.data["gate_state"] = "blocked"
            required_human_action = "resolve blocker"
        elif outcome == "split_required":
            node.data["gate_state"] = "split_required"
            required_human_action = "split spec scope before rerun"
        elif outcome == "retry":
            node.data["gate_state"] = "retry_pending"
            if refinement_acceptance["decision"] == REFINEMENT_ACCEPT_DECISION_REJECT:
                required_human_action = "repair invalid or empty refinement and rerun supervisor"
            else:
                required_human_action = "rerun supervisor"
        elif outcome == "escalate":
            node.data["gate_state"] = "escalated"
            required_human_action = "manual escalation"
        else:
            node.data["gate_state"] = "retry_pending"
            required_human_action = "rerun supervisor"
        clear_pending_review_state(node)

    graph_health = empty_graph_health(node.id)
    artifact_io_errors: list[str] = []
    if not primary_executor_failure and not worktree_load_errors:
        accepted_graph_health_outcome = None
        if split_sync_allowed or (success and node.gate_state == "none"):
            accepted_graph_health_outcome = outcome
        graph_health = derive_accepted_graph_health(
            source_node=node,
            current_specs=load_specs(),
            outcome=accepted_graph_health_outcome,
        )
        try:
            proposal_queue_artifact, proposal_items = update_proposal_queue(
                graph_health=graph_health,
                run_id=run_id,
            )
            refactor_queue_artifact = update_refactor_queue(
                graph_health=graph_health,
                run_id=run_id,
                proposal_items=proposal_items,
            )
        except RuntimeError as exc:
            artifact_io_errors.append(str(exc))
            validation_errors.append(str(exc))
            proposal_queue_artifact = proposal_queue_path()
            refactor_queue_artifact = refactor_queue_path()
    else:
        proposal_queue_artifact = proposal_queue_path()
        refactor_queue_artifact = refactor_queue_path()
    if artifact_io_errors:
        success = False
        outcome = "blocked"
        blocker = blocker or "runtime artifact failure"
        node.data["gate_state"] = "blocked"
        clear_pending_review_state(node)
        required_human_action = "repair malformed runtime artifact and rerun supervisor"
    proposal_queue_after = load_proposal_queue()
    refactor_queue_after = load_refactor_queue()

    cleanup_failed_child_materialization = (
        child_materialization_requested
        and not success
        and not any(path != source_spec_relpath for path in changed if is_spec_node_path(path))
    )
    changed_spec_paths = [path for path in changed if is_spec_node_path(path)]
    source_only_changed_spec_paths = not changed_spec_paths or set(changed_spec_paths) == {
        source_spec_relpath
    }
    canonical_writeback_succeeded = success or split_sync_allowed
    cleanup_failed_source_refinement = (
        not success
        and not canonical_writeback_succeeded
        and source_only_changed_spec_paths
        and bool(worktree_load_errors)
    )

    validator_results = {
        "outputs": not output_errors,
        "allowed_paths": not allowed_path_errors,
        "reconciliation": not reconciliation_errors,
        "atomicity": not atomicity_errors,
        "transition": not transition_errors,
        "executor_environment": not primary_executor_failure,
        "runtime_artifacts": not artifact_io_errors,
        "refinement_acceptance": accepted_refinement,
    }
    completion_status = classify_completion_status(
        success=success,
        productive_split_required=productive_split_required,
    )
    preserve_run_worktree = node.data.get("gate_state") == "review_pending"

    node.data["required_human_action"] = required_human_action
    node.data["last_outcome"] = outcome
    node.data["last_blocker"] = blocker
    node.data["last_run_id"] = run_id
    node.data["last_exit_code"] = result.returncode
    node.data["last_changed_files"] = changed
    node.data["last_run_at"] = utc_now_iso()
    node.data["last_worktree_path"] = worktree_path.as_posix() if preserve_run_worktree else ""
    node.data["last_branch"] = branch if preserve_run_worktree else ""
    node.data["last_validator_results"] = validator_results
    node.data["last_refinement_acceptance"] = refinement_acceptance
    node.data["last_reconciliation"] = reconciliation
    node.data["last_requested_child_materialization"] = child_materialization_requested
    node.data["last_materialized_child_paths"] = materialized_child_paths
    if validation_errors:
        node.data["last_errors"] = validation_errors
    node.save()
    if child_materialization_hint is not None:
        release_child_materialization_spec_id(
            spec_id=str(child_materialization_hint.get("id", "")).strip(),
            run_id=run_id,
        )

    decision_inspector = build_decision_inspector(
        run_id=run_id,
        spec_id=node.id,
        selected_by_rule=selected_by_rule,
        outcome=outcome,
        gate_state=str(node.data.get("gate_state", "none")),
        required_human_action=required_human_action,
        blocker=blocker,
        changed_files=changed,
        validation_errors=validation_errors,
        validator_results=validator_results,
        graph_health=graph_health,
        graph_health_truth_basis="accepted_canonical",
        proposal_queue_before=proposal_queue_before,
        proposal_queue_after=proposal_queue_after,
        refactor_queue_before=refactor_queue_before,
        refactor_queue_after=refactor_queue_after,
        refinement_acceptance=refinement_acceptance,
    )
    decision_inspector_artifact = write_decision_inspector_artifact(run_id, decision_inspector)
    payload = {
        "run_id": run_id,
        "timestamp_utc": utc_now_iso(),
        "spec_id": node.id,
        "title": node.title,
        "completion_status": completion_status,
        "selected_by_rule": selected_by_rule,
        "before_status": before_status,
        "proposed_status": node.data.get("proposed_status"),
        "final_status": node.data.get("status"),
        "outcome": outcome,
        "blocker": blocker,
        "gate_state": node.data.get("gate_state"),
        "required_human_action": required_human_action,
        "exit_code": result.returncode,
        "auto_approved": bool(
            success
            and auto_approve
            and refinement_acceptance["decision"] == REFINEMENT_ACCEPT_DECISION_APPROVE
        ),
        "worktree_path": worktree_path.as_posix(),
        "isolation_mode": isolation_mode_for_branch(branch),
        "yaml_repair_paths": yaml_repair_paths,
        "branch": branch,
        "changed_files": changed,
        "validation_errors": validation_errors,
        "validator_results": validator_results,
        "reconciliation": reconciliation,
        "graph_health": graph_health,
        "graph_health_truth_basis": "accepted_canonical",
        "decision_inspector": decision_inspector,
        "decision_inspector_artifact": decision_inspector_artifact.as_posix(),
        "executor_environment": executor_environment,
        "refinement_acceptance": refinement_acceptance,
        "refactor_queue_artifact": refactor_queue_artifact.as_posix(),
        "proposal_queue_artifact": proposal_queue_artifact.as_posix(),
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
    if candidate_graph_health != graph_health:
        payload["candidate_graph_health"] = candidate_graph_health
        payload["candidate_graph_health_truth_basis"] = "review_candidate"
    log_path = write_run_log(run_id, payload)
    write_latest_summary(payload)

    if cleanup_failed_child_materialization or cleanup_failed_source_refinement:
        node.path.write_text(before_source_text, encoding="utf-8")
        node.reload()

    if not preserve_run_worktree:
        cleanup_isolated_worktree(worktree_path, branch)

    emit_run_footer(
        log_path=log_path,
        completion_status=completion_status,
        stdout=result.stdout,
        stderr=result.stderr,
        validation_errors=validation_errors,
        verbose=verbose,
    )

    exit_code = 0 if success else 1
    return exit_code, outcome, completion_status, str(payload.get("gate_state") or "none")


def main(
    *,
    executor: Callable[[SpecNode, Path], subprocess.CompletedProcess[str]] | None = None,
    dry_run: bool = False,
    auto_approve: bool = False,
    loop: bool = False,
    max_iterations: int = 50,
    resolve_gate: str | None = None,
    decision: str | None = None,
    note: str = "",
    target_spec: str | None = None,
    split_proposal: bool = False,
    apply_split_proposal: bool = False,
    operator_note: str = "",
    mutation_budget: tuple[str, ...] = (),
    run_authority: tuple[str, ...] = (),
    execution_profile: str | None = None,
    child_model: str | None = None,
    child_timeout_seconds: int | None = None,
    verbose: bool = False,
    list_stale_runtime: bool = False,
    clean_stale_runtime: bool = False,
    observe_graph_health_mode: bool = False,
    validate_transition_packet_path: str | None = None,
    transition_profile: str | None = None,
    build_intent_layer_overlay_mode: bool = False,
    build_graph_health_overlay_mode: bool = False,
    build_graph_health_trends_mode: bool = False,
    build_spec_trace_index_mode: bool = False,
    build_spec_trace_projection_mode: bool = False,
    build_proposal_lane_overlay_mode: bool = False,
    build_proposal_runtime_index_mode: bool = False,
    build_proposal_promotion_index_mode: bool = False,
) -> int:
    """Entry point for CLI and tests.

    `main()` dispatches between high-level modes:
    - gate resolution
    - non-mutating graph-health observation
    - explicit split proposal mode
    - explicit split proposal application
    - autonomous loop mode
    - default single-pass mode
    """
    if executor is None:
        executor = run_codex

    try:
        if execution_profile is not None:
            resolve_execution_profile_name(
                requested_profile=execution_profile,
                run_authority=(),
            )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if transition_profile and not validate_transition_packet_path:
        print("--transition-profile requires --validate-transition-packet", file=sys.stderr)
        return 1

    if validate_transition_packet_path:
        if any(
            (
                dry_run,
                auto_approve,
                loop,
                resolve_gate,
                decision,
                note,
                target_spec,
                split_proposal,
                apply_split_proposal,
                operator_note,
                mutation_budget,
                run_authority,
                execution_profile,
                child_model,
                child_timeout_seconds,
                verbose,
                list_stale_runtime,
                clean_stale_runtime,
                observe_graph_health_mode,
                build_intent_layer_overlay_mode,
                build_graph_health_overlay_mode,
                build_graph_health_trends_mode,
                build_spec_trace_index_mode,
                build_spec_trace_projection_mode,
                build_proposal_lane_overlay_mode,
                build_proposal_runtime_index_mode,
                build_proposal_promotion_index_mode,
            )
        ):
            print(
                "--validate-transition-packet must be used as a standalone command",
                file=sys.stderr,
            )
            return 1
        report = validate_transition_packet_file(
            Path(validate_transition_packet_path),
            validator_profile=transition_profile,
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report["ok"] else 1

    if build_intent_layer_overlay_mode:
        if any(
            (
                dry_run,
                auto_approve,
                loop,
                resolve_gate,
                decision,
                note,
                target_spec,
                split_proposal,
                apply_split_proposal,
                operator_note,
                mutation_budget,
                run_authority,
                execution_profile,
                child_model,
                child_timeout_seconds,
                verbose,
                list_stale_runtime,
                clean_stale_runtime,
                observe_graph_health_mode,
                build_graph_health_overlay_mode,
                build_graph_health_trends_mode,
                build_spec_trace_index_mode,
                build_spec_trace_projection_mode,
                build_proposal_lane_overlay_mode,
                build_proposal_runtime_index_mode,
                build_proposal_promotion_index_mode,
            )
        ):
            print(
                "--build-intent-layer-overlay must be used as a standalone command",
                file=sys.stderr,
            )
            return 1
        overlay = build_intent_layer_overlay()
        write_intent_layer_overlay(overlay)
        print(json.dumps(overlay, ensure_ascii=False, indent=2))
        return 0

    if build_proposal_lane_overlay_mode:
        if any(
            (
                dry_run,
                auto_approve,
                loop,
                resolve_gate,
                decision,
                note,
                target_spec,
                split_proposal,
                apply_split_proposal,
                operator_note,
                mutation_budget,
                run_authority,
                execution_profile,
                child_model,
                child_timeout_seconds,
                verbose,
                list_stale_runtime,
                clean_stale_runtime,
                observe_graph_health_mode,
                build_proposal_runtime_index_mode,
                build_proposal_promotion_index_mode,
            )
        ):
            print(
                "--build-proposal-lane-overlay must be used as a standalone command",
                file=sys.stderr,
            )
            return 1
        overlay = build_proposal_lane_overlay()
        write_proposal_lane_overlay(overlay)
        print(json.dumps(overlay, ensure_ascii=False, indent=2))
        return 0

    try:
        specs = load_specs()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if not specs:
        print("No spec nodes found in specs/nodes")
        return 0

    if build_graph_health_overlay_mode:
        if any(
            (
                dry_run,
                auto_approve,
                loop,
                resolve_gate,
                decision,
                note,
                target_spec,
                split_proposal,
                apply_split_proposal,
                operator_note,
                mutation_budget,
                run_authority,
                execution_profile,
                child_model,
                child_timeout_seconds,
                verbose,
                list_stale_runtime,
                clean_stale_runtime,
                observe_graph_health_mode,
                build_graph_health_trends_mode,
                build_spec_trace_index_mode,
                build_spec_trace_projection_mode,
                build_proposal_lane_overlay_mode,
                build_proposal_runtime_index_mode,
                build_proposal_promotion_index_mode,
            )
        ):
            print(
                "--build-graph-health-overlay must be used as a standalone command",
                file=sys.stderr,
            )
            return 1
        overlay = build_graph_health_overlay(specs)
        write_graph_health_overlay(overlay)
        print(json.dumps(overlay, ensure_ascii=False, indent=2))
        return 0

    if build_graph_health_trends_mode:
        if any(
            (
                dry_run,
                auto_approve,
                loop,
                resolve_gate,
                decision,
                note,
                target_spec,
                split_proposal,
                apply_split_proposal,
                operator_note,
                mutation_budget,
                run_authority,
                execution_profile,
                child_model,
                child_timeout_seconds,
                verbose,
                list_stale_runtime,
                clean_stale_runtime,
                observe_graph_health_mode,
                build_graph_health_overlay_mode,
                build_spec_trace_index_mode,
                build_spec_trace_projection_mode,
                build_proposal_lane_overlay_mode,
                build_proposal_runtime_index_mode,
                build_proposal_promotion_index_mode,
            )
        ):
            print(
                "--build-graph-health-trends must be used as a standalone command",
                file=sys.stderr,
            )
            return 1
        overlay = build_graph_health_overlay(specs)
        write_graph_health_overlay(overlay)
        trends = build_graph_health_trends(specs, overlay=overlay)
        write_graph_health_trends(trends)
        print(json.dumps(trends, ensure_ascii=False, indent=2))
        return 0

    if build_spec_trace_index_mode:
        if any(
            (
                dry_run,
                auto_approve,
                loop,
                resolve_gate,
                decision,
                note,
                target_spec,
                split_proposal,
                apply_split_proposal,
                operator_note,
                mutation_budget,
                run_authority,
                execution_profile,
                child_model,
                child_timeout_seconds,
                verbose,
                list_stale_runtime,
                clean_stale_runtime,
                observe_graph_health_mode,
                build_proposal_lane_overlay_mode,
                build_spec_trace_projection_mode,
                build_proposal_runtime_index_mode,
                build_proposal_promotion_index_mode,
            )
        ):
            print(
                "--build-spec-trace-index must be used as a standalone command",
                file=sys.stderr,
            )
            return 1
        index = build_spec_trace_index(specs)
        write_spec_trace_index(index)
        print(json.dumps(index, ensure_ascii=False, indent=2))
        return 0

    if build_spec_trace_projection_mode:
        if any(
            (
                dry_run,
                auto_approve,
                loop,
                resolve_gate,
                decision,
                note,
                target_spec,
                split_proposal,
                apply_split_proposal,
                operator_note,
                mutation_budget,
                run_authority,
                execution_profile,
                child_model,
                child_timeout_seconds,
                verbose,
                list_stale_runtime,
                clean_stale_runtime,
                observe_graph_health_mode,
                build_proposal_lane_overlay_mode,
                build_proposal_runtime_index_mode,
            )
        ):
            print(
                "--build-spec-trace-projection must be used as a standalone command",
                file=sys.stderr,
            )
            return 1
        index = build_spec_trace_index(specs)
        write_spec_trace_index(index)
        projection = build_spec_trace_projection(index)
        write_spec_trace_projection(projection)
        print(json.dumps(projection, ensure_ascii=False, indent=2))
        return 0

    if build_proposal_runtime_index_mode:
        if any(
            (
                dry_run,
                auto_approve,
                loop,
                resolve_gate,
                decision,
                note,
                target_spec,
                split_proposal,
                apply_split_proposal,
                operator_note,
                mutation_budget,
                run_authority,
                execution_profile,
                child_model,
                child_timeout_seconds,
                verbose,
                list_stale_runtime,
                clean_stale_runtime,
                observe_graph_health_mode,
                build_proposal_lane_overlay_mode,
                build_proposal_promotion_index_mode,
            )
        ):
            print(
                "--build-proposal-runtime-index must be used as a standalone command",
                file=sys.stderr,
            )
            return 1
        index = build_proposal_runtime_index()
        write_proposal_runtime_index(index)
        print(json.dumps(index, ensure_ascii=False, indent=2))
        return 0

    if build_proposal_promotion_index_mode:
        if any(
            (
                dry_run,
                auto_approve,
                loop,
                resolve_gate,
                decision,
                note,
                target_spec,
                split_proposal,
                apply_split_proposal,
                operator_note,
                mutation_budget,
                run_authority,
                execution_profile,
                child_model,
                child_timeout_seconds,
                verbose,
                list_stale_runtime,
                clean_stale_runtime,
                observe_graph_health_mode,
                build_proposal_lane_overlay_mode,
            )
        ):
            print(
                "--build-proposal-promotion-index must be used as a standalone command",
                file=sys.stderr,
            )
            return 1
        index = build_proposal_promotion_index()
        write_proposal_promotion_index(index)
        print(json.dumps(index, ensure_ascii=False, indent=2))
        return 0

    if list_stale_runtime and clean_stale_runtime:
        print(
            "--list-stale-runtime cannot be combined with --clean-stale-runtime",
            file=sys.stderr,
        )
        return 1

    if list_stale_runtime or clean_stale_runtime:
        if clean_stale_runtime and dry_run:
            print(
                "--dry-run cannot be combined with --clean-stale-runtime",
                file=sys.stderr,
            )
            return 1
        if any(
            (
                resolve_gate,
                decision,
                target_spec,
                split_proposal,
                apply_split_proposal,
                loop,
                operator_note,
                mutation_budget,
                run_authority,
            )
        ):
            print(
                "--list-stale-runtime/--clean-stale-runtime must be used as standalone commands",
                file=sys.stderr,
            )
            return 1
        return handle_stale_runtime(specs=specs, clean=clean_stale_runtime)

    artifact_integrity_errors = runtime_artifact_integrity_errors()
    if artifact_integrity_errors:
        for error in artifact_integrity_errors:
            print(error, file=sys.stderr)
        return 1

    if observe_graph_health_mode:
        if not target_spec:
            print("--observe-graph-health requires --target-spec", file=sys.stderr)
            return 1
        if any(
            (
                resolve_gate,
                decision,
                split_proposal,
                apply_split_proposal,
                loop,
                auto_approve,
                dry_run,
                operator_note,
                mutation_budget,
                run_authority,
            )
        ):
            print(
                "--observe-graph-health must be used only with --target-spec",
                file=sys.stderr,
            )
            return 1
        index = index_specs(specs)
        node = index.get(str(target_spec).strip())
        if node is None:
            print(f"Spec not found: {target_spec}", file=sys.stderr)
            return 1
        if str(node.data.get("kind", "")).strip() != "spec":
            print(f"Explicit target is not a spec node: {target_spec}", file=sys.stderr)
            return 1

        snapshot = inspect_canonical_graph_health(node=node, specs=specs)
        print(f"Selected spec node: {node.id} — {node.title}")
        print("\n=== graph-health observation mode ===")
        print(f"Diagnostic outcome basis: {snapshot['diagnostic_outcome']}")
        print(
            "Subtree nodes: " + ", ".join(str(spec_id) for spec_id in snapshot["subtree_spec_ids"])
        )
        if snapshot["historical_descendant_ids"]:
            print(
                "Historical descendants excluded: "
                + ", ".join(str(spec_id) for spec_id in snapshot["historical_descendant_ids"])
            )
        print(json.dumps(snapshot, ensure_ascii=False, indent=2))
        return 0

    if resolve_gate:
        if not decision:
            print("--decision is required with --resolve-gate", file=sys.stderr)
            return 1
        return resolve_gate_decision(
            specs=specs, spec_id=resolve_gate, decision=decision, note=note
        )

    if decision:
        print("--decision is only valid with --resolve-gate", file=sys.stderr)
        return 1

    if split_proposal and apply_split_proposal:
        print("--split-proposal cannot be combined with --apply-split-proposal", file=sys.stderr)
        return 1
    if (split_proposal or apply_split_proposal) and not target_spec:
        print(
            "--split-proposal and --apply-split-proposal both require --target-spec",
            file=sys.stderr,
        )
        return 1
    if (split_proposal or apply_split_proposal) and loop:
        print(
            "--split-proposal and --apply-split-proposal cannot be combined with --loop",
            file=sys.stderr,
        )
        return 1
    if (split_proposal or apply_split_proposal) and auto_approve:
        print(
            "--split-proposal and --apply-split-proposal cannot be combined with --auto-approve",
            file=sys.stderr,
        )
        return 1
    if target_spec and loop:
        print("--target-spec cannot be combined with --loop", file=sys.stderr)
        return 1
    if operator_note and loop:
        print("--operator-note cannot be combined with --loop", file=sys.stderr)
        return 1
    if mutation_budget and loop:
        print("--mutation-budget cannot be combined with --loop", file=sys.stderr)
        return 1
    if run_authority and loop:
        print("--run-authority cannot be combined with --loop", file=sys.stderr)
        return 1

    if loop and not auto_approve:
        print("--loop requires --auto-approve", file=sys.stderr)
        return 1

    if loop and dry_run:
        print("--loop cannot be combined with --dry-run", file=sys.stderr)
        return 1

    cycles = detect_cycles(specs)
    if cycles:
        print("Dependency cycles detected:", file=sys.stderr)
        for cycle in cycles:
            print(f"  {' -> '.join(cycle)}", file=sys.stderr)
        return 1

    if split_proposal:
        index = index_specs(specs)
        node = index.get(str(target_spec).strip())
        if node is None:
            print(f"Spec not found: {target_spec}", file=sys.stderr)
            return 1
        eligibility_errors = validate_split_refactor_target(node)
        if eligibility_errors:
            for error in eligibility_errors:
                print(error, file=sys.stderr)
            return 1

        refactor_work_item = build_split_refactor_work_item(node)
        selected_by_rule = {
            "selection_mode": "split_refactor_proposal",
            "operator_target": node.id,
            "sort_order": policy_lookup("selection_priorities.explicit_target_sort_order"),
            "refactor_work_item": {
                "id": str(refactor_work_item.get("id", "")),
                "proposal_type": str(refactor_work_item.get("proposal_type", "")),
                "signal": str(refactor_work_item.get("signal", "")),
                "refactor_kind": str(refactor_work_item.get("refactor_kind", "")),
                "execution_policy": str(refactor_work_item.get("execution_policy", "")),
                "proposal_artifact_relpath": str(
                    refactor_work_item.get("proposal_artifact_relpath", "")
                ),
            },
        }
        if operator_note.strip():
            selected_by_rule["operator_note"] = operator_note.strip()
        if mutation_budget:
            selected_by_rule["mutation_budget"] = list(mutation_budget)
        if run_authority:
            selected_by_rule["run_authority"] = list(run_authority)
        selected_by_rule["execution_profile"] = resolve_execution_profile_name(
            requested_profile=execution_profile,
            run_authority=(),
            operator_target=True,
        )

        print(f"Selected spec node: {node.id} — {node.title}")

        if dry_run:
            print("\n=== dry-run mode ===")
            print(f"Would execute prompt for: {node.id}")
            print(
                f"Status: {node.status} | Maturity: {node.maturity:.2f} | Gate: {node.gate_state}"
            )
            print(f"Selection context: {json.dumps(selected_by_rule, ensure_ascii=False)}")
            prompt = build_prompt(
                node,
                refactor_work_item,
                operator_note=operator_note,
                mutation_budget=mutation_budget,
            )
            print(f"\n{prompt}")
            return 0

        proposal_timeout = child_timeout_seconds
        if proposal_timeout is None and is_seed_like_spec(node.data):
            proposal_timeout = ROOT_REFACTOR_TIMEOUT_SECONDS

        proposal_kwargs: dict[str, Any] = {
            "node": node,
            "executor": executor,
            "operator_note": operator_note,
            "execution_profile": execution_profile,
            "child_model": child_model,
            "child_timeout_seconds": proposal_timeout,
        }
        if callable_supports_keyword(_process_split_refactor_proposal, "verbose"):
            proposal_kwargs["verbose"] = verbose
        exit_code, _outcome = _process_split_refactor_proposal(**proposal_kwargs)
        return exit_code

    if apply_split_proposal:
        index = index_specs(specs)
        node = index.get(str(target_spec).strip())
        if node is None:
            print(f"Spec not found: {target_spec}", file=sys.stderr)
            return 1

        print(f"Selected spec node: {node.id} — {node.title}")
        return _apply_split_proposal(node=node, specs=specs)

    if target_spec:
        index = index_specs(specs)
        node = index.get(str(target_spec).strip())
        if node is None:
            print(f"Spec not found: {target_spec}", file=sys.stderr)
            return 1
        if str(node.data.get("kind", "")).strip() != "spec":
            print(f"Explicit target is not a spec node: {target_spec}", file=sys.stderr)
            return 1

        selected_by_rule = {
            "selection_mode": "explicit_target_refine",
            "operator_target": node.id,
            "sort_order": policy_lookup("selection_priorities.explicit_target_sort_order"),
            "status_filter": sorted(WORKABLE_STATUSES),
            "dependency_required_statuses": sorted(READY_DEP_STATUSES),
        }
        if operator_note.strip():
            selected_by_rule["operator_note"] = operator_note.strip()
        if mutation_budget:
            selected_by_rule["mutation_budget"] = list(mutation_budget)
        if run_authority:
            selected_by_rule["run_authority"] = list(run_authority)
        selected_by_rule["execution_profile"] = resolve_execution_profile_name(
            requested_profile=execution_profile,
            run_authority=run_authority,
            operator_target=True,
        )
        print(f"Selected spec node: {node.id} — {node.title}")
        preflight_errors = child_materialization_preflight_errors(
            node=node,
            specs=specs,
            operator_target=True,
            operator_note=operator_note,
            run_authority=run_authority,
        )
        if preflight_errors:
            for error in preflight_errors:
                print(error, file=sys.stderr)
            return 1

        if dry_run:
            print("\n=== dry-run mode ===")
            print(f"Would execute prompt for: {node.id}")
            print(
                f"Status: {node.status} | Maturity: {node.maturity:.2f} | Gate: {node.gate_state}"
            )
            print(f"Selection context: {json.dumps(selected_by_rule, ensure_ascii=False)}")
            prompt = build_prompt(
                node,
                operator_target=True,
                operator_note=operator_note,
                mutation_budget=mutation_budget,
                run_authority=run_authority,
            )
            print(f"\n{prompt}")
            return 0

        target_timeout = child_timeout_seconds
        if target_timeout is None and is_seed_like_spec(node.data):
            target_timeout = ROOT_REFACTOR_TIMEOUT_SECONDS

        process_kwargs: dict[str, Any] = {
            "node": node,
            "specs": specs,
            "executor": executor,
            "auto_approve": auto_approve,
            "operator_target": True,
            "operator_note": operator_note,
            "mutation_budget": mutation_budget,
            "run_authority": run_authority,
            "execution_profile": execution_profile,
            "child_model": child_model,
            "child_timeout_seconds": target_timeout,
        }
        if callable_supports_keyword(_process_one_spec, "verbose"):
            process_kwargs["verbose"] = verbose
        exit_code, _outcome, _completion_status, _gate_state = _process_one_spec(**process_kwargs)
        return exit_code

    if loop:
        print(f"Starting autonomous loop mode (max_iterations={max_iterations})")
        succeeded = 0
        progressed = 0
        failed = 0
        for iteration in range(1, max_iterations + 1):
            try:
                specs = load_specs()
            except RuntimeError as exc:
                print(str(exc), file=sys.stderr)
                return 1

            cycles = detect_cycles(specs)
            if cycles:
                print("Dependency cycles detected:", file=sys.stderr)
                for cycle in cycles:
                    print(f"  {' -> '.join(cycle)}", file=sys.stderr)
                return 1

            node, refactor_work_item = pick_next_work_item(specs)
            if node is None:
                print("No more eligible spec gaps. Loop complete.")
                gate_actions = pending_gate_actions(specs)
                if gate_actions:
                    print(format_pending_gate_actions(gate_actions))
                break

            print(f"\n{'=' * 60}")
            print(
                f"[{iteration}/{max_iterations}] Processing: {node.id} — {node.title}"
                f" (status={node.status}, maturity={node.maturity:.2f})"
            )
            print(f"{'=' * 60}")

            process_kwargs = {
                "node": node,
                "specs": specs,
                "executor": executor,
                "auto_approve": auto_approve,
                "refactor_work_item": refactor_work_item,
                "execution_profile": execution_profile,
                "child_model": child_model,
                "child_timeout_seconds": child_timeout_seconds,
            }
            if callable_supports_keyword(_process_one_spec, "verbose"):
                process_kwargs["verbose"] = verbose
            exit_code, outcome, completion_status, gate_state = _process_one_spec(**process_kwargs)

            if completion_status == COMPLETION_STATUS_OK:
                succeeded += 1
                print(f"[{iteration}] {node.id} promoted successfully.")
            elif completion_status == COMPLETION_STATUS_PROGRESSED:
                progressed += 1
                print(
                    f"[{iteration}] {node.id} progressed with outcome={outcome},"
                    f" gate_state={gate_state}. Continuing."
                )
            else:
                failed += 1
                print(
                    f"[{iteration}] {node.id} finished with outcome={outcome},"
                    f" gate_state={gate_state}. Continuing."
                )
        else:
            print(f"Safety limit reached ({max_iterations} iterations). Stopping loop.")

        print(f"\nLoop summary: {succeeded} succeeded, {progressed} progressed, {failed} failed")
        return 0

    # --- single-pass mode (original behaviour) ---
    node, refactor_work_item = pick_next_work_item(specs)
    if node is None:
        print(format_pending_gate_actions(pending_gate_actions(specs)))
        return 0

    dependents = reverse_dependents_count(specs)
    selection_mode = selection_mode_for_node(node, specs, refactor_work_item=refactor_work_item)
    continuation_reasons = linked_continuation_reasons(node, index_specs(specs))
    selected_by_rule = {
        "status_filter": sorted(
            WORKABLE_STATUSES
            | (CONTINUATION_STATUSES if selection_mode == "linked_continuation" else set())
        ),
        "dependency_required_statuses": sorted(READY_DEP_STATUSES),
        "selection_mode": selection_mode,
        "sort_order": policy_lookup("selection_priorities.ordinary_sort_order"),
        "dependents_count": dependents.get(node.id, 0),
    }
    if selection_mode == "linked_continuation":
        selected_by_rule["continuation_reasons"] = continuation_reasons
    if refactor_work_item is not None:
        selected_by_rule["refactor_work_item"] = {
            "id": str(refactor_work_item.get("id", "")),
            "work_item_type": str(refactor_work_item.get("work_item_type", "")),
            "signal": str(refactor_work_item.get("signal", "")),
            "recommended_action": str(refactor_work_item.get("recommended_action", "")),
            "source_run_id": str(refactor_work_item.get("source_run_id", "")),
        }
    selected_by_rule["execution_profile"] = infer_ordinary_execution_profile_name(
        node=node,
        specs=specs,
        requested_profile=execution_profile,
        operator_target=False,
        run_authority=(),
    )

    print(f"Selected spec node: {node.id} — {node.title}")

    if dry_run:
        print("\n=== dry-run mode ===")
        print(f"Would execute prompt for: {node.id}")
        print(f"Status: {node.status} | Maturity: {node.maturity:.2f} | Gate: {node.gate_state}")
        print(f"Selection context: {json.dumps(selected_by_rule, ensure_ascii=False)}")
        print(f"\n{build_prompt(node, refactor_work_item)}")
        return 0

    process_kwargs = {
        "node": node,
        "specs": specs,
        "executor": executor,
        "auto_approve": auto_approve,
        "refactor_work_item": refactor_work_item,
        "execution_profile": execution_profile,
        "child_model": child_model,
        "child_timeout_seconds": child_timeout_seconds,
    }
    if callable_supports_keyword(_process_one_spec, "verbose"):
        process_kwargs["verbose"] = verbose
    exit_code, _outcome, _completion_status, _gate_state = _process_one_spec(**process_kwargs)
    return exit_code


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SpecGraph supervisor")
    parser.add_argument("--dry-run", action="store_true", help="Show selection and prompt only")
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print full executor stdout/stderr and detailed runtime trace",
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Apply proposed status/maturity immediately when run succeeds",
    )
    parser.add_argument(
        "--list-stale-runtime",
        action="store_true",
        help="List stale gate states and orphaned worktrees without modifying anything",
    )
    parser.add_argument(
        "--clean-stale-runtime",
        action="store_true",
        help="Clean stale gate states and orphaned worktrees",
    )
    parser.add_argument(
        "--observe-graph-health",
        action="store_true",
        help="Print non-mutating graph-health diagnostics for --target-spec and its subtree",
    )
    parser.add_argument(
        "--validate-transition-packet",
        metavar="PATH",
        help="Validate one normalized transition packet JSON file and print structured findings",
    )
    parser.add_argument(
        "--transition-profile",
        choices=sorted(VALID_TRANSITION_VALIDATOR_PROFILES),
        help=(
            "Optional validator profile used with --validate-transition-packet, for example: "
            "specgraph_core or implementation_trace"
        ),
    )
    parser.add_argument(
        "--build-intent-layer-overlay",
        action="store_true",
        help=(
            "Build a viewer-facing intent-layer overlay from repository-tracked "
            "pre-canonical intent and operator-request nodes"
        ),
    )
    parser.add_argument(
        "--build-graph-health-overlay",
        action="store_true",
        help=(
            "Build a viewer-facing graph-health overlay from the accepted canonical graph "
            "without reading raw run logs"
        ),
    )
    parser.add_argument(
        "--build-graph-health-trends",
        action="store_true",
        help=(
            "Build longitudinal graph-health trends from run history so repeated structural "
            "problems are visible as trends"
        ),
    )
    parser.add_argument(
        "--build-spec-trace-index",
        action="store_true",
        help=(
            "Build a graph-bound spec trace index from literal spec-id mentions "
            "in tools/ and tests/, enriched with weak commit/pr and verification linkage"
        ),
    )
    parser.add_argument(
        "--build-spec-trace-projection",
        action="store_true",
        help=(
            "Build a viewer/backlog projection from the spec trace plane, including freshness "
            "and drift groupings"
        ),
    )
    parser.add_argument(
        "--build-proposal-lane-overlay",
        action="store_true",
        help=(
            "Build a viewer-facing proposal-lane overlay from repository-tracked proposal nodes "
            "without mutating canonical specs"
        ),
    )
    parser.add_argument(
        "--build-proposal-runtime-index",
        action="store_true",
        help=(
            "Build a derived proposal runtime index showing posture, realization, "
            "validation closure, and observation coverage"
        ),
    )
    parser.add_argument(
        "--build-proposal-promotion-index",
        action="store_true",
        help=(
            "Build a derived proposal promotion index showing source traceability "
            "and promotion provenance gaps"
        ),
    )
    parser.add_argument("--resolve-gate", metavar="SPEC_ID", help="Resolve gate for a spec id")
    parser.add_argument(
        "--decision",
        choices=["approve", "retry", "split", "block", "redirect", "escalate"],
        help="Decision used with --resolve-gate",
    )
    parser.add_argument("--note", default="", help="Optional note for gate resolution")
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Keep processing specs until no eligible gaps remain (requires --auto-approve)",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        default=50,
        help="Safety limit for loop mode (default: 50)",
    )
    parser.add_argument(
        "--target-spec",
        metavar="SPEC_ID",
        help=(
            "Explicit operator target. Alone, runs one ordinary refinement pass for that spec; "
            "with --split-proposal or --apply-split-proposal, runs the corresponding split mode."
        ),
    )
    parser.add_argument(
        "--operator-note",
        help=(
            "Ephemeral one-run operator guidance added to the agent prompt and run log "
            "without editing canonical specs."
        ),
    )
    parser.add_argument(
        "--mutation-budget",
        help=(
            "Optional comma-separated mutation classes allowed for an explicit targeted run, "
            "for example: policy_text,schema_required_addition"
        ),
    )
    parser.add_argument(
        "--run-authority",
        help=(
            "Optional comma-separated run authority grants for an explicit targeted run, "
            "for example: materialize_one_child"
        ),
    )
    parser.add_argument(
        "--execution-profile",
        choices=sorted(EXECUTION_PROFILES),
        help=(
            "Optional named execution profile for nested child runs, "
            "for example: fast, standard, or materialize"
        ),
    )
    parser.add_argument(
        "--child-timeout",
        type=int,
        help="Optional direct override in seconds for child executor timeout.",
    )
    parser.add_argument(
        "--child-model",
        help="Optional model override for nested child runs, for example: gpt-5.3-codex-spark",
    )
    parser.add_argument(
        "--split-proposal",
        action="store_true",
        help="Run explicit split_oversized_spec proposal mode for --target-spec",
    )
    parser.add_argument(
        "--apply-split-proposal",
        action="store_true",
        help="Apply an approved split_oversized_spec proposal for --target-spec",
    )
    args = parser.parse_args()
    try:
        mutation_budget = parse_mutation_budget(args.mutation_budget or "")
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
    try:
        run_authority = parse_run_authority(args.run_authority or "")
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
    if args.child_timeout is not None and args.child_timeout <= 0:
        print("--child-timeout must be a positive integer", file=sys.stderr)
        raise SystemExit(1)
    child_model = (args.child_model or "").strip() if args.child_model is not None else None
    if child_model is not None and not child_model:
        print("--child-model must be a non-empty string", file=sys.stderr)
        raise SystemExit(1)
    raise SystemExit(
        main(
            dry_run=args.dry_run,
            auto_approve=args.auto_approve,
            loop=args.loop,
            max_iterations=args.max_iterations,
            resolve_gate=args.resolve_gate,
            decision=args.decision,
            note=args.note,
            target_spec=args.target_spec,
            split_proposal=args.split_proposal,
            apply_split_proposal=args.apply_split_proposal,
            operator_note=args.operator_note or "",
            mutation_budget=mutation_budget,
            run_authority=run_authority,
            execution_profile=args.execution_profile,
            child_model=child_model,
            child_timeout_seconds=args.child_timeout,
            verbose=args.verbose,
            list_stale_runtime=args.list_stale_runtime,
            clean_stale_runtime=args.clean_stale_runtime,
            observe_graph_health_mode=args.observe_graph_health,
            validate_transition_packet_path=args.validate_transition_packet,
            transition_profile=args.transition_profile,
            build_intent_layer_overlay_mode=args.build_intent_layer_overlay,
            build_graph_health_overlay_mode=args.build_graph_health_overlay,
            build_graph_health_trends_mode=args.build_graph_health_trends,
            build_spec_trace_index_mode=args.build_spec_trace_index,
            build_spec_trace_projection_mode=args.build_spec_trace_projection,
            build_proposal_lane_overlay_mode=args.build_proposal_lane_overlay,
            build_proposal_runtime_index_mode=args.build_proposal_runtime_index,
            build_proposal_promotion_index_mode=args.build_proposal_promotion_index,
        )
    )
