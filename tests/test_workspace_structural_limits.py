"""Workspace structural limits preserve defaults and isolate run evidence."""

import json

import pytest


def configure(module, monkeypatch, tmp_path, values, **section):
    monkeypatch.setattr(module, "ROOT", tmp_path)
    config = {
        "artifact_kind": "specgraph_project_config",
        "schema_version": 1,
        "supervisor": {"structural_limits": {"schema_version": 1, "thresholds": values, **section}},
    }
    (tmp_path / "specgraph.project.yaml").write_text(json.dumps(config))


def node(module, count):
    return module.SpecNode(
        path=module.ROOT / "specs/nodes/ZEU-SPEC-0009.yaml",
        data={
            "id": "ZEU-SPEC-0009",
            "kind": "spec",
            "status": "specified",
            "acceptance": [f"Criterion {i}" for i in range(count)],
            "depends_on": [],
        },
    )


def test_default_atomicity_is_characterized(supervisor_module, monkeypatch, tmp_path):
    monkeypatch.setattr(supervisor_module, "ROOT", tmp_path)
    assert supervisor_module.validate_atomicity(node(supervisor_module, 5)) == []
    assert (
        "6 acceptance criteria > 5"
        in supervisor_module.validate_atomicity(node(supervisor_module, 6))[0]
    )


def test_workspace_override_and_default_fallback(supervisor_module, monkeypatch, tmp_path):
    configure(supervisor_module, monkeypatch, tmp_path, {"atomicity_max_acceptance": 8})
    assert supervisor_module.validate_atomicity(node(supervisor_module, 7)) == []
    assert supervisor_module.structural_threshold("atomicity_max_blocking_children") == 3
    assert (
        "9 acceptance criteria > 8"
        in supervisor_module.validate_atomicity(node(supervisor_module, 9))[0]
    )


@pytest.mark.parametrize("value", [True, False, 0, -1, 5.0, "8", None])
def test_invalid_counts_fail_closed(supervisor_module, monkeypatch, tmp_path, value):
    configure(supervisor_module, monkeypatch, tmp_path, {"atomicity_max_acceptance": value})
    with pytest.raises(RuntimeError, match="atomicity_max_acceptance"):
        supervisor_module.structural_threshold("atomicity_max_acceptance")


@pytest.mark.parametrize(
    "thresholds",
    [
        {"unknown": 8},
        {"linked_continuation_maturity": 0.1},
        {"refinement_fan_out_grouped_child_coverage": 1.1},
        {"subtree_shape_min_single_child_ratio": float("nan")},
    ],
)
def test_unknown_and_invalid_ratios_rejected(supervisor_module, monkeypatch, tmp_path, thresholds):
    configure(supervisor_module, monkeypatch, tmp_path, thresholds)
    with pytest.raises(RuntimeError):
        supervisor_module.structural_limits()


def test_snapshot_is_stable_and_restored(supervisor_module, monkeypatch, tmp_path):
    configure(supervisor_module, monkeypatch, tmp_path, {"atomicity_max_acceptance": 8})
    with supervisor_module.structural_limits_scope():
        before = supervisor_module.structural_limits().evidence()
        configure(supervisor_module, monkeypatch, tmp_path, {"atomicity_max_acceptance": 9})
        assert supervisor_module.structural_threshold("atomicity_max_acceptance") == 8
        assert supervisor_module.structural_limits().evidence() == before
        assert supervisor_module.build_project_environment()["structural_limits"] == before
    assert supervisor_module.structural_threshold("atomicity_max_acceptance") == 9
    monkeypatch.setattr(supervisor_module, "ROOT", tmp_path / "other")
    assert supervisor_module.structural_threshold("atomicity_max_acceptance") == 5


def test_run_log_records_effective_limits(supervisor_module, monkeypatch, tmp_path):
    configure(supervisor_module, monkeypatch, tmp_path, {"atomicity_max_acceptance": 8})
    monkeypatch.setattr(supervisor_module, "RUNS_DIR", tmp_path / "runs")
    payload = {"run_id": "sample"}
    path = supervisor_module.write_run_log("sample", payload)
    saved = json.loads(path.read_text())
    evidence = saved["structural_limits"]
    assert evidence["effective_thresholds"]["atomicity_max_acceptance"] == 8
    assert evidence["sources"]["atomicity_max_acceptance"] == "workspace"
    assert len(evidence["source_config"]["artifact_sha256"]) == 64
    assert len(evidence["effective_sha256"]) == 64
    assert {entry["outcome"] for entry in evidence["specification_trace"]} <= {
        "selected",
        "satisfied",
        "unsatisfied",
        "skipped",
    }
    assert any(
        entry["rule_id"]
        == "SG-RFC-0222.structural_limits.atomicity_max_acceptance.positive_integer"
        for entry in evidence["specification_trace"]
    )
    assert payload == {"run_id": "sample"}


def test_main_rejects_bad_config_before_loading_specs(supervisor_module, monkeypatch, tmp_path):
    configure(supervisor_module, monkeypatch, tmp_path, {"atomicity_max_acceptance": True})
    monkeypatch.setattr(supervisor_module, "load_specs", lambda: pytest.fail("loaded specs"))
    assert supervisor_module.main(dry_run=True) == 1


def test_diagnosis_uses_historical_snapshot(supervisor_module, monkeypatch, tmp_path):
    configure(supervisor_module, monkeypatch, tmp_path, {"atomicity_max_acceptance": 8})
    evidence = supervisor_module.structural_limits().evidence()
    configure(supervisor_module, monkeypatch, tmp_path, {"atomicity_max_acceptance": 5})
    monkeypatch.setattr(supervisor_module, "canonical_acceptance_count_for_spec", lambda _: 7)
    payload = {
        "spec_id": "ZEU-SPEC-0009",
        "outcome": "split_required",
        "decision_inspector": {"queue_effects": {"proposal_queue": {"emitted_ids": []}}},
        "structural_limits": evidence,
    }
    matched, count, _ = (
        supervisor_module.supervisor_run_has_split_required_candidate_without_proposal_path(payload)
    )
    assert matched and count == 7


@pytest.mark.parametrize(
    "section",
    [
        {"schema_version": True},
        {"schema_version": 2},
        {"surprise": 1},
        {"thresholds": []},
    ],
)
def test_bad_section_schema_rejected(supervisor_module, monkeypatch, tmp_path, section):
    configure(supervisor_module, monkeypatch, tmp_path, {}, **section)
    with pytest.raises(RuntimeError):
        supervisor_module.structural_limits()


def test_large_count_has_no_arbitrary_ceiling(supervisor_module, monkeypatch, tmp_path):
    configure(supervisor_module, monkeypatch, tmp_path, {"atomicity_max_acceptance": 10000})
    assert supervisor_module.structural_threshold("atomicity_max_acceptance") == 10000


def test_prompt_changed_spec_and_inspector_agree(supervisor_module, monkeypatch, tmp_path):
    configure(
        supervisor_module,
        monkeypatch,
        tmp_path,
        {
            "atomicity_max_acceptance": 8,
            "atomicity_max_blocking_children": 7,
        },
    )
    candidate = node(supervisor_module, 7)
    monkeypatch.setattr(supervisor_module, "load_specs", lambda: [candidate])
    prompt = supervisor_module.build_prompt(candidate)
    assert '"atomicity_max_acceptance": 8' in prompt
    assert '"atomicity_max_blocking_children": 7' in prompt
    assert (
        supervisor_module.validate_changed_spec_atomicity(
            source_node_id=candidate.id,
            changed_files=["specs/nodes/ZEU-SPEC-0009.yaml"],
            worktree_specs=[candidate],
            worktree_path=tmp_path,
        )
        == []
    )
    rule = supervisor_module.policy_rule("thresholds.atomicity_max_acceptance", reason="test")
    assert rule["matched_value"] == 8
    assert (
        supervisor_module.supervisor_policy_reference()["structural_limits"][
            "effective_thresholds"
        ]["atomicity_max_acceptance"]
        == 8
    )


def test_environment_discovery_uses_explicit_config_path(supervisor_module, tmp_path):
    path = tmp_path / "specgraph.project.yaml"
    path.write_text(
        json.dumps(
            {
                "artifact_kind": "specgraph_project_config",
                "schema_version": 1,
                "supervisor": {
                    "structural_limits": {
                        "schema_version": 1,
                        "thresholds": {"atomicity_max_acceptance": 9},
                    }
                },
            }
        )
    )
    report = supervisor_module.build_project_environment(config_path=path)
    assert report["structural_limits"]["effective_thresholds"]["atomicity_max_acceptance"] == 9


def test_corrupt_historical_digest_is_rejected(supervisor_module, monkeypatch, tmp_path):
    configure(supervisor_module, monkeypatch, tmp_path, {"atomicity_max_acceptance": 8})
    evidence = supervisor_module.structural_limits().evidence()
    evidence["effective_thresholds"]["atomicity_max_acceptance"] = 9
    with pytest.raises(RuntimeError, match="digest mismatch"):
        supervisor_module.run_structural_threshold(
            {"structural_limits": evidence}, "atomicity_max_acceptance"
        )


def test_null_historical_snapshot_is_not_legacy(supervisor_module):
    with pytest.raises(RuntimeError, match="null"):
        supervisor_module.run_structural_threshold(
            {"structural_limits": None}, "atomicity_max_acceptance"
        )


def test_other_graph_budgets_are_workspace_scoped(supervisor_module, monkeypatch, tmp_path):
    configure(
        supervisor_module,
        monkeypatch,
        tmp_path,
        {
            "atomicity_max_blocking_children": 9,
            "subtree_shape_one_child_chain": 10,
            "refinement_fan_out_direct_children": 10,
            "graph_layer_exhausted_chain": 12,
            "over_atomized_acceptance_max": 4,
            "refinement_fan_out_grouped_child_coverage": 0.9,
            "refinement_fan_out_parent_aggregate_floor": 0.7,
            "subtree_shape_min_single_child_ratio": 0.8,
        },
    )
    candidate = node(supervisor_module, 1)
    monkeypatch.setattr(
        supervisor_module, "active_refining_child_specs", lambda *_: [candidate] * 4
    )
    assert (
        supervisor_module.fan_out_legibility_profile(candidate, [candidate])["classification"]
        == "not_applicable"
    )
    candidate.data["depends_on"] = [f"ZEU-SPEC-{i:04d}" for i in range(20, 29)]
    assert supervisor_module.validate_atomicity(candidate) == []
    candidate.data["depends_on"].append("ZEU-SPEC-0029")
    assert "10 blocking children > 9" in supervisor_module.validate_atomicity(candidate)[0]


def test_entry_scope_restores_after_exception(supervisor_module, monkeypatch, tmp_path):
    configure(supervisor_module, monkeypatch, tmp_path, {"atomicity_max_acceptance": 8})

    @supervisor_module.with_structural_limits
    def run():
        configure(supervisor_module, monkeypatch, tmp_path, {"atomicity_max_acceptance": 9})
        assert supervisor_module.structural_threshold("atomicity_max_acceptance") == 8
        raise RuntimeError("executor failure")

    with pytest.raises(RuntimeError, match="executor failure"):
        run()
    assert supervisor_module.structural_threshold("atomicity_max_acceptance") == 9
