import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "ontology_skill_eval"))
from grade import grade


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
