#!/usr/bin/env python3
"""Fail fast when SpecGraph tooling runs on an unsupported Python runtime."""

from __future__ import annotations

import sys

MIN_VERSION = (3, 10)


def version_tuple(version_info: object) -> tuple[int, int, int]:
    if all(hasattr(version_info, name) for name in ("major", "minor", "micro")):
        return (
            int(version_info.major),
            int(version_info.minor),
            int(version_info.micro),
        )

    return (
        int(version_info[0]),
        int(version_info[1]),
        int(version_info[2]),
    )


def format_version(version: tuple[int, int, int]) -> str:
    return ".".join(str(part) for part in version)


def is_supported(version_info: object) -> bool:
    return version_tuple(version_info)[:2] >= MIN_VERSION


def main() -> int:
    current = version_tuple(sys.version_info)
    if is_supported(sys.version_info):
        return 0

    required = ".".join(str(part) for part in MIN_VERSION)
    print(
        "SpecGraph requires Python >= "
        f"{required}; current interpreter is {format_version(current)} "
        f"at {sys.executable}. Pass PYTHON=/path/to/python3.10-or-newer "
        "or create a .venv with Python 3.10+.",
        file=sys.stderr,
    )
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
