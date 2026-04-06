import subprocess
import sys

# Mirrors the blocking GitHub Actions `python-quality` job so pre-commit can
# fail on the same project-wide Ruff lint and format checks before push.


def run_step(args: list[str]) -> int:
    completed = subprocess.run(args)
    return int(completed.returncode)


def main() -> int:
    steps = [
        [sys.executable, "-m", "ruff", "check", "."],
        [sys.executable, "-m", "ruff", "format", "--check", "."],
    ]
    for step in steps:
        exit_code = run_step(step)
        if exit_code != 0:
            return exit_code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
