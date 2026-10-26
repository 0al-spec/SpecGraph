"""Fixed loopback HTTP surface; no file browser or note mutation routes."""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from .snapshot import NotesPreview

ASSETS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
    "/icon.svg": ("icon.svg", "image/svg+xml"),
}


def create_server(
    workspace: Path, *, port: int = 0, node_id: str | None = None
) -> ThreadingHTTPServer:
    preview = NotesPreview(workspace, node_id)
    assets = Path(__file__).with_name("static")

    class NotesPage(BaseHTTPRequestHandler):
        def log_message(self, *_args) -> None:
            pass

        def respond(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; script-src 'self'; style-src 'self'; "
                "connect-src 'self'; object-src 'none'; base-uri 'none'",
            )
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def do_GET(self) -> None:
            allowed_hosts = {
                f"127.0.0.1:{self.server.server_port}",
                f"localhost:{self.server.server_port}",
            }
            if self.headers.get("Host", "").lower() not in allowed_hosts:
                self.respond(403, b"Local host required.", "text/plain")
                return
            route = urlsplit(self.path)
            if route.query:
                self.respond(400, b"The workspace is selected at startup.", "text/plain")
            elif route.path == "/api/notes":
                body = json.dumps(preview.observe(), ensure_ascii=False).encode("utf-8")
                self.respond(200, body, "application/json; charset=utf-8")
            elif route.path in ASSETS:
                name, content_type = ASSETS[route.path]
                self.respond(200, (assets / name).read_bytes(), content_type)
            else:
                self.respond(404, b"Not found.", "text/plain")

        def do_HEAD(self) -> None:
            self.do_GET()

        def do_POST(self) -> None:
            self.respond(405, b"Read-only preview.", "text/plain")

    return ThreadingHTTPServer(("127.0.0.1", port), NotesPage)
