"""Product workspace next moves stay within the selected project graph."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "product_workspace_next_moves.py"


def write_workspace(root: Path, *, profile: str = "product_workspace") -> None:
    (root / "specs" / "nodes").mkdir(parents=True)
    (root / "specgraph.project.yaml").write_text(
        json.dumps(
            {
                "artifact_kind": "specgraph_project_config",
                "schema_version": 1,
                "project_id": "zeusus",
                "display_name": "Zeusus",
                "governance_profile": profile,
                "workspace": {
                    "specs_root": "specs/",
                    "proposals_root": "docs/proposals/",
                    "runs_root": "runs/",
                    "publish_root": "projects/zeusus/",
                },
                "supervisor": {
                    "allow_project_spec_refinement": True,
                    "allow_project_proposals": True,
                    "allow_project_retrospectives": True,
                    "allow_core_policy_mutation": False,
                    "allow_core_tooling_mutation": False,
                    "allow_self_evolution_proposals": False,
                },
            }
        ),
        encoding="utf-8",
    )


def write_spec(
    root: Path,
    spec_id: str,
    *,
    status: str,
    refines: str = "",
    gate_state: str = "none",
) -> None:
    node = {
        "id": spec_id,
        "title": spec_id,
        "kind": "spec",
        "status": status,
        "maturity": 0.4,
        "gate_state": gate_state,
        "allowed_paths": [f"specs/nodes/{spec_id}.yaml"],
    }
    if refines:
        node["refines"] = [refines]
    (root / "specs" / "nodes" / f"{spec_id}.yaml").write_text(json.dumps(node), encoding="utf-8")


def run_advisor(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--workspace-root", str(root), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_product_next_move_reads_only_project_specs_and_writes_advisory(
    tmp_path: Path,
) -> None:
    write_workspace(tmp_path)
    write_spec(tmp_path, "ZEU-SPEC-0003", status="specified")
    before = (tmp_path / "specs" / "nodes" / "ZEU-SPEC-0003.yaml").read_bytes()

    result = run_advisor(tmp_path)

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["project"]["project_id"] == "zeusus"
    assert report["recommended_next_move"]["spec_id"] == "ZEU-SPEC-0003"
    assert report["recommended_next_move"]["next_gap"] == "targeted_refinement"
    assert report["input_contract"]["required"] == [
        "specgraph.project.yaml",
        "specs/nodes/",
    ]
    assert report["input_contract"]["scanned"] == ["specs/nodes/*.yaml"]
    assert report["canonical_mutations_allowed"] is False
    assert report["tracked_artifacts_written"] is False
    assert (
        json.loads((tmp_path / "runs" / "product_workspace_next_moves.json").read_text()) == report
    )
    assert (tmp_path / "specs" / "nodes" / "ZEU-SPEC-0003.yaml").read_bytes() == before
    assert not (tmp_path / "tools").exists()


def test_product_next_move_exposes_core_id_block_in_scoped_branch(tmp_path: Path) -> None:
    write_workspace(tmp_path)
    write_spec(tmp_path, "ZEU-SPEC-0003", status="reviewed")
    write_spec(tmp_path, "SG-SPEC-0001", status="specified", refines="ZEU-SPEC-0003")

    result = run_advisor(tmp_path, "--target-spec", "ZEU-SPEC-0003")

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["current_scene"] == "governance_blocked"
    assert report["recommended_next_move_kind"] == "none"
    assert report["blocked_moves"][0]["spec_id"] == "SG-SPEC-0001"
    assert report["blocked_moves"][0]["blocked_by"] == ["blocked_by_governance_profile"]
    assert report["blocked_moves"][0]["command_hint"].startswith("Resolve governance")


def test_product_next_move_prioritizes_pending_gate(tmp_path: Path) -> None:
    write_workspace(tmp_path)
    write_spec(tmp_path, "ZEU-SPEC-0001", status="outlined")
    write_spec(
        tmp_path,
        "ZEU-SPEC-0002",
        status="specified",
        gate_state="review_pending",
    )

    result = run_advisor(tmp_path)

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["current_scene"] == "review_gate"
    assert report["recommended_next_move"]["spec_id"] == "ZEU-SPEC-0002"
    assert report["recommended_next_move"]["next_gap"] == "review_exact_gate_candidate"


@pytest.mark.parametrize("profile", ["self_hosted_bootstrap", "unknown_profile"])
def test_product_next_move_rejects_non_product_profile(tmp_path: Path, profile: str) -> None:
    write_workspace(tmp_path, profile=profile)
    write_spec(tmp_path, "ZEU-SPEC-0003", status="specified")

    result = run_advisor(tmp_path)

    assert result.returncode != 0
    assert "product_workspace" in result.stderr
    assert not (tmp_path / "runs" / "product_workspace_next_moves.json").exists()


def test_product_next_move_rejects_unknown_scope(tmp_path: Path) -> None:
    write_workspace(tmp_path)
    write_spec(tmp_path, "ZEU-SPEC-0003", status="specified")

    result = run_advisor(tmp_path, "--target-spec", "ZEU-SPEC-0999")

    assert result.returncode != 0
    assert "ZEU-SPEC-0999" in result.stderr
    assert not (tmp_path / "runs" / "product_workspace_next_moves.json").exists()


def test_product_next_move_rejects_malformed_node(tmp_path: Path) -> None:
    write_workspace(tmp_path)
    (tmp_path / "specs" / "nodes" / "ZEU-SPEC-0001.yaml").write_text(
        "- not-a-spec-mapping\n", encoding="utf-8"
    )

    result = run_advisor(tmp_path)

    assert result.returncode != 0
    assert "canonical spec nodes must be mappings" in result.stderr
    assert not (tmp_path / "runs" / "product_workspace_next_moves.json").exists()
