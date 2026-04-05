#!/usr/bin/env python3
"""Search ChatGPT dialog conversations via PageIndex.

Requires the PageIndex local API server to be running:
    cd ~/Development/GitHub/PageIndexInstance
    python3 -m pageindex.local_api --port 8765

Usage:
    python3 tools/search_pageindex.py QUERY [options]

Options:
    --catalog PATH    Path to catalog.json
                      (default:
                       ~/Development/GitHub/PageIndexInstance/results/chatgpt_dialogs/catalog.json)
    --api-url URL     PageIndex local API base URL (default: http://localhost:8765)
    --model MODEL     LLM model for retrieval (default: gpt-4o-2024-11-20)
    --top-k N         Number of results to return (default: 7)
    --context         Fetch full node text for top results
    --json            Output raw JSON instead of formatted text

Example:
    python3 tools/search_pageindex.py "success criteria for SpecGraph"
    python3 tools/search_pageindex.py "agent operating system constraints" --top-k 5 --context
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

_DEFAULT_CATALOG_PATHS = [
    Path.home()
    / "Development/GitHub/PageIndexInstance/results/chatgpt_dialogs_optimized/catalog.json",
    Path.home() / "Development/GitHub/PageIndexInstance/results/chatgpt_dialogs/catalog.json",
]
_DEFAULT_API_URL = "http://localhost:8765"


def _find_default_catalog() -> Path | None:
    """Find the first available catalog."""
    for path in _DEFAULT_CATALOG_PATHS:
        if path.exists():
            return path
    return _DEFAULT_CATALOG_PATHS[0]


def _post(url: str, payload: dict) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")
        print(f"HTTP {exc.code} from PageIndex API:\n{body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError:
        print(
            f"Cannot reach PageIndex API at {url}.\n"
            "Start it with:\n"
            "  cd ~/Development/GitHub/PageIndexInstance\n"
            "  python3 -m pageindex.local_api --port 8765",
            file=sys.stderr,
        )
        sys.exit(1)


def _search(api_url: str, query: str, catalog_path: Path, model: str, top_k: int) -> list[dict]:
    payload = {
        "query": query,
        "catalog": str(catalog_path),
        "model": model,
        "top_k": top_k,
        "include_reasoning": True,
    }
    result = _post(f"{api_url}/search", payload)
    return result.get("selected_nodes") or result.get("results") or result.get("nodes") or []


def _fetch_context(api_url: str, nodes: list[dict]) -> list[dict]:
    selected = [
        {
            "record_id": n.get("record_id", ""),
            "node_id": n.get("node_id", ""),
            "title": n.get("title", ""),
            "source_path": n.get("source_path", ""),
            "output_path": n.get("output_path", ""),
            "summary": n.get("summary", ""),
            "line_number": n.get("line_number") or n.get("line_num"),
            "reasoning": n.get("reasoning", ""),
        }
        for n in nodes
    ]
    result = _post(api_url + "/context", {"selected_nodes": selected, "require_text": True})
    return result.get("nodes") or []


def _format_results(nodes: list[dict], *, with_context: bool) -> str:
    if not nodes:
        return "(no results)"

    parts: list[str] = []
    for i, node in enumerate(nodes, start=1):
        title = node.get("title", "—")
        doc = node.get("document_name") or node.get("record_id", "")
        summary = node.get("summary", "")
        reasoning = node.get("reasoning", "")
        text = node.get("text", "") if with_context else ""

        block = [f"[{i}] {title}"]
        if doc:
            block.append(f"    Source: {doc}")
        if summary:
            block.append(f"    Summary: {summary}")
        if reasoning:
            block.append(f"    Relevance: {reasoning}")
        if text:
            block.append(f"    ---\n{text.strip()}\n    ---")
        parts.append("\n".join(block))

    return "\n\n".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="Search query")
    parser.add_argument("--catalog", default=str(_find_default_catalog()))
    parser.add_argument("--api-url", default=_DEFAULT_API_URL)
    parser.add_argument("--model", default="gpt-4o-2024-11-20")
    parser.add_argument("--top-k", type=int, default=7)
    parser.add_argument(
        "--context",
        action="store_true",
        help="Fetch full node text for each result",
    )
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    catalog_path = Path(args.catalog)
    if not catalog_path.exists():
        print(
            f"Catalog not found: {catalog_path}\n"
            "Build it first:\n"
            "  cd ~/Development/GitHub/ChatGPTDialogs\n"
            "  python3 export_to_markdown.py\n"
            "  cd ~/Development/GitHub/PageIndexInstance\n"
            "  python3 index_chatgpt_dialogs.py",
            file=sys.stderr,
        )
        sys.exit(1)

    nodes = _search(args.api_url, args.query, catalog_path, args.model, args.top_k)

    if args.context and nodes:
        nodes = _fetch_context(args.api_url, nodes)

    if args.as_json:
        print(json.dumps(nodes, indent=2, ensure_ascii=False))
    else:
        print(_format_results(nodes, with_context=args.context))


if __name__ == "__main__":
    main()
