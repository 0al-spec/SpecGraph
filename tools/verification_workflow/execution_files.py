"""Run-local filesystem custody and safe, filter-free extraction of Git blobs."""

import json
import os
import stat
import subprocess
from pathlib import Path

from traceability.criterion_inputs import read_regular, sha256

from .model import FilePin, revision


def regular_path(root: Path, path: Path) -> Path:
    if root.is_symlink() or not root.is_dir():
        raise ValueError("artifact root must remain a real directory")
    path = path.absolute()
    relative = path.relative_to(root)
    if not relative.parts or any(part in {".", ".."} for part in relative.parts):
        raise ValueError("artifact path escapes its run root")
    current = root
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise ValueError("symlink artifacts are unsupported")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError("artifact must be an unlinked regular file")
    return path


def git(repository: Path, *arguments: str) -> bytes:
    return subprocess.check_output(
        ["git", "--no-replace-objects", "-C", str(repository), *arguments],
        stderr=subprocess.PIPE,
        timeout=30,
    )


def snapshot(repository: Path, commit: str, destination: Path) -> tuple[tuple[FilePin, int], ...]:
    revision(commit)
    if git(repository, "rev-parse", "--verify", f"{commit}^{{commit}}").decode().strip() != commit:
        raise ValueError("execution revision must identify the exact commit")
    destination.mkdir()
    manifest = []
    total = 0
    for entry in git(repository, "ls-tree", "-rz", "--full-tree", commit).split(b"\0"):
        if not entry:
            continue
        metadata, raw_path = entry.split(b"\t", 1)
        mode, kind, object_id = metadata.decode().split()
        path = raw_path.decode()
        # FilePin applies the existing normalized relative-path contract.
        pin = FilePin(path, "0" * 64)
        if mode not in {"100644", "100755"} or kind != "blob" or ".git" in Path(path).parts:
            raise ValueError("snapshot supports regular Git blobs only")
        size = int(git(repository, "cat-file", "-s", object_id))
        total += size
        if size > 128 * 1024 * 1024 or total > 512 * 1024 * 1024 or len(manifest) >= 10000:
            raise ValueError("snapshot exceeds bounded extraction limits")
        raw = git(repository, "cat-file", "blob", object_id)
        if len(raw) != size:
            raise ValueError("Git blob changed during extraction")
        target = destination / pin.path
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(raw)
        permissions = 0o755 if mode == "100755" else 0o644
        target.chmod(permissions)
        manifest.append((FilePin(path, sha256(raw)), permissions))
    return tuple(manifest)


def check_snapshot(root: Path, manifest: tuple[tuple[FilePin, int], ...]) -> None:
    for pin, permissions in manifest:
        path = regular_path(root, root / pin.path)
        if sha256(read_regular(path, 128 * 1024 * 1024)) != pin.sha256:
            raise ValueError(f"snapshot bytes changed: {pin.path}")
        if stat.S_IMODE(path.stat().st_mode) != permissions:
            raise ValueError(f"snapshot mode changed: {pin.path}")


def existing_paths(root: Path) -> frozenset[Path]:
    paths = set()
    for directory, directories, files in os.walk(root, followlinks=False):
        paths.update(Path(directory) / name for name in (*directories, *files))
    return frozenset(paths)


class RunFiles:
    """I/O adapter: exclusive artifacts, byte checks and atomic terminal publication."""

    def __init__(self, root: Path):
        self.root = root
        self.pins: list[FilePin] = []

    def write(self, name: str, raw: bytes) -> FilePin:
        pin = FilePin(name, sha256(raw))
        if self.root.is_symlink() or not self.root.is_dir():
            raise ValueError("run root must remain a real directory")
        path = self.root / name
        parent = self.root
        for part in Path(name).parts[:-1]:
            parent = parent / part
            if parent.is_symlink():
                raise ValueError("artifact parent cannot be a symlink")
            parent.mkdir(exist_ok=True)
        with path.open("xb") as stream:
            stream.write(raw)
        regular_path(self.root, path)
        self.pins.append(pin)
        return pin

    def json(self, name: str, value: object) -> FilePin:
        return self.write(
            name, (json.dumps(value, ensure_ascii=False, indent=2, default=sorted) + "\n").encode()
        )

    def verify(self) -> None:
        for pin in self.pins:
            path = regular_path(self.root, self.root / pin.path)
            if sha256(read_regular(path, 128 * 1024 * 1024)) != pin.sha256:
                raise ValueError(f"run artifact changed: {pin.path}")

    def terminal(self, payload: object) -> None:
        if self.root.is_symlink() or not self.root.is_dir():
            raise ValueError("run root must remain a real directory")
        target = self.root / "terminal.json"
        temporary = self.root / ".terminal.tmp"
        if target.exists():
            raise FileExistsError("terminal record already exists")
        with temporary.open("xb") as stream:
            stream.write((json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode())
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
        descriptor = os.open(self.root, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
