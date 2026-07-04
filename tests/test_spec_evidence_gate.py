from __future__ import annotations

import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS_DIR))
try:
    import spec_evidence_gate
finally:
    sys.path.remove(str(TOOLS_DIR))


def _repo_with_evidence(tmp_path: Path) -> Path:
    specs = tmp_path / "specs" / "nodes"
    proposals = tmp_path / "docs" / "proposals"
    specs.mkdir(parents=True)
    proposals.mkdir(parents=True)
    (specs / "SG-SPEC-0006.yaml").write_text(
        "id: SG-SPEC-0006\ntitle: Tracked Proposal Lane\n",
        encoding="utf-8",
    )
    (proposals / "0047_evidence_backed_build_protocol.md").write_text(
        "# Evidence-Backed Build Protocol\n",
        encoding="utf-8",
    )
    return tmp_path


def test_gate_skips_when_no_logic_files_changed(tmp_path: Path) -> None:
    repo = _repo_with_evidence(tmp_path)

    result = spec_evidence_gate.evaluate_gate(
        repo,
        ["docs/proposals/0047_evidence_backed_build_protocol.md"],
        [],
    )

    assert result.passed is True
    assert result.logic_files == ()


def test_gate_fails_logic_change_without_evidence(tmp_path: Path) -> None:
    repo = _repo_with_evidence(tmp_path)

    result = spec_evidence_gate.evaluate_gate(repo, ["tools/supervisor.py"], [])

    assert result.passed is False
    assert "without Spec-ID" in result.message
    assert result.logic_files == ("tools/supervisor.py",)


def test_gate_treats_top_level_tooling_configs_as_logic() -> None:
    paths = [
        ".pre-commit-config.yaml",
        "Package.swift",
        "pyproject.toml",
        "specgraph.project.yaml",
    ]

    for path in paths:
        assert spec_evidence_gate.is_logic_path(path), path


def test_gate_accepts_existing_spec_id_from_pr_body(tmp_path: Path) -> None:
    repo = _repo_with_evidence(tmp_path)

    result = spec_evidence_gate.evaluate_gate(
        repo,
        ["tools/supervisor.py"],
        ["Spec-ID: SG-SPEC-0006\nSpec-Impact: tooling\n"],
    )

    assert result.passed is True
    assert result.evidence.spec_ids == ("SG-SPEC-0006",)


def test_gate_accepts_existing_proposal_id_from_commit_trailer(tmp_path: Path) -> None:
    repo = _repo_with_evidence(tmp_path)

    result = spec_evidence_gate.evaluate_gate(
        repo,
        [".github/workflows/python-ci.yml"],
        ["Tighten PR evidence gate\n\nProposal-ID: 0047\n"],
    )

    assert result.passed is True
    assert result.evidence.proposal_ids == ("0047",)


def test_gate_rejects_unknown_spec_id(tmp_path: Path) -> None:
    repo = _repo_with_evidence(tmp_path)

    result = spec_evidence_gate.evaluate_gate(
        repo,
        ["tools/supervisor.py"],
        ["Spec-ID: SG-SPEC-9999\n"],
    )

    assert result.passed is False
    assert "do not exist" in result.message


def test_gate_requires_rationale_for_no_spec_impact(tmp_path: Path) -> None:
    repo = _repo_with_evidence(tmp_path)

    result = spec_evidence_gate.evaluate_gate(
        repo,
        ["tools/supervisor.py"],
        ["Spec-ID: NO-SPEC-IMPACT\nSpec-Impact: no-impact\n"],
    )

    assert result.passed is False
    assert "Spec-Rationale" in result.message


def test_gate_accepts_justified_no_spec_impact(tmp_path: Path) -> None:
    repo = _repo_with_evidence(tmp_path)

    result = spec_evidence_gate.evaluate_gate(
        repo,
        ["tools/supervisor.py"],
        [
            "Spec-ID: NO-SPEC-IMPACT\n"
            "Spec-Impact: no-impact\n"
            "Spec-Rationale: Local refactor with no observable behavior change.\n"
        ],
    )

    assert result.passed is True
    assert result.evidence.no_spec_impact is True


def test_pr_template_contains_spec_evidence_fields() -> None:
    template = (
        Path(__file__).resolve().parents[1] / ".github" / "PULL_REQUEST_TEMPLATE.md"
    ).read_text(encoding="utf-8")

    assert "## Spec Evidence" in template
    assert "Spec-ID:" in template
    assert "Proposal-ID:" in template
    assert "Spec-Impact:" in template
    assert "Spec-Rationale:" in template


def test_python_ci_runs_spec_evidence_gate_for_pull_requests() -> None:
    workflow = (
        Path(__file__).resolve().parents[1] / ".github" / "workflows" / "python-ci.yml"
    ).read_text(encoding="utf-8")

    assert "spec-evidence:" in workflow
    assert "if: github.event_name == 'pull_request'" in workflow
    assert "types: [opened, synchronize, reopened, edited]" in workflow
    assert "fetch-depth: 0" in workflow
    assert "make spec-evidence-gate" in workflow
