from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: str) -> dict[str, object]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


@pytest.fixture()
def supervisor_module() -> object:
    module_path = ROOT / "tools" / "supervisor.py"
    spec = importlib.util.spec_from_file_location("metric_pack_supervisor_module", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


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


def test_parse_metric_pack_contract_table(supervisor_module: object) -> None:
    packs = supervisor_module.parse_metric_pack_contract_packs(
        """
| `metric_pack_id` | Display name | Source path |
| --- | --- | --- |
| `sib` | SIB | `SIB/metrics.tex` |
| `sib_full` | SIB Full Metrics | `SIB_FULL/sib_full_metrics.tex` |
"""
    )

    assert packs == {
        "sib": {
            "metric_pack_id": "sib",
            "display_name": "SIB",
            "source_path": "SIB/metrics.tex",
        },
        "sib_full": {
            "metric_pack_id": "sib_full",
            "display_name": "SIB Full Metrics",
            "source_path": "SIB_FULL/sib_full_metrics.tex",
        },
    }


def test_metric_pack_registry_drift_reports_in_sync_contract(
    supervisor_module: object,
    tmp_path: Path,
) -> None:
    metrics_root = tmp_path / "Metrics"
    (metrics_root / "SIB").mkdir(parents=True)
    (metrics_root / "SIB" / "metrics.tex").write_text("% sib\n", encoding="utf-8")
    (metrics_root / "METRIC_PACKS.md").write_text(
        """
# Metric Packs

| `metric_pack_id` | Display name | Source path |
| --- | --- | --- |
| `sib` | SIB | `SIB/metrics.tex` |
""",
        encoding="utf-8",
    )

    report = supervisor_module.build_metric_pack_registry_drift(
        {
            "artifact_kind": "metric_pack_registry",
            "source_registry": {
                "repository": "0al-spec/Metrics",
                "contract_path": "METRIC_PACKS.md",
            },
            "packs": [
                {
                    "metric_pack_id": "sib",
                    "title": "SIB",
                    "source": {"path": "SIB/metrics.tex"},
                }
            ],
        },
        {
            "generated_at": "2026-05-01T00:00:00Z",
            "entries": [
                {
                    "repo_url": "https://github.com/0al-spec/Metrics",
                    "local_checkout": {
                        "status": "available",
                        "checkout_path": str(metrics_root),
                        "repo_revision": "abc123",
                    },
                }
            ],
        },
    )

    assert report["artifact_kind"] == "metric_pack_registry_drift"
    assert report["review_state"] == "clean"
    assert report["next_gap"] == "none"
    assert report["entry_count"] == 0
    assert report["viewer_projection"]["named_filters"]["in_sync"] == ["0al-spec/Metrics"]
    assert report["canonical_mutations_allowed"] is False
    assert report["tracked_artifacts_written"] is False


def test_metric_pack_registry_drift_reports_source_path_mismatch(
    supervisor_module: object,
    tmp_path: Path,
) -> None:
    metrics_root = tmp_path / "Metrics"
    (metrics_root / "SIB").mkdir(parents=True)
    (metrics_root / "SIB" / "metrics_v2.tex").write_text("% sib\n", encoding="utf-8")
    (metrics_root / "METRIC_PACKS.md").write_text(
        """
| `metric_pack_id` | Display name | Source path |
| --- | --- | --- |
| `sib` | SIB | `SIB/metrics_v2.tex` |
""",
        encoding="utf-8",
    )

    report = supervisor_module.build_metric_pack_registry_drift(
        {
            "source_registry": {
                "repository": "0al-spec/Metrics",
                "contract_path": "METRIC_PACKS.md",
            },
            "packs": [
                {
                    "metric_pack_id": "sib",
                    "title": "SIB",
                    "source": {"path": "SIB/metrics.tex"},
                }
            ],
        },
        {
            "entries": [
                {
                    "repo_url": "https://github.com/0al-spec/Metrics",
                    "local_checkout": {
                        "status": "available",
                        "checkout_path": str(metrics_root),
                    },
                }
            ],
        },
    )

    assert report["review_state"] == "ready_for_review"
    assert report["next_gap"] == "review_metric_pack_registry_drift"
    assert report["summary"]["status_counts"] == {"source_path_mismatch": 1}
    assert report["entries"][0]["subject_id"] == "sib"
    assert report["entries"][0]["specgraph_value"] == "SIB/metrics.tex"
    assert report["entries"][0]["metrics_value"] == "SIB/metrics_v2.tex"


def test_metric_pack_registry_drift_reports_missing_checkout(
    supervisor_module: object,
) -> None:
    report = supervisor_module.build_metric_pack_registry_drift(
        {
            "source_registry": {
                "repository": "0al-spec/Metrics",
                "contract_path": "METRIC_PACKS.md",
            },
            "packs": [
                {
                    "metric_pack_id": "sib",
                    "title": "SIB",
                    "source": {"path": "SIB/metrics.tex"},
                }
            ],
        },
        {"entries": []},
    )

    assert report["entry_count"] == 1
    assert report["entries"][0]["drift_status"] == "missing_checkout"
    assert report["entries"][0]["next_gap"] == "provide_metrics_checkout"
    assert report["summary"]["status_counts"] == {"missing_checkout": 1}


def test_main_builds_metric_pack_registry_drift_as_standalone_command(
    supervisor_module: object,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    monkeypatch.setattr(supervisor_module, "ROOT", tmp_path)
    monkeypatch.setattr(supervisor_module, "RUNS_DIR", runs_dir)
    monkeypatch.setattr(
        supervisor_module,
        "load_metric_pack_registry",
        lambda: {"source_registry": {"repository": "0al-spec/Metrics"}, "packs": []},
    )
    monkeypatch.setattr(
        supervisor_module,
        "build_external_consumer_index",
        lambda: {"generated_at": "2026-05-01T00:00:00Z", "entries": []},
    )

    exit_code = supervisor_module.main(build_metric_pack_registry_drift_mode=True)

    assert exit_code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["artifact_kind"] == "metric_pack_registry_drift"
    assert report["entry_count"] == 1
    artifact = json.loads((runs_dir / "metric_pack_registry_drift.json").read_text())
    assert artifact["entries"][0]["drift_status"] == "missing_checkout"
