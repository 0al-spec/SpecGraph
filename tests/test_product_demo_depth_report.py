from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "product_demo_depth_report.py"


def load_module():
    spec = importlib.util.spec_from_file_location("product_demo_depth_report_under_test", TOOL_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def intake() -> dict[str, object]:
    return {
        "artifact_kind": "idea_event_storming_intake",
        "event_storming": {
            "actors": [{"id": "actor.household-member", "name": "Household Member"}],
            "commands": [{"id": "command.record-pantry-item", "name": "Record Pantry Item"}],
            "domain_events": [{"id": "event.pantry-item-recorded", "name": "Pantry Item Recorded"}],
            "policies": [{"id": "policy.expiration-review", "name": "Expiration Review Policy"}],
            "constraints": [
                {"id": "constraint.local-storage", "statement": "Store pantry data locally."}
            ],
        },
    }


def candidate_graph() -> dict[str, object]:
    return {
        "artifact_kind": "candidate_spec_graph",
        "nodes": [
            {
                "id": "candidate-spec.record-pantry-item",
                "title": "Record Pantry Item",
                "requirements": [{"id": "req.record-pantry-item"}],
                "acceptance_criteria": [{"id": "ac.record-pantry-item"}],
            }
        ],
        "edges": [
            {
                "id": "edge.actor-command",
                "from": "actor.household-member",
                "to": "command.record-pantry-item",
                "relation": "actor_triggers_command",
            }
        ],
    }


def candidate_overview() -> dict[str, object]:
    return {
        "artifact_kind": "candidate_overview",
        "summary": {"status": "candidate_overview_ready"},
        "sections": {
            "event_storming": {
                "actors": {"count": 1},
                "domain_events": {"count": 1},
            },
            "topology": {"workflow_edge_count": 1},
        },
    }


def idea_maturity() -> dict[str, object]:
    return {
        "artifact_kind": "idea_maturity_metrics_report",
        "status": "ready",
        "summary": {"status": "ready", "lifecycle_state": "candidate_review"},
    }


def test_product_demo_depth_report_passes_baseline(tmp_path: Path) -> None:
    module = load_module()
    run_dir = tmp_path / "runs" / "demo"
    paths = {
        "intake": run_dir / "idea_event_storming_intake.json",
        "graph": run_dir / "candidate_spec_graph.json",
        "overview": run_dir / "candidate_overview.json",
        "maturity": run_dir / "idea_maturity_metrics_report.json",
    }
    write_json(paths["intake"], intake())
    write_json(paths["graph"], candidate_graph())
    write_json(paths["overview"], candidate_overview())
    write_json(paths["maturity"], idea_maturity())

    report = module.build_depth_report(
        run_dir=run_dir,
        intake_path=paths["intake"],
        candidate_graph_path=paths["graph"],
        candidate_overview_path=paths["overview"],
        idea_maturity_path=paths["maturity"],
    )

    assert report["artifact_kind"] == "product_demo_depth_report"
    assert report["proposal_id"] == "0204"
    assert report["summary"]["status"] == "depth_baseline_met"
    assert report["summary"]["actor_count"] == 1
    assert report["summary"]["domain_event_count"] == 1
    assert report["summary"]["workflow_edge_count"] == 1
    assert report["findings"] == []
    assert report["authority_boundary"]["may_execute_specgraph"] is False
    assert report["privacy_boundary"]["raw_idea_text_published"] is False


def test_product_demo_depth_report_blocks_shallow_demo(tmp_path: Path) -> None:
    module = load_module()
    run_dir = tmp_path / "runs" / "demo"
    graph_path = run_dir / "candidate_spec_graph.json"
    write_json(run_dir / "idea_event_storming_intake.json", {"event_storming": {}})
    write_json(graph_path, {"nodes": [], "edges": []})

    report = module.build_depth_report(
        run_dir=run_dir,
        intake_path=run_dir / "idea_event_storming_intake.json",
        candidate_graph_path=graph_path,
        candidate_overview_path=run_dir / "missing_candidate_overview.json",
        idea_maturity_path=run_dir / "missing_idea_maturity.json",
    )

    assert report["summary"]["status"] == "depth_baseline_failed"
    finding_ids = {finding["finding_id"] for finding in report["findings"]}
    assert "product_demo_depth_actor_count_missing" in finding_ids
    assert "product_demo_depth_domain_event_count_missing" in finding_ids
    assert "product_demo_depth_policy_count_missing" in finding_ids
    assert "product_demo_depth_workflow_edge_count_missing" in finding_ids
    assert "product_demo_depth_candidate_overview_missing" in finding_ids
    assert "product_demo_depth_idea_maturity_missing" in finding_ids


def test_product_demo_depth_report_strict_cli_fails_for_missing_depth(tmp_path: Path) -> None:
    run_dir = tmp_path / "runs" / "demo"
    write_json(run_dir / "idea_event_storming_intake.json", {"event_storming": {}})
    write_json(run_dir / "candidate_spec_graph.json", {"nodes": [], "edges": []})
    output = run_dir / "product_demo_depth_report.json"

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--run-dir",
            str(run_dir),
            "--intake",
            str(run_dir / "idea_event_storming_intake.json"),
            "--candidate-graph",
            str(run_dir / "candidate_spec_graph.json"),
            "--candidate-overview",
            str(run_dir / "candidate_overview.json"),
            "--idea-maturity",
            str(run_dir / "idea_maturity_metrics_report.json"),
            "--output",
            str(output),
            "--strict",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["summary"]["status"] == "depth_baseline_failed"
