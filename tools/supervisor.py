#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
import sys
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from types import ModuleType
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None

ROOT = Path.cwd()
SPECS_DIR = ROOT / "specs" / "nodes"
RUNS_DIR = ROOT / "runs"
WORKTREES_DIR = ROOT / ".worktrees"
AGENTS_FILE = ROOT / "AGENTS.md"

READY_DEP_STATUSES = {"reviewed", "frozen"}
WORKABLE_STATUSES = {"outlined", "specified"}
VALID_STATUSES = {"idea", "stub", "outlined", "specified", "linked", "reviewed", "frozen"}
ATOMICITY_MAX_ACCEPTANCE = 5
ATOMICITY_MAX_BLOCKING_CHILDREN = 3
RECURRING_REFACTOR_PROPOSAL_THRESHOLD = 2
BLOCKING_GATE_STATES = {
    "review_pending",
    "blocked",
    "split_required",
    "redirected",
    "escalated",
}
ALLOWED_OUTCOMES = {"done", "retry", "split_required", "blocked", "escalate"}
SPEC_ID_PATTERN = re.compile(r"^SG-SPEC-(\d+)$")

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
    def allowed_paths(self) -> list[str]:
        return list(self.data.get("allowed_paths", []))

    def save(self) -> None:
        yaml_module = get_yaml_module()
        with self.path.open("w", encoding="utf-8") as file:
            yaml_module.safe_dump(self.data, file, sort_keys=False, allow_unicode=True)

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
) -> str:
    if refactor_work_item is not None:
        return "graph_refactor"
    local_specs = specs or load_specs()
    index = index_specs(local_specs)
    if is_ancestor_reconcile_candidate(node, index) and not is_gate_blocking(node):
        return "ancestor_reconcile"
    return "default_refine"


def is_seed_like_spec(node_data: dict[str, Any]) -> bool:
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
        return None

    candidates.sort(key=lambda spec: (dependents.get(spec.id, 0), spec.maturity, spec.id))
    return candidates[0]


def load_refactor_queue() -> list[dict[str, Any]]:
    path = refactor_queue_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def load_proposal_queue() -> list[dict[str, Any]]:
    path = proposal_queue_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(data, list):
        return []
    return [item for item in data if isinstance(item, dict)]


def refactor_signal_priority(signal: str) -> int:
    return {
        "missing_dependency_target": 0,
        "weak_structural_linkage_candidate": 1,
        "oversized_spec": 2,
    }.get(signal, 9)


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
    proposal_items = load_proposal_queue()
    refactor_candidate = pick_next_refactor_work_item(specs, proposal_items=proposal_items)
    if refactor_candidate is not None:
        return refactor_candidate
    node = pick_next_spec_gap(specs)
    return node, None


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


def next_sequential_spec_id(specs: list[SpecNode]) -> str:
    max_number = 0
    for spec in specs:
        match = SPEC_ID_PATTERN.match(spec.id)
        if match:
            max_number = max(max_number, int(match.group(1)))
    return f"SG-SPEC-{max_number + 1:04d}"


def can_create_new_spec_files(node: SpecNode) -> bool:
    if not node.allowed_paths:
        return True
    sample_path = PurePosixPath("specs/nodes/SG-SPEC-9999.yaml")
    return any(sample_path.match(pattern) for pattern in node.allowed_paths)


def bootstrap_child_hint(node: SpecNode, specs: list[SpecNode]) -> dict[str, str] | None:
    if not can_create_new_spec_files(node):
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
    return {
        "id": child_id,
        "path": child_path,
    }


def build_prompt(node: SpecNode, refactor_work_item: dict[str, Any] | None = None) -> str:
    agents_hint = ""
    if AGENTS_FILE.exists():
        agents_hint = "Read and follow AGENTS.md before editing anything.\n\n"

    allowed_paths = "\n".join(f"- {path}" for path in node.allowed_paths) or "- (not specified)"
    outputs = "\n".join(f"- {path}" for path in node.outputs) or "- (not specified)"
    bootstrap_hint = bootstrap_child_hint(node, load_specs())
    selection_mode = selection_mode_for_node(node, refactor_work_item=refactor_work_item)
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
    if selection_mode == "ancestor_reconcile":
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

    return f"""
You are refining a specification node in SpecGraph.

{agents_hint}Spec node ID: {node.id}
Title: {node.title}
Current status: {node.status}
Current maturity: {node.maturity:.2f}

Goal:
{node.prompt}

Allowed paths:
{allowed_paths}

Expected outputs:
{outputs}
{refinement_section}
{mode_section}
{bootstrap_section}

Rules:
- Refine specification only.
- Do not implement runtime code.
- Preserve stable IDs and terminology.
- Do not edit files outside allowed paths.
- Keep acceptance_evidence aligned 1:1 with acceptance criteria.
- If blocked, stop and explain blocker clearly.
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


def validate_allowed_paths(node: SpecNode, changed_files: list[str]) -> list[str]:
    if not node.allowed_paths:
        return []

    errors: list[str] = []
    for changed in changed_files:
        changed_path = PurePosixPath(changed)
        if not any(changed_path.match(pattern) for pattern in node.allowed_paths):
            errors.append(f"Changed file outside allowed_paths: {changed}")
    return errors


def select_sync_paths(allowed_paths: list[str], changed_files: list[str]) -> list[str]:
    """Return changed paths eligible for sync back to root.

    Empty allowed_paths means unrestricted sync.
    """
    if not allowed_paths:
        return list(changed_files)
    return [
        path
        for path in changed_files
        if any(PurePosixPath(path).match(pattern) for pattern in allowed_paths)
    ]


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
        if not str(item).strip():
            errors.append(f"acceptance_evidence[{idx}] must be non-empty")
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
        acceptance_errors: list[str] = []
        requires_acceptance_evidence = spec.id == source_node_id or spec.status not in {
            "idea",
            "stub",
            "outlined",
        }
        if requires_acceptance_evidence:
            acceptance_errors = validate_acceptance_evidence(spec.data)
        output_errors = validate_outputs(spec, base_dir=worktree_path)
        rel_path = spec.path.relative_to(worktree_path).as_posix()
        errors.extend(f"{rel_path}: {error}" for error in status_errors)
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
    index = index_specs(worktree_specs)
    observations: list[dict[str, Any]] = []
    signals: list[str] = []
    recommended_actions: list[str] = []

    reconciled_node = index.get(source_node.id)
    if reconciled_node is not None:
        local_atomicity = validate_atomicity(reconciled_node)
        if local_atomicity:
            observations.append(
                {
                    "kind": "oversized_spec",
                    "spec_id": source_node.id,
                    "details": local_atomicity,
                }
            )
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

    return {
        "source_spec_id": source_node.id,
        "observations": observations,
        "signals": sorted(set(signals)),
        "recommended_actions": sorted(set(recommended_actions)),
    }


def parse_outcome(stdout: str, returncode: int) -> tuple[str, str]:
    default_outcome = "done" if returncode == 0 else "escalate"

    outcome = default_outcome
    outcome_match = re.search(r"^RUN_OUTCOME:\s*([a-z_]+)\s*$", stdout, flags=re.MULTILINE)
    if outcome_match:
        candidate = outcome_match.group(1).strip().lower()
        if candidate in ALLOWED_OUTCOMES:
            outcome = candidate
        else:
            outcome = "escalate"

    blocker = ""
    blocker_match = re.search(r"^BLOCKER:\s*(.+)\s*$", stdout, flags=re.MULTILINE)
    if blocker_match:
        blocker = blocker_match.group(1).strip()
        if blocker.lower() == "none":
            blocker = ""

    return outcome, blocker


def utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def write_run_log(run_id: str, payload: dict[str, Any]) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = RUNS_DIR / f"{run_id}.json"
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
    return path


def refactor_queue_path() -> Path:
    return RUNS_DIR / "refactor_queue.json"


def proposal_queue_path() -> Path:
    return RUNS_DIR / "proposal_queue.json"


def run_log_paths() -> list[Path]:
    return sorted(RUNS_DIR.glob("*-SG-SPEC-*.json"))


def classify_refactor_work_item(signal: str) -> str:
    if signal in {"repeated_split_required_candidate", "stalled_maturity_candidate"}:
        return "governance_proposal"
    return "graph_refactor"


def default_action_for_signal(signal: str) -> str:
    return {
        "oversized_spec": "split_or_narrow_spec",
        "missing_dependency_target": "repair_canonical_dependencies",
        "repeated_split_required_candidate": "review_decomposition_policy",
        "stalled_maturity_candidate": "review_refinement_strategy",
        "weak_structural_linkage_candidate": "repair_refinement_chain",
    }.get(signal, "review_graph_health_signal")


def proposal_is_active(item: dict[str, Any]) -> bool:
    status = str(item.get("status", "proposed")).strip()
    return status in {"proposed", "review_pending", "pending_review"}


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
    return "direct_graph_update"


def classify_proposal_type(work_item_type: str) -> str:
    if work_item_type == "governance_proposal":
        return "governance_proposal"
    return "refactor_proposal"


def proposal_threshold_for_work_item_type(work_item_type: str) -> int:
    if work_item_type == "governance_proposal":
        return 1
    return RECURRING_REFACTOR_PROPOSAL_THRESHOLD


def signal_supporting_run_ids(spec_id: str, signal: str) -> list[str]:
    run_ids: list[str] = []
    for path in run_log_paths():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
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
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = refactor_queue_path()
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(existing, list):
            existing = []
    else:
        existing = []

    source_spec_id = str(graph_health.get("source_spec_id", "")).strip()
    preserved = [
        item
        for item in existing
        if isinstance(item, dict) and str(item.get("spec_id", "")).strip() != source_spec_id
    ]
    updated = preserved + build_refactor_queue_items(
        graph_health=graph_health,
        run_id=run_id,
        proposal_items=proposal_items,
    )
    path.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding="utf-8")
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
        threshold = proposal_threshold_for_work_item_type(work_item_type)
        if occurrence_count < threshold:
            continue

        proposal_type = classify_proposal_type(work_item_type)
        items.append(
            {
                "id": f"{proposal_type}::{source_spec_id}::{signal_name}",
                "proposal_type": proposal_type,
                "spec_id": source_spec_id,
                "signal": signal_name,
                "recommended_action": default_action_for_signal(signal_name),
                "status": "proposed",
                "trigger": (
                    "governance_class_signal"
                    if work_item_type == "governance_proposal"
                    else "recurring_signal"
                ),
                "occurrence_count": occurrence_count,
                "threshold": threshold,
                "supporting_run_ids": supporting_run_ids,
                "source_work_item_type": work_item_type,
                "execution_policy": "emit_proposal",
                "details": observation_by_kind.get(signal_name, {}).get("details"),
            }
        )
    return items


def update_proposal_queue(
    *,
    graph_health: dict[str, Any],
    run_id: str,
) -> tuple[Path, list[dict[str, Any]]]:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    path = proposal_queue_path()
    if path.exists():
        existing = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(existing, list):
            existing = []
    else:
        existing = []

    source_spec_id = str(graph_health.get("source_spec_id", "")).strip()
    preserved = [
        item
        for item in existing
        if isinstance(item, dict) and str(item.get("spec_id", "")).strip() != source_spec_id
    ]
    updated = preserved + build_proposal_queue_items(graph_health=graph_health, run_id=run_id)
    path.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding="utf-8")
    return path, updated


def write_latest_summary(payload: dict[str, Any]) -> None:
    summary = (
        f"# Latest Supervisor Run\n\n"
        f"- run_id: {payload['run_id']}\n"
        f"- spec_id: {payload['spec_id']}\n"
        f"- title: {payload['title']}\n"
        f"- outcome: {payload['outcome']}\n"
        f"- gate_state: {payload['gate_state']}\n"
        f"- before_status: {payload['before_status']}\n"
        f"- proposed_status: {payload.get('proposed_status') or '-'}\n"
        f"- final_status: {payload['final_status']}\n"
        f"- validation_errors: {len(payload['validation_errors'])}\n"
        f"- required_human_action: {payload.get('required_human_action', '-')}\n"
    )
    (RUNS_DIR / "latest-summary.md").write_text(summary, encoding="utf-8")


def sanitize_for_git(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]", "-", value).strip("-._").lower()
    return slug or "spec"


def create_isolated_worktree(node_id: str) -> tuple[Path, str]:
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_id = sanitize_for_git(node_id)
    branch = f"codex/{safe_id}/{timestamp}"
    worktree_path = WORKTREES_DIR / f"{safe_id}-{timestamp}"

    WORKTREES_DIR.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["git", "worktree", "add", "-b", branch, worktree_path.as_posix(), "HEAD"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "failed to create worktree")

    return worktree_path, branch


def sync_current_node_into_worktree(node: SpecNode, worktree_path: Path) -> Path:
    worktree_node_path = worktree_path / node.path.relative_to(ROOT)
    worktree_node_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(node.path, worktree_node_path)
    return worktree_node_path


def sync_files_from_worktree(worktree_path: Path, rel_paths: list[str]) -> None:
    for rel_path in rel_paths:
        src = worktree_path / rel_path
        dst = ROOT / rel_path
        if src.exists() and src.is_file():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            continue
        if dst.exists() and dst.is_file():
            dst.unlink()


def run_codex(
    node: SpecNode,
    worktree_path: Path,
    refactor_work_item: dict[str, Any] | None = None,
) -> subprocess.CompletedProcess[str]:
    cmd = [
        "codex",
        "exec",
        "-c",
        'model_reasoning_effort="medium"',
        build_prompt(node, refactor_work_item),
    ]
    print(f"Launching codex exec for {node.id} in {worktree_path}")
    process = subprocess.Popen(
        cmd,
        cwd=worktree_path,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    stdout_chunks: list[str] = []
    stderr_chunks: list[str] = []

    def _forward(stream: Any, sink: list[str], prefix: str, target: Any) -> None:
        try:
            for line in iter(stream.readline, ""):
                sink.append(line)
                print(f"{prefix}{line}", end="", file=target)
        finally:
            stream.close()

    stdout_thread = threading.Thread(
        target=_forward,
        args=(process.stdout, stdout_chunks, "[codex stdout] ", sys.stdout),
        daemon=True,
    )
    stderr_thread = threading.Thread(
        target=_forward,
        args=(process.stderr, stderr_chunks, "[codex stderr] ", sys.stderr),
        daemon=True,
    )
    stdout_thread.start()
    stderr_thread.start()
    returncode = process.wait()
    stdout_thread.join()
    stderr_thread.join()

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

    if decision == "approve":
        if node.gate_state != "review_pending":
            print(f"Spec {spec_id} is not in review_pending gate.", file=sys.stderr)
            return 1

        proposed_status = node.data.get("proposed_status")
        proposed_maturity = node.data.get("proposed_maturity")
        transition_errors = validate_transition(node.status, proposed_status)
        if transition_errors:
            print("\n".join(transition_errors), file=sys.stderr)
            return 1

        worktree_path = Path(str(node.data.get("last_worktree_path", ""))).expanduser()
        changed_files = list(node.data.get("last_changed_files", []))
        if worktree_path.as_posix() and worktree_path.exists():
            allowed_changes = select_sync_paths(node.allowed_paths, changed_files)
            sync_files_from_worktree(worktree_path, allowed_changes)
            # Keep approved content from the worktree while attaching gate metadata in root.
            node.reload()

        if proposed_status:
            node.data["status"] = proposed_status
        if proposed_maturity is not None:
            node.data["maturity"] = proposed_maturity

        node.data["gate_state"] = "none"
        node.data["proposed_status"] = None
        node.data["proposed_maturity"] = None
        node.data["required_human_action"] = "-"
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

    node.data["last_gate_decision"] = decision
    node.data["last_gate_note"] = note
    node.data["last_gate_at"] = utc_now_iso()
    node.save()

    print(f"Resolved gate for {spec_id}: {decision}")
    return 0


def _process_one_spec(
    *,
    node: SpecNode,
    specs: list[SpecNode],
    executor: Callable[[SpecNode, Path], subprocess.CompletedProcess[str]],
    auto_approve: bool,
    refactor_work_item: dict[str, Any] | None = None,
) -> tuple[int, str]:
    """Process a single spec node. Returns (exit_code, outcome)."""
    is_graph_refactor_run = (
        refactor_work_item is not None
        and str(refactor_work_item.get("work_item_type", "")).strip() == "graph_refactor"
    )
    dependents = reverse_dependents_count(specs)
    selection_mode = selection_mode_for_node(node, specs, refactor_work_item=refactor_work_item)
    selected_by_rule = {
        "status_filter": sorted(WORKABLE_STATUSES),
        "dependency_required_statuses": sorted(READY_DEP_STATUSES),
        "selection_mode": selection_mode,
        "sort_order": [
            "refactor_queue_first",
            "ancestor_reconcile_first",
            "nearest_unlocked_ancestor",
            "leaf_first",
            "lower_maturity",
            "stable_id",
        ],
        "dependents_count": dependents.get(node.id, 0),
    }
    if refactor_work_item is not None:
        selected_by_rule["refactor_work_item"] = {
            "id": str(refactor_work_item.get("id", "")),
            "work_item_type": str(refactor_work_item.get("work_item_type", "")),
            "signal": str(refactor_work_item.get("signal", "")),
            "recommended_action": str(refactor_work_item.get("recommended_action", "")),
            "source_run_id": str(refactor_work_item.get("source_run_id", "")),
        }

    before_status = node.status

    try:
        worktree_path, branch = create_isolated_worktree(node.id)
    except RuntimeError as exc:
        print(f"Failed to create worktree: {exc}", file=sys.stderr)
        return 1, "escalate"
    print(f"Created worktree: {worktree_path}")
    print(f"Branch: {branch}")
    synced_node_path = sync_current_node_into_worktree(node, worktree_path)
    print(f"Seeded worktree node from current tree: {synced_node_path}")

    before = git_changed_files(worktree_path)
    tracked_paths = sorted(set(before))
    before_digests = snapshot_file_digests(tracked_paths, base_dir=worktree_path)
    print(f"Starting executor for {node.id}...")
    if executor is run_codex:
        result = executor(node, worktree_path, refactor_work_item)
    else:
        result = executor(node, worktree_path)
    print(f"Executor finished for {node.id} with exit_code={result.returncode}")
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
    print(f"Detected changed files: {changed or ['(none)']}")

    run_timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    run_id = f"{run_timestamp}-{node.id}"

    try:
        worktree_specs = load_specs_from_dir(worktree_path / "specs" / "nodes")
    except Exception as exc:
        worktree_specs = []
        worktree_load_errors = [f"Failed to load worktree specs for validation: {exc}"]
    else:
        worktree_load_errors = []

    output_errors = validate_outputs(node, base_dir=worktree_path)
    allowed_path_errors = validate_allowed_paths(node, changed)
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
    transition_errors = (
        [] if is_graph_refactor_run else validate_transition(node.status, proposed_status)
    )

    validation_errors: list[str] = []
    validation_errors.extend(output_errors)
    validation_errors.extend(allowed_path_errors)
    validation_errors.extend(reconciliation_errors)
    validation_errors.extend(atomicity_errors)
    validation_errors.extend(transition_errors)

    outcome, blocker = parse_outcome(result.stdout, result.returncode)
    if atomicity_errors and outcome == "done":
        outcome = "split_required"
        if not blocker:
            blocker = "spec exceeds atomicity quality gate"

    graph_health = observe_graph_health(
        source_node=node,
        worktree_specs=worktree_specs,
        reconciliation=reconciliation,
        atomicity_errors=atomicity_errors,
        outcome=outcome,
    )
    proposal_queue_artifact, proposal_items = update_proposal_queue(
        graph_health=graph_health,
        run_id=run_id,
    )
    refactor_queue_artifact = update_refactor_queue(
        graph_health=graph_health,
        run_id=run_id,
        proposal_items=proposal_items,
    )
    success = result.returncode == 0 and not validation_errors and outcome == "done"

    required_human_action = "resolve gate: approve|retry|split|block|redirect|escalate"
    node.data["proposed_status"] = None
    node.data["proposed_maturity"] = None

    split_sync_allowed = (
        outcome == "split_required"
        and any(spec_id != node.id for spec_id in reconciliation.get("changed_spec_ids", []))
        and result.returncode == 0
        and not output_errors
        and not allowed_path_errors
        and not reconciliation_errors
        and not transition_errors
    )
    if split_sync_allowed:
        allowed_changes = select_sync_paths(node.allowed_paths, changed)
        sync_files_from_worktree(worktree_path, allowed_changes)
        node.reload()

    if success:
        proposed_maturity = (
            None if is_graph_refactor_run else min(1.0, round(node.maturity + 0.2, 2))
        )
        node.data["proposed_status"] = proposed_status
        node.data["proposed_maturity"] = proposed_maturity
        if auto_approve:
            allowed_changes = select_sync_paths(node.allowed_paths, changed)
            sync_files_from_worktree(worktree_path, allowed_changes)
            # Preserve approved content produced in the isolated worktree.
            node.reload()
            if proposed_status:
                node.data["status"] = proposed_status
            node.data["maturity"] = proposed_maturity
            node.data["gate_state"] = "none"
            node.data["proposed_status"] = None
            node.data["proposed_maturity"] = None
            required_human_action = "-"
        else:
            node.data["gate_state"] = "review_pending"
    else:
        if outcome == "blocked":
            node.data["gate_state"] = "blocked"
            required_human_action = "resolve blocker"
        elif outcome == "split_required":
            node.data["gate_state"] = "split_required"
            required_human_action = "split spec scope before rerun"
        elif outcome == "retry":
            node.data["gate_state"] = "retry_pending"
            required_human_action = "rerun supervisor"
        elif outcome == "escalate":
            node.data["gate_state"] = "escalated"
            required_human_action = "manual escalation"
        else:
            node.data["gate_state"] = "retry_pending"
            required_human_action = "rerun supervisor"

    validator_results = {
        "outputs": not output_errors,
        "allowed_paths": not allowed_path_errors,
        "reconciliation": not reconciliation_errors,
        "atomicity": not atomicity_errors,
        "transition": not transition_errors,
    }

    node.data["required_human_action"] = required_human_action
    node.data["last_outcome"] = outcome
    node.data["last_blocker"] = blocker
    node.data["last_run_id"] = run_id
    node.data["last_exit_code"] = result.returncode
    node.data["last_changed_files"] = changed
    node.data["last_run_at"] = utc_now_iso()
    node.data["last_worktree_path"] = worktree_path.as_posix()
    node.data["last_branch"] = branch
    node.data["last_validator_results"] = validator_results
    node.data["last_reconciliation"] = reconciliation
    if validation_errors:
        node.data["last_errors"] = validation_errors
    node.save()

    payload = {
        "run_id": run_id,
        "timestamp_utc": utc_now_iso(),
        "spec_id": node.id,
        "title": node.title,
        "selected_by_rule": selected_by_rule,
        "before_status": before_status,
        "proposed_status": node.data.get("proposed_status"),
        "final_status": node.data.get("status"),
        "outcome": outcome,
        "blocker": blocker,
        "gate_state": node.data.get("gate_state"),
        "required_human_action": required_human_action,
        "exit_code": result.returncode,
        "auto_approved": bool(success and auto_approve),
        "worktree_path": worktree_path.as_posix(),
        "branch": branch,
        "changed_files": changed,
        "validation_errors": validation_errors,
        "validator_results": validator_results,
        "reconciliation": reconciliation,
        "graph_health": graph_health,
        "refactor_queue_artifact": refactor_queue_artifact.as_posix(),
        "proposal_queue_artifact": proposal_queue_artifact.as_posix(),
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
    log_path = write_run_log(run_id, payload)
    write_latest_summary(payload)

    print(f"Run log: {log_path.as_posix()}")
    print("Finished status:", "ok" if success else "failed")

    if result.stdout.strip():
        print("\n=== codex stdout ===")
        print(result.stdout.strip())
    if result.stderr.strip():
        print("\n=== codex stderr ===", file=sys.stderr)
        print(result.stderr.strip(), file=sys.stderr)

    if validation_errors:
        print("\n=== validation errors ===", file=sys.stderr)
        for error in validation_errors:
            print(f"- {error}", file=sys.stderr)

    exit_code = 0 if success else 1
    return exit_code, outcome


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
) -> int:
    if executor is None:
        executor = run_codex

    try:
        specs = load_specs()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if not specs:
        print("No spec nodes found in specs/nodes")
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

    if loop:
        print(f"Starting autonomous loop mode (max_iterations={max_iterations})")
        succeeded = 0
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
                break

            print(f"\n{'=' * 60}")
            print(
                f"[{iteration}/{max_iterations}] Processing: {node.id} — {node.title}"
                f" (status={node.status}, maturity={node.maturity:.2f})"
            )
            print(f"{'=' * 60}")

            exit_code, outcome = _process_one_spec(
                node=node,
                specs=specs,
                executor=executor,
                auto_approve=auto_approve,
                refactor_work_item=refactor_work_item,
            )

            if exit_code == 0:
                succeeded += 1
                print(f"[{iteration}] {node.id} promoted successfully.")
            else:
                failed += 1
                print(
                    f"[{iteration}] {node.id} finished with outcome={outcome},"
                    f" gate_state={node.gate_state}. Continuing."
                )
        else:
            print(f"Safety limit reached ({max_iterations} iterations). Stopping loop.")

        print(f"\nLoop summary: {succeeded} succeeded, {failed} failed")
        return 0

    # --- single-pass mode (original behaviour) ---
    node, refactor_work_item = pick_next_work_item(specs)
    if node is None:
        print("No eligible spec gaps found.")
        return 0

    dependents = reverse_dependents_count(specs)
    selection_mode = selection_mode_for_node(node, specs, refactor_work_item=refactor_work_item)
    selected_by_rule = {
        "status_filter": sorted(WORKABLE_STATUSES),
        "dependency_required_statuses": sorted(READY_DEP_STATUSES),
        "selection_mode": selection_mode,
        "sort_order": [
            "refactor_queue_first",
            "ancestor_reconcile_first",
            "nearest_unlocked_ancestor",
            "leaf_first",
            "lower_maturity",
            "stable_id",
        ],
        "dependents_count": dependents.get(node.id, 0),
    }
    if refactor_work_item is not None:
        selected_by_rule["refactor_work_item"] = {
            "id": str(refactor_work_item.get("id", "")),
            "work_item_type": str(refactor_work_item.get("work_item_type", "")),
            "signal": str(refactor_work_item.get("signal", "")),
            "recommended_action": str(refactor_work_item.get("recommended_action", "")),
            "source_run_id": str(refactor_work_item.get("source_run_id", "")),
        }

    print(f"Selected spec node: {node.id} — {node.title}")

    if dry_run:
        print("\n=== dry-run mode ===")
        print(f"Would execute prompt for: {node.id}")
        print(f"Status: {node.status} | Maturity: {node.maturity:.2f} | Gate: {node.gate_state}")
        print(f"Selection context: {json.dumps(selected_by_rule, ensure_ascii=False)}")
        print(f"\n{build_prompt(node, refactor_work_item)}")
        return 0

    exit_code, _outcome = _process_one_spec(
        node=node,
        specs=specs,
        executor=executor,
        auto_approve=auto_approve,
        refactor_work_item=refactor_work_item,
    )
    return exit_code


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SpecGraph supervisor")
    parser.add_argument("--dry-run", action="store_true", help="Show selection and prompt only")
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Apply proposed status/maturity immediately when run succeeds",
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
    args = parser.parse_args()
    raise SystemExit(
        main(
            dry_run=args.dry_run,
            auto_approve=args.auto_approve,
            loop=args.loop,
            max_iterations=args.max_iterations,
            resolve_gate=args.resolve_gate,
            decision=args.decision,
            note=args.note,
        )
    )
