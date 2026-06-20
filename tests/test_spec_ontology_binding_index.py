from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_binding_module() -> object:
    module_path = ROOT / "tools" / "spec_ontology_binding_index.py"
    spec = importlib.util.spec_from_file_location(
        "spec_ontology_binding_index_under_test", module_path
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(module_path.parent))
    try:
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
    finally:
        sys.path.remove(str(module_path.parent))
    return module


def test_legacy_spec_binding_index_reports_existing_corpus() -> None:
    module = load_binding_module()

    index = module.build_binding_index()

    spec_files = sorted((ROOT / "specs" / "nodes").glob("SG-SPEC-*.yaml"))
    assert index["artifact_kind"] == "spec_ontology_binding_index"
    assert index["proposal_id"] == "0134"
    assert index["status"] == "report_only"
    assert index["canonical_mutations_allowed"] is False
    assert index["tracked_artifacts_written"] is False
    assert index["legacy_corpus"] is True
    assert index["ontology_ir_ref"] == (
        "ontology/packages/specgraph-core/generated/ontology.normalized.json"
    )
    assert index["summary"]["spec_count"] == len(spec_files)
    assert index["summary"]["accepted_binding_count"] >= len(spec_files)
    assert index["summary"]["gap_count"] > 0


def test_legacy_spec_binding_index_maps_root_spec_structure() -> None:
    module = load_binding_module()

    index = module.build_binding_index()
    entries = {entry["spec_id"]: entry for entry in index["entries"]}
    root_entry = entries["SG-SPEC-0001"]

    assert root_entry["status"] == "legacy_report_only"
    ontology_refs = {binding["ontology_ref"] for binding in root_entry["accepted_bindings"]}
    assert "sgcore:Spec" in ontology_refs
    assert "sgcore:Node" in ontology_refs
    assert "sgcore:AcceptanceCriterion" in ontology_refs
    assert "sgcore:Evidence" in ontology_refs
    relation_refs = {candidate["relation_ref"] for candidate in root_entry["relation_candidates"]}
    assert "sgcore:hasAcceptanceCriterion" in relation_refs
    assert "sgcore:evidenceSupportsCriterion" in relation_refs
    assert root_entry["gaps"]


def test_legacy_spec_binding_index_matches_camelcase_ontology_ids() -> None:
    module = load_binding_module()

    index = module.build_binding_index()
    entries = {entry["spec_id"]: entry for entry in index["entries"]}
    executable_entry = entries["SG-SPEC-0020"]

    bindings = {
        (binding["term"], binding["ontology_ref"])
        for binding in executable_entry["accepted_bindings"]
    }
    assert ("code_surface", "sgcore:CodeSurface") in bindings
    assert all(
        gap["gap_id"] != "ontology-gap-sg-spec-0020-code-surface"
        for gap in executable_entry["gaps"]
    )


def test_legacy_spec_binding_index_does_not_emit_missing_structural_ir_refs(tmp_path: Path) -> None:
    module = load_binding_module()
    ir_path = tmp_path / "ontology.normalized.json"
    ir_path.write_text(
        json.dumps(
            {
                "classes": [
                    {"id": "Node", "fqid": "sgcore:Node"},
                ],
                "relations": [],
            }
        ),
        encoding="utf-8",
    )

    index = module.build_binding_index(ir_path=ir_path)
    root_entry = {entry["spec_id"]: entry for entry in index["entries"]}["SG-SPEC-0001"]

    ontology_refs = {binding["ontology_ref"] for binding in root_entry["accepted_bindings"]}
    assert "sgcore:Node" in ontology_refs
    assert "sgcore:Spec" not in ontology_refs
    assert "sgcore:AcceptanceCriterion" not in ontology_refs
    assert not root_entry["relation_candidates"]
    assert any(
        gap["classification"] == "missing_ontology_ref" and gap["term"] == "spec"
        for gap in root_entry["gaps"]
    )


def test_legacy_spec_binding_index_write_target_is_runs_only() -> None:
    module = load_binding_module()

    assert module.relative_path(module.DEFAULT_OUTPUT_PATH) == (
        "runs/spec_ontology_binding_index.json"
    )
    assert module.resolve_output_path("runs/custom_binding_index.json") == (
        ROOT / "runs" / "custom_binding_index.json"
    )


def test_legacy_spec_binding_index_rejects_non_runs_output() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "tools" / "spec_ontology_binding_index.py"),
            "--write",
            "--output",
            "specs/nodes/SG-SPEC-0001.yaml",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 2
    assert "--output must stay under runs" in result.stderr
