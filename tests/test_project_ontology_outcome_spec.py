"""Priority, caller-specific success and diagnostic traces of context decisions."""

import sys
from itertools import permutations
from pathlib import Path

import pytest
from specification_core import TraceRecorder

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from project_ontology_context.model import CheckResult, ContextFacts  # noqa: E402
from project_ontology_context.outcome_spec import context_check_outcome  # noqa: E402
from project_ontology_supervisor_check import _outcome  # noqa: E402


@pytest.mark.parametrize(
    ("checks", "failure"),
    [
        ((), None),
        (("verified",), None),
        (("unknown",), None),
        (("verified", "unknown"), None),
        (("unavailable",), "unavailable"),
        (("invalid",), "invalid"),
        (("invalid", "unavailable", "verified"), "invalid"),
        (("unavailable", "unknown", "verified"), "unavailable"),
        (("invalid", "invalid"), "invalid"),
    ],
)
def test_outcome_table_preserves_both_success_vocabularies(checks, failure):
    for outcomes in set(permutations(checks)):
        facts = ContextFacts(
            tuple(CheckResult(str(i), value, value) for i, value in enumerate(outcomes))
        )
        assert context_check_outcome(facts, success="verified") == (failure or "verified")
        assert context_check_outcome(facts, success="checked") == (failure or "checked")
        assert _outcome(facts) == (failure or "checked")


@pytest.mark.parametrize(
    ("outcomes", "result", "expected"),
    [
        (
            ("unavailable", "invalid"),
            "invalid",
            [
                ("project_ontology_context.failure_precedence", "selected"),
                ("project_ontology_context.invalid", "satisfied"),
                ("pair[1]:project_ontology_context.unavailable", "skipped"),
            ],
        ),
        (
            ("unavailable",),
            "unavailable",
            [
                ("project_ontology_context.failure_precedence", "selected"),
                ("project_ontology_context.invalid", "unsatisfied"),
                ("project_ontology_context.unavailable", "satisfied"),
            ],
        ),
        (
            ("verified",),
            "checked",
            [
                ("project_ontology_context.failure_precedence", "selected"),
                ("project_ontology_context.invalid", "unsatisfied"),
                ("project_ontology_context.unavailable", "unsatisfied"),
            ],
        ),
    ],
)
def test_trace_shows_selected_and_skipped_rules(outcomes, result, expected):
    facts = ContextFacts(tuple(CheckResult(value, value, value) for value in outcomes))
    recorder = TraceRecorder()
    assert context_check_outcome(facts, success="checked", recorder=recorder) == result
    assert [(event.name, event.outcome.value) for event in recorder.events] == expected
