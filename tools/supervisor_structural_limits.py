"""Pure, versioned workspace structural policy resolution (proposal 0222)."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any

COUNT_KEYS = frozenset(
    {
        "atomicity_max_acceptance",
        "atomicity_max_blocking_children",
        "subtree_shape_one_child_chain",
        "refinement_fan_out_direct_children",
        "graph_layer_exhausted_chain",
        "over_atomized_acceptance_max",
    }
)
RATIO_KEYS = frozenset(
    {
        "refinement_fan_out_grouped_child_coverage",
        "refinement_fan_out_parent_aggregate_floor",
        "subtree_shape_min_single_child_ratio",
    }
)


def validate_thresholds(values: dict[str, Any]) -> None:
    for key, value in values.items():
        if key in COUNT_KEYS:
            valid = type(value) is int and value > 0
        elif key in RATIO_KEYS:
            valid = type(value) in (int, float) and 0 <= value <= 1 and math.isfinite(value)
        else:
            raise RuntimeError(f"unsupported structural limit: {key}")
        if not valid:
            raise RuntimeError(f"invalid structural limit {key}: {value!r}")


def threshold_digest(values: dict[str, Any]) -> str:
    raw = json.dumps(values, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(raw.encode()).hexdigest()


@dataclass(frozen=True)
class StructuralLimits:
    thresholds: tuple[tuple[str, int | float], ...]
    overrides: frozenset[str]
    config_sha256: str
    config_status: str
    policy_sha256: str

    def value(self, key: str) -> int | float:
        return dict(self.thresholds)[key]

    def evidence(self) -> dict[str, Any]:
        values = dict(self.thresholds)
        return {
            "schema_version": 1,
            "effective_thresholds": values,
            "effective_sha256": threshold_digest(values),
            "sources": {
                key: "workspace" if key in self.overrides else "repository" for key in values
            },
            "source_config": {
                "artifact_path": "specgraph.project.yaml",
                "artifact_sha256": self.config_sha256,
                "status": self.config_status,
            },
            "source_policy": {
                "artifact_path": "tools/supervisor_policy.json",
                "artifact_sha256": self.policy_sha256,
            },
        }


def resolve_structural_limits(
    config: dict[str, Any],
    defaults: dict[str, Any],
    *,
    config_sha256: str,
    config_status: str,
    policy_sha256: str,
) -> StructuralLimits:
    supervisor = config.get("supervisor", {})
    if not isinstance(supervisor, dict):
        raise RuntimeError("supervisor config must be a mapping")
    overrides: dict[str, Any] = {}
    if "structural_limits" in supervisor:
        if config.get("artifact_kind") != "specgraph_project_config":
            raise RuntimeError("structural_limits requires specgraph_project_config")
        if type(config.get("schema_version")) is not int or config["schema_version"] != 1:
            raise RuntimeError("structural_limits requires project schema_version 1")
        section = supervisor["structural_limits"]
        if not isinstance(section, dict) or set(section) != {"schema_version", "thresholds"}:
            raise RuntimeError("structural_limits requires only schema_version and thresholds")
        if type(section["schema_version"]) is not int or section["schema_version"] != 1:
            raise RuntimeError("unsupported structural_limits schema_version (expected 1)")
        overrides = section["thresholds"]
        if not isinstance(overrides, dict):
            raise RuntimeError("structural_limits.thresholds must be a mapping")
        validate_thresholds(overrides)
    values = {key: defaults[key] for key in sorted(COUNT_KEYS | RATIO_KEYS)}
    values.update(overrides)
    validate_thresholds(values)
    return StructuralLimits(
        tuple(values.items()), frozenset(overrides), config_sha256, config_status, policy_sha256
    )


def recorded_threshold(evidence: Any, key: str, legacy_default: int | float) -> int | float:
    """Historical diagnostics must not reinterpret a run under today's workspace config."""
    if evidence is None:
        return legacy_default
    if not isinstance(evidence, dict) or type(evidence.get("schema_version")) is not int:
        raise RuntimeError("malformed recorded structural_limits")
    values = evidence.get("effective_thresholds")
    if evidence["schema_version"] != 1 or not isinstance(values, dict):
        raise RuntimeError("unsupported recorded structural_limits")
    if set(values) != COUNT_KEYS | RATIO_KEYS:
        raise RuntimeError("incomplete recorded structural_limits")
    validate_thresholds(values)
    if evidence.get("effective_sha256") != threshold_digest(values):
        raise RuntimeError("recorded structural_limits digest mismatch")
    return values[key]
