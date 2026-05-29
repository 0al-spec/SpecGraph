#!/usr/bin/env python3
"""Validate that repository docs and DocC mirror pages stay synchronized."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = ROOT / "tools" / "docc_sync_contract.json"


def _load_contract(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise SystemExit(f"DocC sync contract not found: {path}") from None
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid DocC sync contract JSON at {path}: {exc}") from exc

    if not isinstance(data, dict) or not isinstance(data.get("groups"), list):
        raise SystemExit("DocC sync contract must contain a top-level 'groups' list")
    return data


def _read_text(relative_path: str, errors: list[str]) -> str:
    path = ROOT / relative_path
    if not path.is_file():
        errors.append(f"missing file: {relative_path}")
        return ""
    return path.read_text(encoding="utf-8")


def _validate_group(group: dict[str, Any], errors: list[str]) -> None:
    group_id = str(group.get("id", "<missing-id>"))
    docs = group.get("docs")
    docc = group.get("docc")
    required_terms = group.get("required_terms", [])
    docs_required_terms = group.get("docs_required_terms", [])
    docc_required_terms = group.get("docc_required_terms", [])

    if not isinstance(docs, list) or not docs:
        errors.append(f"{group_id}: 'docs' must be a non-empty list")
        return
    if not isinstance(docc, list) or not docc:
        errors.append(f"{group_id}: 'docc' must be a non-empty list")
        return
    for field_name, value in (
        ("required_terms", required_terms),
        ("docs_required_terms", docs_required_terms),
        ("docc_required_terms", docc_required_terms),
    ):
        if not isinstance(value, list):
            errors.append(f"{group_id}: '{field_name}' must be a list")
            return

    if not required_terms and not docs_required_terms and not docc_required_terms:
        errors.append(
            f"{group_id}: at least one of 'required_terms', "
            "'docs_required_terms', or 'docc_required_terms' must be non-empty"
        )
        return

    texts = {str(path): _read_text(str(path), errors) for path in [*docs, *docc]}

    term_sets: dict[str, list[Any]] = {}
    for path in docs:
        term_sets[str(path)] = [*required_terms, *docs_required_terms]
    for path in docc:
        term_sets[str(path)] = [*required_terms, *docc_required_terms]

    for path, text in texts.items():
        if not text:
            continue
        for term in term_sets[path]:
            if not isinstance(term, str) or not term:
                errors.append(f"{group_id}: required term must be a non-empty string")
                continue
            if term not in text:
                errors.append(f"{group_id}: {path} is missing required term {term!r}")


def validate(contract_path: Path) -> list[str]:
    contract = _load_contract(contract_path)
    errors: list[str] = []
    for raw_group in contract["groups"]:
        if not isinstance(raw_group, dict):
            errors.append("DocC sync contract group must be an object")
            continue
        _validate_group(raw_group, errors)
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Validate synchronized coverage between repository docs and DocC pages."
    )
    parser.add_argument(
        "--contract",
        type=Path,
        default=DEFAULT_CONTRACT,
        help="Path to the DocC sync contract JSON.",
    )
    args = parser.parse_args(argv)

    errors = validate(args.contract)
    if errors:
        print("DocC sync validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("DocC sync validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
