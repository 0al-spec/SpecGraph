from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest
import yaml

TOOL = Path(__file__).resolve().parents[1] / "tools" / "implementation_contract_pack.py"
spec = importlib.util.spec_from_file_location("implementation_contract_pack", TOOL)
assert spec and spec.loader
pack = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = pack
spec.loader.exec_module(pack)


@pytest.fixture
def workspace(tmp_path):
    node = {
        "id": "ZEU-SPEC-0016",
        "kind": "spec",
        "title": "Route composition",
        "status": "linked",
        "gate_state": "none",
        "refines": ["ZEU-SPEC-0015"],
        "acceptance": ["Tracing preserves route semantics"],
        "specification": {
            "bdd_scenarios": [
                {
                    "id": "ROUTE-001",
                    "steps": [
                        "Given a route",
                        "When tracing is enabled",
                        "Then the route is unchanged",
                    ],
                }
            ],
            "observability": {
                "obligations": [
                    {
                        "id": "route-selection",
                        "event": "route.selected",
                        "boundary": "composition return",
                        "attributes": ["operation_id", "sequence"],
                        "expected_outcomes": ["selected", "no_path"],
                        "scenario_ids": ["ROUTE-001"],
                    }
                ],
                "non_interference": ["No world mutation"],
                "excluded_attributes": ["user_id"],
            },
        },
    }
    path = tmp_path / "specs/nodes/ZEU-SPEC-0016.yaml"
    path.parent.mkdir(parents=True)
    path.write_text(yaml.safe_dump(node))
    return tmp_path, path, node


def test_handoff_preserves_obligations_without_granting_execution(workspace):
    root, path, node = workspace
    before = path.read_bytes()
    result = pack.build_contract_pack(root, node["id"])
    assert result["status"] == "review_required"
    assert result["observability"] == node["specification"]["observability"]
    assert result["implementation_work_preview"]["required_tests"] == ["ROUTE-001"]
    assert result["implementation_work_preview"]["expected_evidence"] == ["route-selection"]
    assert result["canonical_mutations_allowed"] is False
    assert result["runtime_code_mutations_allowed"] is False
    assert result["evidence_status"] == "not_evaluated"
    assert result["context"]["refines"] == ["ZEU-SPEC-0015"]
    assert result["context"]["inheritance"] == "not_evaluated"
    assert path.read_bytes() == before
    assert result == pack.build_contract_pack(root, node["id"])


def test_missing_obligation_is_a_visible_blocker(workspace):
    root, path, node = workspace
    del node["specification"]["observability"]
    path.write_text(yaml.safe_dump(node))
    result = pack.build_contract_pack(root, node["id"])
    assert result["status"] == "blocked"
    assert "missing_observability_contract" in result["blockers"]


@pytest.mark.parametrize("mutation", ["duplicate", "unknown_scenario", "empty", "conflict"])
def test_invalid_obligation_cannot_be_handed_off(workspace, mutation):
    root, path, node = workspace
    contract = node["specification"]["observability"]
    item = contract["obligations"][0]
    if mutation == "duplicate":
        contract["obligations"].append(copy.deepcopy(item))
    elif mutation == "unknown_scenario":
        item["scenario_ids"] = ["UNKNOWN"]
    elif mutation == "empty":
        item["boundary"] = " "
    else:
        item["attributes"].append("user_id")
    path.write_text(yaml.safe_dump(node))
    with pytest.raises(ValueError):
        pack.build_contract_pack(root, node["id"])


def test_pending_spec_gate_stays_blocked(workspace):
    root, path, node = workspace
    node["gate_state"] = "review_pending"
    path.write_text(yaml.safe_dump(node))
    assert "source_gate:review_pending" in pack.build_contract_pack(root, node["id"])["blockers"]


def test_source_change_invalidates_pinned_pack(workspace):
    root, path, node = workspace
    original = pack.build_contract_pack(root, node["id"])
    path.write_text(path.read_text() + "\n# changed revision\n")
    assert pack.build_contract_pack(root, node["id"])["source"] != original["source"]


def test_absent_gate_state_uses_supervisor_default(workspace):
    root, path, node = workspace
    del node["gate_state"]
    path.write_text(yaml.safe_dump(node))
    result = pack.build_contract_pack(root, node["id"])
    assert result["source"]["gate_state"] == "none"
    assert result["status"] == "review_required"


def test_repeated_ordered_scenario_steps_are_preserved(workspace):
    root, path, node = workspace
    node["specification"]["bdd_scenarios"][0]["steps"] = ["When retrying", "When retrying"]
    path.write_text(yaml.safe_dump(node))
    result = pack.build_contract_pack(root, node["id"])
    steps = result["specification"]["bdd_scenarios"][0]["steps"]
    assert steps == ["When retrying", "When retrying"]


@pytest.mark.parametrize("target", ["APP-SPEC-001", "SG-SPEC-LEGACY-001"])
def test_existing_product_spec_id_forms_are_accepted(workspace, target):
    root, path, node = workspace
    node["id"] = target
    path = root / f"specs/nodes/{target}.yaml"
    path.write_text(yaml.safe_dump(node))
    assert pack.build_contract_pack(root, target)["source"]["spec_id"] == target


def test_yaml_dates_are_normalized_before_json_serialization(workspace):
    root, path, node = workspace
    node["specification"]["rollout_date"] = date(2026, 9, 28)
    path.write_text(yaml.safe_dump(node))
    result = pack.build_contract_pack(root, node["id"])
    assert result["specification"]["rollout_date"] == "2026-09-28"
    json.dumps(result)


@pytest.mark.parametrize("target", ["../bad", "", "ZEU-SPEC-0016/../../bad"])
def test_invalid_target_rejected(workspace, target):
    with pytest.raises(ValueError):
        pack.build_contract_pack(workspace[0], target)


def test_cli_writes_only_derived_pack(workspace):
    root, path, node = workspace
    before = path.read_bytes()
    process = subprocess.run(
        [sys.executable, str(TOOL), "--workspace-root", str(root), "--target-spec", node["id"]],
        capture_output=True,
        text=True,
    )
    assert process.returncode == 0, process.stderr
    output = root / "runs/implementation-contract-packs/ZEU-SPEC-0016.json"
    assert json.loads(output.read_text())["status"] == "review_required"
    assert path.read_bytes() == before


def test_cli_rejects_symlink_output_into_canonical_sources(workspace):
    root, path, node = workspace
    before = path.read_bytes()
    output = root / "runs/implementation-contract-packs/ZEU-SPEC-0016.json"
    output.parent.mkdir(parents=True)
    output.symlink_to(path)
    process = subprocess.run(
        [sys.executable, str(TOOL), "--workspace-root", str(root), "--target-spec", node["id"]],
        capture_output=True,
        text=True,
    )
    assert process.returncode == 1
    assert path.read_bytes() == before


def test_cli_reports_blocked_without_claiming_success(workspace):
    root, path, node = workspace
    del node["specification"]["observability"]
    path.write_text(yaml.safe_dump(node))
    process = subprocess.run(
        [sys.executable, str(TOOL), "--workspace-root", str(root), "--target-spec", node["id"]],
        capture_output=True,
        text=True,
    )
    assert process.returncode == 2
    assert json.loads(process.stdout)["status"] == "blocked"


def test_wrong_source_identity_rejected(workspace):
    root, path, node = workspace
    node["id"] = "OTHER-SPEC-0001"
    path.write_text(yaml.safe_dump(node))
    with pytest.raises(ValueError, match="requested canonical"):
        pack.build_contract_pack(root, "ZEU-SPEC-0016")


def test_duplicate_yaml_cannot_shadow_an_obligation(workspace):
    root, path, node = workspace
    path.write_text(path.read_text() + "\nspecification: {}\n")
    with pytest.raises(ValueError, match="duplicate YAML key"):
        pack.build_contract_pack(root, node["id"])
