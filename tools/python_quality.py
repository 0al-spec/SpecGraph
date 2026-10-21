import os
import subprocess
import sys

# Mirrors the blocking GitHub Actions `python-quality` job so pre-commit can
# fail on the same project-wide Python, canonical spec-YAML, and architecture
# style checks before push.


def run_step(args: list[str]) -> int:
    completed = subprocess.run(args)
    return int(completed.returncode)


def main() -> int:
    steps = [
        [sys.executable, "-m", "ruff", "check", "."],
        [sys.executable, "-m", "ruff", "format", "--check", "."],
        [sys.executable, "tools/spec_yaml_lint.py"],
        [sys.executable, "tools/validate_architecture_style.py"],
        [sys.executable, "tools/lifecycle_architecture.py", "--check"],
    ]
    for step in steps:
        exit_code = run_step(step)
        if exit_code != 0:
            return exit_code
    if os.environ.get("GITHUB_EVENT_NAME") == "pull_request":
        # Existing blocking CI job installs project dependencies and fetches the
        # full history. The event supplies exact revisions and the full PR body.
        return run_step(
            [
                sys.executable,
                "tools/intent_decision_review_gate.py",
                "--event-path",
                os.environ.get("GITHUB_EVENT_PATH", ""),
            ]
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
