#!/usr/bin/env python3
"""Search nested JSON conversation archives for product signals.

MVP goals:
- Work on raw folders with many JSON files.
- Traverse arbitrary tree-shaped JSON payloads.
- Extract structured requirement statements from free-form dialogue/spec text.
- Cache request-response pairs for faster repeated lookups.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Match:
    file: Path
    path: str
    text: str
    score: int
    kind: str = "unknown"


@dataclass(frozen=True)
class RequirementCandidate:
    path: str
    text: str
    kind: str


_BULLET_PREFIX_RE = re.compile(r"^\s*(?:[-*•–—]|\d+[.)])\s+")
_QUERY_SPLIT_RE = re.compile(r"\s+")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


_KIND_KEYWORDS: dict[str, tuple[str, ...]] = {
    "acceptance": (
        "acceptance",
        "acceptance criteria",
        "success criteria",
        "definition of done",
        "критер",
    ),
    "constraint": (
        "must",
        "must not",
        "should",
        "should not",
        "do not",
        "cannot",
        "can't",
        "avoid",
        "required",
        "обяз",
        "долж",
        "нельзя",
        "не нужно",
        "не должен",
    ),
    "goal": (
        "goal",
        "purpose",
        "objective",
        "target",
        "цель",
        "задач",
    ),
    "risk": (
        "risk",
        "pitfall",
        "danger",
        "tradeoff",
        "failure mode",
        "риск",
        "угроз",
        "ошибк",
    ),
    "scope": (
        "in scope",
        "out of scope",
        "scope",
        "в рамках",
        "вне scope",
        "не входит",
    ),
    "assumption": (
        "assumption",
        "assume",
        "предполож",
        "допустим",
    ),
}


_KIND_ALIASES = {
    "constraints": "constraint",
    "limitations": "constraint",
    "criteria": "acceptance",
    "success": "acceptance",
    "goals": "goal",
    "risks": "risk",
}


_PATH_KIND_HINTS = {
    "acceptance": "acceptance",
    "criteria": "acceptance",
    "success": "acceptance",
    "constraint": "constraint",
    "limitation": "constraint",
    "requirement": "constraint",
    "goal": "goal",
    "objective": "goal",
    "purpose": "goal",
    "risk": "risk",
    "pitfall": "risk",
    "scope": "scope",
    "assumption": "assumption",
}


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


def normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


def parse_query_terms(query: str) -> list[str]:
    return [part.lower() for part in _QUERY_SPLIT_RE.split(query.strip()) if part]


def normalize_kind(raw: str | None) -> str | None:
    if raw is None:
        return None
    lowered = raw.strip().lower()
    if not lowered:
        return None
    return _KIND_ALIASES.get(lowered, lowered)


def infer_kind_from_text(text: str, path: str, heading: str | None = None) -> str:
    source = text.lower()
    path_lower = path.lower()
    heading_lower = (heading or "").lower()

    for marker, kind in _PATH_KIND_HINTS.items():
        if marker in path_lower:
            return kind

    for kind, markers in _KIND_KEYWORDS.items():
        for marker in markers:
            if marker in heading_lower:
                return kind
        for marker in markers:
            if marker in source:
                return kind

    return "unknown"


def is_heading_line(text: str, was_bullet: bool) -> bool:
    if was_bullet:
        return False

    stripped = text.strip()
    if not stripped:
        return False
    if stripped.endswith(":"):
        return True
    if any(punct in stripped for punct in ".!?"):
        return False

    words = stripped.split()
    return 1 <= len(words) <= 6 and len(stripped) <= 60


def line_requirement_signal(text: str, kind: str, was_bullet: bool) -> int:
    lowered = text.lower()
    signal = 0
    if was_bullet:
        signal += 1
    if kind != "unknown":
        signal += 2
    if any(token in lowered for token in ("must", "should", "долж", "нужно", "нельзя", "не ")):
        signal += 2
    if 6 <= len(text) <= 240:
        signal += 1
    return signal


def extract_requirements_from_text(text: str, path: str) -> list[RequirementCandidate]:
    candidates: list[RequirementCandidate] = []
    current_heading: str | None = None

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue

        bullet_match = _BULLET_PREFIX_RE.match(stripped)
        was_bullet = bullet_match is not None
        content = _BULLET_PREFIX_RE.sub("", stripped).strip()
        if not content:
            continue

        if is_heading_line(content, was_bullet=was_bullet):
            current_heading = content
            continue

        normalized = normalize_whitespace(content)
        if not normalized:
            continue

        kind = infer_kind_from_text(normalized, path=path, heading=current_heading)
        signal = line_requirement_signal(normalized, kind=kind, was_bullet=was_bullet)
        if signal < 3:
            continue

        candidates.append(RequirementCandidate(path=path, text=normalized, kind=kind))

    if candidates:
        return candidates

    normalized_text = normalize_whitespace(text)
    if not normalized_text:
        return []

    sentence_candidates: list[RequirementCandidate] = []
    for sentence in _SENTENCE_SPLIT_RE.split(normalized_text):
        sentence_text = sentence.strip()
        if not sentence_text:
            continue
        if len(sentence_text) > 240:
            continue

        kind = infer_kind_from_text(sentence_text, path=path)
        signal = line_requirement_signal(sentence_text, kind=kind, was_bullet=False)
        if signal < 3:
            continue

        sentence_candidates.append(
            RequirementCandidate(path=path, text=sentence_text, kind=kind)
        )

    if sentence_candidates:
        return sentence_candidates

    kind = infer_kind_from_text(normalized_text, path=path)
    if kind == "unknown" or len(normalized_text) > 240:
        return []

    return [RequirementCandidate(path=path, text=normalized_text, kind=kind)]


def iter_requirement_candidates(node: Any, path: str = "$"):
    for json_path, text in iter_text_nodes(node, path=path):
        yield from extract_requirements_from_text(text, path=json_path)


def score_requirement(text: str, terms: list[str], kind: str) -> int:
    if not terms:
        return 1
    lowered = text.lower()
    kind_lower = kind.lower()
    total = 0
    for term in terms:
        total += lowered.count(term)
        total += kind_lower.count(term)
    return total


def dataset_fingerprint(json_dir: Path) -> str:
    """Return a lightweight signature of current JSON files for cache invalidation."""
    parts: list[str] = []
    for file in sorted(json_dir.glob("*.json")):
        if file.name.startswith("."):
            continue
        stat = file.stat()
        parts.append(f"{file.name}:{stat.st_mtime_ns}:{stat.st_size}")
    return "|".join(parts)


def make_cache_key(query: str, limit: int, fingerprint: str, kind: str | None) -> str:
    kind_token = kind or "any"
    return f"q={query.strip().lower()}|kind={kind_token}|limit={limit}|fp={fingerprint}"


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
                kind=item.get("kind", "unknown"),
            )
        )
    return matches


def find_matches(
    json_dir: Path,
    query: str,
    limit: int = 20,
    kind: str | None = None,
) -> list[Match]:
    terms = parse_query_terms(query)
    normalized_kind = normalize_kind(kind)
    if not terms and normalized_kind is None:
        raise ValueError("Query must contain at least one non-space character or --kind.")
    if limit < 0:
        raise ValueError("Limit must be a non-negative integer.")

    valid_kinds = set(_KIND_KEYWORDS) | {"unknown"}
    if normalized_kind is not None and normalized_kind not in valid_kinds:
        kinds = ", ".join(sorted(valid_kinds))
        raise ValueError(f"Unknown kind '{normalized_kind}'. Expected one of: {kinds}")

    matches: list[Match] = []
    for file in sorted(json_dir.glob("*.json")):
        if file.name.startswith("."):
            continue
        try:
            payload = json.loads(file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        for candidate in iter_requirement_candidates(payload):
            if normalized_kind is not None and candidate.kind != normalized_kind:
                continue
            score = score_requirement(candidate.text, terms=terms, kind=candidate.kind)
            if score > 0:
                matches.append(
                    Match(
                        file=file,
                        path=candidate.path,
                        text=candidate.text,
                        score=score,
                        kind=candidate.kind,
                    )
                )

    matches.sort(key=lambda item: (item.score, len(item.text)), reverse=True)
    return matches[:limit]


def find_matches_with_cache(
    json_dir: Path,
    query: str,
    limit: int,
    cache_file: Path,
    use_cache: bool,
    kind: str | None = None,
) -> tuple[list[Match], bool]:
    if not use_cache:
        return find_matches(json_dir=json_dir, query=query, limit=limit, kind=kind), False

    cache = load_cache(cache_file)
    fingerprint = dataset_fingerprint(json_dir)
    key = make_cache_key(query=query, limit=limit, fingerprint=fingerprint, kind=kind)

    entries = cache["entries"]
    if key in entries:
        return deserialize_matches(entries[key]), True

    matches = find_matches(json_dir=json_dir, query=query, limit=limit, kind=kind)
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
    parser.add_argument(
        "--kind",
        default=None,
        help=(
            "Optional requirement kind filter. "
            "Examples: goal, constraint, acceptance, risk, scope, assumption."
        ),
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if not args.json_dir.exists() or not args.json_dir.is_dir():
        raise SystemExit(f"JSON folder not found: {args.json_dir}")
    if args.limit < 0:
        raise SystemExit("--limit must be a non-negative integer.")

    cache_file = args.cache_file or (args.json_dir / ".search_kg_cache.json")
    matches, cache_hit = find_matches_with_cache(
        json_dir=args.json_dir,
        query=args.query,
        limit=args.limit,
        cache_file=cache_file,
        use_cache=not args.no_cache,
        kind=args.kind,
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
            f"{idx:02d}. score={match.score:<3} kind={match.kind:<10} file={match.file.name} "
            f"path={match.path}\n    {preview}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
