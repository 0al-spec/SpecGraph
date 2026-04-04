#!/usr/bin/env python3
"""Search nested JSON conversation archives for product signals.

MVP goals:
- Work on raw folders with many JSON files.
- Traverse arbitrary tree-shaped JSON payloads.
- Rank matching text snippets for simple keyword queries.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Match:
    file: Path
    path: str
    text: str
    score: int


def iter_text_nodes(node: Any, path: str = "$"):
    """Yield (json_path, text) for every string value in a nested JSON object."""
    if isinstance(node, str):
        yield path, node
        return

    if isinstance(node, dict):
        for key, value in node.items():
            yield from iter_text_nodes(value, f"{path}.{key}")
        return

    if isinstance(node, list):
        for index, value in enumerate(node):
            yield from iter_text_nodes(value, f"{path}[{index}]")


def score_text(text: str, terms: list[str]) -> int:
    lowered = text.lower()
    return sum(lowered.count(term) for term in terms)


def find_matches(json_dir: Path, query: str, limit: int = 20) -> list[Match]:
    terms = [part.lower() for part in query.strip().split() if part]
    if not terms:
        raise ValueError("Query must contain at least one non-space character.")

    matches: list[Match] = []
    for file in sorted(json_dir.glob("*.json")):
        try:
            payload = json.loads(file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        for json_path, text in iter_text_nodes(payload):
            score = score_text(text, terms)
            if score > 0:
                matches.append(Match(file=file, path=json_path, text=text.strip(), score=score))

    matches.sort(key=lambda item: (item.score, len(item.text)), reverse=True)
    return matches[:limit]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Search nested JSON files for idea/requirement snippets."
    )
    parser.add_argument("query", help="Free text query, for example: 'success criteria limitations'")
    parser.add_argument(
        "--json-dir",
        default="data",
        type=Path,
        help="Directory with conversation JSON files (default: ./data)",
    )
    parser.add_argument(
        "--limit",
        default=20,
        type=int,
        help="Maximum number of hits to print (default: 20)",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if not args.json_dir.exists() or not args.json_dir.is_dir():
        raise SystemExit(f"JSON folder not found: {args.json_dir}")

    matches = find_matches(json_dir=args.json_dir, query=args.query, limit=args.limit)

    if not matches:
        print("No matches found.")
        return 0

    for idx, match in enumerate(matches, start=1):
        preview = " ".join(match.text.split())
        if len(preview) > 180:
            preview = preview[:177] + "..."
        print(
            f"{idx:02d}. score={match.score:<3} file={match.file.name} "
            f"path={match.path}\n    {preview}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
