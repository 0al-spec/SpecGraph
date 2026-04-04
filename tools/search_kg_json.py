#!/usr/bin/env python3
"""Search nested JSON conversation archives for product signals.

MVP goals:
- Work on raw folders with many JSON files.
- Traverse arbitrary tree-shaped JSON payloads.
- Rank matching text snippets for simple keyword queries.
- Cache request-response pairs for faster repeated lookups.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
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


def dataset_fingerprint(json_dir: Path) -> str:
    """Return a lightweight signature of current JSON files for cache invalidation."""
    parts: list[str] = []
    for file in sorted(json_dir.glob("*.json")):
        if file.name.startswith("."):
            continue
        stat = file.stat()
        parts.append(f"{file.name}:{stat.st_mtime_ns}:{stat.st_size}")
    return "|".join(parts)


def make_cache_key(query: str, limit: int, fingerprint: str) -> str:
    return f"q={query.strip().lower()}|limit={limit}|fp={fingerprint}"


def load_cache(cache_file: Path) -> dict[str, Any]:
    if not cache_file.exists():
        return {"entries": {}}

    try:
        payload = json.loads(cache_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"entries": {}}

    if not isinstance(payload, dict) or not isinstance(payload.get("entries"), dict):
        return {"entries": {}}
    return payload


def save_cache(cache_file: Path, cache: dict[str, Any]) -> None:
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def serialize_matches(matches: list[Match]) -> list[dict[str, Any]]:
    return [{**asdict(item), "file": str(item.file)} for item in matches]


def deserialize_matches(items: list[dict[str, Any]]) -> list[Match]:
    matches: list[Match] = []
    for item in items:
        matches.append(
            Match(
                file=Path(item["file"]),
                path=item["path"],
                text=item["text"],
                score=item["score"],
            )
        )
    return matches


def find_matches(json_dir: Path, query: str, limit: int = 20) -> list[Match]:
    terms = [part.lower() for part in query.strip().split() if part]
    if not terms:
        raise ValueError("Query must contain at least one non-space character.")

    matches: list[Match] = []
    for file in sorted(json_dir.glob("*.json")):
        if file.name.startswith("."):
            continue
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


def find_matches_with_cache(
    json_dir: Path, query: str, limit: int, cache_file: Path, use_cache: bool
) -> tuple[list[Match], bool]:
    if not use_cache:
        return find_matches(json_dir=json_dir, query=query, limit=limit), False

    cache = load_cache(cache_file)
    fingerprint = dataset_fingerprint(json_dir)
    key = make_cache_key(query=query, limit=limit, fingerprint=fingerprint)

    entries = cache["entries"]
    if key in entries:
        return deserialize_matches(entries[key]), True

    matches = find_matches(json_dir=json_dir, query=query, limit=limit)
    entries[key] = serialize_matches(matches)
    save_cache(cache_file=cache_file, cache=cache)
    return matches, False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Search nested JSON files for idea/requirement snippets."
    )
    parser.add_argument(
        "query",
        help="Free text query, for example: 'success criteria limitations'",
    )
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
    parser.add_argument(
        "--cache-file",
        type=Path,
        default=None,
        help="Path to request-response cache file (default: <json-dir>/.search_kg_cache.json)",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable cache reads/writes for this request",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if not args.json_dir.exists() or not args.json_dir.is_dir():
        raise SystemExit(f"JSON folder not found: {args.json_dir}")

    cache_file = args.cache_file or (args.json_dir / ".search_kg_cache.json")
    matches, cache_hit = find_matches_with_cache(
        json_dir=args.json_dir,
        query=args.query,
        limit=args.limit,
        cache_file=cache_file,
        use_cache=not args.no_cache,
    )

    if cache_hit:
        print(f"[cache] hit: {cache_file}")
    elif not args.no_cache:
        print(f"[cache] miss -> saved: {cache_file}")

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
