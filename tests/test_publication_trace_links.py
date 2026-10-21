"""Pinned declaration resolution, distinct from executed or accepted evidence."""

# ruff: noqa: E402 -- tools are executable scripts, not installed Python packages.

import copy
import json
import os
import subprocess
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
import yaml
from specification_core import PredicateSpec

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from traceability import publication
from traceability.atom_roles_spec import ATOM_ROLES_SPEC
from traceability.context import (
    AtomRolesFacts,
    Declaration,
    DeclaredReference,
    PolicyAtomBindingsFacts,
    ReferenceFacts,
)
from traceability.policy_atom_bindings_spec import POLICY_ATOM_BINDINGS_SPEC
from traceability.publication import build_publication_links
from traceability.reference_status_spec import REFERENCE_STATUS_SPEC
from traceability.references import resolve_references


def git(root, *args):
    return (
        subprocess.check_output(["git", *args], cwd=root, stderr=subprocess.PIPE).decode().strip()
    )


@pytest.fixture
def repository(tmp_path):
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.name", "Trace fixture")
    git(tmp_path, "config", "user.email", "trace@example.invalid")
    node = {
        "id": "SG-SPEC-0071",
        "kind": "spec",
        "status": "specified",
        "gate_state": "review_pending",
        "atoms": {
            "intents": [
                {"id": "PB-ALL", "verifiable_by": ["tests/test_sample.py::test_all"]},
                {"id": "PE-CASE", "verifiable_by": ["tests/test_sample.py::test_case"]},
            ]
        },
        "specification": {
            "requirement": {"criteria": [{"id": "PB-ALL", "intent_atom_id": "PB-ALL"}]},
            "delivery_signals": {"policy_atom_ids": ["PE-CASE"]},
        },
    }
    bindings = {
        "schema_version": 1,
        "spec": "specs/nodes/SG-SPEC-0071.yaml",
        "passport": "tools/passport.json",
        "implementation": "tools/implementation.py",
        "symbol": "verify",
        "obligations": [{"criterion_id": "PB-ALL", "test": "tests/test_sample.py::test_all"}],
        "policies": [{"atom_ids": ["PE-CASE"], "specification": "policy.POLICY"}],
    }
    files = {
        bindings["spec"]: yaml.safe_dump(node),
        bindings["passport"]: json.dumps(
            {
                "artifact_kind": "feature_passport",
                "schema_version": 1,
                "spec": {"intent": {"acceptance_criteria": [{"id": "PB-ALL"}]}},
            }
        ),
        "tools/feature_passports/static-publication-bindings.json": json.dumps(bindings),
        "tools/implementation.py": "raise RuntimeError('must not execute')\ndef verify(): pass\n",
        "tools/policy.py": "raise RuntimeError('must not execute')\nPOLICY = object()\n",
        "tests/test_sample.py": (
            "raise RuntimeError('must not execute')\n"
            "def test_all(): pass\nasync def test_case(): pass\n"
        ),
    }
    for name, value in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value)
    commit(tmp_path)
    return tmp_path


def commit(root):
    git(root, "add", ".")
    git(root, "-c", "core.hooksPath=/dev/null", "commit", "-qm", "trace fixture")
    return git(root, "rev-parse", "HEAD")


def edit_json(root, name, transform):
    path = root / name
    value = json.loads(path.read_text())
    transform(value)
    path.write_text(json.dumps(value))


def edit_node(root, transform):
    path = root / "specs/nodes/SG-SPEC-0071.yaml"
    value = yaml.safe_load(path.read_text())
    transform(value)
    path.write_text(yaml.safe_dump(value))


@pytest.mark.parametrize(
    ("facts", "expected"),
    [
        (ReferenceFacts(False, False, 0), "unsupported"),
        (ReferenceFacts(True, False, 1), "unavailable"),
        (ReferenceFacts(True, True, 0), "unresolved"),
        (ReferenceFacts(True, True, 2), "ambiguous"),
        (ReferenceFacts(True, True, 1, False), "wrong_kind"),
        (ReferenceFacts(True, True, 1), "resolved"),
    ],
)
def test_reference_status_policy(facts, expected):
    assert REFERENCE_STATUS_SPEC.decide(facts).value == expected


@pytest.mark.parametrize(
    ("bound", "declared", "expected"),
    [
        ((), (), True),
        (("A",), ("A",), True),
        (("B", "A"), ("A", "B"), True),
        (("A", "A"), ("A",), False),
        (("A",), ("A", "A"), False),
        (("A", "A"), ("A", "A"), False),
        (("A",), ("A", "B"), False),
        (("A", "B"), ("A",), False),
        (("A",), ("B",), False),
    ],
)
def test_policy_atom_bindings_spec(bound, declared, expected):
    assert (
        POLICY_ATOM_BINDINGS_SPEC.is_satisfied_by(PolicyAtomBindingsFacts(bound, declared))
        is expected
    )


@pytest.mark.parametrize(
    ("inventory", "criteria", "policies", "expected"),
    [
        (("A", "B"), ("A",), ("B",), True),
        (("A",), ("A",), ("A",), True),  # Existing overlap semantics are preserved.
        ((), (), (), True),
        (("A", "B"), ("A",), (), False),
        (("A",), ("A",), ("B",), False),
        (("A",), ("B",), (), False),
    ],
)
def test_atom_roles_spec(inventory, criteria, policies, expected):
    context = AtomRolesFacts(frozenset(inventory), frozenset(criteria), frozenset(policies))
    assert ATOM_ROLES_SPEC.is_satisfied_by(context) is expected


def test_mapping_contexts_copy_mutable_inputs_and_remain_frozen():
    bound, declared, inventory = ["A"], ["A"], {"A"}
    bindings = PolicyAtomBindingsFacts(bound, declared)
    roles = AtomRolesFacts(inventory, inventory, set())
    bound.append("B")
    declared.clear()
    inventory.clear()
    assert bindings.bound_atom_ids == bindings.declared_atom_ids == ("A",)
    assert roles.inventory_atom_ids == roles.criterion_atom_ids == frozenset({"A"})
    assert roles.policy_atom_ids == frozenset()
    with pytest.raises(FrozenInstanceError):
        roles.inventory_atom_ids = frozenset()


@pytest.mark.parametrize(
    ("name", "context_type", "finding"),
    [
        (
            "POLICY_ATOM_BINDINGS_SPEC",
            PolicyAtomBindingsFacts,
            "policy_atom_bindings_incomplete_or_duplicate",
        ),
        ("ATOM_ROLES_SPEC", AtomRolesFacts, "atom_roles_incomplete"),
    ],
)
def test_mapping_policies_drive_adapter_findings(
    repository, monkeypatch, name, context_type, finding
):
    observed = []

    def reject(context):
        observed.append(context)
        return False

    monkeypatch.setattr(publication, name, PredicateSpec(reject, name="test.mapping_rejection"))
    report = build_publication_links(repository, "HEAD")
    assert len(observed) == 1 and isinstance(observed[0], context_type)
    assert report["findings"] == [{"code": finding}]
    assert report["status"] == "needs_review"


def test_generic_exact_ids_and_zeusus_reported_failures():
    # Small synthetic regression based on the intake; no executed Swift evidence.
    declarations = tuple(
        Declaration(kind, identity, "candidate.yaml", pointer, "a" * 64)
        for kind, identity, pointer in (
            ("rule", "HST-ELIGIBILITY", "/rules/0"),
            ("obligation", "hst-eligibility-observation", "/obligations/0"),
            ("scenario", "ZEU-HISTORY-STACKS-001", "/scenarios/0"),
        )
    )
    links = tuple(
        DeclaredReference("rule", "mapping", kind, value, "candidate.yaml", "/mapping")
        for kind, value in (
            ("rule", "HST-ELIGIBILITY"),
            ("obligation", "construction_effect_commit_and_owned_inventory_inverse_generation"),
            ("scenario", "ZEU-HISTORY-STACKS-001–003"),
            ("scenario", "ZEU-HISTORY-STACKS-001..ZEU-HISTORY-STACKS-003"),
            ("target", "restoreEmptyHouseWithoutCohortRecall"),
        )
    )
    result = resolve_references(links, declarations)
    assert [r.status for r in result] == [
        "resolved",
        "unresolved",
        "unsupported",
        "unresolved",
        "unresolved",
    ]
    assert tuple(r.declared for r in result) == links  # Failed declarations survive.
    duplicate = resolve_references((links[0],), declarations + (declarations[0],))[0]
    assert duplicate.status == "ambiguous" and len(duplicate.candidates) == 2
    with pytest.raises(FrozenInstanceError):
        duplicate.status = "resolved"


def test_revision_pin_non_execution_and_lifecycle(repository):
    before = git(repository, "rev-parse", "HEAD")
    report = build_publication_links(repository, before)
    assert report["status"] == "resolved"
    assert report["atom_inventory"] == {"complete": True, "declared_count": 2, "unique_count": 2}
    assert report["source_lifecycle"] == {"status": "specified", "gate_state": "review_pending"}
    assert report["execution"] == "not_collected"
    assert report["admission"] == report["fulfillment"] == "not_evaluated"
    assert report["canonical_mutations_allowed"] is False
    (repository / "tests/test_sample.py").write_text("def another(): pass\n")
    # A working-tree edit must not contaminate an old revision's resolution.
    assert build_publication_links(repository, before) == report
    after = commit(repository)
    changed = build_publication_links(repository, after)
    assert changed["status"] == "needs_review"
    assert changed["source_revision"] == after
    assert changed["content_sha256"] != report["content_sha256"]
    assert "unresolved" in changed["resolution_counts"]


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("def test_all(): pass\ndef test_all(): pass\nasync def test_case(): pass\n", "ambiguous"),
        ("test_all = 1\nasync def test_case(): pass\n", "wrong_kind"),
        ("from external import test_all\nasync def test_case(): pass\n", "unresolved"),
        ("def test_all(:\n", "unavailable"),
    ],
)
def test_python_declaration_outcomes(repository, source, expected):
    (repository / "tests/test_sample.py").write_text(source)
    pin = commit(repository)
    report = build_publication_links(repository, pin)
    rows = [
        r for r in report["links"] if r["declared"]["target"] == "tests/test_sample.py::test_all"
    ]
    assert rows and all(row["status"] == expected for row in rows)
    assert report["status"] == "needs_review"


def test_missing_file_is_unavailable_and_preserves_authored_link(repository):
    (repository / "tests/test_sample.py").unlink()
    report = build_publication_links(repository, commit(repository))
    assert report["sources"]["tests/test_sample.py"]["status"] == "unavailable"
    assert report["resolution_counts"]["unavailable"] == 3
    assert report["atom_inventory"]["complete"] is True


@pytest.mark.parametrize(
    "selector",
    [
        "tests/unsupported.py",
        "tests/unsupported.py::test_all[case]",
        "tests/unsupported.py::test_all–test_case",
        "../secret.py::test_all",
        "/etc/secret.py::test_all",
        "tests\\test_sample.py::test_all",
        "tools/implementation.py::verify",
    ],
)
def test_unsupported_selectors_are_retained_without_reading_them(repository, selector):
    edit_node(repository, lambda n: n["atoms"]["intents"][0].update(verifiable_by=[selector]))
    report = build_publication_links(repository, commit(repository))
    row = next(r for r in report["links"] if r["declared"]["target"] == selector)
    assert row["status"] == "unsupported"
    if selector != "tools/implementation.py::verify":  # Independently read as implementation.
        assert selector.split("::")[0] not in report["sources"]


def test_unknown_policy_symbol_and_invalid_module_notation(repository):
    bindings = "tools/feature_passports/static-publication-bindings.json"
    edit_json(
        repository, bindings, lambda b: b["policies"][0].update(specification="policy.MISSING")
    )
    report = build_publication_links(repository, commit(repository))
    row = next(r for r in report["links"] if r["declared"]["relation"] == "policy_declaration")
    assert row["status"] == "unresolved"
    edit_json(
        repository, bindings, lambda b: b["policies"][0].update(specification="./policy.POLICY")
    )
    report = build_publication_links(repository, commit(repository))
    row = next(r for r in report["links"] if r["declared"]["relation"] == "policy_declaration")
    assert row["status"] == "unsupported"


def test_annotation_without_value_does_not_resolve_policy_value(repository):
    (repository / "tools/policy.py").write_text("POLICY: object\n")
    report = build_publication_links(repository, commit(repository))
    row = next(r for r in report["links"] if r["declared"]["relation"] == "policy_declaration")
    assert row["status"] == "wrong_kind"


def test_duplicate_atom_not_coalesced(repository):
    edit_node(
        repository, lambda n: n["atoms"]["intents"].append(copy.deepcopy(n["atoms"]["intents"][0]))
    )
    report = build_publication_links(repository, commit(repository))
    assert report["status"] == "needs_review"
    assert report["atom_inventory"] == {"complete": False, "declared_count": 3, "unique_count": 2}
    assert report["resolution_counts"]["ambiguous"] == 1


@pytest.mark.parametrize(
    "change",
    ["unknown_atom", "unknown_criterion", "missing_policy", "wrong_bound_test", "empty_channels"],
)
def test_mapping_gaps_cannot_be_reported_resolved(repository, change):
    bindings = "tools/feature_passports/static-publication-bindings.json"
    if change == "unknown_atom":
        edit_json(repository, bindings, lambda b: b["policies"][0].update(atom_ids=["UNKNOWN"]))
    elif change == "unknown_criterion":
        edit_json(
            repository, bindings, lambda b: b["obligations"][0].update(criterion_id="UNKNOWN")
        )
    elif change == "missing_policy":
        edit_json(repository, bindings, lambda b: b.update(policies=[]))
    elif change == "wrong_bound_test":
        edit_json(
            repository,
            bindings,
            lambda b: b["obligations"][0].update(test="tests/test_sample.py::test_case"),
        )
    else:
        edit_node(repository, lambda n: n["atoms"]["intents"][0].update(verifiable_by=[]))
    report = build_publication_links(repository, commit(repository))
    assert report["status"] == "needs_review"
    assert report["findings"]


def test_symlink_never_resolves_to_checkout_content(repository):
    path = repository / "tests/test_sample.py"
    path.unlink()
    path.symlink_to(ROOT / "tests/test_publication_evidence_policies.py")
    report = build_publication_links(repository, commit(repository))
    assert report["sources"]["tests/test_sample.py"]["status"] == "unavailable"


def test_invalid_required_inventory_is_error(repository):
    edit_node(repository, lambda n: n.update(atoms={"intents": None}))
    with pytest.raises(ValueError, match="atoms.intents"):
        build_publication_links(repository, commit(repository))


@pytest.mark.parametrize(
    "path", ["tools/passport.json", "tools/feature_passports/static-publication-bindings.json"]
)
def test_unknown_required_source_version_is_error(repository, path):
    edit_json(repository, path, lambda data: data.update(schema_version=2))
    with pytest.raises(ValueError, match="schema_version 1"):
        build_publication_links(repository, commit(repository))


def test_real_publication_inventory_resolves_without_running_it():
    report = build_publication_links(ROOT, "HEAD")
    assert report["status"] == "resolved"
    assert report["links"] and set(report["resolution_counts"]) == {"resolved"}
    assert report["findings"] == report["duplicate_ids"] == []
    assert report["execution"] == "not_collected"


def test_independent_cli_and_invalid_revision(repository, tmp_path):
    command = [
        sys.executable,
        "-B",
        str(ROOT / "tools/publication_trace_links.py"),
        "--repository-root",
        str(repository),
        "--revision",
        "HEAD",
    ]
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": ""}
    completed = subprocess.run(command, cwd=tmp_path, env=env, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout)["status"] == "resolved"
    failed = subprocess.run(
        [*command[:-1], "missing-revision"], cwd=tmp_path, env=env, capture_output=True, text=True
    )
    assert failed.returncode == 1 and failed.stdout == ""
