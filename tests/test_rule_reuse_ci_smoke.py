"""Check snapshot provenance independently of analyzer matching."""

import json
import subprocess
from pathlib import Path

import pytest
from tools import rule_reuse_ci_smoke as smoke


def test_dirty_fixture_does_not_change_recorded_snapshot(tmp_path, monkeypatch):
    repo = tmp_path / "source"
    repo.mkdir()
    smoke.git(repo, "init", "-q")
    fixture = repo / "tests/fixtures/rule_reuse/workspace_allocation_copy.py"
    fixture.parent.mkdir(parents=True)
    original = "def policy(value):\n    return value is True\n\n"
    fixture.write_text(original, encoding="utf-8")
    catalog = repo / "tools/rule_reuse_catalog.toml"
    catalog.parent.mkdir()
    catalog.write_text("schema_version = 1\n", encoding="utf-8")
    additional = {}
    for name in (
        "reviewed_record_copy",
        "reviewed_record_reuse",
        "reviewed_record_partial",
        "unrelated_digest",
    ):
        text = (Path(__file__).parent / "fixtures/rule_reuse" / f"{name}.py").read_text(
            encoding="utf-8"
        )
        additional[name] = text
        (fixture.parent / f"{name}.py").write_text(text, encoding="utf-8")
    revision = smoke.commit(repo)
    for name in additional:
        (fixture.parent / f"{name}.py").write_text("uncommitted invalid fixture!", encoding="utf-8")
    fixture.write_text("uncommitted invalid fixture!", encoding="utf-8")
    observed = []

    def gate(args, **kwargs):
        # Only the external analyzer is simulated. Git commits and fixture
        # selection use the real smoke producer and an actual dirty checkout.
        root, base, head, output = Path(args[2]), args[4], args[5], Path(args[6])
        output.mkdir()
        copied = root / "tools/smoke_copy.py"
        code = copied.read_text(encoding="utf-8") if copied.exists() else None
        observed.append(code)
        exact = int(output.name in {"exact_copy", "reviewed_record_exact"})
        near = int(output.name == "changed_authority")
        reuse = int(output.name == "reviewed_record_reuse")
        report = {
            "status": "complete",
            "base_revision": base,
            "head_revision": head,
            "new_reimplementations": exact,
            "new_near_matches": near,
            "reused_specifications": reuse,
            "findings": []
            if not (exact or near)
            else [
                {
                    "rule_id": "subject_publication.complete_reviewed_record"
                    if output.name == "reviewed_record_exact"
                    else "subject_publication.workspace_allocation",
                    "path": "tools/smoke_copy.py",
                    "introduced": True,
                    "kind": "reimplementation" if exact else "near_match",
                }
            ],
        }
        (output / "report.json").write_text(json.dumps(report), encoding="utf-8")
        (output / "mode.txt").write_text("enforcing\n", encoding="utf-8")
        return subprocess.CompletedProcess(
            args, exact, "", "rule reuse gate failed:" if exact else ""
        )

    # check_output uses subprocess.run internally; preserve actual Git calls.
    real_run = subprocess.run

    def run(args, **kwargs):
        return gate(args, **kwargs) if args[0] == "bash" else real_run(args, **kwargs)

    monkeypatch.setattr(smoke.subprocess, "run", run)
    result = smoke.smoke(repo, tmp_path / "analyzer", tmp_path / "output")
    assert result["source_revision"] == revision
    assert result["status"] == "complete"
    assert observed == [
        None,
        original,
        original.replace("is True", "is False", 1),
        additional["reviewed_record_reuse"],
        additional["reviewed_record_copy"],
        additional["reviewed_record_partial"],
        additional["unrelated_digest"],
    ]
    assert "partial field checks are not detected" in result["coverage_gaps"][0]
    for name in additional:
        assert (fixture.parent / f"{name}.py").read_text(
            encoding="utf-8"
        ) == "uncommitted invalid fixture!"
    assert fixture.read_text(encoding="utf-8") == "uncommitted invalid fixture!"


@pytest.mark.parametrize("field,value", [("status", "frozen"), ("authority_class", "derived")])
def test_partial_check_is_not_full_record_equivalence(field, value, monkeypatch):
    """Counterexamples explain why the historical check cannot block as exact."""
    import copy
    import runpy

    monkeypatch.syspath_prepend(str(Path(__file__).resolve().parents[1] / "tools"))

    from subject_publication import scope_digest
    from subject_publication_context import ReviewedRecordContext
    from subject_reviewed_record_spec import REVIEWED_RECORD_SPEC

    partial = runpy.run_path(
        str(Path(__file__).parent / "fixtures/rule_reuse/reviewed_record_partial.py")
    )["partial_reviewed_record"]
    revision = {
        "number": 1,
        "statement": "reviewed statement",
        "revision_scope": "full",
        "acceptance_criteria_refs": ["criterion:1"],
    }
    reviewed = {
        "subject": "subject:1",
        "title": "Reviewed subject",
        "status": "draft",
        "authority_class": "canonical",
        "revisions": [revision],
    }
    requested = copy.deepcopy(reviewed)
    requested[field] = value
    assert partial(
        reviewed, requested, requested["revisions"][-1], {"statement": revision["statement"]}
    )
    assert not REVIEWED_RECORD_SPEC.is_satisfied_by(
        ReviewedRecordContext(scope_digest(reviewed), scope_digest(requested))
    )
