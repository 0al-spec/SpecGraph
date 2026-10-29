"""Safety and provenance boundaries for the external compiler smoke."""

import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import ontology_release_smoke as smoke  # noqa: E402
from ontology_imports import CapturedOntologyInputs, build_ontology_import_surfaces  # noqa: E402
from ontology_snapshot import OntologySnapshot  # noqa: E402


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def test_refuses_nonempty_work_dir_without_touching_content(tmp_path):
    work = tmp_path / "existing"
    work.mkdir()
    valuable = work / "receipt.json"
    valuable.write_text("keep this")
    with pytest.raises(ValueError, match="new or empty"):
        smoke.prepare_work_dir(work)
    assert valuable.read_text() == "keep this"


def test_refuses_symlink_work_dir(tmp_path):
    actual = tmp_path / "actual"
    actual.mkdir()
    link = tmp_path / "link"
    link.symlink_to(actual, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        smoke.prepare_work_dir(link)
    assert list(actual.iterdir()) == []


def test_authority_observations_do_not_invent_or_change_status():
    package = {"metadata": {"approvalStatus": "approved"}}
    fixture = {"governance": {"lifecycle_state": "review_pending"}}
    observed = smoke.observe_authority(package, fixture)
    assert observed == {
        "package_approval_status": "approved",
        "fixture_authority_class": None,
        "fixture_lifecycle_state": "review_pending",
    }
    assert package == {"metadata": {"approvalStatus": "approved"}}
    assert fixture == {"governance": {"lifecycle_state": "review_pending"}}


def test_checks_release_revision_and_rejects_tracked_changes(tmp_path, monkeypatch):
    repo = tmp_path / "ontology"
    repo.mkdir()
    git(repo, "init", "-q")
    (repo / "package").write_text("release")
    git(repo, "add", "package")
    git(
        repo,
        "-c",
        "user.name=Smoke Test",
        "-c",
        "user.email=smoke@example.invalid",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "-qm",
        "fixture",
    )
    revision = git(repo, "rev-parse", "HEAD")
    with pytest.raises(ValueError, match="ontology source must be at"):
        smoke.check_ontology_source(repo)
    monkeypatch.setattr(smoke, "ONTOLOGY_REVISION", revision)
    assert smoke.check_ontology_source(repo) == revision
    (repo / "package").write_text("changed")
    with pytest.raises(ValueError, match="tracked changes"):
        smoke.check_ontology_source(repo)


def test_wrong_release_does_not_create_work_dir(tmp_path):
    repo = tmp_path / "ontology"
    repo.mkdir()
    git(repo, "init", "-q")
    (repo / "package").write_text("other")
    git(repo, "add", "package")
    git(
        repo,
        "-c",
        "user.name=Smoke Test",
        "-c",
        "user.email=smoke@example.invalid",
        "-c",
        "commit.gpgsign=false",
        "commit",
        "-qm",
        "fixture",
    )
    work = tmp_path / "output"
    with pytest.raises(ValueError, match="ontology source must be at"):
        smoke.smoke(Path(sys.executable), repo, work)
    assert not work.exists()


def test_smoke_uses_snapshot_bytes_after_source_changes(tmp_path, monkeypatch):
    package = tmp_path / "package"
    package.mkdir()
    source = package / "domain-ontology-package.yaml"
    original = b"metadata:\n  approvalStatus: draft\n"
    source.write_bytes(original)
    (package / "import-fixture.yaml").write_text(
        yaml.safe_dump({"package": {"source_uri": "example:source", "source_ref": "example:ref"}})
    )
    compiler = tmp_path / "ontologyc"
    compiler.write_bytes(b"original compiler")
    compiler_hash = hashlib.sha256(compiler.read_bytes()).hexdigest()
    expected_ir = package / "generated/ontology.normalized.json"
    ir = b'{"fixture":"verified IR"}'
    calls = []
    monkeypatch.setattr(smoke, "PACKAGE_ROOT", package)
    monkeypatch.setattr(smoke, "check_ontology_source", lambda _source: "revision")

    def capture(source_path, compiler_path, *, expected_ir_path):
        calls.append((source_path, compiler_path, expected_ir_path))
        source.write_text("metadata:\n  approvalStatus: changed\n")
        return OntologySnapshot(
            source_bytes=original,
            ir_bytes=ir,
            source_sha256=hashlib.sha256(original).hexdigest(),
            compiler_source_digest="sha256:source",
            ir_sha256=hashlib.sha256(ir).hexdigest(),
            compiler_sha256=compiler_hash,
        )

    def validate(command, **kwargs):
        work = kwargs["cwd"]
        assert command[1] == "validate-specgraph"
        assert (work / "ontology.yaml").read_bytes() == original
        assert (work / "ontology.normalized.json").read_bytes() == ir
        assert (work / "ontologyc").read_bytes() == b"original compiler"
        (work / "ontology-gaps.yaml").write_text("spec:\n  gaps: []\n")

    monkeypatch.setattr(smoke, "capture_ontology_snapshot", capture)
    monkeypatch.setattr(smoke.subprocess, "run", validate)
    monkeypatch.setattr(
        smoke,
        "build_ontology_import_surfaces",
        lambda *_args, **_kwargs: {
            "adapter_report_smoke": {
                "canonical_mutations_allowed": False,
                "tracked_artifacts_written": False,
                "checks": [],
                "summary": {"status": "passed", "resolved_ref_count": 0, "gap_count": 0},
            },
            "binding_preview": {"unresolved_refs": []},
        },
    )
    work = tmp_path / "work"
    receipt = smoke.smoke(compiler, tmp_path, work)
    assert calls == [(source, compiler, expected_ir)]
    assert receipt["package_approval_status"] == "draft"
    assert receipt["ontologyc_source_provenance"] == "not_verified"
    assert receipt["normalized_ir_matches_project_file"] is True
    assert receipt == json.loads((work / "receipt.json").read_text())


def test_smoke_rejects_compiler_replaced_after_snapshot(tmp_path, monkeypatch):
    source = tmp_path / "domain-ontology-package.yaml"
    source.write_bytes(b"metadata: {}")
    (tmp_path / "import-fixture.yaml").write_text("package: {}")
    compiler = tmp_path / "ontologyc"
    compiler.write_bytes(b"original")
    original_hash = hashlib.sha256(compiler.read_bytes()).hexdigest()
    monkeypatch.setattr(smoke, "PACKAGE_ROOT", tmp_path)
    monkeypatch.setattr(smoke, "check_ontology_source", lambda _source: "revision")

    def capture(*_args, **_kwargs):
        compiler.write_bytes(b"replacement")
        return OntologySnapshot(b"metadata: {}", b"{}", "", "", "", original_hash)

    monkeypatch.setattr(smoke, "capture_ontology_snapshot", capture)
    with pytest.raises(ValueError, match="compiler changed after snapshot"):
        smoke.smoke(compiler, tmp_path, tmp_path / "output")


@pytest.mark.parametrize("target", ["fixture", "ir"])
def test_smoke_refuses_receipt_if_report_input_drifts_during_adapter(tmp_path, monkeypatch, target):
    package = tmp_path / "package"
    package.mkdir()
    source_bytes = b"metadata:\n  approvalStatus: draft\n"
    (package / "domain-ontology-package.yaml").write_bytes(source_bytes)
    (package / "import-fixture.yaml").write_text(
        yaml.safe_dump({"package": {"source_uri": "example:source", "source_ref": "example:ref"}})
    )
    compiler = tmp_path / "ontologyc"
    compiler.write_bytes(b"compiler")
    ir = b'{"captured":"ir"}'
    snapshot = OntologySnapshot(
        source_bytes, ir, "source", "digest", "ir", hashlib.sha256(b"compiler").hexdigest()
    )
    monkeypatch.setattr(smoke, "PACKAGE_ROOT", package)
    monkeypatch.setattr(smoke, "check_ontology_source", lambda _source: "revision")
    monkeypatch.setattr(smoke, "capture_ontology_snapshot", lambda *_a, **_k: snapshot)
    monkeypatch.setattr(smoke.subprocess, "run", lambda *_a, **_k: None)
    work = tmp_path / "output"

    def replace_during_adapter(fixture_path, **kwargs):
        inputs = kwargs["captured_inputs"]
        assert inputs.ir_bytes == ir
        assert yaml.safe_load(inputs.fixture_bytes)["package"]["source_uri"] == "example:source"
        path = (
            fixture_path
            if target == "fixture"
            else fixture_path.parent / "ontology.normalized.json"
        )
        path.write_bytes(b"changed")
        return {
            "adapter_report_smoke": {
                "canonical_mutations_allowed": False,
                "tracked_artifacts_written": False,
                "checks": [],
                "summary": {"status": "passed", "resolved_ref_count": 0, "gap_count": 0},
            },
            "binding_preview": {"unresolved_refs": []},
        }

    monkeypatch.setattr(smoke, "build_ontology_import_surfaces", replace_during_adapter)
    with pytest.raises(ValueError, match="inputs drifted"):
        smoke.smoke(compiler, tmp_path, work)
    assert not (work / "receipt.json").exists()


def test_adapter_evaluates_captured_inputs_after_files_are_replaced(tmp_path):
    source = Path(__file__).resolve().parents[1] / "tests/fixtures/ontology_import/specgraph-core"
    fixture_root = tmp_path / "fixture"
    shutil.copytree(source, fixture_root)
    fixture_path = fixture_root / "import-fixture.yaml"
    ir_path = fixture_root / "ontology.normalized.json"
    report_path = fixture_root / "ontologyc-adapter-report.yaml"
    inputs = CapturedOntologyInputs(fixture_path.read_bytes(), ir_path.read_bytes())

    changed_fixture = yaml.safe_load(inputs.fixture_bytes)
    changed_fixture["binding"]["refs"] = []
    fixture_path.write_text(yaml.safe_dump(changed_fixture))
    changed_ir = json.loads(inputs.ir_bytes)
    changed_ir["classes"] = []
    ir_path.write_text(json.dumps(changed_ir))

    captured = build_ontology_import_surfaces(
        fixture_path,
        adapter_report_path=report_path,
        semantic_policy_path=None,
        captured_inputs=inputs,
    )
    summary = captured["adapter_report_smoke"]["summary"]
    assert summary["resolved_ref_count"] == 7
    assert summary["gap_count"] == 1
    assert captured["binding_preview"]["unresolved_refs"] == ["sgcore:ClaimCalibration"]

    # Legacy path-based evaluation still sees the replacement and must reject
    # the old compiler report instead of presenting it as a matching result.
    with pytest.raises(ValueError):
        build_ontology_import_surfaces(
            fixture_path, adapter_report_path=report_path, semantic_policy_path=None
        )


def test_captured_ontology_inputs_reject_mutable_bytes():
    with pytest.raises(TypeError, match="immutable bytes"):
        CapturedOntologyInputs(bytearray(b"fixture"), b"ir")
