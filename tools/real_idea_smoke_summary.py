"""Summarize real-idea smoke artifacts without exposing raw idea text."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROPOSAL_ID = "0190"
SCHEMA_VERSION = 1
CONTRACT_REF = "specgraph.idea-to-spec.real-idea-smoke-summary.v0.1"


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _text(value: Any, default: str = "") -> str:
    return value.strip() if isinstance(value, str) and value.strip() else default


def _relative_ref(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_optional(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def write_json(payload: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _artifact_entry(run_dir: Path, name: str) -> dict[str, Any]:
    path = run_dir / name
    payload = load_optional(path)
    summary = _dict(payload.get("summary"))
    readiness = _dict(payload.get("readiness"))
    return {
        "path": _relative_ref(path),
        "present": path.exists(),
        "artifact_kind": payload.get("artifact_kind"),
        "status": _text(
            summary.get("status"),
            _text(payload.get("status"), _text(readiness.get("review_state"))),
        ),
        "ready": readiness.get("ready"),
        "summary": summary,
    }


def build_summary(run_dir: Path) -> dict[str, Any]:
    artifacts = {
        "intake_session": _artifact_entry(run_dir, "user_idea_intake_session.json"),
        "candidate_source": _artifact_entry(run_dir, "user_idea_intake_source.json"),
        "event_storming_seed": _artifact_entry(run_dir, "idea_event_storming_seed.json"),
        "event_storming_intake": _artifact_entry(run_dir, "idea_event_storming_intake.json"),
        "candidate_graph": _artifact_entry(run_dir, "candidate_spec_graph.json"),
        "pre_sib": _artifact_entry(run_dir, "pre_sib_coherence_report.json"),
        "repair_loop": _artifact_entry(run_dir, "candidate_repair_loop_report.json"),
        "clarification_requests": _artifact_entry(
            run_dir, "idea_to_spec_clarification_requests.json"
        ),
        "materialization": _artifact_entry(run_dir, "candidate_spec_materialization_report.json"),
        "promotion_gate": _artifact_entry(run_dir, "idea_to_spec_promotion_gate.json"),
        "active_candidate": _artifact_entry(run_dir, "active_idea_to_spec_candidate.json"),
    }
    active_summary = _dict(artifacts["active_candidate"].get("summary"))
    missing = [name for name, artifact in artifacts.items() if not artifact["present"]]
    status = _text(active_summary.get("status"), "incomplete")
    return {
        "artifact_kind": "real_idea_smoke_summary",
        "schema_version": SCHEMA_VERSION,
        "contract_ref": CONTRACT_REF,
        "proposal_id": PROPOSAL_ID,
        "generated_at": _now_iso(),
        "run_dir": _relative_ref(run_dir),
        "status": status,
        "summary": {
            "status": status,
            "candidate_id": active_summary.get("candidate_id"),
            "workspace_route": active_summary.get("workspace_route"),
            "missing_artifact_count": len(missing),
            "active_candidate_ready": status == "active_candidate_ready",
            "promotion_path_count": active_summary.get("promotion_path_count", 0),
            "source_artifact_count": active_summary.get("source_artifact_count", 0),
        },
        "artifacts": artifacts,
        "missing_artifacts": missing,
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


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = build_summary(args.run_dir)
    write_json(summary, args.output)
    print(f"{summary['status']} -> {_relative_ref(args.output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
