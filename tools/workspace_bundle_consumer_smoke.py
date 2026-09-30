#!/usr/bin/env python3
"""Exercise a published workspace bundle through a pinned real SpecSpace HTTP consumer."""

from __future__ import annotations

import argparse
import functools
import json
import shutil
import subprocess
import sys
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class QuietArtifacts(SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:
        pass


class ArtifactServer(ThreadingHTTPServer):
    # The real consumer fetches up to twelve artifacts concurrently.
    request_queue_size = 64


def require_workspace_content(payload: dict[str, object], workspace_id: str) -> dict[str, object]:
    workspace = payload.get("workspace", {})
    if not (
        workspace.get("available") is True
        and workspace.get("id") == workspace_id
        and workspace.get("ready") is True
    ):
        raise ValueError(
            "Published bundle does not yield the selected ready source: " + json.dumps(workspace)
        )
    summary = payload.get("summary", {})
    if summary.get("candidate_node_count", 0) <= 0 or summary.get("missing_artifact_count") != 0:
        raise ValueError("Workspace has incomplete candidate content: " + json.dumps(summary))
    # A complete read model may correctly report a blocked domain workflow.
    return summary


def run(
    bundle: Path,
    consumer_repo: Path,
    workspace_id: str,
    expected_commit: str,
    require_binding: bool = True,
) -> dict[str, object]:
    commit = subprocess.check_output(
        ["git", "-C", str(consumer_repo), "rev-parse", "HEAD"], text=True
    ).strip()
    if commit != expected_commit:
        raise ValueError("SpecSpace checkout differs from selected consumer source pin")
    dirty = subprocess.check_output(
        ["git", "-C", str(consumer_repo), "status", "--porcelain", "--", "viewer"], text=True
    )
    if dirty:
        raise ValueError("SpecSpace consumer source has uncommitted changes")
    sys.path.insert(0, str(consumer_repo))
    from viewer import specspace_provider

    checks: dict[str, object] = {}
    with tempfile.TemporaryDirectory(prefix="workspace-consumer-") as temporary:
        root = Path(temporary) / "bundle"
        shutil.copytree(bundle, root)
        handler = functools.partial(QuietArtifacts, directory=str(root))
        server = ArtifactServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:

            def read(selected_workspace: str = workspace_id) -> dict[str, object]:
                delegate = specspace_provider.HttpSpecGraphProvider(
                    base_url=f"http://127.0.0.1:{server.server_port}",
                    cache=specspace_provider.HttpArtifactCache(),
                )
                provider = specspace_provider.ProductWorkspaceHttpProvider(
                    delegate, selected_workspace
                )
                status, payload = provider.read_idea_to_spec_workspace()
                if status != 200:
                    raise ValueError(f"Consumer returned HTTP {status}")
                return payload

            payload = read()
            summary = require_workspace_content(payload, workspace_id)
            checks["readable_workspace"] = True
            checks["workspace_source_ready"] = True
            checks["candidate_node_count"] = summary["candidate_node_count"]
            checks["domain_status"] = summary.get("status")
            checks["workspace_id"] = workspace_id
            if require_binding:
                binding = payload.get("workspace_binding", {})
                if binding.get("status") != "ready" or binding.get("trusted") is not True:
                    raise ValueError("Bound workspace did not yield a ready trusted binding")
                checks["ready_binding"] = True
                manifest_path = root / "artifact_manifest.json"
                original_manifest = manifest_path.read_bytes()
                manifest = json.loads(original_manifest)
                candidate_paths = {
                    f"runs/{workspace_id}/{name}"
                    for name in (
                        "active_idea_to_spec_candidate.json",
                        "repaired_active_idea_to_spec_candidate.json",
                    )
                }
                listed_candidates = candidate_paths.intersection(
                    entry["path"] for entry in manifest["files"]
                )
                if not listed_candidates:
                    raise ValueError("No scoped active candidate is manifest-authorized")
                manifest["files"] = [
                    entry for entry in manifest["files"] if entry["path"] not in candidate_paths
                ]
                manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
                if read().get("workspace", {}).get("available") is True:
                    raise ValueError(
                        "Consumer accepted unlisted scoped candidates or used flat fallback"
                    )
                checks["unlisted_candidate_rejected_with_flat_alias_present"] = True
                manifest_path.write_bytes(original_manifest)
                for path in listed_candidates:
                    artifact = root / path
                    artifact.write_bytes(artifact.read_bytes() + b"\n")
                if read().get("workspace", {}).get("available") is True:
                    raise ValueError("Consumer accepted a candidate with mismatched digest")
                checks["candidate_digest_mismatch_rejected"] = True
            if read("foreign-workspace").get("workspace", {}).get("available") is True:
                raise ValueError("Consumer accepted candidate identity from another workspace")
            checks["foreign_workspace_rejected"] = True
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()
    return {
        "artifact_kind": "workspace_bundle_consumer_smoke",
        "ok": True,
        "consumer_commit": commit,
        "workspace_id": workspace_id,
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-dir", required=True, type=Path)
    parser.add_argument("--consumer-repo", required=True, type=Path)
    parser.add_argument("--consumer-commit", required=True)
    parser.add_argument("--workspace-id", required=True)
    parser.add_argument("--legacy-workspace", action="store_true")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        report = run(
            args.bundle_dir.resolve(),
            args.consumer_repo.resolve(),
            args.workspace_id,
            args.consumer_commit,
            require_binding=not args.legacy_workspace,
        )
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as error:
        report = {
            "artifact_kind": "workspace_bundle_consumer_smoke",
            "ok": False,
            "workspace_id": args.workspace_id,
            "error": str(error),
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, sort_keys=True))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
