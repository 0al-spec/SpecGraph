"""Compare explicit ontology declarations in two selected YAML documents."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml

from project_ontology_term_declarations import (
    PROFILE,
    read_term_declarations,
    source_position,
    term_field_path,
)


def read_document(root: Path, name: str) -> tuple[dict[str, str], dict[str, list[dict[str, Any]]]]:
    relative = Path(name)
    if relative.is_absolute() or ".." in relative.parts or relative.suffix not in {".yaml", ".yml"}:
        raise ValueError(f"expected a workspace-relative YAML path: {name}")
    path = root / relative
    if path.resolve(strict=True) != path or not path.is_file():
        raise ValueError(f"expected a regular file without symlinks: {name}")
    raw = path.read_bytes()
    spec_id, declarations = read_term_declarations(relative.as_posix(), raw)
    by_term = defaultdict(list)
    for field, node in declarations:
        by_term[node.value].append(
            {
                "field_path": term_field_path(field, node.value),
                "location": source_position(node),
            }
        )
    return {
        "path": relative.as_posix(),
        "spec_id": spec_id,
        "sha256": hashlib.sha256(raw).hexdigest(),
    }, dict(by_term)


def build_ref_diff(
    workspace: Path, before: str, after: str, explanations: list[list[str]]
) -> dict[str, Any]:
    root = workspace.resolve(strict=True)
    before_source, before_terms = read_document(root, before)
    after_source, after_terms = read_document(root, after)
    removed = before_terms.keys() - after_terms.keys()
    reasons: dict[str, str] = {}
    for term, reason in explanations:
        if term not in removed:
            raise ValueError(f"removal explanation must name an absent declaration: {term}")
        if term in reasons or not reason.strip():
            raise ValueError(f"expected one nonempty removal explanation for: {term}")
        reasons[term] = reason.strip()

    return {
        "artifact_kind": "specgraph_ontology_ref_diff",
        "schema_version": 1,
        "analysis_profile": PROFILE,
        "inputs": {"before": before_source, "after": after_source},
        "retained": [
            {"term": term, "before": before_terms[term], "after": after_terms[term]}
            for term in sorted(before_terms.keys() & after_terms.keys())
        ],
        "added": [
            {"term": term, "after": after_terms[term]}
            for term in sorted(after_terms.keys() - before_terms.keys())
        ],
        "removed": [
            {"term": term, "before": before_terms[term], "removal_explanation": reasons.get(term)}
            for term in sorted(removed)
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--workspace-root", type=Path, required=True)
    parser.add_argument("before", help="workspace-relative source YAML")
    parser.add_argument("after", help="workspace-relative successor YAML")
    parser.add_argument(
        "--explain-removal", nargs=2, metavar=("TERM", "REASON"), action="append", default=[]
    )
    args = parser.parse_args()
    try:
        report = build_ref_diff(args.workspace_root, args.before, args.after, args.explain_removal)
    except (OSError, RuntimeError, ValueError, yaml.YAMLError) as error:
        parser.error(str(error))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
