from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "specauthor_authoring_flow.py"
CONTEXT_PATH = (
    ROOT / "tests" / "fixtures" / "specauthor_authoring_flow" / "active_context_ready.json"
)
GENERATED_READY = (
    ROOT
    / "tests"
    / "fixtures"
    / "specauthor_generated_artifact_contract"
    / "generated_spec_ready.json"
)
GENERATED_REVIEW_REQUIRED = (
    ROOT
    / "tests"
    / "fixtures"
    / "specauthor_ontology_write_gate"
    / "generated_spec_review_required.json"
)
TERM_POLICY = ROOT / "tools" / "ontology_term_binding_policy.json"


def load_module() -> object:
    spec = importlib.util.spec_from_file_location(
        "specauthor_authoring_flow_under_test",
        TOOL_PATH,
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def finding_ids(report: dict[str, object]) -> set[str]:
    findings = report["findings"]
    assert isinstance(findings, list)
    return {finding["finding_id"] for finding in findings if isinstance(finding, dict)}


def test_specauthor_authoring_flow_builds_ready_invocation_artifact(tmp_path: Path) -> None:
    module = load_module()
    invocation_output = tmp_path / "specauthor_invocation_artifact.json"
    contract_output = tmp_path / "specauthor_invocation_artifact_contract_report.json"

    invocation, contract_report, flow_report = module.build_specauthor_authoring_flow_report(
        context=load_json(CONTEXT_PATH),
        generated_artifact=load_json(GENERATED_READY),
        generated_artifact_path=GENERATED_READY,
        term_policy=load_json(TERM_POLICY),
        invocation_output_path=invocation_output,
        contract_output_path=contract_output,
    )

    assert invocation["artifact_kind"] == "specauthor_invocation_artifact"
    assert invocation["canonical_mutations_allowed"] is False
    assert invocation["tracked_artifacts_written"] is False
    assert invocation["invocation"]["agent_id"] == "SpecAuthorAgent"
    assert invocation["active_frame"]["ontology_layer_refs"] == ["meta"]
    assert contract_report["ok"] is True
    assert flow_report["ok"] is True
    assert flow_report["review_state"] == "ready_for_operator_review"
    assert flow_report["validation_chain_summary"]["write_decision"] == "allow_graph_write"
    assert flow_report["privacy_boundary"]["raw_prompt_published"] is False


def test_specauthor_authoring_flow_blocks_missing_frame_and_applicability(tmp_path: Path) -> None:
    module = load_module()
    context = load_json(CONTEXT_PATH)
    context["active_frame"] = {
        "project": "SpecGraph",
        "target_artifact": "Proposal",
        "lifecycle_phase": "draft",
    }
    context["model_applicability"] = {}

    _, contract_report, flow_report = module.build_specauthor_authoring_flow_report(
        context=context,
        generated_artifact=load_json(GENERATED_READY),
        generated_artifact_path=GENERATED_READY,
        term_policy=load_json(TERM_POLICY),
        invocation_output_path=tmp_path / "specauthor_invocation_artifact.json",
        contract_output_path=tmp_path / "specauthor_invocation_artifact_contract_report.json",
    )

    ids = finding_ids(contract_report)
    assert flow_report["ok"] is False
    assert "active_frame_incomplete" in ids
    assert "model_applicability_incomplete" in ids


def test_specauthor_authoring_flow_blocks_low_r_decision_from_write_gate(tmp_path: Path) -> None:
    module = load_module()

    _, contract_report, flow_report = module.build_specauthor_authoring_flow_report(
        context=load_json(CONTEXT_PATH),
        generated_artifact=load_json(GENERATED_REVIEW_REQUIRED),
        generated_artifact_path=GENERATED_REVIEW_REQUIRED,
        term_policy=load_json(TERM_POLICY),
        invocation_output_path=tmp_path / "specauthor_invocation_artifact.json",
        contract_output_path=tmp_path / "specauthor_invocation_artifact_contract_report.json",
    )

    ids = finding_ids(contract_report)
    assert flow_report["ok"] is False
    assert "generated_artifact_contract_failed" in ids
    assert "write_gate_not_clear" in ids


def test_specauthor_authoring_flow_cli_writes_invocation_and_contract(tmp_path: Path) -> None:
    invocation_output = tmp_path / "specauthor_invocation_artifact.json"
    contract_output = tmp_path / "specauthor_invocation_artifact_contract_report.json"
    flow_output = tmp_path / "specauthor_authoring_flow_report.json"

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--context",
            str(CONTEXT_PATH),
            "--generated-artifact",
            str(GENERATED_READY),
            "--term-policy",
            str(TERM_POLICY),
            "--invocation-output",
            str(invocation_output),
            "--contract-output",
            str(contract_output),
            "--flow-report-output",
            str(flow_output),
            "--strict",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    invocation = load_json(invocation_output)
    contract_report = load_json(contract_output)
    flow_report = load_json(flow_output)
    assert invocation["artifact_kind"] == "specauthor_invocation_artifact"
    assert contract_report["ok"] is True
    assert flow_report["ok"] is True
