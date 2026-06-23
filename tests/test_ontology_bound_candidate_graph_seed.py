from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "ontology_bound_candidate_graph_seed.py"
USER_SOURCE_TOOL = ROOT / "tools" / "user_idea_intake_source.py"
EVENT_INTAKE_TOOL = ROOT / "tools" / "idea_event_storming_intake.py"
CANDIDATE_GRAPH_TOOL = ROOT / "tools" / "candidate_spec_graph.py"
USER_SOURCE_READY = ROOT / "tests" / "fixtures" / "user_idea_intake" / "source_ready.json"
ONTOLOGY_IR = (
    ROOT / "ontology" / "packages" / "specgraph-core" / "generated" / "ontology.normalized.json"
)


def load_module(path: Path, name: str) -> object:
    spec = importlib.util.spec_from_file_location(name, path)
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


def support_triage_intake() -> dict[str, object]:
    source_module = load_module(USER_SOURCE_TOOL, "user_idea_source_for_ontology_seed")
    intake_module = load_module(EVENT_INTAKE_TOOL, "event_storming_intake_for_ontology_seed")
    seed = source_module.build_user_idea_event_storming_seed(
        load_json(USER_SOURCE_READY),
        source_path=USER_SOURCE_READY,
    )
    return intake_module.build_idea_event_storming_intake(
        seed,
        source_path=USER_SOURCE_READY,
    )


def build_seed(
    *,
    intake: dict[str, object] | None = None,
    ontology_ir: dict[str, object] | None = None,
) -> dict[str, object]:
    module = load_module(TOOL_PATH, "ontology_bound_candidate_seed_under_test")
    return module.build_ontology_bound_candidate_graph_seed(
        intake=intake or support_triage_intake(),
        ontology_ir=ontology_ir or load_json(ONTOLOGY_IR),
        intake_path=USER_SOURCE_READY,
        ontology_ir_path=ONTOLOGY_IR,
    )


def test_ontology_bound_candidate_seed_builds_ready_seed_from_generic_intake() -> None:
    seed = build_seed()

    assert seed["artifact_kind"] == "candidate_spec_graph_seed"
    assert seed["contract_ref"] == "specgraph.idea-to-spec.candidate-spec-graph-seed.v0.1"
    assert seed["source_ref"] == "product://support-triage-log/candidate-spec-graph-seed"
    source_generation = seed["source_generation"]
    assert source_generation["proposal_id"] == "0159"
    assert source_generation["readiness"]["ready"] is True
    assert source_generation["findings"] == []
    assert source_generation["summary"]["ontology_binding_count"] == 5
    assert source_generation["summary"]["ontology_gap_count"] >= 1
    gap_terms = {gap["term"] for gap in source_generation["ontology_gaps"] if isinstance(gap, dict)}
    assert "SupportCase" in gap_terms

    graph = seed["candidate_graph"]
    assert isinstance(graph, dict)
    nodes = graph["nodes"]
    assert isinstance(nodes, list)
    product = nodes[0]
    assert "ontology://org.0al.specgraph.core/0.1.0/classes/Spec" in product["ontology_refs"]
    command_nodes = [node for node in nodes if node["kind"] == "behavior_requirement"]
    assert command_nodes
    assert all(
        "ontology://org.0al.specgraph.core/0.1.0/classes/Requirement" in node["ontology_refs"]
        for node in command_nodes
    )


def test_ontology_bound_candidate_seed_feeds_candidate_graph_builder() -> None:
    candidate_module = load_module(CANDIDATE_GRAPH_TOOL, "candidate_graph_for_ontology_seed")
    intake = support_triage_intake()
    seed = build_seed(intake=intake)

    graph = candidate_module.build_candidate_spec_graph(
        intake=intake,
        seed=seed,
        intake_path=USER_SOURCE_READY,
        seed_path=ROOT / "runs" / "candidate_spec_graph_seed.json",
    )

    assert graph["pre_sib_readiness"]["ready"] is True
    assert graph["summary"]["node_count"] >= 4
    assert graph["summary"]["gap_count"] >= 1
    assert graph["active_frame"]["domain_refs"] == ["domain.support_triage_log"]
    assert graph["findings"] == []


def test_ontology_bound_candidate_seed_disambiguates_duplicate_node_slugs() -> None:
    candidate_module = load_module(CANDIDATE_GRAPH_TOOL, "candidate_graph_for_duplicate_slugs")
    intake = support_triage_intake()
    event_storming = intake["event_storming"]
    assert isinstance(event_storming, dict)
    commands = event_storming["commands"]
    assert isinstance(commands, list)
    commands.append(
        {
            "id": "command.record-triage-note-copy",
            "name": "Record Triage Note",
            "actor_refs": ["actor.support-agent"],
            "produces_event_refs": ["event.triage-note-recorded"],
        }
    )
    commands.append(
        {
            "id": "command.product-boundary",
            "name": "Product Boundary",
            "actor_refs": ["actor.support-agent"],
            "produces_event_refs": ["event.triage-note-recorded"],
        }
    )

    seed = build_seed(intake=intake)
    graph_seed = seed["candidate_graph"]
    assert isinstance(graph_seed, dict)
    nodes = graph_seed["nodes"]
    assert isinstance(nodes, list)
    node_ids = [node["id"] for node in nodes if isinstance(node, dict)]

    assert len(node_ids) == len(set(node_ids))
    assert "candidate-spec.record-triage-note" in node_ids
    assert "candidate-spec.record-triage-note-copy" in node_ids
    assert "candidate-spec.product-boundary-command-product-boundary" in node_ids

    graph = candidate_module.build_candidate_spec_graph(
        intake=intake,
        seed=seed,
        intake_path=USER_SOURCE_READY,
        seed_path=ROOT / "runs" / "candidate_spec_graph_seed.json",
    )

    assert graph["pre_sib_readiness"]["ready"] is True
    assert graph["findings"] == []


def test_ontology_bound_candidate_seed_uses_stable_command_ids_for_node_slugs() -> None:
    intake = support_triage_intake()
    event_storming = intake["event_storming"]
    assert isinstance(event_storming, dict)
    commands = event_storming["commands"]
    assert isinstance(commands, list)
    command = commands[0]
    assert isinstance(command, dict)
    original_id = command["id"]
    command["name"] = "Log Triage Note"

    seed = build_seed(intake=intake)
    graph_seed = seed["candidate_graph"]
    assert isinstance(graph_seed, dict)
    nodes = graph_seed["nodes"]
    assert isinstance(nodes, list)
    renamed_nodes = [
        node
        for node in nodes
        if isinstance(node, dict) and node.get("source_event_refs", [None])[0] == original_id
    ]

    assert renamed_nodes
    assert renamed_nodes[0]["id"] == "candidate-spec.record-triage-note"
    assert renamed_nodes[0]["title"] == "Log Triage Note"


def test_ontology_bound_candidate_seed_bounds_long_constraint_node_slugs() -> None:
    intake = support_triage_intake()
    event_storming = intake["event_storming"]
    assert isinstance(event_storming, dict)
    constraints = event_storming["constraints"]
    assert isinstance(constraints, list)
    constraints.append(
        {
            "kind": "process",
            "statement": (
                "Every triage record that references external incident evidence must preserve "
                "the evidence source, actor, timestamp, scope, and review rationale before "
                "a candidate graph can be promoted."
            ),
        }
    )

    seed = build_seed(intake=intake)
    graph_seed = seed["candidate_graph"]
    assert isinstance(graph_seed, dict)
    nodes = graph_seed["nodes"]
    assert isinstance(nodes, list)
    long_constraint_nodes = [
        node
        for node in nodes
        if isinstance(node, dict)
        and node.get("title", "").startswith("Every triage record that references")
    ]

    assert long_constraint_nodes
    node_id = long_constraint_nodes[0]["id"]
    assert isinstance(node_id, str)
    assert node_id.startswith("candidate-spec.")
    assert len(node_id.removeprefix("candidate-spec.")) <= 72


def test_ontology_bound_candidate_seed_requires_ontology_frame() -> None:
    candidate_module = load_module(CANDIDATE_GRAPH_TOOL, "candidate_graph_for_bad_ontology_seed")
    intake = support_triage_intake()
    active_frame = intake["active_frame"]
    assert isinstance(active_frame, dict)
    active_frame.pop("ontology_layer_refs")
    active_frame.pop("model_applicability_refs")

    seed = build_seed(intake=intake)
    source_generation = seed["source_generation"]
    assert source_generation["readiness"]["ready"] is False
    assert "active_frame_ontology_context_missing" in finding_ids(source_generation)

    graph = candidate_module.build_candidate_spec_graph(
        intake=intake,
        seed=seed,
        intake_path=USER_SOURCE_READY,
        seed_path=ROOT / "runs" / "candidate_spec_graph_seed.json",
    )

    assert graph["pre_sib_readiness"]["ready"] is False
    assert "candidate_graph_seed_source_generation_review_required" in finding_ids(graph)


def test_ontology_bound_candidate_seed_requires_core_ontology_classes() -> None:
    ontology_ir = deepcopy(load_json(ONTOLOGY_IR))
    classes = ontology_ir["classes"]
    assert isinstance(classes, list)
    ontology_ir["classes"] = [
        entry for entry in classes if isinstance(entry, dict) and entry.get("id") != "Requirement"
    ]

    seed = build_seed(ontology_ir=ontology_ir)
    source_generation = seed["source_generation"]

    assert source_generation["readiness"]["ready"] is False
    assert "ontology_required_class_missing" in finding_ids(source_generation)


def test_ontology_bound_candidate_seed_cli_writes_seed(tmp_path: Path) -> None:
    output = tmp_path / "candidate_spec_graph_seed.json"
    intake_path = tmp_path / "idea_event_storming_intake.json"
    intake_path.write_text(json.dumps(support_triage_intake()), encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            str(TOOL_PATH),
            "--intake",
            str(intake_path),
            "--ontology-ir",
            str(ONTOLOGY_IR),
            "--output",
            str(output),
            "--strict",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )

    assert "ready_for_candidate_graph" in result.stdout
    written = load_json(output)
    assert written["artifact_kind"] == "candidate_spec_graph_seed"
    assert written["source_generation"]["readiness"]["ready"] is True
