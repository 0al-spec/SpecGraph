"""Verify the enforcing CLI contract with isolated, committed Python fixtures."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def commit(root: Path) -> str:
    git(root, "add", ".")
    git(
        root,
        "-c",
        "user.name=RuleReuseFixture",
        "-c",
        "user.email=fixture@example.invalid",
        "commit",
        "--allow-empty",
        "-qm",
        "isolated rule reuse fixture",
    )
    return git(root, "rev-parse", "HEAD")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def smoke(repo: Path, analyzer: Path, output: Path) -> dict:
    output.mkdir(parents=True, exist_ok=False)
    summary = {
        "artifact_kind": "rule_reuse_ci_smoke",
        "schema_version": 1,
        "status": "incomplete",
        "production_metrics": False,
        "source_revision": git(repo, "rev-parse", "HEAD"),
        "cases": [],
    }
    summary_path = output / "summary.json"

    def save() -> None:
        summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    save()
    fixture = (repo / "tests/fixtures/rule_reuse/workspace_allocation_copy.py").read_text(
        encoding="utf-8"
    )
    revision = summary["source_revision"]
    with tempfile.TemporaryDirectory(prefix="specgraph-rule-reuse-smoke-") as directory:
        root = Path(directory)
        git(root, "init", "-q")
        # Read one committed snapshot; source files are never imported or executed.
        paths = [
            p
            for p in git(repo, "ls-tree", "-r", "--name-only", revision).splitlines()
            if p.endswith(".py")
        ]
        for path in [*paths, "tools/rule_reuse_catalog.toml"]:
            target = root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(
                subprocess.check_output(["git", "-C", str(repo), "show", f"{revision}:{path}"])
            )
        base = commit(root)
        cases = [
            ("clean", None, 0, 0),
            ("exact_copy", fixture, 1, 0),
            ("changed_authority", fixture.replace("is True", "is False", 1), 0, 1),
        ]
        for name, code, exact, near in cases:
            if code is not None:
                (root / "tools/smoke_copy.py").write_text(code, encoding="utf-8")
            head = commit(root)
            case_output = output / name
            completed = subprocess.run(
                [
                    "bash",
                    str(repo / "tools/check_rule_reuse.sh"),
                    str(root),
                    str(analyzer),
                    base,
                    head,
                    str(case_output),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            (case_output / "execution.json").write_text(
                json.dumps(
                    {"exit_code": completed.returncode, "stderr": completed.stderr}, indent=2
                )
                + "\n",
                encoding="utf-8",
            )
            require(
                (case_output / "report.json").is_file(),
                f"{name}: missing comparison report: {completed.stderr[-2000:]}",
            )
            report = json.loads((case_output / "report.json").read_text(encoding="utf-8"))
            mode = (case_output / "mode.txt").read_text(encoding="utf-8").strip()
            require(mode == "enforcing", f"{name}: expected enforcing, got {mode}")
            require(report["status"] == "complete", f"{name}: incomplete comparison")
            require(
                report["base_revision"] == base and report["head_revision"] == head,
                f"{name}: wrong comparison revisions",
            )
            require(report["new_reimplementations"] == exact, f"{name}: wrong exact count")
            require(report["new_near_matches"] == near, f"{name}: wrong near count")
            require((completed.returncode != 0) == bool(exact), f"{name}: wrong exit code")
            if exact:
                require(
                    completed.returncode == 1 and "rule reuse gate failed:" in completed.stderr,
                    f"{name}: rejection is not the registered-copy gate",
                )
            findings = report["findings"]
            if code is not None:
                expected_kind = "reimplementation" if exact else "near_match"
                require(
                    any(
                        f["rule_id"] == "subject_publication.workspace_allocation"
                        and f["path"] == "tools/smoke_copy.py"
                        and f["introduced"]
                        and f["kind"] == expected_kind
                        for f in findings
                    ),
                    f"{name}: missing expected registered rule finding",
                )
            summary["cases"].append(
                {
                    "case": name,
                    "mode": mode,
                    "status": "passed",
                    "exit_code": completed.returncode,
                    "new_reimplementations": exact,
                    "new_near_matches": near,
                    "report": f"{name}/report.json",
                }
            )
            save()
    summary["status"] = "complete"
    save()
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--analyzer", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = smoke(args.root.resolve(), args.analyzer.resolve(), args.output.resolve())
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
