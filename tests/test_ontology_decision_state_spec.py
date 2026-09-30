"""Behavior matrix for extracted ontology decision-state counts."""

from __future__ import annotations

import importlib.util
import itertools
import sys
from dataclasses import FrozenInstanceError, astuple
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/ontology_decision_counts"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


BASELINE = load_module(FIXTURES / "baseline.py", "decision_counts_baseline")
CONVENTIONAL = load_module(FIXTURES / "conventional.py", "decision_counts_conventional")
SPECIFICATION = load_module(
    ROOT / "tools/ontology_decision_state_spec.py", "decision_counts_specification"
)
BASELINE_FUNCTIONS = (
    BASELINE.owner_report_counts,
    BASELINE.import_preview_counts,
    BASELINE.import_v2_counts,
)


def test_extracted_counts_match_all_three_baselines() -> None:
    states = ("accepted", "rejected", "needs_clarification", "unknown", None)
    cases = 0
    for length in range(5):
        for values in itertools.product(states, repeat=length):
            records = [{"decision_state": value} for value in values]
            expected = (
                values.count("accepted"),
                values.count("rejected"),
                values.count("needs_clarification"),
            )
            assert all(count(records) == expected for count in BASELINE_FUNCTIONS)
            assert astuple(CONVENTIONAL.count_decision_states(records)) == expected
            assert astuple(SPECIFICATION.count_decision_states(records)) == expected
            cases += 1
    assert cases == 781


@pytest.mark.parametrize("value", [" ACCEPTED ", "Accepted", "", True, 0, [], {}])
def test_unknown_values_are_ignored_without_normalization(value: object) -> None:
    records = [{"decision_state": value}]
    assert astuple(CONVENTIONAL.count_decision_states(records)) == (0, 0, 0)
    assert astuple(SPECIFICATION.count_decision_states(records)) == (0, 0, 0)
    assert all(count(records) == (0, 0, 0) for count in BASELINE_FUNCTIONS)


def test_missing_key_remains_an_error() -> None:
    for count in (
        *BASELINE_FUNCTIONS,
        CONVENTIONAL.count_decision_states,
        SPECIFICATION.count_decision_states,
    ):
        with pytest.raises(KeyError, match="decision_state"):
            count([{}])


@pytest.mark.parametrize("module", [CONVENTIONAL, SPECIFICATION])
def test_result_is_immutable(module) -> None:
    counts = module.count_decision_states([])
    with pytest.raises(FrozenInstanceError):
        counts.accepted = 1
