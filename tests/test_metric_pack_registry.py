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
    assert "spec_graph" in by_id["sib"]["inputs"]
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
    assert (
        report["source_snapshot"]["artifact_path"]
        == supervisor_module.METRIC_PACK_REGISTRY_DRIFT_RELATIVE_PATH
    )
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


def test_metric_pack_adapter_index_maps_available_and_missing_inputs(
    supervisor_module: object,
) -> None:
    report = supervisor_module.build_metric_pack_adapter_index(
        {
            "artifact_kind": "metric_pack_index",
            "generated_at": "2026-05-01T00:00:00Z",
            "entry_count": 2,
            "entries": [
                {
                    "metric_pack_id": "sib",
                    "title": "SIB",
                    "pack_status": "ready_for_index_review",
                    "pack_authority_state": "operational_source_after_review",
                    "reference_state": "stable_reference",
                    "metric_count": 1,
                    "inputs": ["spec_graph", "implementation_work", "runtime_events"],
                    "metrics": [
                        {
                            "metric_id": "sib",
                            "requires": ["specification_signal", "implementation_signal"],
                        }
                    ],
                },
                {
                    "metric_pack_id": "sib_full",
                    "title": "SIB Full Metrics",
                    "pack_status": "draft_visible_only",
                    "pack_authority_state": "not_threshold_authority",
                    "reference_state": "draft_reference",
                    "metric_count": 1,
                    "inputs": ["spec_graph", "trace_plane", "implementation_work"],
                    "metrics": [
                        {
                            "metric_id": "sib_eff_star",
                            "requires": [
                                "intent_atoms",
                                "expected_implementation_potential",
                            ],
                        }
                    ],
                },
            ],
        }
    )

    assert report["artifact_kind"] == "metric_pack_adapter_index"
    assert report["schema_version"] == 1
    assert report["entry_count"] == 2
    assert report["canonical_mutations_allowed"] is False
    assert report["tracked_artifacts_written"] is False
    by_id = {entry["metric_pack_id"]: entry for entry in report["entries"]}

    assert by_id["sib"]["adapter_status"] == "ready_for_adapter_review"
    assert by_id["sib"]["missing_input_count"] == 0
    assert by_id["sib"]["adapter_execution"] == {
        "status": "deferred",
        "next_gap": "add_metric_pack_execution_runtime",
    }

    assert by_id["sib_full"]["adapter_status"] == "missing_input_adapters"
    assert by_id["sib_full"]["missing_inputs"] == [
        "expected_implementation_potential",
        "intent_atoms",
    ]
    assert report["adapter_backlog"]["entry_count"] == 2
    assert report["summary"]["status_counts"] == {
        "missing_input_adapters": 1,
        "ready_for_adapter_review": 1,
    }
    assert report["viewer_projection"]["missing_inputs"] == {
        "expected_implementation_potential": ["sib_full"],
        "intent_atoms": ["sib_full"],
    }


def test_metric_pricing_provenance_declares_economic_guardrail(
    supervisor_module: object,
) -> None:
    report = supervisor_module.build_metric_pricing_provenance()

    assert report["artifact_kind"] == "metric_pricing_provenance"
    assert report["schema_version"] == 1
    assert report["canonical_mutations_allowed"] is False
    assert report["tracked_artifacts_written"] is False
    assert report["summary"]["status_counts"] == {"missing_price_source": 1}
    surface = report["pricing_surfaces"][0]
    assert surface["pricing_surface_id"] == "codex_supervisor_default_model"
    assert surface["model"] == supervisor_module.CHILD_EXECUTOR_MODEL
    assert surface["unit_convention"] == "model_token_usage"
    assert surface["currency"] == "internal_proxy_unit"
    assert surface["missing_price_behavior"] == "report_observation_gap"
    assert surface["next_gap"] == "connect_model_usage_telemetry"


def test_metric_pack_adapter_index_maps_pricing_surface_to_provenance(
    supervisor_module: object,
) -> None:
    report = supervisor_module.build_metric_pack_adapter_index(
        {
            "artifact_kind": "metric_pack_index",
            "generated_at": "2026-05-01T00:00:00Z",
            "entry_count": 1,
            "entries": [
                {
                    "metric_pack_id": "sib_economic_observability",
                    "title": "SIB Economic Observability",
                    "pack_status": "draft_visible_only",
                    "pack_authority_state": "not_threshold_authority",
                    "reference_state": "draft_reference",
                    "metric_count": 1,
                    "inputs": ["pricing_surface"],
                    "metrics": [
                        {
                            "metric_id": "node_inference_cost",
                            "requires": ["model_usage", "pricing_surface"],
                        }
                    ],
                }
            ],
        }
    )

    entry = report["entries"][0]
    by_input = {item["input_id"]: item for item in entry["inputs"]}
    assert by_input["pricing_surface"]["computability"] == "available"
    assert by_input["pricing_surface"]["source_artifact"] == "runs/metric_pricing_provenance.json"
    assert by_input["model_usage"]["computability"] == "not_computable"
    assert entry["missing_inputs"] == ["model_usage"]


def test_metric_pack_runs_computes_available_signal_and_preserves_gaps(
    supervisor_module: object,
) -> None:
    metric_pack_index = {
        "artifact_kind": "metric_pack_index",
        "generated_at": "2026-05-01T00:00:00Z",
        "entry_count": 2,
        "entries": [
            {
                "metric_pack_id": "sib",
                "title": "SIB",
                "pack_status": "ready_for_index_review",
                "pack_authority_state": "operational_source_after_review",
                "reference_state": "stable_reference",
                "metrics": [{"metric_id": "sib", "label": "SIB", "kind": "diagnostic"}],
            },
            {
                "metric_pack_id": "sib_full",
                "title": "SIB Full Metrics",
                "pack_status": "draft_visible_only",
                "pack_authority_state": "not_threshold_authority",
                "reference_state": "draft_reference",
                "metrics": [{"metric_id": "sib_eff_star", "label": "Effective SIB"}],
            },
        ],
    }
    adapter_index = {
        "artifact_kind": "metric_pack_adapter_index",
        "generated_at": "2026-05-01T00:00:01Z",
        "entry_count": 2,
        "entries": [
            {
                "metric_pack_id": "sib",
                "adapter_status": "ready_for_adapter_review",
                "inputs": [{"input_id": "spec_graph", "computability": "available"}],
                "missing_inputs": [],
                "next_gap": "review_metric_pack_adapter_index",
            },
            {
                "metric_pack_id": "sib_full",
                "adapter_status": "missing_input_adapters",
                "inputs": [{"input_id": "intent_atoms", "computability": "not_computable"}],
                "missing_inputs": ["intent_atoms"],
                "next_gap": "define_intent_atom_extraction",
            },
        ],
    }
    metric_signal_index = {
        "artifact_kind": "metric_signal_index",
        "generated_at": "2026-05-01T00:00:02Z",
        "entry_count": 2,
        "metrics": [
            {
                "metric_id": "sib",
                "score": 0.82,
                "minimum_score": 0.7,
                "threshold_gap": 0.0,
                "status": "healthy",
                "signal_emitted": False,
                "threshold_authority_state": "canonical_threshold_authority",
            },
            {
                "metric_id": "sib_eff_star",
                "score": 0.4,
                "minimum_score": 0.7,
                "threshold_gap": 0.3,
                "status": "below_threshold",
                "signal_emitted": True,
                "threshold_authority_state": "not_threshold_authority",
            },
        ],
    }

    report = supervisor_module.build_metric_pack_runs(
        metric_pack_index,
        adapter_index,
        metric_signal_index,
    )

    assert report["artifact_kind"] == "metric_pack_runs"
    assert report["schema_version"] == 1
    assert report["canonical_mutations_allowed"] is False
    assert report["tracked_artifacts_written"] is False
    assert report["summary"] == {
        "pack_count": 2,
        "run_status_counts": {"computed": 1, "not_computable": 1},
        "computed_value_count": 1,
        "gap_count": 1,
    }
    by_id = {entry["metric_pack_id"]: entry for entry in report["entries"]}
    assert by_id["sib"]["run_status"] == "computed"
    assert by_id["sib"]["computed_values"][0]["metric_id"] == "sib"
    assert by_id["sib"]["computed_values"][0]["score"] == 0.82
    assert by_id["sib"]["finding_projection"] == {
        "status": "deferred",
        "next_gap": "add_metric_pack_finding_index",
    }
    assert by_id["sib_full"]["run_status"] == "not_computable"
    assert by_id["sib_full"]["computed_values"] == []
    assert by_id["sib_full"]["gaps"][0]["gap_status"] == "missing_input_adapter"
    assert report["viewer_projection"]["run_status"]["computed"] == ["sib"]
    assert report["viewer_projection"]["named_filters"]["proposal_pressure_deferred"] == [
        "sib",
        "sib_full",
    ]


def test_metric_pack_runs_keep_adapter_root_cause_for_non_ready_contracts(
    supervisor_module: object,
) -> None:
    report = supervisor_module.build_metric_pack_runs(
        {
            "entries": [
                {
                    "metric_pack_id": "broken_pack",
                    "title": "Broken Pack",
                    "metrics": [{"metric_id": "missing_metric"}],
                },
                {
                    "metric_pack_id": "stale_pack",
                    "title": "Stale Pack",
                    "metrics": [{"metric_id": "stale_metric"}],
                },
            ],
        },
        {
            "entries": [
                {
                    "metric_pack_id": "broken_pack",
                    "adapter_status": "invalid_pack_contract",
                    "missing_inputs": [],
                    "next_gap": "repair_metric_pack_contract",
                },
                {
                    "metric_pack_id": "stale_pack",
                    "adapter_status": "stale_input_adapters",
                    "missing_inputs": [],
                    "next_gap": "refresh_metric_pack_input_adapter",
                },
            ],
        },
        {
            "metrics": [
                {"metric_id": "stale_metric", "score": 0.5},
            ],
        },
    )

    by_id = {entry["metric_pack_id"]: entry for entry in report["entries"]}
    assert by_id["broken_pack"]["run_status"] == "invalid_pack_contract"
    assert by_id["broken_pack"]["next_gap"] == "repair_metric_pack_contract"
    assert by_id["broken_pack"]["gaps"][0]["gap_status"] == "invalid_pack_contract"
    assert by_id["stale_pack"]["run_status"] == "not_computable"
    assert by_id["stale_pack"]["next_gap"] == "refresh_metric_pack_input_adapter"
    assert by_id["stale_pack"]["computed_values"] == []
    assert by_id["stale_pack"]["gaps"][0]["gap_status"] == "stale_input_adapters"
    assert report["summary"]["computed_value_count"] == 0


def test_main_builds_metric_pack_adapter_index_as_standalone_command(
    supervisor_module: object,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    monkeypatch.setattr(supervisor_module, "ROOT", tmp_path)
    monkeypatch.setattr(supervisor_module, "RUNS_DIR", runs_dir)
    monkeypatch.setattr(supervisor_module, "load_metric_pack_registry", lambda: {"packs": []})
    monkeypatch.setattr(
        supervisor_module,
        "build_external_consumer_index",
        lambda: {"generated_at": "2026-05-01T00:00:00Z", "entries": []},
    )

    exit_code = supervisor_module.main(build_metric_pack_adapter_index_mode=True)

    assert exit_code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["artifact_kind"] == "metric_pack_adapter_index"
    artifact = json.loads((runs_dir / "metric_pack_adapter_index.json").read_text())
    assert artifact["artifact_kind"] == "metric_pack_adapter_index"


def test_main_builds_metric_pack_runs_as_standalone_command(
    supervisor_module: object,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    monkeypatch.setattr(supervisor_module, "ROOT", tmp_path)
    monkeypatch.setattr(supervisor_module, "RUNS_DIR", runs_dir)
    monkeypatch.setattr(supervisor_module, "load_specs", lambda: [object()])
    monkeypatch.setattr(supervisor_module, "build_external_consumer_index", lambda: {})
    monkeypatch.setattr(
        supervisor_module,
        "build_metric_signal_index",
        lambda specs: {
            "artifact_kind": "metric_signal_index",
            "generated_at": "2026-05-01T00:00:00Z",
            "entry_count": 1,
            "metrics": [{"metric_id": "sib", "score": 0.9, "status": "healthy"}],
        },
    )
    monkeypatch.setattr(
        supervisor_module,
        "load_metric_pack_registry",
        lambda: {
            "packs": [
                {
                    "metric_pack_id": "sib",
                    "title": "SIB",
                    "consumer_id": "metrics_sib",
                    "reference_state": "stable_reference",
                    "pack_authority_state": "operational_source_after_review",
                    "lifecycle_state": "active",
                    "source": {"path": "SIB/metrics.tex"},
                    "inputs": ["spec_graph"],
                    "metrics": [{"metric_id": "sib", "requires": ["specification_signal"]}],
                }
            ]
        },
    )

    exit_code = supervisor_module.main(build_metric_pack_runs_mode=True)

    assert exit_code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["artifact_kind"] == "metric_pack_runs"
    assert report["summary"]["computed_value_count"] == 1
    artifact = json.loads((runs_dir / "metric_pack_runs.json").read_text())
    assert artifact["entries"][0]["metric_pack_id"] == "sib"


def test_main_builds_metric_pricing_provenance_as_standalone_command(
    supervisor_module: object,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    monkeypatch.setattr(supervisor_module, "ROOT", tmp_path)
    monkeypatch.setattr(supervisor_module, "RUNS_DIR", runs_dir)

    exit_code = supervisor_module.main(build_metric_pricing_provenance_mode=True)

    assert exit_code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["artifact_kind"] == "metric_pricing_provenance"
    artifact = json.loads((runs_dir / "metric_pricing_provenance.json").read_text())
    assert artifact["pricing_surfaces"][0]["missing_price_behavior"] == ("report_observation_gap")
