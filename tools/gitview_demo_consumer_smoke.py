#!/usr/bin/env python3
"""Check the static GitView demo with the real pinned SpecSpace HTTP provider."""

from __future__ import annotations

import argparse
import functools
import http.server
import json
import socketserver
import subprocess
import sys
import threading
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-dir", required=True, type=Path)
    parser.add_argument("--consumer-repo", required=True, type=Path)
    parser.add_argument("--consumer-commit", required=True)
    args = parser.parse_args()
    repo = args.consumer_repo.resolve()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=repo, text=True).strip()
    dirty = subprocess.check_output(["git", "status", "--porcelain"], cwd=repo, text=True)
    if head != args.consumer_commit or dirty:
        raise SystemExit("SpecSpace checkout does not match the clean pinned commit")
    sys.path.insert(0, str(repo))
    from viewer.specspace_provider import (  # noqa: PLC0415
        HttpArtifactCache,
        HttpSpecGraphProvider,
        ProductWorkspaceHttpProvider,
    )

    class QuietHandler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, _format: str, *args: object) -> None:
            pass

    handler = functools.partial(QuietHandler, directory=str(args.bundle_dir.resolve()))
    with socketserver.TCPServer(("127.0.0.1", 0), handler) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            provider = ProductWorkspaceHttpProvider(
                HttpSpecGraphProvider(
                    base_url=f"http://127.0.0.1:{server.server_address[1]}",
                    cache=HttpArtifactCache(),
                ),
                workspace_id="gitview",
            )
            status, graph = provider.read_spec_graph()
            manifest, error = provider._manifest()
            if error is not None or manifest is None:
                raise ValueError(f"Demo manifest is unavailable: {error}")
            _, binding = provider._workspace_artifacts(manifest)
            summary = graph["summary"]
            if status != 200 or summary["node_count"] != 71 or summary["edge_count"] != 434:
                raise ValueError(f"Unexpected demo graph: {status}, {summary}")
            if summary["diagnostic_count"] != 0 or summary["broken_edge_count"] != 0:
                raise ValueError(f"Demo graph has diagnostics: {summary}")
            if binding.get("status") != "ready" or binding.get("trusted") is not True:
                raise ValueError(f"Demo workspace binding is not trusted and ready: {binding}")
            print(
                json.dumps(
                    {
                        "status": "passed",
                        "consumer_commit": head,
                        "summary": summary,
                        "binding": "ready",
                        "scope": "read_only_demo_graph",
                    }
                )
            )
        finally:
            server.shutdown()
            thread.join()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
