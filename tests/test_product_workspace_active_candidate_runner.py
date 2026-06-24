from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = ROOT / "runs" / "test_product_workspace_active_candidate_runner"
DEFAULT_RUN_ARTIFACTS = (
    ROOT / "runs" / "idea_event_storming_seed.json",
    ROOT / "runs" / "idea_event_storming_intake.json",
    ROOT / "runs" / "candidate_spec_graph_seed.json",
    ROOT / "runs" / "candidate_spec_graph.json",
    ROOT / "runs" / "pre_sib_coherence_report.json",
    ROOT / "runs" / "candidate_repair_loop_report.json",
    ROOT / "runs" / "materialized_candidate_specs",
    ROOT / "runs" / "candidate_spec_materialization_report.json",
    ROOT / "runs" / "idea_to_spec_promotion_gate.json",
    ROOT / "runs" / "active_idea_to_spec_candidate.json",
)


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def backup_paths(paths: tuple[Path, ...], backup_dir: Path) -> None:
    if backup_dir.exists():
        shutil.rmtree(backup_dir)
    backup_dir.mkdir(parents=True)
    for path in paths:
        if not path.exists():
            continue
        destination = backup_dir / path.relative_to(ROOT)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if path.is_dir():
            shutil.copytree(path, destination)
        else:
            shutil.copy2(path, destination)


def restore_paths(paths: tuple[Path, ...], backup_dir: Path) -> None:
    for path in paths:
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()
    for backup_path in sorted(backup_dir.rglob("*")):
        if backup_path.is_dir():
            continue
        destination = ROOT / backup_path.relative_to(backup_dir)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(backup_path, destination)
    for backup_path in sorted(
        (path for path in backup_dir.rglob("*") if path.is_dir()),
        key=lambda path: len(path.parts),
    ):
        destination = ROOT / backup_path.relative_to(backup_dir)
        destination.mkdir(parents=True, exist_ok=True)
    if backup_dir.exists():
        shutil.rmtree(backup_dir)


def supported_python() -> str:
    candidates = [
        sys.executable,
        str(ROOT / ".venv" / "bin" / "python"),
        *(
            shutil.which(name) or ""
            for name in ("python3.13", "python3.12", "python3.11", "python3.10")
        ),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        candidate_path = Path(candidate)
        if candidate_path.is_absolute() and not candidate_path.exists():
            continue
        result = subprocess.run(
            [candidate, "tools/check_python_version.py"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        yaml_result = subprocess.run(
            [candidate, "-c", "import yaml"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and yaml_result.returncode == 0:
            return candidate
    pytest.skip("No Python >=3.10 interpreter with PyYAML available for Makefile integration test")


def test_product_workspace_active_candidate_default_paths_do_not_require_config() -> None:
    backup_dir = RUN_DIR / "default_path_backup"
    backup_paths(DEFAULT_RUN_ARTIFACTS, backup_dir)
    try:
        result = subprocess.run(
            [
                "make",
                "product-workspace-active-candidate",
                f"PYTHON={supported_python()}",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, result.stderr
        active = load_json(ROOT / "runs" / "active_idea_to_spec_candidate.json")
        assert active["artifact_kind"] == "active_idea_to_spec_candidate"
        assert active["candidate"]["candidate_id"] == "team-decision-log"
        assert active["config_source"]["mode"] == "artifact_defaults"
        assert active["config_source"]["required"] is False
        assert active["source_derivation"]["artifact_paths_source"] == "defaults"
        assert active["source_derivation"]["config_required"] is False
    finally:
        restore_paths(DEFAULT_RUN_ARTIFACTS, backup_dir)


def test_product_workspace_active_candidate_runs_from_generic_user_idea_source() -> None:
    if RUN_DIR.exists():
        shutil.rmtree(RUN_DIR)
    try:
        seed = RUN_DIR / "idea_event_storming_seed.json"
        intake = RUN_DIR / "idea_event_storming_intake.json"
        candidate_seed = RUN_DIR / "candidate_spec_graph_seed.json"
        candidate_graph = RUN_DIR / "candidate_spec_graph.json"
        pre_sib = RUN_DIR / "pre_sib_coherence_report.json"
        repair_loop = RUN_DIR / "candidate_repair_loop_report.json"
        materialized_dir = RUN_DIR / "materialized_candidate_specs"
        materialization = RUN_DIR / "candidate_spec_materialization_report.json"
        promotion_gate = RUN_DIR / "idea_to_spec_promotion_gate.json"
        active_candidate = RUN_DIR / "active_idea_to_spec_candidate.json"
        config = RUN_DIR / "active_candidate_source_generic.json"
        write_json(
            config,
            {
                "artifact_kind": "active_idea_to_spec_candidate_source_config",
                "artifacts": {
                    "candidate_graph": candidate_graph.relative_to(ROOT).as_posix(),
                    "intake": intake.relative_to(ROOT).as_posix(),
                    "materialization": materialization.relative_to(ROOT).as_posix(),
                    "pre_sib": pre_sib.relative_to(ROOT).as_posix(),
                    "promotion_gate": promotion_gate.relative_to(ROOT).as_posix(),
                    "repair_loop": repair_loop.relative_to(ROOT).as_posix(),
                },
                "contract_ref": "specgraph.idea-to-spec.active-candidate-source-config.v0.1",
                "schema_version": 1,
            },
        )

        result = subprocess.run(
            [
                "make",
                "product-workspace-active-candidate",
                f"PYTHON={supported_python()}",
                "PRODUCT_WORKSPACE_IDEA_SOURCE=tests/fixtures/user_idea_intake/source_ready.json",
                f"USER_IDEA_EVENT_STORMING_SEED_OUTPUT={seed.relative_to(ROOT).as_posix()}",
                f"IDEA_EVENT_STORMING_INTAKE_OUTPUT={intake.relative_to(ROOT).as_posix()}",
                "PRODUCT_WORKSPACE_CANDIDATE_SEED_OUTPUT="
                f"{candidate_seed.relative_to(ROOT).as_posix()}",
                f"CANDIDATE_SPEC_GRAPH_OUTPUT={candidate_graph.relative_to(ROOT).as_posix()}",
                f"PRE_SIB_COHERENCE_OUTPUT={pre_sib.relative_to(ROOT).as_posix()}",
                f"CANDIDATE_REPAIR_LOOP_OUTPUT={repair_loop.relative_to(ROOT).as_posix()}",
                "CANDIDATE_SPEC_MATERIALIZATION_OUTPUT_DIR="
                f"{materialized_dir.relative_to(ROOT).as_posix()}",
                "CANDIDATE_SPEC_MATERIALIZATION_OUTPUT="
                f"{materialization.relative_to(ROOT).as_posix()}",
                f"IDEA_TO_SPEC_PROMOTION_GATE_OUTPUT={promotion_gate.relative_to(ROOT).as_posix()}",
                "ACTIVE_IDEA_TO_SPEC_CANDIDATE_OUTPUT="
                f"{active_candidate.relative_to(ROOT).as_posix()}",
                f"PRODUCT_WORKSPACE_ACTIVE_CANDIDATE_CONFIG={config.relative_to(ROOT).as_posix()}",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, result.stderr
        active = load_json(active_candidate)
        assert active["artifact_kind"] == "active_idea_to_spec_candidate"
        assert active["candidate"]["candidate_id"] == "support-triage-log"
        assert active["candidate"]["public_route"] == "/support-triage-log"
        assert active["readiness"]["ready"] is False
        assert active["readiness"]["review_state"] == "active_candidate_review_required"
        assert "promotion_gate_not_ready" in active["readiness"]["blocked_by"]
        assert (
            active["source_artifacts"]["intake"]["source_ref"]
            == intake.relative_to(ROOT).as_posix()
        )
        gate = load_json(promotion_gate)
        assert gate["artifact_kind"] == "idea_to_spec_promotion_gate"
        assert gate["readiness"]["review_state"] == "idea_to_spec_promotion_blocked"
        assert "team-decision-log" not in json.dumps(active)
    finally:
        if RUN_DIR.exists():
            shutil.rmtree(RUN_DIR)


def test_product_workspace_active_candidate_preserves_legacy_prepared_seed_path() -> None:
    run_dir = RUN_DIR / "legacy_prepared_seed"
    if run_dir.exists():
        shutil.rmtree(run_dir)
    try:
        intake = run_dir / "idea_event_storming_intake.json"
        candidate_seed = run_dir / "candidate_spec_graph_seed.json"
        candidate_graph = run_dir / "candidate_spec_graph.json"
        pre_sib = run_dir / "pre_sib_coherence_report.json"
        repair_loop = run_dir / "candidate_repair_loop_report.json"
        materialized_dir = run_dir / "materialized_candidate_specs"
        materialization = run_dir / "candidate_spec_materialization_report.json"
        promotion_gate = run_dir / "idea_to_spec_promotion_gate.json"
        active_candidate = run_dir / "active_idea_to_spec_candidate.json"
        config = run_dir / "active_candidate_source_generic.json"
        write_json(
            config,
            {
                "artifact_kind": "active_idea_to_spec_candidate_source_config",
                "artifacts": {
                    "candidate_graph": candidate_graph.relative_to(ROOT).as_posix(),
                    "intake": intake.relative_to(ROOT).as_posix(),
                    "materialization": materialization.relative_to(ROOT).as_posix(),
                    "pre_sib": pre_sib.relative_to(ROOT).as_posix(),
                    "promotion_gate": promotion_gate.relative_to(ROOT).as_posix(),
                    "repair_loop": repair_loop.relative_to(ROOT).as_posix(),
                },
                "contract_ref": "specgraph.idea-to-spec.active-candidate-source-config.v0.1",
                "schema_version": 1,
            },
        )

        result = subprocess.run(
            [
                "make",
                "product-workspace-active-candidate",
                f"PYTHON={supported_python()}",
                "PRODUCT_WORKSPACE_INTAKE_SOURCE="
                "tests/fixtures/product_workspace_active_candidate/idea_event_storming_seed.json",
                f"IDEA_EVENT_STORMING_INTAKE_OUTPUT={intake.relative_to(ROOT).as_posix()}",
                "PRODUCT_WORKSPACE_CANDIDATE_SEED_OUTPUT="
                f"{candidate_seed.relative_to(ROOT).as_posix()}",
                f"CANDIDATE_SPEC_GRAPH_OUTPUT={candidate_graph.relative_to(ROOT).as_posix()}",
                f"PRE_SIB_COHERENCE_OUTPUT={pre_sib.relative_to(ROOT).as_posix()}",
                f"CANDIDATE_REPAIR_LOOP_OUTPUT={repair_loop.relative_to(ROOT).as_posix()}",
                "CANDIDATE_SPEC_MATERIALIZATION_OUTPUT_DIR="
                f"{materialized_dir.relative_to(ROOT).as_posix()}",
                "CANDIDATE_SPEC_MATERIALIZATION_OUTPUT="
                f"{materialization.relative_to(ROOT).as_posix()}",
                f"IDEA_TO_SPEC_PROMOTION_GATE_OUTPUT={promotion_gate.relative_to(ROOT).as_posix()}",
                "ACTIVE_IDEA_TO_SPEC_CANDIDATE_OUTPUT="
                f"{active_candidate.relative_to(ROOT).as_posix()}",
                f"PRODUCT_WORKSPACE_ACTIVE_CANDIDATE_CONFIG={config.relative_to(ROOT).as_posix()}",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, result.stderr
        intake_payload = load_json(intake)
        assert "source_intake" not in intake_payload
        active = load_json(active_candidate)
        assert active["artifact_kind"] == "active_idea_to_spec_candidate"
        assert active["candidate"]["candidate_id"] == "team-decision-log"
        assert active["candidate"]["display_name"] == "Team Decision Log"
        assert active["candidate"]["public_route"] == "/team-decision-log"
    finally:
        if run_dir.exists():
            shutil.rmtree(run_dir)
