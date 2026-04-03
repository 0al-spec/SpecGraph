#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    print("Missing dependency: pyyaml. Install with: pip install pyyaml", file=sys.stderr)
    raise SystemExit(1)

ROOT = Path.cwd()
SPECS_DIR = ROOT / "specs" / "nodes"
RUNS_DIR = ROOT / "runs"
AGENTS_FILE = ROOT / "AGENTS.md"

READY_DEP_STATUSES = {"reviewed", "frozen"}
WORKABLE_STATUSES = {"outlined", "specified"}
VALID_STATUSES = {"idea", "stub", "outlined", "specified", "linked", "reviewed", "frozen"}


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
        with self.path.open("w", encoding="utf-8") as file:
            yaml.safe_dump(self.data, file, sort_keys=False, allow_unicode=True)


def load_specs() -> list[SpecNode]:
    if not SPECS_DIR.exists():
        return []

    nodes: list[SpecNode] = []
    for path in sorted(SPECS_DIR.glob("*.yaml")):
        with path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file) or {}
        nodes.append(SpecNode(path=path, data=data))
    return nodes


def index_specs(specs: list[SpecNode]) -> dict[str, SpecNode]:
    return {spec.id: spec for spec in specs if spec.id}


def dependencies_ready(node: SpecNode, index: dict[str, SpecNode]) -> bool:
    for dep_id in node.depends_on:
        dep = index.get(dep_id)
        if dep is None or dep.status not in READY_DEP_STATUSES:
            return False
    return True


def pick_next_spec_gap(specs: list[SpecNode]) -> SpecNode | None:
    index = index_specs(specs)
    candidates = [
        spec
        for spec in specs
        if spec.status in WORKABLE_STATUSES and dependencies_ready(spec, index)
    ]
    if not candidates:
        return None

    candidates.sort(key=lambda spec: (spec.maturity, spec.id))
    return candidates[0]


def git_changed_files() -> list[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    changed: list[str] = []
    for line in result.stdout.splitlines():
        if len(line) >= 4:
            changed.append(line[3:].strip())
    return changed


def build_prompt(node: SpecNode) -> str:
    agents_hint = ""
    if AGENTS_FILE.exists():
        agents_hint = "Read and follow AGENTS.md before editing anything.\n\n"

    allowed_paths = "\n".join(f"- {path}" for path in node.allowed_paths) or "- (not specified)"
    outputs = "\n".join(f"- {path}" for path in node.outputs) or "- (not specified)"

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

Rules:
- Refine specification only.
- Do not implement runtime code.
- Preserve stable IDs and terminology.
- Do not edit files outside allowed paths.
- If blocked, stop and explain blocker clearly.
- End with a short summary of changed files, improvements, and blockers.
""".strip()


def validate_yaml(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        with path.open("r", encoding="utf-8") as file:
            yaml.safe_load(file)
    except Exception as exc:
        errors.append(f"Invalid YAML in {path.as_posix()}: {exc}")
    return errors


def validate_outputs(node: SpecNode) -> list[str]:
    errors: list[str] = []
    for rel_path in node.outputs:
        output_path = ROOT / rel_path
        if not output_path.exists():
            errors.append(f"Missing expected output: {rel_path}")
            continue
        if output_path.suffix.lower() in {".yaml", ".yml"}:
            errors.extend(validate_yaml(output_path))
    return errors


def validate_allowed_paths(node: SpecNode, changed_files: list[str]) -> list[str]:
    if not node.allowed_paths:
        return []

    allowed = set(node.allowed_paths)
    errors: list[str] = []
    for changed in changed_files:
        if changed not in allowed:
            errors.append(f"Changed file outside allowed_paths: {changed}")
    return errors


def validate_status(node: SpecNode) -> list[str]:
    if node.status not in VALID_STATUSES:
        return [f"Unknown status: {node.status}"]
    if "acceptance" not in node.data or not isinstance(node.data.get("acceptance"), list):
        return ["acceptance list must be present"]
    return []


def write_run_log(node: SpecNode, payload: dict[str, Any]) -> Path:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = RUNS_DIR / f"{timestamp}-{node.id}.json"
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)
    return path


def run_codex(node: SpecNode) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["codex", "exec", build_prompt(node)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def main() -> int:
    specs = load_specs()
    if not specs:
        print("No spec nodes found in specs/nodes")
        return 0

    node = pick_next_spec_gap(specs)
    if node is None:
        print("No eligible spec gaps found.")
        return 0

    print(f"Selected spec node: {node.id} — {node.title}")

    before = git_changed_files()
    result = run_codex(node)
    after = git_changed_files()
    changed = sorted(set(after) - set(before))

    validation_errors: list[str] = []
    validation_errors.extend(validate_outputs(node))
    validation_errors.extend(validate_allowed_paths(node, changed))
    validation_errors.extend(validate_status(node))

    success = result.returncode == 0 and not validation_errors
    if success:
        if node.status == "outlined":
            node.data["status"] = "specified"
        elif node.status == "specified":
            node.data["status"] = "reviewed"
        node.data["maturity"] = min(1.0, round(node.maturity + 0.2, 2))
    else:
        node.data["last_errors"] = validation_errors

    node.data["last_exit_code"] = result.returncode
    node.data["last_changed_files"] = changed
    node.data["last_run_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    node.save()

    log_path = write_run_log(
        node,
        {
            "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "spec_id": node.id,
            "title": node.title,
            "selected_status": node.status,
            "exit_code": result.returncode,
            "changed_files": changed,
            "validation_errors": validation_errors,
            "stdout": result.stdout,
            "stderr": result.stderr,
        },
    )

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

    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
