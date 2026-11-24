import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "ontology_skill_eval"))
from grade import first_catalog_correct, grade
from scenario import CATALOG, DISTRACTOR, digest, trial_inputs


def test_projection_requires_expected_catalog_and_binding(tmp_path):
    catalog = tmp_path / "model.json"
    catalog.write_text(json.dumps({"classes": {"DomainEntity": {"declaration": "expected"}}}))
    graph = tmp_path / "graph.json"
    payload = {
        "foundationCatalogs": [
            {
                "id": "specgraph.foundation",
                "version": "0.1.0",
                "catalog": {"classes": {"DomainEntity": {"declaration": "expected"}}},
            }
        ],
        "classes": [{"fqid": "review:Proposal", "extends": "sg:DomainEntity"}],
    }
    graph.write_text(json.dumps(payload))
    assert grade(graph, catalog)
    payload["foundationCatalogs"][0]["catalog"]["classes"]["DomainEntity"]["declaration"] = "wrong"
    graph.write_text(json.dumps(payload))
    assert not grade(graph, catalog)
    payload["foundationCatalogs"] = []
    graph.write_text(json.dumps(payload))
    assert not grade(graph, catalog)
    graph.write_text("{")
    assert not grade(graph, catalog)


def test_exact_binding_checks_catalog_bytes_and_rejects_extra_bindings(tmp_path):
    catalog = tmp_path / "model.json"
    model = {"id": "ontology.foundation", "classes": {"DomainEntity": {"declaration": "expected"}}}
    catalog.write_text(json.dumps(model))
    graph = tmp_path / "ontology.graph.json"
    binding = {
        "id": "specgraph.foundation",
        "alias": "sg",
        "version": "0.1.0",
        "catalog": model,
        "catalogByteDigest": f"sha256:{digest(catalog)}",
    }
    payload = {
        "foundationCatalogs": [binding],
        "classes": [{"fqid": "review:Proposal", "extends": "sg:DomainEntity"}],
    }
    graph.write_text(json.dumps(payload))
    assert grade(graph, catalog, exact_binding=True)

    payload["foundationCatalogs"].append({**binding, "version": "0.2.0"})
    graph.write_text(json.dumps(payload))
    assert not grade(graph, catalog, exact_binding=True)

    payload["foundationCatalogs"].pop()
    catalog.write_text(json.dumps(model, indent=2))
    assert not grade(graph, catalog, exact_binding=True)


@pytest.mark.parametrize("initial", [[], ["wrong.json"], ["expected.json", "wrong.json"]])
def test_first_choice_stays_wrong_after_successful_retry(tmp_path, initial):
    trace = tmp_path / "calls.jsonl"
    expected = tmp_path / "expected.json"
    rows = [
        {"parsed": True, "catalogs": [str(tmp_path / item) for item in initial]},
        {"parsed": True, "catalogs": [str(expected)]},
    ]
    trace.write_text("".join(json.dumps(row) + "\n" for row in rows))
    assert first_catalog_correct(trace, expected) is False
    trace.write_text(json.dumps(rows[1]) + "\n")
    assert first_catalog_correct(trace, expected) is True


def test_missing_and_unparsable_trace_is_unobserved(tmp_path):
    trace = tmp_path / "calls.jsonl"
    catalog = tmp_path / "expected.json"
    assert first_catalog_correct(trace, catalog) is None
    trace.write_text("{\n")
    assert first_catalog_correct(trace, catalog) is None
    trace.write_text('{"parsed": false, "catalogs": []}\n')
    assert first_catalog_correct(trace, catalog) is False


def test_catalog_layout_swaps_between_repeats():
    first = trial_inputs(1, two_catalogs=True)
    second = trial_inputs(2, two_catalogs=True)
    assert first[CATALOG] == second[DISTRACTOR] == Path("catalogs/b/model.json")
    assert second[CATALOG] == first[DISTRACTOR] == Path("catalogs/a/model.json")
