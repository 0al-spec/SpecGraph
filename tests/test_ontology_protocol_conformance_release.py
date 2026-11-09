"""Exercise imported protocol obligations in the pinned Ontology release."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

CONTRACTS = """\
apiVersion: ontology.specgraph.io/v1alpha1
kind: DomainOntologyPackage
metadata: {id: example.contracts, namespace: contracts, version: 1.0.0}
spec:
  imports:
    - {id: ontology.foundation, version: 0.2.0}
  classes:
    Anchor: {extends: 'ont:DomainEntity', description: Anchor.}
  relations:
    links: {domain: Anchor, range: Anchor, description: Link.}
  protocols:
    Tracked:
      description: A traced document.
      requiredFields: [trace]
      requiredRelations: [auditLink]
"""


def package(*, field: bool, relation: bool) -> str:
    source = """\
apiVersion: ontology.specgraph.io/v1alpha1
kind: DomainOntologyPackage
metadata: {id: example.documents, namespace: doc, version: 1.0.0}
spec:
  imports:
    - {id: ontology.foundation, version: 0.2.0}
    - {id: example.contracts, namespace: p, version: 1.0.0}
  classes:
    Document:
      extends: ont:DomainEntity
      implements: ['p:Tracked']
      description: A document.
"""
    if field:
        source += "      fields: {trace: {type: string, required: true}}\n"
    source += """\
  relations:
    trace: {domain: Document, range: Document, description: Not a field.}
"""
    if relation:
        source += "    auditLink: {domain: Document, range: Document, description: Audit.}\n"
    return source


@pytest.fixture
def compiler():
    if not (value := os.environ.get("ONTOLOGYC_BINARY_PATH")):
        pytest.skip("set ONTOLOGYC_BINARY_PATH to exercise the pinned release")
    return Path(value).resolve(strict=True)


@pytest.mark.parametrize(
    ("field", "relation", "expected"),
    [
        (True, True, None),
        (False, True, "protocol.field.missing"),
        (True, False, "protocol.relation.missing"),
    ],
)
def test_imported_protocol_checks_fields_and_relations(
    compiler, tmp_path, field, relation, expected
):
    definitions = tmp_path / "contracts.yaml"
    model = tmp_path / "documents.yaml"
    definitions.write_text(CONTRACTS, encoding="utf-8")
    model.write_text(package(field=field, relation=relation), encoding="utf-8")
    check = subprocess.run(
        [compiler, "check", model, "--import", definitions],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if expected is None:
        assert check.returncode == 0, check.stdout + check.stderr
    else:
        assert check.returncode == 1
        assert expected in check.stdout


def test_staged_advice_checks_index_with_imported_protocol(compiler, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    template = tmp_path / "empty-template"
    template.mkdir()
    env = os.environ | {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
    subprocess.run(["git", "init", "-q", f"--template={template}"], cwd=repo, env=env, check=True)
    (repo / "contracts.yaml").write_text(CONTRACTS, encoding="utf-8")
    model = repo / "documents.yaml"
    model.write_text(package(field=False, relation=True), encoding="utf-8")
    subprocess.run(
        ["git", "add", "contracts.yaml", "documents.yaml"], cwd=repo, env=env, check=True
    )
    model.write_text(package(field=True, relation=True), encoding="utf-8")
    advice = subprocess.run(
        [compiler, "advise-staged", "--import", "contracts.yaml"],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert advice.returncode == 0
    assert '"documents.yaml"' in advice.stderr
    assert "protocol.field.missing" in advice.stderr
