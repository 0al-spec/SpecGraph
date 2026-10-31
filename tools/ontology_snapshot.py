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

    def __init__(self, message: str, *, outcome: str = "invalid") -> None:
        super().__init__(message)
        if outcome not in {"invalid", "unavailable"}:
            raise ValueError("invalid snapshot error outcome")
        self.outcome = outcome


class OntologySourceRejection(OntologySnapshotError):
    """A coherent compiler rejection of the captured source, without a verified IR."""

    def __init__(
        self,
        diagnostics: tuple[tuple[str, str, str], ...],
        source_sha256: str,
        compiler_sha256: str,
    ):
        super().__init__("ontology compiler rejected the selected source", outcome="unavailable")
        self.diagnostics = diagnostics
        self.source_sha256 = source_sha256
        self.compiler_sha256 = compiler_sha256


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


@dataclass(frozen=True, slots=True)
class CapturedOntologyInputs:
    """Independently captured inputs and read failures for one operation."""

    source_path: Path
    ir_path: Path | None
    source: bytes | None
    ir: bytes | None
    source_error: str | None
    ir_error: str | None


def capture_ontology_inputs(source_path: Path, ir_path: Path | None) -> CapturedOntologyInputs:
    def read(path: Path) -> tuple[bytes | None, str | None]:
        try:
            if not path.is_file():
                return None, f"not an available regular file: {path}"
            return path.read_bytes(), None
        except OSError as error:
            return None, str(error)

    source, source_error = read(source_path)
    ir, ir_error = read(ir_path) if ir_path is not None else (None, None)
    return CapturedOntologyInputs(source_path, ir_path, source, ir, source_error, ir_error)


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


def parse_ontology_ir(data: bytes) -> object:
    return json.loads(
        data.decode("utf-8"),
        object_pairs_hook=_strict_object,
        parse_constant=_reject_constant,
        parse_float=_strict_float,
    )


def _check_response(
    result: subprocess.CompletedProcess[str], source_sha256: str, compiler_sha256: str
) -> None:
    """Accept only the pinned CLI's structured success or rejection contract."""
    if result.returncode not in (0, 1):
        result.check_returncode()
    try:
        rows = parse_ontology_ir(result.stdout.encode())
        if not isinstance(rows, list) or any(
            not isinstance(row, dict)
            or row.get("severity") not in ("error", "warning")
            or not all(isinstance(row.get(k), str) and row[k] for k in ("code", "path", "message"))
            for row in rows
        ):
            raise ValueError("invalid diagnostic array")
        errors = tuple(
            (r["code"], r["path"], r["message"]) for r in rows if r["severity"] == "error"
        )
        if bool(errors) != (result.returncode == 1):
            raise ValueError("exit status and diagnostics disagree")
    except (ValueError, UnicodeError) as error:
        raise OntologySnapshotError(
            "ontology compiler returned unusable check diagnostics", outcome="unavailable"
        ) from error
    if errors:
        raise OntologySourceRejection(errors, source_sha256, compiler_sha256)


def capture_ontology_snapshot(
    source_path: Path,
    ontologyc: Path | None,
    *,
    expected_ir_path: Path | None = None,
    expected_compiler_sha256: str | None = None,
    expected_source_sha256: str | None = None,
    expected_ir_sha256: str | None = None,
    captured_inputs: CapturedOntologyInputs | None = None,
    structured_check: bool = False,
) -> OntologySnapshot:
    """Compile captured source; optionally require an exact saved-IR match.

    A private copy of the selected executable and source ensures their paths
    cannot be replaced between hashing and use. This is not a sandbox: callers
    must trust the chosen compiler and its execution environment.
    """
    inputs = captured_inputs or capture_ontology_inputs(source_path, expected_ir_path)
    if inputs.source_path != source_path or inputs.ir_path != expected_ir_path:
        raise OntologySnapshotError("captured input paths do not match requested paths")
    if expected_ir_sha256 is not None and expected_ir_path is None:
        raise OntologySnapshotError("expected IR hash requires a saved IR path")
    source_bytes, expected_ir = inputs.source, inputs.ir
    if (
        source_bytes is not None
        and expected_source_sha256 is not None
        and (_sha256(source_bytes) != expected_source_sha256)
    ):
        raise OntologySnapshotError("captured source hash does not match selection")
    if (
        expected_ir is not None
        and expected_ir_sha256 is not None
        and (_sha256(expected_ir) != expected_ir_sha256)
    ):
        raise OntologySnapshotError("captured IR hash does not match selection")
    missing_ir = inputs.ir_error or (expected_ir_path is not None and expected_ir is None)
    if source_bytes is None or inputs.source_error or (missing_ir and not structured_check):
        detail = inputs.source_error or inputs.ir_error or "missing input"
        raise OntologySnapshotError(
            f"cannot capture ontology inputs: {detail}", outcome="unavailable"
        )
    try:
        # Foundation's UTF-8 decoder strips a leading BOM before hashing text.
        compiler_source = source_bytes.decode("utf-8-sig").encode("utf-8")
    except UnicodeError as error:
        raise OntologySnapshotError(f"cannot capture ontology inputs: {error}") from error
    source_sha256 = _sha256(source_bytes)
    try:
        if ontologyc is None or not ontologyc.is_file() or not os.access(ontologyc, os.X_OK):
            raise OntologySnapshotError(
                "ontologyc must be an executable file", outcome="unavailable"
            )
        compiler_bytes = ontologyc.read_bytes()
    except OSError as error:
        raise OntologySnapshotError(
            f"cannot capture ontology compiler: {error}", outcome="unavailable"
        ) from error
    compiler_source_digest = f"sha256:{_sha256(compiler_source)}"
    compiler_sha256 = _sha256(compiler_bytes)
    if expected_compiler_sha256 is not None:
        if (
            not isinstance(expected_compiler_sha256, str)
            or len(expected_compiler_sha256) != 64
            or any(c not in "0123456789abcdef" for c in expected_compiler_sha256)
        ):
            raise OntologySnapshotError("expected compiler SHA-256 must be lowercase hex")
        if compiler_sha256 != expected_compiler_sha256:
            raise OntologySnapshotError("compiler hash does not match operator pin")
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

            check_args = ("check", str(staged_source))
            if structured_check:
                check_args += ("--format", "json")
            for arguments in (
                check_args,
                ("compile", str(staged_source), "--target", "typescript", "--out", str(output)),
            ):
                try:
                    result = subprocess.run(
                        [str(executable), *arguments],
                        cwd=work,
                        check=False,
                        capture_output=True,
                        text=True,
                        timeout=60,
                    )
                except UnicodeDecodeError as error:
                    raise OntologySnapshotError(
                        "cannot decode ontology compiler output", outcome="unavailable"
                    ) from error
                if executable.read_bytes() != compiler_bytes:
                    raise OntologySnapshotError("compiler changed captured executable")

                if staged_source.read_bytes() != source_bytes:
                    raise OntologySnapshotError("compiler changed captured ontology source")
                if structured_check and arguments[0] == "check":
                    _check_response(result, source_sha256, compiler_sha256)
                    if missing_ir:
                        raise OntologySnapshotError(
                            f"cannot capture ontology inputs: {inputs.ir_error or 'missing IR'}",
                            outcome="unavailable",
                        )
                result.check_returncode()

            ir_bytes = (output / "ontology.normalized.json").read_bytes()
            ir = parse_ontology_ir(ir_bytes)
            if not isinstance(ir, dict) or ir.get("sourceDigest") != compiler_source_digest:
                raise OntologySnapshotError(
                    "compiler IR source digest does not match captured source"
                )
            if expected_ir is not None and ir_bytes != expected_ir:
                raise OntologySnapshotError("saved ontology IR differs from compiler output")
    except subprocess.CalledProcessError as error:
        detail = error.stderr.strip() if isinstance(error.stderr, str) else ""
        raise OntologySnapshotError(
            f"ontology compiler failed: {detail or error}", outcome="unavailable"
        ) from error
    except (OSError, subprocess.TimeoutExpired) as error:
        raise OntologySnapshotError(
            f"cannot verify ontology snapshot: {error}", outcome="unavailable"
        ) from error
    except (UnicodeError, json.JSONDecodeError) as error:
        raise OntologySnapshotError(f"cannot verify ontology snapshot: {error}") from error

    return OntologySnapshot(
        source_bytes=source_bytes,
        ir_bytes=ir_bytes,
        source_sha256=source_sha256,
        compiler_source_digest=compiler_source_digest,
        ir_sha256=_sha256(ir_bytes),
        compiler_sha256=compiler_sha256,
    )
