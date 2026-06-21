from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "candidate_spec_graph.py"
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "candidate_spec_graph"
INTAKE_READY = FIXTURE_DIR / "idea_event_storming_intake_ready.json"
INTAKE_REVIEW_REQUIRED = FIXTURE_DIR / "intake_review_required.json"
CANDIDATE_READY = FIXTURE_DIR / "candidate_ready.json"


def load_module() -> object:
    spec = importlib.util.spec_from_file_location(
        "candidate_spec_graph_under_test",
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


def build_ready_graph() -> dict[str, object]:
    module = load_module()
    return module.build_candidate_spec_graph(
        intake=load_json(INTAKE_READY),
        seed=load_json(CANDIDATE_READY),
        intake_path=INTAKE_READY,
        seed_path=CANDIDATE_READY,
    )


def test_candidate_spec_graph_builds_ready_graph() -> None:
    graph = build_ready_graph()

    assert graph["artifact_kind"] == "candidate_spec_graph"
    assert graph["proposal_id"] == "0150"
    assert graph["canonical_mutations_allowed"] is False
    assert graph["tracked_artifacts_written"] is False
    assert graph["pre_sib_readiness"]["ready"] is True
    assert graph["pre_sib_readiness"]["review_state"] == "ready_for_pre_sib"
    assert graph["source_intake"]["root_intent_sha256"]
    assert graph["summary"]["node_count"] == 3
    assert graph["summary"]["edge_count"] == 2
    assert graph["summary"]["requirement_count"] == 3
    assert graph["summary"]["acceptance_criteria_count"] == 3
    assert graph["summary"]["claim_count"] == 1
    assert graph["summary"]["gap_count"] == 1
    assert graph["privacy_boundary"]["raw_intent_text_published"] is False
    assert graph["findings"] == []


def test_candidate_spec_graph_blocks_unready_intake() -> None:
    module = load_module()

    graph = module.build_candidate_spec_graph(
        intake=load_json(INTAKE_REVIEW_REQUIRED),
        seed=load_json(CANDIDATE_READY),
        intake_path=INTAKE_REVIEW_REQUIRED,
        seed_path=CANDIDATE_READY,
    )

    assert graph["pre_sib_readiness"]["ready"] is False
    assert "intake_not_ready" in finding_ids(graph)


def test_candidate_spec_graph_rejects_unknown_refs() -> None:
    module = load_module()
    seed = load_json(CANDIDATE_READY)
    candidate_graph = seed["candidate_graph"]
    assert isinstance(candidate_graph, dict)
    nodes = candidate_graph["nodes"]
    edges = candidate_graph["edges"]
    assert isinstance(nodes, list)
    assert isinstance(edges, list)
    nodes[0]["source_event_refs"] = ["event.missing"]
    edges[0]["to"] = "candidate-spec.missing"

    graph = module.build_candidate_spec_graph(
        intake=load_json(INTAKE_READY),
        seed=seed,
        intake_path=INTAKE_READY,
        seed_path=CANDIDATE_READY,
    )

    ids = finding_ids(graph)
    assert graph["pre_sib_readiness"]["ready"] is False
    assert "candidate_node_unknown_intake_ref" in ids
    assert "candidate_edge_invalid" in ids


def test_candidate_spec_graph_filters_raw_seed_fields() -> None:
    module = load_module()
    seed = load_json(CANDIDATE_READY)
    candidate_graph = seed["candidate_graph"]
    assert isinstance(candidate_graph, dict)
    nodes = candidate_graph["nodes"]
    assert isinstance(nodes, list)
    nodes[0]["raw_prompt"] = "secret prompt"
    nodes[0]["raw_model_output"] = "secret model output"
    nodes[0]["intent_text"] = "secret intent"

    graph = module.build_candidate_spec_graph(
        intake=load_json(INTAKE_READY),
        seed=seed,
        intake_path=INTAKE_READY,
        seed_path=CANDIDATE_READY,
    )

    node = graph["nodes"][0]
    assert "raw_prompt" not in node
    assert "raw_model_output" not in node
    assert "intent_text" not in node
    assert "secret prompt" not in json.dumps(graph)
    assert graph["privacy_boundary"]["raw_prompt_published"] is False
    assert graph["privacy_boundary"]["raw_model_output_published"] is False


def test_candidate_spec_graph_rejects_duplicate_node_ids() -> None:
    module = load_module()
    seed = load_json(CANDIDATE_READY)
    candidate_graph = seed["candidate_graph"]
    assert isinstance(candidate_graph, dict)
    nodes = candidate_graph["nodes"]
    assert isinstance(nodes, list)
    duplicate = dict(nodes[0])
    duplicate["title"] = "Duplicate Calculator Product"
    nodes.append(duplicate)

    graph = module.build_candidate_spec_graph(
        intake=load_json(INTAKE_READY),
        seed=seed,
        intake_path=INTAKE_READY,
        seed_path=CANDIDATE_READY,
    )

    assert graph["pre_sib_readiness"]["ready"] is False
    assert "candidate_node_duplicate_id" in finding_ids(graph)


def test_candidate_spec_graph_requires_real_requirement_and_ac_text() -> None:
    module = load_module()
    seed = load_json(CANDIDATE_READY)
    candidate_graph = seed["candidate_graph"]
    assert isinstance(candidate_graph, dict)
    nodes = candidate_graph["nodes"]
    assert isinstance(nodes, list)
    nodes[0]["requirements"] = [{"id": "req.placeholder"}]
    nodes[0]["acceptance_criteria"] = [{"id": "ac.placeholder"}]

    graph = module.build_candidate_spec_graph(
        intake=load_json(INTAKE_READY),
        seed=seed,
        intake_path=INTAKE_READY,
        seed_path=CANDIDATE_READY,
    )

    ids = finding_ids(graph)
    assert graph["pre_sib_readiness"]["ready"] is False
    assert "candidate_requirement_statement_missing" in ids
    assert "candidate_acceptance_criterion_statement_missing" in ids


def test_candidate_spec_graph_requires_requirement_ac_refs() -> None:
    module = load_module()
    seed = load_json(CANDIDATE_READY)
    candidate_graph = seed["candidate_graph"]
    assert isinstance(candidate_graph, dict)
    nodes = candidate_graph["nodes"]
    assert isinstance(nodes, list)
    requirements = nodes[0]["requirements"]
    assert isinstance(requirements, list)
    requirements[0].pop("acceptance_criteria_refs")

    graph = module.build_candidate_spec_graph(
        intake=load_json(INTAKE_READY),
        seed=seed,
        intake_path=INTAKE_READY,
        seed_path=CANDIDATE_READY,
    )

    assert graph["pre_sib_readiness"]["ready"] is False
    assert "candidate_requirement_ac_refs_missing" in finding_ids(graph)


def test_candidate_spec_graph_requires_source_event_refs() -> None:
    module = load_module()
    seed = load_json(CANDIDATE_READY)
    candidate_graph = seed["candidate_graph"]
    assert isinstance(candidate_graph, dict)
    nodes = candidate_graph["nodes"]
    assert isinstance(nodes, list)
    nodes[0].pop("source_event_refs")

    graph = module.build_candidate_spec_graph(
        intake=load_json(INTAKE_READY),
        seed=seed,
        intake_path=INTAKE_READY,
        seed_path=CANDIDATE_READY,
    )

    assert graph["pre_sib_readiness"]["ready"] is False
    assert "candidate_node_source_event_refs_missing" in finding_ids(graph)


def test_candidate_spec_graph_rejects_strong_claim_without_fgr() -> None:
    module = load_module()
    seed = load_json(CANDIDATE_READY)
    candidate_graph = seed["candidate_graph"]
    assert isinstance(candidate_graph, dict)
    nodes = candidate_graph["nodes"]
    assert isinstance(nodes, list)
    claims = nodes[0]["claims"]
    assert isinstance(claims, list)
    claims[0].pop("calibration")

    graph = module.build_candidate_spec_graph(
        intake=load_json(INTAKE_READY),
        seed=seed,
        intake_path=INTAKE_READY,
        seed_path=CANDIDATE_READY,
    )

    assert graph["pre_sib_readiness"]["ready"] is False
    assert "candidate_strong_claim_without_fgr" in finding_ids(graph)


def test_candidate_spec_graph_rejects_invalid_fgr_levels() -> None:
    module = load_module()
    seed = load_json(CANDIDATE_READY)
    candidate_graph = seed["candidate_graph"]
    assert isinstance(candidate_graph, dict)
    nodes = candidate_graph["nodes"]
    assert isinstance(nodes, list)
    claims = nodes[0]["claims"]
    assert isinstance(claims, list)
    claims[0]["calibration"]["F"] = "formal"
    claims[0]["calibration"]["R"] = "reliable"

    graph = module.build_candidate_spec_graph(
        intake=load_json(INTAKE_READY),
        seed=seed,
        intake_path=INTAKE_READY,
        seed_path=CANDIDATE_READY,
    )

    assert graph["pre_sib_readiness"]["ready"] is False
    assert "candidate_strong_claim_without_fgr" in finding_ids(graph)


def test_candidate_spec_graph_validates_seed_contract_metadata() -> None:
    module = load_module()
    seed = load_json(CANDIDATE_READY)
    seed["artifact_kind"] = "idea_event_storming_seed"
    seed.pop("contract_ref", None)

    graph = module.build_candidate_spec_graph(
        intake=load_json(INTAKE_READY),
        seed=seed,
        intake_path=INTAKE_READY,
        seed_path=CANDIDATE_READY,
    )

    assert graph["pre_sib_readiness"]["ready"] is False
    assert "candidate_graph_seed_contract_invalid" in finding_ids(graph)


def test_candidate_spec_graph_rejects_requirement_without_known_ac() -> None:
    module = load_module()
    seed = load_json(CANDIDATE_READY)
    candidate_graph = seed["candidate_graph"]
    assert isinstance(candidate_graph, dict)
    nodes = candidate_graph["nodes"]
    assert isinstance(nodes, list)
    requirements = nodes[0]["requirements"]
    assert isinstance(requirements, list)
    requirements[0]["acceptance_criteria_refs"] = ["ac.missing"]

    graph = module.build_candidate_spec_graph(
        intake=load_json(INTAKE_READY),
        seed=seed,
        intake_path=INTAKE_READY,
        seed_path=CANDIDATE_READY,
    )

    assert graph["pre_sib_readiness"]["ready"] is False
    assert "candidate_requirement_unknown_ac_ref" in finding_ids(graph)


def test_candidate_spec_graph_cli_writes_output(tmp_path: Path) -> None:
    output = tmp_path / "candidate_spec_graph.json"

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--intake",
            str(INTAKE_READY),
            "--candidate-seed",
            str(CANDIDATE_READY),
            "--output",
            str(output),
            "--strict",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    graph = load_json(output)
    assert graph["artifact_kind"] == "candidate_spec_graph"
    assert graph["pre_sib_readiness"]["ready"] is True


def test_candidate_spec_graph_strict_cli_exits_nonzero(tmp_path: Path) -> None:
    output = tmp_path / "candidate_spec_graph.json"

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--intake",
            str(INTAKE_REVIEW_REQUIRED),
            "--candidate-seed",
            str(CANDIDATE_READY),
            "--output",
            str(output),
            "--strict",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 1
    graph = load_json(output)
    assert graph["pre_sib_readiness"]["ready"] is False
