#!/usr/bin/env python3
"""Inspect exact publication links at one Git revision; diagnostic, not a merge gate."""

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml

from traceability.publication import build_publication_links


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", required=True, type=Path)
    parser.add_argument("--revision", required=True)
    args = parser.parse_args(argv)
    try:
        report = build_publication_links(args.repository_root, args.revision)
    except (OSError, ValueError, subprocess.CalledProcessError, yaml.YAMLError) as error:
        print(f"publication link input error: {error}", file=sys.stderr)
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0  # Resolution findings are informational. Invalid required input exits 1.


if __name__ == "__main__":
    raise SystemExit(main())
