"""Capture ontology bytes once and fail closed when compilation disagrees."""

import hashlib
import json
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from ontology_snapshot import OntologySnapshotError, capture_ontology_snapshot  # noqa: E402


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


def test_rejects_tampered_ir_even_when_source_digest_matches(tmp_path):
    source = tmp_path / "source.yaml"
    source.write_text("original")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    saved = tmp_path / "saved-ir.json"
    saved.write_text(json.dumps({"sourceDigest": f"sha256:{digest}", "classes": []}))
    compiler = compiler_fixture(tmp_path / "ontologyc")

    with pytest.raises(OntologySnapshotError, match="saved ontology IR differs"):
        capture_ontology_snapshot(source, compiler, expected_ir_path=saved)
    assert source.read_text() == "original"
    assert json.loads(saved.read_text())["classes"] == []


def test_invalid_source_fails_closed_without_changing_inputs(tmp_path):
    source = tmp_path / "source.yaml"
    source.write_text("invalid")
    compiler = compiler_fixture(tmp_path / "ontologyc")
    with pytest.raises(OntologySnapshotError, match="invalid ontology"):
        capture_ontology_snapshot(source, compiler)
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
    with pytest.raises(OntologySnapshotError, match="compile failed"):
        capture_ontology_snapshot(source, compiler)
    assert source.read_text() == "original"


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
