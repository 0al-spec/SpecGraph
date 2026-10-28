"""Capture a compiler-checked ontology without reopening the consumer inputs.

The caller selects the compiler. Its digest identifies the executed bytes, but
does not establish where they came from or make domain claims authoritative.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


class OntologySnapshotError(ValueError):
    """An ontology snapshot could not be verified for use."""


@dataclass(frozen=True, slots=True)
class OntologySnapshot:
    """Immutable source and IR bytes captured in the same compiler invocation."""

    source_bytes: bytes
    ir_bytes: bytes
    source_sha256: str
    compiler_source_digest: str
    ir_sha256: str
    compiler_sha256: str
    compiler_provenance: str = "not_verified"


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise OntologySnapshotError(f"compiler IR has duplicate key: {key!r}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise OntologySnapshotError(f"compiler IR has non-finite value: {value}")


def _strict_float(value: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise OntologySnapshotError(f"compiler IR has non-finite value: {value}")
    return result


def capture_ontology_snapshot(
    source_path: Path,
    ontologyc: Path,
    *,
    expected_ir_path: Path | None = None,
) -> OntologySnapshot:
    """Compile captured source; optionally require an exact saved-IR match.

    A private copy of the selected executable and source ensures their paths
    cannot be replaced between hashing and use. This is not a sandbox: callers
    must trust the chosen compiler and its execution environment.
    """
    try:
        source_bytes = source_path.read_bytes()
        # Foundation's UTF-8 decoder strips a leading BOM before hashing text.
        compiler_source = source_bytes.decode("utf-8-sig").encode("utf-8")
        expected_ir = expected_ir_path.read_bytes() if expected_ir_path is not None else None
        if not ontologyc.is_file() or not os.access(ontologyc, os.X_OK):
            raise OntologySnapshotError("ontologyc must be an executable file")
        compiler_bytes = ontologyc.read_bytes()
    except (OSError, UnicodeError) as error:
        raise OntologySnapshotError(f"cannot capture ontology inputs: {error}") from error

    source_sha256 = _sha256(source_bytes)
    compiler_source_digest = f"sha256:{_sha256(compiler_source)}"
    compiler_sha256 = _sha256(compiler_bytes)
    try:
        with tempfile.TemporaryDirectory(prefix="specgraph-ontology-") as temporary:
            work = Path(temporary)
            staged_source = work / "ontology.yaml"
            staged_source.write_bytes(source_bytes)
            staged_source.chmod(0o400)
            executable = work / "ontologyc"
            executable.write_bytes(compiler_bytes)
            executable.chmod(0o500)
            output = work / "generated"

            for arguments in (
                ("check", str(staged_source)),
                ("compile", str(staged_source), "--target", "typescript", "--out", str(output)),
            ):
                subprocess.run(
                    [str(executable), *arguments],
                    cwd=work,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if executable.read_bytes() != compiler_bytes:
                    raise OntologySnapshotError("compiler changed captured executable")

            if staged_source.read_bytes() != source_bytes:
                raise OntologySnapshotError("compiler changed captured ontology source")
            ir_bytes = (output / "ontology.normalized.json").read_bytes()
            ir = json.loads(
                ir_bytes.decode("utf-8"),
                object_pairs_hook=_strict_object,
                parse_constant=_reject_constant,
                parse_float=_strict_float,
            )
            if not isinstance(ir, dict) or ir.get("sourceDigest") != compiler_source_digest:
                raise OntologySnapshotError(
                    "compiler IR source digest does not match captured source"
                )
            if expected_ir is not None and ir_bytes != expected_ir:
                raise OntologySnapshotError("saved ontology IR differs from compiler output")
    except subprocess.CalledProcessError as error:
        detail = error.stderr.strip() if isinstance(error.stderr, str) else ""
        raise OntologySnapshotError(f"ontology compiler failed: {detail or error}") from error
    except (OSError, UnicodeError, json.JSONDecodeError, subprocess.TimeoutExpired) as error:
        raise OntologySnapshotError(f"cannot verify ontology snapshot: {error}") from error

    return OntologySnapshot(
        source_bytes=source_bytes,
        ir_bytes=ir_bytes,
        source_sha256=source_sha256,
        compiler_source_digest=compiler_source_digest,
        ir_sha256=_sha256(ir_bytes),
        compiler_sha256=compiler_sha256,
    )
