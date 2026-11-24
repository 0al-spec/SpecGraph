"""Scope outcome priorities and traces, including conservative completion fallback."""

import sys
from itertools import permutations
from pathlib import Path

import pytest
from specification_core import TraceRecorder

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from project_ontology_check_scopes import ScopeFacts  # noqa: E402
from project_ontology_scope_aggregation_spec import scope_check_outcome  # noqa: E402

DOMAIN = "domain_vocabulary"
META = "specification_metamodel"


@pytest.mark.parametrize(
    ("requested", "outcomes", "expected"),
    [
        ((), (), "unavailable"),
        ((DOMAIN,), ("analyzed",), "analyzed"),
        ((DOMAIN,), ("unavailable",), "unavailable"),
        ((DOMAIN,), ("invalid",), "invalid"),
        ((DOMAIN, META), ("analyzed", "analyzed"), "analyzed"),
        ((DOMAIN, META), ("analyzed", "unavailable"), "unavailable"),
        ((DOMAIN, META), ("unavailable", "unavailable"), "unavailable"),
        ((DOMAIN, META), ("invalid", "analyzed"), "invalid"),
        ((DOMAIN, META), ("invalid", "unavailable"), "invalid"),
        ((DOMAIN, META), ("invalid", "invalid"), "invalid"),
        ((DOMAIN,), (), "unavailable"),
        ((DOMAIN,), ("analyzed", "analyzed"), "unavailable"),
        ((DOMAIN,), ("unknown",), "unavailable"),
        ((DOMAIN,), ("not_requested",), "unavailable"),
    ],
)
def test_scope_outcome_table(requested, outcomes, expected):
    for ordered in set(permutations(outcomes)):
        assert scope_check_outcome(ScopeFacts(requested, ordered)) == expected


@pytest.mark.parametrize(
    ("outcomes", "expected", "events"),
    [
        (
            ("invalid", "unavailable"),
            "invalid",
            [
                ("project_ontology_report.scope_outcome", "selected"),
                ("project_ontology_report.requested_scope_invalid", "satisfied"),
                ("pair[1]:project_ontology_report.requested_scopes_analyzed", "skipped"),
            ],
        ),
        (
            ("analyzed", "analyzed"),
            "analyzed",
            [
                ("project_ontology_report.scope_outcome", "selected"),
                ("project_ontology_report.requested_scope_invalid", "unsatisfied"),
                ("project_ontology_report.requested_scopes_analyzed", "satisfied"),
            ],
        ),
        (
            ("analyzed", "unavailable"),
            "unavailable",
            [
                ("project_ontology_report.scope_outcome", "selected"),
                ("project_ontology_report.requested_scope_invalid", "unsatisfied"),
                ("project_ontology_report.requested_scopes_analyzed", "unsatisfied"),
            ],
        ),
    ],
)
def test_scope_trace_preserves_rule_names_and_skips(outcomes, expected, events):
    recorder = TraceRecorder()
    facts = ScopeFacts((DOMAIN, META), outcomes)
    assert scope_check_outcome(facts, recorder=recorder) == expected
    assert [(event.name, event.outcome.value) for event in recorder.events] == events
