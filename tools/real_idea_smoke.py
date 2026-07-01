"""Run a real-idea smoke flow in one repository-local directory."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

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
    "real_idea_smoke_session_state_report.json",
    "real_idea_answer_template.json",
    "real_idea_answer_authoring_report.json",
    "real_idea_answer_set.json",
    "specspace_real_idea_answer_import_preview.json",
    "real_idea_answer_continuation_report.json",
)
DERIVED_REPAIR_OUTPUT_DIRS = (
    "repaired_materialized_candidate_specs",
    "absent-post-approval",
)
RESERVED_RUN_DIRS = {"runs"}
INTAKE_STATE_OUTPUT_NAMES = {
    "local_operator_user_idea_raw_input.json",
    "user_idea_intake_session.json",
    "user_idea_intake_interview_report.json",
    "idea_intake_clarification_requests.json",
    "idea_intake_clarification_answers.json",
    "idea_intake_answer_rerun_input.json",
    "local_operator_clarified_user_idea_raw_input.json",
    "clarified_user_idea_intake_session.json",
    "idea_intake_clarification_rerun_report.json",
}
SESSION_STATE_REPORT_NAME = "real_idea_smoke_session_state_report.json"


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
    env.pop("REAL_IDEA_INTAKE_REFRESH", None)
    return env


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _text(value: Any, default: str = "") -> str:
    return value.strip() if isinstance(value, str) and value.strip() else default


def _load_optional(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _relative_ref(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


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


def _clear_downstream_outputs(run_dir: Path, *, summary_output: Path) -> None:
    managed_names = [
        name for _, name in SMOKE_OUTPUT_FILES if name not in INTAKE_STATE_OUTPUT_NAMES
    ]
    managed_names.extend(DERIVED_REPAIR_OUTPUT_NAMES)
    managed_names.append("real_idea_smoke_summary.json")
    for name in managed_names:
        (run_dir / name).unlink(missing_ok=True)
    for _, name in SMOKE_OUTPUT_DIRS:
        shutil.rmtree(run_dir / name, ignore_errors=True)
    for name in DERIVED_REPAIR_OUTPUT_DIRS:
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


def _clarification_make_args(
    run_dir_ref: str,
    *,
    python: str,
    answers_input: str,
) -> list[list[str]]:
    common = [
        f"PYTHON={python}",
        f"USER_IDEA_RAW_INPUT_OUTPUT={run_dir_ref}/local_operator_user_idea_raw_input.json",
        f"USER_IDEA_INTAKE_SESSION_OUTPUT={run_dir_ref}/user_idea_intake_session.json",
        f"USER_IDEA_INTAKE_SESSION_SOURCE_OUTPUT={run_dir_ref}/user_idea_intake_source.json",
        f"USER_IDEA_INTAKE_INTERVIEW_REPORT_OUTPUT={run_dir_ref}/user_idea_intake_interview_report.json",
        f"IDEA_INTAKE_CLARIFICATION_REQUESTS_OUTPUT={run_dir_ref}/idea_intake_clarification_requests.json",
        f"IDEA_INTAKE_CLARIFICATION_ANSWERS_OUTPUT={run_dir_ref}/idea_intake_clarification_answers.json",
        f"IDEA_INTAKE_ANSWER_RERUN_INPUT_OUTPUT={run_dir_ref}/idea_intake_answer_rerun_input.json",
        f"CLARIFIED_USER_IDEA_RAW_INPUT_OUTPUT={run_dir_ref}/local_operator_clarified_user_idea_raw_input.json",
        f"CLARIFIED_USER_IDEA_INTAKE_SESSION_OUTPUT={run_dir_ref}/clarified_user_idea_intake_session.json",
        f"CLARIFIED_USER_IDEA_INTAKE_SOURCE_OUTPUT={run_dir_ref}/clarified_user_idea_intake_source.json",
        f"IDEA_INTAKE_CLARIFICATION_RERUN_REPORT_OUTPUT={run_dir_ref}/idea_intake_clarification_rerun_report.json",
    ]
    return [
        ["make", "real-idea-intake-clarification-requests", *common],
        [
            "make",
            "real-idea-intake-clarification-rerun",
            *common,
            f"IDEA_INTAKE_CLARIFICATION_ANSWERS_INPUT={answers_input}",
        ],
    ]


def _artifact_state(path: Path) -> dict[str, Any]:
    payload = _load_optional(path)
    readiness = _dict(payload.get("readiness"))
    summary = _dict(payload.get("summary"))
    return {
        "path": _relative_ref(path),
        "present": path.exists(),
        "artifact_kind": payload.get("artifact_kind"),
        "contract_ref": payload.get("contract_ref"),
        "review_state": _text(readiness.get("review_state"), _text(summary.get("status"))),
        "ready": readiness.get("ready"),
    }


def _session_state_report(
    run_dir: Path,
    *,
    answers_input: str,
    status: str,
    continuation_path: str,
    blocked_by: list[str] | None = None,
    next_action: str = "",
) -> dict[str, Any]:
    original = _artifact_state(run_dir / "user_idea_intake_session.json")
    clarified = _artifact_state(run_dir / "clarified_user_idea_intake_session.json")
    selected = clarified if clarified["present"] else original
    answer_path = None
    if answers_input.strip():
        raw_path = Path(answers_input)
        answer_path = raw_path if raw_path.is_absolute() else (ROOT / raw_path)
    return {
        "artifact_kind": "real_idea_smoke_session_state_report",
        "schema_version": 1,
        "contract_ref": "specgraph.idea-to-spec.real-idea-smoke-session-state.v0.1",
        "proposal_id": "0193",
        "run_dir": _relative_ref(run_dir),
        "status": status,
        "summary": {
            "status": status,
            "continuation_path": continuation_path,
            "selected_session": "clarified" if clarified["present"] else "original",
            "selected_review_state": selected.get("review_state"),
            "answer_input_present": bool(answer_path and answer_path.exists()),
            "blocked_count": len(blocked_by or []),
            "next_action": next_action,
        },
        "source_refs": {
            "original_intake_session": _relative_ref(run_dir / "user_idea_intake_session.json"),
            "clarified_intake_session": _relative_ref(
                run_dir / "clarified_user_idea_intake_session.json"
            ),
            "clarification_requests": _relative_ref(
                run_dir / "idea_intake_clarification_requests.json"
            ),
            "clarification_answers_input": _relative_ref(answer_path) if answer_path else None,
            "validated_answers": _relative_ref(run_dir / "idea_intake_clarification_answers.json"),
        },
        "sessions": {
            "original": original,
            "clarified": clarified,
            "selected": selected,
        },
        "blocked_by": blocked_by or [],
        "next_action": next_action,
        "authority_boundary": {
            "may_execute_prompt_agent": False,
            "may_mutate_candidate_source_artifacts": False,
            "may_mutate_canonical_specs": False,
            "may_write_ontology_package": False,
            "may_accept_ontology_terms": False,
            "may_create_branch_or_commit": False,
            "may_open_pull_request": False,
        },
        "privacy_boundary": {
            "raw_idea_text_published": False,
            "raw_model_output_published": False,
            "raw_prompt_published": False,
        },
    }


def _write_session_state_report(
    run_dir: Path,
    *,
    answers_input: str,
    status: str,
    continuation_path: str,
    blocked_by: list[str] | None = None,
    next_action: str = "",
) -> None:
    _write_json(
        _session_state_report(
            run_dir,
            answers_input=answers_input,
            status=status,
            continuation_path=continuation_path,
            blocked_by=blocked_by,
            next_action=next_action,
        ),
        run_dir / SESSION_STATE_REPORT_NAME,
    )


def _prepare_continuation(
    *,
    run_dir_ref: str,
    run_dir: Path,
    python: str,
    answers_input: str,
) -> int:
    original_session = run_dir / "user_idea_intake_session.json"
    clarified_session = run_dir / "clarified_user_idea_intake_session.json"
    if not original_session.exists() and not clarified_session.exists():
        _write_session_state_report(
            run_dir,
            answers_input=answers_input,
            status="blocked",
            continuation_path="missing_intake_session",
            blocked_by=["intake_session_missing"],
            next_action="Run make real-idea-smoke first with a raw idea input.",
        )
        return 2

    clarified_payload = _load_optional(clarified_session)
    clarified_ready = _dict(clarified_payload.get("readiness")).get("ready") is True
    if clarified_session.exists() and (clarified_ready or not answers_input.strip()):
        status = "ready" if clarified_ready else "blocked"
        blocked_by = [] if clarified_ready else ["clarified_intake_session_not_ready"]
        next_action = (
            "Continue active candidate generation from clarified intake session."
            if clarified_ready
            else "Provide corrected REAL_IDEA_SMOKE_CLARIFICATION_ANSWERS_INPUT=<json>."
        )
        _write_session_state_report(
            run_dir,
            answers_input=answers_input,
            status=status,
            continuation_path="use_existing_clarified_session",
            blocked_by=blocked_by,
            next_action=next_action,
        )
        return 0 if clarified_ready else 2

    original_payload = _load_optional(original_session)
    review_state = _text(_dict(original_payload.get("readiness")).get("review_state"))
    if review_state != "needs_clarification":
        _write_session_state_report(
            run_dir,
            answers_input=answers_input,
            status="ready",
            continuation_path="use_original_session",
            next_action="Continue active candidate generation from the existing intake session.",
        )
        return 0

    if not answers_input.strip():
        result = subprocess.run(
            _clarification_make_args(run_dir_ref, python=python, answers_input="")[0],
            cwd=ROOT,
            env=_child_env(),
            check=False,
        )
        _write_session_state_report(
            run_dir,
            answers_input=answers_input,
            status="blocked",
            continuation_path="await_clarification_answers",
            blocked_by=["clarification_answers_input_missing"],
            next_action=(
                "Provide REAL_IDEA_SMOKE_CLARIFICATION_ANSWERS_INPUT=<json> "
                "and run make real-idea-smoke-continue."
            ),
        )
        return result.returncode or 2

    for make_args in _clarification_make_args(
        run_dir_ref,
        python=python,
        answers_input=answers_input,
    ):
        result = subprocess.run(make_args, cwd=ROOT, env=_child_env(), check=False)
        if result.returncode != 0:
            _write_session_state_report(
                run_dir,
                answers_input=answers_input,
                status="blocked",
                continuation_path="apply_clarification_answers",
                blocked_by=["clarification_rerun_failed"],
                next_action="Inspect the clarification answer set and rerun continuation.",
            )
            return result.returncode

    _write_session_state_report(
        run_dir,
        answers_input=answers_input,
        status="ready",
        continuation_path="applied_clarification_answers",
        next_action="Continue active candidate generation from clarified intake session.",
    )
    return 0


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
    parser.add_argument(
        "--continue-existing",
        action="store_true",
        help="Preserve intake state and continue after clarification when possible.",
    )
    parser.add_argument("--clarification-answers-input", default="")
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
    if args.continue_existing:
        _clear_downstream_outputs(run_dir, summary_output=summary_output)
        continuation_result = _prepare_continuation(
            run_dir_ref=run_dir_ref,
            run_dir=run_dir,
            python=args.python,
            answers_input=args.clarification_answers_input,
        )
        if continuation_result != 0:
            summary = real_idea_smoke_summary.build_summary(run_dir)
            real_idea_smoke_summary.write_json(summary, summary_output)
            print(f"{summary['status']} -> {real_idea_smoke_summary._relative_ref(summary_output)}")
            return continuation_result
    elif not args.preserve_existing:
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
