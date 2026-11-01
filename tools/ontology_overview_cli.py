#!/usr/bin/env python3
"""Export an explicitly authored ontology composition as readable HC/HCS."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ontology_overview.export import export_overview
from ontology_overview.model import OverviewError
from ontology_snapshot import OntologySnapshotError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--workspace-root", type=Path, required=True)
    parser.add_argument(
        "--hc", type=Path, required=True, help="workspace-relative authored composition"
    )
    parser.add_argument(
        "--hcs", type=Path, required=True, help="workspace-relative authored bindings"
    )
    parser.add_argument("--hypercode", type=Path, required=True)
    parser.add_argument("--ontologyc", type=Path, required=True)
    parser.add_argument(
        "--output-dir", type=Path, required=True, help="new directory; never overwritten"
    )
    args = parser.parse_args(argv)
    try:
        result = export_overview(
            args.workspace_root.expanduser(),
            args.hc,
            args.hcs,
            args.hypercode.expanduser().resolve(),
            args.ontologyc.expanduser().resolve(),
            args.output_dir.expanduser().absolute(),
        )
    except (OverviewError, OntologySnapshotError, OSError, ValueError) as error:
        status = getattr(error, "outcome", "invalid")
        print(json.dumps({"status": status, "error": str(error)}), file=sys.stderr)
        return 1 if status == "unavailable" else 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
