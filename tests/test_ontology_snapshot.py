"""Capture ontology bytes once and fail closed when compilation disagrees."""

import hashlib
import json
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from ontology_snapshot import (  # noqa: E402
    OntologySnapshotError,
    OntologySourceRejection,
    capture_ontology_inputs,
    capture_ontology_snapshot,
)


def compiler_fixture(path: Path, *, during_check: str = "") -> Path:
    path.write_text(
        "#!/usr/bin/env python3\n"
        "import hashlib, json, pathlib, sys\n"
        "source = pathlib.Path(sys.argv[2]).read_bytes()\n"
        "if source == b'invalid':\n"
        "    print('invalid ontology', file=sys.stderr)\n"
        "    raise SystemExit(1)\n"
        "if sys.argv[1] == 'check':\n"
        f"    {during_check or 'pass'}\n"
        "elif sys.argv[1] == 'compile':\n"
        "    out = pathlib.Path(sys.argv[sys.argv.index('--out') + 1])\n"
        "    out.mkdir()\n"
        "    text = source.decode('utf-8-sig').encode('utf-8')\n"
        "    ir = {'sourceDigest': 'sha256:' + hashlib.sha256(text).hexdigest(),"
        " 'classes': [{'id': 'Original'}]}\n"
        "    (out / 'ontology.normalized.json').write_text(json.dumps(ir, sort_keys=True))\n"
        "else:\n"
        "    raise SystemExit(2)\n"
    )
    path.chmod(0o700)
    return path


def test_snapshot_uses_captured_source_and_saved_ir_when_paths_change(tmp_path):
    source = tmp_path / "source.yaml"
    source.write_text("original")
    digest = hashlib.sha256(b"original").hexdigest()
    ir_bytes = json.dumps(
        {"sourceDigest": f"sha256:{digest}", "classes": [{"id": "Original"}]}, sort_keys=True
    ).encode()
    expected = tmp_path / "saved-ir.json"
    expected.write_bytes(ir_bytes)
    compiler_path = tmp_path / "ontologyc"
    compiler = compiler_fixture(
        compiler_path,
        during_check=(
            f"pathlib.Path({str(source)!r}).write_text('new source'); "
            f"pathlib.Path({str(expected)!r}).write_text('new IR'); "
            f"pathlib.Path({str(compiler_path)!r}).write_text('new compiler')"
        ),
    )
    compiler_sha256 = hashlib.sha256(compiler.read_bytes()).hexdigest()

    snapshot = capture_ontology_snapshot(source, compiler, expected_ir_path=expected)

    assert snapshot.source_bytes == b"original" and snapshot.ir_bytes == ir_bytes
    assert source.read_text() == "new source" and expected.read_text() == "new IR"
    assert compiler.read_text() == "new compiler"
    assert snapshot.source_sha256 == digest
    assert snapshot.compiler_source_digest == f"sha256:{digest}"
    assert snapshot.ir_sha256 == hashlib.sha256(ir_bytes).hexdigest()
    assert snapshot.compiler_sha256 == compiler_sha256
    assert snapshot.compiler_provenance == "not_verified"
    with pytest.raises(FrozenInstanceError):
        snapshot.ir_bytes = b"changed"


def test_pre_captured_inputs_are_reused_and_bound_to_paths(tmp_path):
    source = tmp_path / "source.yaml"
    source.write_text("original")
    compiler = compiler_fixture(tmp_path / "ontologyc")
    inputs = capture_ontology_inputs(source, None)
    source.write_text("changed")
    snapshot = capture_ontology_snapshot(source, compiler, captured_inputs=inputs)
    assert snapshot.source_bytes == b"original"
    with pytest.raises(OntologySnapshotError, match="paths do not match") as error:
        capture_ontology_snapshot(tmp_path / "other.yaml", compiler, captured_inputs=inputs)
    assert error.value.outcome == "invalid"


def test_rejects_tampered_ir_even_when_source_digest_matches(tmp_path):
    source = tmp_path / "source.yaml"
    source.write_text("original")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    saved = tmp_path / "saved-ir.json"
    saved.write_text(json.dumps({"sourceDigest": f"sha256:{digest}", "classes": []}))
    compiler = compiler_fixture(tmp_path / "ontologyc")

    with pytest.raises(OntologySnapshotError, match="saved ontology IR differs") as error:
        capture_ontology_snapshot(source, compiler, expected_ir_path=saved)
    assert error.value.outcome == "invalid"
    assert source.read_text() == "original"
    assert json.loads(saved.read_text())["classes"] == []


def test_invalid_source_fails_closed_without_changing_inputs(tmp_path):
    source = tmp_path / "source.yaml"
    source.write_text("invalid")
    compiler = compiler_fixture(tmp_path / "ontologyc")
    with pytest.raises(OntologySnapshotError, match="invalid ontology") as error:
        capture_ontology_snapshot(source, compiler)
    # The diagnostic text and nonzero exit do not prove why the compiler failed.
    assert error.value.outcome == "unavailable"
    assert source.read_text() == "invalid"


def test_compile_failure_after_successful_check_fails_closed(tmp_path):
    source = tmp_path / "source.yaml"
    source.write_text("original")
    compiler = tmp_path / "ontologyc"
    compiler.write_text(
        "#!/usr/bin/env python3\n"
        "import sys\n"
        "if sys.argv[1] == 'compile':\n"
        "    print('compile failed', file=sys.stderr)\n"
        "    raise SystemExit(1)\n"
    )
    compiler.chmod(0o700)
    with pytest.raises(OntologySnapshotError, match="compile failed") as error:
        capture_ontology_snapshot(source, compiler)
    assert error.value.outcome == "unavailable"
    assert source.read_text() == "original"


@pytest.mark.parametrize("failure", ["check", "signal", "undecodable"])
def test_ambiguous_compiler_failures_are_unavailable(tmp_path, failure):
    source = tmp_path / "source.yaml"
    source.write_text("original")
    compiler = tmp_path / "ontologyc"
    action = {
        "check": "raise SystemExit(1)",
        "signal": "os.kill(os.getpid(), signal.SIGTERM)",
        "undecodable": "os.write(2, bytes([255])); raise SystemExit(1)",
    }[failure]
    compiler.write_text(
        "#!/usr/bin/env python3\n"
        "import os, signal, sys\n"
        "if sys.argv[1] == 'check':\n"
        f"    {action}\n"
    )
    compiler.chmod(0o700)
    with pytest.raises(OntologySnapshotError) as error:
        capture_ontology_snapshot(source, compiler)
    assert error.value.outcome == "unavailable"


def test_missing_compiler_and_source_fail_closed(tmp_path):
    source = tmp_path / "source.yaml"
    source.write_text("original")
    with pytest.raises(OntologySnapshotError, match="executable file"):
        capture_ontology_snapshot(source, tmp_path / "missing")
    with pytest.raises(OntologySnapshotError, match="cannot capture ontology inputs"):
        capture_ontology_snapshot(tmp_path / "missing", compiler_fixture(tmp_path / "ontologyc"))


def test_rejects_compiler_output_with_incorrect_digest(tmp_path):
    source = tmp_path / "source.yaml"
    source.write_text("original")
    compiler = tmp_path / "ontologyc"
    compiler.write_text(
        "#!/usr/bin/env python3\n"
        "import pathlib, sys\n"
        "if sys.argv[1] == 'compile':\n"
        "    out = pathlib.Path(sys.argv[sys.argv.index('--out') + 1])\n"
        "    out.mkdir()\n"
        "    (out / 'ontology.normalized.json').write_text(\n"
        '        \'{"sourceDigest": "sha256:wrong"}\')\n'
    )
    compiler.chmod(0o700)
    with pytest.raises(OntologySnapshotError, match="source digest"):
        capture_ontology_snapshot(source, compiler)


def test_utf8_bom_and_non_ascii_preserve_raw_and_compiler_hashes(tmp_path):
    source_bytes = b"\xef\xbb\xbf" + "имя: значение\r\n".encode()
    source = tmp_path / "source.yaml"
    source.write_bytes(source_bytes)
    compiler = compiler_fixture(tmp_path / "ontologyc")

    snapshot = capture_ontology_snapshot(source, compiler)

    assert snapshot.source_bytes == source_bytes
    assert snapshot.source_sha256 == hashlib.sha256(source_bytes).hexdigest()
    expected = hashlib.sha256(source_bytes[3:]).hexdigest()
    assert snapshot.compiler_source_digest == f"sha256:{expected}"
    assert json.loads(snapshot.ir_bytes)["sourceDigest"] == snapshot.compiler_source_digest


@pytest.mark.parametrize(
    ("output", "message"),
    [
        ('{"sourceDigest": "a", "sourceDigest": "b"}', "duplicate key"),
        ('{"nested": {"id": 1, "id": 2}}', "duplicate key"),
        ('{"invalid": NaN}', "non-finite value"),
        ('{"invalid": Infinity}', "non-finite value"),
        ('{"invalid": -Infinity}', "non-finite value"),
        ('{"invalid": 1e400}', "non-finite value"),
    ],
)
def test_invalid_json_values_and_duplicate_keys_fail_closed(tmp_path, output, message):
    source = tmp_path / "source.yaml"
    source.write_text("original")
    compiler = tmp_path / "ontologyc"
    compiler.write_text(
        "#!/usr/bin/env python3\n"
        "import pathlib, sys\n"
        "if sys.argv[1] == 'compile':\n"
        "    out = pathlib.Path(sys.argv[sys.argv.index('--out') + 1])\n"
        "    out.mkdir()\n"
        f"    (out / 'ontology.normalized.json').write_text({output!r})\n"
    )
    compiler.chmod(0o700)
    with pytest.raises(OntologySnapshotError, match=message):
        capture_ontology_snapshot(source, compiler)


def test_compiler_pin_is_checked_before_execution(tmp_path):
    source = tmp_path / "source.yaml"
    source.write_text("original")
    marker = tmp_path / "executed"
    compiler = compiler_fixture(
        tmp_path / "ontologyc", during_check=f"pathlib.Path({str(marker)!r}).touch()"
    )
    with pytest.raises(OntologySnapshotError, match="compiler hash") as error:
        capture_ontology_snapshot(source, compiler, expected_compiler_sha256="0" * 64)
    assert error.value.outcome == "invalid"
    assert not marker.exists()


@pytest.mark.parametrize("mismatch", ["source", "ir"])
def test_input_hash_mismatch_is_invalid_before_compiler_execution(tmp_path, mismatch):
    source = tmp_path / "source.yaml"
    source.write_text("original")
    saved_ir = tmp_path / "saved.json"
    saved_ir.write_text("saved")
    marker = tmp_path / "executed"
    compiler = compiler_fixture(
        tmp_path / "ontologyc", during_check=f"pathlib.Path({str(marker)!r}).touch()"
    )
    with pytest.raises(OntologySnapshotError, match="hash does not match") as error:
        capture_ontology_snapshot(
            source,
            compiler,
            expected_ir_path=saved_ir,
            expected_source_sha256="0" * 64 if mismatch == "source" else None,
            expected_ir_sha256="0" * 64 if mismatch == "ir" else None,
        )
    assert error.value.outcome == "invalid"
    assert not marker.exists()


def test_snapshot_error_classifies_io_timeout_and_malformed_ir(tmp_path, monkeypatch):
    import subprocess

    compiler = compiler_fixture(tmp_path / "ontologyc")
    source = tmp_path / "source.yaml"
    with pytest.raises(OntologySnapshotError) as unavailable:
        capture_ontology_snapshot(source, compiler)
    assert unavailable.value.outcome == "unavailable"
    source.write_text("original")

    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], 60)

    monkeypatch.setattr(subprocess, "run", timeout)
    with pytest.raises(OntologySnapshotError) as unavailable:
        capture_ontology_snapshot(source, compiler)
    assert unavailable.value.outcome == "unavailable"
    monkeypatch.undo()
    compiler.write_text(
        "#!/usr/bin/env python3\n"
        "import pathlib,sys\n"
        "if sys.argv[1] == 'compile':\n"
        " out=pathlib.Path(sys.argv[sys.argv.index('--out')+1]); out.mkdir()\n"
        " (out/'ontology.normalized.json').write_text('{invalid')\n"
    )
    with pytest.raises(OntologySnapshotError) as invalid:
        capture_ontology_snapshot(source, compiler)
    assert invalid.value.outcome == "invalid"


@pytest.mark.parametrize(
    ("status", "payload"),
    [
        (1, "not JSON"),
        (1, "[]"),
        (0, '[{"severity":"error","code":"ref","path":"a","message":"bad"}]'),
        (1, '[{"severity":"error","code":"ref"}]'),
        (2, "[]"),
    ],
)
def test_incoherent_structured_check_cannot_invalidate_a_reference(tmp_path, status, payload):
    source = tmp_path / "package.yaml"
    source.write_text("source")
    compiler = compiler_fixture(
        tmp_path / "ontologyc", during_check=f"print({payload!r}); sys.exit({status})"
    )
    with pytest.raises(OntologySnapshotError) as caught:
        capture_ontology_snapshot(source, compiler, structured_check=True)
    assert caught.value.outcome == "unavailable" and not isinstance(
        caught.value, OntologySourceRejection
    )
