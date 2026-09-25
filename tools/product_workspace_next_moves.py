"""Read-only next-move advice from one explicit SpecGraph product workspace."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

import product_workspace_next_moves_support as workspace

POLICY_PATH = Path(__file__).with_name("product_workspace_next_moves_policy.json")
VALID_STATUSES = {"idea", "stub", "outlined", "specified", "linked", "reviewed", "frozen"}
GATE_ACTIONS = {
    "review_pending": (
        "review_gate",
        "review_exact_gate_candidate",
        "Read the exact run and candidate for {spec_id}, then resolve its review gate.",
    ),
    "split_required": (
        "split_spec",
        "structural_split",
        "Review the structural split requirement for {spec_id} before rerunning refinement.",
    ),
    "retry_pending": (
        "retry_refinement",
        "repair_then_retry",
        "Repair the failed condition for {spec_id}, then rerun targeted refinement.",
    ),
    "blocked": (
        "resolve_blocker",
        "resolve_blocker",
        "Identify and resolve the recorded blocker for {spec_id} before retrying.",
    ),
    "redirected": (
        "redirect_refinement",
        "update_prompt_scope_and_rerun",
        "Update the prompt or scope for {spec_id}, then rerun targeted refinement.",
    ),
    "escalated": (
        "manual_escalation",
        "manual_escalation",
        "Review the manual escalation for {spec_id} before further refinement.",
    ),
}


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_policy() -> dict[str, Any]:
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


def candidate_move(
    node: workspace.SpecNode,
    *,
    source_path: str,
    gate_order: list[str],
    status_order: list[str],
) -> tuple[int, dict[str, Any]] | None:
    if node.status not in VALID_STATUSES:
        raise ValueError(f"unsupported canonical status for {node.id}: {node.status}")
    gate = node.gate_state
    if gate != "none":
        if gate not in gate_order or gate not in GATE_ACTIONS:
            raise ValueError(f"unsupported gate state for {node.id}: {gate}")
        kind, next_gap, hint_template = GATE_ACTIONS[gate]
        command_hint = hint_template.format(spec_id=node.id)
        rank = gate_order.index(gate)
    elif node.status in status_order:
        next_gap = "targeted_refinement"
        command_hint = f"Run a targeted dry-run for {node.id}, then refine one bounded concern."
        rank = len(gate_order) + status_order.index(node.status)
        kind = "refine_spec"
    else:
        return None

    return rank, {
        "kind": kind,
        "spec_id": node.id,
        "title": node.title,
        "status": node.status,
        "gate_state": gate,
        "next_gap": next_gap,
        "source_artifact": source_path,
        "command_hint": command_hint,
        "review_required": True,
    }


def build_product_workspace_next_moves(
    workspace_root: Path,
    *,
    target_spec: str | None = None,
) -> dict[str, Any]:
    root = workspace_root.expanduser().resolve(strict=True)
    if not root.is_dir():
        raise ValueError(f"workspace root is not a directory: {root}")
    policy = load_policy()
    config_path = root / "specgraph.project.yaml"
    if not config_path.is_file():
        raise ValueError("product_workspace requires specgraph.project.yaml")
    project_policy = workspace.load_product_policy()
    environment = workspace.product_environment(config_path, project_policy)
    project = environment["project"]
    profile = project["governance_profile"]

    specs_dir = root / "specs" / "nodes"
    if not specs_dir.is_dir():
        raise ValueError("product_workspace requires specs/nodes directory")
    specs = workspace.load_specs_from_dir(specs_dir)
    if any(not isinstance(node.data, dict) for node in specs):
        raise ValueError("canonical spec nodes must be mappings with nonempty IDs")
    ids = [node.id for node in specs]
    if any(not node.id for node in specs):
        raise ValueError("canonical spec nodes must be mappings with nonempty IDs")
    if len(ids) != len(set(ids)):
        raise ValueError("canonical spec node IDs must be unique")
    for node in specs:
        if node.path.stem != node.id or node.data.get("kind") != "spec":
            raise ValueError(f"invalid canonical spec identity: {node.path.name}")

    if target_spec:
        target = next((node for node in specs if node.id == target_spec), None)
        if target is None:
            raise ValueError(f"target spec is absent from product workspace: {target_spec}")
        selected_specs = workspace.subtree_nodes(target, specs)
    else:
        selected_specs = specs

    gate_order = list(policy["priority"]["gates"])
    status_order = list(policy["priority"]["refinable_statuses"])
    if set(gate_order) != set(GATE_ACTIONS):
        raise ValueError("product next-move policy must rank every canonical gate state")
    authority = environment.get("supervisor_authority", {})
    refinement_allowed = (
        isinstance(authority, dict) and authority.get("allow_project_spec_refinement") is True
    )
    eligible: list[tuple[int, dict[str, Any]]] = []
    blocked: list[dict[str, Any]] = []
    for node in selected_specs:
        source_path = node.path.relative_to(root).as_posix()
        candidate = candidate_move(
            node,
            source_path=source_path,
            gate_order=gate_order,
            status_order=status_order,
        )
        if candidate is None:
            continue
        rank, move = candidate
        authorization = workspace.authorize_target(
            target_spec_id=node.id,
            target_paths=workspace.effective_allowed_paths_for_run(node, root),
            environment=environment,
        )
        blocked_by = list(authorization["blocked_by"])
        if not refinement_allowed:
            blocked_by.append("blocked_by_project_spec_refinement_disabled")
        if not blocked_by:
            eligible.append((rank, move))
        else:
            blocked.append(
                {
                    **move,
                    "command_hint": (
                        f"Resolve governance and workspace authority for {node.id} before action."
                    ),
                    "blocked_by": blocked_by,
                    "target_domain": authorization["target_domain"],
                }
            )
    eligible.sort(key=lambda entry: (entry[0], entry[1]["spec_id"]))
    blocked.sort(key=lambda move: move["spec_id"])
    recommended = eligible[0][1] if eligible else None
    current_scene = (
        ("refinement_ready" if recommended["kind"] == "refine_spec" else recommended["kind"])
        if recommended
        else "governance_blocked"
        if blocked
        else "steady_state"
    )

    return {
        "artifact_kind": "product_workspace_next_moves",
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "policy_reference": {
            "artifact_path": "tools/product_workspace_next_moves_policy.json",
            "sha256": file_digest(POLICY_PATH),
        },
        "project_environment_policy_reference": {
            "artifact_path": "tools/project_environment_policy.json",
            "sha256": file_digest(workspace.PROJECT_POLICY_PATH),
        },
        "project": {
            "project_id": project["project_id"],
            "governance_profile": profile,
        },
        "scope": {
            "target_spec": target_spec or "",
            "selected_spec_ids": [node.id for node in selected_specs],
            "selected_spec_count": len(selected_specs),
        },
        "input_contract": policy["input_contract"],
        "inputs": {
            "project_config": {
                "path": "specgraph.project.yaml",
                "sha256": file_digest(config_path),
            },
            "canonical_specs": [
                {
                    "path": node.path.relative_to(root).as_posix(),
                    "sha256": file_digest(node.path),
                }
                for node in specs
            ],
        },
        "current_scene": current_scene,
        "recommended_next_move_kind": recommended["kind"] if recommended else "none",
        "recommended_next_move": recommended,
        "alternatives": [move for _, move in eligible[1:]],
        "blocked_moves": blocked,
        "canonical_mutations_allowed": False,
        "tracked_artifacts_written": False,
    }


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    encoded = json.dumps(payload, ensure_ascii=False, indent=2)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as temporary:
            temporary.write(encoded)
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-root", type=Path, required=True)
    parser.add_argument("--target-spec")
    args = parser.parse_args()
    try:
        report = build_product_workspace_next_moves(
            args.workspace_root, target_spec=args.target_spec
        )
        root = args.workspace_root.expanduser().resolve(strict=True)
        output_dir = root / "runs"
        output_path = output_dir / "product_workspace_next_moves.json"
        if output_dir.is_symlink() or output_path.is_symlink():
            raise ValueError("product advisory output must not traverse symlinks")
        output_dir.mkdir(parents=True, exist_ok=True)
        if not output_dir.resolve(strict=True).is_relative_to(root):
            raise ValueError("product advisory output escapes the selected workspace")
        atomic_write_json(output_path, report)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
