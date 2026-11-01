"""Exercise a real installed snapshot from two isolated synthetic workspaces."""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import yaml


def ontology_overview_probe(installation, workspace, environment, hypercode, ontologyc):
    """Run installed tools against only project-owned inputs, never the source checkout."""
    inputs = workspace / "runs/overview-inputs"
    inputs.mkdir(parents=True)
    shutil.copyfile(
        installation / "source/specs/models/SG-SPEC-0072/domain-ontology-package.yaml",
        inputs / "ontology.yaml",
    )
    (inputs / "selection.hc").write_text(
        "ContextVerificationCase#case\n  CheckResult#member\n  CheckResult#dependencies\n"
    )
    (inputs / "rule.py").write_text(
        "raise RuntimeError('bound modules must not execute')\n"
        "def decide(value):\n    return bool(value)\n"
    )
    (inputs / "selection.hcs").write_text(
        'ContextVerificationCase:\n  overview_name: "ContextVerification"\n'
        '  ontology_source: "runs/overview-inputs/ontology.yaml"\n'
        '  ontology_ref: "ontology://org.0al.specgraph.local.contextcase/0.2.0/classes/ContextVerificationCase"\n'
        "CheckResult:\n"
        '  ontology_ref: "ontology://org.0al.specgraph.local.contextcase/0.2.0/classes/CheckResult"\n'
        '  production_path: "runs/overview-inputs/rule.py"\n'
        '  production_symbol: "decide"\n  production_anchor: "return bool(value)"\n'
        "'#member':\n  overview_name: \"Member\"\n"
        "'#dependencies':\n  overview_name: \"Dependencies\"\n"
    )
    # A product-local module must not shadow the installed export adapter.
    shadow = workspace / "ontology_overview.py"
    shadow.write_text("raise RuntimeError('unexpected product import')\n")
    command = [
        str(installation / "specgraph-runtime"),
        "--workspace",
        str(workspace),
        "ontology-overview",
        "--",
    ]
    help_result = subprocess.run(
        [*command, "--help"], cwd=workspace.parent, env=environment, capture_output=True, text=True
    )
    assert help_result.returncode == 0 and "--hc" in help_result.stdout
    arguments = [
        "--hc",
        "runs/overview-inputs/selection.hc",
        "--hcs",
        "runs/overview-inputs/selection.hcs",
        "--output-dir",
        "runs/overview-result",
    ]
    missing = subprocess.run(
        [
            *command,
            *arguments,
            "--hypercode",
            str(inputs / "missing-hypercode"),
            "--ontologyc",
            str(inputs / "missing-ontologyc"),
        ],
        cwd=workspace.parent,
        env=environment,
        capture_output=True,
        text=True,
    )
    assert missing.returncode == 1 and not missing.stdout
    assert json.loads(missing.stderr)["status"] == "unavailable"
    output = workspace / "runs/overview-result"
    assert not output.exists()
    observation = {
        "launcher_help": "passed",
        "unavailable_report": "passed",
        "reference_export": "not_requested",
    }
    before = {p.name: p.read_bytes() for p in inputs.iterdir()}
    if hypercode is not None:
        process = subprocess.run(
            [*command, *arguments, "--hypercode", str(hypercode), "--ontologyc", str(ontologyc)],
            cwd=workspace.parent,
            env=environment,
            capture_output=True,
            text=True,
        )
        assert process.returncode == 0, (process.stdout, process.stderr)
        exported = json.loads(process.stdout)
        assert exported["status"] == "exported" and exported["roles"] == 3
        assert exported["semantic_approval"] == "not_established"
        for suffix in ("hc", "hcs"):
            assert (
                hashlib.sha256((output / f"context.{suffix}").read_bytes()).hexdigest()
                == (exported[f"{suffix}_sha256"])
            )
        assert (
            output / "context.hc"
        ).read_text() == "ContextVerification\n  Member\n  Dependencies\n"
        observation.update(
            reference_export="passed",
            hc_sha256=exported["hc_sha256"],
            hcs_sha256=exported["hcs_sha256"],
        )
    assert before == {p.name: p.read_bytes() for p in inputs.iterdir()}
    assert not (workspace.parent / "runs/overview-result").exists()
    shadow.unlink()  # Keep the later initializer/refinement probe's allowed layout.
    return observation


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--hypercode", type=Path, help="optional real overview export tool")
    parser.add_argument("--ontologyc", type=Path, help="supply together with --hypercode")
    args = parser.parse_args()
    if (args.hypercode is None) != (args.ontologyc is None):
        parser.error("--hypercode and --ontologyc must be supplied together")
    if args.hypercode is not None:
        args.hypercode, args.ontologyc = args.hypercode.resolve(), args.ontologyc.resolve()
    root = args.root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    install = root / "runtime with spaces"
    project_a = root / "project a"
    project_b = root / "project b"
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
            ".",
            "--revision",
            args.revision,
            "--destination",
            str(install),
        ],
        cwd=args.repo,
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
    overview_observations = []
    for index, project in enumerate((project_a, project_b), 1):
        workspace = project / "knowledge workspace"
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
                    str(project / "sketch"),
                ]
            )
        )
        assert notes["canonical"] is False and notes["revision"] is None
        skill_name = "specgraph-project-ontology"
        installed_skill = json.loads(
            call(
                [
                    str(launcher),
                    "--workspace",
                    str(workspace),
                    "draft",
                    "--",
                    "skill",
                    "install",
                    "--name",
                    skill_name,
                    "--project",
                    str(project),
                ]
            )
        )
        skill_path = project / ".codex" / "skills" / skill_name / "SKILL.md"
        assert installed_skill["status"] == "installed" and installed_skill["skill"] == skill_name
        assert (
            hashlib.sha256(skill_path.read_bytes()).hexdigest()
            == (installed_skill["files_sha256"]["SKILL.md"])
        )
        assert (
            skill_path.read_bytes()
            == (install / "source/.codex/skills" / skill_name / "SKILL.md").read_bytes()
        )
        assert not (workspace / ".codex" / "skills" / skill_name).exists()
        overview_observations.append(
            ontology_overview_probe(install, workspace, environment, args.hypercode, args.ontologyc)
        )
        request = project / "request.json"
        request.write_text(
            json.dumps(
                {
                    "expected_revision": None,
                    "source": {
                        "ref": "synthetic:pilot",
                        "quote": "Fixture note",
                        "speaker": "human",
                    },
                    "changes": [{"op": "add", "id": "goal", "label": "Goal", "parent_id": None}],
                }
            )
        )
        saved = json.loads(
            call(
                [
                    str(launcher),
                    "--workspace",
                    str(workspace),
                    "draft",
                    "--",
                    "notes",
                    "update_notes",
                    "--workspace",
                    str(project / "sketch"),
                    "--input",
                    str(request),
                ],
                cwd=project,
            )
        )
        assert saved["revision"] and saved["canonical"] is False
        history = json.loads(
            call(
                [
                    str(launcher),
                    "--workspace",
                    str(workspace),
                    "draft",
                    "--",
                    "notes",
                    "verify_history",
                    "--workspace",
                    str(project / "sketch"),
                ],
                cwd=project,
            )
        )
        assert history["revision"] == saved["revision"] and history["revision_count"] == 1
    assert (project_a / "knowledge workspace/specgraph.project.yaml").read_text() != (
        project_b / "knowledge workspace/specgraph.project.yaml"
    ).read_text()
    assert overview_observations[0] == overview_observations[1]
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
    before_a = (project_a / "knowledge workspace/specs/nodes/PROBE-SPEC-0001.yaml").read_bytes()
    call(
        [str(install / "venv/bin/python"), "-c", code, str(install / "source")],
        cwd=project_b / "knowledge workspace",
    )
    logs = []
    for path in (project_b / "knowledge workspace/runs").glob("*.json"):
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
    assert (
        project_a / "knowledge workspace/specs/nodes/PROBE-SPEC-0001.yaml"
    ).read_bytes() == before_a
    workspace = project_b / "knowledge workspace"
    # The shadowing fixture is unrelated to the initializer's allowed layout.
    (workspace / "specgraph.py").unlink()
    worktrees = workspace / ".worktrees"
    assert worktrees.is_dir() and not worktrees.is_symlink()
    before_worktrees = sorted(
        path.relative_to(worktrees).as_posix() for path in worktrees.rglob("*")
    )
    before_config = (workspace / "specgraph.project.yaml").read_bytes()
    before_intent = (workspace / ".specgraph/root_intent.md").read_bytes()
    repeated = json.loads(
        call(
            [
                str(launcher),
                "--workspace",
                str(workspace),
                "init",
                "--",
                "--project-id",
                "native-2",
                "--output-mode",
                "full",
            ]
        )
    )
    assert repeated["summary"]["status"] == "ready"
    assert repeated["validation_findings"] == []
    assert (
        sorted(path.relative_to(worktrees).as_posix() for path in worktrees.rglob("*"))
        == before_worktrees
    )
    assert (workspace / "specgraph.project.yaml").read_bytes() == before_config
    assert (workspace / ".specgraph/root_intent.md").read_bytes() == before_intent
    report = {
        "artifact_kind": "native_runtime_observation",
        "schema_version": 1,
        "source_commit": args.revision,
        "status": "passed",
        "synthetic_workspaces": 2,
        "ontology_overview": overview_observations,
        "checks": [
            "exact_snapshot_without_git",
            "isolated_venv",
            "path_with_spaces",
            "init",
            "product_advisor",
            "targeted_supervisor_dry_run",
            "specdraft_read",
            "named_skill_install_in_project_outside_workspace",
            "specdraft_absolute_request_outside_workspace",
            "specdraft_full_history_verification",
            "repeat_init_after_git_worktree_refinement",
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
