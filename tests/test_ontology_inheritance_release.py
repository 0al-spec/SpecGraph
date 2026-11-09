"""Exercise semantic inheritance in the pinned Ontology release."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "ontology/packages/specgraph-core/versions/0.4.0/domain-ontology-package.yaml"
CYCLE = (
    ROOT
    / "docs/reviews/0232_project_ontology_context/inheritance-validation-gap-20261109/cycle.yaml"
)


@pytest.fixture
def compiler():
    if not (value := os.environ.get("ONTOLOGYC_BINARY_PATH")):
        pytest.skip("set ONTOLOGYC_BINARY_PATH to exercise the pinned release")
    return Path(value).resolve(strict=True)


def test_pinned_compiler_rejects_cycle_and_staged_advice_reports_it(compiler, tmp_path):
    check = subprocess.run([compiler, "check", CYCLE], capture_output=True, text=True, timeout=60)
    assert check.returncode == 1
    assert "class.inheritance.cycle" in check.stdout

    repo = tmp_path / "repo"
    repo.mkdir()
    template = tmp_path / "empty-template"
    template.mkdir()
    env = os.environ | {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
    subprocess.run(["git", "init", "-q", f"--template={template}"], cwd=repo, env=env, check=True)
    (repo / "cycle.yaml").write_bytes(CYCLE.read_bytes())
    subprocess.run(["git", "add", "cycle.yaml"], cwd=repo, env=env, check=True)
    advice = subprocess.run(
        [compiler, "advise-staged"], cwd=repo, env=env, capture_output=True, text=True, timeout=60
    )
    assert advice.returncode == 0
    assert '"cycle.yaml"' in advice.stderr
    assert "class.inheritance.cycle" in advice.stderr


def test_graph_invariant_sdk_retains_its_foundation_ancestry(compiler, tmp_path):
    if not (tsc := os.environ.get("TYPESCRIPT_TSC_PATH")):
        pytest.skip("set TYPESCRIPT_TSC_PATH to type-check the generated SDK")
    sdk = tmp_path / "sdk"
    subprocess.run(
        [compiler, "compile", CORE, "--target", "typescript", "--out", sdk],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    (tmp_path / "probe.ts").write_text(
        """import type { GraphInvariant, $OntologyFoundationInstance } from './sdk/types';
declare const graph: GraphInvariant;
type InvariantBase = $OntologyFoundationInstance<'ontology://specgraph.foundation/0.1.0/classes/Invariant'>;
type CommandBase = $OntologyFoundationInstance<'ontology://specgraph.foundation/0.1.0/classes/Command'>;
const base: InvariantBase = graph;
// @ts-expect-error a graph invariant is not a command
const command: CommandBase = graph;
// @ts-expect-error declaration metadata is not an instance field
const kind = graph.kind;
void [base, command, kind];
""",
        encoding="utf-8",
    )
    subprocess.run(
        ["node", tsc, "--strict", "--noEmit", "probe.ts"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
