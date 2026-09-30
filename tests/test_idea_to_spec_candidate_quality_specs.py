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
