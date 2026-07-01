"""Run a real-idea smoke flow in one repository-local directory."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
from pathlib import Path

import real_idea_smoke_summary

ROOT = Path(__file__).resolve().parents[1]
SMOKE_OUTPUT_FILES = (
    ("USER_IDEA_RAW_INPUT_OUTPUT", "local_operator_user_idea_raw_input.json"),
    ("USER_IDEA_INTAKE_SESSION_OUTPUT", "user_idea_intake_session.json"),
    ("USER_IDEA_INTAKE_SESSION_SOURCE_OUTPUT", "user_idea_intake_source.json"),
    ("USER_IDEA_INTAKE_INTERVIEW_REPORT_OUTPUT", "user_idea_intake_interview_report.json"),
    (
        "CLARIFIED_USER_IDEA_INTAKE_SESSION_OUTPUT",
        "clarified_user_idea_intake_session.json",
    ),
    (
        "INTAKE_SESSION_CANDIDATE_SOURCE_REPORT_OUTPUT",
        "intake_session_candidate_source_report.json",
    ),
    ("USER_IDEA_EVENT_STORMING_SEED_OUTPUT", "idea_event_storming_seed.json"),
    ("IDEA_EVENT_STORMING_INTAKE_OUTPUT", "idea_event_storming_intake.json"),
    ("PRODUCT_WORKSPACE_CANDIDATE_SEED_OUTPUT", "candidate_spec_graph_seed.json"),
    ("CANDIDATE_SPEC_GRAPH_OUTPUT", "candidate_spec_graph.json"),
    ("PRE_SIB_COHERENCE_OUTPUT", "pre_sib_coherence_report.json"),
    ("CANDIDATE_REPAIR_LOOP_OUTPUT", "candidate_repair_loop_report.json"),
    ("IDEA_TO_SPEC_CLARIFICATION_OUTPUT", "idea_to_spec_clarification_requests.json"),
    ("CANDIDATE_SPEC_MATERIALIZATION_OUTPUT", "candidate_spec_materialization_report.json"),
    ("IDEA_TO_SPEC_PROMOTION_GATE_OUTPUT", "idea_to_spec_promotion_gate.json"),
    ("ACTIVE_IDEA_TO_SPEC_CANDIDATE_OUTPUT", "active_idea_to_spec_candidate.json"),
)
SMOKE_OUTPUT_DIRS = (("CANDIDATE_SPEC_MATERIALIZATION_OUTPUT_DIR", "materialized_candidate_specs"),)
DERIVED_REPAIR_OUTPUT_NAMES = (
    "idea_to_spec_clarification_answers.json",
    "product_ontology_gap_review_decisions.json",
    "idea_to_spec_answer_rerun_input.json",
    "idea_to_spec_rerun_preview.json",
    "idea_to_spec_rerun_materialization.json",
    "idea_to_spec_repair_session.json",
    "repaired_candidate_promotion_handoff_report.json",
    "repaired_candidate_spec_graph.json",
    "repaired_pre_sib_coherence_report.json",
    "repaired_candidate_repair_loop_report.json",
    "repaired_candidate_spec_materialization_report.json",
    "repaired_idea_to_spec_promotion_gate.json",
    "repaired_active_idea_to_spec_candidate.json",
    "repaired_idea_to_spec_repair_session.json",
    "idea_maturity_metrics_report.json",
    "idea_maturity_metrics_validation_report.json",
)
DERIVED_REPAIR_OUTPUT_DIRS = (
    "repaired_materialized_candidate_specs",
    "absent-post-approval",
)
RESERVED_RUN_DIRS = {"runs"}


def _repo_relative_path(value: str, *, field: str) -> tuple[str, Path]:
    path = Path(value)
    resolved = path.resolve() if path.is_absolute() else (ROOT / path).resolve()
    try:
        rel = resolved.relative_to(ROOT)
    except ValueError as exc:
        raise SystemExit(f"{field} must stay inside the SpecGraph repository: {value}") from exc
    if not rel.parts:
        raise SystemExit(f"{field} must not point to the repository root.")
    return rel.as_posix(), ROOT / rel


def _child_env() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("PRODUCT_WORKSPACE_ACTIVE_CANDIDATE_CONFIG", None)
    env.pop("ACTIVE_IDEA_TO_SPEC_CANDIDATE_CONFIG", None)
    return env


def _reject_reserved_run_dir(run_dir_ref: str) -> None:
    if run_dir_ref in RESERVED_RUN_DIRS:
        raise SystemExit(
            f"REAL_IDEA_SMOKE_RUN_DIR={run_dir_ref} is reserved for shared SpecGraph runs. "
            "Use a child directory such as runs/real_idea_smoke or runs/<id>."
        )


def _clear_managed_outputs(run_dir: Path, *, summary_output: Path) -> None:
    managed_names = [
        *(name for _, name in SMOKE_OUTPUT_FILES),
        *DERIVED_REPAIR_OUTPUT_NAMES,
        "real_idea_smoke_summary.json",
    ]
    for name in managed_names:
        (run_dir / name).unlink(missing_ok=True)
    managed_dirs = [
        *(name for _, name in SMOKE_OUTPUT_DIRS),
        *DERIVED_REPAIR_OUTPUT_DIRS,
    ]
    for name in managed_dirs:
        shutil.rmtree(run_dir / name, ignore_errors=True)
    summary_output.unlink(missing_ok=True)


def _smoke_make_args(run_dir_ref: str, *, python: str, interview_input: str) -> list[str]:
    args = [
        "make",
        "real-idea-intake-active-candidate",
        f"PYTHON={python}",
        "PRODUCT_WORKSPACE_ACTIVE_CANDIDATE_CONFIG=",
        "ACTIVE_IDEA_TO_SPEC_CANDIDATE_CONFIG=",
    ]
    args.extend(f"{var}={run_dir_ref}/{name}" for var, name in SMOKE_OUTPUT_FILES)
    args.extend(f"{var}={run_dir_ref}/{name}" for var, name in SMOKE_OUTPUT_DIRS)
    if interview_input.strip():
        args.append(f"USER_IDEA_INTAKE_INTERVIEW_INPUT={interview_input}")
    return args


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--summary-output", required=True)
    parser.add_argument("--python", default=".venv/bin/python")
    parser.add_argument("--interview-input", default="")
    parser.add_argument(
        "--preserve-existing",
        action="store_true",
        help="Do not clear managed smoke outputs before running.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    run_dir_ref, run_dir = _repo_relative_path(args.run_dir, field="REAL_IDEA_SMOKE_RUN_DIR")
    _reject_reserved_run_dir(run_dir_ref)
    _, summary_output = _repo_relative_path(
        args.summary_output,
        field="REAL_IDEA_SMOKE_SUMMARY_OUTPUT",
    )
    run_dir.mkdir(parents=True, exist_ok=True)
    if not args.preserve_existing:
        _clear_managed_outputs(run_dir, summary_output=summary_output)

    result = subprocess.run(
        _smoke_make_args(run_dir_ref, python=args.python, interview_input=args.interview_input),
        cwd=ROOT,
        env=_child_env(),
        check=False,
    )
    summary = real_idea_smoke_summary.build_summary(run_dir)
    real_idea_smoke_summary.write_json(summary, summary_output)
    print(f"{summary['status']} -> {real_idea_smoke_summary._relative_ref(summary_output)}")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
