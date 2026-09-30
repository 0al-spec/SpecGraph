"""Regression checks for the criterion-change experiment, including missed edits."""

from __future__ import annotations

import ast
import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/ontology_decision_counts"
spec = importlib.util.spec_from_file_location(
    "decision_change_exercise", FIXTURES / "change_exercise.py"
)
assert spec and spec.loader
EXERCISE = importlib.util.module_from_spec(spec)
spec.loader.exec_module(EXERCISE)


@pytest.fixture()
def cohorts(monkeypatch):
    # Unit tests need no Git history in a shallow CI checkout. The measured
    # exercise separately reads the full pinned production files through Git.
    frozen = ast.parse((FIXTURES / "baseline.py").read_text()).body
    functions = [node for node in frozen if isinstance(node, ast.FunctionDef)]
    baseline = {}
    index = 0
    for filename, symbols in EXERCISE.SITES.items():
        nodes = []
        for symbol, _ in symbols:
            node = copy.deepcopy(functions[index])
            node.name = symbol
            nodes.append(node)
            index += 1
        baseline[filename] = ast.unparse(ast.Module(body=nodes, type_ignores=[])) + "\n"
    consumers = dict(baseline)
    for filename, symbols in EXERCISE.SITES.items():
        tree = ast.parse(consumers[filename])
        assert len(tree.body) == len(symbols)
        for index, (_, records_name) in enumerate(symbols):
            node = tree.body[index]
            node.body = ast.parse(
                f"decision_counts = count_decision_states({records_name})\n"
                "accepted_count = decision_counts.accepted\n"
                "rejected_count = decision_counts.rejected\n"
                "clarification_count = decision_counts.clarification\n"
                "return accepted_count, rejected_count, clarification_count\n"
            ).body
        consumers[filename] = ast.unparse(tree) + "\n"
    result = {
        "baseline": baseline,
        "conventional": {**consumers, EXERCISE.MODULE: (FIXTURES / "conventional.py").read_text()},
        "specification": {
            **consumers,
            EXERCISE.MODULE: (ROOT / "tools" / EXERCISE.MODULE).read_text(),
        },
    }
    monkeypatch.setattr(EXERCISE, "sources_from_git", lambda: result)
    return result


def test_change_reaches_all_consumers_and_detects_incomplete_edit(tmp_path, cohorts) -> None:
    before = copy.deepcopy(cohorts)
    report = EXERCISE.run(tmp_path / "experiment")
    assert report["status"] == "pass"
    assert cohorts == before
    for name, variant in report["variants"].items():
        assert variant["footprint"]["changed_files"] == (2 if name == "baseline" else 1)
        assert variant["edited_criteria"] == (3 if name == "baseline" else 1)
        assert len(variant["changed_consumers"]) == 3
        assert variant["edge_checks_passed"] is True
        for phase in ("before_matrix", "after_matrix"):
            assert variant[phase]["cases_per_consumer"] == 1555
            assert set(variant[phase]["failures"].values()) == {0}
        assert (tmp_path / "experiment" / f"{name}.patch").is_file()
    assert report["incomplete_change_probe"]["failures"] == {
        "build_ontology_owner_decision_report": 0,
        "build_ontology_decision_import_preview": 774,
        "build_owner_decision_import_v2": 774,
    }
    assert json.loads((tmp_path / "experiment/result.json").read_text()) == report


def test_existing_output_directory_is_rejected(tmp_path) -> None:
    with pytest.raises(ValueError, match="fresh output directory"):
        EXERCISE.run(tmp_path)


def test_source_drift_is_reported_instead_of_silently_skipping_a_criterion(cohorts) -> None:
    sources = dict(cohorts["specification"])
    sources[EXERCISE.MODULE] = sources[EXERCISE.MODULE].replace('== "accepted"', '== "other"')
    with pytest.raises(ValueError, match="Expected one accepted criterion, found 0"):
        EXERCISE.change_criterion(sources, "specification")
