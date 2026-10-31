"""False-green controls for the bounded model; real tool runs are opt-in.

Integration tests require ONTOLOGYC_BINARY_PATH and TYPESCRIPT_TSC_PATH.
Use the checkout's configured external pytest basetemp for local runs; all
mutations and compiler output stay beneath pytest's temporary directory.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
AUTHORED_MODEL = ROOT / "specs/models/SG-SPEC-0072"
SOURCE = ROOT / "specs/nodes/SG-SPEC-0072.yaml"
RUNNER = ROOT / "tools/local_ontology_pilot.py"
sys.path.insert(0, str(ROOT / "tools"))
import local_ontology_pilot as pilot  # noqa: E402


def source_inputs():
    source = SOURCE.read_bytes()
    return (
        json.loads((AUTHORED_MODEL / "source-map.json").read_bytes()),
        yaml.safe_load(source),
        source,
    )


def test_source_mapping_accepts_the_partial_authored_inventory_without_mutation():
    mapping, document, source = source_inputs()
    before = deepcopy((mapping, document))
    pilot.source_mapping(mapping, document, source)
    assert (mapping, document) == before


@pytest.mark.parametrize(
    ("mutation", "finding_path"),
    [
        ("missing_acceptance_row", "source-map.json/acceptance"),
        ("erase_partial_status", "source-map.json/acceptance"),
        ("missing_source_clause", "source-map.json/source_fragments"),
        ("unrelated_existing_pointer", "source-map.json/source_fragments"),
        ("stale_source_hash", "source-map.json/source_sha256"),
        ("missing_required_check", "source-map.json/expected"),
        ("wrong_expected_outcome", "source-map.json/expected"),
    ],
)
def test_source_mapping_cannot_shrink_or_relabel_the_claim(mutation, finding_path):
    mapping, document, source = source_inputs()
    if mutation == "missing_acceptance_row":
        mapping["acceptance"].pop(2)
    elif mutation == "erase_partial_status":
        mapping["acceptance"][2]["status"] = "unmodelled"
    elif mutation == "missing_source_clause":
        mapping["source_fragments"].pop()
    elif mutation == "unrelated_existing_pointer":
        # An existing pointer and an exact quote are insufficient if the
        # mixed-outcome source obligation has been replaced with unrelated text.
        mapping["source_fragments"][0] = {"pointer": "/title", "quote": document["title"]}
    elif mutation == "stale_source_hash":
        mapping["source_sha256"] = "0" * 64
    elif mutation == "missing_required_check":
        mapping["expected"]["checks"].pop(0)
    elif mutation == "wrong_expected_outcome":
        mapping["expected"]["outcome"] = "unavailable"
    with pytest.raises(pilot.PilotFailure) as caught:
        pilot.source_mapping(mapping, document, source)
    assert caught.value.layer == "model"
    assert caught.value.path == finding_path


def test_a_new_hash_cannot_relabel_a_different_source_specification():
    mapping, _, source = source_inputs()
    source = source.replace(b"id: SG-SPEC-0072", b"id: SG-SPEC-9999", 1)
    document = yaml.safe_load(source)
    assert document["id"] == "SG-SPEC-9999"
    mapping["source_sha256"] = pilot.digest(source)
    with pytest.raises(pilot.PilotFailure) as caught:
        pilot.source_mapping(mapping, document, source)
    assert caught.value.layer == "model"
    assert caught.value.path == "spec.yaml/id"


@pytest.fixture(scope="module")
def real_tools():
    names = ("ONTOLOGYC_BINARY_PATH", "TYPESCRIPT_TSC_PATH")
    missing = [name for name in names if not os.environ.get(name)]
    if missing:
        pytest.skip("Real ontologyc/TypeScript integration requires " + ", ".join(missing))
    paths = tuple(Path(os.environ[name]).expanduser().resolve() for name in names)
    for name, path in zip(names, paths, strict=True):
        assert path.is_file(), f"{name} does not name an existing tool: {path}"
    assert os.access(paths[0], os.X_OK), "ONTOLOGYC_BINARY_PATH must be executable"
    assert shutil.which("node"), "Configured TypeScript integration requires Node.js"
    return paths


@pytest.fixture
def copied_model(tmp_path):
    return Path(shutil.copytree(AUTHORED_MODEL, tmp_path / "authored-model"))


def run_cli(real_tools, model_dir, work_dir, *extra):
    compiler, tsc = real_tools
    completed = subprocess.run(
        [
            sys.executable,
            "-B",
            str(RUNNER),
            "--ontologyc",
            str(compiler),
            "--tsc",
            str(tsc),
            "--model-dir",
            str(model_dir),
            "--work-dir",
            str(work_dir),
            *extra,
        ],
        cwd=ROOT,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    return completed


def read_report(completed, work):
    report_path = work / "report.json"
    assert report_path.is_file(), completed.stdout + completed.stderr
    return json.loads(report_path.read_bytes())


def replace_once(model_dir, old, new, *, filename="model.ts"):
    path = model_dir / filename
    source = path.read_text()
    assert source.count(old) == 1, f"Authored model anchor must be unambiguous: {old!r}"
    path.write_text(source.replace(old, new, 1))


def assert_layer_failure(completed, report, layer):
    assert completed.returncode != 0, report
    assert report["outcome"] == "mismatch", report
    assert report["layers"][layer]["status"] == "failed", report
    assert any(finding["layer"] == layer for finding in report["findings"]), report


def test_real_sdk_and_behavior_preserve_partial_coverage(real_tools, copied_model, tmp_path):
    work = tmp_path / "positive"
    completed = run_cli(real_tools, copied_model, work)
    report = read_report(completed, work)
    assert completed.returncode == 0, report
    assert report["outcome"] == "satisfied"
    assert all(
        report["layers"][name]["status"] == "passed"
        for name in ("compiler", "typecheck", "model", "behavior")
    )
    for generated in ("src/generated/pilot/types.ts", "src/generated/sgcore/types.ts"):
        assert generated in report["generated"]
        assert (work / generated).is_file()
    local_ir = json.loads((work / "src/generated/pilot/ontology.normalized.json").read_bytes())
    assert local_ir["policies"] == []
    assert local_ir["stateMachines"] == []
    assert report["coverage"]["complete"] is False
    assert [(row["pointer"], row["status"]) for row in report["coverage"]["acceptance"]] == [
        ("/acceptance/0", "unmodelled"),
        ("/acceptance/1", "unmodelled"),
        ("/acceptance/2", "partial"),
        ("/acceptance/3", "unmodelled"),
    ]
    assert report["canonical_mutations_allowed"] is False
    assert report["observed"]["outcome"] == "invalid"
    checks = {(item["check"], item["outcome"]): item for item in report["observed"]["checks"]}
    assert checks[("selection", "invalid")]["detail"] == "duplicate package identity or namespace"
    assert (
        checks[("compiler", "unavailable")]["detail"]
        == "operator-provided executable is unavailable"
    )
    assert all(command["returncode"] == 0 for command in report["commands"])


@pytest.mark.parametrize("mutation", ["required_field", "unknown_type", "unknown_relation"])
def test_real_typescript_rejects_sdk_contract_violations(
    real_tools, copied_model, tmp_path, mutation
):
    if mutation == "required_field":
        replace_once(copied_model, '  expectedOutcome: "invalid",\n', "")
    elif mutation == "unknown_type":
        replace_once(
            copied_model,
            "CheckResult, ContextVerificationCase",
            "UnknownCheckResult, ContextVerificationCase",
        )
    else:
        replace_once(
            copied_model,
            'relations.caseIncludesCheck.alias, from: scenario.id, to: "duplicate-selection"',
            'relations.unknownRelation.alias, from: scenario.id, to: "duplicate-selection"',
        )
    work = tmp_path / "sdk-rejection"
    completed = run_cli(real_tools, copied_model, work)
    report = read_report(completed, work)
    assert report["layers"]["compiler"]["status"] == "passed", report
    assert_layer_failure(completed, report, "typecheck")
    tsc = next(command for command in report["commands"] if command["name"] == "typescript-model")
    assert tsc["returncode"] != 0
    diagnostic = (work / tsc["stdout"]).read_text() + (work / tsc["stderr"]).read_text()
    assert re.search(r"error TS\d+:", diagnostic), diagnostic
    assert report["layers"]["behavior"]["status"] == "not_run"


@pytest.mark.parametrize(
    "mutation",
    [
        "wrong_endpoint",
        "wrong_outcome",
        "empty_diagnostic",
        "removed_check",
        "wrong_spec_id",
        "missing_spec_link",
    ],
)
def test_type_correct_models_cannot_omit_required_meaning(
    real_tools, copied_model, tmp_path, mutation
):
    if mutation == "wrong_endpoint":
        replace_once(
            copied_model,
            'relations.caseIncludesCheck.alias, from: scenario.id, to: "duplicate-selection"',
            'relations.caseIncludesCheck.alias, from: scenario.id, to: "SG72-OUTCOME-PRECEDENCE"',
        )
    elif mutation == "wrong_outcome":
        replace_once(
            copied_model, '  expectedOutcome: "invalid",', '  expectedOutcome: "unavailable",'
        )
    elif mutation == "empty_diagnostic":
        replace_once(
            copied_model, 'detail: "duplicate package identity or namespace"', 'detail: ""'
        )
    elif mutation == "removed_check":
        replace_once(
            copied_model,
            '  {\n    $type: classes.CheckResult.alias, id: "missing-compiler",\n'
            '    check: "compiler", outcome: "unavailable",\n'
            '    detail: "operator-provided executable is unavailable",\n  },\n',
            "",
        )
        replace_once(
            copied_model,
            "  { relation: relations.caseIncludesCheck.alias, from: scenario.id, "
            'to: "missing-compiler" },\n',
            "",
        )
    elif mutation == "wrong_spec_id":
        replace_once(
            copied_model, 'id: "SG-SPEC-0072"', 'id: "SG-SPEC-9999"', filename="case-model.ts"
        )
    else:
        replace_once(
            copied_model,
            "  { relation: coreRelations.definesRequirement.alias, "
            "from: specification.id, to: requirement.id },\n",
            "",
            filename="case-model.ts",
        )
    work = tmp_path / "model-rejection"
    completed = run_cli(real_tools, copied_model, work)
    report = read_report(completed, work)
    assert report["layers"]["compiler"]["status"] == "passed", report
    assert report["layers"]["typecheck"]["status"] == "passed", report
    assert_layer_failure(completed, report, "model")
    assert report["layers"]["behavior"]["status"] == "not_run"


def test_well_formed_model_still_has_to_match_observed_behavior(real_tools, copied_model, tmp_path):
    replace_once(
        copied_model,
        'detail: "duplicate package identity or namespace"',
        'detail: "a different, nonempty expected diagnostic"',
    )
    work = tmp_path / "behavior-rejection"
    completed = run_cli(real_tools, copied_model, work)
    report = read_report(completed, work)
    for layer in ("compiler", "typecheck", "model"):
        assert report["layers"][layer]["status"] == "passed", report
    assert_layer_failure(completed, report, "behavior")
    assert report["observed"]["outcome"] == "invalid"
    assert any(
        finding["path"] == "model.ts/checks/duplicate-selection" for finding in report["findings"]
    )


def test_cli_rejects_a_stale_source_map_before_compilation(real_tools, copied_model, tmp_path):
    path = copied_model / "source-map.json"
    mapping = json.loads(path.read_bytes())
    mapping["source_sha256"] = "0" * 64
    path.write_text(json.dumps(mapping))
    work = tmp_path / "stale-mapping"
    completed = run_cli(real_tools, copied_model, work)
    report = read_report(completed, work)
    assert_layer_failure(completed, report, "model")
    assert report["commands"] == []
    assert report["layers"]["compiler"]["status"] == "not_run"


def test_cli_preserves_preexisting_work_directory(real_tools, copied_model, tmp_path):
    work = tmp_path / "existing"
    work.mkdir()
    receipt = work / "report.json"
    original = b'{"valuable":"previous result"}\n'
    receipt.write_bytes(original)
    completed = run_cli(real_tools, copied_model, work)
    assert completed.returncode != 0
    assert "new or empty" in completed.stderr
    assert receipt.read_bytes() == original
    assert list(work.iterdir()) == [receipt]


def test_closure_map_cannot_borrow_mixed_case_obligations():
    scenario = pilot.CASES["SG72-UNSUPPORTED-CLOSURE"]
    mixed, document, source = source_inputs()
    mapping = json.loads((AUTHORED_MODEL / scenario.mapping).read_bytes())
    pilot.source_mapping(mapping, document, source, scenario)
    for field in ("source_fragments", "expected", "scenario_id"):
        with pytest.raises(pilot.PilotFailure):
            pilot.source_mapping({**mapping, field: mixed[field]}, document, source, scenario)


def test_verified_member_with_unsupported_closure(real_tools, copied_model, tmp_path):
    work = tmp_path / "closure"
    scenario = "SG72-UNSUPPORTED-CLOSURE"
    completed = run_cli(real_tools, copied_model, work, "--scenario", scenario)
    report = read_report(completed, work)
    assert completed.returncode == 0, report
    assert report["scenario_id"] == scenario
    assert report["outcome"] == "satisfied"
    assert all(layer["status"] == "passed" for layer in report["layers"].values())
    assert report["coverage"]["complete"] is False
    observed = report["observed"]
    assert observed["outcome"] == "unavailable"
    [snapshot] = observed["snapshots"]
    assert snapshot["compiler_sha256"] == report["tools"]["ontologyc"]["sha256"]
    assert {
        (check["check"], check["outcome"])
        for check in observed["checks"]
        if check["package"] == snapshot["id"]
    } >= {("member_capture", "verified"), ("dependency_closure", "unavailable")}


def test_type_correct_reversed_closure_link_is_rejected(real_tools, copied_model, tmp_path):
    replace_once(
        copied_model,
        'from: "unsupported-closure", to: "captured-member"',
        'from: "captured-member", to: "unsupported-closure"',
        filename="unsupported-closure.ts",
    )
    work = tmp_path / "reversed"
    completed = run_cli(real_tools, copied_model, work, "--scenario", "SG72-UNSUPPORTED-CLOSURE")
    report = read_report(completed, work)
    assert report["layers"]["typecheck"]["status"] == "passed"
    assert_layer_failure(completed, report, "model")
    assert report["findings"][0]["path"] == "model.ts/relations"
    assert report["layers"]["behavior"]["status"] == "not_run"


def test_closure_diagnostic_from_another_member_cannot_satisfy_the_scenario():
    scenario = pilot.CASES["SG72-UNSUPPORTED-CLOSURE"]
    declared = {role: {"id": role[0], "detail": role[0]} for role in scenario.roles}
    checks = [
        {"check": name, "outcome": status, "detail": name, "package": package}
        for (name, status), package in zip(scenario.roles, ("pkg-a", "pkg-b"), strict=True)
    ]
    with pytest.raises(pilot.PilotFailure) as caught:
        pilot.verify_behavior(
            {"outcome": "unavailable", "checks": checks}, scenario, declared, {"id": "pkg-a"}, "sha"
        )
    assert caught.value.layer == "behavior"
    assert caught.value.path == "model.ts/checks/dependency_closure"


def test_verified_member_diagnostic_requires_its_pinned_snapshot():
    scenario = pilot.CASES["SG72-UNSUPPORTED-CLOSURE"]
    member = {
        "id": "core",
        "namespace": "sgcore",
        "version": "0.1.0",
        "source_sha256": "1" * 64,
        "ir_sha256": "2" * 64,
    }
    declared = {role: {"id": role[0], "detail": role[0]} for role in scenario.roles}
    observed = {
        "outcome": "unavailable",
        "snapshots": [{**member, "compiler_sha256": "3" * 64}],
        "checks": [
            {"check": name, "outcome": status, "detail": name, "package": "core"}
            for name, status in scenario.roles
        ],
    }
    with pytest.raises(pilot.PilotFailure) as caught:
        pilot.verify_behavior(observed, scenario, declared, member, "4" * 64)
    assert caught.value.path == "observed/snapshots"


def test_verified_foundation_model_runs_through_all_four_layers(real_tools, copied_model, tmp_path):
    work = tmp_path / "pinned"
    result = run_cli(real_tools, copied_model, work, "--scenario", "SG72-PINNED-FOUNDATION")
    report = read_report(result, work)
    assert result.returncode == 0, report["findings"]
    assert report["scenario_id"] == "SG72-PINNED-FOUNDATION"
    assert all(layer["status"] == "passed" for layer in report["layers"].values())
    assert report["observed"]["outcome"] == "verified"
    assert [
        row["pointer"] for row in report["coverage"]["acceptance"] if row["status"] == "partial"
    ] == ["/acceptance/0", "/acceptance/2"]
    assert report["coverage"]["complete"] is False
