"""Serve one saved sketch as a local live mind map (proposal 0228)."""

import argparse
import json
from pathlib import Path

from specdraft_preview.server import create_server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--node-id", help="Display one existing note branch")
    args = parser.parse_args(argv)
    if not args.workspace.is_dir():
        parser.error("--workspace must be an existing notes directory")
    if not 0 <= args.port <= 65535:
        parser.error("--port must be between 0 and 65535; 0 selects a free port")
    try:
        server = create_server(args.workspace, port=args.port, node_id=args.node_id)
    except OSError as error:
        parser.error(f"Cannot start preview: {error}")
    print(
        json.dumps({"url": f"http://127.0.0.1:{server.server_port}/", "canonical": False}),
        flush=True,
    )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
