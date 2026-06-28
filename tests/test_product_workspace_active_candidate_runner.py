from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUN_DIR = ROOT / "runs" / "test_product_workspace_active_candidate_runner"


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def copy_repo_for_make_test(tmp_path: Path) -> Path:
    destination = tmp_path / "repo"
    shutil.copytree(
        ROOT,
        destination,
        ignore=shutil.ignore_patterns(
            ".git",
            ".mypy_cache",
            ".pytest_cache",
            ".ruff_cache",
            ".venv",
            "__pycache__",
            "dist",
            "runs",
        ),
    )
    return destination


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


def test_product_workspace_active_candidate_default_paths_do_not_require_config(
    tmp_path: Path,
) -> None:
    repo = copy_repo_for_make_test(tmp_path)
    result = subprocess.run(
        [
            "make",
            "product-workspace-active-candidate",
            f"PYTHON={supported_python()}",
        ],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    active = load_json(repo / "runs" / "active_idea_to_spec_candidate.json")
    assert active["artifact_kind"] == "active_idea_to_spec_candidate"
    assert active["candidate"]["candidate_id"] == "team-decision-log"
    assert active["config_source"]["mode"] == "artifact_defaults"
    assert active["config_source"]["required"] is False
    assert active["source_derivation"]["artifact_paths_source"] == "defaults"
    assert active["source_derivation"]["config_required"] is False


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
        assert active["config_source"]["mode"] == "artifact_arguments"
        assert active["config_source"]["source_ref"] is None
        assert active["source_derivation"]["artifact_paths_source"] == "arguments"
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


def test_product_workspace_decision_backed_repair_chain_threads_ontology_decisions() -> None:
    run_dir = RUN_DIR / "decision_backed_repair_chain"
    if run_dir.exists():
        shutil.rmtree(run_dir)
    try:
        session = run_dir / "user_idea_intake_session.json"
        source = run_dir / "user_idea_intake_source.json"
        seed = run_dir / "idea_event_storming_seed.json"
        intake = run_dir / "idea_event_storming_intake.json"
        candidate_seed = run_dir / "candidate_spec_graph_seed.json"
        candidate_graph = run_dir / "candidate_spec_graph.json"
        pre_sib = run_dir / "pre_sib_coherence_report.json"
        repair_loop = run_dir / "candidate_repair_loop_report.json"
        requests = run_dir / "idea_to_spec_clarification_requests.json"
        answers = run_dir / "idea_to_spec_clarification_answers.json"
        ontology_decisions = run_dir / "product_ontology_gap_review_decisions.json"
        rerun_input = run_dir / "idea_to_spec_answer_rerun_input.json"
        rerun_preview = run_dir / "idea_to_spec_rerun_preview.json"
        rerun_materialization = run_dir / "idea_to_spec_rerun_materialization.json"
        repair_session = run_dir / "idea_to_spec_repair_session.json"
        materialized_dir = run_dir / "materialized_candidate_specs"
        materialization = run_dir / "candidate_spec_materialization_report.json"
        promotion_gate = run_dir / "idea_to_spec_promotion_gate.json"
        active_candidate = run_dir / "active_idea_to_spec_candidate.json"
        maturity_report = run_dir / "idea_maturity_metrics_report.json"
        maturity_validation = run_dir / "idea_maturity_metrics_validation_report.json"
        fake_metrics_cli = run_dir / "fake_metrics_cli.py"
        fake_metrics_cli.parent.mkdir(parents=True, exist_ok=True)
        fake_metrics_cli.write_text(
            "\n".join(
                [
                    "import json",
                    "import sys",
                    "from pathlib import Path",
                    "args = sys.argv[1:]",
                    "output = Path(args[args.index('--output') + 1])",
                    "output.parent.mkdir(parents=True, exist_ok=True)",
                    "output.write_text(json.dumps({",
                    "  'artifact_kind': 'idea_maturity_metrics_validation_report',",
                    "  'metric_pack_id': 'idea_to_spec_maturity',",
                    "  'summary': {'status': 'ok'},",
                    "  'reports': [{'path': args[2], 'status': 'ok', 'diagnostics': []}],",
                    "}), encoding='utf-8')",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                "make",
                "product-workspace-decision-backed-repair-chain",
                f"PYTHON={supported_python()}",
                "PRODUCT_WORKSPACE_IDEA_SOURCE=tests/fixtures/product_workspace_active_candidate/raw_idea_source.json",
                f"USER_IDEA_INTAKE_SESSION_OUTPUT={session.relative_to(ROOT).as_posix()}",
                f"USER_IDEA_INTAKE_SESSION_SOURCE_OUTPUT={source.relative_to(ROOT).as_posix()}",
                f"USER_IDEA_EVENT_STORMING_SEED_OUTPUT={seed.relative_to(ROOT).as_posix()}",
                f"IDEA_EVENT_STORMING_INTAKE_OUTPUT={intake.relative_to(ROOT).as_posix()}",
                "PRODUCT_WORKSPACE_CANDIDATE_SEED_OUTPUT="
                f"{candidate_seed.relative_to(ROOT).as_posix()}",
                f"CANDIDATE_SPEC_GRAPH_OUTPUT={candidate_graph.relative_to(ROOT).as_posix()}",
                f"PRE_SIB_COHERENCE_OUTPUT={pre_sib.relative_to(ROOT).as_posix()}",
                f"CANDIDATE_REPAIR_LOOP_OUTPUT={repair_loop.relative_to(ROOT).as_posix()}",
                f"IDEA_TO_SPEC_CLARIFICATION_OUTPUT={requests.relative_to(ROOT).as_posix()}",
                f"IDEA_TO_SPEC_CLARIFICATION_ANSWERS_OUTPUT={answers.relative_to(ROOT).as_posix()}",
                "PRODUCT_ONTOLOGY_GAP_REVIEW_DECISIONS_OUTPUT="
                f"{ontology_decisions.relative_to(ROOT).as_posix()}",
                "IDEA_TO_SPEC_ANSWER_RERUN_INPUT_OUTPUT="
                f"{rerun_input.relative_to(ROOT).as_posix()}",
                f"IDEA_TO_SPEC_RERUN_PREVIEW_OUTPUT={rerun_preview.relative_to(ROOT).as_posix()}",
                "IDEA_TO_SPEC_RERUN_MATERIALIZATION_OUTPUT="
                f"{rerun_materialization.relative_to(ROOT).as_posix()}",
                f"IDEA_TO_SPEC_REPAIR_SESSION_OUTPUT={repair_session.relative_to(ROOT).as_posix()}",
                "CANDIDATE_SPEC_MATERIALIZATION_OUTPUT_DIR="
                f"{materialized_dir.relative_to(ROOT).as_posix()}",
                "CANDIDATE_SPEC_MATERIALIZATION_OUTPUT="
                f"{materialization.relative_to(ROOT).as_posix()}",
                f"IDEA_TO_SPEC_PROMOTION_GATE_OUTPUT={promotion_gate.relative_to(ROOT).as_posix()}",
                "ACTIVE_IDEA_TO_SPEC_CANDIDATE_OUTPUT="
                f"{active_candidate.relative_to(ROOT).as_posix()}",
                f"IDEA_MATURITY_METRICS_OUTPUT={maturity_report.relative_to(ROOT).as_posix()}",
                "IDEA_MATURITY_METRICS_VALIDATION_OUTPUT="
                f"{maturity_validation.relative_to(ROOT).as_posix()}",
                f"METRICS_CLI={sys.executable} {fake_metrics_cli.relative_to(ROOT).as_posix()}",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0, result.stderr
        assert ontology_decisions.is_file()
        assert rerun_input.is_file()
        assert rerun_preview.is_file()
        assert rerun_materialization.is_file()
        assert repair_session.is_file()
        assert maturity_report.is_file()
        assert maturity_validation.is_file()
        rerun_input_payload = load_json(rerun_input)
        assert rerun_input_payload["summary"]["ontology_decision_count"] == 1
        assert (
            rerun_input_payload["summary"]["ontology_decision_source"]
            == "product_ontology_gap_review_decisions"
        )
        assert (
            rerun_input_payload["source_artifacts"]["product_ontology_gap_review_decisions"][
                "source_ref"
            ]
            == ontology_decisions.relative_to(ROOT).as_posix()
        )
        preview = load_json(rerun_preview)
        assert preview["summary"]["resolved_ontology_gap_count"] == 1
        materialized = load_json(rerun_materialization)
        assert materialized["summary"]["removed_gap_count"] == 1
        journal = load_json(repair_session)
        assert journal["artifact_kind"] == "idea_to_spec_repair_session_journal"
        assert journal["summary"]["ontology_decision_count"] == 1
        assert journal["summary"]["unresolved_ontology_gap_count"] == 10
        maturity = load_json(maturity_report)
        assert maturity["artifact_kind"] == "idea_maturity_metrics_report"
        validation = load_json(maturity_validation)
        assert validation["summary"]["status"] == "ok"
        assert (
            journal["source_artifacts"]["rerun_materialization"]["source_ref"]
            == rerun_materialization.relative_to(ROOT).as_posix()
        )
    finally:
        if run_dir.exists():
            shutil.rmtree(run_dir)


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
