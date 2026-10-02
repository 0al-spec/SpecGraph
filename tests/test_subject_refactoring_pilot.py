from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

import subject_refactoring_pilot as pilot  # noqa: E402


@pytest.fixture()
def plan() -> dict:
    return json.loads((TOOLS / "subject_refactoring_pilot.json").read_text())


@pytest.mark.parametrize("defect", ["current", "unavailable", "duplicate", "canonical", "trace"])
def test_invalid_binding_never_becomes_evidence(plan: dict, defect: str) -> None:
    binding = plan["bindings"][0]
    if defect == "current":
        binding["criterion"]["mode"] = "current"
    elif defect == "unavailable":
        binding["criterion"]["revision"] = 2
    elif defect == "duplicate":
        plan["bindings"].append(copy.deepcopy(binding))
    elif defect == "canonical":
        binding["canonical_requirement"] = "fabricated-requirement"
    else:
        plan["trace_probe"]["criterion"]["revision"] = 2
    with pytest.raises(ValueError):
        pilot.validate_plan(plan)


def test_curated_id_is_independent_of_checkpoint_and_source_path(plan: dict) -> None:
    index = pilot.validate_plan(plan)
    for binding in plan["bindings"]:
        selection = binding["criterion"]
        ref = pilot.parse_subject_ref(selection["subject"])
        exact = index.lookup_exact(ref, 1)
        assert index.lookup_current(ref).selected_revision == exact.selected_revision
        assert index.lookup_exact(ref, 2).status == "unavailable_revision"
        assert exact.record.canonical_presence is None
        assert binding["canonical_requirement"] is None
    assert len(index.snapshots[0].subjects) == 4


@pytest.mark.parametrize(
    "xml,returncode",
    [
        ("<testsuites/>", 0),
        (
            '<testsuites><testcase classname="tests.test_demo" name="test_ok">'
            "<skipped/></testcase></testsuites>",
            0,
        ),
        ('<testsuites><testcase classname="tests.test_demo" name="test_other"/></testsuites>', 0),
        ('<testsuites><testcase classname="tests.test_demo" name="test_ok"/></testsuites>', 1),
    ],
)
def test_process_success_or_skipped_or_wrong_tests_are_not_passing_evidence(
    tmp_path: Path,
    xml: str,
    returncode: int,
) -> None:
    path = tmp_path / "tests.xml"
    path.write_text(xml)
    result = pilot.junit_results(path, ["tests/test_demo.py::test_ok"], returncode)
    assert result["status"] == "failed"


def test_junit_requires_exact_selected_case_set(tmp_path: Path) -> None:
    path = tmp_path / "tests.xml"
    case = '<testcase classname="tests.test_demo" name="test_ok"/>'
    path.write_text(f"<testsuites>{case}</testsuites>")
    expected = ["tests/test_demo.py::test_ok"]
    assert pilot.junit_results(path, expected, 0)["status"] == "passed"
    path.write_text(f"<testsuites>{case}{case}</testsuites>")
    assert pilot.junit_results(path, expected, 0)["status"] == "failed"


def test_missing_file_does_not_resolve_same_named_symbol_elsewhere(monkeypatch) -> None:
    monkeypatch.setattr(pilot, "source_blob", lambda *_: None)
    result = pilot.code_anchor(Path("."), "a" * 40, "tools/removed.py::policy")
    assert result["status"] == "missing_path"


def test_source_anchor_rejects_nested_and_ambiguous_symbols(monkeypatch) -> None:
    for source in (
        b"def outer():\n    def policy(): pass\n",
        b"def policy(): pass\ndef policy(): pass\n",
    ):
        monkeypatch.setattr(pilot, "source_blob", lambda *_, blob=source: blob)
        result = pilot.code_anchor(Path("."), "a" * 40, "tools/module.py::policy")
        assert result["status"] == "missing_or_ambiguous_symbol"


def test_text_presence_is_not_a_fuzzy_semantic_match(monkeypatch) -> None:
    monkeypatch.setattr(pilot, "source_blob", lambda *_: b"must stay blocked")
    result = pilot.source_statement(Path("."), "a" * 40, "rule.md", "may become ready")
    assert result["status"] == "missing_or_ambiguous_text"


def test_previous_run_cannot_supply_stale_success(tmp_path: Path, plan: dict) -> None:
    (tmp_path / "report.json").write_text('{"status":"pilot_passed"}')
    with pytest.raises(FileExistsError):
        pilot.run_pilot(tmp_path, plan, tmp_path, execute=False)


def test_source_only_run_is_explicitly_incomplete(tmp_path: Path, plan: dict, monkeypatch) -> None:
    monkeypatch.setattr(pilot, "checked_commit", lambda _, commit: commit)
    monkeypatch.setattr(pilot, "source_statement", lambda *_: {"status": "unique_text_match"})
    stale = plan["stale_anchor_probe"]

    def anchor(_, commit, value):
        missing = commit == stale["absent_at"] and value == stale["anchor"]
        return {"status": "missing_path" if missing else "source_anchored"}

    monkeypatch.setattr(pilot, "code_anchor", anchor)
    report = pilot.run_pilot(tmp_path, plan, tmp_path / "new-run", execute=False)
    assert report["status"] == "incomplete"
    assert report["canonical_readiness"] == "not_evaluated"
    assert all(r["execution"]["status"] == "not_run" for r in report["checkpoints"])


def test_trace_requires_observed_outcomes_and_exact_event_name() -> None:
    rows = [
        {
            "scenario": name,
            "ready": ready,
            "no_op_repair_loop": True,
            "events": [{"name": "candidate_repair.preview_ready", "outcome": outcome}],
        }
        for name, ready, outcome in [
            ("clean-noop", True, "satisfied"),
            ("invalid-noop", False, "unsatisfied"),
        ]
    ]
    assert pilot.check_trace(rows, "candidate_repair.preview_ready")
    assert not pilot.check_trace(rows, "different_rule")
    rows[1]["ready"] = True
    assert not pilot.check_trace(rows, "candidate_repair.preview_ready")


def test_curated_report_matches_the_executed_plan_and_runner(plan: dict) -> None:
    path = TOOLS.parent / "docs/reviews/0221_refactoring_binding_pilot.json"
    report = json.loads(path.read_text())
    assert report["plan_sha256"] == pilot.digest(json.dumps(plan, sort_keys=True).encode())
    assert report["runner_sha256"] == pilot.digest(Path(pilot.__file__).read_bytes())
    assert report["status"] == "pilot_passed"
    assert report["canonical_readiness"] == "not_evaluated"
    assert [c["checkpoint"] for c in report["checkpoints"]] == plan["checkpoints"]
    assert all(c["execution"]["status"] == "passed" for c in report["checkpoints"])
    assert sum(len(c["execution"]["cases"]) for c in report["checkpoints"]) == 12
    assert (
        report["checkpoints"][-1]["execution"]["runtime_trace"]["criterion"]
        == (plan["trace_probe"]["criterion"])
    )
