"""Immutable Git source exports and compare-and-swap publication for SG-SPEC-0069."""

from __future__ import annotations

import os
import re
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory

from subject_canonical_source import DECLARATION
from subject_read_model_io import SubjectDocumentError

SOURCE_REF_PREFIX = "refs/specgraph/subject-storage/"


class SubjectSourceConflict(SubjectDocumentError):
    """The selected source no longer satisfies a publication precondition."""


def git_command(
    repository: Path,
    *arguments: str,
    content: bytes | None = None,
    environment: dict[str, str] | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess:
    # Inherited Git overrides must not select a different repository, index or replacement object.
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update({"GIT_NO_REPLACE_OBJECTS": "1", **(environment or {})})
    result = subprocess.run(
        ["git", "-C", str(repository), *arguments],
        input=content,
        capture_output=True,
        env=env,
        check=False,
    )
    if check and result.returncode:
        raise SubjectDocumentError(result.stderr.decode("utf-8", errors="replace").strip())
    return result


def require_commit_id(value: str) -> None:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{40}|[0-9a-f]{64}", value):
        raise SubjectDocumentError("expected a complete lowercase Git commit ID")


def selected_source_commit(repository: Path, source_ref: str) -> str:
    if repository.is_symlink() or not repository.is_dir():
        raise SubjectDocumentError("repository root must be a real directory")
    if not isinstance(source_ref, str) or not source_ref.startswith(SOURCE_REF_PREFIX):
        raise SubjectDocumentError(f"publication requires an explicit {SOURCE_REF_PREFIX} ref")
    git_command(repository, "check-ref-format", source_ref)
    symbolic = git_command(repository, "symbolic-ref", "--quiet", source_ref, check=False)
    if symbolic.returncode != 1:
        raise SubjectDocumentError("source ref must be an existing direct ref, not a symbolic ref")
    commit = git_command(repository, "rev-parse", "--verify", source_ref).stdout.decode().strip()
    require_commit_id(commit)
    kind = git_command(repository, "cat-file", "-t", commit).stdout.decode().strip()
    if kind != "commit":
        raise SubjectDocumentError("source ref must point directly to a commit")
    return commit


def _storage_entry(path: str) -> bool:
    return path in {"specs", DECLARATION, "specs/requirements", "specs/criteria"} or any(
        path.startswith(prefix) for prefix in ("specs/requirements/", "specs/criteria/")
    )


@dataclass(frozen=True)
class SubjectSourceBlob:
    path: str
    mode: str
    content: bytes


@dataclass(frozen=True)
class SubjectSourceCommit:
    repository: Path
    commit_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.repository, Path):
            raise ValueError("repository must be a Path")
        require_commit_id(self.commit_id)

    def blobs(self) -> tuple[SubjectSourceBlob, ...]:
        entries = git_command(
            self.repository, "ls-tree", "-r", "-z", self.commit_id, "--", "specs"
        ).stdout
        blobs = []
        for entry in entries.split(b"\0"):
            if not entry:
                continue
            metadata, encoded_path = entry.split(b"\t", 1)
            path = encoded_path.decode("utf-8")
            if not _storage_entry(path):
                continue
            mode, kind, object_id = metadata.decode("ascii").split()
            if (
                kind != "blob"
                or mode not in {"100644", "100755"}
                or str(PurePosixPath(path)) != path
                or ".." in PurePosixPath(path).parts
                or path in {"specs", "specs/requirements", "specs/criteria"}
            ):
                raise SubjectDocumentError("canonical storage must contain real files, no symlinks")
            content = git_command(self.repository, "cat-file", "blob", object_id).stdout
            blobs.append(SubjectSourceBlob(path, mode, content))
        return tuple(blobs)

    @contextmanager
    def export(self) -> Iterator[Path]:
        """Export only subject storage; callers retain the context while reading its paths."""
        blobs = self.blobs()
        with TemporaryDirectory(prefix="specgraph-subject-source-") as directory:
            root = Path(directory)
            (root / "specs").mkdir()
            for blob in blobs:
                target = root / blob.path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(blob.content)
            yield root

    def candidate_commit(
        self, files: dict[str, bytes], recorded_at: str, request_digest: str
    ) -> str:
        """Prepare immutable objects using a private index; preserve unrelated tracked paths."""
        modes = {blob.path: blob.mode for blob in self.blobs()}
        with TemporaryDirectory(prefix="specgraph-subject-index-") as directory:
            environment = {"GIT_INDEX_FILE": str(Path(directory) / "index")}
            git_command(self.repository, "read-tree", self.commit_id, environment=environment)
            for path, content in sorted(files.items()):
                blob = git_command(self.repository, "hash-object", "-w", "--stdin", content=content)
                object_id = blob.stdout.decode().strip()
                git_command(
                    self.repository,
                    "update-index",
                    "--add",
                    "--cacheinfo",
                    f"{modes.get(path, '100644')},{object_id},{path}",
                    environment=environment,
                )
            tree = git_command(
                self.repository, "write-tree", environment=environment
            ).stdout.strip()
            attribution = {
                "GIT_AUTHOR_NAME": "SpecGraph subject writer",
                "GIT_AUTHOR_EMAIL": "subject-writer@localhost",
                "GIT_AUTHOR_DATE": recorded_at,
                "GIT_COMMITTER_NAME": "SpecGraph subject writer",
                "GIT_COMMITTER_EMAIL": "subject-writer@localhost",
                "GIT_COMMITTER_DATE": recorded_at,
            }
            result = git_command(
                self.repository,
                "-c",
                "commit.gpgsign=false",
                "commit-tree",
                tree.decode(),
                "-p",
                self.commit_id,
                content=f"Publish subject source request {request_digest}\n".encode(),
                environment=attribution,
            )
            return result.stdout.decode().strip()

    def check_candidate_scope(self, candidate_commit: str, paths: set[str]) -> None:
        header = git_command(self.repository, "cat-file", "commit", candidate_commit).stdout.split(
            b"\n\n", 1
        )[0]
        parents = [line[7:].decode() for line in header.splitlines() if line.startswith(b"parent ")]
        changed = git_command(
            self.repository,
            "diff-tree",
            "--no-commit-id",
            "--name-only",
            "-z",
            "--no-renames",
            "-r",
            self.commit_id,
            candidate_commit,
        ).stdout
        changed_paths = {path.decode("utf-8") for path in changed.split(b"\0") if path}
        if parents != [self.commit_id] or changed_paths != paths:
            raise SubjectDocumentError(
                "prepared commit has unrequested paths or an unexpected parent"
            )

    def publish(self, source_ref: str, candidate_commit: str) -> None:
        require_commit_id(candidate_commit)
        if selected_source_commit(self.repository, source_ref) != self.commit_id:
            raise SubjectSourceConflict("source ref changed before publication")
        result = git_command(
            self.repository,
            "update-ref",
            "--no-deref",
            source_ref,
            candidate_commit,
            self.commit_id,
            check=False,
        )
        if result.returncode:
            if selected_source_commit(self.repository, source_ref) != self.commit_id:
                raise SubjectSourceConflict("source ref changed at atomic publication")
            raise SubjectDocumentError(result.stderr.decode("utf-8", errors="replace").strip())
