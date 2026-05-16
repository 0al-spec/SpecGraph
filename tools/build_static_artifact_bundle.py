from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

DEFAULT_OUTPUT_DIR = Path("dist/specgraph-public")
PUBLISHED_ROOTS = ("specs", "runs")
REQUIRED_RUN_SURFACES = (
    "graph_dashboard.json",
    "graph_backlog_projection.json",
    "graph_next_moves.json",
    "spec_activity_feed.json",
)
JUNK_FILENAMES = {".DS_Store", ".gitkeep"}
JUNK_DIRNAMES = {"__pycache__", ".pytest_cache", ".ruff_cache"}
LOCAL_PATH_RE = re.compile(r"(?P<prefix>(?:/Users/|/private/var/|/var/folders/))[^\s\"'<>]+")
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"(?i)(?:^|[^A-Z0-9_])(?:[A-Z0-9_]*_)?API_KEY\s*=\s*[^\s\"']+"),
    re.compile(r"(?i)\"(?:api_key|authorization|password)\"\s*:\s*\"[^\"\n]+\""),
)


@dataclass
class PublishFile:
    path: str
    root: str
    size_bytes: int
    sha256: str


@dataclass
class BuildResult:
    output_dir: Path
    manifest_path: Path
    checksums_path: Path
    manifest: dict[str, object]
    copied_files: list[PublishFile] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    redacted_local_path_occurrences: int = 0


class PublishBundleError(RuntimeError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def repo_git_value(root: Path, *args: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    value = completed.stdout.strip()
    return value or None


def should_skip_file(path: Path, root: Path) -> bool:
    rel = path.relative_to(root)
    if path.name in JUNK_FILENAMES:
        return True
    return any(part in JUNK_DIRNAMES for part in rel.parts)


def iter_publish_sources(repo_root: Path) -> Iterable[tuple[str, Path, PurePosixPath]]:
    for root_name in PUBLISHED_ROOTS:
        source_root = repo_root / root_name
        if not source_root.exists():
            continue
        for path in sorted(source_root.rglob("*")):
            if not path.is_file() or should_skip_file(path, repo_root):
                continue
            rel = PurePosixPath(root_name, path.relative_to(source_root).as_posix())
            yield root_name, path, rel


def load_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise PublishBundleError(f"unsupported non-utf8 artifact: {path}") from exc


def validate_json_artifact(path: Path, text: str) -> None:
    try:
        json.loads(text)
    except json.JSONDecodeError as exc:
        raise PublishBundleError(f"malformed JSON artifact: {path}: {exc}") from exc


def redact_local_paths(text: str) -> tuple[str, int]:
    return LOCAL_PATH_RE.subn("$LOCAL_PATH", text)


def detect_secret_like_content(path: PurePosixPath, text: str) -> list[str]:
    findings: list[str] = []
    for pattern in SECRET_PATTERNS:
        if pattern.search(text):
            findings.append(f"secret-like content in {path}")
    return findings


def write_text_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    tmp_path.write_text(text, encoding="utf-8")
    tmp_path.replace(path)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        for chunk in iter(lambda: file_obj.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ensure_required_surfaces(output_dir: Path) -> dict[str, bool]:
    return {surface: (output_dir / "runs" / surface).is_file() for surface in REQUIRED_RUN_SURFACES}


def build_manifest(
    *,
    repo_root: Path,
    output_dir: Path,
    copied_files: list[PublishFile],
    warnings: list[str],
    redacted_local_path_occurrences: int,
) -> dict[str, object]:
    root_summary: dict[str, dict[str, int]] = {
        root: {"file_count": 0, "byte_count": 0} for root in PUBLISHED_ROOTS
    }
    for file_info in copied_files:
        root_info = root_summary[file_info.root]
        root_info["file_count"] += 1
        root_info["byte_count"] += file_info.size_bytes

    required_surfaces = ensure_required_surfaces(output_dir)
    missing_required = [path for path, present in required_surfaces.items() if not present]
    safety_status = "passed" if not missing_required else "failed"
    if missing_required:
        warnings.append("missing required run surfaces: " + ", ".join(missing_required))

    return {
        "artifact_kind": "specgraph_static_artifact_manifest",
        "schema_version": 1,
        "generated_at": utc_now(),
        "git": {
            "sha": repo_git_value(repo_root, "rev-parse", "HEAD"),
            "ref": repo_git_value(repo_root, "rev-parse", "--abbrev-ref", "HEAD"),
        },
        "published_roots": list(PUBLISHED_ROOTS),
        "roots": root_summary,
        "checksums_path": "checksums.sha256",
        "required_surfaces": required_surfaces,
        "safety_gate": {
            "status": safety_status,
            "redacted_local_path_occurrences": redacted_local_path_occurrences,
            "warnings": warnings,
        },
        "files": [file_info.__dict__ for file_info in copied_files],
    }


def write_checksums(output_dir: Path, copied_files: list[PublishFile]) -> Path:
    checksums_path = output_dir / "checksums.sha256"
    lines = [
        f"{file_info.sha256}  {file_info.path}"
        for file_info in sorted(copied_files, key=lambda f: f.path)
    ]
    write_text_atomic(checksums_path, "\n".join(lines) + "\n")
    return checksums_path


def refresh_viewer_surfaces(repo_root: Path) -> None:
    completed = subprocess.run(
        ["make", "viewer-surfaces"],
        cwd=repo_root,
        text=True,
    )
    if completed.returncode != 0:
        raise PublishBundleError("make viewer-surfaces failed")


def build_public_bundle(
    *,
    repo_root: Path,
    output_dir: Path,
    refresh_surfaces: bool = False,
    strict_required_surfaces: bool = True,
) -> BuildResult:
    repo_root = repo_root.resolve()
    output_dir = (
        (repo_root / output_dir).resolve() if not output_dir.is_absolute() else output_dir.resolve()
    )

    if refresh_surfaces:
        refresh_viewer_surfaces(repo_root)

    git_dir = repo_root / ".git"
    if output_dir == repo_root or output_dir == git_dir or git_dir in output_dir.parents:
        raise PublishBundleError(f"unsafe output directory: {output_dir}")

    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    copied_files: list[PublishFile] = []
    warnings: list[str] = []
    redacted_total = 0
    secret_findings: list[str] = []

    for root_name, source_path, rel_path in iter_publish_sources(repo_root):
        text = load_text(source_path)
        if root_name == "runs" and source_path.suffix == ".json":
            validate_json_artifact(source_path, text)

        redacted_text, redaction_count = redact_local_paths(text)
        redacted_total += redaction_count
        secret_findings.extend(detect_secret_like_content(rel_path, redacted_text))

        target_path = output_dir / rel_path.as_posix()
        write_text_atomic(target_path, redacted_text)
        copied_files.append(
            PublishFile(
                path=rel_path.as_posix(),
                root=root_name,
                size_bytes=target_path.stat().st_size,
                sha256=file_sha256(target_path),
            )
        )

    if secret_findings:
        shutil.rmtree(output_dir)
        raise PublishBundleError("; ".join(sorted(set(secret_findings))))

    manifest = build_manifest(
        repo_root=repo_root,
        output_dir=output_dir,
        copied_files=copied_files,
        warnings=warnings,
        redacted_local_path_occurrences=redacted_total,
    )
    required_surfaces = manifest["required_surfaces"]
    if not isinstance(required_surfaces, dict):
        raise PublishBundleError("internal manifest error: required_surfaces is not an object")
    missing_required = [path for path, present in required_surfaces.items() if not present]
    if strict_required_surfaces and missing_required:
        shutil.rmtree(output_dir)
        raise PublishBundleError("missing required run surfaces: " + ", ".join(missing_required))

    manifest_path = output_dir / "artifact_manifest.json"
    write_text_atomic(manifest_path, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    copied_files.append(
        PublishFile(
            path="artifact_manifest.json",
            root=".",
            size_bytes=manifest_path.stat().st_size,
            sha256=file_sha256(manifest_path),
        )
    )
    checksums_path = write_checksums(output_dir, copied_files)

    return BuildResult(
        output_dir=output_dir,
        manifest_path=manifest_path,
        checksums_path=checksums_path,
        manifest=manifest,
        copied_files=copied_files,
        warnings=warnings,
        redacted_local_path_occurrences=redacted_total,
    )


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a static HTTP-ready SpecGraph artifact bundle.",
    )
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument(
        "--refresh-viewer-surfaces",
        action="store_true",
        help="Run make viewer-surfaces before collecting specs/ and runs/.",
    )
    parser.add_argument(
        "--allow-missing-required-surfaces",
        action="store_true",
        help="Build even if core viewer-facing runs artifacts are missing.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    try:
        result = build_public_bundle(
            repo_root=args.repo_root,
            output_dir=args.output_dir,
            refresh_surfaces=args.refresh_viewer_surfaces,
            strict_required_surfaces=not args.allow_missing_required_surfaces,
        )
    except PublishBundleError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    summary = {
        "output_dir": str(result.output_dir),
        "manifest_path": str(result.manifest_path),
        "checksums_path": str(result.checksums_path),
        "file_count": len(result.copied_files),
        "redacted_local_path_occurrences": result.redacted_local_path_occurrences,
        "safety_gate": result.manifest["safety_gate"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
