"""Run a real-idea smoke flow in one repository-local directory."""

from __future__ import annotations

import argparse
import os
import subprocess
from pathlib import Path

import real_idea_smoke_summary

ROOT = Path(__file__).resolve().parents[1]


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


def _smoke_make_args(run_dir_ref: str, *, python: str, interview_input: str) -> list[str]:
    args = [
        "make",
        "real-idea-intake-active-candidate",
        f"PYTHON={python}",
        "PRODUCT_WORKSPACE_ACTIVE_CANDIDATE_CONFIG=",
        "ACTIVE_IDEA_TO_SPEC_CANDIDATE_CONFIG=",
        f"USER_IDEA_RAW_INPUT_OUTPUT={run_dir_ref}/local_operator_user_idea_raw_input.json",
        f"USER_IDEA_INTAKE_SESSION_OUTPUT={run_dir_ref}/user_idea_intake_session.json",
        f"USER_IDEA_INTAKE_SESSION_SOURCE_OUTPUT={run_dir_ref}/user_idea_intake_source.json",
        f"USER_IDEA_INTAKE_INTERVIEW_REPORT_OUTPUT={run_dir_ref}/user_idea_intake_interview_report.json",
        (
            "CLARIFIED_USER_IDEA_INTAKE_SESSION_OUTPUT="
            f"{run_dir_ref}/clarified_user_idea_intake_session.json"
        ),
        (
            "INTAKE_SESSION_CANDIDATE_SOURCE_REPORT_OUTPUT="
            f"{run_dir_ref}/intake_session_candidate_source_report.json"
        ),
        f"USER_IDEA_EVENT_STORMING_SEED_OUTPUT={run_dir_ref}/idea_event_storming_seed.json",
        f"IDEA_EVENT_STORMING_INTAKE_OUTPUT={run_dir_ref}/idea_event_storming_intake.json",
        f"PRODUCT_WORKSPACE_CANDIDATE_SEED_OUTPUT={run_dir_ref}/candidate_spec_graph_seed.json",
        f"CANDIDATE_SPEC_GRAPH_OUTPUT={run_dir_ref}/candidate_spec_graph.json",
        f"PRE_SIB_COHERENCE_OUTPUT={run_dir_ref}/pre_sib_coherence_report.json",
        f"CANDIDATE_REPAIR_LOOP_OUTPUT={run_dir_ref}/candidate_repair_loop_report.json",
        f"IDEA_TO_SPEC_CLARIFICATION_OUTPUT={run_dir_ref}/idea_to_spec_clarification_requests.json",
        f"CANDIDATE_SPEC_MATERIALIZATION_OUTPUT_DIR={run_dir_ref}/materialized_candidate_specs",
        (
            "CANDIDATE_SPEC_MATERIALIZATION_OUTPUT="
            f"{run_dir_ref}/candidate_spec_materialization_report.json"
        ),
        f"IDEA_TO_SPEC_PROMOTION_GATE_OUTPUT={run_dir_ref}/idea_to_spec_promotion_gate.json",
        f"ACTIVE_IDEA_TO_SPEC_CANDIDATE_OUTPUT={run_dir_ref}/active_idea_to_spec_candidate.json",
    ]
    if interview_input.strip():
        args.append(f"USER_IDEA_INTAKE_INTERVIEW_INPUT={interview_input}")
    return args


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--summary-output", required=True)
    parser.add_argument("--python", default=".venv/bin/python")
    parser.add_argument("--interview-input", default="")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    run_dir_ref, run_dir = _repo_relative_path(args.run_dir, field="REAL_IDEA_SMOKE_RUN_DIR")
    _, summary_output = _repo_relative_path(
        args.summary_output,
        field="REAL_IDEA_SMOKE_SUMMARY_OUTPUT",
    )
    run_dir.mkdir(parents=True, exist_ok=True)

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
