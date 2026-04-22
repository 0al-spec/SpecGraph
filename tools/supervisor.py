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
- supervisor performance index: `runs/supervisor_performance_index.json`
- graph dashboard: `runs/graph_dashboard.json`
- intent-layer overlay: `runs/intent_layer_overlay.json`
- proposal-lane overlay: `runs/proposal_lane_overlay.json`
- graph health overlay: `runs/graph_health_overlay.json`
- external consumer index: `runs/external_consumer_index.json`
- external consumer overlay: `runs/external_consumer_overlay.json`
- external consumer handoff packets: `runs/external_consumer_handoff_packets.json`
- SpecPM import preview: `runs/specpm_import_preview.json`
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
OPERATOR_REQUEST_BRIDGE_POLICY_RELATIVE_PATH = "tools/operator_request_bridge_policy.json"
SPECGRAPH_VOCABULARY_RELATIVE_PATH = "tools/specgraph_vocabulary.json"
PRE_SPEC_SEMANTICS_POLICY_RELATIVE_PATH = "tools/pre_spec_semantics_policy.json"
VALIDATION_FINDINGS_POLICY_RELATIVE_PATH = "tools/validation_findings_policy.json"
SAFE_REPAIR_POLICY_RELATIVE_PATH = "tools/safe_repair_policy.json"
EVALUATOR_LOOP_POLICY_RELATIVE_PATH = "tools/evaluator_loop_policy.json"
EVALUATOR_INTERVENTION_POLICY_RELATIVE_PATH = "tools/evaluator_intervention_policy.json"
EVIDENCE_PLANE_POLICY_RELATIVE_PATH = "tools/evidence_plane_policy.json"
METRIC_SIGNAL_POLICY_RELATIVE_PATH = "tools/metric_signal_policy.json"
SUPERVISOR_PERFORMANCE_POLICY_RELATIVE_PATH = "tools/supervisor_performance_policy.json"
EXTERNAL_CONSUMER_REGISTRY_RELATIVE_PATH = "tools/external_consumers.json"
EXTERNAL_CONSUMER_OVERLAY_POLICY_RELATIVE_PATH = "tools/external_consumer_overlay_policy.json"
EXTERNAL_CONSUMER_HANDOFF_POLICY_RELATIVE_PATH = "tools/external_consumer_handoff_policy.json"
SPECPM_EXPORT_POLICY_RELATIVE_PATH = "tools/specpm_export_policy.json"
SPECPM_HANDOFF_POLICY_RELATIVE_PATH = "tools/specpm_handoff_policy.json"
SPECPM_MATERIALIZATION_POLICY_RELATIVE_PATH = "tools/specpm_materialization_policy.json"
SPECPM_IMPORT_POLICY_RELATIVE_PATH = "tools/specpm_import_policy.json"
SPECPM_EXPORT_REGISTRY_RELATIVE_PATH = "tools/specpm_export_registry.json"


def supervisor_policy_path() -> Path:
    return TOOLS_DIR / "supervisor_policy.json"


def techspec_handoff_policy_path() -> Path:
    return TOOLS_DIR / "techspec_handoff_policy.json"


def proposal_lane_policy_path() -> Path:
    return TOOLS_DIR / "proposal_lane_policy.json"


def intent_layer_policy_path() -> Path:
    return TOOLS_DIR / "intent_layer_policy.json"


def operator_request_bridge_policy_path() -> Path:
    return TOOLS_DIR / "operator_request_bridge_policy.json"


def specgraph_vocabulary_path() -> Path:
    return TOOLS_DIR / "specgraph_vocabulary.json"


def external_consumers_registry_path() -> Path:
    return ROOT / "tools" / "external_consumers.json"


def pre_spec_semantics_policy_path() -> Path:
    return TOOLS_DIR / "pre_spec_semantics_policy.json"


def validation_findings_policy_path() -> Path:
    return TOOLS_DIR / "validation_findings_policy.json"


def safe_repair_policy_path() -> Path:
    return TOOLS_DIR / "safe_repair_policy.json"


def evaluator_loop_policy_path() -> Path:
    return TOOLS_DIR / "evaluator_loop_policy.json"


def evaluator_intervention_policy_path() -> Path:
    return TOOLS_DIR / "evaluator_intervention_policy.json"


def evidence_plane_policy_path() -> Path:
    return TOOLS_DIR / "evidence_plane_policy.json"


def metric_signal_policy_path() -> Path:
    return TOOLS_DIR / "metric_signal_policy.json"


def supervisor_performance_policy_path() -> Path:
    return TOOLS_DIR / "supervisor_performance_policy.json"


def external_consumer_overlay_policy_path() -> Path:
    return TOOLS_DIR / "external_consumer_overlay_policy.json"


def external_consumer_handoff_policy_path() -> Path:
    return TOOLS_DIR / "external_consumer_handoff_policy.json"


def specpm_export_policy_path() -> Path:
    return TOOLS_DIR / "specpm_export_policy.json"


def specpm_handoff_policy_path() -> Path:
    return TOOLS_DIR / "specpm_handoff_policy.json"


def specpm_materialization_policy_path() -> Path:
    return TOOLS_DIR / "specpm_materialization_policy.json"


def specpm_import_policy_path() -> Path:
    return TOOLS_DIR / "specpm_import_policy.json"


def specpm_export_registry_path() -> Path:
    return TOOLS_DIR / "specpm_export_registry.json"


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


def load_operator_request_bridge_policy() -> tuple[dict[str, Any], str]:
    path = operator_request_bridge_policy_path()
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(
            f"failed to read operator request bridge policy artifact: {path.as_posix()} ({exc})"
        ) from exc
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"malformed operator request bridge policy artifact: {path.as_posix()} ({exc})"
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeError(
            "malformed operator request bridge policy artifact: "
            f"{path.as_posix()} must contain a JSON object"
        )
    required_sections = ("packet_contract", "typed_request_contract", "bridge_boundary")
    missing = [section for section in required_sections if section not in payload]
    if missing:
        raise RuntimeError(
            "malformed operator request bridge policy artifact: missing top-level section(s): "
            + ", ".join(missing)
        )
    return payload, hashlib.sha256(raw_text.encode("utf-8")).hexdigest()


(
    OPERATOR_REQUEST_BRIDGE_POLICY,
    OPERATOR_REQUEST_BRIDGE_POLICY_SHA256,
) = load_operator_request_bridge_policy()


def load_specgraph_vocabulary() -> tuple[dict[str, Any], str]:
    path = specgraph_vocabulary_path()
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(
            f"failed to read SpecGraph vocabulary artifact: {path.as_posix()} ({exc})"
        ) from exc
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"malformed SpecGraph vocabulary artifact: {path.as_posix()} ({exc})"
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeError(
            f"malformed SpecGraph vocabulary artifact: {path.as_posix()} must contain a JSON object"
        )
    required_sections = ("contexts", "term_families")
    missing = [section for section in required_sections if section not in payload]
    if missing:
        raise RuntimeError(
            "malformed SpecGraph vocabulary artifact: missing top-level section(s): "
            + ", ".join(missing)
        )
    if not isinstance(payload.get("term_families"), dict):
        raise RuntimeError(
            "malformed SpecGraph vocabulary artifact: term_families must be an object"
        )
    return payload, hashlib.sha256(raw_text.encode("utf-8")).hexdigest()


SPECGRAPH_VOCABULARY, SPECGRAPH_VOCABULARY_SHA256 = load_specgraph_vocabulary()


def load_pre_spec_semantics_policy() -> tuple[dict[str, Any], str]:
    path = pre_spec_semantics_policy_path()
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(
            f"failed to read pre-spec semantics policy artifact: {path.as_posix()} ({exc})"
        ) from exc
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"malformed pre-spec semantics policy artifact: {path.as_posix()} ({exc})"
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeError(
            "malformed pre-spec semantics policy artifact: "
            f"{path.as_posix()} must contain a JSON object"
        )
    required_sections = (
        "repository_layout",
        "semantic_boundary",
        "artifact_classes",
        "axes_contract",
        "index_contract",
    )
    missing = [section for section in required_sections if section not in payload]
    if missing:
        raise RuntimeError(
            "malformed pre-spec semantics policy artifact: missing top-level section(s): "
            + ", ".join(missing)
        )
    return payload, hashlib.sha256(raw_text.encode("utf-8")).hexdigest()


PRE_SPEC_SEMANTICS_POLICY, PRE_SPEC_SEMANTICS_POLICY_SHA256 = load_pre_spec_semantics_policy()


def load_validation_findings_policy() -> tuple[dict[str, Any], str]:
    path = validation_findings_policy_path()
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(
            f"failed to read validation findings policy artifact: {path.as_posix()} ({exc})"
        ) from exc
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"malformed validation findings policy artifact: {path.as_posix()} ({exc})"
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeError(
            "malformed validation findings policy artifact: "
            f"{path.as_posix()} must contain a JSON object"
        )
    required_sections = ("finding_families", "error_classes", "severity_levels")
    missing = [section for section in required_sections if section not in payload]
    if missing:
        raise RuntimeError(
            "malformed validation findings policy artifact: missing top-level section(s): "
            + ", ".join(missing)
        )
    return payload, hashlib.sha256(raw_text.encode("utf-8")).hexdigest()


VALIDATION_FINDINGS_POLICY, VALIDATION_FINDINGS_POLICY_SHA256 = load_validation_findings_policy()


def load_safe_repair_policy() -> tuple[dict[str, Any], str]:
    path = safe_repair_policy_path()
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(
            f"failed to read safe repair policy artifact: {path.as_posix()} ({exc})"
        ) from exc
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"malformed safe repair policy artifact: {path.as_posix()} ({exc})"
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeError(
            f"malformed safe repair policy artifact: {path.as_posix()} must contain a JSON object"
        )
    required_sections = ("trust_boundary", "repair_kinds", "contract_fields")
    missing = [section for section in required_sections if section not in payload]
    if missing:
        raise RuntimeError(
            "malformed safe repair policy artifact: missing top-level section(s): "
            + ", ".join(missing)
        )
    return payload, hashlib.sha256(raw_text.encode("utf-8")).hexdigest()


SAFE_REPAIR_POLICY, SAFE_REPAIR_POLICY_SHA256 = load_safe_repair_policy()


def load_evaluator_loop_policy() -> tuple[dict[str, Any], str]:
    path = evaluator_loop_policy_path()
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(
            f"failed to read evaluator loop policy artifact: {path.as_posix()} ({exc})"
        ) from exc
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"malformed evaluator loop policy artifact: {path.as_posix()} ({exc})"
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeError(
            "malformed evaluator loop policy artifact: "
            f"{path.as_posix()} must contain a JSON object"
        )
    required_sections = ("intervention_kinds", "stop_conditions", "escalation_reasons")
    missing = [section for section in required_sections if section not in payload]
    if missing:
        raise RuntimeError(
            "malformed evaluator loop policy artifact: missing top-level section(s): "
            + ", ".join(missing)
        )
    return payload, hashlib.sha256(raw_text.encode("utf-8")).hexdigest()


EVALUATOR_LOOP_POLICY, EVALUATOR_LOOP_POLICY_SHA256 = load_evaluator_loop_policy()


def load_evaluator_intervention_policy() -> tuple[dict[str, Any], str]:
    path = evaluator_intervention_policy_path()
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(
            f"failed to read evaluator intervention policy artifact: {path.as_posix()} ({exc})"
        ) from exc
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"malformed evaluator intervention policy artifact: {path.as_posix()} ({exc})"
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeError(
            "malformed evaluator intervention policy artifact: "
            f"{path.as_posix()} must contain a JSON object"
        )
    required_sections = (
        "selection_mode_defaults",
        "signal_override_order",
        "graph_health_signal_overrides",
        "recommended_action_override_order",
        "recommended_action_overrides",
        "validation_family_override_order",
        "validation_family_overrides",
        "safe_repair_override",
    )
    missing = [section for section in required_sections if section not in payload]
    if missing:
        raise RuntimeError(
            "malformed evaluator intervention policy artifact: missing top-level section(s): "
            + ", ".join(missing)
        )
    return payload, hashlib.sha256(raw_text.encode("utf-8")).hexdigest()


EVALUATOR_INTERVENTION_POLICY, EVALUATOR_INTERVENTION_POLICY_SHA256 = (
    load_evaluator_intervention_policy()
)


def load_evidence_plane_policy() -> tuple[dict[str, Any], str]:
    path = evidence_plane_policy_path()
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(
            f"failed to read evidence plane policy artifact: {path.as_posix()} ({exc})"
        ) from exc
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"malformed evidence plane policy artifact: {path.as_posix()} ({exc})"
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeError(
            "malformed evidence plane policy artifact: "
            f"{path.as_posix()} must contain a JSON object"
        )
    required_sections = (
        "repository_layout",
        "semantic_boundary",
        "index_contract",
        "overlay_contract",
    )
    missing = [section for section in required_sections if section not in payload]
    if missing:
        raise RuntimeError(
            "malformed evidence plane policy artifact: missing top-level section(s): "
            + ", ".join(missing)
        )
    return payload, hashlib.sha256(raw_text.encode("utf-8")).hexdigest()


EVIDENCE_PLANE_POLICY, EVIDENCE_PLANE_POLICY_SHA256 = load_evidence_plane_policy()


def load_metric_signal_policy() -> tuple[dict[str, Any], str]:
    path = metric_signal_policy_path()
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(
            f"failed to read metric signal policy artifact: {path.as_posix()} ({exc})"
        ) from exc
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"malformed metric signal policy artifact: {path.as_posix()} ({exc})"
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeError(
            f"malformed metric signal policy artifact: {path.as_posix()} must contain a JSON object"
        )
    required_sections = (
        "repository_layout",
        "signal_contract",
        "status_scoring",
        "metric_thresholds",
        "metric_composition",
        "proposal_contract",
        "proposal_mapping",
    )
    missing = [section for section in required_sections if section not in payload]
    if missing:
        raise RuntimeError(
            "malformed metric signal policy artifact: missing top-level section(s): "
            + ", ".join(missing)
        )
    return payload, hashlib.sha256(raw_text.encode("utf-8")).hexdigest()


METRIC_SIGNAL_POLICY, METRIC_SIGNAL_POLICY_SHA256 = load_metric_signal_policy()


def load_supervisor_performance_policy() -> tuple[dict[str, Any], str]:
    path = supervisor_performance_policy_path()
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(
            f"failed to read supervisor performance policy artifact: {path.as_posix()} ({exc})"
        ) from exc
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"malformed supervisor performance policy artifact: {path.as_posix()} ({exc})"
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeError(
            "malformed supervisor performance policy artifact: "
            f"{path.as_posix()} must contain a JSON object"
        )
    required_sections = (
        "repository_layout",
        "index_contract",
        "runtime_thresholds",
        "yield_contract",
        "graph_impact_contract",
        "batch_contract",
    )
    missing = [section for section in required_sections if section not in payload]
    if missing:
        raise RuntimeError(
            "malformed supervisor performance policy artifact: missing top-level section(s): "
            + ", ".join(missing)
        )
    return payload, hashlib.sha256(raw_text.encode("utf-8")).hexdigest()


SUPERVISOR_PERFORMANCE_POLICY, SUPERVISOR_PERFORMANCE_POLICY_SHA256 = (
    load_supervisor_performance_policy()
)


def load_external_consumer_overlay_policy() -> tuple[dict[str, Any], str]:
    path = external_consumer_overlay_policy_path()
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(
            f"failed to read external consumer overlay policy artifact: {path.as_posix()} ({exc})"
        ) from exc
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"malformed external consumer overlay policy artifact: {path.as_posix()} ({exc})"
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeError(
            "malformed external consumer overlay policy artifact: "
            f"{path.as_posix()} must contain a JSON object"
        )
    required_sections = (
        "repository_layout",
        "overlay_contract",
        "bridge_statuses",
        "next_gap_defaults",
    )
    missing = [section for section in required_sections if section not in payload]
    if missing:
        raise RuntimeError(
            "malformed external consumer overlay policy artifact: missing top-level section(s): "
            + ", ".join(missing)
        )
    return payload, hashlib.sha256(raw_text.encode("utf-8")).hexdigest()


EXTERNAL_CONSUMER_OVERLAY_POLICY, EXTERNAL_CONSUMER_OVERLAY_POLICY_SHA256 = (
    load_external_consumer_overlay_policy()
)


def load_external_consumer_handoff_policy() -> tuple[dict[str, Any], str]:
    path = external_consumer_handoff_policy_path()
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(
            f"failed to read external consumer handoff policy artifact: {path.as_posix()} ({exc})"
        ) from exc
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"malformed external consumer handoff policy artifact: {path.as_posix()} ({exc})"
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeError(
            "malformed external consumer handoff policy artifact: "
            f"{path.as_posix()} must contain a JSON object"
        )
    required_sections = (
        "repository_layout",
        "handoff_contract",
        "eligibility_rules",
        "packet_provenance",
        "next_gap_defaults",
    )
    missing = [section for section in required_sections if section not in payload]
    if missing:
        raise RuntimeError(
            "malformed external consumer handoff policy artifact: missing top-level section(s): "
            + ", ".join(missing)
        )
    return payload, hashlib.sha256(raw_text.encode("utf-8")).hexdigest()


EXTERNAL_CONSUMER_HANDOFF_POLICY, EXTERNAL_CONSUMER_HANDOFF_POLICY_SHA256 = (
    load_external_consumer_handoff_policy()
)


def load_specpm_export_policy() -> tuple[dict[str, Any], str]:
    path = specpm_export_policy_path()
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(
            f"failed to read SpecPM export policy artifact: {path.as_posix()} ({exc})"
        ) from exc
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"malformed SpecPM export policy artifact: {path.as_posix()} ({exc})"
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeError(
            f"malformed SpecPM export policy artifact: {path.as_posix()} must contain a JSON object"
        )
    required_sections = (
        "repository_layout",
        "consumer_contract",
        "preview_contract",
        "next_gap_defaults",
        "required_export_fields",
        "boundary_spec_gaps",
    )
    missing = [section for section in required_sections if section not in payload]
    if missing:
        raise RuntimeError(
            "malformed SpecPM export policy artifact: missing top-level section(s): "
            + ", ".join(missing)
        )
    return payload, hashlib.sha256(raw_text.encode("utf-8")).hexdigest()


SPECPM_EXPORT_POLICY, SPECPM_EXPORT_POLICY_SHA256 = load_specpm_export_policy()


def load_specpm_handoff_policy() -> tuple[dict[str, Any], str]:
    path = specpm_handoff_policy_path()
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(
            f"failed to read SpecPM handoff policy artifact: {path.as_posix()} ({exc})"
        ) from exc
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"malformed SpecPM handoff policy artifact: {path.as_posix()} ({exc})"
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeError(
            "malformed SpecPM handoff policy artifact: "
            f"{path.as_posix()} must contain a JSON object"
        )
    required_sections = (
        "repository_layout",
        "handoff_contract",
        "packet_provenance",
        "next_gap_defaults",
    )
    missing = [section for section in required_sections if section not in payload]
    if missing:
        raise RuntimeError(
            "malformed SpecPM handoff policy artifact: missing top-level section(s): "
            + ", ".join(missing)
        )
    return payload, hashlib.sha256(raw_text.encode("utf-8")).hexdigest()


SPECPM_HANDOFF_POLICY, SPECPM_HANDOFF_POLICY_SHA256 = load_specpm_handoff_policy()


def load_specpm_materialization_policy() -> tuple[dict[str, Any], str]:
    path = specpm_materialization_policy_path()
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(
            f"failed to read SpecPM materialization policy artifact: {path.as_posix()} ({exc})"
        ) from exc
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"malformed SpecPM materialization policy artifact: {path.as_posix()} ({exc})"
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeError(
            "malformed SpecPM materialization policy artifact: "
            f"{path.as_posix()} must contain a JSON object"
        )
    required_sections = (
        "repository_layout",
        "materialization_contract",
        "eligibility_rules",
        "bundle_layout",
        "boundary_defaults",
        "next_gap_defaults",
    )
    missing = [section for section in required_sections if section not in payload]
    if missing:
        raise RuntimeError(
            "malformed SpecPM materialization policy artifact: missing top-level section(s): "
            + ", ".join(missing)
        )
    return payload, hashlib.sha256(raw_text.encode("utf-8")).hexdigest()


SPECPM_MATERIALIZATION_POLICY, SPECPM_MATERIALIZATION_POLICY_SHA256 = (
    load_specpm_materialization_policy()
)


def load_specpm_import_policy() -> tuple[dict[str, Any], str]:
    path = specpm_import_policy_path()
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError(
            f"failed to read SpecPM import policy artifact: {path.as_posix()} ({exc})"
        ) from exc
    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"malformed SpecPM import policy artifact: {path.as_posix()} ({exc})"
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeError(
            f"malformed SpecPM import policy artifact: {path.as_posix()} must contain a JSON object"
        )
    required_sections = (
        "repository_layout",
        "consumer_contract",
        "bundle_contract",
        "suggested_target_kind_mapping",
        "next_gap_defaults",
    )
    missing = [section for section in required_sections if section not in payload]
    if missing:
        raise RuntimeError(
            "malformed SpecPM import policy artifact: missing top-level section(s): "
            + ", ".join(missing)
        )
    return payload, hashlib.sha256(raw_text.encode("utf-8")).hexdigest()


SPECPM_IMPORT_POLICY, SPECPM_IMPORT_POLICY_SHA256 = load_specpm_import_policy()


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


def operator_request_bridge_policy_lookup(policy_path: str) -> Any:
    current: Any = OPERATOR_REQUEST_BRIDGE_POLICY
    for part in policy_path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(policy_path)
        current = current[part]
    return copy.deepcopy(current)


def external_consumer_overlay_policy_lookup(policy_path: str) -> Any:
    current: Any = EXTERNAL_CONSUMER_OVERLAY_POLICY
    for part in policy_path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(policy_path)
        current = current[part]
    return copy.deepcopy(current)


def external_consumer_handoff_policy_lookup(policy_path: str) -> Any:
    current: Any = EXTERNAL_CONSUMER_HANDOFF_POLICY
    for part in policy_path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(policy_path)
        current = current[part]
    return copy.deepcopy(current)


def specpm_export_policy_lookup(policy_path: str) -> Any:
    current: Any = SPECPM_EXPORT_POLICY
    for part in policy_path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(policy_path)
        current = current[part]
    return copy.deepcopy(current)


def specpm_handoff_policy_lookup(policy_path: str) -> Any:
    current: Any = SPECPM_HANDOFF_POLICY
    for part in policy_path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(policy_path)
        current = current[part]
    return copy.deepcopy(current)


def specpm_materialization_policy_lookup(policy_path: str) -> Any:
    current: Any = SPECPM_MATERIALIZATION_POLICY
    for part in policy_path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(policy_path)
        current = current[part]
    return copy.deepcopy(current)


def specpm_import_policy_lookup(policy_path: str) -> Any:
    current: Any = SPECPM_IMPORT_POLICY
    for part in policy_path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(policy_path)
        current = current[part]
    return copy.deepcopy(current)


def specgraph_vocabulary_lookup(policy_path: str) -> Any:
    current: Any = SPECGRAPH_VOCABULARY
    for part in policy_path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(policy_path)
        current = current[part]
    return copy.deepcopy(current)


def pre_spec_semantics_policy_lookup(policy_path: str) -> Any:
    current: Any = PRE_SPEC_SEMANTICS_POLICY
    for part in policy_path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(policy_path)
        current = current[part]
    return copy.deepcopy(current)


def evidence_plane_policy_lookup(policy_path: str) -> Any:
    current: Any = EVIDENCE_PLANE_POLICY
    for part in policy_path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(policy_path)
        current = current[part]
    return copy.deepcopy(current)


def metric_signal_policy_lookup(policy_path: str) -> Any:
    current: Any = METRIC_SIGNAL_POLICY
    for part in policy_path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(policy_path)
        current = current[part]
    return copy.deepcopy(current)


def supervisor_performance_policy_lookup(policy_path: str) -> Any:
    current: Any = SUPERVISOR_PERFORMANCE_POLICY
    for part in policy_path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise KeyError(policy_path)
        current = current[part]
    return copy.deepcopy(current)


def evaluator_intervention_policy_lookup(policy_path: str) -> Any:
    current: Any = EVALUATOR_INTERVENTION_POLICY
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


def evaluator_intervention_rule(
    policy_path: str,
    *,
    reason: str,
    matched_value: Any | None = None,
    inputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if matched_value is None:
        try:
            matched_value = evaluator_intervention_policy_lookup(policy_path)
        except KeyError:
            matched_value = None
    return {
        "rule_source": "evaluator_intervention_policy",
        "rule_id": policy_path,
        "policy_path": policy_path,
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


def operator_request_bridge_policy_reference() -> dict[str, Any]:
    return {
        "artifact_path": OPERATOR_REQUEST_BRIDGE_POLICY_RELATIVE_PATH,
        "artifact_sha256": OPERATOR_REQUEST_BRIDGE_POLICY_SHA256,
        "version": OPERATOR_REQUEST_BRIDGE_POLICY.get("version"),
    }


def specgraph_vocabulary_reference() -> dict[str, Any]:
    return {
        "artifact_path": SPECGRAPH_VOCABULARY_RELATIVE_PATH,
        "artifact_sha256": SPECGRAPH_VOCABULARY_SHA256,
        "version": SPECGRAPH_VOCABULARY.get("version"),
    }


def pre_spec_semantics_policy_reference() -> dict[str, Any]:
    return {
        "artifact_path": PRE_SPEC_SEMANTICS_POLICY_RELATIVE_PATH,
        "artifact_sha256": PRE_SPEC_SEMANTICS_POLICY_SHA256,
        "version": PRE_SPEC_SEMANTICS_POLICY.get("version"),
    }


def evidence_plane_policy_reference() -> dict[str, Any]:
    return {
        "artifact_path": EVIDENCE_PLANE_POLICY_RELATIVE_PATH,
        "artifact_sha256": EVIDENCE_PLANE_POLICY_SHA256,
        "version": EVIDENCE_PLANE_POLICY.get("version"),
    }


def metric_signal_policy_reference() -> dict[str, Any]:
    return {
        "artifact_path": METRIC_SIGNAL_POLICY_RELATIVE_PATH,
        "artifact_sha256": METRIC_SIGNAL_POLICY_SHA256,
        "version": METRIC_SIGNAL_POLICY.get("version"),
    }


def supervisor_performance_policy_reference() -> dict[str, Any]:
    return {
        "artifact_path": SUPERVISOR_PERFORMANCE_POLICY_RELATIVE_PATH,
        "artifact_sha256": SUPERVISOR_PERFORMANCE_POLICY_SHA256,
        "version": SUPERVISOR_PERFORMANCE_POLICY.get("version"),
    }


def external_consumer_overlay_policy_reference() -> dict[str, Any]:
    return {
        "artifact_path": EXTERNAL_CONSUMER_OVERLAY_POLICY_RELATIVE_PATH,
        "artifact_sha256": EXTERNAL_CONSUMER_OVERLAY_POLICY_SHA256,
        "version": EXTERNAL_CONSUMER_OVERLAY_POLICY.get("version"),
    }


def external_consumer_handoff_policy_reference() -> dict[str, Any]:
    return {
        "artifact_path": EXTERNAL_CONSUMER_HANDOFF_POLICY_RELATIVE_PATH,
        "artifact_sha256": EXTERNAL_CONSUMER_HANDOFF_POLICY_SHA256,
        "version": EXTERNAL_CONSUMER_HANDOFF_POLICY.get("version"),
    }


def specpm_export_policy_reference() -> dict[str, Any]:
    return {
        "artifact_path": SPECPM_EXPORT_POLICY_RELATIVE_PATH,
        "artifact_sha256": SPECPM_EXPORT_POLICY_SHA256,
        "version": SPECPM_EXPORT_POLICY.get("version"),
    }


def specpm_handoff_policy_reference() -> dict[str, Any]:
    return {
        "artifact_path": SPECPM_HANDOFF_POLICY_RELATIVE_PATH,
        "artifact_sha256": SPECPM_HANDOFF_POLICY_SHA256,
        "version": SPECPM_HANDOFF_POLICY.get("version"),
    }


def specpm_materialization_policy_reference() -> dict[str, Any]:
    return {
        "artifact_path": SPECPM_MATERIALIZATION_POLICY_RELATIVE_PATH,
        "artifact_sha256": SPECPM_MATERIALIZATION_POLICY_SHA256,
        "version": SPECPM_MATERIALIZATION_POLICY.get("version"),
    }


def specpm_import_policy_reference() -> dict[str, Any]:
    return {
        "artifact_path": SPECPM_IMPORT_POLICY_RELATIVE_PATH,
        "artifact_sha256": SPECPM_IMPORT_POLICY_SHA256,
        "version": SPECPM_IMPORT_POLICY.get("version"),
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
PRE_SPEC_SEMANTICS_INDEX_FILENAME = Path(
    str(pre_spec_semantics_policy_lookup("repository_layout.index_artifact"))
).name
PRE_SPEC_SEMANTICS_INDEX_ARTIFACT_KIND = str(
    pre_spec_semantics_policy_lookup("index_contract.artifact_kind")
)
PRE_SPEC_SEMANTICS_INDEX_SCHEMA_VERSION = int(
    pre_spec_semantics_policy_lookup("index_contract.schema_version")
)
PRE_SPEC_SEMANTICS_LAYER_NAME = str(
    pre_spec_semantics_policy_lookup("semantic_boundary.layer_name")
)
PRE_SPEC_SEMANTICS_PHASE = str(pre_spec_semantics_policy_lookup("semantic_boundary.phase"))
PRE_SPEC_SEMANTICS_NAMED_FILTERS = list(
    pre_spec_semantics_policy_lookup("index_contract.named_filters")
)
PRE_SPEC_IMPLEMENTED_ARTIFACT_CLASSES = pre_spec_semantics_policy_lookup(
    "artifact_classes.implemented_tracked_classes"
)
PRE_SPEC_RESERVED_PRIMARY_KINDS = list(
    pre_spec_semantics_policy_lookup("artifact_classes.reserved_primary_kinds")
)
PRE_SPEC_REQUIRED_AXES = list(pre_spec_semantics_policy_lookup("axes_contract.required_axes"))
EVIDENCE_PLANE_INDEX_FILENAME = Path(
    str(evidence_plane_policy_lookup("repository_layout.index_artifact"))
).name
EVIDENCE_PLANE_OVERLAY_FILENAME = Path(
    str(evidence_plane_policy_lookup("repository_layout.overlay_artifact"))
).name
EVIDENCE_PLANE_LAYER_NAME = str(evidence_plane_policy_lookup("semantic_boundary.layer_name"))
EVIDENCE_PLANE_SEMANTIC_CHAIN = list(
    evidence_plane_policy_lookup("semantic_boundary.semantic_chain")
)
EVIDENCE_PLANE_INDEX_ARTIFACT_KIND = str(
    evidence_plane_policy_lookup("index_contract.artifact_kind")
)
EVIDENCE_PLANE_INDEX_SCHEMA_VERSION = int(
    evidence_plane_policy_lookup("index_contract.schema_version")
)
EVIDENCE_PLANE_CHAIN_STATUSES = list(evidence_plane_policy_lookup("index_contract.chain_statuses"))
EVIDENCE_PLANE_COVERAGE_STATUSES = list(
    evidence_plane_policy_lookup("index_contract.coverage_statuses")
)
EVIDENCE_PLANE_STAGE_STATUSES = list(evidence_plane_policy_lookup("index_contract.stage_statuses"))
EVIDENCE_PLANE_OVERLAY_ARTIFACT_KIND = str(
    evidence_plane_policy_lookup("overlay_contract.artifact_kind")
)
EVIDENCE_PLANE_OVERLAY_SCHEMA_VERSION = int(
    evidence_plane_policy_lookup("overlay_contract.schema_version")
)
EVIDENCE_PLANE_NAMED_FILTERS = list(evidence_plane_policy_lookup("overlay_contract.named_filters"))
EXTERNAL_CONSUMER_INDEX_FILENAME = "external_consumer_index.json"
EXTERNAL_CONSUMER_INDEX_ARTIFACT_KIND = "external_consumer_index"
EXTERNAL_CONSUMER_INDEX_SCHEMA_VERSION = 1
EXTERNAL_CONSUMER_OVERLAY_FILENAME = Path(
    str(external_consumer_overlay_policy_lookup("repository_layout.overlay_artifact"))
).name
EXTERNAL_CONSUMER_OVERLAY_ARTIFACT_KIND = str(
    external_consumer_overlay_policy_lookup("overlay_contract.artifact_kind")
)
EXTERNAL_CONSUMER_OVERLAY_SCHEMA_VERSION = int(
    external_consumer_overlay_policy_lookup("overlay_contract.schema_version")
)
EXTERNAL_CONSUMER_LAYER_NAME = str(
    external_consumer_overlay_policy_lookup("overlay_contract.layer_name")
)
EXTERNAL_CONSUMER_BRIDGE_STATUSES = list(external_consumer_overlay_policy_lookup("bridge_statuses"))
EXTERNAL_CONSUMER_NAMED_FILTERS = list(
    external_consumer_overlay_policy_lookup("overlay_contract.named_filters")
)
EXTERNAL_CONSUMER_HANDOFF_FILENAME = Path(
    str(external_consumer_handoff_policy_lookup("repository_layout.artifact"))
).name
EXTERNAL_CONSUMER_HANDOFF_ARTIFACT_KIND = str(
    external_consumer_handoff_policy_lookup("handoff_contract.artifact_kind")
)
EXTERNAL_CONSUMER_HANDOFF_SCHEMA_VERSION = int(
    external_consumer_handoff_policy_lookup("handoff_contract.schema_version")
)
EXTERNAL_CONSUMER_HANDOFF_TRANSITION_PROFILE = str(
    external_consumer_handoff_policy_lookup("handoff_contract.transition_profile")
)
EXTERNAL_CONSUMER_HANDOFF_PACKET_TYPE = str(
    external_consumer_handoff_policy_lookup("handoff_contract.packet_type")
)
EXTERNAL_CONSUMER_HANDOFF_TARGET_ARTIFACT_CLASS = str(
    external_consumer_handoff_policy_lookup("handoff_contract.target_artifact_class")
)
EXTERNAL_CONSUMER_HANDOFF_STATUSES = list(
    external_consumer_handoff_policy_lookup("handoff_contract.handoff_statuses")
)
EXTERNAL_CONSUMER_HANDOFF_REVIEW_STATES = list(
    external_consumer_handoff_policy_lookup("handoff_contract.review_states")
)
EXTERNAL_CONSUMER_HANDOFF_NAMED_FILTERS = list(
    external_consumer_handoff_policy_lookup("handoff_contract.named_filters")
)
SPECPM_EXPORT_PREVIEW_FILENAME = Path(
    str(specpm_export_policy_lookup("repository_layout.preview_artifact"))
).name
SPECPM_EXPORT_PREVIEW_ARTIFACT_KIND = str(
    specpm_export_policy_lookup("preview_contract.artifact_kind")
)
SPECPM_EXPORT_PREVIEW_SCHEMA_VERSION = int(
    specpm_export_policy_lookup("preview_contract.schema_version")
)
SPECPM_EXPORT_PREVIEW_STATUSES = list(specpm_export_policy_lookup("preview_contract.status_values"))
SPECPM_EXPORT_PREVIEW_REVIEW_STATES = list(
    specpm_export_policy_lookup("preview_contract.review_states")
)
SPECPM_EXPORT_PREVIEW_NAMED_FILTERS = list(
    specpm_export_policy_lookup("preview_contract.named_filters")
)
SPECPM_HANDOFF_FILENAME = Path(str(specpm_handoff_policy_lookup("repository_layout.artifact"))).name
SPECPM_HANDOFF_ARTIFACT_KIND = str(specpm_handoff_policy_lookup("handoff_contract.artifact_kind"))
SPECPM_HANDOFF_SCHEMA_VERSION = int(specpm_handoff_policy_lookup("handoff_contract.schema_version"))
SPECPM_HANDOFF_TRANSITION_PROFILE = str(
    specpm_handoff_policy_lookup("handoff_contract.transition_profile")
)
SPECPM_HANDOFF_PACKET_TYPE = str(specpm_handoff_policy_lookup("handoff_contract.packet_type"))
SPECPM_HANDOFF_TARGET_ARTIFACT_CLASS = str(
    specpm_handoff_policy_lookup("handoff_contract.target_artifact_class")
)
SPECPM_HANDOFF_STATUSES = list(specpm_handoff_policy_lookup("handoff_contract.handoff_statuses"))
SPECPM_HANDOFF_REVIEW_STATES = list(specpm_handoff_policy_lookup("handoff_contract.review_states"))
SPECPM_HANDOFF_NAMED_FILTERS = list(specpm_handoff_policy_lookup("handoff_contract.named_filters"))
SPECPM_MATERIALIZATION_REPORT_FILENAME = Path(
    str(specpm_materialization_policy_lookup("repository_layout.report_artifact"))
).name
SPECPM_MATERIALIZATION_REPORT_ARTIFACT_KIND = str(
    specpm_materialization_policy_lookup("materialization_contract.artifact_kind")
)
SPECPM_MATERIALIZATION_REPORT_SCHEMA_VERSION = int(
    specpm_materialization_policy_lookup("materialization_contract.schema_version")
)
SPECPM_MATERIALIZATION_ENTRY_STATUSES = list(
    specpm_materialization_policy_lookup("materialization_contract.entry_statuses")
)
SPECPM_MATERIALIZATION_REVIEW_STATES = list(
    specpm_materialization_policy_lookup("materialization_contract.review_states")
)
SPECPM_MATERIALIZATION_NAMED_FILTERS = list(
    specpm_materialization_policy_lookup("materialization_contract.named_filters")
)
SPECPM_IMPORT_PREVIEW_FILENAME = Path(
    str(specpm_import_policy_lookup("repository_layout.artifact"))
).name
SPECPM_IMPORT_PREVIEW_ARTIFACT_KIND = str(
    specpm_import_policy_lookup("bundle_contract.artifact_kind")
)
SPECPM_IMPORT_PREVIEW_SCHEMA_VERSION = int(
    specpm_import_policy_lookup("bundle_contract.schema_version")
)
SPECPM_IMPORT_PREVIEW_STATUSES = list(specpm_import_policy_lookup("bundle_contract.status_values"))
SPECPM_IMPORT_PREVIEW_REVIEW_STATES = list(
    specpm_import_policy_lookup("bundle_contract.review_states")
)
SPECPM_IMPORT_PREVIEW_NAMED_FILTERS = list(
    specpm_import_policy_lookup("bundle_contract.named_filters")
)
METRIC_SIGNAL_INDEX_FILENAME = Path(
    str(metric_signal_policy_lookup("repository_layout.signal_artifact"))
).name
METRIC_THRESHOLD_PROPOSALS_FILENAME = Path(
    str(metric_signal_policy_lookup("repository_layout.proposal_artifact"))
).name
METRIC_SIGNAL_INDEX_ARTIFACT_KIND = str(
    metric_signal_policy_lookup("signal_contract.artifact_kind")
)
METRIC_SIGNAL_INDEX_SCHEMA_VERSION = int(
    metric_signal_policy_lookup("signal_contract.schema_version")
)
METRIC_SIGNAL_METRIC_IDS = list(metric_signal_policy_lookup("signal_contract.metric_ids"))
METRIC_SIGNAL_STATUSES = list(metric_signal_policy_lookup("signal_contract.metric_statuses"))
METRIC_SIGNAL_NAMED_FILTERS = list(metric_signal_policy_lookup("signal_contract.named_filters"))
METRIC_THRESHOLD_PROPOSALS_ARTIFACT_KIND = str(
    metric_signal_policy_lookup("proposal_contract.artifact_kind")
)
METRIC_THRESHOLD_PROPOSALS_SCHEMA_VERSION = int(
    metric_signal_policy_lookup("proposal_contract.schema_version")
)
METRIC_THRESHOLD_PROPOSAL_KINDS = list(
    metric_signal_policy_lookup("proposal_contract.proposal_kinds")
)
METRIC_THRESHOLD_PROPOSAL_NAMED_FILTERS = list(
    metric_signal_policy_lookup("proposal_contract.named_filters")
)
SUPERVISOR_PERFORMANCE_INDEX_FILENAME = Path(
    str(supervisor_performance_policy_lookup("repository_layout.index_artifact"))
).name
SUPERVISOR_PERFORMANCE_INDEX_ARTIFACT_KIND = str(
    supervisor_performance_policy_lookup("index_contract.artifact_kind")
)
SUPERVISOR_PERFORMANCE_INDEX_SCHEMA_VERSION = int(
    supervisor_performance_policy_lookup("index_contract.schema_version")
)
SUPERVISOR_PERFORMANCE_RUNTIME_STATUSES = list(
    supervisor_performance_policy_lookup("index_contract.runtime_statuses")
)
SUPERVISOR_PERFORMANCE_YIELD_STATUSES = list(
    supervisor_performance_policy_lookup("index_contract.yield_statuses")
)
SUPERVISOR_PERFORMANCE_GRAPH_IMPACT_STATUSES = list(
    supervisor_performance_policy_lookup("index_contract.graph_impact_statuses")
)
SUPERVISOR_PERFORMANCE_NAMED_FILTERS = list(
    supervisor_performance_policy_lookup("index_contract.named_filters")
)
SUPERVISOR_PERFORMANCE_SLOW_RUN_THRESHOLD_SECONDS = float(
    supervisor_performance_policy_lookup("runtime_thresholds.slow_run_duration_sec")
)
SUPERVISOR_PERFORMANCE_PROPOSAL_RUN_KINDS = set(
    supervisor_performance_policy_lookup("yield_contract.proposal_run_kinds")
)
SUPERVISOR_PERFORMANCE_REVIEW_PENDING_GATE_STATES = set(
    supervisor_performance_policy_lookup("yield_contract.review_pending_gate_states")
)
SUPERVISOR_PERFORMANCE_BLOCKED_GATE_STATES = set(
    supervisor_performance_policy_lookup("graph_impact_contract.blocked_gate_states")
)
SUPERVISOR_PERFORMANCE_REPEAT_HOTSPOT_RUN_COUNT = int(
    supervisor_performance_policy_lookup("batch_contract.repeat_hotspot_run_count")
)
OPERATOR_REQUEST_PACKET_ARTIFACT_KIND = str(
    operator_request_bridge_policy_lookup("packet_contract.artifact_kind")
)
OPERATOR_REQUEST_PACKET_SCHEMA_VERSION = int(
    operator_request_bridge_policy_lookup("packet_contract.schema_version")
)
OPERATOR_REQUEST_SOURCE_KINDS = set(
    operator_request_bridge_policy_lookup("packet_contract.source_kinds")
)
OPERATOR_REQUEST_RUN_MODES = set(operator_request_bridge_policy_lookup("packet_contract.run_modes"))
OPERATOR_REQUEST_REQUIRED_TOP_LEVEL_SECTIONS = tuple(
    operator_request_bridge_policy_lookup("packet_contract.required_top_level_sections")
)
OPERATOR_REQUEST_REQUIRED_USER_INTENT_FIELDS = tuple(
    operator_request_bridge_policy_lookup("packet_contract.required_user_intent_fields")
)
OPERATOR_REQUEST_REQUIRED_REQUEST_FIELDS = tuple(
    operator_request_bridge_policy_lookup("packet_contract.required_operator_request_fields")
)
OPERATOR_REQUEST_OPTIONAL_REQUEST_FIELDS = tuple(
    operator_request_bridge_policy_lookup("packet_contract.optional_operator_request_fields")
)
OPERATOR_REQUEST_EXECUTION_CONTRACT_REQUIRED_FIELDS = tuple(
    operator_request_bridge_policy_lookup(
        "typed_request_contract.execution_contract.required_fields"
    )
)
OPERATOR_REQUEST_ALLOWED_STOP_CONDITIONS = tuple(
    operator_request_bridge_policy_lookup(
        "typed_request_contract.execution_contract.allowed_stop_conditions"
    )
)
OPERATOR_REQUEST_DEFAULT_STOP_CONDITIONS = tuple(
    operator_request_bridge_policy_lookup(
        "typed_request_contract.execution_contract.default_stop_conditions"
    )
)
OPERATOR_REQUEST_AUTHORITY_REQUIRED_FIELDS = tuple(
    operator_request_bridge_policy_lookup(
        "typed_request_contract.execution_contract.authority_shape.required_fields"
    )
)
SPECGRAPH_VOCABULARY_ARTIFACT_KIND = str(specgraph_vocabulary_lookup("artifact_kind"))
SPECGRAPH_VOCABULARY_VERSION = int(specgraph_vocabulary_lookup("version"))
SPECGRAPH_VOCABULARY_FAMILIES = specgraph_vocabulary_lookup("term_families")
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
GRAPH_DASHBOARD_FILENAME = "graph_dashboard.json"
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


def validation_findings_policy_reference() -> dict[str, Any]:
    return {
        "path": VALIDATION_FINDINGS_POLICY_RELATIVE_PATH,
        "sha256": VALIDATION_FINDINGS_POLICY_SHA256,
    }


def validation_finding(
    *,
    code: str,
    family: str,
    error_class: str,
    message: str,
    severity: str = "error",
    field: str = "",
    path: str = "",
    spec_id: str = "",
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_severity = (
        severity
        if severity in set(VALIDATION_FINDINGS_POLICY.get("severity_levels", []))
        else "error"
    )
    finding = {
        "code": str(code).strip(),
        "family": str(family).strip(),
        "error_class": str(error_class).strip(),
        "severity": normalized_severity,
        "message": str(message).strip(),
    }
    if field.strip():
        finding["field"] = field.strip()
    if path.strip():
        finding["path"] = path.strip()
    if spec_id.strip():
        finding["spec_id"] = spec_id.strip()
    if details:
        finding["details"] = copy.deepcopy(details)
    return finding


def coerce_validation_findings(items: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code", "")).strip()
        family = str(item.get("family", "")).strip()
        error_class = str(item.get("error_class", "")).strip()
        message = str(item.get("message", "")).strip()
        if not all((code, family, error_class, message)):
            continue
        findings.append(
            validation_finding(
                code=code,
                family=family,
                error_class=error_class,
                message=message,
                severity=str(item.get("severity", "error")).strip() or "error",
                field=str(item.get("field", "")).strip(),
                path=str(item.get("path", "")).strip(),
                spec_id=str(item.get("spec_id", "")).strip(),
                details=item.get("details") if isinstance(item.get("details"), dict) else None,
            )
        )
    return findings


def validation_messages(findings: list[dict[str, Any]] | None) -> list[str]:
    messages: list[str] = []
    for finding in coerce_validation_findings(findings):
        message = str(finding.get("message", "")).strip()
        if not message:
            continue
        messages.append(message)
    return messages


def formatted_validation_messages(findings: list[dict[str, Any]] | None) -> list[str]:
    messages: list[str] = []
    for finding in coerce_validation_findings(findings):
        family = str(finding.get("family", "")).strip()
        error_class = str(finding.get("error_class", "")).strip()
        code = str(finding.get("code", "")).strip()
        prefix = "/".join(part for part in (family, error_class, code) if part)
        message = str(finding.get("message", "")).strip()
        if not message:
            continue
        messages.append(f"[{prefix}] {message}" if prefix else message)
    return messages


def validation_summary(findings: list[dict[str, Any]] | None) -> dict[str, Any]:
    normalized = coerce_validation_findings(findings)
    families: dict[str, int] = {}
    error_classes: dict[str, int] = {}
    severity_counts: dict[str, int] = {}
    codes: dict[str, int] = {}
    for finding in normalized:
        family = str(finding.get("family", "")).strip()
        if family:
            families[family] = families.get(family, 0) + 1
        error_class = str(finding.get("error_class", "")).strip()
        if error_class:
            error_classes[error_class] = error_classes.get(error_class, 0) + 1
        severity = str(finding.get("severity", "")).strip() or "error"
        severity_counts[severity] = severity_counts.get(severity, 0) + 1
        code = str(finding.get("code", "")).strip()
        if code:
            codes[code] = codes.get(code, 0) + 1
    return {
        "finding_count": len(normalized),
        "families": families,
        "error_classes": error_classes,
        "severity_counts": severity_counts,
        "codes": codes,
    }


def string_errors_to_validation_findings(
    errors: list[str] | None,
    *,
    family: str,
    error_class: str,
    code: str,
    severity: str = "error",
    field: str = "",
    path: str = "",
    spec_id: str = "",
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for error in errors or []:
        message = str(error).strip()
        if not message:
            continue
        findings.append(
            validation_finding(
                code=code,
                family=family,
                error_class=error_class,
                message=message,
                severity=severity,
                field=field,
                path=path,
                spec_id=spec_id,
            )
        )
    return findings


def safe_repair_policy_reference() -> dict[str, Any]:
    return {
        "path": SAFE_REPAIR_POLICY_RELATIVE_PATH,
        "sha256": SAFE_REPAIR_POLICY_SHA256,
    }


def safe_repair_dir_path() -> Path:
    return RUNS_DIR / "safe_repairs"


def safe_repair_artifact_path(run_id: str) -> Path:
    return safe_repair_dir_path() / f"{run_id}.json"


def write_safe_repair_artifact(payload: dict[str, Any]) -> Path:
    path = safe_repair_artifact_path(str(payload.get("run_id", "")).strip())
    path.parent.mkdir(parents=True, exist_ok=True)
    with artifact_lock(path):
        atomic_write_json(path, payload)
    return path


def evaluator_loop_policy_reference() -> dict[str, Any]:
    return {
        "path": EVALUATOR_LOOP_POLICY_RELATIVE_PATH,
        "sha256": EVALUATOR_LOOP_POLICY_SHA256,
    }


def evaluator_intervention_policy_reference() -> dict[str, Any]:
    return {
        "path": EVALUATOR_INTERVENTION_POLICY_RELATIVE_PATH,
        "sha256": EVALUATOR_INTERVENTION_POLICY_SHA256,
    }


def evaluator_control_dir_path() -> Path:
    return RUNS_DIR / "evaluator_control"


def evaluator_control_artifact_path(run_id: str) -> Path:
    return evaluator_control_dir_path() / f"{run_id}.json"


def write_evaluator_control_artifact(payload: dict[str, Any]) -> Path:
    path = evaluator_control_artifact_path(str(payload.get("run_id", "")).strip())
    path.parent.mkdir(parents=True, exist_ok=True)
    with artifact_lock(path):
        atomic_write_json(path, payload)
    return path


def choose_evaluator_intervention(
    *,
    selected_by_rule: dict[str, Any],
    graph_health: dict[str, Any],
    validation_findings: list[dict[str, Any]],
    safe_repair_contract: dict[str, Any] | None = None,
) -> tuple[str, list[dict[str, Any]]]:
    selection_mode = str(selected_by_rule.get("selection_mode", "")).strip()
    refactor_work_item = (
        selected_by_rule.get("refactor_work_item")
        if isinstance(selected_by_rule.get("refactor_work_item"), dict)
        else None
    )
    selection_defaults = evaluator_intervention_policy_lookup("selection_mode_defaults")
    chosen_intervention = str(selection_defaults.get(selection_mode, "refine")).strip() or "refine"
    applied_rules: list[dict[str, Any]] = [
        evaluator_intervention_rule(
            f"selection_mode_defaults.{selection_mode}",
            reason="selection mode established the baseline evaluator intervention",
            matched_value=chosen_intervention,
            inputs={"selection_mode": selection_mode},
        )
    ]

    signals = {str(item).strip() for item in graph_health.get("signals", []) if str(item).strip()}
    signal_overrides = evaluator_intervention_policy_lookup("graph_health_signal_overrides")
    for signal_name in evaluator_intervention_policy_lookup("signal_override_order"):
        signal_text = str(signal_name).strip()
        if not signal_text or signal_text not in signals:
            continue
        override = str(signal_overrides.get(signal_text, "")).strip()
        if not override:
            continue
        chosen_intervention = override
        applied_rules.append(
            evaluator_intervention_rule(
                f"graph_health_signal_overrides.{signal_text}",
                reason="derived graph-health signal promoted a more specific intervention",
                matched_value=override,
                inputs={"signal": signal_text, "signals": sorted(signals)},
            )
        )
        break

    recommended_actions = {
        str(item).strip()
        for item in graph_health.get("recommended_actions", [])
        if str(item).strip()
    }
    action_overrides = evaluator_intervention_policy_lookup("recommended_action_overrides")
    for action_name in evaluator_intervention_policy_lookup("recommended_action_override_order"):
        action_text = str(action_name).strip()
        if not action_text or action_text not in recommended_actions:
            continue
        override = str(action_overrides.get(action_text, "")).strip()
        if not override:
            continue
        chosen_intervention = override
        applied_rules.append(
            evaluator_intervention_rule(
                f"recommended_action_overrides.{action_text}",
                reason="derived recommended action refined the intervention choice",
                matched_value=override,
                inputs={
                    "recommended_action": action_text,
                    "recommended_actions": sorted(recommended_actions),
                },
            )
        )
        break

    validation_families = set(validation_summary(validation_findings).get("families", {}))
    family_overrides = evaluator_intervention_policy_lookup("validation_family_overrides")
    for family_name in evaluator_intervention_policy_lookup("validation_family_override_order"):
        family_text = str(family_name).strip()
        if not family_text or family_text not in validation_families:
            continue
        override = str(family_overrides.get(family_text, "")).strip()
        if not override:
            continue
        if chosen_intervention in {"handoff", "apply"}:
            continue
        if family_text == "authority" and chosen_intervention in {"refine", "rewrite", "merge"}:
            chosen_intervention = override
            applied_rules.append(
                evaluator_intervention_rule(
                    f"validation_family_overrides.{family_text}",
                    reason=(
                        "authority constraints require a reviewable mediated intervention "
                        "instead of direct local mutation"
                    ),
                    matched_value=override,
                    inputs={"validation_families": sorted(validation_families)},
                )
            )
            break

    safe_repair_count = int((safe_repair_contract or {}).get("repair_count") or 0)
    if safe_repair_count and chosen_intervention == "refine":
        applied_rules.append(
            evaluator_intervention_rule(
                "safe_repair_override",
                reason=(
                    "bounded safe-repair activity kept the evaluator intervention in the "
                    "local refinement lane"
                ),
                matched_value=evaluator_intervention_policy_lookup("safe_repair_override"),
                inputs={"repair_count": safe_repair_count},
            )
        )

    if (
        selection_mode == "split_refactor_proposal"
        and str((refactor_work_item or {}).get("signal", "")).strip()
        == TECHSPEC_HANDOFF_PRIMARY_SIGNAL
        and chosen_intervention == "propose"
    ):
        chosen_intervention = "handoff"
        applied_rules.append(
            evaluator_intervention_rule(
                f"graph_health_signal_overrides.{TECHSPEC_HANDOFF_PRIMARY_SIGNAL}",
                reason="TechSpec handoff split proposals should surface as handoff interventions",
                matched_value="handoff",
                inputs={"selection_mode": selection_mode},
            )
        )

    return chosen_intervention, dedupe_decision_rules(applied_rules)


def build_evaluator_loop_control(
    *,
    run_id: str,
    spec_id: str,
    selected_by_rule: dict[str, Any],
    outcome: str,
    gate_state: str,
    blocker: str,
    required_human_action: str,
    graph_health: dict[str, Any],
    validation_findings: list[dict[str, Any]],
    safe_repair_contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    selection_mode = str(selected_by_rule.get("selection_mode", "")).strip()
    refactor_work_item = (
        selected_by_rule.get("refactor_work_item")
        if isinstance(selected_by_rule.get("refactor_work_item"), dict)
        else None
    )
    chosen_intervention, applied_rules = choose_evaluator_intervention(
        selected_by_rule=selected_by_rule,
        graph_health=graph_health,
        validation_findings=validation_findings,
        safe_repair_contract=safe_repair_contract,
    )
    stop_conditions: list[str] = []
    if gate_state == "review_pending":
        stop_conditions.append("review_gate_created")
    elif outcome == "split_required":
        stop_conditions.append("split_required")
    elif outcome == "done" and gate_state == "none":
        stop_conditions.append("canonical_change_synced")
    elif outcome == "blocked":
        if any(
            str(finding.get("family", "")).strip() == "executor_environment"
            for finding in validation_findings
        ):
            stop_conditions.append("blocked_by_runtime_failure")
        else:
            stop_conditions.append("blocked_by_validation_failure")
    if chosen_intervention == "propose":
        stop_conditions.append("proposal_emitted")
    if chosen_intervention == "handoff":
        stop_conditions.append("handoff_emitted")

    escalation_reasons: list[str] = []
    if any(
        str(finding.get("family", "")).strip() == "executor_environment"
        for finding in validation_findings
    ):
        escalation_reasons.append("executor_environment_failure")
    if any(
        str(finding.get("family", "")).strip() == "artifact"
        and str(finding.get("error_class", "")).strip() == "artifact_integrity_failure"
        for finding in validation_findings
    ):
        escalation_reasons.append("runtime_artifact_failure")
    if any(
        str(finding.get("family", "")).strip() == "authority" for finding in validation_findings
    ):
        escalation_reasons.append("authority_constraint")
    if gate_state == "review_pending":
        escalation_reasons.append("human_review_required")
    if not escalation_reasons and blocker and blocker != "none":
        escalation_reasons.append("unknown")

    return {
        "artifact_kind": "evaluator_loop_control",
        "schema_version": 1,
        "run_id": run_id,
        "spec_id": spec_id,
        "generated_at": utc_now_iso(),
        "policy_reference": evaluator_loop_policy_reference(),
        "intervention_policy_reference": evaluator_intervention_policy_reference(),
        "chosen_intervention": chosen_intervention,
        "selection_mode": selection_mode,
        "applied_rules": applied_rules,
        "improvement_basis": {
            "graph_health_signals": list(graph_health.get("signals", [])),
            "graph_health_recommended_actions": list(graph_health.get("recommended_actions", [])),
            "validation_summary": validation_summary(validation_findings),
            "required_human_action": required_human_action,
            "safe_repair_applied": bool((safe_repair_contract or {}).get("repair_count")),
            "refactor_work_item": copy.deepcopy(refactor_work_item) if refactor_work_item else {},
        },
        "stop_conditions": sorted(set(stop_conditions)),
        "escalation_reasons": sorted(set(escalation_reasons)),
    }


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
    validation_findings: list[dict[str, Any]],
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
    messages = formatted_validation_messages(validation_findings)
    if messages:
        emit("\n=== validation errors ===", file=sys.stderr)
        for error in messages:
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
    "last_pre_spec_provenance",
    "pending_sync_paths",
    "pending_base_digests",
    "pending_candidate_digests",
    "pending_run_id",
}
DERIVED_SPEC_TRACKING_KEYS = {"created_at", "updated_at", "last_pre_spec_provenance"}
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


def median_float(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return float(ordered[midpoint])
    return round((ordered[midpoint - 1] + ordered[midpoint]) / 2.0, 3)


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


def build_safe_repair_contract(
    *,
    run_id: str,
    spec_id: str,
    repair_paths: list[str],
) -> dict[str, Any]:
    repairs: list[dict[str, Any]] = []
    repair_definition = SAFE_REPAIR_POLICY.get("repair_kinds", {}).get("yaml_candidate_repair", {})
    application_scope = str(repair_definition.get("application_scope", "")).strip()
    bounded_by = [
        str(item).strip() for item in repair_definition.get("bounded_by", []) if str(item).strip()
    ]
    for path in sorted({str(item).strip() for item in repair_paths if str(item).strip()}):
        repairs.append(
            {
                "repair_id": f"yaml_candidate_repair::{path}",
                "repair_kind": "yaml_candidate_repair",
                "application_scope": application_scope,
                "status": "applied",
                "target_path": path,
                "bounded_write_surface": [path],
                "bounded_by": bounded_by,
                "canonical_write": False,
                "requires_followup_validation": True,
                "trigger_findings": [
                    validation_finding(
                        code="candidate_yaml_requires_safe_repair",
                        family="yaml",
                        error_class="parse_failure",
                        message=(
                            "Recoverable YAML candidate repair was required before bounded "
                            "validation could continue."
                        ),
                        path=path,
                    )
                ],
            }
        )
    return {
        "artifact_kind": "safe_repair_contract",
        "schema_version": 1,
        "run_id": run_id,
        "spec_id": spec_id,
        "generated_at": utc_now_iso(),
        "policy_reference": safe_repair_policy_reference(),
        "repair_count": len(repairs),
        "repairs": repairs,
    }


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


def executor_environment_validation_findings(
    executor_environment: dict[str, Any],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    for issue in executor_environment.get("issues", []):
        if not isinstance(issue, dict):
            continue
        summary = str(issue.get("summary", "")).strip() or "Executor environment failure"
        evidence = issue.get("evidence", [])
        message = (
            f"{summary} Evidence: {evidence[0]}"
            if isinstance(evidence, list) and evidence
            else summary
        )
        findings.append(
            validation_finding(
                code=str(issue.get("kind", "")).strip() or "executor_environment_failure",
                family="executor_environment",
                error_class="runtime_failure",
                message=message,
                details={"evidence": evidence[:3] if isinstance(evidence, list) else []},
            )
        )
    return findings


def executor_environment_validation_errors(executor_environment: dict[str, Any]) -> list[str]:
    return validation_messages(executor_environment_validation_findings(executor_environment))


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


def parse_executor_protocol(stdout: str, returncode: int) -> tuple[str, str, list[dict[str, Any]]]:
    default_outcome = "done" if returncode == 0 else "escalate"

    outcome = default_outcome
    protocol_errors: list[dict[str, Any]] = []
    outcome_match = re.search(r"^RUN_OUTCOME:\s*([a-z_]+)\s*$", stdout, flags=re.MULTILINE)
    if outcome_match:
        candidate = outcome_match.group(1).strip().lower()
        if candidate in ALLOWED_OUTCOMES:
            outcome = candidate
        else:
            outcome = "escalate"
            protocol_errors.append(
                validation_finding(
                    code="invalid_executor_protocol_run_outcome",
                    family="runtime_protocol",
                    error_class="protocol_failure",
                    field="RUN_OUTCOME",
                    message=f"Invalid executor machine protocol marker RUN_OUTCOME: {candidate}",
                )
            )
    else:
        protocol_errors.append(
            validation_finding(
                code="missing_executor_protocol_run_outcome",
                family="runtime_protocol",
                error_class="protocol_failure",
                field="RUN_OUTCOME",
                message="Missing executor machine protocol marker RUN_OUTCOME",
            )
        )

    blocker = ""
    blocker_match = re.search(r"^BLOCKER:\s*(.+)\s*$", stdout, flags=re.MULTILINE)
    if blocker_match:
        blocker = blocker_match.group(1).strip()
        if blocker.lower() == "none":
            blocker = ""
    else:
        protocol_errors.append(
            validation_finding(
                code="missing_executor_protocol_blocker",
                family="runtime_protocol",
                error_class="protocol_failure",
                field="BLOCKER",
                message="Missing executor machine protocol marker BLOCKER",
            )
        )

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


def pre_spec_semantics_index_path() -> Path:
    return RUNS_DIR / PRE_SPEC_SEMANTICS_INDEX_FILENAME


def vocabulary_index_path() -> Path:
    return RUNS_DIR / "vocabulary_index.json"


def vocabulary_drift_report_path() -> Path:
    return RUNS_DIR / "vocabulary_drift_report.json"


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


def iter_vocabulary_entries() -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    contexts = SPECGRAPH_VOCABULARY.get("contexts", {})
    for family_name, family in sorted(SPECGRAPH_VOCABULARY_FAMILIES.items()):
        if not isinstance(family, dict):
            continue
        description = str(family.get("description", "")).strip()
        owner_specs = sorted(
            {
                str(spec_id).strip()
                for spec_id in family.get("owner_specs", [])
                if str(spec_id).strip()
            }
        )
        owner_artifacts = sorted(
            {str(path).strip() for path in family.get("owner_artifacts", []) if str(path).strip()}
        )
        family_contexts = sorted(
            {
                context_name
                for context_name, context in contexts.items()
                if isinstance(context, dict)
                and any(
                    spec_id in owner_specs
                    for spec_id in (str(item).strip() for item in context.get("owner_specs", []))
                    if spec_id
                )
            }
        )
        canonical_terms = family.get("canonical_terms", {})
        if not isinstance(canonical_terms, dict):
            continue
        for canonical_term, definition in sorted(canonical_terms.items()):
            if not isinstance(definition, dict):
                continue
            entries.append(
                {
                    "family": family_name,
                    "canonical_term": str(canonical_term).strip(),
                    "definition": str(definition.get("definition", "")).strip(),
                    "aliases": sorted(
                        {
                            str(alias).strip()
                            for alias in definition.get("aliases", [])
                            if str(alias).strip()
                        }
                    ),
                    "deprecated_aliases": sorted(
                        {
                            str(alias).strip()
                            for alias in definition.get("deprecated_aliases", [])
                            if str(alias).strip()
                        }
                    ),
                    "family_description": description,
                    "owner_specs": owner_specs,
                    "owner_artifacts": owner_artifacts,
                    "contexts": family_contexts,
                }
            )
    return entries


def vocabulary_term_resolution(
    term: str,
    *,
    family: str | None = None,
) -> dict[str, str] | None:
    normalized = str(term).strip()
    if not normalized:
        return None
    for entry in iter_vocabulary_entries():
        if family is not None and entry["family"] != family:
            continue
        canonical_term = str(entry["canonical_term"]).strip()
        if normalized == canonical_term:
            return {
                "family": str(entry["family"]),
                "canonical_term": canonical_term,
                "resolution_kind": "canonical",
            }
        if normalized in entry["aliases"]:
            return {
                "family": str(entry["family"]),
                "canonical_term": canonical_term,
                "resolution_kind": "alias",
            }
        if normalized in entry["deprecated_aliases"]:
            return {
                "family": str(entry["family"]),
                "canonical_term": canonical_term,
                "resolution_kind": "deprecated_alias",
            }
    return None


def build_vocabulary_index() -> dict[str, Any]:
    entries = iter_vocabulary_entries()
    alias_index: dict[str, list[str]] = {}
    deprecated_alias_index: dict[str, list[str]] = {}
    family_index: dict[str, list[str]] = {}
    for entry in entries:
        family = str(entry["family"]).strip()
        canonical_term = str(entry["canonical_term"]).strip()
        family_index.setdefault(family, []).append(canonical_term)
        for alias in entry["aliases"]:
            alias_index.setdefault(alias, []).append(f"{family}:{canonical_term}")
        for alias in entry["deprecated_aliases"]:
            deprecated_alias_index.setdefault(alias, []).append(f"{family}:{canonical_term}")

    contexts = SPECGRAPH_VOCABULARY.get("contexts", {})
    context_entries = []
    for context_name, context in sorted(contexts.items()):
        if not isinstance(context, dict):
            continue
        context_entries.append(
            {
                "context": context_name,
                "description": str(context.get("description", "")).strip(),
                "owner_specs": sorted(
                    {
                        str(spec_id).strip()
                        for spec_id in context.get("owner_specs", [])
                        if str(spec_id).strip()
                    }
                ),
                "owner_artifacts": sorted(
                    {
                        str(path).strip()
                        for path in context.get("owner_artifacts", [])
                        if str(path).strip()
                    }
                ),
            }
        )

    return {
        "artifact_kind": "specgraph_vocabulary_index",
        "schema_version": 1,
        "generated_at": utc_now_iso(),
        "vocabulary_reference": specgraph_vocabulary_reference(),
        "context_count": len(context_entries),
        "contexts": context_entries,
        "family_count": len(family_index),
        "term_count": len(entries),
        "entries": entries,
        "family_index": {family: sorted(values) for family, values in sorted(family_index.items())},
        "alias_index": {alias: sorted(values) for alias, values in sorted(alias_index.items())},
        "deprecated_alias_index": {
            alias: sorted(values) for alias, values in sorted(deprecated_alias_index.items())
        },
    }


def write_vocabulary_index(index: dict[str, Any]) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = vocabulary_index_path()
    with artifact_lock(path):
        atomic_write_json(path, index)
    return path


def _vocabulary_surface_contracts(specs: list[SpecNode]) -> list[dict[str, Any]]:
    surfaces: list[dict[str, Any]] = [
        {
            "surface_kind": "policy_contract",
            "surface_id": INTENT_LAYER_POLICY_RELATIVE_PATH,
            "family": "runtime_artifact_kind",
            "terms": [
                INTENT_LAYER_NODE_ARTIFACT_KIND,
                INTENT_LAYER_OVERLAY_ARTIFACT_KIND,
            ],
        },
        {
            "surface_kind": "policy_contract",
            "surface_id": INTENT_LAYER_POLICY_RELATIVE_PATH,
            "family": "pre_spec_artifact_class",
            "terms": sorted(INTENT_LAYER_ALLOWED_KINDS),
        },
        {
            "surface_kind": "policy_contract",
            "surface_id": INTENT_LAYER_POLICY_RELATIVE_PATH,
            "family": "pre_spec_lifecycle_state",
            "terms": sorted(INTENT_LAYER_ALLOWED_STATES),
        },
        {
            "surface_kind": "policy_contract",
            "surface_id": OPERATOR_REQUEST_BRIDGE_POLICY_RELATIVE_PATH,
            "family": "runtime_artifact_kind",
            "terms": [OPERATOR_REQUEST_PACKET_ARTIFACT_KIND],
        },
        {
            "surface_kind": "policy_contract",
            "surface_id": OPERATOR_REQUEST_BRIDGE_POLICY_RELATIVE_PATH,
            "family": "operator_request_source_kind",
            "terms": sorted(OPERATOR_REQUEST_SOURCE_KINDS),
        },
        {
            "surface_kind": "policy_contract",
            "surface_id": OPERATOR_REQUEST_BRIDGE_POLICY_RELATIVE_PATH,
            "family": "operator_request_run_mode",
            "terms": sorted(OPERATOR_REQUEST_RUN_MODES),
        },
        {
            "surface_kind": "policy_contract",
            "surface_id": OPERATOR_REQUEST_BRIDGE_POLICY_RELATIVE_PATH,
            "family": "operator_request_stop_condition",
            "terms": sorted(set(OPERATOR_REQUEST_ALLOWED_STOP_CONDITIONS)),
        },
        {
            "surface_kind": "policy_contract",
            "surface_id": PROPOSAL_LANE_POLICY_RELATIVE_PATH,
            "family": "runtime_artifact_kind",
            "terms": [
                PROPOSAL_LANE_NODE_ARTIFACT_KIND,
                PROPOSAL_LANE_OVERLAY_ARTIFACT_KIND,
            ],
        },
        {
            "surface_kind": "policy_contract",
            "surface_id": PROPOSAL_LANE_POLICY_RELATIVE_PATH,
            "family": "proposal_authority_state",
            "allow_deprecated_aliases": True,
            "terms": sorted(
                {
                    str(term).strip()
                    for term in (
                        list(PROPOSAL_LANE_AUTHORITY_STATE_MAPPING.keys())
                        + list(PROPOSAL_LANE_AUTHORITY_STATE_MAPPING.values())
                    )
                    if str(term).strip()
                }
            ),
        },
        {
            "surface_kind": "policy_contract",
            "surface_id": PROPOSAL_PROMOTION_POLICY_RELATIVE_PATH,
            "family": "proposal_artifact_class",
            "terms": sorted(
                {
                    str(term).strip()
                    for term in load_proposal_promotion_policy_report()[0]
                    .get("semantic_artifact_classes", {})
                    .keys()
                    if str(term).strip()
                }
            )
            if load_proposal_promotion_policy_report()[0]
            else [],
        },
        {
            "surface_kind": "policy_contract",
            "surface_id": PRE_SPEC_SEMANTICS_POLICY_RELATIVE_PATH,
            "family": "runtime_artifact_kind",
            "terms": [PRE_SPEC_SEMANTICS_INDEX_ARTIFACT_KIND],
        },
        {
            "surface_kind": "policy_contract",
            "surface_id": PRE_SPEC_SEMANTICS_POLICY_RELATIVE_PATH,
            "family": "pre_spec_artifact_class",
            "terms": sorted(PRE_SPEC_IMPLEMENTED_ARTIFACT_CLASSES.keys()),
        },
        {
            "surface_kind": "canonical_spec_terminology",
            "surface_id": "canonical_spec_terminology",
            "family": "",
            "terms": [],
        },
    ]
    for spec in specs:
        terminology = spec.data.get("specification", {}).get("terminology", {})
        if not isinstance(terminology, dict):
            continue
        for term in sorted(str(key).strip() for key in terminology.keys() if str(key).strip()):
            resolution = vocabulary_term_resolution(term)
            surfaces.append(
                {
                    "surface_kind": "canonical_spec_terminology",
                    "surface_id": display_artifact_path(spec.path),
                    "spec_id": spec.id,
                    "family": str((resolution or {}).get("family", "")).strip(),
                    "terms": [term],
                }
            )
    return surfaces


def build_vocabulary_drift_report(specs: list[SpecNode]) -> dict[str, Any]:
    index = build_vocabulary_index()
    alias_index = index.get("alias_index", {})
    deprecated_alias_index = index.get("deprecated_alias_index", {})
    findings: list[dict[str, str]] = []

    for alias, resolutions in alias_index.items():
        if len(resolutions) > 1:
            findings.append(
                {
                    "code": "alias_collision",
                    "severity": "error",
                    "surface_kind": "vocabulary_artifact",
                    "surface_id": SPECGRAPH_VOCABULARY_RELATIVE_PATH,
                    "term": alias,
                    "message": (
                        "Alias resolves to multiple canonical terms: "
                        + ", ".join(sorted(resolutions))
                    ),
                }
            )
    for alias, resolutions in deprecated_alias_index.items():
        if len(resolutions) > 1:
            findings.append(
                {
                    "code": "deprecated_alias_collision",
                    "severity": "error",
                    "surface_kind": "vocabulary_artifact",
                    "surface_id": SPECGRAPH_VOCABULARY_RELATIVE_PATH,
                    "term": alias,
                    "message": (
                        "Deprecated alias resolves to multiple canonical terms: "
                        + ", ".join(sorted(resolutions))
                    ),
                }
            )

    for surface in _vocabulary_surface_contracts(specs):
        family = str(surface.get("family", "")).strip()
        surface_kind = str(surface.get("surface_kind", "")).strip()
        surface_id = str(surface.get("surface_id", "")).strip()
        spec_id = str(surface.get("spec_id", "")).strip()
        allow_deprecated_aliases = bool(surface.get("allow_deprecated_aliases"))
        for term in surface.get("terms", []):
            normalized_term = str(term).strip()
            if not normalized_term:
                continue
            resolution = vocabulary_term_resolution(normalized_term, family=family or None)
            if resolution is None:
                findings.append(
                    {
                        "code": "undefined_term",
                        "severity": "error",
                        "surface_kind": surface_kind,
                        "surface_id": surface_id,
                        "term": normalized_term,
                        "family": family,
                        "message": (
                            f"Term `{normalized_term}` is not defined in the shared vocabulary"
                            + (f" for family `{family}`." if family else ".")
                        ),
                    }
                )
                continue
            if resolution["resolution_kind"] == "deprecated_alias" and not allow_deprecated_aliases:
                findings.append(
                    {
                        "code": "deprecated_alias_usage",
                        "severity": "warning",
                        "surface_kind": surface_kind,
                        "surface_id": surface_id,
                        "term": normalized_term,
                        "family": resolution["family"],
                        "message": (
                            f"Surface still uses deprecated alias `{normalized_term}` for "
                            f"`{resolution['canonical_term']}`."
                        ),
                    }
                )
            if surface_kind == "canonical_spec_terminology":
                matching_entries = [
                    entry
                    for entry in index["entries"]
                    if entry["family"] == resolution["family"]
                    and entry["canonical_term"] == resolution["canonical_term"]
                ]
                owner_specs = set()
                for entry in matching_entries:
                    owner_specs.update(str(item).strip() for item in entry.get("owner_specs", []))
                if owner_specs and spec_id and spec_id not in owner_specs:
                    findings.append(
                        {
                            "code": "meaning_divergence",
                            "severity": "warning",
                            "surface_kind": surface_kind,
                            "surface_id": surface_id,
                            "term": normalized_term,
                            "family": resolution["family"],
                            "message": (
                                f"Canonical spec {spec_id} defines shared term `{normalized_term}` "
                                f"outside its owning spec set: {', '.join(sorted(owner_specs))}."
                            ),
                        }
                    )

    findings_by_code: dict[str, list[str]] = {}
    for finding in findings:
        findings_by_code.setdefault(str(finding["code"]), []).append(
            str(finding.get("surface_id", "")).strip() or str(finding.get("term", "")).strip()
        )

    return {
        "artifact_kind": "vocabulary_drift_report",
        "schema_version": 1,
        "generated_at": utc_now_iso(),
        "vocabulary_reference": specgraph_vocabulary_reference(),
        "source_spec_count": len(specs),
        "finding_count": len(findings),
        "findings": findings,
        "findings_by_code": {
            code: sorted(set(values)) for code, values in sorted(findings_by_code.items())
        },
    }


def write_vocabulary_drift_report(report: dict[str, Any]) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = vocabulary_drift_report_path()
    with artifact_lock(path):
        atomic_write_json(path, report)
    return path


def refresh_vocabulary_artifacts(specs: list[SpecNode]) -> dict[str, Path]:
    index_path = write_vocabulary_index(build_vocabulary_index())
    drift_path = write_vocabulary_drift_report(build_vocabulary_drift_report(specs))
    return {
        "vocabulary_index": index_path,
        "vocabulary_drift_report": drift_path,
    }


def refresh_pre_spec_semantics_artifacts(specs: list[SpecNode]) -> dict[str, Path]:
    overlay_path = write_intent_layer_overlay(build_intent_layer_overlay())
    pre_spec_index = write_pre_spec_semantics_index(build_pre_spec_semantics_index(specs))
    return {
        "intent_layer_overlay": overlay_path,
        "pre_spec_semantics_index": pre_spec_index,
    }


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
    operator_request_context: dict[str, Any] | None = None,
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
                "user_intent_handle": str(
                    (operator_request_context or {}).get("user_intent_handle", "")
                ).strip(),
                "operator_request_handle": str(
                    (operator_request_context or {}).get("operator_request_handle", "")
                ).strip(),
                **handoff_metadata_for_signal(signal_name),
            }
        )
    return items


def update_proposal_queue(
    *,
    graph_health: dict[str, Any],
    run_id: str,
    operator_request_context: dict[str, Any] | None = None,
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
        updated = preserved + build_proposal_queue_items(
            graph_health=graph_health,
            run_id=run_id,
            operator_request_context=operator_request_context,
        )
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
    validator_results: dict[str, bool] | None,
    graph_health: dict[str, Any],
    graph_health_truth_basis: str,
    proposal_queue_before: list[dict[str, Any]] | None,
    proposal_queue_after: list[dict[str, Any]] | None,
    refactor_queue_before: list[dict[str, Any]] | None,
    refactor_queue_after: list[dict[str, Any]] | None,
    refinement_acceptance: dict[str, Any] | None = None,
    validation_errors: list[str] | None = None,
    validation_findings: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    normalized_validation_findings = coerce_validation_findings(validation_findings)
    if not normalized_validation_findings and validation_errors:
        normalized_validation_findings = string_errors_to_validation_findings(
            validation_errors,
            family="artifact",
            error_class="contract_failure",
            code="legacy_validation_error",
            spec_id=spec_id,
        )
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
        "validation_error_count": len(normalized_validation_findings),
        "validation_summary": validation_summary(normalized_validation_findings),
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
            "validation_findings": normalized_validation_findings,
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


def _normalize_packet_string_list(
    *,
    field_name: str,
    value: Any,
) -> tuple[list[str], list[str]]:
    if value in (None, ""):
        return [], []
    raw_items: list[Any]
    if isinstance(value, str):
        raw_items = [item.strip() for item in value.split(",") if item.strip()]
    elif isinstance(value, list):
        raw_items = value
    else:
        return [], [f"{field_name} must be a string or list of strings"]

    normalized: list[str] = []
    errors: list[str] = []
    for idx, item in enumerate(raw_items):
        if not isinstance(item, str) or not item.strip():
            errors.append(f"{field_name}[{idx}] must be a non-empty string")
            continue
        normalized.append(item.strip())
    return normalized, errors


def _normalize_vocabulary_term(
    *,
    field_name: str,
    value: Any,
    family: str,
) -> tuple[str, list[str]]:
    normalized = str(value).strip()
    if not normalized:
        return "", []
    resolution = vocabulary_term_resolution(normalized, family=family)
    if resolution is None:
        return "", [f"{field_name} must use a defined {family} term"]
    return str(resolution["canonical_term"]).strip(), []


def _normalize_vocabulary_term_list(
    *,
    field_name: str,
    value: Any,
    family: str,
    default_terms: tuple[str, ...] = (),
) -> tuple[list[str], list[str]]:
    normalized_items, errors = _normalize_packet_string_list(field_name=field_name, value=value)
    if errors:
        return [], errors
    if not normalized_items:
        normalized_items = list(default_terms)

    normalized_terms: list[str] = []
    for idx, item in enumerate(normalized_items):
        canonical_term, term_errors = _normalize_vocabulary_term(
            field_name=f"{field_name}[{idx}]",
            value=item,
            family=family,
        )
        errors.extend(term_errors)
        if canonical_term:
            normalized_terms.append(canonical_term)
    if errors:
        return [], errors
    return list(dict.fromkeys(normalized_terms)), []


def default_user_intent_handle(source_summary: str) -> str:
    slug = sanitize_for_git(source_summary)[:48]
    return f"user_intent::{slug or 'intent'}"


def default_operator_request_handle(
    *,
    target_spec_id: str,
    run_mode: str,
    source_summary: str,
) -> str:
    target = sanitize_for_git(target_spec_id).upper() if target_spec_id else "UNSCOPED"
    mode = sanitize_for_git(run_mode) or "request"
    summary = sanitize_for_git(source_summary)[:32] or "intent"
    return f"operator_request::{target}::{mode}::{summary}"


def normalize_operator_request_packet(
    path: Path,
    *,
    specs: list[SpecNode],
) -> tuple[dict[str, Any] | None, list[str]]:
    packet, error = load_json_object_report(path, artifact_kind="operator request packet")
    if packet is None:
        return None, [error]

    errors: list[str] = []
    if str(packet.get("artifact_kind", "")).strip() != OPERATOR_REQUEST_PACKET_ARTIFACT_KIND:
        errors.append(
            "operator request packet must declare "
            f"artifact_kind: {OPERATOR_REQUEST_PACKET_ARTIFACT_KIND}"
        )
    raw_schema_version = packet.get("schema_version", 0)
    try:
        schema_version = int(raw_schema_version or 0)
    except (TypeError, ValueError):
        errors.append("operator request packet schema_version must be an integer")
        schema_version = None
    if schema_version is not None and schema_version != OPERATOR_REQUEST_PACKET_SCHEMA_VERSION:
        errors.append(
            "operator request packet must declare "
            f"schema_version: {OPERATOR_REQUEST_PACKET_SCHEMA_VERSION}"
        )

    for section_name in OPERATOR_REQUEST_REQUIRED_TOP_LEVEL_SECTIONS:
        if not isinstance(packet.get(section_name), dict):
            errors.append(f"operator request packet must contain object section: {section_name}")

    user_intent = packet.get("user_intent") if isinstance(packet.get("user_intent"), dict) else {}
    operator_request = (
        packet.get("operator_request") if isinstance(packet.get("operator_request"), dict) else {}
    )

    for field_name in OPERATOR_REQUEST_REQUIRED_USER_INTENT_FIELDS:
        if not str(user_intent.get(field_name, "")).strip():
            errors.append(f"user_intent.{field_name} must be a non-empty string")
    for field_name in OPERATOR_REQUEST_REQUIRED_REQUEST_FIELDS:
        if not str(operator_request.get(field_name, "")).strip():
            errors.append(f"operator_request.{field_name} must be a non-empty string")

    source_kind, source_kind_errors = _normalize_vocabulary_term(
        field_name="user_intent.source_kind",
        value=user_intent.get("source_kind"),
        family="operator_request_source_kind",
    )
    errors.extend(source_kind_errors)
    source_summary = str(user_intent.get("source_summary", "")).strip()
    selected_node_ref = str(user_intent.get("selected_node_ref", "")).strip()
    unresolved_questions, unresolved_question_errors = _normalize_packet_string_list(
        field_name="user_intent.unresolved_questions",
        value=user_intent.get("unresolved_questions"),
    )
    errors.extend(unresolved_question_errors)

    run_mode, run_mode_errors = _normalize_vocabulary_term(
        field_name="operator_request.run_mode",
        value=operator_request.get("run_mode"),
        family="operator_request_run_mode",
    )
    errors.extend(run_mode_errors)
    target_spec_id = str(operator_request.get("target_spec_id", "")).strip()
    if target_spec_id and target_spec_id not in {spec.id for spec in specs}:
        errors.append(f"operator_request.target_spec_id not found: {target_spec_id}")

    operator_note = str(operator_request.get("operator_note", "")).strip()
    mutation_budget_list, mutation_budget_errors = _normalize_packet_string_list(
        field_name="operator_request.mutation_budget",
        value=operator_request.get("mutation_budget"),
    )
    run_authority_list, run_authority_errors = _normalize_packet_string_list(
        field_name="operator_request.run_authority",
        value=operator_request.get("run_authority"),
    )
    errors.extend(mutation_budget_errors)
    errors.extend(run_authority_errors)
    stop_conditions, stop_condition_errors = _normalize_vocabulary_term_list(
        field_name="operator_request.stop_conditions",
        value=operator_request.get("stop_conditions"),
        family="operator_request_stop_condition",
        default_terms=OPERATOR_REQUEST_DEFAULT_STOP_CONDITIONS,
    )
    errors.extend(stop_condition_errors)

    mutation_budget: tuple[str, ...] = ()
    run_authority: tuple[str, ...] = ()
    if not mutation_budget_errors:
        try:
            mutation_budget = parse_mutation_budget(",".join(mutation_budget_list))
        except ValueError as exc:
            errors.append(str(exc))
    if not run_authority_errors:
        try:
            run_authority = parse_run_authority(",".join(run_authority_list))
        except ValueError as exc:
            errors.append(str(exc))

    execution_profile_value = str(operator_request.get("execution_profile", "")).strip()
    execution_profile: str | None = execution_profile_value or None
    if execution_profile is not None:
        try:
            execution_profile = resolve_execution_profile_name(
                requested_profile=execution_profile,
                run_authority=run_authority,
                operator_target=True,
            )
        except ValueError as exc:
            errors.append(str(exc))

    if errors:
        return None, errors

    user_intent_handle = str(user_intent.get("intent_handle", "")).strip() or (
        default_user_intent_handle(source_summary)
    )
    operator_request_handle = str(
        operator_request.get("request_handle", "")
    ).strip() or default_operator_request_handle(
        target_spec_id=target_spec_id,
        run_mode=run_mode,
        source_summary=source_summary,
    )
    packet_reference = display_artifact_path(path)
    execution_contract = {
        "authority": {
            "requested_run_authority": list(run_authority),
            "canonical_write_boundary": "forbidden",
            "allowed_downstream_routes": list(
                operator_request_bridge_policy_lookup("bridge_boundary.allowed_downstream_routes")
            ),
        },
        "mutation_budget": list(mutation_budget),
        "stop_conditions": list(stop_conditions),
        "execution_profile": execution_profile or "",
    }
    return (
        {
            "packet_reference": packet_reference,
            "policy_reference": operator_request_bridge_policy_reference(),
            "user_intent": {
                "handle": user_intent_handle,
                "source_kind": source_kind,
                "source_summary": source_summary,
                "selected_node_ref": selected_node_ref,
                "unresolved_questions": unresolved_questions,
            },
            "operator_request": {
                "handle": operator_request_handle,
                "target_spec_id": target_spec_id,
                "run_mode": run_mode,
                "operator_note": operator_note,
                "mutation_budget": mutation_budget,
                "run_authority": run_authority,
                "stop_conditions": tuple(stop_conditions),
                "execution_profile": execution_profile,
                "execution_contract": execution_contract,
            },
        },
        [],
    )


def sync_user_intent_node(context: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    user_intent = context["user_intent"]
    handle_value = str(user_intent["handle"]).strip()
    path = intent_layer_node_path(handle_value)
    tracked_path = path.relative_to(ROOT).as_posix()
    existing = load_json_object(path) if path.exists() else None
    created_at = str((existing or {}).get("created_at", "")).strip() or utc_now_iso()
    packet_reference = str(context.get("packet_reference", "")).strip()
    node = dict(existing or {})
    user_intent_status = (
        "mediated"
        if str(user_intent.get("source_kind", "")).strip() == "mediated_artifact"
        else "captured"
    )
    user_intent_authority = (
        "mediator"
        if str(user_intent.get("source_kind", "")).strip() == "mediated_artifact"
        else "external_actor"
    )
    node.update(
        {
            "artifact_kind": INTENT_LAYER_NODE_ARTIFACT_KIND,
            "schema_version": INTENT_LAYER_NODE_SCHEMA_VERSION,
            "title": f"User intent: {str(user_intent.get('source_summary', '')).strip()}",
            "created_at": created_at,
            "updated_at": utc_now_iso(),
            "policy_reference": intent_layer_policy_reference(),
            "vocabulary_reference": specgraph_vocabulary_reference(),
            "intent_repository_presence": {
                **copy.deepcopy(INTENT_LAYER_PRESENCE_CONTRACT),
                "tracked_path": tracked_path,
            },
            "intent_handle": {
                "handle_value": handle_value,
                "handle_status": "active",
            },
            "intent_layer_kind": "user_intent",
            "mediation_state": user_intent_status,
            "pre_spec_semantics": {
                "policy_reference": pre_spec_semantics_policy_reference(),
                "phase": PRE_SPEC_SEMANTICS_PHASE,
                "semantic_artifact_class": "user_intent",
                "status": user_intent_status,
                "authority": user_intent_authority,
                "required_axes": list(PRE_SPEC_REQUIRED_AXES),
                "implemented_axes": pre_spec_semantics_policy_lookup(
                    "axes_contract.implemented_axes"
                ),
                "adjacent_primary_kinds": list(
                    PRE_SPEC_IMPLEMENTED_ARTIFACT_CLASSES["user_intent"]["adjacent_primary_kinds"]
                ),
                "canonical_boundary": str(
                    pre_spec_semantics_policy_lookup("semantic_boundary.canonical_boundary")
                ),
            },
            "intent_capture": {
                "source_kind": str(user_intent.get("source_kind", "")).strip(),
                "source_summary": str(user_intent.get("source_summary", "")).strip(),
                "selected_node_ref": str(user_intent.get("selected_node_ref", "")).strip(),
                "unresolved_questions": list(user_intent.get("unresolved_questions", [])),
            },
            "intent_lineage_link": [
                {
                    "lineage_role": "captured_from",
                    "source_kind": "runtime_artifact",
                    "source_reference": packet_reference,
                }
            ],
            "runtime_bridge": {
                "latest_operator_request_handle": str(
                    context.get("operator_request", {}).get("handle", "")
                ).strip(),
                "latest_packet_reference": packet_reference,
            },
        }
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with artifact_lock(path):
        atomic_write_json(path, node)
    return path, node


def sync_operator_request_node(
    context: dict[str, Any],
    *,
    user_intent_handle: str,
) -> tuple[Path, dict[str, Any]]:
    request = context["operator_request"]
    handle_value = str(request["handle"]).strip()
    path = intent_layer_node_path(handle_value)
    tracked_path = path.relative_to(ROOT).as_posix()
    existing = load_json_object(path) if path.exists() else None
    created_at = str((existing or {}).get("created_at", "")).strip() or utc_now_iso()
    packet_reference = str(context.get("packet_reference", "")).strip()
    node = dict(existing or {})
    node.update(
        {
            "artifact_kind": INTENT_LAYER_NODE_ARTIFACT_KIND,
            "schema_version": INTENT_LAYER_NODE_SCHEMA_VERSION,
            "title": (
                "Operator request for "
                f"{str(request.get('target_spec_id', '')).strip() or 'unscoped target'}"
            ),
            "created_at": created_at,
            "updated_at": utc_now_iso(),
            "policy_reference": intent_layer_policy_reference(),
            "bridge_policy_reference": operator_request_bridge_policy_reference(),
            "vocabulary_reference": specgraph_vocabulary_reference(),
            "intent_repository_presence": {
                **copy.deepcopy(INTENT_LAYER_PRESENCE_CONTRACT),
                "tracked_path": tracked_path,
            },
            "intent_handle": {
                "handle_value": handle_value,
                "handle_status": "active",
            },
            "intent_layer_kind": "operator_request",
            "mediation_state": "ready_for_execution",
            "pre_spec_semantics": {
                "policy_reference": pre_spec_semantics_policy_reference(),
                "phase": PRE_SPEC_SEMANTICS_PHASE,
                "semantic_artifact_class": "operator_request",
                "status": "ready_for_execution",
                "authority": "operator",
                "required_axes": list(PRE_SPEC_REQUIRED_AXES),
                "implemented_axes": pre_spec_semantics_policy_lookup(
                    "axes_contract.implemented_axes"
                ),
                "adjacent_primary_kinds": list(
                    PRE_SPEC_IMPLEMENTED_ARTIFACT_CLASSES["operator_request"][
                        "adjacent_primary_kinds"
                    ]
                ),
                "canonical_boundary": str(
                    pre_spec_semantics_policy_lookup("semantic_boundary.canonical_boundary")
                ),
            },
            "request_bridge": {
                "target_spec_id": str(request.get("target_spec_id", "")).strip(),
                "run_mode": str(request.get("run_mode", "")).strip(),
                "operator_note": str(request.get("operator_note", "")).strip(),
                "mutation_budget": list(request.get("mutation_budget", ())),
                "run_authority": list(request.get("run_authority", ())),
                "stop_conditions": list(request.get("stop_conditions", ())),
                "execution_profile": str(request.get("execution_profile", "") or "").strip(),
                "execution_contract": copy.deepcopy(request.get("execution_contract", {})),
            },
            "intent_lineage_link": [
                {
                    "lineage_role": "derived_from",
                    "source_kind": "intent_layer_node",
                    "source_reference": user_intent_handle,
                },
                {
                    "lineage_role": "normalized_from",
                    "source_kind": "runtime_artifact",
                    "source_reference": packet_reference,
                },
            ],
            "runtime_bridge": {
                "latest_packet_reference": packet_reference,
                "bridge_state": "ready_for_execution",
            },
        }
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with artifact_lock(path):
        atomic_write_json(path, node)
    return path, node


def sync_intent_layer_from_operator_request(context: dict[str, Any]) -> dict[str, Any]:
    user_intent_path, user_intent_node = sync_user_intent_node(context)
    user_intent_handle = str(
        user_intent_node.get("intent_handle", {}).get("handle_value", "")
    ).strip()
    operator_request_path, operator_request_node = sync_operator_request_node(
        context,
        user_intent_handle=user_intent_handle,
    )
    specs = load_specs()
    refresh_vocabulary_artifacts(specs)
    refresh_pre_spec_semantics_artifacts(specs)
    return {
        "user_intent_path": user_intent_path.relative_to(ROOT).as_posix(),
        "user_intent_handle": str(
            user_intent_node.get("intent_handle", {}).get("handle_value", "")
        ).strip(),
        "operator_request_path": operator_request_path.relative_to(ROOT).as_posix(),
        "operator_request_handle": str(
            operator_request_node.get("intent_handle", {}).get("handle_value", "")
        ).strip(),
    }


def build_last_pre_spec_provenance(
    *,
    operator_request_context: dict[str, Any] | None,
    proposal_ids: list[str] | None = None,
) -> dict[str, Any] | None:
    if not operator_request_context:
        return None
    user_intent_handle = str(operator_request_context.get("user_intent_handle", "")).strip()
    operator_request_handle = str(
        operator_request_context.get("operator_request_handle", "")
    ).strip()
    packet_reference = str(operator_request_context.get("packet_reference", "")).strip()
    if not any((user_intent_handle, operator_request_handle, packet_reference)):
        return None
    return {
        "policy_reference": pre_spec_semantics_policy_reference(),
        "vocabulary_reference": specgraph_vocabulary_reference(),
        "packet_reference": packet_reference,
        "user_intent_handle": user_intent_handle,
        "operator_request_handle": operator_request_handle,
        "proposal_ids": sorted(
            {str(item).strip() for item in (proposal_ids or []) if str(item).strip()}
        ),
        "recorded_at": utc_now_iso(),
    }


def record_operator_request_execution(
    *,
    operator_request_context: dict[str, Any] | None,
    run_id: str,
    spec_id: str,
    outcome: str,
    gate_state: str,
    proposal_items: list[dict[str, Any]] | None = None,
) -> None:
    if not operator_request_context:
        return

    operator_request_handle = str(
        operator_request_context.get("operator_request_handle", "")
    ).strip()
    user_intent_handle = str(operator_request_context.get("user_intent_handle", "")).strip()
    if not operator_request_handle:
        return

    proposal_ids = sorted(
        {
            str(item.get("id", "")).strip()
            for item in (proposal_items or [])
            if isinstance(item, dict)
            and str(item.get("spec_id", "")).strip() == spec_id
            and str(item.get("operator_request_handle", "")).strip() == operator_request_handle
            and str(item.get("id", "")).strip()
        }
    )
    if proposal_ids:
        mediation_state = "proposal_linked"
        downstream_route = "proposal_lane_emission"
        canonical_spec_ids: list[str] = []
    elif str(gate_state).strip() == "blocked" or str(outcome).strip() == "blocked":
        mediation_state = "blocked"
        downstream_route = "execution_blocked"
        canonical_spec_ids = []
    else:
        mediation_state = "canonical_candidate"
        downstream_route = "supervisor_refinement_candidate"
        canonical_spec_ids = [spec_id]

    operator_request_path = intent_layer_node_path(operator_request_handle)
    operator_request_node = load_json_object(operator_request_path)
    if isinstance(operator_request_node, dict):
        runtime_bridge = dict(operator_request_node.get("runtime_bridge", {}))
        runtime_bridge.update(
            {
                "bridge_state": mediation_state,
                "last_executed_run_id": run_id,
                "last_executed_at": utc_now_iso(),
                "last_outcome": outcome,
                "last_gate_state": gate_state,
                "proposal_ids": proposal_ids,
                "canonical_spec_ids": canonical_spec_ids,
                "downstream_route": downstream_route,
            }
        )
        operator_request_node["mediation_state"] = mediation_state
        if isinstance(operator_request_node.get("pre_spec_semantics"), dict):
            operator_request_node["pre_spec_semantics"]["status"] = mediation_state
        operator_request_node["runtime_bridge"] = runtime_bridge
        operator_request_node["updated_at"] = utc_now_iso()
        with artifact_lock(operator_request_path):
            atomic_write_json(operator_request_path, operator_request_node)

    if user_intent_handle:
        user_intent_path = intent_layer_node_path(user_intent_handle)
        user_intent_node = load_json_object(user_intent_path)
        if isinstance(user_intent_node, dict):
            runtime_bridge = dict(user_intent_node.get("runtime_bridge", {}))
            runtime_bridge.update(
                {
                    "latest_operator_request_handle": operator_request_handle,
                    "latest_run_id": run_id,
                    "latest_outcome": outcome,
                    "latest_gate_state": gate_state,
                    "latest_proposal_ids": proposal_ids,
                    "latest_canonical_spec_ids": canonical_spec_ids,
                    "latest_downstream_route": downstream_route,
                }
            )
            user_intent_node["runtime_bridge"] = runtime_bridge
            user_intent_node["updated_at"] = utc_now_iso()
            with artifact_lock(user_intent_path):
                atomic_write_json(user_intent_path, user_intent_node)

    specs = load_specs()
    refresh_vocabulary_artifacts(specs)
    refresh_pre_spec_semantics_artifacts(specs)


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
    user_intent_handle = str(proposal_item.get("user_intent_handle", "")).strip()
    if user_intent_handle:
        lineage_links.append(
            {
                "lineage_role": "motivated_by",
                "source_kind": "intent_layer_node",
                "source_reference": user_intent_handle,
            }
        )
    operator_request_handle = str(proposal_item.get("operator_request_handle", "")).strip()
    if operator_request_handle:
        lineage_links.append(
            {
                "lineage_role": "derived_from",
                "source_kind": "intent_layer_node",
                "source_reference": operator_request_handle,
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
                "user_intent_handle": str(proposal_item.get("user_intent_handle", "")).strip(),
                "operator_request_handle": str(
                    proposal_item.get("operator_request_handle", "")
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
                "operator_request_handle": str(
                    proposal_item.get("operator_request_handle", "")
                ).strip(),
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


def load_intent_layer_nodes_report() -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    nodes_dir = intent_layer_nodes_dir_path()
    raw_nodes: list[dict[str, Any]] = []
    artifact_warnings: list[dict[str, str]] = []
    if not nodes_dir.exists():
        return raw_nodes, artifact_warnings
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
    return raw_nodes, artifact_warnings


def load_proposal_lane_nodes_report() -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    nodes_dir = proposal_lane_nodes_dir_path()
    raw_nodes: list[dict[str, Any]] = []
    artifact_warnings: list[dict[str, str]] = []
    if not nodes_dir.exists():
        return raw_nodes, artifact_warnings
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
    return raw_nodes, artifact_warnings


def build_pre_spec_semantics_index(specs: list[SpecNode]) -> dict[str, Any]:
    raw_intent_nodes, intent_warnings = load_intent_layer_nodes_report()
    raw_proposal_nodes, proposal_warnings = load_proposal_lane_nodes_report()
    entries: list[dict[str, Any]] = []
    edges: list[dict[str, str]] = []
    named_filters = {name: [] for name in PRE_SPEC_SEMANTICS_NAMED_FILTERS}

    proposal_links_by_handle: dict[str, set[str]] = {}
    for raw in raw_proposal_nodes:
        node = raw["node"]
        proposal_handle = str(node.get("proposal_handle", {}).get("handle_value", "")).strip()
        for link in (
            node.get("proposal_lineage_link", [])
            if isinstance(node.get("proposal_lineage_link", []), list)
            else []
        ):
            if not isinstance(link, dict):
                continue
            if str(link.get("source_kind", "")).strip() != "intent_layer_node":
                continue
            handle = str(link.get("source_reference", "")).strip()
            if handle and proposal_handle:
                proposal_links_by_handle.setdefault(handle, set()).add(proposal_handle)

    canonical_links_by_handle: dict[str, set[str]] = {}
    for spec in specs:
        provenance = spec.data.get("last_pre_spec_provenance", {})
        if not isinstance(provenance, dict):
            continue
        for handle_field in ("user_intent_handle", "operator_request_handle"):
            handle = str(provenance.get(handle_field, "")).strip()
            if handle:
                canonical_links_by_handle.setdefault(handle, set()).add(spec.id)

    for raw in raw_intent_nodes:
        tracked_path = str(raw["tracked_path"])
        node = raw["node"]
        presence = node.get("intent_repository_presence")
        query_findings: list[str] = []
        if not (
            isinstance(presence, dict)
            and all(
                str(presence.get(key, "")).strip() == str(value)
                for key, value in INTENT_LAYER_PRESENCE_CONTRACT.items()
            )
        ):
            query_findings.append("invalid_presence_contract")
        handle = node.get("intent_handle", {})
        if not isinstance(handle, dict):
            query_findings.append("invalid_intent_handle_section")
            handle = {}
        handle_value = str(handle.get("handle_value", "")).strip()
        intent_kind = str(node.get("intent_layer_kind", "")).strip()
        mediation_state = str(node.get("mediation_state", "")).strip()
        if not handle_value:
            query_findings.append("missing_handle")
        if intent_kind not in PRE_SPEC_IMPLEMENTED_ARTIFACT_CLASSES:
            query_findings.append("unknown_pre_spec_artifact_class")
        if not isinstance(node.get("intent_lineage_link"), list) or not node.get(
            "intent_lineage_link"
        ):
            query_findings.append("missing_provenance")

        runtime_bridge = node.get("runtime_bridge", {})
        if not isinstance(runtime_bridge, dict):
            query_findings.append("invalid_runtime_bridge_section")
            runtime_bridge = {}
        pre_spec_semantics = node.get("pre_spec_semantics", {})
        if not isinstance(pre_spec_semantics, dict):
            query_findings.append("invalid_pre_spec_semantics_section")
            pre_spec_semantics = {}
        linked_proposals = sorted(
            set(
                list(proposal_links_by_handle.get(handle_value, set()))
                + list(
                    str(item).strip()
                    for item in (
                        runtime_bridge.get("proposal_ids", [])
                        if isinstance(runtime_bridge, dict)
                        else []
                    )
                    if str(item).strip()
                )
                + list(
                    str(item).strip()
                    for item in (
                        runtime_bridge.get("latest_proposal_ids", [])
                        if isinstance(runtime_bridge, dict)
                        else []
                    )
                    if str(item).strip()
                )
            )
        )
        linked_specs = sorted(
            set(
                list(canonical_links_by_handle.get(handle_value, set()))
                + list(
                    str(item).strip()
                    for item in (
                        runtime_bridge.get("canonical_spec_ids", [])
                        if isinstance(runtime_bridge, dict)
                        else []
                    )
                    if str(item).strip()
                )
                + list(
                    str(item).strip()
                    for item in (
                        runtime_bridge.get("latest_canonical_spec_ids", [])
                        if isinstance(runtime_bridge, dict)
                        else []
                    )
                    if str(item).strip()
                )
            )
        )
        entry = {
            "tracked_path": tracked_path,
            "title": str(node.get("title", "")).strip(),
            "intent_handle": handle_value,
            "semantic_artifact_class": intent_kind,
            "phase": str(pre_spec_semantics.get("phase", PRE_SPEC_SEMANTICS_PHASE)).strip(),
            "status": str(pre_spec_semantics.get("status", mediation_state)).strip(),
            "authority": str(pre_spec_semantics.get("authority", "")).strip(),
            "mediation_state": mediation_state,
            "required_axes": list(pre_spec_semantics.get("required_axes", PRE_SPEC_REQUIRED_AXES)),
            "downstream_proposal_ids": linked_proposals,
            "downstream_canonical_spec_ids": linked_specs,
            "query_contract": {
                "status": "queryable" if not query_findings else "invalid_pre_spec_state",
                "findings": query_findings,
            },
        }
        entries.append(entry)
        if intent_kind in named_filters:
            named_filters[intent_kind].append(handle_value or tracked_path)
        if mediation_state == "proposal_linked" or linked_proposals:
            named_filters["proposal_linked"].append(handle_value or tracked_path)
        if mediation_state == "canonical_candidate":
            named_filters["canonical_candidate"].append(handle_value or tracked_path)
        if linked_specs:
            named_filters["canonical_materialized"].append(handle_value or tracked_path)
        if mediation_state == "blocked":
            named_filters["blocked"].append(handle_value or tracked_path)
        if "missing_provenance" in query_findings:
            named_filters["missing_provenance"].append(handle_value or tracked_path)
        for proposal_id in linked_proposals:
            edges.append(
                {
                    "source": handle_value or tracked_path,
                    "target": proposal_id,
                    "edge_kind": "pre_spec::proposal_lane",
                }
            )
        for spec_id in linked_specs:
            edges.append(
                {
                    "source": handle_value or tracked_path,
                    "target": spec_id,
                    "edge_kind": "pre_spec::canonical_spec",
                }
            )

    return {
        "artifact_kind": PRE_SPEC_SEMANTICS_INDEX_ARTIFACT_KIND,
        "schema_version": PRE_SPEC_SEMANTICS_INDEX_SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "policy_reference": pre_spec_semantics_policy_reference(),
        "vocabulary_reference": specgraph_vocabulary_reference(),
        "layer_name": PRE_SPEC_SEMANTICS_LAYER_NAME,
        "source_dir": INTENT_LAYER_NODES_RELATIVE_DIR,
        "entry_count": len(entries),
        "entries": entries,
        "edges": edges,
        "named_filters": {key: sorted(set(value)) for key, value in sorted(named_filters.items())},
        "artifact_warnings": intent_warnings + proposal_warnings,
        "reserved_primary_kinds": PRE_SPEC_RESERVED_PRIMARY_KINDS,
    }


def write_pre_spec_semantics_index(index: dict[str, Any]) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = pre_spec_semantics_index_path()
    with artifact_lock(path):
        atomic_write_json(path, index)
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


def runtime_evidence_registry_path() -> Path:
    return ROOT / "tools" / "runtime_evidence_registry.json"


def external_consumer_index_path() -> Path:
    return RUNS_DIR / EXTERNAL_CONSUMER_INDEX_FILENAME


def external_consumer_overlay_path() -> Path:
    return RUNS_DIR / EXTERNAL_CONSUMER_OVERLAY_FILENAME


def external_consumer_handoff_packets_path() -> Path:
    return RUNS_DIR / EXTERNAL_CONSUMER_HANDOFF_FILENAME


def specpm_export_preview_path() -> Path:
    return RUNS_DIR / SPECPM_EXPORT_PREVIEW_FILENAME


def specpm_handoff_packets_path() -> Path:
    return RUNS_DIR / SPECPM_HANDOFF_FILENAME


def specpm_materialization_report_path() -> Path:
    return RUNS_DIR / SPECPM_MATERIALIZATION_REPORT_FILENAME


def specpm_import_preview_path() -> Path:
    return RUNS_DIR / SPECPM_IMPORT_PREVIEW_FILENAME


def evidence_plane_index_path() -> Path:
    return RUNS_DIR / EVIDENCE_PLANE_INDEX_FILENAME


def evidence_plane_overlay_path() -> Path:
    return RUNS_DIR / EVIDENCE_PLANE_OVERLAY_FILENAME


def metric_signal_index_path() -> Path:
    return RUNS_DIR / METRIC_SIGNAL_INDEX_FILENAME


def metric_threshold_proposals_path() -> Path:
    return RUNS_DIR / METRIC_THRESHOLD_PROPOSALS_FILENAME


def supervisor_performance_index_path() -> Path:
    return RUNS_DIR / SUPERVISOR_PERFORMANCE_INDEX_FILENAME


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


def load_runtime_evidence_registry() -> dict[str, dict[str, Any]]:
    path = runtime_evidence_registry_path()
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise RuntimeError(
            f"failed to read runtime evidence registry: {path.as_posix()} ({exc})"
        ) from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"malformed runtime evidence registry: {path.as_posix()} ({exc})"
        ) from exc
    if not isinstance(payload, list):
        raise RuntimeError(
            f"malformed runtime evidence registry: {path.as_posix()} must contain a JSON list"
        )

    registry: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, dict):
            raise RuntimeError(
                "malformed runtime evidence registry: "
                f"entry {index} in {path.as_posix()} must be an object"
            )
        spec_id = str(item.get("spec_id", "")).strip()
        if not spec_id:
            raise RuntimeError(
                "malformed runtime evidence registry: "
                f"entry {index} in {path.as_posix()} missing spec_id"
            )
        registry[spec_id] = item
    return registry


def load_external_consumers_registry() -> dict[str, Any]:
    path = external_consumers_registry_path()
    if not path.exists():
        return {
            "artifact_kind": "external_consumer_registry",
            "version": 1,
            "consumers": [],
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise RuntimeError(
            f"failed to read external consumer registry: {path.as_posix()} ({exc})"
        ) from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"malformed external consumer registry: {path.as_posix()} ({exc})"
        ) from exc
    if not isinstance(payload, dict):
        raise RuntimeError(
            f"malformed external consumer registry: {path.as_posix()} must contain a JSON object"
        )
    raw_consumers = payload.get("consumers", [])
    if not isinstance(raw_consumers, list):
        raise RuntimeError(
            f"malformed external consumer registry: {path.as_posix()} consumers must be a JSON list"
        )
    for index, item in enumerate(raw_consumers, start=1):
        if not isinstance(item, dict):
            raise RuntimeError(
                "malformed external consumer registry: "
                f"entry {index} in {path.as_posix()} must be an object"
            )
        consumer_id = str(item.get("consumer_id", "")).strip()
        if not consumer_id:
            raise RuntimeError(
                "malformed external consumer registry: "
                f"entry {index} in {path.as_posix()} missing consumer_id"
            )
    return payload


def load_specpm_export_registry() -> dict[str, Any]:
    path = specpm_export_registry_path()
    if not path.exists():
        return {
            "artifact_kind": "specpm_export_registry",
            "version": 1,
            "entries": [],
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise RuntimeError(
            f"failed to read SpecPM export registry: {path.as_posix()} ({exc})"
        ) from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"malformed SpecPM export registry: {path.as_posix()} ({exc})") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(
            f"malformed SpecPM export registry: {path.as_posix()} must contain a JSON object"
        )
    raw_entries = payload.get("entries", [])
    if not isinstance(raw_entries, list):
        raise RuntimeError(
            f"malformed SpecPM export registry: {path.as_posix()} entries must be a JSON list"
        )
    for index, item in enumerate(raw_entries, start=1):
        if not isinstance(item, dict):
            raise RuntimeError(
                "malformed SpecPM export registry: "
                f"entry {index} in {path.as_posix()} must be an object"
            )
        export_id = str(item.get("export_id", "")).strip()
        if not export_id:
            raise RuntimeError(
                "malformed SpecPM export registry: "
                f"entry {index} in {path.as_posix()} missing export_id"
            )
    return payload


def normalize_repo_url(url: str) -> str:
    normalized = str(url).strip().rstrip("/")
    if normalized.startswith("git@") and ":" in normalized:
        host_part, repo_part = normalized.split(":", 1)
        normalized = f"{host_part[4:]}/{repo_part}"
    normalized = re.sub(r"^https?://", "", normalized)
    normalized = re.sub(r"^ssh://", "", normalized)
    if normalized.endswith(".git"):
        normalized = normalized[:-4]
    return normalized


def inspect_external_consumer_checkout(checkout_hint: str, repo_url: str) -> dict[str, Any]:
    checkout_text = str(checkout_hint).strip()
    if not checkout_text:
        return {
            "status": "missing",
            "checkout_path": "",
            "is_git_checkout": False,
            "repo_revision": "",
            "remote_url": "",
            "remote_matches": None,
        }
    checkout_path = Path(checkout_text).expanduser()
    if not checkout_path.exists() or not checkout_path.is_dir():
        return {
            "status": "missing",
            "checkout_path": checkout_path.as_posix(),
            "is_git_checkout": False,
            "repo_revision": "",
            "remote_url": "",
            "remote_matches": None,
        }

    is_git_checkout = False
    repo_revision = ""
    remote_url = ""
    remote_matches = None
    if shutil.which("git") is not None:
        probe = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=checkout_path,
            capture_output=True,
            text=True,
            check=False,
        )
        is_git_checkout = probe.returncode == 0 and probe.stdout.strip() == "true"
        if is_git_checkout:
            revision_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=checkout_path,
                capture_output=True,
                text=True,
                check=False,
            )
            if revision_result.returncode == 0:
                repo_revision = revision_result.stdout.strip()
            remote_result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=checkout_path,
                capture_output=True,
                text=True,
                check=False,
            )
            if remote_result.returncode == 0:
                remote_url = remote_result.stdout.strip()
            if remote_url and repo_url:
                remote_matches = normalize_repo_url(remote_url) == normalize_repo_url(repo_url)

    return {
        "status": "available",
        "checkout_path": checkout_path.as_posix(),
        "is_git_checkout": is_git_checkout,
        "repo_revision": repo_revision,
        "remote_url": remote_url,
        "remote_matches": remote_matches,
    }


def inspect_external_consumer_artifact(
    checkout_path: Path | None,
    artifact_definition: dict[str, Any],
) -> dict[str, Any]:
    artifact_id = str(artifact_definition.get("artifact_id", "")).strip()
    rel_path = str(artifact_definition.get("path", "")).strip()
    required = bool(artifact_definition.get("required", False))
    markers = [
        str(item).strip() for item in artifact_definition.get("markers", []) if str(item).strip()
    ]
    if checkout_path is None:
        return {
            "artifact_id": artifact_id,
            "kind": str(artifact_definition.get("kind", "")).strip(),
            "path": rel_path,
            "required": required,
            "status": "unavailable",
            "expected_marker_count": len(markers),
            "matched_marker_count": 0,
            "matched_markers": [],
            "missing_markers": copy.deepcopy(markers),
        }

    abs_path = checkout_path / rel_path
    if not abs_path.exists():
        return {
            "artifact_id": artifact_id,
            "kind": str(artifact_definition.get("kind", "")).strip(),
            "path": rel_path,
            "required": required,
            "status": "missing",
            "expected_marker_count": len(markers),
            "matched_marker_count": 0,
            "matched_markers": [],
            "missing_markers": copy.deepcopy(markers),
        }

    matched_markers: list[str] = []
    missing_markers: list[str] = []
    if markers:
        try:
            text = abs_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            text = ""
        for marker in markers:
            if marker in text:
                matched_markers.append(marker)
            else:
                missing_markers.append(marker)
    status = "verified" if not missing_markers else "marker_mismatch"
    return {
        "artifact_id": artifact_id,
        "kind": str(artifact_definition.get("kind", "")).strip(),
        "path": rel_path,
        "required": required,
        "status": status,
        "expected_marker_count": len(markers),
        "matched_marker_count": len(matched_markers),
        "matched_markers": matched_markers,
        "missing_markers": missing_markers,
    }


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


def declared_evidence_marker_list(entry: dict[str, Any], field: str) -> list[dict[str, Any]]:
    raw_value = entry.get(field, [])
    if not isinstance(raw_value, list):
        return []
    markers: list[dict[str, Any]] = []
    for item in raw_value:
        if not isinstance(item, dict):
            continue
        path = str(item.get("path", "")).strip()
        pattern = str(item.get("pattern", "")).strip()
        if not path or not pattern:
            continue
        markers.append({"path": path, "pattern": pattern})
    return markers


def declared_runtime_entities(entry: dict[str, Any]) -> list[dict[str, Any]]:
    raw_value = entry.get("runtime_entities", [])
    if not isinstance(raw_value, list):
        return []
    entities: list[dict[str, Any]] = []
    for item in raw_value:
        if not isinstance(item, dict):
            continue
        entity_id = str(item.get("entity_id", "")).strip()
        entity_kind = str(item.get("entity_kind", "")).strip()
        if not entity_id or not entity_kind:
            continue
        normalized = {"entity_id": entity_id, "entity_kind": entity_kind}
        label = str(item.get("label", "")).strip()
        if label:
            normalized["label"] = label
        entities.append(normalized)
    return entities


def build_evidence_plane_index(specs: list[SpecNode]) -> dict[str, Any]:
    registry = load_runtime_evidence_registry()
    trace_index = build_spec_trace_index(specs)
    trace_entries = {
        str(entry.get("spec_id", "")).strip(): entry
        for entry in trace_index.get("entries", [])
        if isinstance(entry, dict) and str(entry.get("spec_id", "")).strip()
    }
    known_spec_ids = {spec.id for spec in specs if spec.id}
    entries: list[dict[str, Any]] = []
    for spec in sorted(specs, key=lambda item: item.id):
        registry_entry = registry.get(spec.id)
        artifact_refs = (
            [
                str(item).strip()
                for item in registry_entry.get("artifact_refs", [])
                if str(item).strip()
            ]
            if isinstance(registry_entry, dict)
            else []
        )
        runtime_entities = declared_runtime_entities(registry_entry or {})
        observation_markers = declared_evidence_marker_list(
            registry_entry or {}, "observation_markers"
        )
        outcome_markers = declared_evidence_marker_list(registry_entry or {}, "outcome_markers")
        adoption_markers = declared_evidence_marker_list(registry_entry or {}, "adoption_markers")
        artifact_surface_report = evaluate_declared_paths(artifact_refs)
        trace_entry = trace_entries.get(spec.id)
        artifact_stage = derive_evidence_artifact_stage(
            registry_entry=registry_entry,
            artifact_refs=artifact_refs,
            artifact_surface_report=artifact_surface_report,
            trace_entry=trace_entry,
        )
        observation_coverage = evaluate_evidence_markers(observation_markers)
        outcome_coverage = evaluate_evidence_markers(outcome_markers)
        adoption_coverage = evaluate_evidence_markers(adoption_markers)
        chain_status = derive_evidence_chain_status(
            registry_entry=registry_entry,
            observation_coverage=observation_coverage,
            outcome_coverage=outcome_coverage,
            adoption_coverage=adoption_coverage,
        )
        entries.append(
            {
                "spec_id": spec.id,
                "title": spec.title,
                "evidence_scope": (
                    str(registry_entry.get("evidence_scope", "")).strip()
                    if isinstance(registry_entry, dict)
                    else "untracked"
                ),
                "evidence_contract": {
                    "source": "runtime_evidence_registry" if registry_entry is not None else "none",
                    "policy_reference": evidence_plane_policy_reference(),
                    "registry_path": runtime_evidence_registry_path().relative_to(ROOT).as_posix(),
                    "notes": (
                        str(registry_entry.get("notes", "")).strip()
                        if isinstance(registry_entry, dict)
                        else ""
                    ),
                },
                "artifact_stage": artifact_stage,
                "artifact_refs": artifact_refs,
                "runtime_entities": runtime_entities,
                "observation_coverage": observation_coverage,
                "outcome_coverage": outcome_coverage,
                "adoption_coverage": adoption_coverage,
                "chain_status": chain_status,
                "trace_binding": (
                    {
                        "implementation_state": copy.deepcopy(
                            trace_entry.get("implementation_state", {})
                        ),
                        "freshness": copy.deepcopy(trace_entry.get("freshness", {})),
                        "verification_basis": copy.deepcopy(
                            trace_entry.get("verification_basis", {})
                        ),
                    }
                    if isinstance(trace_entry, dict)
                    else {}
                ),
                "evidence_summary": {
                    "artifact_ref_count": len(artifact_refs),
                    "runtime_entity_count": len(runtime_entities),
                    "observation_source_count": len(observation_markers),
                    "outcome_source_count": len(outcome_markers),
                    "adoption_source_count": len(adoption_markers),
                    "chain_status": chain_status,
                },
            }
        )

    unknown_registry_specs = sorted(set(registry) - known_spec_ids)
    return {
        "artifact_kind": EVIDENCE_PLANE_INDEX_ARTIFACT_KIND,
        "schema_version": EVIDENCE_PLANE_INDEX_SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "layer_name": EVIDENCE_PLANE_LAYER_NAME,
        "policy_reference": evidence_plane_policy_reference(),
        "trace_reference": {
            "artifact_path": spec_trace_index_path().relative_to(ROOT).as_posix(),
            "generated_at": trace_index.get("generated_at"),
        },
        "registry_path": runtime_evidence_registry_path().relative_to(ROOT).as_posix(),
        "semantic_chain": list(EVIDENCE_PLANE_SEMANTIC_CHAIN),
        "entry_count": len(entries),
        "tracked_entry_count": len(registry),
        "entries": entries,
        "unknown_registry_specs": unknown_registry_specs,
        "available_chain_statuses": list(EVIDENCE_PLANE_CHAIN_STATUSES),
    }


def write_evidence_plane_index(index: dict[str, Any]) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = evidence_plane_index_path()
    with artifact_lock(path):
        atomic_write_json(path, index)
    return path


def build_evidence_plane_overlay(index: dict[str, Any]) -> dict[str, Any]:
    entries = list(index.get("entries", []))
    chain_status_groups: dict[str, list[str]] = {}
    artifact_stage_groups: dict[str, list[str]] = {}
    observation_groups: dict[str, list[str]] = {}
    outcome_groups: dict[str, list[str]] = {}
    adoption_groups: dict[str, list[str]] = {}
    named_filters = {name: [] for name in EVIDENCE_PLANE_NAMED_FILTERS}
    backlog_items: list[dict[str, Any]] = []

    for entry in entries:
        spec_id = str(entry.get("spec_id", "")).strip()
        title = str(entry.get("title", "")).strip()
        chain_status = str(entry.get("chain_status", "untracked")).strip() or "untracked"
        artifact_status = (
            str(entry.get("artifact_stage", {}).get("status", "untracked")).strip() or "untracked"
        )
        observation_status = (
            str(entry.get("observation_coverage", {}).get("status", "not_declared")).strip()
            or "not_declared"
        )
        outcome_status = (
            str(entry.get("outcome_coverage", {}).get("status", "not_declared")).strip()
            or "not_declared"
        )
        adoption_status = (
            str(entry.get("adoption_coverage", {}).get("status", "not_declared")).strip()
            or "not_declared"
        )

        chain_status_groups.setdefault(chain_status, []).append(spec_id)
        artifact_stage_groups.setdefault(artifact_status, []).append(spec_id)
        observation_groups.setdefault(observation_status, []).append(spec_id)
        outcome_groups.setdefault(outcome_status, []).append(spec_id)
        adoption_groups.setdefault(adoption_status, []).append(spec_id)

        next_gap = "none"
        if chain_status == "untracked":
            named_filters["missing_evidence_contract"].append(spec_id)
            next_gap = "attach_evidence_contract"
        elif artifact_status in {"missing", "partial"}:
            named_filters["artifact_gap"].append(spec_id)
            next_gap = "align_artifact_surfaces"
        elif observation_status != "covered":
            named_filters["observation_gap"].append(spec_id)
            next_gap = "collect_observation_evidence"
        elif outcome_status != "covered":
            named_filters["outcome_gap"].append(spec_id)
            next_gap = "collect_outcome_evidence"
        elif adoption_status != "covered":
            named_filters["adoption_gap"].append(spec_id)
            next_gap = "collect_adoption_evidence"
        else:
            named_filters["complete_chain"].append(spec_id)

        if next_gap != "none":
            backlog_items.append(
                {
                    "spec_id": spec_id,
                    "title": title,
                    "chain_status": chain_status,
                    "artifact_stage_status": artifact_status,
                    "observation_status": observation_status,
                    "outcome_status": outcome_status,
                    "adoption_status": adoption_status,
                    "next_gap": next_gap,
                }
            )

    grouped_backlog: dict[str, list[str]] = {}
    for item in backlog_items:
        grouped_backlog.setdefault(str(item["next_gap"]), []).append(str(item["spec_id"]))

    return {
        "artifact_kind": EVIDENCE_PLANE_OVERLAY_ARTIFACT_KIND,
        "schema_version": EVIDENCE_PLANE_OVERLAY_SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "layer_name": EVIDENCE_PLANE_LAYER_NAME,
        "policy_reference": evidence_plane_policy_reference(),
        "source_index_path": evidence_plane_index_path().relative_to(ROOT).as_posix(),
        "source_index_generated_at": index.get("generated_at"),
        "entry_count": len(entries),
        "viewer_projection": {
            "chain_status": {
                key: sorted(value) for key, value in sorted(chain_status_groups.items())
            },
            "artifact_stage": {
                key: sorted(value) for key, value in sorted(artifact_stage_groups.items())
            },
            "observation_coverage": {
                key: sorted(value) for key, value in sorted(observation_groups.items())
            },
            "outcome_coverage": {
                key: sorted(value) for key, value in sorted(outcome_groups.items())
            },
            "adoption_coverage": {
                key: sorted(value) for key, value in sorted(adoption_groups.items())
            },
            "named_filters": {
                key: sorted(set(value)) for key, value in sorted(named_filters.items())
            },
        },
        "evidence_backlog": {
            "entry_count": len(backlog_items),
            "items": backlog_items,
            "grouped_by_next_gap": {
                key: sorted(value) for key, value in sorted(grouped_backlog.items())
            },
        },
    }


def write_evidence_plane_overlay(overlay: dict[str, Any]) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = evidence_plane_overlay_path()
    with artifact_lock(path):
        atomic_write_json(path, overlay)
    return path


def build_external_consumer_index() -> dict[str, Any]:
    registry = load_external_consumers_registry()
    consumers = list(registry.get("consumers", []))
    entries: list[dict[str, Any]] = []
    reference_state_groups: dict[str, list[str]] = {}
    contract_status_groups: dict[str, list[str]] = {}
    metric_groups: dict[str, list[str]] = {}
    named_filters = {
        "stable_ready": [],
        "stable_partial": [],
        "draft_visible": [],
        "missing_checkout": [],
        "bridge_bound": [],
    }

    for consumer in consumers:
        if not isinstance(consumer, dict):
            continue
        consumer_id = str(consumer.get("consumer_id", "")).strip()
        if not consumer_id:
            continue
        reference_state = str(consumer.get("reference_state", "")).strip() or "draft_reference"
        repo_url = str(consumer.get("repo_url", "")).strip()
        checkout = inspect_external_consumer_checkout(
            str(consumer.get("local_checkout_hint", "")).strip(),
            repo_url,
        )
        checkout_path_text = str(checkout.get("checkout_path", "")).strip()
        checkout_path = Path(checkout_path_text) if checkout_path_text else None
        if str(checkout.get("status", "")).strip() != "available":
            checkout_path = None

        artifact_reports: list[dict[str, Any]] = []
        artifact_status_counts = {key: 0 for key in registry.get("artifact_statuses", [])}
        for artifact_definition in consumer.get("declared_artifacts", []):
            if not isinstance(artifact_definition, dict):
                continue
            artifact_report = inspect_external_consumer_artifact(checkout_path, artifact_definition)
            artifact_reports.append(artifact_report)
            status = str(artifact_report.get("status", "")).strip()
            artifact_status_counts[status] = artifact_status_counts.get(status, 0) + 1

        if str(checkout.get("status", "")).strip() != "available":
            contract_status = "unavailable"
        else:
            required_reports = [item for item in artifact_reports if item.get("required")]
            if not required_reports:
                contract_status = "ready"
            elif all(
                str(item.get("status", "")).strip() == "verified" for item in required_reports
            ):
                contract_status = "ready"
            else:
                contract_status = "partial"

        metric_bindings = [
            {
                "metric_id": str(item.get("metric_id", "")).strip(),
                "binding_role": str(item.get("binding_role", "")).strip(),
            }
            for item in consumer.get("metric_bindings", [])
            if isinstance(item, dict) and str(item.get("metric_id", "")).strip()
        ]

        entry = {
            "consumer_id": consumer_id,
            "title": str(consumer.get("title", "")).strip(),
            "profile": str(consumer.get("profile", "")).strip(),
            "reference_state": reference_state,
            "repo_url": repo_url,
            "local_checkout": checkout,
            "contract_status": contract_status,
            "declared_artifact_count": len(artifact_reports),
            "artifact_status_counts": {
                key: value
                for key, value in artifact_status_counts.items()
                if value or key in {"verified", "missing", "marker_mismatch", "unavailable"}
            },
            "artifacts": artifact_reports,
            "metric_bindings": metric_bindings,
            "notes": str(consumer.get("notes", "")).strip(),
        }
        entries.append(entry)

        reference_state_groups.setdefault(reference_state, []).append(consumer_id)
        contract_status_groups.setdefault(contract_status, []).append(consumer_id)
        if reference_state == "stable_reference" and contract_status == "ready":
            named_filters["stable_ready"].append(consumer_id)
        if reference_state == "stable_reference" and contract_status == "partial":
            named_filters["stable_partial"].append(consumer_id)
        if (
            reference_state == "draft_reference"
            and str(checkout.get("status", "")).strip() == "available"
        ):
            named_filters["draft_visible"].append(consumer_id)
        if str(checkout.get("status", "")).strip() != "available":
            named_filters["missing_checkout"].append(consumer_id)
        if metric_bindings:
            named_filters["bridge_bound"].append(consumer_id)
        for binding in metric_bindings:
            metric_id = str(binding.get("metric_id", "")).strip()
            if metric_id:
                metric_groups.setdefault(metric_id, []).append(consumer_id)

    for bucket in (reference_state_groups, contract_status_groups, metric_groups, named_filters):
        for key in list(bucket):
            bucket[key] = sorted(set(bucket[key]))

    available_entry_count = sum(
        1
        for entry in entries
        if str(entry.get("local_checkout", {}).get("status", "")).strip() == "available"
    )
    return {
        "artifact_kind": EXTERNAL_CONSUMER_INDEX_ARTIFACT_KIND,
        "schema_version": EXTERNAL_CONSUMER_INDEX_SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "registry_reference": {
            "artifact_path": external_consumers_registry_path().relative_to(ROOT).as_posix(),
            "artifact_kind": (
                str(registry.get("artifact_kind", "")).strip() or "external_consumer_registry"
            ),
            "version": int(registry.get("version", 1) or 1),
        },
        "entry_count": len(entries),
        "available_entry_count": available_entry_count,
        "entries": entries,
        "available_reference_states": list(registry.get("reference_states", [])),
        "available_profiles": list(registry.get("consumer_profiles", [])),
        "viewer_projection": {
            "reference_state": reference_state_groups,
            "contract_status": contract_status_groups,
            "metric_id": metric_groups,
            "named_filters": named_filters,
        },
    }


def write_external_consumer_index(index: dict[str, Any]) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = external_consumer_index_path()
    with artifact_lock(path):
        atomic_write_json(path, index)
    return path


def derive_external_consumer_bridge_state(entry: dict[str, Any]) -> str:
    reference_state = str(entry.get("reference_state", "")).strip() or "draft_reference"
    checkout_status = str(entry.get("local_checkout", {}).get("status", "")).strip() or "missing"
    remote_matches = entry.get("local_checkout", {}).get("remote_matches")
    contract_status = str(entry.get("contract_status", "")).strip() or "unavailable"
    if reference_state == "stable_reference":
        if checkout_status != "available":
            return "stable_checkout_missing"
        if remote_matches is not True:
            return "stable_identity_unverified"
        if contract_status == "ready":
            return "stable_ready"
        return "stable_partial"
    if checkout_status == "available":
        return "draft_visible"
    return "draft_checkout_missing"


def derive_external_consumer_next_gap(entry: dict[str, Any], bridge_state: str) -> str:
    artifact_status_counts = entry.get("artifact_status_counts", {})
    if not isinstance(artifact_status_counts, dict):
        artifact_status_counts = {}
    if bridge_state == "stable_checkout_missing":
        return str(
            external_consumer_overlay_policy_lookup("next_gap_defaults.stable_checkout_missing")
        )
    if bridge_state == "stable_identity_unverified":
        return str(
            external_consumer_overlay_policy_lookup("next_gap_defaults.stable_identity_unverified")
        )
    if bridge_state == "stable_partial":
        partial_priority = external_consumer_overlay_policy_lookup(
            "next_gap_defaults.stable_partial_priority"
        )
        if isinstance(partial_priority, list):
            for item in partial_priority:
                if not isinstance(item, dict):
                    continue
                artifact_status = str(item.get("artifact_status", "")).strip()
                next_gap = str(item.get("next_gap", "")).strip()
                status_count = int(artifact_status_counts.get(artifact_status, 0) or 0)
                if artifact_status and next_gap and status_count > 0:
                    return next_gap
        return str(external_consumer_overlay_policy_lookup("next_gap_defaults.stable_partial"))
    if bridge_state == "draft_visible":
        return str(external_consumer_overlay_policy_lookup("next_gap_defaults.draft_visible"))
    if bridge_state == "draft_checkout_missing":
        return str(
            external_consumer_overlay_policy_lookup("next_gap_defaults.draft_checkout_missing")
        )
    return "none"


def build_external_consumer_overlay(
    index: dict[str, Any],
    metric_signal_index: dict[str, Any],
) -> dict[str, Any]:
    entries = list(index.get("entries", []))
    metrics_by_id = {
        str(entry.get("metric_id", "")).strip(): entry
        for entry in metric_signal_index.get("metrics", [])
        if isinstance(entry, dict) and str(entry.get("metric_id", "")).strip()
    }
    bridge_state_groups: dict[str, list[str]] = {}
    reference_state_groups: dict[str, list[str]] = {}
    contract_status_groups: dict[str, list[str]] = {}
    metric_pressure_groups: dict[str, list[str]] = {}
    named_filters = {name: [] for name in EXTERNAL_CONSUMER_NAMED_FILTERS}
    backlog_items: list[dict[str, Any]] = []
    overlay_entries: list[dict[str, Any]] = []

    for raw_entry in entries:
        if not isinstance(raw_entry, dict):
            continue
        consumer_id = str(raw_entry.get("consumer_id", "")).strip()
        if not consumer_id:
            continue
        reference_state = str(raw_entry.get("reference_state", "")).strip() or "draft_reference"
        contract_status = str(raw_entry.get("contract_status", "")).strip() or "unavailable"
        bridge_state = derive_external_consumer_bridge_state(raw_entry)
        metric_bindings = [
            binding
            for binding in raw_entry.get("metric_bindings", [])
            if isinstance(binding, dict) and str(binding.get("metric_id", "")).strip()
        ]
        bound_metrics: list[dict[str, Any]] = []
        bound_metric_status = "unbound"
        for binding in metric_bindings:
            metric_id = str(binding.get("metric_id", "")).strip()
            metric_entry = metrics_by_id.get(metric_id, {})
            metric_status = str(metric_entry.get("status", "unknown")).strip() or "unknown"
            bound_metrics.append(
                {
                    "metric_id": metric_id,
                    "binding_role": str(binding.get("binding_role", "")).strip(),
                    "status": metric_status,
                    "score": metric_entry.get("score"),
                    "minimum_score": metric_entry.get("minimum_score"),
                    "threshold_gap": metric_entry.get("threshold_gap"),
                }
            )
        if bound_metrics:
            statuses = {str(item.get("status", "")).strip() for item in bound_metrics}
            if "below_threshold" in statuses:
                bound_metric_status = "below_threshold"
            elif "healthy" in statuses:
                bound_metric_status = "healthy"
            else:
                bound_metric_status = "tracked_unknown"
        next_gap = derive_external_consumer_next_gap(raw_entry, bridge_state)

        bridge_state_groups.setdefault(bridge_state, []).append(consumer_id)
        reference_state_groups.setdefault(reference_state, []).append(consumer_id)
        contract_status_groups.setdefault(contract_status, []).append(consumer_id)
        metric_pressure_groups.setdefault(bound_metric_status, []).append(consumer_id)

        if bridge_state == "stable_ready":
            named_filters["stable_ready"].append(consumer_id)
        if bridge_state == "stable_partial":
            named_filters["contract_gap"].append(consumer_id)
        if bridge_state == "stable_identity_unverified":
            named_filters["identity_unverified"].append(consumer_id)
        if bridge_state in {"stable_checkout_missing", "draft_checkout_missing"}:
            named_filters["missing_checkout"].append(consumer_id)
        if bridge_state == "draft_visible":
            named_filters["draft_visible"].append(consumer_id)
        if bound_metric_status == "below_threshold":
            named_filters["metric_pressure"].append(consumer_id)
        if bridge_state == "stable_ready" and metric_bindings:
            named_filters["threshold_driver_ready"].append(consumer_id)

        overlay_entry = {
            "consumer_id": consumer_id,
            "title": str(raw_entry.get("title", "")).strip(),
            "reference_state": reference_state,
            "bridge_state": bridge_state,
            "contract_status": contract_status,
            "bound_metric_status": bound_metric_status,
            "next_gap": next_gap,
            "policy_reference": external_consumer_overlay_policy_reference(),
            "local_checkout": copy.deepcopy(raw_entry.get("local_checkout", {})),
            "artifact_status_counts": copy.deepcopy(raw_entry.get("artifact_status_counts", {})),
            "metric_bindings": bound_metrics,
            "notes": str(raw_entry.get("notes", "")).strip(),
        }
        overlay_entries.append(overlay_entry)

        if next_gap != "none":
            backlog_items.append(
                {
                    "consumer_id": consumer_id,
                    "title": str(raw_entry.get("title", "")).strip(),
                    "bridge_state": bridge_state,
                    "contract_status": contract_status,
                    "bound_metric_status": bound_metric_status,
                    "next_gap": next_gap,
                }
            )

    grouped_backlog: dict[str, list[str]] = {}
    for item in backlog_items:
        grouped_backlog.setdefault(str(item["next_gap"]), []).append(str(item["consumer_id"]))

    for bucket in (
        bridge_state_groups,
        reference_state_groups,
        contract_status_groups,
        metric_pressure_groups,
        named_filters,
        grouped_backlog,
    ):
        for key in list(bucket):
            bucket[key] = sorted(set(bucket[key]))

    return {
        "artifact_kind": EXTERNAL_CONSUMER_OVERLAY_ARTIFACT_KIND,
        "schema_version": EXTERNAL_CONSUMER_OVERLAY_SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "layer_name": EXTERNAL_CONSUMER_LAYER_NAME,
        "policy_reference": external_consumer_overlay_policy_reference(),
        "source_index_path": external_consumer_index_path().relative_to(ROOT).as_posix(),
        "source_index_generated_at": index.get("generated_at"),
        "source_metric_signal_path": metric_signal_index_path().relative_to(ROOT).as_posix(),
        "source_metric_signal_generated_at": metric_signal_index.get("generated_at"),
        "entry_count": len(overlay_entries),
        "entries": overlay_entries,
        "viewer_projection": {
            "bridge_state": {
                key: sorted(value) for key, value in sorted(bridge_state_groups.items())
            },
            "reference_state": {
                key: sorted(value) for key, value in sorted(reference_state_groups.items())
            },
            "contract_status": {
                key: sorted(value) for key, value in sorted(contract_status_groups.items())
            },
            "bound_metric_status": {
                key: sorted(value) for key, value in sorted(metric_pressure_groups.items())
            },
            "named_filters": {key: sorted(value) for key, value in sorted(named_filters.items())},
        },
        "external_consumer_backlog": {
            "entry_count": len(backlog_items),
            "items": backlog_items,
            "grouped_by_next_gap": {
                key: sorted(value) for key, value in sorted(grouped_backlog.items())
            },
        },
    }


def write_external_consumer_overlay(overlay: dict[str, Any]) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = external_consumer_overlay_path()
    with artifact_lock(path):
        atomic_write_json(path, overlay)
    return path


def derive_external_consumer_handoff_status(
    *,
    reference_state: str,
    bridge_state: str,
) -> str:
    stable_reference_state = str(
        external_consumer_handoff_policy_lookup("eligibility_rules.stable_reference_state")
    ).strip()
    draft_reference_state = str(
        external_consumer_handoff_policy_lookup("eligibility_rules.draft_reference_state")
    ).strip()
    ready_bridge_states = {
        str(item).strip()
        for item in external_consumer_handoff_policy_lookup("eligibility_rules.ready_bridge_states")
        if str(item).strip()
    }
    blocked_bridge_states = {
        str(item).strip()
        for item in external_consumer_handoff_policy_lookup(
            "eligibility_rules.blocked_bridge_states"
        )
        if str(item).strip()
    }

    if reference_state == draft_reference_state:
        return "draft_reference_only"
    if reference_state == stable_reference_state and bridge_state in ready_bridge_states:
        return "ready_for_handoff"
    if reference_state == stable_reference_state and bridge_state in blocked_bridge_states:
        return "blocked_by_bridge_gap"
    return "blocked_by_bridge_gap"


def derive_external_consumer_handoff_next_gap(
    *,
    handoff_status: str,
    overlay_entry: dict[str, Any],
) -> str:
    default_gap = str(
        external_consumer_handoff_policy_lookup(f"next_gap_defaults.{handoff_status}")
    ).strip()
    if default_gap == "inherit_external_consumer_next_gap":
        inherited = str(overlay_entry.get("next_gap", "")).strip()
        return inherited or "review_bridge_gap"
    return default_gap or "none"


def build_external_consumer_handoff_packets(
    external_consumer_index: dict[str, Any],
    external_consumer_overlay: dict[str, Any],
    metric_signal_index: dict[str, Any],
    metric_threshold_proposals: dict[str, Any],
) -> dict[str, Any]:
    overlay_entries = {
        str(entry.get("consumer_id", "")).strip(): entry
        for entry in external_consumer_overlay.get("entries", [])
        if isinstance(entry, dict) and str(entry.get("consumer_id", "")).strip()
    }
    metrics_by_id = {
        str(entry.get("metric_id", "")).strip(): entry
        for entry in metric_signal_index.get("metrics", [])
        if isinstance(entry, dict) and str(entry.get("metric_id", "")).strip()
    }
    threshold_entries_by_metric: dict[str, list[dict[str, Any]]] = {}
    for entry in metric_threshold_proposals.get("entries", []):
        if not isinstance(entry, dict):
            continue
        metric_id = str(entry.get("metric_id", "")).strip()
        if not metric_id:
            continue
        threshold_entries_by_metric.setdefault(metric_id, []).append(entry)

    entries: list[dict[str, Any]] = []
    handoff_status_groups: dict[str, list[str]] = {}
    review_state_groups: dict[str, list[str]] = {}
    named_filters = {name: [] for name in EXTERNAL_CONSUMER_HANDOFF_NAMED_FILTERS}
    backlog_items: list[dict[str, Any]] = []
    grouped_backlog: dict[str, list[str]] = {}
    source_refs = [
        str(path).strip()
        for path in external_consumer_handoff_policy_lookup("packet_provenance.source_refs")
        if str(path).strip()
    ]
    required_provenance_links = [
        str(item).strip()
        for item in external_consumer_handoff_policy_lookup(
            "packet_provenance.required_provenance_links"
        )
        if str(item).strip()
    ]

    for raw_entry in external_consumer_index.get("entries", []):
        if not isinstance(raw_entry, dict):
            continue
        consumer_id = str(raw_entry.get("consumer_id", "")).strip()
        if not consumer_id:
            continue
        local_checkout = raw_entry.get("local_checkout", {})
        local_checkout_hint = ""
        if isinstance(local_checkout, dict):
            local_checkout_hint = str(local_checkout.get("checkout_path", "")).strip()
        if not local_checkout_hint:
            local_checkout_hint = str(raw_entry.get("local_checkout_hint", "")).strip()
        overlay_entry = overlay_entries.get(consumer_id, {})
        reference_state = str(raw_entry.get("reference_state", "")).strip()
        bridge_state = str(overlay_entry.get("bridge_state", "")).strip()
        handoff_status = derive_external_consumer_handoff_status(
            reference_state=reference_state,
            bridge_state=bridge_state,
        )
        next_gap = derive_external_consumer_handoff_next_gap(
            handoff_status=handoff_status,
            overlay_entry=overlay_entry if isinstance(overlay_entry, dict) else {},
        )
        metric_ids = sorted(
            {
                str(binding.get("metric_id", "")).strip()
                for binding in raw_entry.get("metric_bindings", [])
                if isinstance(binding, dict) and str(binding.get("metric_id", "")).strip()
            }
        )
        bound_metrics = [
            copy.deepcopy(metrics_by_id[metric_id])
            for metric_id in metric_ids
            if metric_id in metrics_by_id
        ]
        threshold_proposals = []
        for metric_id in metric_ids:
            threshold_proposals.extend(
                copy.deepcopy(item) for item in threshold_entries_by_metric.get(metric_id, [])
            )
        threshold_proposal_ids = sorted(
            {
                str(item.get("proposal_id", "")).strip()
                for item in threshold_proposals
                if str(item.get("proposal_id", "")).strip()
            }
        )
        review_state = (
            "ready_for_review" if handoff_status == "ready_for_handoff" else "not_emitted"
        )
        transition_packet = None
        validation_report = None
        if handoff_status == "ready_for_handoff":
            transition_packet = {
                "packet_type": EXTERNAL_CONSUMER_HANDOFF_PACKET_TYPE,
                "transition_profile": EXTERNAL_CONSUMER_HANDOFF_TRANSITION_PROFILE,
                "transition_intent": (
                    "handoff bounded SpecGraph metric and bridge surfaces to external consumer "
                    f"{str(raw_entry.get('title', consumer_id)).strip()}"
                ),
                "source_refs": copy.deepcopy(source_refs),
                "actor_class": "supervisor_derived",
                "target_artifact_class": EXTERNAL_CONSUMER_HANDOFF_TARGET_ARTIFACT_CLASS,
                "lineage_root": f"external-consumer::{consumer_id}",
                "declared_change_surface": [
                    external_consumer_handoff_packets_path().relative_to(ROOT).as_posix()
                ],
                "required_provenance_links": copy.deepcopy(required_provenance_links),
            }
            validation_report = validate_transition_packet_report(
                transition_packet,
                validator_profile=EXTERNAL_CONSUMER_HANDOFF_TRANSITION_PROFILE,
            )

        entry = {
            "handoff_id": f"external_consumer_handoff::{consumer_id}",
            "consumer_id": consumer_id,
            "title": str(raw_entry.get("title", "")).strip(),
            "reference_state": reference_state,
            "bridge_state": bridge_state,
            "handoff_status": handoff_status,
            "review_state": review_state,
            "next_gap": next_gap,
            "policy_reference": external_consumer_handoff_policy_reference(),
            "bound_metric_ids": metric_ids,
            "bound_metrics": bound_metrics,
            "threshold_proposal_ids": threshold_proposal_ids,
            "threshold_proposal_count": len(threshold_proposal_ids),
            "target_consumer": {
                "consumer_id": consumer_id,
                "profile": str(raw_entry.get("profile", "")).strip(),
                "repo_url": str(raw_entry.get("repo_url", "")).strip(),
                "local_checkout_hint": local_checkout_hint,
            },
            "transition_packet": transition_packet,
            "transition_packet_validation": validation_report,
            "notes": str(raw_entry.get("notes", "")).strip(),
        }
        entries.append(entry)
        handoff_status_groups.setdefault(handoff_status, []).append(consumer_id)
        review_state_groups.setdefault(review_state, []).append(consumer_id)
        if handoff_status == "ready_for_handoff":
            named_filters["ready_for_handoff"].append(consumer_id)
        if handoff_status == "blocked_by_bridge_gap":
            named_filters["blocked_by_bridge_gap"].append(consumer_id)
        if handoff_status == "draft_reference_only":
            named_filters["draft_reference_only"].append(consumer_id)
        if threshold_proposal_ids:
            named_filters["threshold_driven"].append(consumer_id)
        if validation_report and not validation_report.get("ok"):
            named_filters["packet_validation_failed"].append(consumer_id)
        if next_gap != "none":
            backlog_items.append(
                {
                    "consumer_id": consumer_id,
                    "handoff_status": handoff_status,
                    "review_state": review_state,
                    "next_gap": next_gap,
                }
            )
            grouped_backlog.setdefault(next_gap, []).append(consumer_id)

    for bucket in (handoff_status_groups, review_state_groups, named_filters, grouped_backlog):
        for key in list(bucket):
            bucket[key] = sorted(set(bucket[key]))

    return {
        "artifact_kind": EXTERNAL_CONSUMER_HANDOFF_ARTIFACT_KIND,
        "schema_version": EXTERNAL_CONSUMER_HANDOFF_SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "policy_reference": external_consumer_handoff_policy_reference(),
        "source_artifacts": {
            "external_consumer_index": {
                "artifact_path": external_consumer_index_path().relative_to(ROOT).as_posix(),
                "generated_at": external_consumer_index.get("generated_at"),
            },
            "external_consumer_overlay": {
                "artifact_path": external_consumer_overlay_path().relative_to(ROOT).as_posix(),
                "generated_at": external_consumer_overlay.get("generated_at"),
            },
            "metric_signal_index": {
                "artifact_path": metric_signal_index_path().relative_to(ROOT).as_posix(),
                "generated_at": metric_signal_index.get("generated_at"),
            },
            "metric_threshold_proposals": {
                "artifact_path": metric_threshold_proposals_path().relative_to(ROOT).as_posix(),
                "generated_at": metric_threshold_proposals.get("generated_at"),
            },
        },
        "entry_count": len(entries),
        "entries": entries,
        "viewer_projection": {
            "handoff_status": {
                key: sorted(value) for key, value in sorted(handoff_status_groups.items())
            },
            "review_state": {
                key: sorted(value) for key, value in sorted(review_state_groups.items())
            },
            "named_filters": {key: sorted(value) for key, value in sorted(named_filters.items())},
        },
        "handoff_backlog": {
            "entry_count": len(backlog_items),
            "items": backlog_items,
            "grouped_by_next_gap": {
                key: sorted(value) for key, value in sorted(grouped_backlog.items())
            },
        },
    }


def write_external_consumer_handoff_packets(report: dict[str, Any]) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = external_consumer_handoff_packets_path()
    with artifact_lock(path):
        atomic_write_json(path, report)
    return path


def build_specpm_export_preview(specs: list[SpecNode]) -> dict[str, Any]:
    registry = load_specpm_export_registry()
    external_consumer_index = build_external_consumer_index()
    metric_signal_index = build_metric_signal_index(specs)
    external_consumer_overlay = build_external_consumer_overlay(
        external_consumer_index,
        metric_signal_index,
    )
    spec_by_id = {spec.id: spec for spec in specs if spec.id}
    consumer_entries = {
        str(entry.get("consumer_id", "")).strip(): entry
        for entry in external_consumer_index.get("entries", [])
        if isinstance(entry, dict) and str(entry.get("consumer_id", "")).strip()
    }
    overlay_entries = {
        str(entry.get("consumer_id", "")).strip(): entry
        for entry in external_consumer_overlay.get("entries", [])
        if isinstance(entry, dict) and str(entry.get("consumer_id", "")).strip()
    }
    required_consumer_id = str(
        specpm_export_policy_lookup("consumer_contract.required_consumer_id")
    )
    required_profile = str(specpm_export_policy_lookup("consumer_contract.required_profile"))
    required_fields = [
        str(item).strip()
        for item in specpm_export_policy_lookup("required_export_fields")
        if str(item).strip()
    ]
    boundary_spec_gaps = [
        str(item).strip()
        for item in specpm_export_policy_lookup("boundary_spec_gaps")
        if str(item).strip()
    ]

    entries: list[dict[str, Any]] = []
    status_groups: dict[str, list[str]] = {}
    review_state_groups: dict[str, list[str]] = {}
    next_gap_groups: dict[str, list[str]] = {}
    named_filters = {name: [] for name in SPECPM_EXPORT_PREVIEW_NAMED_FILTERS}
    backlog_items: list[dict[str, Any]] = []

    for raw_entry in registry.get("entries", []):
        if not isinstance(raw_entry, dict):
            continue
        export_id = str(raw_entry.get("export_id", "")).strip()
        if not export_id:
            continue

        export_contract_errors: list[str] = []
        for field_name in required_fields:
            raw_value = raw_entry.get(field_name)
            if field_name in {
                "source_spec_ids",
                "provides_capabilities",
                "requires_capabilities",
                "keywords",
            }:
                if field_name not in raw_entry:
                    export_contract_errors.append(f"missing_{field_name}")
                    continue
                if not isinstance(raw_value, list) or not any(
                    str(item).strip() for item in raw_value
                ):
                    if field_name != "requires_capabilities":
                        export_contract_errors.append(f"invalid_{field_name}")
                continue
            if not str(raw_value).strip():
                export_contract_errors.append(f"missing_{field_name}")

        consumer_id = str(raw_entry.get("consumer_id", "")).strip()
        consumer_entry = consumer_entries.get(consumer_id, {})
        overlay_entry = overlay_entries.get(consumer_id, {})
        consumer_title = str(consumer_entry.get("title", "")).strip() or consumer_id
        consumer_profile = str(consumer_entry.get("profile", "")).strip()
        consumer_reference_state = (
            str(consumer_entry.get("reference_state", "")).strip() or "draft_reference"
        )
        consumer_bridge_state = str(overlay_entry.get("bridge_state", "")).strip()
        consumer_next_gap = str(overlay_entry.get("next_gap", "")).strip() or "none"

        if consumer_id != required_consumer_id:
            export_contract_errors.append("wrong_consumer_id")
        if consumer_profile != required_profile:
            export_contract_errors.append("wrong_consumer_profile")
        if not consumer_entry:
            export_contract_errors.append("missing_external_consumer")

        root_spec_id = str(raw_entry.get("root_spec_id", "")).strip()
        source_spec_ids: list[str] = []
        for item in raw_entry.get("source_spec_ids", []):
            spec_id = str(item).strip()
            if spec_id and spec_id not in source_spec_ids:
                source_spec_ids.append(spec_id)
        provides_capabilities: list[str] = []
        for item in raw_entry.get("provides_capabilities", []):
            capability_id = str(item).strip()
            if capability_id and capability_id not in provides_capabilities:
                provides_capabilities.append(capability_id)
        requires_capabilities: list[str] = []
        for item in raw_entry.get("requires_capabilities", []):
            capability_id = str(item).strip()
            if capability_id and capability_id not in requires_capabilities:
                requires_capabilities.append(capability_id)
        keywords: list[str] = []
        for item in raw_entry.get("keywords", []):
            keyword = str(item).strip()
            if keyword and keyword not in keywords:
                keywords.append(keyword)

        if root_spec_id and root_spec_id not in spec_by_id:
            export_contract_errors.append("missing_root_spec")
        missing_source_spec_ids = [
            spec_id for spec_id in source_spec_ids if spec_id not in spec_by_id
        ]
        if missing_source_spec_ids:
            export_contract_errors.append("missing_source_specs")

        export_status = "invalid_export_contract"
        review_state = "not_emitted"
        if not export_contract_errors:
            if consumer_bridge_state == "stable_ready":
                export_status = "ready_for_review"
                review_state = "ready_for_review"
            elif consumer_bridge_state == "draft_visible":
                export_status = "draft_preview_only"
                review_state = "draft_preview_only"
            else:
                export_status = "blocked_by_consumer_gap"

        if export_status == "ready_for_review":
            next_gap = str(specpm_export_policy_lookup("next_gap_defaults.ready_for_review"))
        elif export_status == "draft_preview_only":
            next_gap = str(specpm_export_policy_lookup("next_gap_defaults.draft_preview_only"))
        elif export_status == "blocked_by_consumer_gap":
            next_gap = consumer_next_gap or str(
                specpm_export_policy_lookup("next_gap_defaults.blocked_by_consumer_gap")
            )
        else:
            next_gap = str(specpm_export_policy_lookup("next_gap_defaults.invalid_export_contract"))

        manifest_preview = None
        boundary_source_preview = None
        if not export_contract_errors:
            manifest_preview = {
                "apiVersion": "specpm.dev/v0.1",
                "kind": "SpecPackage",
                "metadata": {
                    "id": str(raw_entry.get("package_id", "")).strip(),
                    "name": str(raw_entry.get("package_name", "")).strip(),
                    "version": str(raw_entry.get("package_version", "")).strip(),
                    "summary": str(raw_entry.get("package_summary", "")).strip(),
                    "license": str(raw_entry.get("package_license", "")).strip(),
                },
                "specs": [
                    {
                        "path": "specs/main.spec.yaml",
                    }
                ],
                "index": {
                    "provides": {
                        "capabilities": provides_capabilities,
                    },
                    "requires": {
                        "capabilities": requires_capabilities,
                    },
                },
                "preview_only": True,
            }
            if keywords:
                manifest_preview["keywords"] = keywords

            source_spec_entries = [
                {
                    "spec_id": spec.id,
                    "title": spec.title,
                    "path": spec.path.relative_to(ROOT).as_posix(),
                    "status": spec.status,
                    "maturity": spec.maturity,
                }
                for spec_id in source_spec_ids
                for spec in [spec_by_id[spec_id]]
            ]
            root_spec = spec_by_id[root_spec_id]
            boundary_source_preview = {
                "root_spec_id": root_spec_id,
                "root_spec_title": root_spec.title,
                "bounded_context": str(raw_entry.get("bounded_context", "")).strip(),
                "intent_summary": str(raw_entry.get("package_summary", "")).strip(),
                "source_specs": source_spec_entries,
                "acceptance_criteria": [
                    str(item).strip()
                    for item in root_spec.data.get("acceptance", [])
                    if str(item).strip()
                ],
                "evidence_refs": sorted(
                    {
                        str(item).strip()
                        for item in (
                            list(root_spec.inputs)
                            + [spec.path.relative_to(ROOT).as_posix() for spec in [root_spec]]
                        )
                        if str(item).strip()
                    }
                ),
                "provides_capabilities": provides_capabilities,
                "requires_capabilities": requires_capabilities,
                "missing_fields_for_full_boundary_spec": boundary_spec_gaps,
                "notes": str(raw_entry.get("notes", "")).strip(),
            }

        entry = {
            "export_id": export_id,
            "consumer_id": consumer_id,
            "consumer_title": consumer_title,
            "consumer_reference_state": consumer_reference_state,
            "consumer_bridge_state": consumer_bridge_state,
            "export_status": export_status,
            "review_state": review_state,
            "next_gap": next_gap,
            "policy_reference": specpm_export_policy_reference(),
            "registry_reference": {
                "artifact_path": SPECPM_EXPORT_REGISTRY_RELATIVE_PATH,
                "artifact_kind": str(registry.get("artifact_kind", "")).strip()
                or "specpm_export_registry",
                "version": int(registry.get("version", 1) or 1),
            },
            "package_preview": manifest_preview,
            "boundary_source_preview": boundary_source_preview,
            "contract_summary": {
                "root_spec_id": root_spec_id,
                "source_spec_ids": source_spec_ids,
                "provides_capabilities": provides_capabilities,
                "requires_capabilities": requires_capabilities,
            },
            "contract_errors": sorted(set(export_contract_errors)),
            "notes": str(raw_entry.get("notes", "")).strip(),
        }
        entries.append(entry)

        status_groups.setdefault(export_status, []).append(export_id)
        review_state_groups.setdefault(review_state, []).append(export_id)
        next_gap_groups.setdefault(next_gap, []).append(export_id)

        if export_status == "ready_for_review":
            named_filters["stable_ready"].append(export_id)
        if export_status == "draft_preview_only":
            named_filters["draft_preview_only"].append(export_id)
        if export_status == "blocked_by_consumer_gap":
            named_filters["blocked_by_consumer_gap"].append(export_id)
        if export_status == "invalid_export_contract":
            named_filters["invalid_export_contract"].append(export_id)
        if manifest_preview is not None:
            named_filters["manifest_preview_complete"].append(export_id)

        if next_gap != "none":
            backlog_items.append(
                {
                    "export_id": export_id,
                    "export_status": export_status,
                    "review_state": review_state,
                    "next_gap": next_gap,
                }
            )

    for bucket in (status_groups, review_state_groups, next_gap_groups, named_filters):
        for key in list(bucket):
            bucket[key] = sorted(set(bucket[key]))

    return {
        "artifact_kind": SPECPM_EXPORT_PREVIEW_ARTIFACT_KIND,
        "schema_version": SPECPM_EXPORT_PREVIEW_SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "policy_reference": specpm_export_policy_reference(),
        "source_artifacts": {
            "specpm_export_registry": {
                "artifact_path": SPECPM_EXPORT_REGISTRY_RELATIVE_PATH,
                "version": int(registry.get("version", 1) or 1),
            },
            "external_consumer_index": {
                "artifact_path": external_consumer_index_path().relative_to(ROOT).as_posix(),
                "generated_at": external_consumer_index.get("generated_at"),
            },
            "external_consumer_overlay": {
                "artifact_path": external_consumer_overlay_path().relative_to(ROOT).as_posix(),
                "generated_at": external_consumer_overlay.get("generated_at"),
            },
        },
        "entry_count": len(entries),
        "entries": entries,
        "viewer_projection": {
            "export_status": {key: sorted(value) for key, value in sorted(status_groups.items())},
            "review_state": {
                key: sorted(value) for key, value in sorted(review_state_groups.items())
            },
            "next_gap": {key: sorted(value) for key, value in sorted(next_gap_groups.items())},
            "named_filters": {key: sorted(value) for key, value in sorted(named_filters.items())},
        },
        "export_backlog": {
            "entry_count": len(backlog_items),
            "items": backlog_items,
        },
    }


def write_specpm_export_preview(report: dict[str, Any]) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = specpm_export_preview_path()
    with artifact_lock(path):
        atomic_write_json(path, report)
    return path


def derive_specpm_handoff_next_gap(
    *,
    handoff_status: str,
    preview_entry: dict[str, Any],
) -> str:
    default_gap = str(specpm_handoff_policy_lookup(f"next_gap_defaults.{handoff_status}")).strip()
    if default_gap == "inherit_preview_next_gap":
        inherited = str(preview_entry.get("next_gap", "")).strip()
        return inherited or "review_specpm_export_preview"
    return default_gap or "none"


def build_specpm_handoff_packets(
    specpm_export_preview: dict[str, Any],
    external_consumer_index: dict[str, Any],
) -> dict[str, Any]:
    consumer_entries = {
        str(entry.get("consumer_id", "")).strip(): entry
        for entry in external_consumer_index.get("entries", [])
        if isinstance(entry, dict) and str(entry.get("consumer_id", "")).strip()
    }
    entries: list[dict[str, Any]] = []
    handoff_status_groups: dict[str, list[str]] = {}
    review_state_groups: dict[str, list[str]] = {}
    named_filters = {name: [] for name in SPECPM_HANDOFF_NAMED_FILTERS}
    backlog_items: list[dict[str, Any]] = []
    grouped_backlog: dict[str, list[str]] = {}
    source_refs = [
        str(path).strip()
        for path in specpm_handoff_policy_lookup("packet_provenance.source_refs")
        if str(path).strip()
    ]
    required_provenance_links = [
        str(item).strip()
        for item in specpm_handoff_policy_lookup("packet_provenance.required_provenance_links")
        if str(item).strip()
    ]

    for raw_entry in specpm_export_preview.get("entries", []):
        if not isinstance(raw_entry, dict):
            continue
        export_id = str(raw_entry.get("export_id", "")).strip()
        if not export_id:
            continue
        consumer_id = str(raw_entry.get("consumer_id", "")).strip()
        consumer_entry = consumer_entries.get(consumer_id, {})
        export_status = str(raw_entry.get("export_status", "")).strip()
        if export_status == "ready_for_review":
            handoff_status = "ready_for_handoff"
            review_state = "ready_for_review"
        elif export_status == "draft_preview_only":
            handoff_status = "draft_preview_only"
            review_state = "draft_preview_only"
        elif export_status == "blocked_by_consumer_gap":
            handoff_status = "blocked_by_preview_gap"
            review_state = "not_emitted"
        else:
            handoff_status = "invalid_export_contract"
            review_state = "not_emitted"

        next_gap = derive_specpm_handoff_next_gap(
            handoff_status=handoff_status,
            preview_entry=raw_entry,
        )
        local_checkout_hint = ""
        local_checkout = consumer_entry.get("local_checkout", {})
        local_checkout_status = ""
        remote_matches = None
        if isinstance(local_checkout, dict):
            local_checkout_hint = str(local_checkout.get("checkout_path", "")).strip()
            local_checkout_status = str(local_checkout.get("status", "")).strip()
            remote_matches = local_checkout.get("remote_matches")
        if not local_checkout_hint:
            local_checkout_hint = str(consumer_entry.get("local_checkout_hint", "")).strip()

        package_preview = copy.deepcopy(raw_entry.get("package_preview"))
        boundary_source_preview = copy.deepcopy(raw_entry.get("boundary_source_preview"))
        package_metadata = (
            package_preview.get("metadata", {}) if isinstance(package_preview, dict) else {}
        )
        transition_packet = None
        validation_report = None
        if handoff_status == "ready_for_handoff":
            transition_packet = {
                "packet_type": SPECPM_HANDOFF_PACKET_TYPE,
                "transition_profile": SPECPM_HANDOFF_TRANSITION_PROFILE,
                "transition_intent": (
                    "handoff SpecPM boundary package preview "
                    f"{str(package_metadata.get('id', export_id)).strip() or export_id} "
                    "for downstream review"
                ),
                "source_refs": copy.deepcopy(source_refs),
                "actor_class": "supervisor_derived",
                "target_artifact_class": SPECPM_HANDOFF_TARGET_ARTIFACT_CLASS,
                "lineage_root": f"specpm-export::{export_id}",
                "declared_change_surface": [
                    specpm_handoff_packets_path().relative_to(ROOT).as_posix()
                ],
                "required_provenance_links": copy.deepcopy(required_provenance_links),
            }
            validation_report = validate_transition_packet_report(
                transition_packet,
                validator_profile=SPECPM_HANDOFF_TRANSITION_PROFILE,
            )

        entry = {
            "handoff_id": f"specpm_handoff::{export_id}",
            "export_id": export_id,
            "consumer_id": consumer_id,
            "handoff_status": handoff_status,
            "review_state": review_state,
            "next_gap": next_gap,
            "policy_reference": specpm_handoff_policy_reference(),
            "preview_reference": {
                "artifact_path": specpm_export_preview_path().relative_to(ROOT).as_posix(),
                "generated_at": specpm_export_preview.get("generated_at"),
                "export_status": export_status,
                "review_state": str(raw_entry.get("review_state", "")).strip(),
            },
            "target_consumer": {
                "consumer_id": consumer_id,
                "title": str(consumer_entry.get("title", "")).strip()
                or str(raw_entry.get("consumer_title", "")).strip()
                or consumer_id,
                "profile": str(consumer_entry.get("profile", "")).strip(),
                "reference_state": str(raw_entry.get("consumer_reference_state", "")).strip(),
                "bridge_state": str(raw_entry.get("consumer_bridge_state", "")).strip(),
                "repo_url": str(consumer_entry.get("repo_url", "")).strip(),
                "local_checkout_hint": local_checkout_hint,
                "local_checkout_status": local_checkout_status,
                "identity_verified": remote_matches is True,
            },
            "package_identity": {
                "package_id": str(package_metadata.get("id", "")).strip(),
                "package_name": str(package_metadata.get("name", "")).strip(),
                "package_version": str(package_metadata.get("version", "")).strip(),
            },
            "package_preview": package_preview,
            "boundary_source_preview": boundary_source_preview,
            "contract_errors": copy.deepcopy(raw_entry.get("contract_errors", [])),
            "transition_packet": transition_packet,
            "transition_packet_validation": validation_report,
            "notes": str(raw_entry.get("notes", "")).strip(),
        }
        entries.append(entry)
        handoff_status_groups.setdefault(handoff_status, []).append(export_id)
        review_state_groups.setdefault(review_state, []).append(export_id)
        named_filters.setdefault(handoff_status, []).append(export_id)
        if package_preview is not None:
            named_filters["package_preview_complete"].append(export_id)
        if validation_report and not validation_report.get("ok"):
            named_filters["packet_validation_failed"].append(export_id)
        if next_gap != "none":
            backlog_items.append(
                {
                    "export_id": export_id,
                    "handoff_status": handoff_status,
                    "review_state": review_state,
                    "next_gap": next_gap,
                }
            )
            grouped_backlog.setdefault(next_gap, []).append(export_id)

    for bucket in (handoff_status_groups, review_state_groups, named_filters, grouped_backlog):
        for key in list(bucket):
            bucket[key] = sorted(set(bucket[key]))

    return {
        "artifact_kind": SPECPM_HANDOFF_ARTIFACT_KIND,
        "schema_version": SPECPM_HANDOFF_SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "policy_reference": specpm_handoff_policy_reference(),
        "source_artifacts": {
            "specpm_export_preview": {
                "artifact_path": specpm_export_preview_path().relative_to(ROOT).as_posix(),
                "generated_at": specpm_export_preview.get("generated_at"),
            },
            "external_consumer_index": {
                "artifact_path": external_consumer_index_path().relative_to(ROOT).as_posix(),
                "generated_at": external_consumer_index.get("generated_at"),
            },
        },
        "entry_count": len(entries),
        "entries": entries,
        "viewer_projection": {
            "handoff_status": {
                key: sorted(value) for key, value in sorted(handoff_status_groups.items())
            },
            "review_state": {
                key: sorted(value) for key, value in sorted(review_state_groups.items())
            },
            "named_filters": {key: sorted(value) for key, value in sorted(named_filters.items())},
        },
        "handoff_backlog": {
            "entry_count": len(backlog_items),
            "items": backlog_items,
            "grouped_by_next_gap": {
                key: sorted(value) for key, value in sorted(grouped_backlog.items())
            },
        },
    }


def write_specpm_handoff_packets(report: dict[str, Any]) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = specpm_handoff_packets_path()
    with artifact_lock(path):
        atomic_write_json(path, report)
    return path


def render_yaml_document(data: dict[str, Any]) -> str:
    if yaml is None:
        raise RuntimeError("PyYAML is required to render SpecPM export bundles")
    rendered = yaml.safe_dump(
        data,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=100,
    )
    if not rendered.endswith("\n"):
        rendered += "\n"
    return rendered


def infer_evidence_kind(rel_path: str) -> str:
    text = str(rel_path).strip().lower()
    if text.endswith(".md"):
        return "documentation"
    if "/tests/" in text or text.startswith("tests/"):
        return "test"
    if text.endswith((".yaml", ".yml", ".json", ".graphql", ".proto")):
        return "schema"
    if text.endswith((".py", ".ts", ".js", ".rs", ".go", ".java", ".swift")):
        return "source"
    return "unknown"


def build_specpm_boundary_spec(
    handoff_entry: dict[str, Any],
    *,
    evidence_entries: list[dict[str, Any]],
) -> dict[str, Any]:
    boundary_preview = handoff_entry.get("boundary_source_preview", {})
    package_identity = handoff_entry.get("package_identity", {})
    package_preview = handoff_entry.get("package_preview", {})
    provides_capabilities = [
        str(item).strip()
        for item in boundary_preview.get("provides_capabilities", [])
        if str(item).strip()
    ]
    requires_capabilities = [
        str(item).strip()
        for item in boundary_preview.get("requires_capabilities", [])
        if str(item).strip()
    ]
    includes = [
        str(item).strip()
        for item in boundary_preview.get("acceptance_criteria", [])
        if str(item).strip()
    ]
    boundary_spec_id = (
        provides_capabilities[0]
        if provides_capabilities
        else str(package_identity.get("package_id", "")).strip()
    )
    title = str(package_identity.get("package_name", "")).strip()
    version = str(package_identity.get("package_version", "")).strip()
    summary = (
        str(boundary_preview.get("intent_summary", "")).strip()
        or str(package_preview.get("metadata", {}).get("summary", "")).strip()
    )
    bounded_context = str(boundary_preview.get("bounded_context", "")).strip()
    interface_id = str(
        specpm_materialization_policy_lookup("boundary_defaults.placeholder_inbound_interface_id")
    ).strip()
    interface_kind = str(
        specpm_materialization_policy_lookup("boundary_defaults.placeholder_inbound_interface_kind")
    ).strip()
    interface_summary = str(
        specpm_materialization_policy_lookup("boundary_defaults.placeholder_inbound_summary")
    ).strip()
    draft_constraint_id = str(
        specpm_materialization_policy_lookup("boundary_defaults.draft_constraint_id")
    ).strip()
    draft_constraint_statement = str(
        specpm_materialization_policy_lookup("boundary_defaults.draft_constraint_statement")
    ).strip()

    return {
        "apiVersion": str(specpm_materialization_policy_lookup("boundary_defaults.api_version")),
        "kind": "BoundarySpec",
        "metadata": {
            "id": boundary_spec_id,
            "title": title,
            "version": version,
            "status": str(specpm_materialization_policy_lookup("boundary_defaults.status")),
        },
        "intent": {
            "summary": summary,
        },
        "scope": {
            "boundedContext": bounded_context,
            "includes": includes,
        },
        "provides": {
            "capabilities": [
                {
                    "id": capability_id,
                    "role": "primary" if index == 0 else "supporting",
                    "summary": (
                        f"Exported capability {capability_id} from SpecGraph boundary preview."
                    ),
                }
                for index, capability_id in enumerate(provides_capabilities)
            ],
        },
        "requires": {
            "capabilities": [
                {
                    "id": capability_id,
                    "optional": False,
                    "summary": (
                        f"Required capability {capability_id} declared by the "
                        "SpecGraph boundary preview."
                    ),
                }
                for capability_id in requires_capabilities
            ],
        },
        "interfaces": {
            "inbound": [
                {
                    "id": interface_id,
                    "kind": interface_kind,
                    "summary": interface_summary,
                }
            ],
            "outbound": [],
        },
        "constraints": [
            {
                "id": draft_constraint_id,
                "level": "SHOULD",
                "statement": draft_constraint_statement,
            }
        ],
        "evidence": evidence_entries,
        "provenance": {
            "sourceConfidence": copy.deepcopy(
                specpm_materialization_policy_lookup("boundary_defaults.source_confidence")
            )
        },
    }


def derive_specpm_materialization_next_gap(
    *,
    status: str,
    handoff_entry: dict[str, Any],
) -> str:
    default_gap = str(specpm_materialization_policy_lookup(f"next_gap_defaults.{status}")).strip()
    if default_gap == "inherit_handoff_next_gap":
        inherited = str(handoff_entry.get("next_gap", "")).strip()
        return inherited or "review_specpm_handoff_packet"
    return default_gap or "none"


def normalize_specpm_materialization_package_id(value: str) -> str:
    normalized = str(value).strip()
    if not normalized:
        return ""
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts or "." in path.parts or len(path.parts) != 1:
        return ""
    return normalized


def normalize_specpm_materialization_evidence_ref(value: str) -> str:
    normalized = _normalize_transition_repo_path(str(value).strip())
    if not normalized or not _looks_like_repo_path(normalized):
        return ""
    if _validate_transition_surface_path(field_name="evidence_ref", value=normalized):
        return ""
    path = PurePosixPath(normalized)
    if not path.parts or path.name in {"", ".", ".."}:
        return ""
    return path.as_posix()


def materialize_specpm_export_bundles(
    specpm_handoff_packets: dict[str, Any],
) -> dict[str, Any]:
    inbox_root = str(specpm_materialization_policy_lookup("repository_layout.consumer_inbox_root"))
    manifest_relpath = str(specpm_materialization_policy_lookup("bundle_layout.manifest_path"))
    boundary_spec_relpath = str(
        specpm_materialization_policy_lookup("bundle_layout.boundary_spec_path")
    )
    evidence_root_relpath = str(specpm_materialization_policy_lookup("bundle_layout.evidence_root"))
    handoff_sidecar_relpath = str(
        specpm_materialization_policy_lookup("bundle_layout.handoff_sidecar_path")
    )
    required_consumer_id = str(
        specpm_materialization_policy_lookup("eligibility_rules.required_consumer_id")
    )
    required_profile = str(
        specpm_materialization_policy_lookup("eligibility_rules.required_profile")
    )
    required_checkout_status = str(
        specpm_materialization_policy_lookup("eligibility_rules.required_checkout_status")
    )
    require_verified_identity = bool(
        specpm_materialization_policy_lookup("eligibility_rules.require_verified_identity")
    )
    allowed_handoff_statuses = {
        str(item).strip()
        for item in specpm_materialization_policy_lookup(
            "eligibility_rules.allowed_handoff_statuses"
        )
        if str(item).strip()
    }

    entries: list[dict[str, Any]] = []
    status_groups: dict[str, list[str]] = {}
    review_state_groups: dict[str, list[str]] = {}
    named_filters = {name: [] for name in SPECPM_MATERIALIZATION_NAMED_FILTERS}
    backlog_items: list[dict[str, Any]] = []
    grouped_backlog: dict[str, list[str]] = {}

    for raw_entry in specpm_handoff_packets.get("entries", []):
        if not isinstance(raw_entry, dict):
            continue
        export_id = str(raw_entry.get("export_id", "")).strip()
        if not export_id:
            continue
        target_consumer = raw_entry.get("target_consumer", {})
        consumer_id = str(target_consumer.get("consumer_id", "")).strip()
        profile = str(target_consumer.get("profile", "")).strip()
        checkout_hint = str(target_consumer.get("local_checkout_hint", "")).strip()
        checkout_status = str(target_consumer.get("local_checkout_status", "")).strip()
        identity_verified = bool(target_consumer.get("identity_verified", False))
        handoff_status = str(raw_entry.get("handoff_status", "")).strip()
        package_identity = raw_entry.get("package_identity", {})
        package_id = normalize_specpm_materialization_package_id(
            str(package_identity.get("package_id", "")).strip()
        )
        package_preview = raw_entry.get("package_preview")
        boundary_source_preview = raw_entry.get("boundary_source_preview")
        contract_errors = [
            str(item).strip() for item in raw_entry.get("contract_errors", []) if str(item).strip()
        ]

        status = "invalid_handoff_contract"
        review_state = "not_materialized"
        next_gap = "repair_specpm_handoff_packet"
        bundle_root_text = ""
        written_files: list[str] = []
        copied_evidence_refs: list[str] = []
        missing_evidence_refs: list[str] = []

        if (
            consumer_id != required_consumer_id
            or profile != required_profile
            or not package_id
            or not isinstance(package_preview, dict)
            or not isinstance(boundary_source_preview, dict)
            or contract_errors
        ):
            status = "invalid_handoff_contract"
            next_gap = derive_specpm_materialization_next_gap(
                status=status,
                handoff_entry=raw_entry,
            )
        elif handoff_status not in allowed_handoff_statuses:
            status = "blocked_by_handoff_gap"
            next_gap = derive_specpm_materialization_next_gap(
                status=status,
                handoff_entry=raw_entry,
            )
        elif checkout_status != required_checkout_status or not checkout_hint:
            status = "blocked_by_checkout_gap"
            next_gap = derive_specpm_materialization_next_gap(
                status=status,
                handoff_entry=raw_entry,
            )
        elif require_verified_identity and not identity_verified:
            status = "blocked_by_consumer_identity"
            next_gap = derive_specpm_materialization_next_gap(
                status=status,
                handoff_entry=raw_entry,
            )
        else:
            checkout_root = Path(checkout_hint).expanduser()
            inbox_path = checkout_root / inbox_root
            bundle_root = inbox_path / package_id
            try:
                bundle_root.resolve().relative_to(inbox_path.resolve())
            except ValueError:
                status = "invalid_handoff_contract"
                next_gap = derive_specpm_materialization_next_gap(
                    status=status,
                    handoff_entry=raw_entry,
                )
                entry = {
                    "export_id": export_id,
                    "handoff_id": str(raw_entry.get("handoff_id", "")).strip(),
                    "consumer_id": consumer_id,
                    "materialization_status": status,
                    "review_state": review_state,
                    "next_gap": next_gap,
                    "bundle_root": bundle_root_text,
                    "written_files": sorted(set(written_files)),
                    "copied_evidence_refs": sorted(set(copied_evidence_refs)),
                    "missing_evidence_refs": sorted(set(missing_evidence_refs)),
                    "policy_reference": specpm_materialization_policy_reference(),
                    "source_handoff": {
                        "artifact_path": specpm_handoff_packets_path().relative_to(ROOT).as_posix(),
                        "generated_at": specpm_handoff_packets.get("generated_at"),
                        "handoff_status": handoff_status,
                    },
                    "target_consumer": copy.deepcopy(target_consumer),
                    "package_identity": copy.deepcopy(package_identity),
                }
                entries.append(entry)
                status_groups.setdefault(status, []).append(export_id)
                review_state_groups.setdefault(review_state, []).append(export_id)
                named_filters.setdefault(status, []).append(export_id)
                if next_gap != "none":
                    backlog_items.append(
                        {
                            "export_id": export_id,
                            "materialization_status": status,
                            "review_state": review_state,
                            "next_gap": next_gap,
                        }
                    )
                    grouped_backlog.setdefault(next_gap, []).append(export_id)
                continue
            bundle_root_text = bundle_root.as_posix()
            if bundle_root.exists():
                shutil.rmtree(bundle_root)
            (bundle_root / Path(boundary_spec_relpath).parent).mkdir(parents=True, exist_ok=True)
            (bundle_root / evidence_root_relpath).mkdir(parents=True, exist_ok=True)

            evidence_entries: list[dict[str, Any]] = []
            evidence_refs: list[str] = []
            for raw_item in boundary_source_preview.get("evidence_refs", []):
                raw_ref = str(raw_item).strip()
                if not raw_ref:
                    continue
                normalized_ref = normalize_specpm_materialization_evidence_ref(raw_ref)
                if not normalized_ref:
                    missing_evidence_refs.append(raw_ref)
                    continue
                evidence_refs.append(normalized_ref)
            for index, rel_ref in enumerate(evidence_refs, start=1):
                source_path = (ROOT / rel_ref).resolve()
                try:
                    source_path.relative_to(ROOT.resolve())
                except ValueError:
                    missing_evidence_refs.append(rel_ref)
                    continue
                if not source_path.exists() or not source_path.is_file():
                    missing_evidence_refs.append(rel_ref)
                    continue
                target_path = bundle_root / evidence_root_relpath / rel_ref
                try:
                    target_path.resolve().relative_to(
                        (bundle_root / evidence_root_relpath).resolve()
                    )
                except ValueError:
                    missing_evidence_refs.append(rel_ref)
                    continue
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, target_path)
                copied_relpath = target_path.relative_to(bundle_root).as_posix()
                copied_evidence_refs.append(rel_ref)
                written_files.append(copied_relpath)
                evidence_entries.append(
                    {
                        "id": f"evidence_{index}",
                        "kind": infer_evidence_kind(rel_ref),
                        "path": copied_relpath,
                        "supports": [
                            "intent.summary",
                            *[
                                f"provides.capabilities.{capability_id}"
                                for capability_id in (
                                    boundary_source_preview.get("provides_capabilities", []) or []
                                )
                                if str(capability_id).strip()
                            ],
                        ],
                    }
                )

            notes_relpath = f"{evidence_root_relpath}/specgraph_materialization_notes.md"
            notes_text = (
                "# Generated Draft Export Bundle\n\n"
                "This bundle was materialized by SpecGraph from preview and handoff artifacts.\n"
                "Review the placeholder interface surface and complete boundary "
                "details before publication.\n"
            )
            notes_path = bundle_root / notes_relpath
            notes_path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(notes_path, notes_text)
            written_files.append(notes_relpath)
            evidence_entries.append(
                {
                    "id": "materialization_notes",
                    "kind": "manual_assertion",
                    "path": notes_relpath,
                    "supports": ["intent.summary"],
                }
            )

            manifest_text = render_yaml_document(copy.deepcopy(package_preview))
            manifest_path = bundle_root / manifest_relpath
            manifest_path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(manifest_path, manifest_text)
            written_files.append(manifest_relpath)

            boundary_spec = build_specpm_boundary_spec(raw_entry, evidence_entries=evidence_entries)
            boundary_text = render_yaml_document(boundary_spec)
            boundary_path = bundle_root / boundary_spec_relpath
            boundary_path.parent.mkdir(parents=True, exist_ok=True)
            atomic_write_text(boundary_path, boundary_text)
            written_files.append(boundary_spec_relpath)

            sidecar_path = bundle_root / handoff_sidecar_relpath
            sidecar_path.parent.mkdir(parents=True, exist_ok=True)
            sidecar_payload = {
                "materialized_at": utc_now_iso(),
                "export_id": export_id,
                "handoff_id": str(raw_entry.get("handoff_id", "")).strip(),
                "handoff_status": handoff_status,
                "consumer_id": consumer_id,
                "package_identity": copy.deepcopy(package_identity),
                "source_handoff_artifact": (
                    specpm_handoff_packets_path().relative_to(ROOT).as_posix()
                ),
            }
            atomic_write_json(sidecar_path, sidecar_payload)
            written_files.append(handoff_sidecar_relpath)

            if handoff_status == "ready_for_handoff":
                status = "materialized_for_review"
                review_state = "materialized_for_review"
            else:
                status = "draft_materialized"
                review_state = "draft_materialized"
            next_gap = derive_specpm_materialization_next_gap(
                status=status,
                handoff_entry=raw_entry,
            )

        entry = {
            "export_id": export_id,
            "handoff_id": str(raw_entry.get("handoff_id", "")).strip(),
            "consumer_id": consumer_id,
            "materialization_status": status,
            "review_state": review_state,
            "next_gap": next_gap,
            "bundle_root": bundle_root_text,
            "written_files": sorted(set(written_files)),
            "copied_evidence_refs": sorted(set(copied_evidence_refs)),
            "missing_evidence_refs": sorted(set(missing_evidence_refs)),
            "policy_reference": specpm_materialization_policy_reference(),
            "source_handoff": {
                "artifact_path": specpm_handoff_packets_path().relative_to(ROOT).as_posix(),
                "generated_at": specpm_handoff_packets.get("generated_at"),
                "handoff_status": handoff_status,
            },
            "target_consumer": copy.deepcopy(target_consumer),
            "package_identity": copy.deepcopy(package_identity),
        }
        entries.append(entry)
        status_groups.setdefault(status, []).append(export_id)
        review_state_groups.setdefault(review_state, []).append(export_id)
        named_filters.setdefault(status, []).append(export_id)
        if copied_evidence_refs:
            named_filters["evidence_copied"].append(export_id)
        if next_gap != "none":
            backlog_items.append(
                {
                    "export_id": export_id,
                    "materialization_status": status,
                    "review_state": review_state,
                    "next_gap": next_gap,
                }
            )
            grouped_backlog.setdefault(next_gap, []).append(export_id)

    for bucket in (status_groups, review_state_groups, named_filters, grouped_backlog):
        for key in list(bucket):
            bucket[key] = sorted(set(bucket[key]))

    return {
        "artifact_kind": SPECPM_MATERIALIZATION_REPORT_ARTIFACT_KIND,
        "schema_version": SPECPM_MATERIALIZATION_REPORT_SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "policy_reference": specpm_materialization_policy_reference(),
        "source_artifacts": {
            "specpm_handoff_packets": {
                "artifact_path": specpm_handoff_packets_path().relative_to(ROOT).as_posix(),
                "generated_at": specpm_handoff_packets.get("generated_at"),
            }
        },
        "entry_count": len(entries),
        "entries": entries,
        "viewer_projection": {
            "materialization_status": {
                key: sorted(value) for key, value in sorted(status_groups.items())
            },
            "review_state": {
                key: sorted(value) for key, value in sorted(review_state_groups.items())
            },
            "named_filters": {key: sorted(value) for key, value in sorted(named_filters.items())},
        },
        "materialization_backlog": {
            "entry_count": len(backlog_items),
            "items": backlog_items,
            "grouped_by_next_gap": {
                key: sorted(value) for key, value in sorted(grouped_backlog.items())
            },
        },
    }


def write_specpm_materialization_report(report: dict[str, Any]) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = specpm_materialization_report_path()
    with artifact_lock(path):
        atomic_write_json(path, report)
    return path


def load_yaml_object_report(
    path: Path,
    *,
    label: str,
    required_kind: str | None = None,
) -> tuple[dict[str, Any] | None, list[str]]:
    if yaml is None:
        raise RuntimeError("PyYAML is required to read SpecPM import bundles")
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None, [f"unreadable_{label}"]
    try:
        payload = yaml.safe_load(text) or {}
    except yaml.YAMLError:
        return None, [f"malformed_{label}"]
    if not isinstance(payload, dict):
        return None, [f"invalid_{label}_shape"]
    errors: list[str] = []
    if required_kind and str(payload.get("kind", "")).strip() != required_kind:
        errors.append(f"wrong_{label}_kind")
    return payload, errors


def load_json_object_preview_report(
    path: Path,
    *,
    label: str,
) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None, [f"unreadable_{label}"]
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None, [f"malformed_{label}"]
    if not isinstance(payload, dict):
        return None, [f"invalid_{label}_shape"]
    return payload, []


def derive_specpm_import_next_gap(
    *,
    import_status: str,
    checkout_status: str,
    identity_verified: bool,
    missing_files: list[str],
) -> str:
    if import_status == "blocked_by_bundle_gap":
        required_checkout_status = str(
            specpm_import_policy_lookup("consumer_contract.required_checkout_status")
        ).strip()
        require_verified_identity = bool(
            specpm_import_policy_lookup("consumer_contract.require_verified_identity")
        )
        if checkout_status != required_checkout_status:
            return "repair_specpm_checkout"
        if require_verified_identity and not identity_verified:
            return "verify_specpm_checkout_identity"
        if missing_files:
            return "repair_specpm_bundle"
    default_gap = str(specpm_import_policy_lookup(f"next_gap_defaults.{import_status}")).strip()
    return default_gap or "none"


def build_specpm_import_preview(
    external_consumer_index: dict[str, Any] | None = None,
) -> dict[str, Any]:
    consumer_index = (
        copy.deepcopy(external_consumer_index)
        if isinstance(external_consumer_index, dict)
        else build_external_consumer_index()
    )
    consumer_entries = {
        str(entry.get("consumer_id", "")).strip(): entry
        for entry in consumer_index.get("entries", [])
        if isinstance(entry, dict) and str(entry.get("consumer_id", "")).strip()
    }
    required_consumer_id = str(
        specpm_import_policy_lookup("consumer_contract.required_consumer_id")
    ).strip()
    required_profile = str(
        specpm_import_policy_lookup("consumer_contract.required_profile")
    ).strip()
    required_checkout_status = str(
        specpm_import_policy_lookup("consumer_contract.required_checkout_status")
    ).strip()
    require_verified_identity = bool(
        specpm_import_policy_lookup("consumer_contract.require_verified_identity")
    )
    required_files = [
        str(item).strip()
        for item in specpm_import_policy_lookup("bundle_contract.required_files")
        if str(item).strip()
    ]
    required_manifest_kind = str(
        specpm_import_policy_lookup("bundle_contract.required_manifest_kind")
    ).strip()
    required_boundary_kind = str(
        specpm_import_policy_lookup("bundle_contract.required_boundary_kind")
    ).strip()
    consumer_inbox_root = str(
        specpm_import_policy_lookup("repository_layout.consumer_inbox_root")
    ).strip()
    target_kind_mapping = specpm_import_policy_lookup("suggested_target_kind_mapping")

    consumer_entry = consumer_entries.get(required_consumer_id, {})
    target_profile = str(consumer_entry.get("profile", "")).strip()
    local_checkout = consumer_entry.get("local_checkout", {})
    checkout_path = ""
    checkout_status = ""
    identity_verified = False
    if isinstance(local_checkout, dict):
        checkout_path = str(local_checkout.get("checkout_path", "")).strip()
        checkout_status = str(local_checkout.get("status", "")).strip()
        identity_verified = local_checkout.get("remote_matches") is True
    if not checkout_path:
        checkout_path = str(consumer_entry.get("local_checkout_hint", "")).strip()
    if not checkout_status:
        checkout_status = "missing" if not checkout_path else ""
    checkout_root = Path(checkout_path).expanduser() if checkout_path else None
    inbox_root = checkout_root / consumer_inbox_root if checkout_root is not None else None
    bundle_dirs: list[Path] = []
    if inbox_root is not None and inbox_root.exists() and inbox_root.is_dir():
        for child in sorted(inbox_root.iterdir(), key=lambda item: item.name):
            if not child.is_dir():
                continue
            try:
                child.resolve().relative_to(inbox_root.resolve())
            except ValueError:
                continue
            bundle_dirs.append(child)

    source_next_gap = "none"
    if not consumer_entry or target_profile != required_profile:
        source_next_gap = "repair_external_consumer_registry"
    elif checkout_status != required_checkout_status:
        source_next_gap = "repair_specpm_checkout"
    elif require_verified_identity and not identity_verified:
        source_next_gap = "verify_specpm_checkout_identity"
    elif inbox_root is None or not inbox_root.exists():
        source_next_gap = "materialize_specpm_export_bundle"
    elif not bundle_dirs:
        source_next_gap = "materialize_specpm_export_bundle"

    entries: list[dict[str, Any]] = []
    import_status_groups: dict[str, list[str]] = {}
    review_state_groups: dict[str, list[str]] = {}
    suggested_target_groups: dict[str, list[str]] = {}
    named_filters = {name: [] for name in SPECPM_IMPORT_PREVIEW_NAMED_FILTERS}
    backlog_items: list[dict[str, Any]] = []
    grouped_backlog: dict[str, list[str]] = {}

    for bundle_root in bundle_dirs:
        bundle_id = bundle_root.name
        normalized_bundle_id = normalize_specpm_materialization_package_id(bundle_id)
        manifest_path = bundle_root / "specpm.yaml"
        boundary_spec_path = bundle_root / "specs" / "main.spec.yaml"
        handoff_path = bundle_root / "handoff.json"
        evidence_root_path = bundle_root / "evidence" / "source"

        contract_errors: list[str] = []
        missing_files: list[str] = []
        if normalized_bundle_id != bundle_id:
            contract_errors.append("invalid_bundle_directory_name")
        if not consumer_entry:
            contract_errors.append("missing_external_consumer")
        if str(consumer_entry.get("consumer_id", "")).strip() != required_consumer_id:
            contract_errors.append("wrong_consumer_id")
        if target_profile != required_profile:
            contract_errors.append("wrong_consumer_profile")

        required_file_paths = {
            "specpm.yaml": manifest_path,
            "specs/main.spec.yaml": boundary_spec_path,
            "handoff.json": handoff_path,
        }
        for relpath in required_files:
            if not required_file_paths[relpath].exists():
                missing_files.append(relpath)

        manifest_payload = None
        boundary_payload = None
        handoff_payload = None
        if "specpm.yaml" not in missing_files:
            manifest_payload, manifest_errors = load_yaml_object_report(
                manifest_path,
                label="manifest",
                required_kind=required_manifest_kind,
            )
            contract_errors.extend(manifest_errors)
        if "specs/main.spec.yaml" not in missing_files:
            boundary_payload, boundary_errors = load_yaml_object_report(
                boundary_spec_path,
                label="boundary_spec",
                required_kind=required_boundary_kind,
            )
            contract_errors.extend(boundary_errors)
        if "handoff.json" not in missing_files:
            handoff_payload, handoff_errors = load_json_object_preview_report(
                handoff_path,
                label="handoff",
            )
            contract_errors.extend(handoff_errors)

        manifest_metadata = (
            manifest_payload.get("metadata", {}) if isinstance(manifest_payload, dict) else {}
        )
        boundary_metadata = (
            boundary_payload.get("metadata", {}) if isinstance(boundary_payload, dict) else {}
        )
        package_id = str(manifest_metadata.get("id", "")).strip()
        package_name = str(manifest_metadata.get("name", "")).strip()
        package_version = str(manifest_metadata.get("version", "")).strip()
        boundary_spec_id = str(boundary_metadata.get("id", "")).strip()
        boundary_title = str(boundary_metadata.get("title", "")).strip()

        provides_capabilities: list[str] = []
        if isinstance(boundary_payload, dict):
            for raw_item in boundary_payload.get("provides", {}).get("capabilities", []):
                if not isinstance(raw_item, dict):
                    continue
                capability_id = str(raw_item.get("id", "")).strip()
                if capability_id and capability_id not in provides_capabilities:
                    provides_capabilities.append(capability_id)

        handoff_package_identity = (
            handoff_payload.get("package_identity", {}) if isinstance(handoff_payload, dict) else {}
        )
        handoff_package_id = str(handoff_package_identity.get("package_id", "")).strip()
        handoff_consumer_id = str(
            handoff_payload.get("consumer_id", "") if isinstance(handoff_payload, dict) else ""
        ).strip()
        handoff_status = str(
            handoff_payload.get("handoff_status", "") if isinstance(handoff_payload, dict) else ""
        ).strip()
        source_export_id = str(
            handoff_payload.get("export_id", "") if isinstance(handoff_payload, dict) else ""
        ).strip()
        source_handoff_id = str(
            handoff_payload.get("handoff_id", "") if isinstance(handoff_payload, dict) else ""
        ).strip()
        source_handoff_artifact = str(
            handoff_payload.get("source_handoff_artifact", "")
            if isinstance(handoff_payload, dict)
            else ""
        ).strip()

        if manifest_payload is not None and not package_id:
            contract_errors.append("missing_manifest_package_id")
        if boundary_payload is not None and not boundary_spec_id:
            contract_errors.append("missing_boundary_spec_id")
        if handoff_payload is not None and not handoff_status:
            contract_errors.append("missing_handoff_status")
        if handoff_payload is not None and handoff_consumer_id != required_consumer_id:
            contract_errors.append("handoff_consumer_id_mismatch")
        if package_id and normalized_bundle_id and package_id != normalized_bundle_id:
            contract_errors.append("manifest_package_id_mismatch")
        if handoff_package_id and package_id and handoff_package_id != package_id:
            contract_errors.append("handoff_package_id_mismatch")
        if handoff_payload is not None and not handoff_package_id:
            contract_errors.append("missing_handoff_package_id")
        if handoff_status and handoff_status not in {"ready_for_handoff", "draft_preview_only"}:
            contract_errors.append("unknown_handoff_status")

        import_status = "invalid_import_contract"
        review_state = "not_ready"
        if contract_errors:
            import_status = "invalid_import_contract"
        elif (
            checkout_status != required_checkout_status
            or (require_verified_identity and not identity_verified)
            or missing_files
        ):
            import_status = "blocked_by_bundle_gap"
        elif handoff_status == "ready_for_handoff":
            import_status = "ready_for_review"
            review_state = "ready_for_review"
        else:
            import_status = "draft_visible"
            review_state = "draft_visible"

        next_gap = derive_specpm_import_next_gap(
            import_status=import_status,
            checkout_status=checkout_status,
            identity_verified=identity_verified,
            missing_files=missing_files,
        )
        suggested_target_kind = str(target_kind_mapping.get(import_status, "")).strip()
        handoff_continuous = (
            handoff_payload is not None
            and not contract_errors
            and not missing_files
            and handoff_consumer_id == required_consumer_id
            and bool(source_handoff_id)
        )

        entry = {
            "bundle_id": bundle_id,
            "bundle_root": bundle_root.as_posix(),
            "consumer_id": required_consumer_id,
            "import_status": import_status,
            "review_state": review_state,
            "next_gap": next_gap,
            "suggested_target_kind": suggested_target_kind,
            "policy_reference": specpm_import_policy_reference(),
            "target_consumer": {
                "consumer_id": str(consumer_entry.get("consumer_id", "")).strip()
                or required_consumer_id,
                "title": str(consumer_entry.get("title", "")).strip() or required_consumer_id,
                "profile": target_profile,
                "repo_url": str(consumer_entry.get("repo_url", "")).strip(),
                "local_checkout_hint": checkout_path,
                "checkout_status": checkout_status,
                "identity_verified": identity_verified,
            },
            "bundle_sources": {
                "manifest_path": manifest_path.as_posix(),
                "boundary_spec_path": boundary_spec_path.as_posix(),
                "handoff_path": handoff_path.as_posix(),
                "evidence_root_path": evidence_root_path.as_posix(),
            },
            "missing_files": sorted(set(missing_files)),
            "contract_errors": sorted(set(contract_errors)),
            "manifest_summary": {
                "package_id": package_id,
                "package_name": package_name,
                "package_version": package_version,
                "summary": str(manifest_metadata.get("summary", "")).strip(),
            },
            "boundary_summary": {
                "boundary_spec_id": boundary_spec_id,
                "boundary_title": boundary_title,
                "bounded_context": (
                    str(boundary_payload.get("scope", {}).get("boundedContext", "")).strip()
                    if isinstance(boundary_payload, dict)
                    else ""
                ),
                "provides_capabilities": provides_capabilities,
            },
            "handoff_continuity": {
                "handoff_present": handoff_payload is not None,
                "continuous": handoff_continuous,
                "handoff_status": handoff_status,
                "source_export_id": source_export_id,
                "source_handoff_id": source_handoff_id,
                "source_handoff_artifact": source_handoff_artifact,
                "consumer_id_matches": handoff_consumer_id == required_consumer_id,
                "bundle_id_matches_manifest": bool(package_id)
                and package_id == normalized_bundle_id,
                "bundle_id_matches_handoff": bool(handoff_package_id)
                and handoff_package_id == normalized_bundle_id,
            },
        }
        entries.append(entry)
        import_status_groups.setdefault(import_status, []).append(bundle_id)
        review_state_groups.setdefault(review_state, []).append(bundle_id)
        if suggested_target_kind:
            suggested_target_groups.setdefault(suggested_target_kind, []).append(bundle_id)
        named_filters.setdefault(import_status, []).append(bundle_id)
        if handoff_continuous:
            named_filters["handoff_continuous"].append(bundle_id)
        if manifest_payload is not None:
            named_filters["manifest_present"].append(bundle_id)
        if boundary_payload is not None:
            named_filters["boundary_spec_present"].append(bundle_id)
        if next_gap != "none":
            backlog_items.append(
                {
                    "bundle_id": bundle_id,
                    "import_status": import_status,
                    "review_state": review_state,
                    "next_gap": next_gap,
                }
            )
            grouped_backlog.setdefault(next_gap, []).append(bundle_id)

    for bucket in (
        import_status_groups,
        review_state_groups,
        suggested_target_groups,
        named_filters,
        grouped_backlog,
    ):
        for key in list(bucket):
            bucket[key] = sorted(set(bucket[key]))

    return {
        "artifact_kind": SPECPM_IMPORT_PREVIEW_ARTIFACT_KIND,
        "schema_version": SPECPM_IMPORT_PREVIEW_SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "policy_reference": specpm_import_policy_reference(),
        "source_artifacts": {
            "external_consumer_index": {
                "artifact_path": external_consumer_index_path().relative_to(ROOT).as_posix(),
                "generated_at": consumer_index.get("generated_at"),
            }
        },
        "import_source": {
            "consumer_id": required_consumer_id,
            "profile": target_profile,
            "checkout_path": checkout_path,
            "checkout_status": checkout_status,
            "identity_verified": identity_verified,
            "inbox_root": inbox_root.as_posix() if inbox_root is not None else "",
            "bundle_count": len(entries),
            "next_gap": source_next_gap,
        },
        "entry_count": len(entries),
        "entries": entries,
        "viewer_projection": {
            "import_status": {
                key: sorted(value) for key, value in sorted(import_status_groups.items())
            },
            "review_state": {
                key: sorted(value) for key, value in sorted(review_state_groups.items())
            },
            "suggested_target_kind": {
                key: sorted(value) for key, value in sorted(suggested_target_groups.items())
            },
            "named_filters": {key: sorted(value) for key, value in sorted(named_filters.items())},
        },
        "import_backlog": {
            "entry_count": len(backlog_items),
            "items": backlog_items,
            "grouped_by_next_gap": {
                key: sorted(value) for key, value in sorted(grouped_backlog.items())
            },
        },
    }


def write_specpm_import_preview(report: dict[str, Any]) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = specpm_import_preview_path()
    with artifact_lock(path):
        atomic_write_json(path, report)
    return path


def metric_status_score(mapping: dict[str, Any], status: str) -> float | None:
    raw_value = mapping.get(status)
    if raw_value is None:
        return None
    try:
        return float(raw_value)
    except (TypeError, ValueError):
        return None


def average_metric_scores(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 3)


def weighted_metric_average(
    component_scores: dict[str, float | None],
    weights: dict[str, Any],
) -> float | None:
    weighted_total = 0.0
    weight_total = 0.0
    for metric_id, raw_weight in weights.items():
        score = component_scores.get(metric_id)
        if score is None:
            continue
        try:
            weight = float(raw_weight)
        except (TypeError, ValueError):
            continue
        if weight <= 0:
            continue
        weighted_total += score * weight
        weight_total += weight
    if weight_total <= 0:
        return None
    return round(weighted_total / weight_total, 3)


def metric_status_from_score(score: float | None, threshold: float) -> str:
    if score is None:
        return "not_applicable"
    return "healthy" if score >= threshold else "below_threshold"


def metric_gap_from_threshold(score: float | None, threshold: float) -> float | None:
    if score is None:
        return None
    return round(threshold - score, 3)


def metric_threshold_definition(metric_id: str) -> dict[str, Any]:
    return copy.deepcopy(metric_signal_policy_lookup(f"metric_thresholds.{metric_id}"))


def metric_signal_mapping(signal_name: str) -> dict[str, Any]:
    return copy.deepcopy(metric_signal_policy_lookup(f"proposal_mapping.{signal_name}"))


def build_metric_signal_index(specs: list[SpecNode]) -> dict[str, Any]:
    trace_index = build_spec_trace_index(specs)
    trace_projection = build_spec_trace_projection(trace_index)
    evidence_index = build_evidence_plane_index(specs)
    evidence_overlay = build_evidence_plane_overlay(evidence_index)
    external_consumer_index = build_external_consumer_index()
    graph_overlay = build_graph_health_overlay(specs)
    graph_trends = build_graph_health_trends(specs, overlay=graph_overlay)
    proposal_runtime_index = build_proposal_runtime_index()

    acceptance_score_map = copy.deepcopy(
        metric_signal_policy_lookup("status_scoring.acceptance_coverage")
    )
    proposal_observation_score_map = copy.deepcopy(
        metric_signal_policy_lookup("status_scoring.proposal_observation")
    )
    evidence_chain_score_map = copy.deepcopy(
        metric_signal_policy_lookup("status_scoring.evidence_chain")
    )
    external_consumer_score_map = copy.deepcopy(
        metric_signal_policy_lookup("status_scoring.external_consumer_contract")
    )
    sib_weights = copy.deepcopy(metric_signal_policy_lookup("metric_composition.sib_proxy_weights"))

    metrics_by_id: dict[str, dict[str, Any]] = {}

    acceptance_status_counts: dict[str, int] = {}
    acceptance_scores: list[float] = []
    acceptance_relevant_count = 0
    for entry in trace_index.get("entries", []):
        if not isinstance(entry, dict):
            continue
        coverage = entry.get("acceptance_coverage", {})
        if not isinstance(coverage, dict):
            continue
        status = str(coverage.get("status", "")).strip()
        if not status or status == "not_defined":
            continue
        acceptance_relevant_count += 1
        acceptance_status_counts[status] = acceptance_status_counts.get(status, 0) + 1
        score = metric_status_score(acceptance_score_map, status)
        if score is not None:
            acceptance_scores.append(score)

    spec_verifiability_threshold = float(
        metric_threshold_definition("specification_verifiability")["minimum_score"]
    )
    spec_verifiability_score = average_metric_scores(acceptance_scores)
    spec_verifiability_status = metric_status_from_score(
        spec_verifiability_score,
        spec_verifiability_threshold,
    )
    spec_verifiability_signal = str(
        metric_threshold_definition("specification_verifiability")["trigger_signal"]
    )
    metrics_by_id["specification_verifiability"] = {
        "metric_id": "specification_verifiability",
        "title": "Specification Verifiability",
        "score": spec_verifiability_score,
        "minimum_score": spec_verifiability_threshold,
        "threshold_gap": metric_gap_from_threshold(
            spec_verifiability_score,
            spec_verifiability_threshold,
        ),
        "status": spec_verifiability_status,
        "trigger_signal": spec_verifiability_signal,
        "signal_emitted": spec_verifiability_status == "below_threshold",
        "basis": (
            "Derived from acceptance coverage in the trace plane. This remains a weak bootstrap "
            "measure until criterion-level evidence mapping exists."
        ),
        "input_summary": {
            "relevant_spec_count": acceptance_relevant_count,
            "acceptance_status_counts": {
                key: acceptance_status_counts[key] for key in sorted(acceptance_status_counts)
            },
        },
    }

    proposal_status_counts: dict[str, int] = {}
    proposal_scores: list[float] = []
    proposal_relevant_count = 0
    for entry in proposal_runtime_index.get("entries", []):
        if not isinstance(entry, dict):
            continue
        posture = str(entry.get("posture", "")).strip()
        if posture in {"document_only", "deferred_until_canonicalized"}:
            continue
        observation = entry.get("observation_coverage", {})
        if not isinstance(observation, dict):
            continue
        status = str(observation.get("status", "")).strip()
        if not status:
            continue
        proposal_relevant_count += 1
        proposal_status_counts[status] = proposal_status_counts.get(status, 0) + 1
        score = metric_status_score(proposal_observation_score_map, status)
        if score is not None:
            proposal_scores.append(score)

    evidence_chain_counts: dict[str, int] = {}
    evidence_scores: list[float] = []
    evidence_relevant_count = 0
    for entry in evidence_index.get("entries", []):
        if not isinstance(entry, dict):
            continue
        chain_status = str(entry.get("chain_status", "")).strip()
        if not chain_status or chain_status == "untracked":
            continue
        evidence_relevant_count += 1
        evidence_chain_counts[chain_status] = evidence_chain_counts.get(chain_status, 0) + 1
        score = metric_status_score(evidence_chain_score_map, chain_status)
        if score is not None:
            evidence_scores.append(score)

    process_observability_components = {
        "proposal_observation": average_metric_scores(proposal_scores),
        "evidence_chain": average_metric_scores(evidence_scores),
    }
    process_observability_score = average_metric_scores(
        [score for score in process_observability_components.values() if score is not None]
    )
    process_observability_threshold = float(
        metric_threshold_definition("process_observability")["minimum_score"]
    )
    process_observability_status = metric_status_from_score(
        process_observability_score,
        process_observability_threshold,
    )
    process_observability_signal = str(
        metric_threshold_definition("process_observability")["trigger_signal"]
    )
    metrics_by_id["process_observability"] = {
        "metric_id": "process_observability",
        "title": "Process Observability",
        "score": process_observability_score,
        "minimum_score": process_observability_threshold,
        "threshold_gap": metric_gap_from_threshold(
            process_observability_score,
            process_observability_threshold,
        ),
        "status": process_observability_status,
        "trigger_signal": process_observability_signal,
        "signal_emitted": process_observability_status == "below_threshold",
        "basis": (
            "Derived from proposal observation coverage and runtime evidence chain completion. "
            "This measures how reviewable the observe->propose->improve loop currently is."
        ),
        "input_summary": {
            "proposal_relevant_count": proposal_relevant_count,
            "proposal_observation_status_counts": {
                key: proposal_status_counts[key] for key in sorted(proposal_status_counts)
            },
            "evidence_relevant_count": evidence_relevant_count,
            "evidence_chain_status_counts": {
                key: evidence_chain_counts[key] for key in sorted(evidence_chain_counts)
            },
            "component_scores": copy.deepcopy(process_observability_components),
        },
    }

    total_specs = len(specs)
    active_pressure_specs = {
        str(entry.get("spec_id", "")).strip()
        for entry in graph_overlay.get("entries", [])
        if isinstance(entry, dict)
        and str(entry.get("spec_id", "")).strip()
        and any(str(item).strip() for item in entry.get("signals", []) if str(item).strip())
    }
    persistent_pressure_specs = {
        str(entry.get("spec_id", "")).strip()
        for entry in graph_trends.get("entries", [])
        if isinstance(entry, dict)
        and str(entry.get("spec_id", "")).strip()
        and str(entry.get("trend_status", "")).strip() == "persistent"
        and bool(entry.get("currently_active"))
    }
    active_pressure_ratio = (
        round(len(active_pressure_specs) / total_specs, 3) if total_specs > 0 else None
    )
    persistent_pressure_ratio = (
        round(len(persistent_pressure_specs) / total_specs, 3) if total_specs > 0 else None
    )
    structural_observability_score = None
    if total_specs > 0:
        structural_observability_score = round(
            max(
                0.0,
                1.0
                - (
                    (float(active_pressure_ratio or 0.0) * 0.6)
                    + (float(persistent_pressure_ratio or 0.0) * 0.4)
                ),
            ),
            3,
        )
    structural_observability_threshold = float(
        metric_threshold_definition("structural_observability")["minimum_score"]
    )
    structural_observability_status = metric_status_from_score(
        structural_observability_score,
        structural_observability_threshold,
    )
    structural_observability_signal = str(
        metric_threshold_definition("structural_observability")["trigger_signal"]
    )
    metrics_by_id["structural_observability"] = {
        "metric_id": "structural_observability",
        "title": "Structural Observability",
        "score": structural_observability_score,
        "minimum_score": structural_observability_threshold,
        "threshold_gap": metric_gap_from_threshold(
            structural_observability_score,
            structural_observability_threshold,
        ),
        "status": structural_observability_status,
        "trigger_signal": structural_observability_signal,
        "signal_emitted": structural_observability_status == "below_threshold",
        "basis": (
            "Derived from current graph-health pressure and persistent recurring structural "
            "signals. This is advisory and should not be treated as a canonical graph fact."
        ),
        "input_summary": {
            "spec_count": total_specs,
            "active_pressure_spec_count": len(active_pressure_specs),
            "persistent_pressure_spec_count": len(persistent_pressure_specs),
            "active_pressure_ratio": active_pressure_ratio,
            "persistent_pressure_ratio": persistent_pressure_ratio,
            "active_named_filters": copy.deepcopy(
                graph_overlay.get("viewer_projection", {}).get("named_filters", {})
            ),
            "recurring_named_filters": copy.deepcopy(
                graph_trends.get("viewer_projection", {}).get("named_filters", {})
            ),
        },
    }

    stable_bridge_entries = [
        entry
        for entry in external_consumer_index.get("entries", [])
        if isinstance(entry, dict)
        and str(entry.get("reference_state", "")).strip() == "stable_reference"
        and any(
            isinstance(binding, dict) and str(binding.get("metric_id", "")).strip() == "sib_proxy"
            for binding in entry.get("metric_bindings", [])
        )
    ]
    draft_bridge_entries = [
        entry
        for entry in external_consumer_index.get("entries", [])
        if isinstance(entry, dict)
        and str(entry.get("reference_state", "")).strip() == "draft_reference"
        and any(
            isinstance(binding, dict) and str(binding.get("metric_id", "")).strip() == "sib_proxy"
            for binding in entry.get("metric_bindings", [])
        )
    ]
    bridge_ready_entries = [
        entry
        for entry in stable_bridge_entries
        if str(entry.get("local_checkout", {}).get("status", "")).strip() == "available"
        and entry.get("local_checkout", {}).get("remote_matches") is True
        and str(entry.get("contract_status", "")).strip() in {"ready", "partial"}
    ]
    bridge_alignment_scores: list[float] = []
    for entry in bridge_ready_entries:
        score = metric_status_score(
            external_consumer_score_map,
            str(entry.get("contract_status", "")).strip(),
        )
        if score is not None:
            bridge_alignment_scores.append(score)
    external_consumer_alignment = average_metric_scores(bridge_alignment_scores)
    sib_component_scores = {
        "specification_verifiability": metrics_by_id["specification_verifiability"]["score"],
        "process_observability": metrics_by_id["process_observability"]["score"],
        "structural_observability": metrics_by_id["structural_observability"]["score"],
        "external_consumer_alignment": external_consumer_alignment,
    }
    sib_derivation_mode = (
        "bridge_backed" if external_consumer_alignment is not None else "bootstrap_fallback"
    )
    sib_proxy_score = weighted_metric_average(sib_component_scores, sib_weights)
    sib_proxy_threshold = float(metric_threshold_definition("sib_proxy")["minimum_score"])
    sib_proxy_status = metric_status_from_score(sib_proxy_score, sib_proxy_threshold)
    sib_proxy_signal = str(metric_threshold_definition("sib_proxy")["trigger_signal"])
    metrics_by_id["sib_proxy"] = {
        "metric_id": "sib_proxy",
        "title": "SIB Proxy",
        "score": sib_proxy_score,
        "minimum_score": sib_proxy_threshold,
        "threshold_gap": metric_gap_from_threshold(sib_proxy_score, sib_proxy_threshold),
        "status": sib_proxy_status,
        "trigger_signal": sib_proxy_signal,
        "signal_emitted": sib_proxy_status == "below_threshold",
        "derivation_mode": sib_derivation_mode,
        "basis": (
            "Bridge-backed bootstrap composite anchored by the stable external Metrics/SIB "
            "consumer when available."
            if sib_derivation_mode == "bridge_backed"
            else (
                "Bootstrap composite from specification verifiability, process observability, "
                "and structural observability. This remains the fallback until a stable "
                "external Metrics/SIB bridge is locally available."
            )
        ),
        "input_summary": {
            "component_scores": copy.deepcopy(sib_component_scores),
            "component_weights": copy.deepcopy(sib_weights),
            "stable_bridge_consumer_ids": [
                str(entry.get("consumer_id", "")).strip() for entry in stable_bridge_entries
            ],
            "draft_bridge_consumer_ids": [
                str(entry.get("consumer_id", "")).strip() for entry in draft_bridge_entries
            ],
            "bridge_ready_consumer_ids": [
                str(entry.get("consumer_id", "")).strip() for entry in bridge_ready_entries
            ],
            "bridge_unverified_identity_consumer_ids": sorted(
                {
                    str(entry.get("consumer_id", "")).strip()
                    for entry in stable_bridge_entries
                    if str(entry.get("local_checkout", {}).get("status", "")).strip() == "available"
                    and entry.get("local_checkout", {}).get("remote_matches") is not True
                }
            ),
            "bridge_missing_checkout_ids": sorted(
                {
                    str(entry.get("consumer_id", "")).strip()
                    for entry in stable_bridge_entries
                    if str(entry.get("local_checkout", {}).get("status", "")).strip() != "available"
                }
            ),
        },
    }

    metrics = [copy.deepcopy(metrics_by_id[metric_id]) for metric_id in METRIC_SIGNAL_METRIC_IDS]
    status_groups: dict[str, list[str]] = {}
    active_signals: list[str] = []
    named_filters = {name: [] for name in METRIC_SIGNAL_NAMED_FILTERS}
    for entry in metrics:
        metric_id = str(entry["metric_id"])
        status = str(entry["status"])
        status_groups.setdefault(status, []).append(metric_id)
        if entry["signal_emitted"]:
            signal_name = str(entry["trigger_signal"])
            if signal_name:
                active_signals.append(signal_name)
            named_filters["metrics_below_threshold"].append(metric_id)
            if metric_id == "specification_verifiability":
                named_filters["specification_attention"].append(metric_id)
            elif metric_id == "process_observability":
                named_filters["process_attention"].append(metric_id)
            elif metric_id == "structural_observability":
                named_filters["structural_attention"].append(metric_id)
            elif metric_id == "sib_proxy":
                named_filters["sib_attention"].append(metric_id)
        elif status == "healthy":
            named_filters["healthy_metrics"].append(metric_id)

    return {
        "artifact_kind": METRIC_SIGNAL_INDEX_ARTIFACT_KIND,
        "schema_version": METRIC_SIGNAL_INDEX_SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "policy_reference": metric_signal_policy_reference(),
        "source_artifacts": {
            "spec_trace_index": {
                "artifact_path": spec_trace_index_path().relative_to(ROOT).as_posix(),
                "generated_at": trace_index.get("generated_at"),
            },
            "spec_trace_projection": {
                "artifact_path": spec_trace_projection_path().relative_to(ROOT).as_posix(),
                "generated_at": trace_projection.get("generated_at"),
            },
            "evidence_plane_index": {
                "artifact_path": evidence_plane_index_path().relative_to(ROOT).as_posix(),
                "generated_at": evidence_index.get("generated_at"),
            },
            "evidence_plane_overlay": {
                "artifact_path": evidence_plane_overlay_path().relative_to(ROOT).as_posix(),
                "generated_at": evidence_overlay.get("generated_at"),
            },
            "external_consumer_index": {
                "artifact_path": external_consumer_index_path().relative_to(ROOT).as_posix(),
                "generated_at": external_consumer_index.get("generated_at"),
            },
            "graph_health_overlay": {
                "artifact_path": graph_health_overlay_path().relative_to(ROOT).as_posix(),
                "generated_at": graph_overlay.get("generated_at"),
            },
            "graph_health_trends": {
                "artifact_path": graph_health_trends_path().relative_to(ROOT).as_posix(),
                "generated_at": graph_trends.get("generated_at"),
            },
            "proposal_runtime_index": {
                "artifact_path": proposal_runtime_index_path().relative_to(ROOT).as_posix(),
                "generated_at": proposal_runtime_index.get("generated_at"),
            },
        },
        "entry_count": len(metrics),
        "metrics": metrics,
        "active_signals": sorted(set(active_signals)),
        "viewer_projection": {
            "metric_status": {key: sorted(value) for key, value in sorted(status_groups.items())},
            "active_signals": sorted(set(active_signals)),
            "named_filters": {key: sorted(value) for key, value in sorted(named_filters.items())},
        },
    }


def write_metric_signal_index(index: dict[str, Any]) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = metric_signal_index_path()
    with artifact_lock(path):
        atomic_write_json(path, index)
    return path


def metric_threshold_proposal_severity(score: float | None, threshold: float) -> str:
    gap = metric_gap_from_threshold(score, threshold)
    if gap is None:
        return "low"
    if gap >= 0.25:
        return "high"
    if gap >= 0.1:
        return "medium"
    return "low"


def build_metric_threshold_proposals(signal_index: dict[str, Any]) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    by_kind: dict[str, list[str]] = {}
    by_severity: dict[str, list[str]] = {}
    by_metric: dict[str, list[str]] = {}
    named_filters = {name: [] for name in METRIC_THRESHOLD_PROPOSAL_NAMED_FILTERS}

    for metric in signal_index.get("metrics", []):
        if not isinstance(metric, dict):
            continue
        if str(metric.get("status", "")).strip() != "below_threshold":
            continue

        metric_id = str(metric.get("metric_id", "")).strip()
        trigger_signal = str(metric.get("trigger_signal", "")).strip()
        if not metric_id or not trigger_signal:
            continue
        mapping = metric_signal_mapping(trigger_signal)
        proposal_kind = (
            str(mapping.get("proposal_kind", "")).strip() or "metric_remediation_proposal"
        )
        severity = metric_threshold_proposal_severity(
            metric.get("score"),
            float(metric.get("minimum_score", 0.0)),
        )
        proposal_id = f"metric-{metric_id}-followup"
        threshold = float(metric.get("minimum_score", 0.0))
        score = metric.get("score")
        entries.append(
            {
                "proposal_id": proposal_id,
                "proposal_kind": proposal_kind,
                "title": f"Review {metric.get('title', metric_id)} below threshold",
                "metric_id": metric_id,
                "trigger_signal": trigger_signal,
                "severity": severity,
                "score": score,
                "minimum_score": threshold,
                "threshold_gap": metric_gap_from_threshold(score, threshold),
                "policy_mutation_state": "proposal_only",
                "review_intent": "proposal_first_metric_followup",
                "recommended_actions": list(mapping.get("recommended_actions", [])),
                "target_surfaces": list(mapping.get("target_surfaces", [])),
                "proposed_transition": {
                    "transition_profile": "specgraph_core",
                    "packet_type": "proposal",
                    "target_artifact_class": "metric_threshold_followup",
                },
                "basis": (
                    f"{metric.get('title', metric_id)} scored {score} against minimum "
                    f"{threshold}, so the threshold crossing is surfaced as a reviewable "
                    "proposal instead of a direct policy mutation."
                ),
                "metric_summary": {
                    "status": str(metric.get("status", "")).strip(),
                    "input_summary": copy.deepcopy(metric.get("input_summary", {})),
                },
            }
        )
        by_kind.setdefault(proposal_kind, []).append(proposal_id)
        by_severity.setdefault(severity, []).append(proposal_id)
        by_metric.setdefault(metric_id, []).append(proposal_id)
        if proposal_kind == "metric_remediation_proposal":
            named_filters["remediation_proposals"].append(proposal_id)
        else:
            named_filters["threshold_review_proposals"].append(proposal_id)
        if severity in {"high", "medium", "low"}:
            named_filters[f"{severity}_severity"].append(proposal_id)

    return {
        "artifact_kind": METRIC_THRESHOLD_PROPOSALS_ARTIFACT_KIND,
        "schema_version": METRIC_THRESHOLD_PROPOSALS_SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "policy_reference": metric_signal_policy_reference(),
        "source_signal_index_path": metric_signal_index_path().relative_to(ROOT).as_posix(),
        "source_signal_generated_at": signal_index.get("generated_at"),
        "entry_count": len(entries),
        "entries": entries,
        "viewer_projection": {
            "proposal_kind": {key: sorted(value) for key, value in sorted(by_kind.items())},
            "severity": {key: sorted(value) for key, value in sorted(by_severity.items())},
            "metric_id": {key: sorted(value) for key, value in sorted(by_metric.items())},
            "named_filters": {key: sorted(value) for key, value in sorted(named_filters.items())},
        },
    }


def write_metric_threshold_proposals(report: dict[str, Any]) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = metric_threshold_proposals_path()
    with artifact_lock(path):
        atomic_write_json(path, report)
    return path


def _iso_or_empty(value: dt.datetime | None) -> str:
    if value is None:
        return ""
    return value.astimezone(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def performance_run_timestamp(payload: dict[str, Any], path: Path) -> dt.datetime | None:
    finished_at = parse_iso_datetime(payload.get("finished_at_utc", ""))
    if finished_at is not None:
        return finished_at
    started_at = parse_iso_datetime(payload.get("started_at_utc", ""))
    if started_at is not None:
        return started_at
    return graph_health_event_timestamp(payload, path)


def performance_run_kind(payload: dict[str, Any]) -> str:
    explicit = str(payload.get("run_kind", "")).strip()
    if explicit:
        return explicit
    selected_by_rule = payload.get("selected_by_rule", {})
    if not isinstance(selected_by_rule, dict):
        selected_by_rule = {}
    selection_mode = str(selected_by_rule.get("selection_mode", "")).strip()
    if selection_mode == "split_refactor_proposal":
        return "split_proposal"
    if selection_mode == "apply_split_proposal":
        return "apply_split_proposal"
    refactor_work_item = selected_by_rule.get("refactor_work_item", {})
    if isinstance(refactor_work_item, dict) and str(refactor_work_item.get("id", "")).strip():
        return "graph_refactor"
    return "ordinary_refine"


def performance_execution_profile(payload: dict[str, Any]) -> str:
    explicit = str(payload.get("execution_profile", "")).strip()
    if explicit:
        return explicit
    selected_by_rule = payload.get("selected_by_rule", {})
    if not isinstance(selected_by_rule, dict):
        return ""
    return str(selected_by_rule.get("execution_profile", "")).strip()


def performance_child_model(payload: dict[str, Any]) -> str:
    return str(payload.get("child_model", "")).strip()


def performance_run_duration_sec(payload: dict[str, Any], path: Path) -> float | None:
    explicit = payload.get("run_duration_sec")
    if isinstance(explicit, (int, float)):
        return round(float(explicit), 3)
    started_at = parse_iso_datetime(payload.get("started_at_utc", ""))
    finished_at = parse_iso_datetime(payload.get("finished_at_utc", ""))
    if started_at is None or finished_at is None:
        return None
    duration = (finished_at - started_at).total_seconds()
    if duration < 0:
        return None
    return round(duration, 3)


def performance_validation_findings(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return coerce_validation_findings(payload.get("validation_findings", []))


def performance_queue_transition(payload: dict[str, Any], queue_name: str) -> dict[str, Any]:
    decision_inspector = payload.get("decision_inspector", {})
    if not isinstance(decision_inspector, dict):
        return {}
    queue_effects = decision_inspector.get("queue_effects", {})
    if not isinstance(queue_effects, dict):
        return {}
    transition = queue_effects.get(queue_name, {})
    if not isinstance(transition, dict):
        return {}
    return transition


def performance_new_child_materialized_count(payload: dict[str, Any]) -> int:
    explicit = payload.get("new_child_materialized_count")
    if isinstance(explicit, int):
        return max(explicit, 0)
    materialized = payload.get("materialized_child_paths", [])
    if isinstance(materialized, list):
        return sum(1 for item in materialized if str(item).strip())
    changed_files = payload.get("changed_files", [])
    spec_id = str(payload.get("spec_id", "")).strip()
    source_path = f"specs/nodes/{spec_id}.yaml" if spec_id else ""
    if not isinstance(changed_files, list):
        return 0
    return sum(
        1
        for item in changed_files
        if is_spec_node_path(str(item).strip()) and str(item).strip() != source_path
    )


def performance_accepted_canonical_diff(payload: dict[str, Any]) -> bool:
    explicit = payload.get("accepted_canonical_diff")
    if isinstance(explicit, bool):
        return explicit
    if performance_run_kind(payload) == "apply_split_proposal":
        validator_results = payload.get("validator_results", {})
        if isinstance(validator_results, dict):
            return bool(validator_results.get("canonical_writeback"))
    if bool(payload.get("auto_approved")):
        return True
    before_status = str(payload.get("before_status", "")).strip()
    final_status = str(payload.get("final_status", "")).strip()
    if before_status and final_status and before_status != final_status:
        return True
    before_maturity = payload.get("before_maturity")
    final_maturity = payload.get("final_maturity")
    if isinstance(before_maturity, (int, float)) and isinstance(final_maturity, (int, float)):
        return float(final_maturity) > float(before_maturity)
    return False


def performance_productive_split_required(payload: dict[str, Any]) -> bool:
    explicit = payload.get("productive_split_required")
    if isinstance(explicit, bool):
        return explicit
    outcome = str(payload.get("outcome", "")).strip()
    changed_files = payload.get("changed_files", [])
    return outcome == "split_required" and isinstance(changed_files, list) and bool(changed_files)


def performance_runtime_status(
    payload: dict[str, Any],
    findings: list[dict[str, Any]],
) -> tuple[str, list[str]]:
    validator_results = payload.get("validator_results", {})
    if not isinstance(validator_results, dict):
        validator_results = {}
    reasons: list[str] = []
    if validator_results.get("executor_environment") is False:
        reasons.append("executor_environment")
    if validator_results.get("runtime_artifacts") is False:
        reasons.append("runtime_artifacts")
    finding_codes = {
        str(finding.get("code", "")).strip()
        for finding in findings
        if str(finding.get("code", "")).strip()
    }
    if "executor_machine_protocol_failure" in finding_codes:
        reasons.append("executor_machine_protocol")
    if reasons:
        return "runtime_failed", sorted(set(reasons))
    yaml_repair_paths = payload.get("yaml_repair_paths", [])
    if isinstance(yaml_repair_paths, list) and any(str(item).strip() for item in yaml_repair_paths):
        return "runtime_degraded", ["yaml_repair_applied"]
    return "runtime_clean", []


def performance_yield_status(
    payload: dict[str, Any],
    *,
    runtime_status: str,
    accepted_canonical_diff: bool,
    productive_split_required: bool,
    proposal_emitted: bool,
    review_required: bool,
    changed_files: list[str],
) -> tuple[str, bool]:
    if runtime_status == "runtime_failed":
        return "runtime_blocked", False
    if accepted_canonical_diff:
        return "accepted_change", True
    if proposal_emitted:
        return "proposal_emitted", True
    if productive_split_required:
        return "productive_split_required", True
    if review_required and changed_files:
        return "review_pending_candidate", True
    return "low_yield", False


def performance_graph_impact_status(
    *,
    runtime_status: str,
    yield_status: str,
    before_status: str,
    final_status: str,
    before_maturity: float | None,
    final_maturity: float | None,
    new_child_materialized_count: int,
    gate_state: str,
) -> str:
    maturity_increased = (
        before_maturity is not None
        and final_maturity is not None
        and float(final_maturity) > float(before_maturity)
    )
    if yield_status == "accepted_change" and (
        before_status != final_status or maturity_increased or new_child_materialized_count > 0
    ):
        return "canonical_improvement"
    if yield_status == "proposal_emitted":
        return "proposal_only"
    if yield_status == "review_pending_candidate":
        return "pending_review"
    if yield_status == "productive_split_required":
        return "structural_pressure"
    if (
        runtime_status == "runtime_failed"
        or gate_state in SUPERVISOR_PERFORMANCE_BLOCKED_GATE_STATES
    ):
        return "blocked_or_regressed"
    return "neutral"


def build_supervisor_performance_index() -> dict[str, Any]:
    grouped_runtime_status: dict[str, list[str]] = {}
    grouped_yield_status: dict[str, list[str]] = {}
    grouped_graph_impact_status: dict[str, list[str]] = {}
    grouped_run_kind: dict[str, list[str]] = {}
    grouped_execution_profile: dict[str, list[str]] = {}
    named_filters = {name: [] for name in SUPERVISOR_PERFORMANCE_NAMED_FILTERS}
    entries: list[dict[str, Any]] = []
    run_logs_scanned = 0
    skipped_invalid_run_logs: list[dict[str, str]] = []

    run_records: list[tuple[dt.datetime | None, Path, dict[str, Any]]] = []
    for path in run_log_paths():
        payload, error = load_json_object_report(path, artifact_kind="run log")
        if payload is None:
            skipped_invalid_run_logs.append(
                {
                    "path": path.relative_to(ROOT).as_posix(),
                    "error": error,
                }
            )
            continue
        run_logs_scanned += 1
        run_records.append((performance_run_timestamp(payload, path), path, payload))

    run_records.sort(
        key=lambda item: (
            item[0] is None,
            item[0] or dt.datetime.min.replace(tzinfo=dt.timezone.utc),
            str(item[2].get("run_id", item[1].stem)),
        )
    )

    durations: list[float] = []
    spec_run_counts: dict[str, int] = {}
    per_day_buckets: dict[str, dict[str, Any]] = {}

    for timestamp, path, payload in run_records:
        run_id = str(payload.get("run_id", "")).strip() or path.stem
        spec_id = str(payload.get("spec_id", "")).strip()
        spec_run_counts[spec_id] = spec_run_counts.get(spec_id, 0) + 1
        same_spec_repeat_count = max(spec_run_counts[spec_id] - 1, 0) if spec_id else 0

        findings = performance_validation_findings(payload)
        run_kind = performance_run_kind(payload)
        execution_profile = performance_execution_profile(payload)
        child_model = performance_child_model(payload)
        duration_sec = performance_run_duration_sec(payload, path)
        if duration_sec is not None:
            durations.append(duration_sec)
        before_status = str(payload.get("before_status", "")).strip()
        final_status = str(payload.get("final_status", "")).strip()
        gate_state = str(payload.get("gate_state", "")).strip() or "none"
        before_maturity_raw = payload.get("before_maturity")
        final_maturity_raw = payload.get("final_maturity")
        before_maturity = (
            float(before_maturity_raw) if isinstance(before_maturity_raw, (int, float)) else None
        )
        final_maturity = (
            float(final_maturity_raw) if isinstance(final_maturity_raw, (int, float)) else None
        )
        changed_files = (
            [str(item).strip() for item in payload.get("changed_files", []) if str(item).strip()]
            if isinstance(payload.get("changed_files", []), list)
            else []
        )
        proposal_queue_transition = performance_queue_transition(payload, "proposal_queue")
        refactor_queue_transition = performance_queue_transition(payload, "refactor_queue")
        proposal_emitted = bool(proposal_queue_transition.get("emitted_ids")) or (
            run_kind in SUPERVISOR_PERFORMANCE_PROPOSAL_RUN_KINDS
            and str(payload.get("proposal_artifact_path", "")).strip()
            and str(payload.get("outcome", "")).strip() == "done"
        )
        accepted_canonical_diff = performance_accepted_canonical_diff(payload)
        productive_split_required = performance_productive_split_required(payload)
        new_child_materialized_count = performance_new_child_materialized_count(payload)
        review_required = gate_state in SUPERVISOR_PERFORMANCE_REVIEW_PENDING_GATE_STATES
        runtime_status, runtime_failure_reasons = performance_runtime_status(payload, findings)
        yield_status, productive_run = performance_yield_status(
            payload,
            runtime_status=runtime_status,
            accepted_canonical_diff=accepted_canonical_diff,
            productive_split_required=productive_split_required,
            proposal_emitted=proposal_emitted,
            review_required=review_required,
            changed_files=changed_files,
        )
        graph_impact_status = performance_graph_impact_status(
            runtime_status=runtime_status,
            yield_status=yield_status,
            before_status=before_status,
            final_status=final_status,
            before_maturity=before_maturity,
            final_maturity=final_maturity,
            new_child_materialized_count=new_child_materialized_count,
            gate_state=gate_state,
        )
        graph_health = payload.get("graph_health", {})
        if isinstance(graph_health, dict) and isinstance(graph_health.get("signals", []), list):
            graph_signals = [
                str(item).strip() for item in graph_health.get("signals", []) if str(item).strip()
            ]
        else:
            graph_signals = []
        validation_summary_payload = payload.get("validation_summary", {})
        if not isinstance(validation_summary_payload, dict):
            validation_summary_payload = {}

        entry = {
            "run_id": run_id,
            "spec_id": spec_id,
            "title": str(payload.get("title", "")).strip(),
            "run_kind": run_kind,
            "execution_profile": execution_profile,
            "child_model": child_model,
            "timestamp_utc": _iso_or_empty(timestamp),
            "started_at_utc": _iso_or_empty(parse_iso_datetime(payload.get("started_at_utc", ""))),
            "finished_at_utc": _iso_or_empty(
                parse_iso_datetime(payload.get("finished_at_utc", ""))
                or parse_iso_datetime(payload.get("timestamp_utc", ""))
            ),
            "run_duration_sec": duration_sec,
            "runtime_status": runtime_status,
            "runtime_failure_reasons": runtime_failure_reasons,
            "yield_status": yield_status,
            "graph_impact_status": graph_impact_status,
            "productive_run": productive_run,
            "accepted_canonical_diff": accepted_canonical_diff,
            "proposal_emitted": proposal_emitted,
            "productive_split_required": productive_split_required,
            "review_required": review_required,
            "new_child_materialized_count": new_child_materialized_count,
            "same_spec_repeat_count": same_spec_repeat_count,
            "completion_status": str(payload.get("completion_status", "")).strip(),
            "outcome": str(payload.get("outcome", "")).strip(),
            "blocker": str(payload.get("blocker", "")).strip(),
            "gate_state": gate_state,
            "status_delta": {
                "before": before_status,
                "after": final_status,
                "changed": bool(before_status and final_status and before_status != final_status),
            },
            "maturity_delta": {
                "before": before_maturity,
                "after": final_maturity,
                "delta": (
                    round(final_maturity - before_maturity, 3)
                    if before_maturity is not None and final_maturity is not None
                    else None
                ),
            },
            "graph_signal_summary": {
                "signal_count": len(graph_signals),
                "signals": graph_signals,
            },
            "intervention_cost": {
                "changed_file_count": len(changed_files),
                "validation_finding_count": len(findings),
                "proposal_queue_emission_count": len(
                    [
                        item
                        for item in proposal_queue_transition.get("emitted_ids", [])
                        if str(item).strip()
                    ]
                ),
                "refactor_queue_emission_count": len(
                    [
                        item
                        for item in refactor_queue_transition.get("emitted_ids", [])
                        if str(item).strip()
                    ]
                ),
            },
            "validation_summary": copy.deepcopy(validation_summary_payload),
        }
        entries.append(entry)

        grouped_runtime_status.setdefault(runtime_status, []).append(run_id)
        grouped_yield_status.setdefault(yield_status, []).append(run_id)
        grouped_graph_impact_status.setdefault(graph_impact_status, []).append(run_id)
        if run_kind:
            grouped_run_kind.setdefault(run_kind, []).append(run_id)
        if execution_profile:
            grouped_execution_profile.setdefault(execution_profile, []).append(run_id)

        if runtime_status == "runtime_failed":
            named_filters["runtime_failures"].append(run_id)
        if runtime_status == "runtime_degraded":
            named_filters["runtime_degraded"].append(run_id)
        if productive_run:
            named_filters["productive_runs"].append(run_id)
        if yield_status == "accepted_change":
            named_filters["accepted_changes"].append(run_id)
        if yield_status == "proposal_emitted":
            named_filters["proposal_emitted"].append(run_id)
        if yield_status == "productive_split_required":
            named_filters["split_productive_runs"].append(run_id)
        if yield_status == "review_pending_candidate":
            named_filters["review_pending_candidates"].append(run_id)
        if yield_status == "low_yield":
            named_filters["low_yield_runs"].append(run_id)
        if graph_impact_status in {"canonical_improvement", "proposal_only"}:
            named_filters["positive_graph_impact"].append(run_id)
        if graph_impact_status == "blocked_or_regressed":
            named_filters["negative_graph_impact"].append(run_id)
        if (
            duration_sec is not None
            and duration_sec >= SUPERVISOR_PERFORMANCE_SLOW_RUN_THRESHOLD_SECONDS
        ):
            named_filters["slow_runs"].append(run_id)

        day_key = timestamp.date().isoformat() if timestamp is not None else "unknown"
        bucket = per_day_buckets.setdefault(
            day_key,
            {
                "day_utc": day_key,
                "run_ids": [],
                "run_count": 0,
                "productive_run_count": 0,
                "runtime_failed_count": 0,
                "accepted_canonical_diff_count": 0,
                "proposal_emitted_count": 0,
                "new_child_materialized_count": 0,
                "durations": [],
            },
        )
        bucket["run_ids"].append(run_id)
        bucket["run_count"] += 1
        bucket["productive_run_count"] += 1 if productive_run else 0
        bucket["runtime_failed_count"] += 1 if runtime_status == "runtime_failed" else 0
        bucket["accepted_canonical_diff_count"] += 1 if accepted_canonical_diff else 0
        bucket["proposal_emitted_count"] += 1 if proposal_emitted else 0
        bucket["new_child_materialized_count"] += new_child_materialized_count
        if duration_sec is not None:
            bucket["durations"].append(duration_sec)

    repeat_hotspots = sorted(
        (
            {"spec_id": spec_id, "run_count": count}
            for spec_id, count in spec_run_counts.items()
            if spec_id and count >= SUPERVISOR_PERFORMANCE_REPEAT_HOTSPOT_RUN_COUNT
        ),
        key=lambda item: (-int(item["run_count"]), str(item["spec_id"])),
    )
    named_filters["repeat_hotspot_specs"] = [item["spec_id"] for item in repeat_hotspots]

    batches_by_day = []
    for day_key in sorted(per_day_buckets):
        bucket = per_day_buckets[day_key]
        batches_by_day.append(
            {
                "day_utc": day_key,
                "run_count": bucket["run_count"],
                "productive_run_count": bucket["productive_run_count"],
                "runtime_failed_count": bucket["runtime_failed_count"],
                "accepted_canonical_diff_count": bucket["accepted_canonical_diff_count"],
                "proposal_emitted_count": bucket["proposal_emitted_count"],
                "new_child_materialized_count": bucket["new_child_materialized_count"],
                "median_run_duration_sec": median_float(bucket["durations"]),
                "run_ids": list(bucket["run_ids"]),
            }
        )

    runtime_status_counts = grouped_identifier_counts(grouped_runtime_status)
    yield_status_counts = grouped_identifier_counts(grouped_yield_status)
    graph_impact_status_counts = grouped_identifier_counts(grouped_graph_impact_status)
    run_kind_counts = grouped_identifier_counts(grouped_run_kind)
    execution_profile_counts = grouped_identifier_counts(grouped_execution_profile)
    accepted_canonical_diff_count = sum(
        1 for entry in entries if bool(entry.get("accepted_canonical_diff"))
    )
    proposal_emitted_count = sum(1 for entry in entries if bool(entry.get("proposal_emitted")))
    productive_split_required_count = sum(
        1 for entry in entries if bool(entry.get("productive_split_required"))
    )
    review_pending_candidate_count = sum(
        1
        for entry in entries
        if str(entry.get("yield_status", "")).strip() == "review_pending_candidate"
    )
    productive_run_count = sum(1 for entry in entries if bool(entry.get("productive_run")))
    runtime_failed_count = runtime_status_counts.get("runtime_failed", 0)
    runtime_degraded_count = runtime_status_counts.get("runtime_degraded", 0)

    return {
        "artifact_kind": SUPERVISOR_PERFORMANCE_INDEX_ARTIFACT_KIND,
        "schema_version": SUPERVISOR_PERFORMANCE_INDEX_SCHEMA_VERSION,
        "generated_at": utc_now_iso(),
        "policy_reference": supervisor_performance_policy_reference(),
        "source_artifacts": {
            "run_logs_dir": RUNS_DIR.relative_to(ROOT).as_posix(),
            "run_logs_scanned": run_logs_scanned,
            "skipped_invalid_run_log_count": len(skipped_invalid_run_logs),
        },
        "entry_count": len(entries),
        "entries": entries,
        "aggregates": {
            "runtime_status_counts": runtime_status_counts,
            "yield_status_counts": yield_status_counts,
            "graph_impact_status_counts": graph_impact_status_counts,
            "run_kind_counts": run_kind_counts,
            "execution_profile_counts": execution_profile_counts,
            "productive_run_count": productive_run_count,
            "accepted_canonical_diff_count": accepted_canonical_diff_count,
            "proposal_emitted_count": proposal_emitted_count,
            "productive_split_required_count": productive_split_required_count,
            "review_pending_candidate_count": review_pending_candidate_count,
            "runtime_failed_count": runtime_failed_count,
            "runtime_degraded_count": runtime_degraded_count,
            "new_child_materialized_count": sum(
                int(entry.get("new_child_materialized_count", 0)) for entry in entries
            ),
            "median_run_duration_sec": median_float(durations),
            "max_run_duration_sec": round(max(durations), 3) if durations else None,
            "same_spec_repeat_hotspots": repeat_hotspots,
        },
        "batches": {
            "time_bucket": str(supervisor_performance_policy_lookup("batch_contract.time_bucket")),
            "by_day_utc": batches_by_day,
        },
        "viewer_projection": {
            "runtime_status": {
                key: sorted(value) for key, value in sorted(grouped_runtime_status.items())
            },
            "yield_status": {
                key: sorted(value) for key, value in sorted(grouped_yield_status.items())
            },
            "graph_impact_status": {
                key: sorted(value) for key, value in sorted(grouped_graph_impact_status.items())
            },
            "run_kind": {key: sorted(value) for key, value in sorted(grouped_run_kind.items())},
            "execution_profile": {
                key: sorted(value) for key, value in sorted(grouped_execution_profile.items())
            },
            "named_filters": {key: sorted(value) for key, value in sorted(named_filters.items())},
        },
        "skipped_invalid_run_logs": skipped_invalid_run_logs,
    }


def write_supervisor_performance_index(report: dict[str, Any]) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = supervisor_performance_index_path()
    with artifact_lock(path):
        atomic_write_json(path, report)
    return path


def proposal_runtime_registry_path() -> Path:
    return ROOT / "tools" / "proposal_runtime_registry.json"


def proposal_promotion_registry_path() -> Path:
    return ROOT / "tools" / "proposal_promotion_registry.json"


def proposal_runtime_index_path() -> Path:
    return RUNS_DIR / PROPOSAL_RUNTIME_INDEX_FILENAME


def proposal_promotion_index_path() -> Path:
    return RUNS_DIR / PROPOSAL_PROMOTION_INDEX_FILENAME


def graph_dashboard_path() -> Path:
    return RUNS_DIR / GRAPH_DASHBOARD_FILENAME


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


def evaluate_declared_paths(paths: list[str]) -> dict[str, Any]:
    checked_paths: list[dict[str, Any]] = []
    existing_count = 0
    for path_text in paths:
        normalized = str(path_text).strip()
        if not normalized:
            continue
        path = ROOT / normalized
        exists = path.exists()
        if exists:
            existing_count += 1
        checked_paths.append(
            {
                "path": normalized,
                "exists": exists,
            }
        )
    status = "not_declared"
    if checked_paths:
        if existing_count == len(checked_paths):
            status = "covered"
        elif existing_count == 0:
            status = "missing"
        else:
            status = "partial"
    return {
        "status": status,
        "required_count": len(checked_paths),
        "existing_count": existing_count,
        "paths": checked_paths,
        "missing_paths": [item for item in checked_paths if not item["exists"]],
    }


def evaluate_evidence_markers(markers: list[dict[str, Any]]) -> dict[str, Any]:
    report = evaluate_path_markers(markers)
    normalized = copy.deepcopy(report)
    if normalized["status"] == "not_configured":
        normalized["status"] = "not_declared"
    normalized["available_statuses"] = list(EVIDENCE_PLANE_COVERAGE_STATUSES)
    return normalized


def derive_evidence_artifact_stage(
    *,
    registry_entry: dict[str, Any] | None,
    artifact_refs: list[str],
    artifact_surface_report: dict[str, Any],
    trace_entry: dict[str, Any] | None,
) -> dict[str, Any]:
    if registry_entry is None:
        return {
            "status": "untracked",
            "available_statuses": list(EVIDENCE_PLANE_STAGE_STATUSES),
            "basis": "No explicit evidence contract is registered for this spec.",
            "artifact_ref_count": 0,
            "trace_linked": False,
        }

    trace_linked = bool(
        isinstance(trace_entry, dict)
        and (
            trace_entry.get("trace_contract")
            or trace_entry.get("code_refs")
            or trace_entry.get("test_refs")
        )
    )
    if artifact_surface_report["status"] == "covered" and trace_linked:
        status = "linked"
        basis = "Declared artifact refs exist and the spec already has a graph-bound trace entry."
    elif artifact_surface_report["status"] in {"covered", "partial"} or trace_linked:
        status = "partial"
        basis = (
            "Evidence contract exists, but artifact refs and graph-bound trace anchors are only "
            "partially aligned."
        )
    else:
        status = "missing"
        basis = "Evidence contract exists, but declared artifact refs are not currently present."
    return {
        "status": status,
        "available_statuses": list(EVIDENCE_PLANE_STAGE_STATUSES),
        "basis": basis,
        "artifact_ref_count": len(artifact_refs),
        "trace_linked": trace_linked,
        "implementation_state": (
            copy.deepcopy(trace_entry.get("implementation_state", {}))
            if isinstance(trace_entry, dict)
            else {}
        ),
        "freshness": (
            copy.deepcopy(trace_entry.get("freshness", {})) if isinstance(trace_entry, dict) else {}
        ),
        "artifact_surfaces": artifact_surface_report,
    }


def derive_evidence_chain_status(
    *,
    registry_entry: dict[str, Any] | None,
    observation_coverage: dict[str, Any],
    outcome_coverage: dict[str, Any],
    adoption_coverage: dict[str, Any],
) -> str:
    if registry_entry is None:
        return "untracked"
    observation_status = str(observation_coverage.get("status", "")).strip()
    outcome_status = str(outcome_coverage.get("status", "")).strip()
    adoption_status = str(adoption_coverage.get("status", "")).strip()
    if (
        observation_status == "covered"
        and outcome_status == "covered"
        and adoption_status == "covered"
    ):
        return "chain_complete"
    if observation_status == "covered" and outcome_status == "covered":
        return "outcome_backed"
    if observation_status == "covered":
        return "observation_backed"
    if any(status == "partial" for status in (observation_status, outcome_status, adoption_status)):
        return "partial"
    return "contract_only"


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
        "artifact_kind": "proposal_runtime_index",
        "schema_version": 1,
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


def grouped_identifier_counts(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    counts: dict[str, int] = {}
    for key, items in value.items():
        normalized_key = str(key).strip()
        if not normalized_key or not isinstance(items, list):
            continue
        normalized_items = {str(item).strip() for item in items if str(item).strip()}
        counts[normalized_key] = len(normalized_items)
    return counts


def dashboard_card(
    *,
    card_id: str,
    title: str,
    value: int,
    section: str,
    status: str,
    basis: str,
) -> dict[str, Any]:
    return {
        "card_id": card_id,
        "title": title,
        "value": value,
        "value_kind": "count",
        "section": section,
        "status": status,
        "basis": basis,
    }


def build_graph_dashboard(specs: list[SpecNode]) -> dict[str, Any]:
    graph_overlay = build_graph_health_overlay(specs)
    graph_trends = build_graph_health_trends(specs, overlay=graph_overlay)
    intent_overlay = build_intent_layer_overlay()
    proposal_lane_overlay = build_proposal_lane_overlay()
    proposal_runtime_index = build_proposal_runtime_index()
    proposal_promotion_index = build_proposal_promotion_index()
    spec_trace_index = build_spec_trace_index(specs)
    spec_trace_projection = build_spec_trace_projection(spec_trace_index)
    evidence_index = build_evidence_plane_index(specs)
    evidence_overlay = build_evidence_plane_overlay(evidence_index)
    external_consumer_index = build_external_consumer_index()
    metric_signal_index = build_metric_signal_index(specs)
    external_consumer_overlay = build_external_consumer_overlay(
        external_consumer_index,
        metric_signal_index,
    )
    metric_threshold_proposals = build_metric_threshold_proposals(metric_signal_index)
    external_consumer_handoffs = build_external_consumer_handoff_packets(
        external_consumer_index,
        external_consumer_overlay,
        metric_signal_index,
        metric_threshold_proposals,
    )

    total_spec_count = len(specs)
    active_spec_count = sum(1 for spec in specs if not is_historical_spec(spec.data))
    historical_spec_count = total_spec_count - active_spec_count
    gate_state_counts: dict[str, int] = {}
    for spec in specs:
        gate_state = str(spec.gate_state or "none").strip() or "none"
        gate_state_counts[gate_state] = gate_state_counts.get(gate_state, 0) + 1

    graph_overlay_entries = [
        entry for entry in graph_overlay.get("entries", []) if isinstance(entry, dict)
    ]
    structural_pressure_spec_ids = sorted(
        {
            str(entry.get("spec_id", "")).strip()
            for entry in graph_overlay_entries
            if str(entry.get("spec_id", "")).strip()
            and any(str(item).strip() for item in entry.get("signals", []) if str(item).strip())
        }
    )
    graph_signal_counts = grouped_identifier_counts(
        graph_overlay.get("viewer_projection", {}).get("signals", {})
    )
    graph_action_counts = grouped_identifier_counts(
        graph_overlay.get("viewer_projection", {}).get("recommended_actions", {})
    )
    graph_named_filter_counts = grouped_identifier_counts(
        graph_overlay.get("viewer_projection", {}).get("named_filters", {})
    )
    graph_trend_status_counts = grouped_identifier_counts(
        graph_trends.get("viewer_projection", {}).get("trend_status", {})
    )
    graph_trend_named_filter_counts = grouped_identifier_counts(
        graph_trends.get("viewer_projection", {}).get("named_filters", {})
    )

    intent_kind_counts = grouped_identifier_counts(intent_overlay.get("by_kind", {}))
    intent_state_counts = grouped_identifier_counts(intent_overlay.get("by_mediation_state", {}))
    proposal_lane_authority_counts = grouped_identifier_counts(
        proposal_lane_overlay.get("by_authority_state", {})
        or proposal_lane_overlay.get("by_authority", {})
    )
    proposal_lane_active_count = sum(
        count
        for state, count in proposal_lane_authority_counts.items()
        if state not in {"rejected", "superseded"}
    )

    proposal_runtime_posture_counts: dict[str, int] = {}
    for entry in proposal_runtime_index.get("entries", []):
        if not isinstance(entry, dict):
            continue
        posture = str(entry.get("posture", "")).strip() or "unknown"
        proposal_runtime_posture_counts[posture] = (
            proposal_runtime_posture_counts.get(posture, 0) + 1
        )
    proposal_runtime_backlog_counts = grouped_identifier_counts(
        proposal_runtime_index.get("reflective_backlog", {}).get("grouped_by_next_gap", {})
    )
    proposal_promotion_traceability_counts = grouped_identifier_counts(
        proposal_promotion_index.get("viewer_projection", {}).get("traceability_status", {})
    )

    trace_impl_counts = grouped_identifier_counts(
        spec_trace_projection.get("viewer_projection", {}).get("implementation_state", {})
    )
    trace_freshness_counts = grouped_identifier_counts(
        spec_trace_projection.get("viewer_projection", {}).get("freshness", {})
    )
    trace_acceptance_counts = grouped_identifier_counts(
        spec_trace_projection.get("viewer_projection", {}).get("acceptance_coverage", {})
    )
    trace_named_filter_counts = grouped_identifier_counts(
        spec_trace_projection.get("viewer_projection", {}).get("named_filters", {})
    )

    evidence_chain_counts = grouped_identifier_counts(
        evidence_overlay.get("viewer_projection", {}).get("chain_status", {})
    )
    evidence_artifact_stage_counts = grouped_identifier_counts(
        evidence_overlay.get("viewer_projection", {}).get("artifact_stage", {})
    )
    evidence_named_filter_counts = grouped_identifier_counts(
        evidence_overlay.get("viewer_projection", {}).get("named_filters", {})
    )
    external_consumer_bridge_state_counts = grouped_identifier_counts(
        external_consumer_overlay.get("viewer_projection", {}).get("bridge_state", {})
    )
    external_consumer_metric_pressure_counts = grouped_identifier_counts(
        external_consumer_overlay.get("viewer_projection", {}).get("bound_metric_status", {})
    )
    external_consumer_named_filter_counts = grouped_identifier_counts(
        external_consumer_overlay.get("viewer_projection", {}).get("named_filters", {})
    )
    external_consumer_handoff_status_counts = grouped_identifier_counts(
        external_consumer_handoffs.get("viewer_projection", {}).get("handoff_status", {})
    )
    external_consumer_handoff_review_state_counts = grouped_identifier_counts(
        external_consumer_handoffs.get("viewer_projection", {}).get("review_state", {})
    )

    metric_entries = [
        entry for entry in metric_signal_index.get("metrics", []) if isinstance(entry, dict)
    ]
    metric_status_counts: dict[str, int] = {}
    metric_scores: dict[str, dict[str, Any]] = {}
    below_threshold_metric_ids: list[str] = []
    for entry in metric_entries:
        metric_id = str(entry.get("metric_id", "")).strip()
        if not metric_id:
            continue
        status = str(entry.get("status", "")).strip() or "unknown"
        metric_status_counts[status] = metric_status_counts.get(status, 0) + 1
        metric_scores[metric_id] = {
            "score": entry.get("score"),
            "minimum_score": entry.get("minimum_score"),
            "status": status,
            "threshold_gap": entry.get("threshold_gap"),
        }
        if status == "below_threshold":
            below_threshold_metric_ids.append(metric_id)
    metric_threshold_kind_counts = grouped_identifier_counts(
        metric_threshold_proposals.get("viewer_projection", {}).get("proposal_kind", {})
    )
    metric_threshold_severity_counts = grouped_identifier_counts(
        metric_threshold_proposals.get("viewer_projection", {}).get("severity", {})
    )

    headline_cards = [
        dashboard_card(
            card_id="total_specs",
            title="Total Specs",
            value=total_spec_count,
            section="graph",
            status="info",
            basis="All canonical spec nodes currently loaded by the supervisor.",
        ),
        dashboard_card(
            card_id="active_specs",
            title="Active Specs",
            value=active_spec_count,
            section="graph",
            status="info",
            basis="Canonical specs that are not marked historical/superseded lineage only.",
        ),
        dashboard_card(
            card_id="gated_specs",
            title="Gated Specs",
            value=graph_named_filter_counts.get("gated_specs", 0),
            section="health",
            status=(
                "attention" if graph_named_filter_counts.get("gated_specs", 0) > 0 else "healthy"
            ),
            basis="Specs currently carrying a non-none gate state in the graph-health overlay.",
        ),
        dashboard_card(
            card_id="structural_pressure_specs",
            title="Structural Pressure Specs",
            value=len(structural_pressure_spec_ids),
            section="health",
            status="attention" if structural_pressure_spec_ids else "healthy",
            basis="Specs with active graph-health signals, excluding gate-only entries.",
        ),
        dashboard_card(
            card_id="proposal_lane_active",
            title="Active Proposal Lane Nodes",
            value=proposal_lane_active_count,
            section="proposals",
            status="attention" if proposal_lane_active_count > 0 else "healthy",
            basis="Tracked proposal-lane nodes not yet rejected or superseded.",
        ),
        dashboard_card(
            card_id="verified_specs",
            title="Verified Specs",
            value=trace_impl_counts.get("verified", 0),
            section="implementation",
            status="info",
            basis="Specs whose trace plane currently observes both declared code and test anchors.",
        ),
        dashboard_card(
            card_id="complete_evidence_chains",
            title="Complete Evidence Chains",
            value=evidence_named_filter_counts.get("complete_chain", 0),
            section="evidence",
            status="info",
            basis=(
                "Specs whose evidence plane currently covers artifact, observation, "
                "outcome, and adoption."
            ),
        ),
        dashboard_card(
            card_id="stable_bridges_ready",
            title="Stable Bridges Ready",
            value=external_consumer_named_filter_counts.get("stable_ready", 0),
            section="external_consumers",
            status=(
                "healthy"
                if external_consumer_named_filter_counts.get("stable_ready", 0) > 0
                else "attention"
            ),
            basis=(
                "Stable sibling-consumer bridges with verified repo identity and ready "
                "declared contract surfaces."
            ),
        ),
        dashboard_card(
            card_id="ready_external_handoffs",
            title="Ready External Handoffs",
            value=external_consumer_handoff_status_counts.get("ready_for_handoff", 0),
            section="external_consumers",
            status=(
                "attention"
                if external_consumer_handoff_status_counts.get("ready_for_handoff", 0) > 0
                else "healthy"
            ),
            basis=(
                "Stable sibling consumers that now have a reviewable downstream handoff "
                "packet emitted from SpecGraph surfaces."
            ),
        ),
        dashboard_card(
            card_id="metrics_below_threshold",
            title="Metrics Below Threshold",
            value=len(below_threshold_metric_ids),
            section="metrics",
            status="attention" if below_threshold_metric_ids else "healthy",
            basis="Derived metrics currently below configured minimum scores.",
        ),
    ]

    return {
        "artifact_kind": "graph_dashboard",
        "schema_version": 1,
        "generated_at": utc_now_iso(),
        "source_artifacts": {
            "graph_health_overlay": {
                "artifact_path": graph_health_overlay_path().relative_to(ROOT).as_posix(),
                "generated_at": graph_overlay.get("generated_at"),
            },
            "graph_health_trends": {
                "artifact_path": graph_health_trends_path().relative_to(ROOT).as_posix(),
                "generated_at": graph_trends.get("generated_at"),
            },
            "intent_layer_overlay": {
                "artifact_path": intent_layer_overlay_path().relative_to(ROOT).as_posix(),
                "generated_at": intent_overlay.get("generated_at"),
            },
            "proposal_lane_overlay": {
                "artifact_path": proposal_lane_overlay_path().relative_to(ROOT).as_posix(),
                "generated_at": proposal_lane_overlay.get("generated_at"),
            },
            "proposal_runtime_index": {
                "artifact_path": proposal_runtime_index_path().relative_to(ROOT).as_posix(),
                "generated_at": proposal_runtime_index.get("generated_at"),
            },
            "proposal_promotion_index": {
                "artifact_path": proposal_promotion_index_path().relative_to(ROOT).as_posix(),
                "generated_at": proposal_promotion_index.get("generated_at"),
            },
            "spec_trace_projection": {
                "artifact_path": spec_trace_projection_path().relative_to(ROOT).as_posix(),
                "generated_at": spec_trace_projection.get("generated_at"),
            },
            "evidence_plane_overlay": {
                "artifact_path": evidence_plane_overlay_path().relative_to(ROOT).as_posix(),
                "generated_at": evidence_overlay.get("generated_at"),
            },
            "external_consumer_index": {
                "artifact_path": external_consumer_index_path().relative_to(ROOT).as_posix(),
                "generated_at": external_consumer_index.get("generated_at"),
            },
            "external_consumer_overlay": {
                "artifact_path": external_consumer_overlay_path().relative_to(ROOT).as_posix(),
                "generated_at": external_consumer_overlay.get("generated_at"),
            },
            "external_consumer_handoffs": {
                "artifact_path": external_consumer_handoff_packets_path()
                .relative_to(ROOT)
                .as_posix(),
                "generated_at": external_consumer_handoffs.get("generated_at"),
            },
            "metric_signal_index": {
                "artifact_path": metric_signal_index_path().relative_to(ROOT).as_posix(),
                "generated_at": metric_signal_index.get("generated_at"),
            },
            "metric_threshold_proposals": {
                "artifact_path": metric_threshold_proposals_path().relative_to(ROOT).as_posix(),
                "generated_at": metric_threshold_proposals.get("generated_at"),
            },
        },
        "headline_cards": headline_cards,
        "sections": {
            "graph": {
                "total_spec_count": total_spec_count,
                "active_spec_count": active_spec_count,
                "historical_spec_count": historical_spec_count,
                "gate_state_counts": gate_state_counts,
            },
            "health": {
                "signal_counts": graph_signal_counts,
                "recommended_action_counts": graph_action_counts,
                "named_filter_counts": graph_named_filter_counts,
                "trend_status_counts": graph_trend_status_counts,
                "trend_named_filter_counts": graph_trend_named_filter_counts,
                "structural_pressure_spec_ids": structural_pressure_spec_ids,
                "hotspot_region_count": len(graph_overlay.get("hotspot_regions", [])),
            },
            "proposals": {
                "intent_entry_count": int(intent_overlay.get("entry_count", 0) or 0),
                "intent_kind_counts": intent_kind_counts,
                "intent_state_counts": intent_state_counts,
                "proposal_lane_entry_count": int(proposal_lane_overlay.get("entry_count", 0) or 0),
                "proposal_lane_active_count": proposal_lane_active_count,
                "proposal_lane_authority_counts": proposal_lane_authority_counts,
                "proposal_runtime_entry_count": int(
                    proposal_runtime_index.get("entry_count", 0) or 0
                ),
                "proposal_runtime_posture_counts": proposal_runtime_posture_counts,
                "proposal_runtime_backlog_count": int(
                    proposal_runtime_index.get("reflective_backlog", {}).get("entry_count", 0) or 0
                ),
                "proposal_runtime_next_gap_counts": proposal_runtime_backlog_counts,
                "proposal_promotion_entry_count": int(
                    proposal_promotion_index.get("entry_count", 0) or 0
                ),
                "proposal_promotion_traceability_counts": proposal_promotion_traceability_counts,
            },
            "implementation": {
                "trace_entry_count": int(spec_trace_projection.get("entry_count", 0) or 0),
                "implementation_state_counts": trace_impl_counts,
                "freshness_counts": trace_freshness_counts,
                "acceptance_coverage_counts": trace_acceptance_counts,
                "named_filter_counts": trace_named_filter_counts,
                "implementation_backlog_count": int(
                    spec_trace_projection.get("implementation_backlog", {}).get("entry_count", 0)
                    or 0
                ),
            },
            "evidence": {
                "evidence_entry_count": int(evidence_overlay.get("entry_count", 0) or 0),
                "chain_status_counts": evidence_chain_counts,
                "artifact_stage_counts": evidence_artifact_stage_counts,
                "named_filter_counts": evidence_named_filter_counts,
                "evidence_backlog_count": int(
                    evidence_overlay.get("evidence_backlog", {}).get("entry_count", 0) or 0
                ),
            },
            "external_consumers": {
                "entry_count": int(external_consumer_overlay.get("entry_count", 0) or 0),
                "available_count": int(
                    external_consumer_index.get("available_entry_count", 0) or 0
                ),
                "bridge_state_counts": external_consumer_bridge_state_counts,
                "metric_pressure_counts": external_consumer_metric_pressure_counts,
                "named_filter_counts": external_consumer_named_filter_counts,
                "handoff_status_counts": external_consumer_handoff_status_counts,
                "handoff_review_state_counts": external_consumer_handoff_review_state_counts,
                "external_consumer_backlog_count": int(
                    external_consumer_overlay.get("external_consumer_backlog", {}).get(
                        "entry_count", 0
                    )
                    or 0
                ),
                "handoff_backlog_count": int(
                    external_consumer_handoffs.get("handoff_backlog", {}).get("entry_count", 0) or 0
                ),
            },
            "metrics": {
                "metric_count": len(metric_entries),
                "metric_status_counts": metric_status_counts,
                "metric_scores": metric_scores,
                "below_threshold_metric_ids": sorted(below_threshold_metric_ids),
                "threshold_proposal_entry_count": int(
                    metric_threshold_proposals.get("entry_count", 0) or 0
                ),
                "threshold_proposal_kind_counts": metric_threshold_kind_counts,
                "threshold_proposal_severity_counts": metric_threshold_severity_counts,
            },
        },
        "viewer_projection": {
            "headline_card_ids": [card["card_id"] for card in headline_cards],
            "section_ids": [
                "graph",
                "health",
                "proposals",
                "implementation",
                "evidence",
                "external_consumers",
                "metrics",
            ],
            "named_filters": {
                "gated_specs": graph_named_filter_counts.get("gated_specs", 0),
                "techspec_ready_regions": graph_named_filter_counts.get(
                    "techspec_ready_regions", 0
                ),
                "proposal_lane_under_review": proposal_lane_authority_counts.get("under_review", 0),
                "proposal_promotion_missing_trace": proposal_promotion_traceability_counts.get(
                    "missing_trace", 0
                ),
                "drifted_specs": trace_impl_counts.get("drifted", 0),
                "complete_evidence_chain_specs": evidence_named_filter_counts.get(
                    "complete_chain", 0
                ),
                "external_consumer_metric_pressure": external_consumer_named_filter_counts.get(
                    "metric_pressure", 0
                ),
                "ready_external_handoffs": external_consumer_handoff_status_counts.get(
                    "ready_for_handoff", 0
                ),
                "metrics_below_threshold": len(below_threshold_metric_ids),
            },
        },
    }


def write_graph_dashboard(report: dict[str, Any]) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = graph_dashboard_path()
    with artifact_lock(path):
        atomic_write_json(path, report)
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
    operator_request_context: dict[str, Any] | None = None,
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
            "user_intent_handle": str(
                (operator_request_context or {}).get("user_intent_handle", "")
            ).strip(),
            "operator_request_handle": str(
                (operator_request_context or {}).get("operator_request_handle", "")
            ).strip(),
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
    run_started_at = utc_now_iso()
    run_started_monotonic = time.monotonic()
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
    before_maturity = node.maturity
    validation_errors: list[str] = []
    validation_findings: list[dict[str, Any]] = []
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
        validation_findings.extend(
            string_errors_to_validation_findings(
                [str(exc)],
                family="artifact",
                error_class="artifact_integrity_failure",
                code="split_proposal_application_failure",
            )
        )
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
        validation_findings.extend(
            string_errors_to_validation_findings(
                output_errors,
                family="output",
                error_class="contract_failure",
                code="output_contract_violation",
                spec_id=node.id,
            )
        )
        validation_findings.extend(
            string_errors_to_validation_findings(
                atomicity_errors,
                family="acceptance",
                error_class="semantic_rejection",
                code="atomicity_violation",
                spec_id=node.id,
            )
        )
        validation_findings.extend(
            string_errors_to_validation_findings(
                reconciliation_errors,
                family="relation",
                error_class="relation_failure",
                code="graph_reconciliation_error",
                spec_id=node.id,
            )
        )
        if not validation_findings:
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
                validation_findings.extend(
                    string_errors_to_validation_findings(
                        [str(exc)],
                        family="artifact",
                        error_class="artifact_integrity_failure",
                        code="runtime_artifact_write_failure",
                        spec_id=node.id,
                    )
                )
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
            if not validation_findings:
                try:
                    refactor_queue_artifact = update_refactor_queue(
                        graph_health=graph_health,
                        run_id=run_id,
                        proposal_items=proposal_items,
                    )
                except RuntimeError as exc:
                    artifact_io_errors.append(str(exc))
                    validation_findings.extend(
                        string_errors_to_validation_findings(
                            [str(exc)],
                            family="artifact",
                            error_class="artifact_integrity_failure",
                            code="runtime_artifact_write_failure",
                            spec_id=node.id,
                        )
                    )
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

    validation_errors = validation_messages(validation_findings)

    if validation_findings:
        graph_health = {
            "source_spec_id": node.id,
            "observations": [],
            "signals": [],
            "recommended_actions": [],
        }
        proposal_queue_artifact = proposal_queue_path()
        refactor_queue_artifact = refactor_queue_path()

    success = not validation_findings
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
        validation_findings=validation_findings,
        validator_results={
            "proposal_artifact": not validation_findings,
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
    evaluator_loop_control = build_evaluator_loop_control(
        run_id=run_id,
        spec_id=node.id,
        selected_by_rule=selected_by_rule,
        outcome="done" if success else "blocked",
        gate_state="none",
        blocker="none" if success else "split proposal application failed",
        required_human_action="-" if success else "repair proposal before retry",
        graph_health=graph_health,
        validation_findings=validation_findings,
    )
    evaluator_control_artifact = write_evaluator_control_artifact(evaluator_loop_control)
    run_finished_at = utc_now_iso()
    run_duration_sec = round(max(time.monotonic() - run_started_monotonic, 0.0), 3)
    payload = {
        "run_id": run_id,
        "timestamp_utc": run_finished_at,
        "started_at_utc": run_started_at,
        "finished_at_utc": run_finished_at,
        "run_duration_sec": run_duration_sec,
        "spec_id": node.id,
        "title": node.title,
        "run_kind": "apply_split_proposal",
        "execution_profile": "",
        "child_model": "",
        "completion_status": COMPLETION_STATUS_OK if success else COMPLETION_STATUS_FAILED,
        "selected_by_rule": selected_by_rule,
        "before_status": before_status,
        "proposed_status": None,
        "final_status": node.status,
        "before_maturity": before_maturity,
        "final_maturity": node.maturity,
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
        "materialized_child_paths": [
            path
            for path in changed
            if is_spec_node_path(str(path).strip())
            and str(path).strip() != f"specs/nodes/{node.id}.yaml"
        ],
        "new_child_materialized_count": sum(
            1
            for path in changed
            if is_spec_node_path(str(path).strip())
            and str(path).strip() != f"specs/nodes/{node.id}.yaml"
        ),
        "accepted_canonical_diff": bool(success),
        "productive_split_required": False,
        "validation_findings_policy": validation_findings_policy_reference(),
        "validation_findings": validation_findings,
        "validation_summary": validation_summary(validation_findings),
        "validation_errors": validation_errors,
        "validator_results": {
            "proposal_artifact": not validation_findings,
            "canonical_writeback": success,
            "runtime_artifacts": not artifact_io_errors,
        },
        "reconciliation": {},
        "graph_health": graph_health,
        "graph_health_truth_basis": "accepted_canonical",
        "decision_inspector": decision_inspector,
        "decision_inspector_artifact": decision_inspector_artifact.as_posix(),
        "evaluator_loop_control": evaluator_loop_control,
        "evaluator_control_artifact": evaluator_control_artifact.as_posix(),
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
    operator_request_context: dict[str, Any] | None = None,
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
    run_started_at = utc_now_iso()
    run_started_monotonic = time.monotonic()
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
    if operator_request_context:
        selected_by_rule["user_intent_handle"] = str(
            operator_request_context.get("user_intent_handle", "")
        ).strip()
        selected_by_rule["operator_request_handle"] = str(
            operator_request_context.get("operator_request_handle", "")
        ).strip()
        selected_by_rule["operator_request_packet"] = str(
            operator_request_context.get("packet_reference", "")
        ).strip()
    selected_by_rule["execution_profile"] = resolve_execution_profile_name(
        requested_profile=execution_profile,
        run_authority=(),
        operator_target=True,
    )
    before_status = node.status
    before_maturity = node.maturity

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
    outcome, blocker, executor_protocol_findings = parse_executor_protocol(
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
        validation_findings = executor_environment_validation_findings(executor_environment)
    else:
        try:
            worktree_specs = load_specs_from_dir(worktree_path / "specs" / "nodes")
        except Exception as exc:
            worktree_specs = []
            graph_health = empty_graph_health(node.id)
            validation_findings = string_errors_to_validation_findings(
                [f"Failed to load worktree specs for split proposal validation: {exc}"],
                family="yaml",
                error_class="parse_failure",
                code="split_proposal_worktree_load_failure",
                spec_id=node.id,
            )
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
            validation_findings = []
    validation_findings.extend(executor_protocol_findings)

    artifact_relpath = str(refactor_work_item["proposal_artifact_relpath"])
    artifact_worktree_path = worktree_path / artifact_relpath
    proposal_artifact_root_path = ROOT / artifact_relpath
    allowed_changed_paths = split_proposal_allowed_changed_paths(artifact_relpath)
    changed_spec_files = [path for path in changed if is_spec_node_path(path)]
    extra_changed_files = [path for path in changed if path not in allowed_changed_paths]
    if changed_spec_files:
        validation_findings.extend(
            string_errors_to_validation_findings(
                [
                    "split proposal mode must not modify canonical spec files: "
                    + ", ".join(changed_spec_files)
                ],
                family="authority",
                error_class="scope_violation",
                code="split_proposal_canonical_mutation_scope_violation",
                spec_id=node.id,
            )
        )
    if extra_changed_files:
        validation_findings.extend(
            string_errors_to_validation_findings(
                [
                    "split proposal mode must only write the structured proposal artifact: "
                    + ", ".join(extra_changed_files)
                ],
                family="authority",
                error_class="scope_violation",
                code="split_proposal_artifact_scope_violation",
                spec_id=node.id,
            )
        )

    artifact_io_errors: list[str] = []
    proposal_artifact_data: dict[str, Any] | None = None
    if outcome == "done":
        proposal_artifact_data, artifact_error = load_json_object_report(
            artifact_worktree_path,
            artifact_kind="structured split proposal artifact",
        )
        if proposal_artifact_data is None:
            validation_findings.extend(
                string_errors_to_validation_findings(
                    [
                        artifact_error
                        or (
                            "Missing or invalid structured split proposal artifact: "
                            f"{artifact_relpath}"
                        )
                    ],
                    family="artifact",
                    error_class="artifact_integrity_failure",
                    code="invalid_split_proposal_artifact",
                    spec_id=node.id,
                    path=artifact_relpath,
                )
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
            validation_findings.extend(
                string_errors_to_validation_findings(
                    validate_split_proposal_artifact(
                        artifact=proposal_artifact_data,
                        node=node,
                        run_id=run_id,
                    ),
                    family="artifact",
                    error_class="contract_failure",
                    code="split_proposal_artifact_validation_error",
                    spec_id=node.id,
                    path=artifact_relpath,
                )
            )

    validation_errors = validation_messages(validation_findings)
    success = result.returncode == 0 and not validation_findings and outcome == "done"
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
                operator_request_context=operator_request_context,
            )
        except RuntimeError as exc:
            artifact_io_errors.append(str(exc))
            validation_findings.extend(
                string_errors_to_validation_findings(
                    [str(exc)],
                    family="artifact",
                    error_class="artifact_integrity_failure",
                    code="runtime_artifact_write_failure",
                    spec_id=node.id,
                )
            )
            validation_errors = validation_messages(validation_findings)
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
    proposal_ids_for_pre_spec = sorted(
        {
            str(item.get("id", "")).strip()
            for item in proposal_queue_after
            if isinstance(item, dict)
            and str(item.get("spec_id", "")).strip() == node.id
            and str(item.get("operator_request_handle", "")).strip()
            == str((operator_request_context or {}).get("operator_request_handle", "")).strip()
            and str(item.get("id", "")).strip()
        }
    )
    decision_inspector = build_decision_inspector(
        run_id=run_id,
        spec_id=node.id,
        selected_by_rule=selected_by_rule,
        outcome=outcome,
        gate_state="none",
        required_human_action=required_human_action,
        blocker=blocker,
        changed_files=changed,
        validation_findings=validation_findings,
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
    evaluator_loop_control = build_evaluator_loop_control(
        run_id=run_id,
        spec_id=node.id,
        selected_by_rule=selected_by_rule,
        outcome=outcome,
        gate_state="none",
        blocker=blocker,
        required_human_action=required_human_action,
        graph_health=graph_health,
        validation_findings=validation_findings,
    )
    evaluator_control_artifact = write_evaluator_control_artifact(evaluator_loop_control)
    run_finished_at = utc_now_iso()
    run_duration_sec = round(max(time.monotonic() - run_started_monotonic, 0.0), 3)
    payload = {
        "run_id": run_id,
        "timestamp_utc": run_finished_at,
        "started_at_utc": run_started_at,
        "finished_at_utc": run_finished_at,
        "run_duration_sec": run_duration_sec,
        "spec_id": node.id,
        "title": node.title,
        "run_kind": "split_proposal",
        "execution_profile": str(selected_by_rule.get("execution_profile", "")).strip(),
        "child_model": child_model or "",
        "completion_status": COMPLETION_STATUS_OK if success else COMPLETION_STATUS_FAILED,
        "selected_by_rule": selected_by_rule,
        "before_status": before_status,
        "proposed_status": None,
        "final_status": before_status,
        "before_maturity": before_maturity,
        "final_maturity": before_maturity,
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
        "materialized_child_paths": [],
        "new_child_materialized_count": 0,
        "accepted_canonical_diff": False,
        "productive_split_required": False,
        "validation_findings_policy": validation_findings_policy_reference(),
        "validation_findings": validation_findings,
        "validation_summary": validation_summary(validation_findings),
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
        "evaluator_loop_control": evaluator_loop_control,
        "evaluator_control_artifact": evaluator_control_artifact.as_posix(),
        "executor_environment": executor_environment,
        "refactor_queue_artifact": refactor_queue_artifact.as_posix(),
        "proposal_queue_artifact": proposal_queue_artifact.as_posix(),
        "proposal_artifact_path": proposal_artifact_root_path.as_posix(),
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
    if operator_request_context:
        payload["operator_request_bridge"] = {
            "policy_reference": operator_request_bridge_policy_reference(),
            "packet_reference": str(operator_request_context.get("packet_reference", "")).strip(),
            "user_intent_handle": str(
                operator_request_context.get("user_intent_handle", "")
            ).strip(),
            "operator_request_handle": str(
                operator_request_context.get("operator_request_handle", "")
            ).strip(),
        }
        pre_spec_provenance = build_last_pre_spec_provenance(
            operator_request_context=operator_request_context,
            proposal_ids=proposal_ids_for_pre_spec,
        )
        if pre_spec_provenance is not None:
            payload["pre_spec_provenance"] = pre_spec_provenance
    log_path = write_run_log(run_id, payload)
    write_latest_summary(payload)
    record_operator_request_execution(
        operator_request_context=operator_request_context,
        run_id=run_id,
        spec_id=node.id,
        outcome=payload["outcome"],
        gate_state=str(payload.get("gate_state", "")),
        proposal_items=proposal_queue_after,
    )

    cleanup_isolated_worktree(worktree_path, branch)
    emit_run_footer(
        log_path=log_path,
        completion_status=payload["completion_status"],
        stdout=result.stdout,
        stderr=result.stderr,
        validation_findings=validation_findings,
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
    operator_request_context: dict[str, Any] | None = None,
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
    if operator_request_context:
        selected_by_rule["user_intent_handle"] = str(
            operator_request_context.get("user_intent_handle", "")
        ).strip()
        selected_by_rule["operator_request_handle"] = str(
            operator_request_context.get("operator_request_handle", "")
        ).strip()
        selected_by_rule["operator_request_packet"] = str(
            operator_request_context.get("packet_reference", "")
        ).strip()
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
    before_maturity = node.maturity
    source_spec_relpath = node.path.relative_to(ROOT).as_posix()
    run_id = make_run_id(node.id)
    run_started_at = utc_now_iso()
    run_started_monotonic = time.monotonic()
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
    outcome, blocker, executor_protocol_findings = parse_executor_protocol(
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
        child_materialization_errors = []
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
        validation_errors.extend(validation_messages(executor_protocol_findings))

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
                operator_request_context=operator_request_context,
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
    proposal_ids_for_pre_spec = sorted(
        {
            str(item.get("id", "")).strip()
            for item in proposal_queue_after
            if isinstance(item, dict)
            and str(item.get("spec_id", "")).strip() == node.id
            and str(item.get("operator_request_handle", "")).strip()
            == str((operator_request_context or {}).get("operator_request_handle", "")).strip()
            and str(item.get("id", "")).strip()
        }
    )

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
    validation_findings = []
    validation_findings.extend(executor_protocol_findings)
    validation_findings.extend(executor_environment_validation_findings(executor_environment))
    validation_findings.extend(
        string_errors_to_validation_findings(
            worktree_load_errors,
            family="yaml",
            error_class="parse_failure",
            code="worktree_spec_load_failure",
            spec_id=node.id,
        )
    )
    validation_findings.extend(
        string_errors_to_validation_findings(
            output_errors,
            family="output",
            error_class="contract_failure",
            code="output_contract_violation",
            spec_id=node.id,
        )
    )
    validation_findings.extend(
        string_errors_to_validation_findings(
            allowed_path_errors,
            family="authority",
            error_class="scope_violation",
            code="allowed_path_violation",
            spec_id=node.id,
        )
    )
    validation_findings.extend(
        string_errors_to_validation_findings(
            child_materialization_errors,
            family="authority",
            error_class="contract_failure",
            code="child_materialization_contract_failure",
            spec_id=node.id,
        )
    )
    validation_findings.extend(
        string_errors_to_validation_findings(
            reconciliation_errors,
            family="relation",
            error_class="relation_failure",
            code="graph_reconciliation_error",
            spec_id=node.id,
        )
    )
    validation_findings.extend(
        string_errors_to_validation_findings(
            atomicity_errors,
            family="acceptance",
            error_class="semantic_rejection",
            code="atomicity_violation",
            spec_id=node.id,
        )
    )
    validation_findings.extend(
        string_errors_to_validation_findings(
            transition_errors,
            family="transition",
            error_class="transition_failure",
            code="invalid_status_transition",
            spec_id=node.id,
        )
    )
    validation_findings.extend(
        string_errors_to_validation_findings(
            artifact_io_errors,
            family="artifact",
            error_class="artifact_integrity_failure",
            code="runtime_artifact_write_failure",
            spec_id=node.id,
        )
    )
    if structural_success and not accepted_refinement:
        validation_findings.extend(
            string_errors_to_validation_findings(
                list(refinement_acceptance["errors"]),
                family="acceptance",
                error_class="semantic_rejection",
                code="refinement_acceptance_rejection",
                spec_id=node.id,
            )
        )
    validation_errors = validation_messages(validation_findings)
    safe_repair_contract = build_safe_repair_contract(
        run_id=run_id,
        spec_id=node.id,
        repair_paths=yaml_repair_paths,
    )
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
    if operator_request_context:
        pre_spec_provenance = build_last_pre_spec_provenance(
            operator_request_context=operator_request_context,
            proposal_ids=proposal_ids_for_pre_spec,
        )
        if pre_spec_provenance is not None:
            node.data["last_pre_spec_provenance"] = pre_spec_provenance
    if validation_errors:
        node.data["last_errors"] = validation_errors
    else:
        node.data.pop("last_errors", None)

    decision_inspector = build_decision_inspector(
        run_id=run_id,
        spec_id=node.id,
        selected_by_rule=selected_by_rule,
        outcome=outcome,
        gate_state=str(node.data.get("gate_state", "none")),
        required_human_action=required_human_action,
        blocker=blocker,
        changed_files=changed,
        validation_findings=validation_findings,
        validator_results=validator_results,
        graph_health=graph_health,
        graph_health_truth_basis="accepted_canonical",
        proposal_queue_before=proposal_queue_before,
        proposal_queue_after=proposal_queue_after,
        refactor_queue_before=refactor_queue_before,
        refactor_queue_after=refactor_queue_after,
        refinement_acceptance=refinement_acceptance,
    )
    evaluator_loop_control = build_evaluator_loop_control(
        run_id=run_id,
        spec_id=node.id,
        selected_by_rule=selected_by_rule,
        outcome=outcome,
        gate_state=str(node.data.get("gate_state", "none")),
        blocker=blocker,
        required_human_action=required_human_action,
        graph_health=graph_health,
        validation_findings=validation_findings,
        safe_repair_contract=safe_repair_contract,
    )
    artifact_write_errors: list[str] = []
    decision_inspector_artifact = ""
    evaluator_control_artifact = ""
    safe_repair_artifact = ""
    try:
        decision_inspector_artifact = write_decision_inspector_artifact(
            run_id,
            decision_inspector,
        ).as_posix()
    except (OSError, RuntimeError) as exc:
        artifact_write_errors.append(str(exc))
    try:
        evaluator_control_artifact = write_evaluator_control_artifact(
            evaluator_loop_control
        ).as_posix()
    except (OSError, RuntimeError) as exc:
        artifact_write_errors.append(str(exc))
    if safe_repair_contract["repair_count"]:
        try:
            safe_repair_artifact = write_safe_repair_artifact(safe_repair_contract).as_posix()
        except (OSError, RuntimeError) as exc:
            artifact_write_errors.append(str(exc))

    if artifact_write_errors:
        artifact_io_errors.extend(artifact_write_errors)
        validation_findings.extend(
            string_errors_to_validation_findings(
                artifact_write_errors,
                family="artifact",
                error_class="artifact_integrity_failure",
                code="runtime_artifact_write_failure",
                spec_id=node.id,
            )
        )
        validation_errors = validation_messages(validation_findings)
        validator_results["runtime_artifacts"] = False
        success = False
        outcome = "blocked"
        blocker = blocker or "runtime artifact failure"
        node.data["gate_state"] = "blocked"
        clear_pending_review_state(node)
        required_human_action = "repair malformed runtime artifact and rerun supervisor"
        node.data["required_human_action"] = required_human_action
        node.data["last_outcome"] = outcome
        node.data["last_blocker"] = blocker
        node.data["last_validator_results"] = validator_results
        node.data["last_errors"] = validation_errors
        completion_status = classify_completion_status(
            success=success,
            productive_split_required=productive_split_required,
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
            validation_findings=validation_findings,
            validator_results=validator_results,
            graph_health=graph_health,
            graph_health_truth_basis="accepted_canonical",
            proposal_queue_before=proposal_queue_before,
            proposal_queue_after=proposal_queue_after,
            refactor_queue_before=refactor_queue_before,
            refactor_queue_after=refactor_queue_after,
            refinement_acceptance=refinement_acceptance,
        )
        evaluator_loop_control = build_evaluator_loop_control(
            run_id=run_id,
            spec_id=node.id,
            selected_by_rule=selected_by_rule,
            outcome=outcome,
            gate_state=str(node.data.get("gate_state", "none")),
            blocker=blocker,
            required_human_action=required_human_action,
            graph_health=graph_health,
            validation_findings=validation_findings,
            safe_repair_contract=safe_repair_contract,
        )
        decision_inspector_artifact = ""
        evaluator_control_artifact = ""
        safe_repair_artifact = ""

    node.save()
    if child_materialization_hint is not None:
        release_child_materialization_spec_id(
            spec_id=str(child_materialization_hint.get("id", "")).strip(),
            run_id=run_id,
        )
    run_finished_at = utc_now_iso()
    run_duration_sec = round(max(time.monotonic() - run_started_monotonic, 0.0), 3)
    run_kind = "graph_refactor" if is_graph_refactor_run else "ordinary_refine"
    accepted_canonical_diff = bool(success and node.data.get("gate_state") == "none") or bool(
        split_sync_allowed
    )
    payload = {
        "run_id": run_id,
        "timestamp_utc": run_finished_at,
        "started_at_utc": run_started_at,
        "finished_at_utc": run_finished_at,
        "run_duration_sec": run_duration_sec,
        "spec_id": node.id,
        "title": node.title,
        "run_kind": run_kind,
        "execution_profile": effective_execution_profile,
        "child_model": child_model or "",
        "completion_status": completion_status,
        "selected_by_rule": selected_by_rule,
        "before_status": before_status,
        "proposed_status": node.data.get("proposed_status"),
        "final_status": node.data.get("status"),
        "before_maturity": before_maturity,
        "final_maturity": node.maturity,
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
        "safe_repair_contract": safe_repair_contract,
        "safe_repair_artifact": safe_repair_artifact,
        "branch": branch,
        "changed_files": changed,
        "materialized_child_paths": materialized_child_paths,
        "new_child_materialized_count": len(materialized_child_paths),
        "accepted_canonical_diff": accepted_canonical_diff,
        "productive_split_required": productive_split_required,
        "validation_findings_policy": validation_findings_policy_reference(),
        "validation_findings": validation_findings,
        "validation_summary": validation_summary(validation_findings),
        "validation_errors": validation_errors,
        "validator_results": validator_results,
        "reconciliation": reconciliation,
        "graph_health": graph_health,
        "graph_health_truth_basis": "accepted_canonical",
        "decision_inspector": decision_inspector,
        "decision_inspector_artifact": decision_inspector_artifact,
        "evaluator_loop_control": evaluator_loop_control,
        "evaluator_control_artifact": evaluator_control_artifact,
        "executor_environment": executor_environment,
        "refinement_acceptance": refinement_acceptance,
        "refactor_queue_artifact": refactor_queue_artifact.as_posix(),
        "proposal_queue_artifact": proposal_queue_artifact.as_posix(),
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
    if operator_request_context:
        payload["operator_request_bridge"] = {
            "policy_reference": operator_request_bridge_policy_reference(),
            "packet_reference": str(operator_request_context.get("packet_reference", "")).strip(),
            "user_intent_handle": str(
                operator_request_context.get("user_intent_handle", "")
            ).strip(),
            "operator_request_handle": str(
                operator_request_context.get("operator_request_handle", "")
            ).strip(),
        }
        pre_spec_provenance = build_last_pre_spec_provenance(
            operator_request_context=operator_request_context,
            proposal_ids=proposal_ids_for_pre_spec,
        )
        if pre_spec_provenance is not None:
            payload["pre_spec_provenance"] = pre_spec_provenance
    if candidate_graph_health != graph_health:
        payload["candidate_graph_health"] = candidate_graph_health
        payload["candidate_graph_health_truth_basis"] = "review_candidate"
    log_path = write_run_log(run_id, payload)
    write_latest_summary(payload)
    record_operator_request_execution(
        operator_request_context=operator_request_context,
        run_id=run_id,
        spec_id=node.id,
        outcome=payload["outcome"],
        gate_state=str(payload.get("gate_state", "")),
        proposal_items=proposal_queue_after,
    )

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
        validation_findings=validation_findings,
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
    operator_request_packet_path: str | None = None,
    build_intent_layer_overlay_mode: bool = False,
    build_vocabulary_index_mode: bool = False,
    build_vocabulary_drift_report_mode: bool = False,
    build_pre_spec_semantics_index_mode: bool = False,
    build_graph_health_overlay_mode: bool = False,
    build_graph_health_trends_mode: bool = False,
    build_spec_trace_index_mode: bool = False,
    build_spec_trace_projection_mode: bool = False,
    build_evidence_plane_index_mode: bool = False,
    build_evidence_plane_overlay_mode: bool = False,
    build_external_consumer_index_mode: bool = False,
    build_external_consumer_overlay_mode: bool = False,
    build_external_consumer_handoffs_mode: bool = False,
    build_specpm_export_preview_mode: bool = False,
    build_specpm_handoff_packets_mode: bool = False,
    materialize_specpm_export_bundles_mode: bool = False,
    build_specpm_import_preview_mode: bool = False,
    build_metric_signal_index_mode: bool = False,
    build_metric_threshold_proposals_mode: bool = False,
    build_supervisor_performance_index_mode: bool = False,
    build_graph_dashboard_mode: bool = False,
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

    standalone_modes = {
        "--validate-transition-packet": bool(validate_transition_packet_path),
        "--build-intent-layer-overlay": build_intent_layer_overlay_mode,
        "--build-vocabulary-index": build_vocabulary_index_mode,
        "--build-vocabulary-drift-report": build_vocabulary_drift_report_mode,
        "--build-pre-spec-semantics-index": build_pre_spec_semantics_index_mode,
        "--build-graph-health-overlay": build_graph_health_overlay_mode,
        "--build-graph-health-trends": build_graph_health_trends_mode,
        "--build-spec-trace-index": build_spec_trace_index_mode,
        "--build-spec-trace-projection": build_spec_trace_projection_mode,
        "--build-evidence-plane-index": build_evidence_plane_index_mode,
        "--build-evidence-plane-overlay": build_evidence_plane_overlay_mode,
        "--build-external-consumer-index": build_external_consumer_index_mode,
        "--build-external-consumer-overlay": build_external_consumer_overlay_mode,
        "--build-external-consumer-handoffs": build_external_consumer_handoffs_mode,
        "--build-specpm-export-preview": build_specpm_export_preview_mode,
        "--build-specpm-handoff-packets": build_specpm_handoff_packets_mode,
        "--materialize-specpm-export-bundles": materialize_specpm_export_bundles_mode,
        "--build-specpm-import-preview": build_specpm_import_preview_mode,
        "--build-metric-signal-index": build_metric_signal_index_mode,
        "--build-metric-threshold-proposals": build_metric_threshold_proposals_mode,
        "--build-supervisor-performance-index": build_supervisor_performance_index_mode,
        "--build-graph-dashboard": build_graph_dashboard_mode,
        "--build-proposal-lane-overlay": build_proposal_lane_overlay_mode,
        "--build-proposal-runtime-index": build_proposal_runtime_index_mode,
        "--build-proposal-promotion-index": build_proposal_promotion_index_mode,
    }
    enabled_standalone_modes = [name for name, enabled in standalone_modes.items() if enabled]
    if len(enabled_standalone_modes) > 1:
        print(
            "standalone commands cannot be combined: " + ", ".join(enabled_standalone_modes),
            file=sys.stderr,
        )
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
                build_vocabulary_index_mode,
                build_vocabulary_drift_report_mode,
                build_pre_spec_semantics_index_mode,
                build_graph_health_overlay_mode,
                build_graph_health_trends_mode,
                build_spec_trace_index_mode,
                build_spec_trace_projection_mode,
                build_evidence_plane_index_mode,
                build_evidence_plane_overlay_mode,
                build_proposal_lane_overlay_mode,
                build_proposal_runtime_index_mode,
                build_proposal_promotion_index_mode,
                operator_request_packet_path,
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

    if build_vocabulary_index_mode:
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
                operator_request_packet_path,
                build_intent_layer_overlay_mode,
                build_vocabulary_drift_report_mode,
                build_pre_spec_semantics_index_mode,
                build_graph_health_overlay_mode,
                build_graph_health_trends_mode,
                build_spec_trace_index_mode,
                build_spec_trace_projection_mode,
                build_evidence_plane_index_mode,
                build_evidence_plane_overlay_mode,
                build_proposal_lane_overlay_mode,
                build_proposal_runtime_index_mode,
                build_proposal_promotion_index_mode,
            )
        ):
            print(
                "--build-vocabulary-index must be used as a standalone command",
                file=sys.stderr,
            )
            return 1
        index = build_vocabulary_index()
        write_vocabulary_index(index)
        print(json.dumps(index, ensure_ascii=False, indent=2))
        return 0

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
                build_vocabulary_index_mode,
                build_vocabulary_drift_report_mode,
                build_pre_spec_semantics_index_mode,
                build_graph_health_overlay_mode,
                build_graph_health_trends_mode,
                build_spec_trace_index_mode,
                build_spec_trace_projection_mode,
                build_evidence_plane_index_mode,
                build_evidence_plane_overlay_mode,
                build_proposal_lane_overlay_mode,
                build_proposal_runtime_index_mode,
                build_proposal_promotion_index_mode,
                operator_request_packet_path,
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

    if build_external_consumer_index_mode:
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
                operator_request_packet_path,
                build_vocabulary_index_mode,
                build_vocabulary_drift_report_mode,
                build_pre_spec_semantics_index_mode,
                build_graph_health_overlay_mode,
                build_graph_health_trends_mode,
                build_spec_trace_index_mode,
                build_spec_trace_projection_mode,
                build_evidence_plane_index_mode,
                build_evidence_plane_overlay_mode,
                build_proposal_lane_overlay_mode,
                build_proposal_runtime_index_mode,
                build_proposal_promotion_index_mode,
            )
        ):
            print(
                "--build-external-consumer-index must be used as a standalone command",
                file=sys.stderr,
            )
            return 1
        index = build_external_consumer_index()
        write_external_consumer_index(index)
        print(json.dumps(index, ensure_ascii=False, indent=2))
        return 0

    if build_specpm_import_preview_mode:
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
                operator_request_packet_path,
                build_intent_layer_overlay_mode,
                build_vocabulary_index_mode,
                build_vocabulary_drift_report_mode,
                build_pre_spec_semantics_index_mode,
                build_graph_health_overlay_mode,
                build_graph_health_trends_mode,
                build_spec_trace_index_mode,
                build_spec_trace_projection_mode,
                build_evidence_plane_index_mode,
                build_evidence_plane_overlay_mode,
                build_external_consumer_overlay_mode,
                build_external_consumer_handoffs_mode,
                build_specpm_export_preview_mode,
                build_specpm_handoff_packets_mode,
                materialize_specpm_export_bundles_mode,
                build_metric_signal_index_mode,
                build_metric_threshold_proposals_mode,
                build_supervisor_performance_index_mode,
                build_graph_dashboard_mode,
                build_proposal_lane_overlay_mode,
                build_proposal_runtime_index_mode,
                build_proposal_promotion_index_mode,
            )
        ):
            print(
                "--build-specpm-import-preview must be used as a standalone command",
                file=sys.stderr,
            )
            return 1
        consumer_index = build_external_consumer_index()
        write_external_consumer_index(consumer_index)
        preview = build_specpm_import_preview(consumer_index)
        write_specpm_import_preview(preview)
        print(json.dumps(preview, ensure_ascii=False, indent=2))
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
                operator_request_packet_path,
                build_vocabulary_index_mode,
                build_vocabulary_drift_report_mode,
                build_pre_spec_semantics_index_mode,
                build_evidence_plane_index_mode,
                build_evidence_plane_overlay_mode,
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

    if build_supervisor_performance_index_mode:
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
                operator_request_packet_path,
                build_intent_layer_overlay_mode,
                build_vocabulary_index_mode,
                build_vocabulary_drift_report_mode,
                build_pre_spec_semantics_index_mode,
                build_graph_health_overlay_mode,
                build_graph_health_trends_mode,
                build_spec_trace_index_mode,
                build_spec_trace_projection_mode,
                build_evidence_plane_index_mode,
                build_evidence_plane_overlay_mode,
                build_external_consumer_index_mode,
                build_external_consumer_overlay_mode,
                build_external_consumer_handoffs_mode,
                build_metric_signal_index_mode,
                build_metric_threshold_proposals_mode,
                build_graph_dashboard_mode,
                build_proposal_runtime_index_mode,
                build_proposal_promotion_index_mode,
            )
        ):
            print(
                "--build-supervisor-performance-index must be used as a standalone command",
                file=sys.stderr,
            )
            return 1
        report = build_supervisor_performance_index()
        write_supervisor_performance_index(report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    try:
        specs = load_specs()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if not specs:
        print("No spec nodes found in specs/nodes")
        return 0

    if build_vocabulary_drift_report_mode:
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
                operator_request_packet_path,
                build_intent_layer_overlay_mode,
                build_vocabulary_index_mode,
                build_pre_spec_semantics_index_mode,
                build_graph_health_overlay_mode,
                build_graph_health_trends_mode,
                build_spec_trace_index_mode,
                build_spec_trace_projection_mode,
                build_evidence_plane_index_mode,
                build_evidence_plane_overlay_mode,
                build_proposal_lane_overlay_mode,
                build_proposal_runtime_index_mode,
                build_proposal_promotion_index_mode,
            )
        ):
            print(
                "--build-vocabulary-drift-report must be used as a standalone command",
                file=sys.stderr,
            )
            return 1
        report = build_vocabulary_drift_report(specs)
        write_vocabulary_drift_report(report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    if build_pre_spec_semantics_index_mode:
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
                operator_request_packet_path,
                build_intent_layer_overlay_mode,
                build_vocabulary_index_mode,
                build_vocabulary_drift_report_mode,
                build_graph_health_overlay_mode,
                build_graph_health_trends_mode,
                build_spec_trace_index_mode,
                build_spec_trace_projection_mode,
                build_evidence_plane_index_mode,
                build_evidence_plane_overlay_mode,
                build_proposal_lane_overlay_mode,
                build_proposal_runtime_index_mode,
                build_proposal_promotion_index_mode,
            )
        ):
            print(
                "--build-pre-spec-semantics-index must be used as a standalone command",
                file=sys.stderr,
            )
            return 1
        refresh_vocabulary_artifacts(specs)
        index = build_pre_spec_semantics_index(specs)
        write_pre_spec_semantics_index(index)
        print(json.dumps(index, ensure_ascii=False, indent=2))
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
                operator_request_packet_path,
                build_vocabulary_index_mode,
                build_vocabulary_drift_report_mode,
                build_pre_spec_semantics_index_mode,
                build_graph_health_trends_mode,
                build_spec_trace_index_mode,
                build_spec_trace_projection_mode,
                build_evidence_plane_index_mode,
                build_evidence_plane_overlay_mode,
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
                operator_request_packet_path,
                build_vocabulary_index_mode,
                build_vocabulary_drift_report_mode,
                build_pre_spec_semantics_index_mode,
                build_graph_health_overlay_mode,
                build_spec_trace_index_mode,
                build_spec_trace_projection_mode,
                build_evidence_plane_index_mode,
                build_evidence_plane_overlay_mode,
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
                operator_request_packet_path,
                build_vocabulary_index_mode,
                build_vocabulary_drift_report_mode,
                build_pre_spec_semantics_index_mode,
                build_proposal_lane_overlay_mode,
                build_spec_trace_projection_mode,
                build_evidence_plane_index_mode,
                build_evidence_plane_overlay_mode,
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
                build_vocabulary_index_mode,
                build_vocabulary_drift_report_mode,
                build_pre_spec_semantics_index_mode,
                build_evidence_plane_index_mode,
                build_evidence_plane_overlay_mode,
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

    if build_evidence_plane_index_mode:
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
                operator_request_packet_path,
                build_vocabulary_index_mode,
                build_vocabulary_drift_report_mode,
                build_pre_spec_semantics_index_mode,
                build_proposal_lane_overlay_mode,
                build_spec_trace_index_mode,
                build_spec_trace_projection_mode,
                build_evidence_plane_overlay_mode,
                build_proposal_runtime_index_mode,
                build_proposal_promotion_index_mode,
            )
        ):
            print(
                "--build-evidence-plane-index must be used as a standalone command",
                file=sys.stderr,
            )
            return 1
        index = build_evidence_plane_index(specs)
        write_evidence_plane_index(index)
        print(json.dumps(index, ensure_ascii=False, indent=2))
        return 0

    if build_evidence_plane_overlay_mode:
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
                operator_request_packet_path,
                build_vocabulary_index_mode,
                build_vocabulary_drift_report_mode,
                build_pre_spec_semantics_index_mode,
                build_proposal_lane_overlay_mode,
                build_spec_trace_index_mode,
                build_spec_trace_projection_mode,
                build_evidence_plane_index_mode,
                build_proposal_runtime_index_mode,
                build_proposal_promotion_index_mode,
            )
        ):
            print(
                "--build-evidence-plane-overlay must be used as a standalone command",
                file=sys.stderr,
            )
            return 1
        index = build_evidence_plane_index(specs)
        write_evidence_plane_index(index)
        overlay = build_evidence_plane_overlay(index)
        write_evidence_plane_overlay(overlay)
        print(json.dumps(overlay, ensure_ascii=False, indent=2))
        return 0

    if build_external_consumer_overlay_mode:
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
                operator_request_packet_path,
                build_vocabulary_index_mode,
                build_vocabulary_drift_report_mode,
                build_pre_spec_semantics_index_mode,
                build_intent_layer_overlay_mode,
                build_graph_health_overlay_mode,
                build_graph_health_trends_mode,
                build_spec_trace_index_mode,
                build_spec_trace_projection_mode,
                build_evidence_plane_index_mode,
                build_evidence_plane_overlay_mode,
                build_proposal_lane_overlay_mode,
                build_proposal_runtime_index_mode,
                build_proposal_promotion_index_mode,
            )
        ):
            print(
                "--build-external-consumer-overlay must be used as a standalone command",
                file=sys.stderr,
            )
            return 1
        consumer_index = build_external_consumer_index()
        write_external_consumer_index(consumer_index)
        metric_index = build_metric_signal_index(specs)
        write_metric_signal_index(metric_index)
        overlay = build_external_consumer_overlay(consumer_index, metric_index)
        write_external_consumer_overlay(overlay)
        print(json.dumps(overlay, ensure_ascii=False, indent=2))
        return 0

    if build_external_consumer_handoffs_mode:
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
                operator_request_packet_path,
                build_vocabulary_index_mode,
                build_vocabulary_drift_report_mode,
                build_pre_spec_semantics_index_mode,
                build_intent_layer_overlay_mode,
                build_graph_health_overlay_mode,
                build_graph_health_trends_mode,
                build_spec_trace_index_mode,
                build_spec_trace_projection_mode,
                build_evidence_plane_index_mode,
                build_evidence_plane_overlay_mode,
                build_proposal_lane_overlay_mode,
                build_proposal_runtime_index_mode,
                build_proposal_promotion_index_mode,
            )
        ):
            print(
                "--build-external-consumer-handoffs must be used as a standalone command",
                file=sys.stderr,
            )
            return 1
        consumer_index = build_external_consumer_index()
        write_external_consumer_index(consumer_index)
        metric_index = build_metric_signal_index(specs)
        write_metric_signal_index(metric_index)
        overlay = build_external_consumer_overlay(consumer_index, metric_index)
        write_external_consumer_overlay(overlay)
        threshold_proposals = build_metric_threshold_proposals(metric_index)
        write_metric_threshold_proposals(threshold_proposals)
        handoff_packets = build_external_consumer_handoff_packets(
            consumer_index,
            overlay,
            metric_index,
            threshold_proposals,
        )
        write_external_consumer_handoff_packets(handoff_packets)
        print(json.dumps(handoff_packets, ensure_ascii=False, indent=2))
        return 0

    if build_specpm_export_preview_mode:
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
                operator_request_packet_path,
            )
        ):
            print(
                "--build-specpm-export-preview must be used as a standalone command",
                file=sys.stderr,
            )
            return 1
        preview = build_specpm_export_preview(specs)
        write_specpm_export_preview(preview)
        print(json.dumps(preview, ensure_ascii=False, indent=2))
        return 0

    if build_specpm_handoff_packets_mode:
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
                operator_request_packet_path,
            )
        ):
            print(
                "--build-specpm-handoff-packets must be used as a standalone command",
                file=sys.stderr,
            )
            return 1
        preview = build_specpm_export_preview(specs)
        write_specpm_export_preview(preview)
        consumer_index = build_external_consumer_index()
        write_external_consumer_index(consumer_index)
        handoff_packets = build_specpm_handoff_packets(preview, consumer_index)
        write_specpm_handoff_packets(handoff_packets)
        print(json.dumps(handoff_packets, ensure_ascii=False, indent=2))
        return 0

    if materialize_specpm_export_bundles_mode:
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
                operator_request_packet_path,
            )
        ):
            print(
                "--materialize-specpm-export-bundles must be used as a standalone command",
                file=sys.stderr,
            )
            return 1
        consumer_index = build_external_consumer_index()
        write_external_consumer_index(consumer_index)
        preview = build_specpm_export_preview(specs)
        write_specpm_export_preview(preview)
        handoff_packets = build_specpm_handoff_packets(preview, consumer_index)
        write_specpm_handoff_packets(handoff_packets)
        report = materialize_specpm_export_bundles(handoff_packets)
        write_specpm_materialization_report(report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    if build_metric_signal_index_mode:
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
                operator_request_packet_path,
            )
        ):
            print(
                "--build-metric-signal-index must be used as a standalone command",
                file=sys.stderr,
            )
            return 1
        index = build_metric_signal_index(specs)
        write_metric_signal_index(index)
        print(json.dumps(index, ensure_ascii=False, indent=2))
        return 0

    if build_metric_threshold_proposals_mode:
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
                operator_request_packet_path,
            )
        ):
            print(
                "--build-metric-threshold-proposals must be used as a standalone command",
                file=sys.stderr,
            )
            return 1
        index = build_metric_signal_index(specs)
        write_metric_signal_index(index)
        report = build_metric_threshold_proposals(index)
        write_metric_threshold_proposals(report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    if build_graph_dashboard_mode:
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
                operator_request_packet_path,
            )
        ):
            print(
                "--build-graph-dashboard must be used as a standalone command",
                file=sys.stderr,
            )
            return 1
        report = build_graph_dashboard(specs)
        write_graph_dashboard(report)
        print(json.dumps(report, ensure_ascii=False, indent=2))
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
                operator_request_packet_path,
                build_vocabulary_index_mode,
                build_vocabulary_drift_report_mode,
                build_pre_spec_semantics_index_mode,
                build_proposal_lane_overlay_mode,
                build_evidence_plane_index_mode,
                build_evidence_plane_overlay_mode,
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
                operator_request_packet_path,
                build_vocabulary_index_mode,
                build_vocabulary_drift_report_mode,
                build_pre_spec_semantics_index_mode,
                build_proposal_lane_overlay_mode,
                build_evidence_plane_index_mode,
                build_evidence_plane_overlay_mode,
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
                operator_request_packet_path,
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

    operator_request_context: dict[str, Any] | None = None
    if operator_request_packet_path:
        if any(
            (
                resolve_gate,
                decision,
                apply_split_proposal,
                loop,
                observe_graph_health_mode,
                list_stale_runtime,
                clean_stale_runtime,
            )
        ):
            print(
                "--operator-request-packet cannot be combined with gate, loop, observation, "
                "or runtime-cleanup modes",
                file=sys.stderr,
            )
            return 1
        if any(
            (
                target_spec,
                split_proposal,
                operator_note,
                mutation_budget,
                run_authority,
                execution_profile,
            )
        ):
            print(
                "--operator-request-packet must be the sole steering surface for the run",
                file=sys.stderr,
            )
            return 1
        operator_request_context, request_errors = normalize_operator_request_packet(
            Path(operator_request_packet_path),
            specs=specs,
        )
        if request_errors:
            for error in request_errors:
                print(error, file=sys.stderr)
            return 1
        if not dry_run:
            bridge_record = sync_intent_layer_from_operator_request(operator_request_context)
            operator_request_context = {**operator_request_context, **bridge_record}
        request = operator_request_context["operator_request"]
        target_spec = str(request.get("target_spec_id", "")).strip()
        operator_note = str(request.get("operator_note", "")).strip()
        mutation_budget = tuple(request.get("mutation_budget", ()))
        run_authority = tuple(request.get("run_authority", ()))
        execution_profile = request.get("execution_profile")
        split_proposal = str(request.get("run_mode", "")).strip() == "split_proposal"

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
        if operator_request_context:
            selected_by_rule["user_intent_handle"] = str(
                operator_request_context.get("user_intent_handle", "")
            ).strip()
            selected_by_rule["operator_request_handle"] = str(
                operator_request_context.get("operator_request_handle", "")
            ).strip()
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
        if callable_supports_keyword(_process_split_refactor_proposal, "operator_request_context"):
            proposal_kwargs["operator_request_context"] = operator_request_context
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
        if operator_request_context:
            selected_by_rule["user_intent_handle"] = str(
                operator_request_context.get("user_intent_handle", "")
            ).strip()
            selected_by_rule["operator_request_handle"] = str(
                operator_request_context.get("operator_request_handle", "")
            ).strip()
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
        if callable_supports_keyword(_process_one_spec, "operator_request_context"):
            process_kwargs["operator_request_context"] = operator_request_context
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
        "--operator-request-packet",
        metavar="PATH",
        help=(
            "Normalize one bounded operator-request packet into a targeted supervisor run "
            "without using ad hoc target/operator/mutation flags directly"
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
        "--build-vocabulary-index",
        action="store_true",
        help=(
            "Build a flattened shared vocabulary index for canonical terms, aliases, "
            "deprecated aliases, families, and contexts"
        ),
    )
    parser.add_argument(
        "--build-vocabulary-drift-report",
        action="store_true",
        help=(
            "Build a derived vocabulary drift report that flags undefined terms, "
            "alias collisions, deprecated alias usage, and meaning divergence"
        ),
    )
    parser.add_argument(
        "--build-pre-spec-semantics-index",
        action="store_true",
        help=(
            "Build a derived pre-spec semantics index that links tracked intent-layer "
            "artifacts to downstream proposal-lane and canonical lineage"
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
        "--build-evidence-plane-index",
        action="store_true",
        help=(
            "Build a derived evidence-plane index that links canonical specs to declared "
            "artifact surfaces, runtime entities, and observation/outcome/adoption evidence"
        ),
    )
    parser.add_argument(
        "--build-evidence-plane-overlay",
        action="store_true",
        help=(
            "Build a viewer/inspection overlay from the evidence plane, grouped by chain "
            "status and next evidence gap"
        ),
    )
    parser.add_argument(
        "--build-external-consumer-index",
        action="store_true",
        help=(
            "Build a derived bridge index for declared external consumers such as Metrics/SIB, "
            "including stable-vs-draft reference state and local checkout availability"
        ),
    )
    parser.add_argument(
        "--build-external-consumer-overlay",
        action="store_true",
        help=(
            "Build a viewer/backlog overlay for sibling-consumer bridges, including bridge "
            "state, bound metric pressure, and next-gap backlog"
        ),
    )
    parser.add_argument(
        "--build-external-consumer-handoffs",
        action="store_true",
        help=(
            "Build reviewable sibling-consumer handoff packets from stable bridge readiness "
            "and current metric-threshold pressure"
        ),
    )
    parser.add_argument(
        "--build-specpm-export-preview",
        action="store_true",
        help=(
            "Build a reviewable SpecPM package preview from the declared SpecPM export "
            "registry and current external-consumer bridge state"
        ),
    )
    parser.add_argument(
        "--build-specpm-handoff-packets",
        action="store_true",
        help=(
            "Build reviewable SpecPM handoff packets from the current SpecPM export preview "
            "and external-consumer identity data"
        ),
    )
    parser.add_argument(
        "--materialize-specpm-export-bundles",
        action="store_true",
        help=(
            "Materialize local draft SpecPM export bundles into the sibling SpecPM checkout "
            "from the current handoff packets, without auto-committing there"
        ),
    )
    parser.add_argument(
        "--build-specpm-import-preview",
        action="store_true",
        help=(
            "Build a reviewable SpecPM import preview from local bundles in the sibling "
            "SpecPM checkout without mutating canonical SpecGraph specs"
        ),
    )
    parser.add_argument(
        "--build-metric-signal-index",
        action="store_true",
        help=(
            "Build a derived metric signal index from trace, evidence, graph-health, and "
            "proposal-runtime surfaces without turning metrics into canonical facts"
        ),
    )
    parser.add_argument(
        "--build-metric-threshold-proposals",
        action="store_true",
        help=(
            "Build reviewable proposal artifacts from metric-threshold breaches so thresholds "
            "pressure proposal flow before any policy mutation"
        ),
    )
    parser.add_argument(
        "--build-supervisor-performance-index",
        action="store_true",
        help=(
            "Build a derived supervisor performance index from historical run logs, including "
            "runtime cleanliness, yield, and graph-impact summaries"
        ),
    )
    parser.add_argument(
        "--build-graph-dashboard",
        action="store_true",
        help=(
            "Build an aggregated graph dashboard with headline counts from graph health, "
            "proposal, implementation, evidence, and metric surfaces"
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
            operator_request_packet_path=args.operator_request_packet,
            build_intent_layer_overlay_mode=args.build_intent_layer_overlay,
            build_vocabulary_index_mode=args.build_vocabulary_index,
            build_vocabulary_drift_report_mode=args.build_vocabulary_drift_report,
            build_pre_spec_semantics_index_mode=args.build_pre_spec_semantics_index,
            build_graph_health_overlay_mode=args.build_graph_health_overlay,
            build_graph_health_trends_mode=args.build_graph_health_trends,
            build_spec_trace_index_mode=args.build_spec_trace_index,
            build_spec_trace_projection_mode=args.build_spec_trace_projection,
            build_evidence_plane_index_mode=args.build_evidence_plane_index,
            build_evidence_plane_overlay_mode=args.build_evidence_plane_overlay,
            build_external_consumer_index_mode=args.build_external_consumer_index,
            build_external_consumer_overlay_mode=args.build_external_consumer_overlay,
            build_external_consumer_handoffs_mode=args.build_external_consumer_handoffs,
            build_specpm_export_preview_mode=args.build_specpm_export_preview,
            build_specpm_handoff_packets_mode=args.build_specpm_handoff_packets,
            materialize_specpm_export_bundles_mode=args.materialize_specpm_export_bundles,
            build_specpm_import_preview_mode=args.build_specpm_import_preview,
            build_metric_signal_index_mode=args.build_metric_signal_index,
            build_metric_threshold_proposals_mode=args.build_metric_threshold_proposals,
            build_supervisor_performance_index_mode=args.build_supervisor_performance_index,
            build_graph_dashboard_mode=args.build_graph_dashboard,
            build_proposal_lane_overlay_mode=args.build_proposal_lane_overlay,
            build_proposal_runtime_index_mode=args.build_proposal_runtime_index,
            build_proposal_promotion_index_mode=args.build_proposal_promotion_index,
        )
    )
