"""Characterize the JSON facades before sharing their I/O mechanics."""

from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONSUMERS = (
    "publication_delivery_evidence",
    "active_idea_to_spec_candidate_source",
    "idea_intake_clarification_rerun",
)


@pytest.fixture(params=CONSUMERS)
def consumer(request, monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "tools"))
    return importlib.import_module(request.param)


def write_through(consumer, path, payload):
    if consumer.__name__ == "publication_delivery_evidence":
        return consumer.write_json(path, payload)
    return consumer.write_json(payload, path)


def test_read_object_preserves_nested_values_and_unicode(consumer, tmp_path):
    path = tmp_path / "input.json"
    path.write_text('{"name": "намерение", "values": [1, null, false]}', encoding="utf-8")
    assert consumer.load_json(path) == {"name": "намерение", "values": [1, None, False]}


@pytest.mark.parametrize("text", ["[]", "null", '"text"', "1"])
def test_read_non_object_preserves_error_message(consumer, tmp_path, text):
    path = tmp_path / "input.json"
    path.write_text(text, encoding="utf-8")
    expected = (
        f"expected JSON object: {path}"
        if consumer.__name__ == "publication_delivery_evidence"
        else f"{path} must contain a JSON object"
    )
    with pytest.raises(ValueError) as error:
        consumer.load_json(path)
    assert type(error.value) is ValueError
    assert str(error.value) == expected


@pytest.mark.parametrize(
    "content,exception",
    [(b"{broken", json.JSONDecodeError), (b'"\xff"', UnicodeDecodeError)],
)
def test_read_preserves_decode_failures(consumer, tmp_path, content, exception):
    path = tmp_path / "input.json"
    path.write_bytes(content)
    with pytest.raises(exception):
        consumer.load_json(path)


def test_read_preserves_missing_file_failure(consumer, tmp_path):
    with pytest.raises(FileNotFoundError):
        consumer.load_json(tmp_path / "missing.json")


def test_write_preserves_exact_bytes_and_argument_order(consumer, tmp_path, capsys):
    path = tmp_path / "nested" / "report.json"
    payload = {"z": "я", "a": {"ok": True}}
    assert write_through(consumer, path, payload) is None
    assert path.read_bytes() == b'{\n  "a": {\n    "ok": true\n  },\n  "z": "\\u044f"\n}\n'
    path.write_text("previous report", encoding="utf-8")
    write_through(consumer, path, payload)
    assert json.loads(path.read_text(encoding="utf-8")) == payload
    assert capsys.readouterr().out == ""


def test_write_serialization_failure_preserves_previous_report(consumer, tmp_path):
    path = tmp_path / "report.json"
    path.write_text("previous report", encoding="utf-8")
    with pytest.raises(TypeError):
        write_through(consumer, path, {"unsupported": object()})
    assert path.read_text(encoding="utf-8") == "previous report"


def test_write_preserves_filesystem_failure(consumer, tmp_path):
    parent = tmp_path / "file"
    parent.write_text("not a directory", encoding="utf-8")
    with pytest.raises(FileExistsError):
        write_through(consumer, parent / "report.json", {})


def test_http_report_preserves_json_bytes_and_stdout(tmp_path, monkeypatch, capsys):
    monkeypatch.syspath_prepend(str(ROOT / "tools"))
    verifier = importlib.import_module("static_artifact_incremental_stage")
    output = tmp_path / "nested" / "report.json"
    report = {"status": "verified", "summary": {"verified_file_count": 2}, "label": "я"}
    assert verifier._write_report(report, output) is None
    assert output.read_bytes() == (
        b'{\n  "label": "\\u044f",\n  "status": "verified",\n'
        b'  "summary": {\n    "verified_file_count": 2\n  }\n}\n'
    )
    assert (
        capsys.readouterr().out
        == json.dumps(
            {"status": "verified", "summary": report["summary"], "output": str(output)},
            sort_keys=True,
        )
        + "\n"
    )


@pytest.mark.parametrize(
    "name", ["active_idea_to_spec_candidate_source", "static_artifact_incremental_stage"]
)
def test_standalone_file_import_preserves_python_path(name, tmp_path):
    script = """
import importlib.util
import sys
before = list(sys.path)
spec = importlib.util.spec_from_file_location("isolated_json_consumer", sys.argv[1])
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
assert callable(module.main)
assert sys.path == before
"""
    completed = subprocess.run(
        [sys.executable, "-I", "-S", "-B", "-c", script, str(ROOT / "tools" / f"{name}.py")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
