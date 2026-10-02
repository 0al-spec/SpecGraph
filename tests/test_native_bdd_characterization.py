"""Observed 0047 compatibility, not conformance to RFC 0223's future strict profile."""

from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path

import pytest
import yaml

TOOL = Path(__file__).resolve().parents[1] / "tools" / "implementation_contract_pack.py"
module_spec = importlib.util.spec_from_file_location("native_bdd_0047_baseline", TOOL)
assert module_spec and module_spec.loader
pack = importlib.util.module_from_spec(module_spec)
sys.modules[module_spec.name] = pack
module_spec.loader.exec_module(pack)


@pytest.fixture
def node_source(tmp_path):
    node = {
        "id": "APP-SPEC-0001",
        "kind": "spec",
        "title": "BDD compatibility fixture",
        "status": "linked",
        "acceptance": ["The declaration remains read-only"],
        "specification": {
            "bdd_scenarios": [{"id": "NATIVE-001", "steps": ["Given a declaration"]}],
        },
    }
    path = tmp_path / "specs/nodes/APP-SPEC-0001.yaml"
    path.parent.mkdir(parents=True)
    return tmp_path, path, node


def write_node(path, node):
    path.write_text(yaml.safe_dump(node, sort_keys=False))


def observability(refs):
    return {
        "obligations": [
            {
                "id": "declaration-observation",
                "event": "declaration.observed",
                "boundary": "read-only projection",
                "attributes": [],
                "expected_outcomes": ["observed"],
                "scenario_ids": refs,
            }
        ],
        "non_interference": ["No source writes"],
        "excluded_attributes": [],
    }


@pytest.mark.parametrize("presence", ["absent", "explicit_empty"])
def test_absent_and_empty_native_containers_have_no_required_tests(node_source, presence):
    root, path, node = node_source
    if presence == "absent":
        del node["specification"]["bdd_scenarios"]
    else:
        node["specification"]["bdd_scenarios"] = []
    write_node(path, node)
    before = path.read_bytes()

    result = pack.build_contract_pack(root, node["id"])

    assert result["specification"] == node["specification"]
    assert result["implementation_work_preview"]["required_tests"] == []
    assert result["status"] == "blocked"
    assert result["blockers"] == ["missing_observability_contract"]
    assert result["evidence_status"] == "not_evaluated"
    assert result["canonical_mutations_allowed"] is False
    assert result["runtime_code_mutations_allowed"] is False
    assert path.read_bytes() == before


@pytest.mark.parametrize("native_present", [False, True])
@pytest.mark.parametrize(
    "alternate", [None, [], [{"id": "ALTERNATE-001", "steps": ["Given alternate text"]}]]
)
def test_alternate_container_is_retained_but_never_consumed(node_source, native_present, alternate):
    root, path, node = node_source
    node["specification"]["scenarios"] = alternate
    if native_present:
        node["specification"]["observability"] = observability(["NATIVE-001"])
    else:
        del node["specification"]["bdd_scenarios"]
    write_node(path, node)

    result = pack.build_contract_pack(root, node["id"])

    assert result["specification"]["scenarios"] == alternate
    assert result["implementation_work_preview"]["required_tests"] == (
        ["NATIVE-001"] if native_present else []
    )
    assert result["status"] == ("review_required" if native_present else "blocked")


def test_alternate_scenario_cannot_satisfy_observability_reference(node_source):
    root, path, node = node_source
    node["specification"]["scenarios"] = [{"id": "ALTERNATE-001", "steps": ["Given text"]}]
    node["specification"]["observability"] = observability(["ALTERNATE-001"])
    write_node(path, node)
    with pytest.raises(ValueError, match="unknown scenario reference"):
        pack.build_contract_pack(root, node["id"])


@pytest.mark.parametrize("title", [None, "", "  ", True, 42, [], {}])
def test_supplied_descriptive_title_is_not_validated_in_current_consumer(node_source, title):
    root, path, node = node_source
    node["specification"]["bdd_scenarios"][0]["scenario"] = title
    node["specification"]["observability"] = observability(["NATIVE-001"])
    write_node(path, node)
    result = pack.build_contract_pack(root, node["id"])
    assert result["status"] == "review_required"
    assert result["specification"]["bdd_scenarios"][0]["scenario"] == title


@pytest.mark.parametrize("container", [None, True, False, 42, "text", {}])
def test_native_container_must_be_a_list(node_source, container):
    root, path, node = node_source
    node["specification"]["bdd_scenarios"] = container
    write_node(path, node)
    with pytest.raises(ValueError, match="bdd_scenarios must be a list"):
        pack.build_contract_pack(root, node["id"])


@pytest.mark.parametrize(
    "entry",
    [None, "text", True, {}, {"steps": ["Given text"]}, {"id": "NATIVE-001"}],
)
def test_malformed_scenario_entries_are_rejected(node_source, entry):
    root, path, node = node_source
    node["specification"]["bdd_scenarios"] = [entry]
    write_node(path, node)
    with pytest.raises(ValueError):
        pack.build_contract_pack(root, node["id"])


@pytest.mark.parametrize("identity", [None, "", " \t", 42, True])
def test_native_id_must_be_a_nonempty_string(node_source, identity):
    root, path, node = node_source
    node["specification"]["bdd_scenarios"][0]["id"] = identity
    write_node(path, node)
    with pytest.raises(ValueError, match="scenario.id must be a nonempty string"):
        pack.build_contract_pack(root, node["id"])


@pytest.mark.parametrize("steps", [None, [], "text", {}, True, [None], [""], [" \t"], [42]])
def test_steps_require_a_nonempty_list_of_nonempty_strings(node_source, steps):
    root, path, node = node_source
    node["specification"]["bdd_scenarios"][0]["steps"] = steps
    write_node(path, node)
    with pytest.raises(ValueError, match="scenario.steps"):
        pack.build_contract_pack(root, node["id"])


def test_exact_ids_and_ordered_repeated_text_are_not_trimmed_or_parsed(node_source):
    root, path, node = node_source
    identity = " NATIVE-001 "
    steps = [" Given text ", "unclassified text", " When retrying ", " When retrying "]
    scenario = {"id": identity, "steps": steps}
    node["specification"]["bdd_scenarios"] = [scenario]
    node["specification"]["observability"] = observability([identity])
    write_node(path, node)
    before = path.read_bytes()
    result = pack.build_contract_pack(root, node["id"])
    assert result["specification"]["bdd_scenarios"] == [scenario]
    assert result["implementation_work_preview"]["required_tests"] == [identity]
    assert result == pack.build_contract_pack(root, node["id"])
    assert path.read_bytes() == before


def test_exact_duplicate_ids_are_rejected(node_source):
    root, path, node = node_source
    scenarios = node["specification"]["bdd_scenarios"]
    scenarios.append(copy.deepcopy(scenarios[0]))
    write_node(path, node)
    with pytest.raises(ValueError, match="duplicate scenario: NATIVE-001"):
        pack.build_contract_pack(root, node["id"])


def test_meaningful_whitespace_makes_ids_distinct_in_current_consumer(node_source):
    root, path, node = node_source
    node["specification"]["bdd_scenarios"].append(
        {"id": " NATIVE-001 ", "steps": ["Given another declaration"]}
    )
    node["specification"]["observability"] = observability(["NATIVE-001", " NATIVE-001 "])
    write_node(path, node)
    result = pack.build_contract_pack(root, node["id"])
    assert result["implementation_work_preview"]["required_tests"] == [
        " NATIVE-001 ",
        "NATIVE-001",
    ]


@pytest.mark.parametrize("related_node", ["parent", "sibling", "other_workspace"])
def test_reference_lookup_does_not_search_related_nodes(node_source, tmp_path, related_node):
    root, path, node = node_source
    other = copy.deepcopy(node)
    other["id"] = "APP-SPEC-0002"
    other["specification"]["bdd_scenarios"][0]["id"] = "OTHER-001"
    if related_node == "parent":
        node["refines"] = [other["id"]]
    other_root = tmp_path / "other" if related_node == "other_workspace" else root
    other_path = other_root / f"specs/nodes/{other['id']}.yaml"
    other_path.parent.mkdir(parents=True, exist_ok=True)
    write_node(other_path, other)
    node["specification"]["observability"] = observability(["OTHER-001"])
    write_node(path, node)
    before = {p: p.read_bytes() for p in (path, other_path)}
    with pytest.raises(ValueError, match="unknown scenario reference"):
        pack.build_contract_pack(root, node["id"])
    assert {p: p.read_bytes() for p in before} == before


def test_other_nodes_are_not_scanned_for_workspace_uniqueness(node_source):
    root, path, node = node_source
    other = copy.deepcopy(node)
    other["id"] = "APP-SPEC-0002"
    write_node(path.with_name(f"{other['id']}.yaml"), other)
    node["specification"]["observability"] = observability(["NATIVE-001"])
    write_node(path, node)
    result = pack.build_contract_pack(root, node["id"])
    assert result["status"] == "review_required"
    assert result["context"]["scope"] == "explicit_target_only"
    assert result["context"]["inheritance"] == "not_evaluated"


def test_duplicate_step_mapping_keys_are_rejected_before_projection(node_source):
    root, path, node = node_source
    write_node(path, node)
    raw = path.read_text()
    assert "    steps:" in raw
    path.write_text(raw.replace("    steps:", "    steps: [Given shadowed text]\n    steps:", 1))
    before = path.read_bytes()
    with pytest.raises(ValueError, match="duplicate YAML key: steps"):
        pack.build_contract_pack(root, node["id"])
    assert path.read_bytes() == before
