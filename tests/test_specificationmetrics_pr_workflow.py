from __future__ import annotations

from pathlib import Path

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
