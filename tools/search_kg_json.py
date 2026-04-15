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
import hashlib
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Match:
    file: Path
    path: str
    text: str
    score: int
    kind: str = "unknown"
    heading: str | None = None
    source_form: str = "line"
    source_index: int = 0
    signal: int = 0
    requirement_id: str = ""


@dataclass(frozen=True)
class RequirementCandidate:
    path: str
    text: str
    kind: str
    heading: str | None = None
    signal: int = 0
    source_form: str = "line"
    source_index: int = 0


@dataclass(frozen=True)
class RequirementRecord:
    file: Path
    path: str
    text: str
    kind: str
    heading: str | None
    signal: int
    source_form: str
    source_index: int
    requirement_id: str


_BULLET_PREFIX_RE = re.compile(r"^\s*(?:[-*•–—]|\d+[.)])\s+")
_QUERY_SPLIT_RE = re.compile(r"\s+")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_HEADING_WORD_CLEAN_RE = re.compile(r"^[\W_]+|[\W_]+$")


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


_HEADING_DISQUALIFY_MARKERS = (
    "must",
    "should",
    "do not",
    "don't",
    "cannot",
    "can't",
    "avoid",
    "required",
    "need to",
    "needs to",
    "нужно",
    "долж",
    "нельзя",
    "не должен",
    "не нужно",
)


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


def looks_like_heading_word(word: str) -> bool:
    cleaned = _HEADING_WORD_CLEAN_RE.sub("", word)
    if not cleaned:
        return False
    first = cleaned[0]
    return first.isupper() or first.isdigit()


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

    lowered = stripped.lower()
    if any(marker in lowered for marker in _HEADING_DISQUALIFY_MARKERS):
        return False

    words = stripped.split()
    if not (1 <= len(words) <= 6 and len(stripped) <= 60):
        return False

    heading_like_words = sum(1 for word in words if looks_like_heading_word(word))
    return heading_like_words >= max(1, len(words) - 1)


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

    for line_index, raw_line in enumerate(text.splitlines(), start=1):
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

        candidates.append(
            RequirementCandidate(
                path=path,
                text=normalized,
                kind=kind,
                heading=current_heading,
                signal=signal,
                source_form="line",
                source_index=line_index,
            )
        )

    if candidates:
        return candidates

    normalized_text = normalize_whitespace(text)
    if not normalized_text:
        return []

    sentence_candidates: list[RequirementCandidate] = []
    for sentence_index, sentence in enumerate(_SENTENCE_SPLIT_RE.split(normalized_text), start=1):
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
            RequirementCandidate(
                path=path,
                text=sentence_text,
                kind=kind,
                signal=signal,
                source_form="sentence",
                source_index=sentence_index,
            )
        )

    if sentence_candidates:
        return sentence_candidates

    kind = infer_kind_from_text(normalized_text, path=path)
    if kind == "unknown" or len(normalized_text) > 240:
        return []

    return [
        RequirementCandidate(
            path=path,
            text=normalized_text,
            kind=kind,
            signal=line_requirement_signal(normalized_text, kind=kind, was_bullet=False),
            source_form="blob",
            source_index=1,
        )
    ]


def iter_requirement_candidates(node: Any, path: str = "$"):
    for json_path, text in iter_text_nodes(node, path=path):
        yield from extract_requirements_from_text(text, path=json_path)


def requirement_id_for_record(
    file: Path,
    path: str,
    text: str,
    kind: str,
    source_form: str,
    source_index: int,
) -> str:
    payload = "|".join(
        (
            file.as_posix(),
            path,
            text,
            kind,
            source_form,
            str(source_index),
        )
    )
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]
    return f"req-{digest}"


def requirement_record_from_candidate(
    file: Path,
    candidate: RequirementCandidate,
) -> RequirementRecord:
    requirement_id = requirement_id_for_record(
        file=file,
        path=candidate.path,
        text=candidate.text,
        kind=candidate.kind,
        source_form=candidate.source_form,
        source_index=candidate.source_index,
    )
    return RequirementRecord(
        file=file,
        path=candidate.path,
        text=candidate.text,
        kind=candidate.kind,
        heading=candidate.heading,
        signal=candidate.signal,
        source_form=candidate.source_form,
        source_index=candidate.source_index,
        requirement_id=requirement_id,
    )


def serialize_requirement_records(records: list[RequirementRecord]) -> list[dict[str, Any]]:
    return [{**asdict(item), "file": str(item.file)} for item in records]


def collect_requirement_records(
    json_dir: Path,
    kind: str | None = None,
) -> list[RequirementRecord]:
    normalized_kind = normalize_kind(kind)
    valid_kinds = set(_KIND_KEYWORDS) | {"unknown"}
    if normalized_kind is not None and normalized_kind not in valid_kinds:
        kinds = ", ".join(sorted(valid_kinds))
        raise ValueError(f"Unknown kind '{normalized_kind}'. Expected one of: {kinds}")

    records: list[RequirementRecord] = []
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
            records.append(requirement_record_from_candidate(file=file, candidate=candidate))

    return records


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
                heading=item.get("heading"),
                source_form=item.get("source_form", "line"),
                source_index=item.get("source_index", 0),
                signal=item.get("signal", 0),
                requirement_id=item.get("requirement_id", ""),
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

    matches: list[Match] = []
    for record in collect_requirement_records(json_dir=json_dir, kind=normalized_kind):
        score = score_requirement(record.text, terms=terms, kind=record.kind)
        if score > 0:
            matches.append(
                Match(
                    file=record.file,
                    path=record.path,
                    text=record.text,
                    score=score,
                    kind=record.kind,
                    heading=record.heading,
                    source_form=record.source_form,
                    source_index=record.source_index,
                    signal=record.signal,
                    requirement_id=record.requirement_id,
                )
            )

    matches.sort(key=lambda item: (item.score, len(item.text)), reverse=True)
    return matches[:limit]


def build_requirement_projection_artifact(
    *,
    json_dir: Path,
    records: list[RequirementRecord],
) -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    by_kind: dict[str, int] = {}
    requirements: list[dict[str, Any]] = []

    for record in records:
        by_kind[record.kind] = by_kind.get(record.kind, 0) + 1
        requirements.append(
            {
                "requirement_id": record.requirement_id,
                "kind": record.kind,
                "text": record.text,
                "heading": record.heading,
                "source_form": record.source_form,
                "source_index": record.source_index,
                "projection_links": [
                    {"rel": "source_file", "target": record.file.as_posix()},
                    {"rel": "source_json_path", "target": f"{record.file.name}#{record.path}"},
                    {"rel": "provenance", "target": record.requirement_id},
                ],
            }
        )

    return {
        "artifact_version": 1,
        "artifact_kind": "requirement_projection",
        "generator": "tools/search_kg_json.py",
        "generated_at": generated_at,
        "json_dir": json_dir.as_posix(),
        "dataset_fingerprint": dataset_fingerprint(json_dir),
        "requirement_count": len(records),
        "file_count": len({record.file for record in records}),
        "by_kind": by_kind,
        "requirements": requirements,
    }


def build_requirement_provenance_artifact(
    *,
    json_dir: Path,
    records: list[RequirementRecord],
) -> dict[str, Any]:
    generated_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    provenance_records = [
        {
            "requirement_id": record.requirement_id,
            "file": record.file.as_posix(),
            "json_path": record.path,
            "heading": record.heading,
            "source_form": record.source_form,
            "source_index": record.source_index,
            "signal": record.signal,
            "text": record.text,
        }
        for record in records
    ]

    return {
        "artifact_version": 1,
        "artifact_kind": "requirement_provenance",
        "generator": "tools/search_kg_json.py",
        "generated_at": generated_at,
        "json_dir": json_dir.as_posix(),
        "dataset_fingerprint": dataset_fingerprint(json_dir),
        "record_count": len(records),
        "provenance_records": provenance_records,
    }


def write_requirement_artifacts(
    *,
    artifact_dir: Path,
    json_dir: Path,
    records: list[RequirementRecord],
) -> tuple[Path, Path]:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    projection_path = artifact_dir / "requirement_projection.json"
    provenance_path = artifact_dir / "requirement_provenance.json"
    projection_path.write_text(
        json.dumps(
            build_requirement_projection_artifact(json_dir=json_dir, records=records),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    provenance_path.write_text(
        json.dumps(
            build_requirement_provenance_artifact(json_dir=json_dir, records=records),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return projection_path, provenance_path


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
        nargs="?",
        default="",
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
    parser.add_argument(
        "--dump-requirements",
        action="store_true",
        help="Print extracted requirement records instead of ranked query matches.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format for matches or dumped requirement records (default: text).",
    )
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=None,
        help=(
            "Optional directory for derived requirement projection/provenance artifacts "
            "(requirement_projection.json and requirement_provenance.json)."
        ),
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if not args.json_dir.exists() or not args.json_dir.is_dir():
        raise SystemExit(f"JSON folder not found: {args.json_dir}")
    if args.limit < 0:
        raise SystemExit("--limit must be a non-negative integer.")

    if args.dump_requirements and args.no_cache:
        # No-op, but keep the CLI behavior explicit: dumping requirements does not use cache.
        pass

    normalized_kind = normalize_kind(args.kind)
    records: list[RequirementRecord] | None = None
    if args.dump_requirements or args.artifact_dir is not None:
        try:
            records = collect_requirement_records(json_dir=args.json_dir, kind=normalized_kind)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc

    if args.artifact_dir is not None:
        assert records is not None
        projection_path, provenance_path = write_requirement_artifacts(
            artifact_dir=args.artifact_dir,
            json_dir=args.json_dir,
            records=records,
        )
        print(f"[artifacts] projection: {projection_path}", file=sys.stderr)
        print(f"[artifacts] provenance: {provenance_path}", file=sys.stderr)

    if args.dump_requirements:
        assert records is not None
        limited_records = records[: args.limit] if args.limit else records
        if args.format == "json":
            print(
                json.dumps(
                    serialize_requirement_records(limited_records),
                    ensure_ascii=False,
                    indent=2,
                )
            )
        else:
            if not limited_records:
                print("No requirement records found.")
                return 0
            for idx, record in enumerate(limited_records, start=1):
                preview = " ".join(record.text.split())
                if len(preview) > 180:
                    preview = preview[:177] + "..."
                heading = f" heading={record.heading!r}" if record.heading else ""
                print(
                    f"{idx:02d}. kind={record.kind:<10} signal={record.signal:<2} "
                    f"form={record.source_form:<8} file={record.file.name} "
                    f"path={record.path}{heading}\n"
                    f"    {preview}"
                )
        return 0

    if not args.query.strip() and args.artifact_dir is not None:
        return 0

    if not args.query.strip() and normalized_kind is None:
        raise SystemExit(
            "Query must contain at least one non-space character unless "
            "--dump-requirements, --artifact-dir, or --kind is used."
        )

    cache_file = args.cache_file or (args.json_dir / ".search_kg_cache.json")
    try:
        matches, cache_hit = find_matches_with_cache(
            json_dir=args.json_dir,
            query=args.query,
            limit=args.limit,
            cache_file=cache_file,
            use_cache=not args.no_cache,
            kind=normalized_kind,
        )
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    if cache_hit:
        print(f"[cache] hit: {cache_file}", file=sys.stderr)
    elif not args.no_cache:
        print(f"[cache] miss -> saved: {cache_file}", file=sys.stderr)

    if not matches:
        print("No matches found.")
        return 0

    if args.format == "json":
        print(json.dumps(serialize_matches(matches), ensure_ascii=False, indent=2))
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
