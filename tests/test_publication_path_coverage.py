"""Replay the root verifier and audit only its retained files in a separate process."""

import hashlib
import io
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

from test_static_artifact_incremental_stage import MODULE, _bundle

AUDIT = Path(__file__).resolve().parents[1] / "tools/publication_path_coverage.py"


@pytest.fixture
def capture(tmp_path, monkeypatch):
    bundle = _bundle(tmp_path / "bundle", {"first.txt": b"same", "second.txt": b"same"})
    receipt, witness = tmp_path / "verification.json", tmp_path / "observations.json"
    failures = []

    def fetch(url, timeout):
        name = url.rsplit("/", 1)[1]
        if name == "second.txt" and failures:
            raise failures.pop()
        return io.BytesIO((bundle / name).read_bytes())

    monkeypatch.setattr(MODULE.urllib.request, "urlopen", fetch)
    args = [
        "verify",
        "--bundle-dir",
        str(bundle),
        "--remote-base-url",
        "https://publication.example",
        "--output",
        str(receipt),
        "--attempts",
        "2",
        "--retry-delay-seconds",
        "0",
    ]
    return bundle, receipt, witness, args, failures


def _audit(bundle, receipt, witness, *options):
    return subprocess.run(
        [
            sys.executable,
            AUDIT,
            "--bundle-dir",
            bundle,
            "--receipt",
            receipt,
            "--observations",
            witness,
            *options,
        ],
        capture_output=True,
        text=True,
    )


def test_capture_binds_only_the_successful_attempt(capture):
    bundle, receipt, witness, args, failures = capture
    failures.append(TimeoutError("first attempt unavailable"))
    assert MODULE.main([*args, "--observations-output", str(witness)]) == 0
    raw = witness.read_bytes()
    records, report = json.loads(raw), json.loads(receipt.read_bytes())
    assert report["path_observations_sha256"] == hashlib.sha256(raw).hexdigest()
    assert report["attempt"] == records["attempt"] == 2
    assert records["execution_context"] == report["execution_context"]
    assert records["observations"] == [
        {"path": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
        for p in sorted(bundle.iterdir())
    ]
    # The offline auditor only needs the retained manifest and checksums.
    (bundle / "first.txt").unlink()
    (bundle / "second.txt").unlink()
    audit = _audit(bundle, receipt, witness)
    assert audit.returncode == 0
    assert json.loads(audit.stdout)["status"] == "verified"


@pytest.mark.parametrize(
    "mutation", ["delete", "repeat-other", "wrong-digest", "other-run", "other-manifest"]
)
def test_audit_rejects_missing_or_misbound_evidence(capture, mutation):
    bundle, receipt, witness, args, _ = capture
    assert MODULE.main([*args, "--observations-output", str(witness)]) == 0
    record = json.loads(witness.read_bytes())
    rows = record["observations"]
    second = next(row for row in rows if row["path"] == "second.txt")
    if mutation == "delete":
        rows.remove(second)
    elif mutation == "repeat-other":
        second["path"] = "first.txt"
    elif mutation == "wrong-digest":
        second["sha256"] = "0" * 64
    elif mutation == "other-run":
        record["execution_context"]["run_attempt"] = "another"
    else:
        manifest = bundle / "artifact_manifest.json"
        manifest.write_bytes(manifest.read_bytes() + b" ")
    if mutation != "other-manifest":
        witness.write_text(json.dumps(record))
    audit = _audit(bundle, receipt, witness)
    assert audit.returncode == 1
    result = json.loads(audit.stdout)
    assert result["status"] == "unverified"
    if mutation in ("delete", "repeat-other", "wrong-digest"):
        assert result["missing_path_digest_pairs"] == ["second.txt"]
    if mutation == "repeat-other":
        assert result["observed_records"] == 4
        assert result["unexpected_path_digest_pairs"] == ["first.txt"]
    if mutation == "other-run":
        assert any("execution" in error for error in result["errors"])
    if mutation == "other-manifest":
        assert any("metadata" in error for error in result["errors"])


def test_failed_or_disabled_capture(capture):
    _, receipt, witness, args, failures = capture
    failures.extend([TimeoutError(), TimeoutError()])
    assert MODULE.main([*args, "--observations-output", str(witness)]) == 2
    assert not receipt.exists() and not witness.exists()
    assert MODULE.main(args) == 0
    assert "path_observations_sha256" not in json.loads(receipt.read_bytes())
    assert not witness.exists()
    assert MODULE.main([*args, "--observations-output", str(witness)]) == 2
    assert not witness.exists()


def test_receipt_with_same_count_but_duplicate_work(capture, monkeypatch):
    bundle, receipt, witness, args, _ = capture

    class RepeatingPool(ThreadPoolExecutor):
        def map(self, verify, entries):
            first, second = entries
            assert (first[0], second[0]) == ("first.txt", "second.txt")
            return super().map(verify, [first, first])

    monkeypatch.setattr(MODULE, "ThreadPoolExecutor", RepeatingPool)
    assert MODULE.main([*args, "--observations-output", str(witness)]) == 0
    assert json.loads(receipt.read_bytes())["summary"]["verified_file_count"] == 2
    audit = _audit(bundle, receipt, witness)
    assert audit.returncode == 1
    result = json.loads(audit.stdout)
    assert result["missing_path_digest_pairs"] == ["second.txt"]
    assert result["unexpected_path_digest_pairs"] == ["first.txt"]
    assert result["errors"] == []


def test_independent_run_binding(capture, monkeypatch):
    bundle, receipt, witness, args, _ = capture
    monkeypatch.setenv("GITHUB_RUN_ID", "1123")
    assert MODULE.main([*args, "--observations-output", str(witness)]) == 0
    assert _audit(bundle, receipt, witness, "--run-id", "1123").returncode == 0
    wrong = _audit(bundle, receipt, witness, "--run-id", "1124")
    assert wrong.returncode == 1
    assert "requested GitHub run" in wrong.stdout
