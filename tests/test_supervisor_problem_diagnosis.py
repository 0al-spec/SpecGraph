from __future__ import annotations

import json
from pathlib import Path

import pytest


def _patch_repo(
    supervisor_module: object,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> Path:
    root = tmp_path
    specs_dir = root / "specs" / "nodes"
    runs_dir = root / "runs"
    specs_dir.mkdir(parents=True)
    runs_dir.mkdir(parents=True)
    monkeypatch.setattr(supervisor_module, "ROOT", root)
    monkeypatch.setattr(supervisor_module, "SPECS_DIR", specs_dir)
    monkeypatch.setattr(supervisor_module, "RUNS_DIR", runs_dir)
    monkeypatch.setattr(supervisor_module, "WORKTREES_DIR", root / ".worktrees")
    monkeypatch.setattr(supervisor_module, "AGENTS_FILE", root / "AGENTS.md")
    (root / "AGENTS.md").write_text("# AGENTS\n", encoding="utf-8")
    _write_spec(supervisor_module, specs_dir / "SG-SPEC-0001.yaml", "SG-SPEC-0001")
    return root


def _write_spec(supervisor_module: object, path: Path, spec_id: str) -> None:
    data = {
        "id": spec_id,
        "title": "Diagnosis Fixture",
        "kind": "spec",
        "created_at": "2026-05-24T00:00:00Z",
        "updated_at": "2026-05-24T00:00:00Z",
        "status": "outlined",
        "maturity": 0.2,
        "depends_on": [],
        "relates_to": [],
        "inputs": [],
        "outputs": [path.relative_to(path.parents[2]).as_posix()],
        "allowed_paths": [path.relative_to(path.parents[2]).as_posix()],
        "acceptance": ["first bounded criterion", "second bounded criterion"],
        "prompt": "Refine this node.",
    }
    path.write_text(supervisor_module.dump_yaml_text(data), encoding="utf-8")


def _write_run(root: Path, run_id: str, payload: dict[str, object]) -> Path:
    path = root / "runs" / f"{run_id}.json"
    data = {
        "run_id": run_id,
        "spec_id": "SG-SPEC-0001",
        "title": "Diagnosis Fixture",
        "completion_status": "ok",
        "outcome": "done",
        "gate_state": "none",
        "changed_files": [],
        "validation_errors": [],
        "validation_findings": [],
        "validator_results": {},
    }
    data.update(payload)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _read_diagnosis(root: Path) -> dict[str, object]:
    return json.loads((root / "runs" / "supervisor_problem_diagnosis.json").read_text())


def _problem_classes(report: dict[str, object]) -> set[str]:
    problems = report.get("detected_problems", [])
    assert isinstance(problems, list)
    return {str(problem.get("problem_class")) for problem in problems if isinstance(problem, dict)}


def test_problem_diagnosis_handles_missing_run_as_insufficient_evidence(
    supervisor_module: object,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root = _patch_repo(supervisor_module, monkeypatch, tmp_path)

    exit_code = supervisor_module.main(
        build_supervisor_problem_diagnosis_mode=True,
        supervisor_run_path="missing-run",
    )

    assert exit_code == 0
    report = _read_diagnosis(root)
    assert report["artifact_kind"] == "supervisor_problem_diagnosis"
    assert report["canonical_mutations_allowed"] is False
    assert report["tracked_artifacts_written"] is False
    assert report["diagnosis"]["overall_status"] == "insufficient_evidence"
    assert report["source"]["source_status"] == "unavailable"


def test_problem_diagnosis_handles_malformed_run_as_insufficient_evidence(
    supervisor_module: object,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root = _patch_repo(supervisor_module, monkeypatch, tmp_path)
    malformed = root / "runs" / "bad.json"
    malformed.write_text("{not json", encoding="utf-8")

    report = supervisor_module.build_supervisor_problem_diagnosis(
        supervisor_run_path=str(malformed)
    )

    assert report["diagnosis"]["overall_status"] == "insufficient_evidence"
    assert report["source"]["source_status"] == "unavailable"
    assert "malformed supervisor run artifact" in report["source"]["error"]
    assert str(tmp_path) not in report["source"]["error"]
    assert "runs/bad.json" in report["source"]["error"]


def test_problem_diagnosis_detects_provider_failure_without_raw_prompt_text(
    supervisor_module: object,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root = _patch_repo(supervisor_module, monkeypatch, tmp_path)
    run_path = _write_run(
        root,
        "20260524T000000Z-SG-SPEC-0001-provider",
        {
            "completion_status": "failed",
            "outcome": "blocked",
            "validator_results": {"executor_environment": False},
            "executor_environment": {
                "primary_failure": True,
                "issue_kinds": ["quota"],
                "issues": [{"kind": "quota", "summary": "provider usage limit reached"}],
            },
            "validation_errors": ["SECRET RAW PROMPT TEXT should not be copied"],
        },
    )

    report = supervisor_module.build_supervisor_problem_diagnosis(supervisor_run_path=str(run_path))

    assert report["diagnosis"]["overall_status"] == "hard_stop"
    assert "quota_or_provider_failure" in _problem_classes(report)
    assert "SECRET RAW PROMPT TEXT" not in json.dumps(report)


def test_problem_diagnosis_detects_runtime_residue(
    supervisor_module: object,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root = _patch_repo(supervisor_module, monkeypatch, tmp_path)
    run_path = _write_run(
        root,
        "20260524T000001Z-SG-SPEC-0001-residue",
        {
            "completion_status": "failed",
            "outcome": "blocked",
            "gate_state": "blocked",
            "changed_files": ["specs/nodes/SG-SPEC-0001.yaml"],
        },
    )

    report = supervisor_module.build_supervisor_problem_diagnosis(supervisor_run_path=str(run_path))

    assert report["diagnosis"]["overall_status"] == "actionable"
    assert "runtime_residue" in _problem_classes(report)


def test_problem_diagnosis_detects_split_required_candidate_without_proposal_path(
    supervisor_module: object,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    root = _patch_repo(supervisor_module, monkeypatch, tmp_path)
    run_path = _write_run(
        root,
        "20260524T000002Z-SG-SPEC-0001-split",
        {
            "completion_status": "failed",
            "outcome": "blocked",
            "changed_files": ["specs/nodes/SG-SPEC-0001.yaml"],
            "validation_findings": [
                {
                    "code": "atomicity_violation",
                    "family": "acceptance",
                    "error_class": "semantic_rejection",
                    "message": "Atomicity gate exceeded in rejected candidate.",
                }
            ],
            "decision_inspector": {"queue_effects": {"proposal_queue": {"emitted_ids": []}}},
        },
    )

    report = supervisor_module.build_supervisor_problem_diagnosis(supervisor_run_path=str(run_path))

    assert report["diagnosis"]["overall_status"] == "actionable"
    assert "split_required_candidate_without_proposal_path" in _problem_classes(report)
    assert report["detected_problems"][0]["recommended_action"]
