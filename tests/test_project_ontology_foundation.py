"""Foundation closure controls with the normal public context CLI."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
MEMBER = ROOT / "specs/models/SG-SPEC-0072/foundation-member.yaml"
CORE = ROOT / "ontology/packages/specgraph-core/domain-ontology-package.yaml"
sys.path.insert(0, str(ROOT / "tools"))
from ontology_snapshot import OntologySourceRejection  # noqa: E402
from project_ontology_context import foundation  # noqa: E402


def sha(data):
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def compiler():
    if not (binary := os.environ.get("ONTOLOGYC_BINARY_PATH")):
        pytest.skip("set ONTOLOGYC_BINARY_PATH to exercise the real package compiler")
    return Path(binary).resolve(strict=True)


def capture(work, compiler, source, *, prior_ir=None, keep_prior=False):
    work.mkdir()
    package = work / "member.yaml"
    package.write_bytes(source)
    ir = work / "ir/ontology.normalized.json"
    if prior_ir is None:
        subprocess.run(
            [compiler, "compile", package, "--target", "typescript", "--out", ir.parent],
            check=True,
            capture_output=True,
            timeout=60,
        )
        ir_hash = sha(ir.read_bytes())
    else:
        # Keep the last real IR pin from the selection; a rejected edit produces no new IR.
        ir_hash = sha(prior_ir)
        if keep_prior:
            ir.parent.mkdir()
            ir.write_bytes(prior_ir)
        else:
            assert not ir.exists()
    meta = yaml.safe_load(source)["metadata"]
    selection = {
        "artifact_kind": "specgraph_project_ontology_selection",
        "schema_version": 1,
        "packages": [
            {
                **{k: meta[k] for k in ("id", "version", "namespace")},
                "source": "member.yaml",
                "source_sha256": sha(source),
                "ir": "ir/ontology.normalized.json",
                "ir_sha256": ir_hash,
            }
        ],
        "profiles": [foundation.PROFILE],
        "composition": {"dependency_rule": "explicit", "name_resolution_rule": "qualified"},
    }
    (work / "selection.yaml").write_text(yaml.safe_dump(selection))
    proc = subprocess.run(
        [
            sys.executable,
            "-B",
            ROOT / "tools/project_ontology_context_cli.py",
            "--workspace-root",
            work,
            "--project-id",
            "foundation-probe",
            "--selection",
            "selection.yaml",
            "--ontologyc",
            compiler,
            "--compiler-sha256",
            sha(compiler.read_bytes()),
            "--output",
            "report.json",
        ],
        capture_output=True,
        text=True,
        timeout=180,
    )
    report = json.loads(proc.stdout)
    assert json.loads((work / "report.json").read_bytes()) == report
    return proc.returncode, report


@pytest.mark.parametrize("keep_prior", [False, True], ids=["no-ir", "stale-ir"])
def test_same_pinned_foundation_resolves_valueobject_and_rejects_typo(
    compiler, tmp_path, keep_prior
):
    source = MEMBER.read_bytes()
    good_code, good = capture(tmp_path / "valid", compiler, source)
    bad_code, bad = capture(
        tmp_path / "typo",
        compiler,
        source.replace(b"sg:ValueObject", b"sg:Typo"),
        prior_ir=(tmp_path / "valid/ir/ontology.normalized.json").read_bytes(),
        keep_prior=keep_prior,
    )
    assert (good_code, good["outcome"]) == (0, "verified")
    assert (bad_code, bad["outcome"]) == (2, "invalid")
    assert good["context_revision"] and bad["context_revision"] is None
    assert good["resolved_imports"][0]["source_sha256"] == sha(foundation.EXPORTS.read_bytes())
    assert good["snapshots"] and not bad["snapshots"] and not bad.get("resolved_imports")
    assert (tmp_path / "typo/ir/ontology.normalized.json").exists() is keep_prior
    assert any(
        c["check"] == "member_capture" and c["outcome"] == "verified" for c in good["checks"]
    )
    assert not any(
        c["check"] == "member_capture" and c["outcome"] == "verified" for c in bad["checks"]
    )
    [error] = [c for c in bad["checks"] if c.get("compiler_diagnostic")]
    assert error["compiler_diagnostic"] == {
        "code": "class.extends.unresolved",
        "source_sha256": sha(source.replace(b"sg:ValueObject", b"sg:Typo")),
        "compiler_sha256": sha(compiler.read_bytes()),
    }
    for report, name, uri in (
        (good, "sg:ValueObject", "ontology://specgraph.foundation/0.1.0/classes/ValueObject"),
        (bad, "sg:Typo", None),
    ):
        [resolution] = [c for c in report["checks"] if c["check"] == "name_resolution"]
        assert resolution["outcome"] == report["outcome"]
        assert resolution["reference"] == {
            "pointer": "/spec/classes/Entry/extends",
            "name": name,
            "uri": uri,
        }


def test_real_project_core_resolves_its_foundation_import(compiler, tmp_path):
    code, report = capture(tmp_path / "core", compiler, CORE.read_bytes())
    assert (code, report["outcome"]) == (0, "verified"), report["checks"]
    assert any("sg:Policy ->" in c["detail"] for c in report["checks"])


def member_spec():
    doc = yaml.safe_load(MEMBER.read_bytes())
    return doc["spec"], doc["metadata"]


def test_resolution_checks_structural_slots_and_their_roles():
    spec, member = member_spec()
    entry = spec["classes"]["Entry"]
    entry.update(description="Unrelated prose can mention sg:Typo", implements=["sg:Auditable"])
    spec["relations"]["follows"]["range"] = {"oneOf": ["Entry", "sg:Typo"]}
    spec["policies"] = {"Review": {"extends": "sg:Approvable", "appliesTo": ["sg:Typo"]}}
    checks, _ = foundation.check_import(spec, member, 1)
    assert [
        c.detail.split(": ")[0]
        for c in checks
        if c.check == "name_resolution" and c.outcome == "invalid"
    ] == [
        "/spec/relations/follows/range/oneOf/1",
        "/spec/policies/Review/extends",
        "/spec/policies/Review/appliesTo/0",
    ]
    assert any("protocols/Auditable" in c.detail for c in checks)
    assert checks[-1].outcome == "invalid"


def test_catalog_cannot_be_replaced_by_a_project_dictionary(monkeypatch, tmp_path):
    spec, member = member_spec()
    replacement = tmp_path / "exports.json"
    monkeypatch.setattr(foundation, "EXPORTS", replacement)
    checks, imports = foundation.check_import(spec, member, 1)
    assert checks[-1].outcome == "unavailable" and not imports
    replacement.write_text("sg:Typo is valid")
    checks, imports = foundation.check_import(spec, member, 1)
    assert checks[-1].outcome == "invalid" and not imports


@pytest.mark.parametrize(("count", "version"), [(2, "0.1.0"), (1, "0.2.0")])
def test_unsupported_import_sets_stay_unavailable(count, version):
    spec, member = member_spec()
    spec["imports"][0]["version"] = version
    checks, imports = foundation.check_import(spec, member, count)
    assert checks[-1].outcome == "unavailable" and not imports


def test_clean_source_without_saved_ir_remains_unavailable(compiler, tmp_path):
    source = MEMBER.read_bytes()
    capture(tmp_path / "good", compiler, source)
    prior = (tmp_path / "good/ir/ontology.normalized.json").read_bytes()
    code, report = capture(tmp_path / "missing", compiler, source, prior_ir=prior)
    assert code != 0 and report["outcome"] == "unavailable"
    assert report["context_revision"] is None and not report["snapshots"]


def test_compiler_sites_are_bound_to_captured_values():
    spec, member = member_spec()
    spec["relations"]["follows"]["range"] = {"oneOf": ["Entry", "sg:Typo"]}
    failure = ("relation.range.unresolved", "spec.relations.follows.range.oneOf[1]", "reason")
    diagnostics = (
        failure,
        (failure[0], "spec.relations.follows.range.oneOf[9]", "reason"),
        (failure[0], "spec.classes.Entry.description", "wrong field"),
    )
    spec["classes"]["Entry"]["description"] = "sg:Typo"
    [check] = foundation.failed_capture_checks(
        {"spec": spec}, member, 1, OntologySourceRejection(diagnostics, "a" * 64, "b" * 64)
    )
    assert check.reference.pointer == "/spec/relations/follows/range/oneOf/1"
    assert check.reference.name == "sg:Typo" and check.compiler_diagnostic.code == failure[0]


@pytest.mark.parametrize(
    ("old", "new"),
    [(b"namespace: sample", b"namespace: sg"), (b"test.sg72-member", b"specgraph.foundation")],
)
def test_shadowed_identity_is_invalid_even_without_ir(compiler, tmp_path, old, new):
    source = MEMBER.read_bytes()
    capture(tmp_path / "accepted", compiler, source)
    prior = (tmp_path / "accepted/ir/ontology.normalized.json").read_bytes()
    code, report = capture(
        tmp_path / "shadowed", compiler, source.replace(old, new), prior_ir=prior
    )
    assert (code, report["outcome"], report["context_revision"]) == (2, "invalid", None)
    assert any(
        c["check"] == "dependency_closure"
        and c["outcome"] == "invalid"
        and "shadows" in c["detail"]
        for c in report["checks"]
    )
