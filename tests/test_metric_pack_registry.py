from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: str) -> dict[str, object]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_metric_pack_registry_declares_current_metrics_packs() -> None:
    registry = load_json("tools/metric_pack_registry.json")

    assert registry["artifact_kind"] == "metric_pack_registry"
    assert registry["version"] == 1
    assert registry["source_registry"] == {
        "repository_id": "metrics",
        "repository": "0al-spec/Metrics",
        "contract_path": "METRIC_PACKS.md",
        "readme_path": "README.md",
    }

    packs = registry["packs"]
    assert isinstance(packs, list)
    by_id = {str(item["metric_pack_id"]): item for item in packs if isinstance(item, dict)}

    assert sorted(by_id) == ["sib", "sib_economic_observability", "sib_full"]
    assert by_id["sib"]["source"]["path"] == "SIB/metrics.tex"
    assert by_id["sib_full"]["source"]["path"] == "SIB_FULL/sib_full_metrics.tex"
    assert (
        by_id["sib_economic_observability"]["source"]["path"]
        == "SIB_ECONOMIC_OBSERVABILITY/sib_economic_observability.tex"
    )


def test_metric_pack_registry_reuses_external_consumer_reference_states() -> None:
    registry = load_json("tools/metric_pack_registry.json")
    consumers = load_json("tools/external_consumers.json")

    allowed_reference_states = set(consumers["reference_states"])
    consumers_by_id = {
        str(item["consumer_id"]): item for item in consumers["consumers"] if isinstance(item, dict)
    }

    for item in registry["packs"]:
        assert isinstance(item, dict)
        consumer_id = str(item["consumer_id"])
        assert consumer_id in consumers_by_id
        assert item["reference_state"] in allowed_reference_states
        assert item["reference_state"] == consumers_by_id[consumer_id]["reference_state"]


def test_metric_pack_registry_keeps_draft_packs_non_authoritative() -> None:
    registry = load_json("tools/metric_pack_registry.json")

    for item in registry["packs"]:
        assert isinstance(item, dict)
        if item["reference_state"] == "draft_reference":
            assert item["pack_authority_state"] == "not_threshold_authority"
            assert item["lifecycle_state"] == "active"
