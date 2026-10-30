"""Characterization records limits, not invented authoring guarantees."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from authoring_pilot_baseline import characterize  # noqa: E402


def test_existing_checks_distinguish_shape_from_completeness():
    path = Path(__file__).resolve().parents[1] / "specs/nodes/SG-SPEC-0072.yaml"
    source = path.read_bytes()
    report = characterize(source)
    cases = {row["experiment"]: row for row in report["experiments"]}
    assert len(report["expected_acceptance_inventory"]) == 4
    removed = cases["remove_criterion_and_matching_evidence"]
    assert removed["remaining_acceptance_count"] == 3
    assert removed["observations"]["acceptance_shape_errors"] == []
    assert cases["remove_evidence_only"]["observations"]["acceptance_shape_errors"]
    assert cases["contradict_outcome_precedence_prose"]["observations"]["bdd_findings"] == []
    assert cases["synthetic_linked_declaration"]["observations"]["bdd_findings"] == []
    assert cases["remove_referenced_synthetic_scenario"]["observations"]["bdd_findings"]
    assert report["authoring_readiness"] == "not_evaluated"
    assert characterize(source) == report
    assert path.read_bytes() == source
