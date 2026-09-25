"""Narrow, inert read model for product-workspace next-move advice.

This module reads only the selected product workspace and the declared project
environment policy. It deliberately does not import the bootstrap supervisor.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

from yaml import YAMLError

from spec_yaml import load_yaml_text

PROJECT_POLICY_PATH = Path(__file__).with_name("project_environment_policy.json")


@dataclass(frozen=True)
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
    def allowed_paths(self) -> list[str]:
        value = self.data.get("allowed_paths", [])
        return list(value) if isinstance(value, list) else []


def load_product_policy() -> dict[str, Any]:
    policy = json.loads(PROJECT_POLICY_PATH.read_text(encoding="utf-8"))
    if policy.get("artifact_kind") != "project_environment_policy":
        raise ValueError("invalid project environment policy")
    return policy


def safe_workspace_path(value: Any) -> bool:
    text = str(value or "").strip()
    return bool(text) and not (
        text.startswith(("/", "~"))
        or "\\" in text
        or ":" in text
        or ".." in PurePosixPath(text).parts
    )


def product_environment(config_path: Path, policy: dict[str, Any]) -> dict[str, Any]:
    try:
        config = load_yaml_text(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, YAMLError) as exc:
        raise ValueError(f"invalid product workspace config: {exc}") from exc
    if config.get("artifact_kind") != "specgraph_project_config":
        raise ValueError("a valid product_workspace project config is required")
    if config.get("governance_profile") != "product_workspace":
        raise ValueError("a valid product_workspace project config is required")
    profile = next(
        (
            item
            for item in policy.get("governance_profiles", [])
            if isinstance(item, dict) and item.get("profile_id") == "product_workspace"
        ),
        None,
    )
    if profile is None:
        raise ValueError("product_workspace profile is absent from project environment policy")
    workspace = config.get("workspace")
    if not isinstance(workspace, dict):
        raise ValueError("a valid product_workspace project config is required")
    required_fields = policy.get("workspace_contract", {}).get("required_fields", [])
    for field in required_fields:
        if not safe_workspace_path(workspace.get(field)):
            raise ValueError(f"unsafe or missing workspace.{field}")
    supervisor = config.get("supervisor", {})
    if not isinstance(supervisor, dict):
        raise ValueError("invalid product workspace supervisor authority")
    authority_fields = (
        "allow_project_spec_refinement",
        "allow_project_proposals",
        "allow_project_retrospectives",
        "allow_core_policy_mutation",
        "allow_core_tooling_mutation",
        "allow_self_evolution_proposals",
    )
    authority: dict[str, bool] = {}
    for field in authority_fields:
        default = field in {
            "allow_project_spec_refinement",
            "allow_project_proposals",
            "allow_project_retrospectives",
        }
        flag = supervisor.get(field, default)
        if isinstance(flag, str):
            normalized = flag.strip().lower()
            if normalized in {"true", "false"}:
                flag = normalized == "true"
        if not isinstance(flag, bool):
            raise ValueError(f"supervisor.{field} must be boolean")
        authority[field] = flag
    contract = profile.get("enforcement_contract", {})
    if not isinstance(contract, dict):
        raise ValueError("invalid product_workspace enforcement contract")
    return {
        "project": {
            "project_id": str(
                config.get("project_id", policy.get("default_project_id", ""))
            ).strip(),
            "governance_profile": "product_workspace",
        },
        "supervisor_authority": authority,
        "governance_enforcement": {
            "forbidden_target_domains": contract.get("forbidden_target_domains", []),
            "forbidden_mutation_roots": contract.get(
                "forbidden_mutation_roots", profile.get("forbidden_mutation_roots", [])
            ),
        },
    }


def load_specs_from_dir(specs_dir: Path) -> list[SpecNode]:
    nodes: list[SpecNode] = []
    for path in sorted(specs_dir.glob("*.yaml")):
        try:
            data = load_yaml_text(path.read_text(encoding="utf-8"))
        except (ValueError, YAMLError) as exc:
            raise ValueError(f"canonical spec nodes must be mappings: {path.name} ({exc})") from exc
        nodes.append(SpecNode(path=path, data=data))
    return nodes


def subtree_nodes(node: SpecNode, specs: list[SpecNode]) -> list[SpecNode]:
    index = {spec.id: spec for spec in specs if spec.id}
    children_by_parent: dict[str, list[SpecNode]] = {}
    for spec in specs:
        refines = spec.data.get("refines")
        if isinstance(refines, list):
            for parent in {str(item).strip() for item in refines}:
                children_by_parent.setdefault(parent, []).append(spec)
    seen: set[str] = set()
    ordered: list[SpecNode] = []
    stack = [node]
    while stack:
        current = stack.pop()
        if not current.id or current.id in seen:
            continue
        seen.add(current.id)
        ordered.append(current)
        for child in reversed(children_by_parent.get(current.id, [])):
            stack.append(index.get(child.id, child))
    return ordered


def effective_allowed_paths_for_run(node: SpecNode, root: Path) -> list[str]:
    paths = [str(path).strip() for path in node.allowed_paths if str(path).strip()]
    return paths or [node.path.relative_to(root).as_posix()]


def path_matches_root(path_text: str, root_text: str) -> bool:
    path = str(path_text).strip()
    root = str(root_text).strip()
    if not path or not root:
        return False
    if root.endswith("/"):
        return path.startswith(root)
    return path == root or path.startswith(root.rstrip("/") + "/")


def path_pattern_may_match_root(path_text: str, root_text: str) -> bool:
    path = str(path_text).strip()
    root = str(root_text).strip()
    if not path or not root:
        return False
    if not any(marker in path for marker in ("*", "?", "[")):
        return path_matches_root(path, root)
    literal_parts: list[str] = []
    for part in PurePosixPath(path).parts:
        if any(marker in part for marker in ("*", "?", "[")):
            break
        literal_parts.append(part)
    literal_prefix = "/".join(literal_parts).strip("/")
    if not literal_prefix:
        return True
    return path_matches_root(literal_prefix, root) or path_matches_root(root, literal_prefix)


def authorize_target(
    *, target_spec_id: str, target_paths: list[str], environment: dict[str, Any]
) -> dict[str, Any]:
    enforcement = environment["governance_enforcement"]
    forbidden_domains = {
        str(item).strip() for item in enforcement["forbidden_target_domains"] if str(item).strip()
    }
    forbidden_roots = [
        str(item).strip() for item in enforcement["forbidden_mutation_roots"] if str(item).strip()
    ]
    blocked_paths = sorted(
        path
        for path in target_paths
        if any(path_pattern_may_match_root(path, root) for root in forbidden_roots)
    )
    target_domain = "specgraph_core" if target_spec_id.startswith("SG-SPEC-") else "project_graph"
    blocked_by: list[str] = []
    if target_domain in forbidden_domains:
        blocked_by.append("blocked_by_governance_profile")
    if blocked_paths:
        blocked_by.append("blocked_by_forbidden_mutation_root")
    return {
        "authorized": not blocked_by,
        "blocked_by": blocked_by,
        "target_domain": target_domain,
    }
