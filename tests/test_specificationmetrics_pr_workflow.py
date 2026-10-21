from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "specificationmetrics-pr-comment.yml"


def _step_block(workflow: str, step_name: str) -> str:
    marker = f"      - name: {step_name}"
    block = workflow.split(marker, 1)[1]
    return block.split("\n      - name:", 1)[0]


def test_metrics_report_is_bound_to_the_successful_python_ci_head() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    resolve = _step_block(workflow, "Resolve PRs associated with the completed CI head")
    snapshot = _step_block(workflow, "Pin current PR revisions to the successful CI head")

    assert "workflow_head_sha: ${{ steps.resolve.outputs.workflow_head_sha }}" in workflow
    assert 'echo "workflow_head_sha=${HEAD_SHA}" >> "${GITHUB_OUTPUT}"' in resolve
    assert "EXPECTED_HEAD_SHA: ${{ needs.resolve.outputs.workflow_head_sha }}" in snapshot
    assert '[ "${api_head_sha}" != "${EXPECTED_HEAD_SHA}" ]' in snapshot
    assert '[ "${fetched_head}" != "${EXPECTED_HEAD_SHA}" ]' in snapshot
    assert "if: steps.snapshot.outputs.is_current == 'true'" in workflow


def test_scope_manifest_destination_exists_in_each_source_snapshot() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    apply_contract = _step_block(workflow, "Apply the trusted metric contract to both snapshots")

    make_scope_directory = 'mkdir -p "${RUNNER_TEMP}/specificationmetrics/${tree}/scopes"'
    copy_scope_manifest = "cp scopes/specificationmetrics.toml"
    assert make_scope_directory in apply_contract
    assert apply_contract.index(make_scope_directory) < apply_contract.index(copy_scope_manifest)


def report_steps():
    return yaml.safe_load(WORKFLOW.read_text())["jobs"]["report"]["steps"]


def test_evidence_retains_only_named_reports_even_when_collection_fails():
    steps = report_steps()
    upload = next(step for step in steps if step["name"] == "Retain detailed metric evidence")
    assert upload["if"] == "always() && steps.snapshot.outputs.is_current == 'true'"
    assert upload["uses"] == "actions/upload-artifact@v4"
    assert upload["with"]["retention-days"] == 30
    assert upload["with"]["path"].splitlines() == [
        "${{ runner.temp }}/specificationmetrics/" + name
        for name in (
            "before.json",
            "after.json",
            "diff.json",
            "provenance.json",
            "collection-config.toml",
            "scope-manifest.toml",
        )
    ]
    render = next(step for step in steps if step["name"] == "Render the PR metrics comment")
    assert steps.index(upload) < steps.index(render)
    assert "success()" in render["if"]
    assert render["env"]["COLLECTION_RUN_ID"] == "${{ github.run_id }}"
    assert render["env"]["ARTIFACT_URL"] == "${{ steps.evidence.outputs.artifact-url }}"
    assert '--artifact-url "$ARTIFACT_URL"' in render["run"]


@pytest.mark.parametrize("fail_head", [False, True])
def test_collection_preserves_provenance_and_available_reports_on_failure(tmp_path, fail_head):
    if shutil.which("jq") is None:
        pytest.skip("workflow shell needs jq")
    step = next(step for step in report_steps() if step["name"] == "Collect base and PR metrics")
    evidence = tmp_path / "specificationmetrics"
    cli = evidence / "cli/bin/specification-metrics"
    cli.parent.mkdir(parents=True)
    for name in ("before", "after"):
        (evidence / name).mkdir()
    cli.write_text(
        f"#!{sys.executable}\n"
        "import json, pathlib, sys\n"
        "output = pathlib.Path(sys.argv[sys.argv.index('--output') + 1])\n"
        f"if {fail_head!r} and output.name == 'after.json': sys.exit(23)\n"
        "output.write_text(json.dumps({'status': 'provisional'}))\n"
    )
    cli.chmod(0o755)
    completed = subprocess.run(
        ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", step["run"]],
        cwd=ROOT,
        env={
            "PATH": os.environ["PATH"],
            "RUNNER_TEMP": str(tmp_path),
            "PR_NUMBER": "779",
            "REPOSITORY": "0al-spec/SpecGraph",
            "base_sha": "a" * 40,
            "head_sha": "b" * 40,
            "COLLECTION_RUN_ID": "12345",
            "COLLECTION_ATTEMPT": "2",
            "UPSTREAM_CI_RUN_ID": "12344",
        },
        capture_output=True,
        text=True,
    )
    assert completed.returncode == (23 if fail_head else 0), completed.stderr
    provenance = json.loads((evidence / "provenance.json").read_text())
    assert provenance["base_sha"] == "a" * 40
    assert provenance["head_sha"] == "b" * 40
    assert provenance["collection_run_id"] == "12345"
    assert provenance["upstream_ci_run_id"] == "12344"
    assert provenance["collection_attempt"] == "2"
    install = next(
        step for step in report_steps() if step["name"] == "Install pinned SpecificationMetrics CLI"
    )
    assert "--rev " + provenance["analyzer_sha"] in install["run"]
    assert (evidence / "before.json").is_file()
    assert (evidence / "after.json").is_file() == (not fail_head)
    assert (evidence / "diff.json").is_file() == (not fail_head)
    for saved, original in (
        ("collection-config.toml", ".specificationmetrics.toml"),
        ("scope-manifest.toml", "scopes/specificationmetrics.toml"),
    ):
        assert (evidence / saved).read_bytes() == (ROOT / original).read_bytes()
