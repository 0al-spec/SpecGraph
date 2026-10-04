"""Bounded semantic classification is proposed; missing evidence is never zero."""

import ast
import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from publication_policy_diagnostics import (  # noqa: E402
    MANIFEST,
    Sites,
    ast_digest,
    compare,
    main,
    snapshot,
    stable_ast_dump,
    validate_manifest,
)


@pytest.fixture
def classified(tmp_path):
    # Independent syntax corpus: this must not impose a threshold on live code.
    sources = {
        "tools/subject_publication.py": """
from subject_human_approval_spec import HUMAN_APPROVAL_SPEC
from subject_reviewed_record_spec import REVIEWED_RECORD_SPEC
from subject_transition_approval_spec import TRANSITION_APPROVAL_SPEC

def _review(review, scope):
    require(isinstance(review, dict), "missing actual human review")
    require(review["scope_sha256"] == scope_digest(scope), "human review covers a different scope")
    require(HUMAN_APPROVAL_SPEC.is_satisfied_by(
        HumanApprovalContext(review["reviewer_authority"], review["outcome"])
    ), "human approval required")

def _transitions(context):
    require(
        TRANSITION_APPROVAL_SPEC.is_satisfied_by(context),
        "incomplete or unapproved transition",
    )

def _verify_publication(context, workspace, allocated, selection, change):
    require(
        REVIEWED_RECORD_SPEC.is_satisfied_by(context),
        "request complete record differs from reviewed draft",
    )
    require(
        REVIEWED_RECORD_SPEC.is_satisfied_by(context),
        "request declaration differs from reviewed candidate",
    )
    require(workspace == allocated, "workspace allocation covers a different bootstrap")
    if selection is not None:
        pass
    if change.operation == "origin":
        pass
""",
        "tools/subject_human_approval_spec.py": """
from specification_core import PredicateSpec
HUMAN_APPROVAL_SPEC = PredicateSpec(lambda context:
    context.reviewer_authority == "human_project_author" and context.outcome == "approved"
)
""",
        "tools/subject_reviewed_record_spec.py": """
from specification_core import PredicateSpec
REVIEWED_RECORD_SPEC = PredicateSpec(lambda context:
    context.reviewed_scope_sha256 == context.requested_scope_sha256
)
""",
        "tools/subject_transition_approval_spec.py": """
from specification_core import PredicateSpec
TRANSITION_APPROVAL_SPEC = PredicateSpec(lambda context: context.outcome == "approved")
""",
    }
    manifest = {
        "artifact_kind": "publication_policy_classification",
        "schema_version": 1,
        "profile_id": "test.publication.v1",
        "classification_status": "proposed",
        "scope_note": "Independent synthetic syntax corpus only.",
        "modules": [
            {"path": path, "inventory_guards": path.endswith("subject_publication.py")}
            for path in sources
        ],
        "families": [],
        "specifications": [],
        "sites": [],
    }
    import hashlib

    # Explicit semantic assignments; source parsing never infers these categories.
    assignments = {
        "missing actual human review": ("mechanics", None),
        "human review covers a different scope": ("policy", "test.scope"),
        "human approval required": ("policy", "publication.human_approval"),
        "incomplete or unapproved transition": ("policy", "publication.reviewed_transition"),
        "request complete record differs from reviewed draft": (
            "policy",
            "publication.complete_reviewed_record",
        ),
        "request declaration differs from reviewed candidate": (
            "policy",
            "publication.complete_reviewed_record",
        ),
        "workspace allocation covers a different bootstrap": ("policy", "test.allocation"),
        "selection is not None": ("mechanics", None),
        "change.operation == 'origin'": ("variant_behavior", None),
    }
    spec_families = {
        "HUMAN_APPROVAL_SPEC": "publication.human_approval",
        "REVIEWED_RECORD_SPEC": "publication.complete_reviewed_record",
        "TRANSITION_APPROVAL_SPEC": "publication.reviewed_transition",
    }
    for path, text in sources.items():
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)
        tree = ast.parse(text)
        for node in tree.body:
            if isinstance(node, ast.Assign) and node.targets[0].id in spec_families:
                manifest["specifications"].append(
                    {
                        "path": path,
                        "symbol": node.targets[0].id,
                        "family_id": spec_families[node.targets[0].id],
                        "predicate_sha256": ast_digest(node.value),
                    }
                )
    visitor = Sites("tools/subject_publication.py")
    visitor.visit(ast.parse(sources["tools/subject_publication.py"]))
    families = {}
    for site in visitor.sites:
        category, family = assignments[site.label]
        record = {
            "id": hashlib.sha256(site.label.encode()).hexdigest()[:12],
            "path": site.path,
            "kind": site.kind,
            "label": site.label,
            "predicate_sha256": site.predicate_sha256,
            "category": category,
            "rationale": "Synthetic classification.",
            "allowed_locations": [site.location],
        }
        if family:
            record["family_id"] = family
            spec = next((s for s in manifest["specifications"] if s["family_id"] == family), None)
            families.setdefault(
                family,
                {
                    "id": family,
                    "canonical_definition": f"spec:{spec['path']}:{spec['symbol']}"
                    if spec
                    else "inline:" + record["id"],
                    "allowed_definition_paths": [spec["path"]] if spec else [],
                },
            )
        manifest["sites"].append(record)
    manifest["families"] = list(families.values())
    (tmp_path / MANIFEST).write_text(json.dumps(manifest))
    return tmp_path, manifest


def test_corpus_is_complete_and_reused_spec_has_one_definition(classified):
    root, manifest = classified
    report = snapshot(root, manifest)
    assert report["completeness"] == "complete"
    assert report["counts"] == {
        "inline_policies": 2,
        "duplicate_policy_definitions": 0,
        "policy_boundary_violations": 0,
    }
    assert report["coverage"] == {"discovered_sites": 9, "resolved_sites": 9}
    shared = [
        s for s in report["sites"] if s["family_id"] == "publication.complete_reviewed_record"
    ]
    assert len(shared) == 2
    assert len({s["definition"] for s in shared}) == 1
    assert all(s["evaluation"] == "specification" for s in shared)
    assert report["merge_gate_enabled"] is False
    assert report["classification_status"] == "proposed"


@pytest.mark.parametrize(
    "mutation", ["deleted", "changed", "new", "shadowed", "factory", "factory_predicate", "assert"]
)
def test_source_drift_is_incomplete_instead_of_zero(classified, mutation):
    root, manifest = classified
    path = root / "tools/subject_publication.py"
    source = path.read_text()
    if mutation == "deleted":
        source = source.replace('"human approval required"', '"different diagnostic"')
    elif mutation == "changed":
        source = source.replace(
            'HumanApprovalContext(review["reviewer_authority"], review["outcome"])',
            'HumanApprovalContext("agent", review["outcome"])',
        )
    elif mutation == "new":
        source += '\ndef extra(value):\n    require(value, "unclassified new policy")\n'
    elif mutation == "shadowed":
        source += "\nHUMAN_APPROVAL_SPEC = object()\n"
    elif mutation == "assert":
        source += "\ndef extra(value):\n    assert value\n"
    elif mutation == "factory_predicate":
        p = root / "tools/subject_human_approval_spec.py"
        p.write_text(
            p.read_text().replace('context.outcome == "approved"', 'context.outcome == "rejected"')
        )
    else:
        p = root / "tools/subject_human_approval_spec.py"
        p.write_text(p.read_text().replace("PredicateSpec(", "object("))
    path.write_text(source)
    report = snapshot(root, manifest)
    assert report["completeness"] == "incomplete"
    assert report["counts"] is None
    assert report["diagnostics"]


def add_site(manifest, source, label, family, category="policy"):
    visitor = Sites("tools/subject_publication.py")
    visitor.visit(ast.parse(source))
    site = next(s for s in visitor.sites if s.label == label)
    manifest["sites"].append(
        {
            "id": "publication.test.extra",
            "path": site.path,
            "kind": site.kind,
            "label": site.label,
            "predicate_sha256": site.predicate_sha256,
            "category": category,
            "rationale": "Synthetic equivalent policy definition.",
            "allowed_locations": [site.location],
            "family_id": family,
        }
    )


def test_extra_spec_definition_and_wrong_architectural_home(classified):
    root, manifest = classified
    copied = "tools/copied_approval_spec.py"
    (root / copied).write_text((root / "tools/subject_human_approval_spec.py").read_text())
    manifest["modules"].append({"path": copied, "inventory_guards": False})
    manifest["specifications"].append(
        {
            "path": copied,
            "symbol": "HUMAN_APPROVAL_SPEC",
            "family_id": "publication.human_approval",
            "predicate_sha256": next(
                s
                for s in manifest["specifications"]
                if s["family_id"] == "publication.human_approval"
            )["predicate_sha256"],
        }
    )
    path = root / "tools/subject_publication.py"
    source = path.read_text() + (
        "\nfrom copied_approval_spec import HUMAN_APPROVAL_SPEC as COPIED\n"
        "def another_approval(authority, outcome):\n"
        "    require(\n"
        "        COPIED.is_satisfied_by(HumanApprovalContext(authority, outcome)),\n"
        '        "copied approval",\n'
        "    )\n"
    )
    path.write_text(source)
    add_site(manifest, source, "copied approval", "publication.human_approval")
    report = snapshot(root, manifest)
    assert report["completeness"] == "complete"
    assert report["counts"]["duplicate_policy_definitions"] == 1
    assert report["counts"]["policy_boundary_violations"] == 1


def test_moving_policy_to_another_function_is_a_boundary_violation(classified):
    root, manifest = classified
    path = root / "tools/subject_publication.py"
    path.write_text(path.read_text().replace("_review(", "consumer_review("))
    report = snapshot(root, manifest)
    assert report["completeness"] == "complete"
    assert report["counts"]["policy_boundary_violations"] > 0
    human = next(s for s in report["sites"] if s["family_id"] == "publication.human_approval")
    assert human["boundary_violation"]


def test_added_violation_is_not_cancelled_by_removed_violation(classified):
    root, manifest = classified
    base = snapshot(root, manifest)
    head = copy.deepcopy(base)
    removed = head["violations"].pop(0)
    head["violations"].append(
        {"id": "inline:new-policy", "kind": "inline_policy", "site_id": "new-policy"}
    )
    diff = compare(base, head)
    assert diff["count_delta"]["inline_policies"] == 0
    assert diff["added_violations"][0]["id"] == "inline:new-policy"
    assert diff["removed_violations"][0]["id"] == removed["id"]


def test_classification_change_is_explicit_and_partial_diff_is_unavailable(classified):
    root, manifest = classified
    base = snapshot(root, manifest)
    updated = copy.deepcopy(manifest)
    updated["scope_note"] += " Changed classification contract."
    head = snapshot(root, updated)
    assert compare(base, head)["classification_contract_changed"] is True
    head["completeness"] = "incomplete"
    assert compare(base, head)["status"] == "unavailable"


def test_duplicate_selector_cannot_inflate_counts(classified):
    _, manifest = classified
    other = copy.deepcopy(manifest["sites"][0])
    other["id"] = "fake-extra"
    manifest["sites"].append(other)
    with pytest.raises(ValueError):
        validate_manifest(manifest)


@pytest.mark.parametrize(
    "locations",
    ["tools/subject_publication.py::_review", [], ["", "valid"], [1]],
)
def test_allowed_locations_must_be_a_nonempty_array_of_locations(classified, locations):
    _, manifest = classified
    malformed = copy.deepcopy(manifest)
    malformed["sites"][0]["allowed_locations"] = locations
    with pytest.raises(ValueError, match="architectural locations"):
        validate_manifest(malformed)


def test_same_line_guards_are_matched_independently(classified):
    root, manifest = classified
    path = root / "tools/subject_publication.py"
    source = path.read_text() + (
        "\ndef same_line(value):\n"
        "    require(value, 'same-line known'); require(value, 'same-line new')\n"
    )
    path.write_text(source)
    add_site(manifest, source, "same-line known", None, category="mechanics")
    report = snapshot(root, manifest)
    assert report["completeness"] == "incomplete"
    assert report["counts"] is None
    assert report["coverage"]["discovered_sites"] > report["coverage"]["resolved_sites"]
    assert any(diagnostic["code"] == "unclassified_site" for diagnostic in report["diagnostics"])


def test_unreferenced_registered_specification_is_counted(classified):
    root, manifest = classified
    source_path = "tools/subject_human_approval_spec.py"
    copied_path = "tools/unreferenced_approval_spec.py"
    original = (root / source_path).read_text()
    (root / copied_path).write_text(original.replace("HUMAN_APPROVAL_SPEC", "UNREFERENCED_SPEC"))
    manifest["modules"].append({"path": copied_path, "inventory_guards": False})
    original_binding = next(
        spec for spec in manifest["specifications"] if spec["symbol"] == "HUMAN_APPROVAL_SPEC"
    )
    manifest["specifications"].append(
        {
            "path": copied_path,
            "symbol": "UNREFERENCED_SPEC",
            "family_id": original_binding["family_id"],
            "predicate_sha256": original_binding["predicate_sha256"],
        }
    )
    report = snapshot(root, manifest)
    assert report["completeness"] == "complete"
    assert report["counts"]["duplicate_policy_definitions"] == 1
    assert report["counts"]["policy_boundary_violations"] == 1


def test_ast_fingerprint_serialization_includes_empty_fields():
    expression = ast.parse("call(value)").body[0].value
    assert "keywords=[]" in stable_ast_dump(expression)


def test_missing_baseline_classification_does_not_report_zero(classified, capsys):
    root, manifest = classified
    import subprocess

    subprocess.run(["git", "init"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "fixture@example.invalid"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Fixture"], cwd=root, check=True)
    (root / "initial.txt").write_text("No historical classification.")
    subprocess.run(["git", "add", "initial.txt"], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "Initial fixture"], cwd=root, check=True)
    assert main(["--root", str(root), "--base-ref", "HEAD"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["comparison"]["status"] == "unavailable"
    assert "count_delta" not in report["comparison"]


def test_cli_is_informational_when_known_inline_policies_exist(classified, capsys):
    root, _ = classified
    assert main(["--root", str(root)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["counts"]["inline_policies"] == 2
    assert report["merge_gate_enabled"] is False


def test_equivalent_inline_copy_is_counted_as_extra_definition(classified):
    root, manifest = classified
    path = root / "tools/subject_publication.py"
    family = next(
        s["family_id"]
        for s in manifest["sites"]
        if s["label"] == "human review covers a different scope"
    )
    source = path.read_text() + (
        "\ndef copied_scope(review, scope):\n"
        '    require(review["scope_sha256"] == scope_digest(scope), "copied scope")\n'
    )
    path.write_text(source)
    add_site(manifest, source, "copied scope", family)
    report = snapshot(root, manifest)
    assert report["completeness"] == "complete"
    assert report["counts"]["inline_policies"] == 3
    assert report["counts"]["duplicate_policy_definitions"] == 1


def test_source_symlink_cannot_supply_a_complete_snapshot(classified, tmp_path):
    root, manifest = classified
    source = root / "tools/subject_human_approval_spec.py"
    saved = tmp_path / "saved.py"
    source.rename(saved)
    source.symlink_to(saved)
    report = snapshot(root, manifest)
    assert report["completeness"] == "incomplete"
    assert report["counts"] is None


def test_immutable_git_snapshot_ignores_working_tree_changes(classified, capsys):
    root, manifest = classified
    from subject_source_git import git_command

    git_command(root, "init")
    git_command(root, "config", "user.email", "fixture@example.invalid")
    git_command(root, "config", "user.name", "Fixture")
    git_command(root, "add", ".")
    git_command(root, "commit", "-qm", "Classified fixture")
    selected = git_command(root, "rev-parse", "HEAD").stdout.decode().strip()
    path = root / "tools/subject_publication.py"
    path.write_text("Invalid and unclassified working-tree source")
    assert main(["--root", str(root), "--revision", selected, "--summary"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["completeness"] == "complete"
    assert report["counts"]["inline_policies"] == 2


def test_ci_diagnostic_is_nonblocking_and_run_scoped():
    import yaml

    workflow = yaml.safe_load((ROOT / ".github/workflows/python-ci.yml").read_text())
    steps = workflow["jobs"]["test"]["steps"]
    diagnostic = next(
        s for s in steps if s.get("name") == "Publication policy diagnostics (informational)"
    )
    assert diagnostic["continue-on-error"] is True
    assert '--revision "${{ github.event.pull_request.head.sha }}"' in diagnostic["run"]
    assert "${{ runner.temp }}/publication-policy-diagnostics.json" in diagnostic["run"]
    artifact = next(s for s in steps if s.get("name") == "Upload publication policy diagnostics")
    assert artifact["continue-on-error"] is True
    assert artifact["with"]["path"] == "${{ runner.temp }}/publication-policy-diagnostics.json"
