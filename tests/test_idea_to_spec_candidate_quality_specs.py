from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.idea_to_spec_candidate_quality_context import (  # noqa: E402
    CandidateQualityContext,
    GapResolutionContext,
)
from tools.idea_to_spec_candidate_quality_fields import CANDIDATE_QUALITY_FIELDS  # noqa: E402
from tools.idea_to_spec_candidate_quality_review_spec import (  # noqa: E402
    candidate_quality_review_state,
)
from tools.idea_to_spec_gap_resolution_spec import gap_resolution_state  # noqa: E402
from tools.idea_to_spec_rerun_preview import _candidate_quality_preview  # noqa: E402


@pytest.mark.parametrize(
    ("context", "expected"),
    [
        (CandidateQualityContext(1, 0, 0, 0), "candidate_quality_improved"),
        (CandidateQualityContext(1, 1, 0, 0), "candidate_quality_partially_improved"),
        (CandidateQualityContext(0, 1, 0, 1), "candidate_quality_blocked_by_gaps"),
        (
            CandidateQualityContext(0, 1, 0, 0),
            "candidate_quality_blocked_by_ontology_gaps",
        ),
        (
            CandidateQualityContext(0, 0, 0, 1),
            "candidate_quality_blocked_by_candidate_gaps",
        ),
        (CandidateQualityContext(0, 0, 0, 0), "candidate_quality_unchanged"),
    ],
)
def test_candidate_quality_review_spec_preserves_ordered_states(
    context: CandidateQualityContext,
    expected: str,
) -> None:
    assert candidate_quality_review_state(context) == expected


@pytest.mark.parametrize(
    ("resolved_count", "unresolved_count", "aggregate_resolved_count", "expected"),
    [
        (1, 1, 1, "partially_preview_resolved"),
        (0, 1, 1, "partially_preview_resolved"),
        (1, 0, 1, "all_preview_resolved"),
        (0, 1, 0, "unresolved"),
        (0, 0, 0, "no_candidate_gaps"),
    ],
)
def test_gap_resolution_spec_preserves_family_states(
    resolved_count: int,
    unresolved_count: int,
    aggregate_resolved_count: int,
    expected: str,
) -> None:
    context = GapResolutionContext(
        resolved_count=resolved_count,
        unresolved_count=unresolved_count,
        aggregate_resolved_count=aggregate_resolved_count,
        no_gaps_state="no_candidate_gaps",
    )

    assert gap_resolution_state(context) == expected


def test_candidate_quality_preview_preserves_mixed_family_partial_state() -> None:
    result = _candidate_quality_preview(
        {"resolved_ontology_gap_count": 0, "unresolved_ontology_gap_count": 1},
        {"resolved_candidate_gap_count": 1, "unresolved_candidate_gap_count": 0},
    )

    assert result["review_state"] == "candidate_quality_partially_improved"
    assert result["ontology_gap_state"] == "partially_preview_resolved"
    assert result["candidate_gap_state"] == "all_preview_resolved"


def test_candidate_quality_field_trace_keeps_skipped_rules_with_their_field() -> None:
    trace = []
    fields = CANDIDATE_QUALITY_FIELDS.apply(
        CandidateQualityContext(1, 0, 0, 0),
        trace=trace,
    )

    assert fields == {
        "review_state": "candidate_quality_improved",
        "ontology_gap_state": "all_preview_resolved",
        "candidate_gap_state": "no_candidate_gaps",
    }
    assert [field.field_name for field in trace] == [
        "review_state",
        "ontology_gap_state",
        "candidate_gap_state",
    ]
    assert [field.value for field in trace] == list(fields.values())
    assert ("pair[1]:candidate_quality.some_gaps_resolved", "skipped") in [
        (event.name, event.outcome.value) for event in trace[0].events
    ]
    assert ("pair[2]:gap_resolution.unresolved", "skipped") in [
        (event.name, event.outcome.value) for event in trace[1].events
    ]
    assert all(
        not event.name.startswith("candidate_quality.")
        for field in trace[1:]
        for event in field.events
    )
