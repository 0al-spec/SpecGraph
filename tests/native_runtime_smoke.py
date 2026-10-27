"""Exercise a real installed snapshot from two isolated synthetic workspaces."""

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import yaml


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    install = root / "runtime with spaces"
    project_a = root / "project-a"
    project_b = root / "project-b"
    for project in (project_a, project_b):
        project.mkdir()
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"

    def call(command, *, cwd=root):
        result = subprocess.run(command, cwd=cwd, env=environment, text=True, capture_output=True)
        if result.returncode:
            raise AssertionError((command, result.returncode, result.stdout, result.stderr))
        return result.stdout

    setup = call(
        [
            sys.executable,
            str(args.repo / "tools/native_runtime.py"),
            "install",
            "--source",
            str(args.repo),
            "--revision",
            args.revision,
            "--destination",
            str(install),
        ]
    )
    receipt = json.loads(setup)
    assert receipt["source_commit"] == args.revision
    assert not (install / "source/.git").exists()
    for name in ("tools/supervisor.py", "tools/native_runtime.py", "tools/supervisor_policy.json"):
        original = subprocess.check_output(
            ["git", "-C", str(args.repo), "show", f"{args.revision}:{name}"]
        )
        assert (install / "source" / name).read_bytes() == original
    launcher = install / "specgraph-runtime"
    fixture = json.loads(
        (install / "source/docs/evidence/0227_local_workspace_path_reuse.json").read_text()
    )["fixture"]
    for index, project in enumerate((project_a, project_b), 1):
        workspace = project / "knowledge"
        call(
            [
                str(launcher),
                "--workspace",
                str(workspace),
                "init",
                "--",
                "--project-id",
                f"native-{index}",
                "--root-intent",
                f"Synthetic native project {index}",
                "--output-mode",
                "summary",
            ]
        )
        nodes = workspace / "specs/nodes"
        nodes.mkdir(parents=True)
        (nodes / f"{fixture['id']}.yaml").write_text(yaml.safe_dump(fixture, sort_keys=False))
        # A project-local module must not shadow the installed SpecDraft package.
        (workspace / "specgraph.py").write_text("raise RuntimeError('unexpected project import')\n")
        call(["git", "init", "--quiet", str(workspace)])
        call(
            [
                "git",
                "-C",
                str(workspace),
                "add",
                "specgraph.project.yaml",
                "specs",
                ".specgraph/root_intent.md",
                "specgraph.py",
            ]
        )
        call(
            [
                "git",
                "-C",
                str(workspace),
                "-c",
                "user.name=Fixture",
                "-c",
                "user.email=fixture@example.invalid",
                "commit",
                "--quiet",
                "-m",
                "Initial synthetic graph",
            ]
        )
        call(
            [
                str(launcher),
                "--workspace",
                str(workspace),
                "next-move",
                "--",
                "--target-spec",
                fixture["id"],
            ]
        )
        call(
            [
                str(launcher),
                "--workspace",
                str(workspace),
                "supervisor",
                "--",
                "--target-spec",
                fixture["id"],
                "--dry-run",
                "--output-mode",
                "summary",
            ]
        )
        assert (workspace / "runs/product_workspace_next_moves.json").is_file()
        notes = json.loads(
            call(
                [
                    str(launcher),
                    "--workspace",
                    str(workspace),
                    "draft",
                    "--",
                    "notes",
                    "read_notes",
                    "--workspace",
                    str(workspace / "sketch"),
                ]
            )
        )
        assert notes["canonical"] is False and notes["revision"] is None
    assert (project_a / "knowledge/specgraph.project.yaml").read_text() != (
        project_b / "knowledge/specgraph.project.yaml"
    ).read_text()
    # Exercise the installed supervisor's real Git worktree/review path with a
    # deterministic executor. No agent, model or hosted inference is invoked.
    code = """
import subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(sys.argv[1]) / "tools"))
import supervisor
import yaml
def executor(node, worktree):
    path = worktree / "specs/nodes" / (node.id + ".yaml")
    value = yaml.safe_load(path.read_text())
    value["prompt"] += " Keep this bounded to the selected project."
    supervisor.write_spec_yaml(path, value)
    return subprocess.CompletedProcess(["fixture"], 0, "RUN_OUTCOME: done\\nBLOCKER: none\\n", "")
raise SystemExit(supervisor.main(
    target_spec="PROBE-SPEC-0001", executor=executor, auto_approve=False, output_mode="summary"
))
"""
    before_a = (project_a / "knowledge/specs/nodes/PROBE-SPEC-0001.yaml").read_bytes()
    call(
        [str(install / "venv/bin/python"), "-c", code, str(install / "source")],
        cwd=project_b / "knowledge",
    )
    logs = []
    for path in (project_b / "knowledge/runs").glob("*.json"):
        value = json.loads(path.read_text())
        if (
            isinstance(value, dict)
            and value.get("spec_id") == "PROBE-SPEC-0001"
            and "completion_status" in value
        ):
            logs.append(value)
    assert len(logs) == 1
    assert logs[0]["completion_status"] == "ok" and logs[0]["outcome"] == "done"
    assert logs[0]["gate_state"] == "review_pending" and not logs[0]["validation_errors"]
    assert logs[0]["isolation_mode"] == "git_worktree"
    assert (project_a / "knowledge/specs/nodes/PROBE-SPEC-0001.yaml").read_bytes() == before_a
    report = {
        "artifact_kind": "native_runtime_observation",
        "schema_version": 1,
        "source_commit": args.revision,
        "status": "passed",
        "synthetic_workspaces": 2,
        "checks": [
            "exact_snapshot_without_git",
            "isolated_venv",
            "path_with_spaces",
            "init",
            "product_advisor",
            "targeted_supervisor_dry_run",
            "specdraft_read",
        ],
        "executor": "deterministic_fixture_not_a_real_agent",
        "refinement": {
            "outcome": "done",
            "gate_state": "review_pending",
            "isolation_mode": "git_worktree",
        },
        "canonical_publication": "not_evaluated",
        "installer_sha256": hashlib.sha256(
            (install / "source/tools/native_runtime.py").read_bytes()
        ).hexdigest(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
