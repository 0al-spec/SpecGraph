"""Characterize the legacy proxy independently of its extracted implementation."""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
from specification_core import TraceRecorder

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = json.loads(
    (ROOT / "tests/fixtures/metric_packs/legacy_verifiability.json").read_text(encoding="utf-8")
)


@pytest.mark.parametrize("case", FIXTURE["cases"], ids=lambda case: case["name"])
def test_legacy_projection_matches_pre_refactor_snapshot(supervisor_module, case) -> None:
    pack = supervisor_module.get_metric_packs_module()
    context = pack.prepare_verifiability_context(
        case["entries"], case["status_scores"], case["minimum_score"], case["trigger_signal"]
    )
    result = pack.LegacyVerifiabilityMetric().evaluate(context)
    assert result.to_payload() == case["expected"]
    # Preserve the existing serialized key order as well as values and fields.
    assert json.dumps(result.to_payload()) == json.dumps(case["expected"])


@pytest.mark.parametrize(
    "score,threshold,expected",
    [
        (None, 0.45, "not_applicable"),
        (0.45, 0.45, "healthy"),
        (0.44, 0.45, "below_threshold"),
        (0.0, -1.0, "healthy"),
        (float("inf"), 0.45, "healthy"),
        (float("nan"), 0.45, "below_threshold"),
        (0.45, float("nan"), "below_threshold"),
        (None, float("nan"), "not_applicable"),
    ],
)
def test_shared_status_policy_preserves_threshold_semantics(
    supervisor_module, score, threshold, expected
) -> None:
    assert supervisor_module.metric_status_from_score(score, threshold) == expected


def test_absent_score_skips_threshold_branch(supervisor_module) -> None:
    pack = supervisor_module.get_metric_packs_module()
    recorder = TraceRecorder()
    decision = pack.SCORE_STATUS_SPEC.decide(pack.ScoreThreshold(None, 0.45), recorder=recorder)
    assert decision.value == "not_applicable"
    assert ("pair[1]:metrics.score_meets_threshold", "skipped") in [
        (event.name, event.outcome.value) for event in recorder.events
    ]


def test_shared_status_policy_retains_invalid_score_error(supervisor_module) -> None:
    with pytest.raises(TypeError):
        supervisor_module.metric_status_from_score("invalid", 0.45)


def test_prepared_context_is_independent_of_mutable_json(supervisor_module) -> None:
    pack = supervisor_module.get_metric_packs_module()
    entries = [{"acceptance_coverage": {"status": "covered"}}]
    scores = {"covered": 1.0}
    context = pack.prepare_verifiability_context(entries, scores, 0.45, "attention")
    entries[0]["acceptance_coverage"]["status"] = "no_linked_evidence"
    scores["covered"] = 0.0
    result = pack.LegacyVerifiabilityMetric().evaluate(context)
    assert result.score == 1.0
    with pytest.raises(FrozenInstanceError):
        context.observations[0].score = 0.0
    payload = result.to_payload()
    payload["input_summary"]["acceptance_status_counts"]["covered"] = 99
    assert result.to_payload()["input_summary"]["acceptance_status_counts"] == {"covered": 1}


def test_context_defensively_copies_observation_sequence(supervisor_module) -> None:
    pack = supervisor_module.get_metric_packs_module()
    prepared = pack.prepare_verifiability_context(
        [{"acceptance_coverage": {"status": "covered"}}], {"covered": 1}, 0.45, "attention"
    )
    values = list(prepared.observations)
    context = pack.VerifiabilityContext(values, 0.45, "attention")
    values.clear()
    assert len(context.observations) == 1


def test_metric_package_loads_in_isolation_without_writing_artifacts(tmp_path) -> None:
    # No inherited PYTHONPATH, repository cwd, or other pytest module can bootstrap imports.
    source = ROOT / "tools/metric_packs/__init__.py"
    script = """
import importlib.util, json, sys
from pathlib import Path
path = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location(
    'isolated_metric_pack', path, submodule_search_locations=[str(path.parent)])
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
context = module.prepare_verifiability_context(
    [{'acceptance_coverage': {'status': 'covered'}}], {'covered': 1.0}, 0.45, 'attention')
print(json.dumps(module.LegacyVerifiabilityMetric().evaluate(context).to_payload()))
"""
    completed = subprocess.run(
        [sys.executable, "-I", "-B", "-c", script, str(source)],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=True,
    )
    assert json.loads(completed.stdout)["score"] == 1.0
    assert list(tmp_path.iterdir()) == []
