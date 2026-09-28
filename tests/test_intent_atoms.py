from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL_PATH = ROOT / "tools" / "intent_atoms.py"


def load_module() -> object:
    spec = importlib.util.spec_from_file_location("intent_atoms_under_test", TOOL_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def make_repo(tmp_path: Path, documents: dict[str, str]) -> Path:
    repo = tmp_path / "history"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "Intent Atoms Test")
    git(repo, "config", "user.email", "intent-atoms@example.invalid")
    for relative_path, contents in documents.items():
        path = repo / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(contents, encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "fixture")
    return repo


def test_snapshot_counts_legacy_and_envelope_acceptance_and_explicit_atoms(
    tmp_path: Path,
) -> None:
    module = load_module()
    repo = make_repo(
        tmp_path,
        {
            "specs/nodes/legacy.yaml": """
id: SG-1
kind: spec
status: reviewed
acceptance:
  - "  First criterion.  "
  - Second criterion.
""",
            "specs/nodes/envelope.yaml": json.dumps(
                {
                    "apiVersion": "specgraph.io/v0alpha1",
                    "kind": "Node",
                    "metadata": {"id": "node-2", "type": "spec", "status": "specified"},
                    "spec": {"acceptance": ["Envelope criterion."]},
                }
            ),
            "specs/nodes/explicit.yaml": json.dumps(
                {
                    "id": "SG-3",
                    "kind": "spec",
                    "acceptance": ["Keep as context."],
                    "atoms": {
                        "intents": [
                            {
                                "id": "A-1",
                                "type": "behavior",
                                "statement": "  Explicit intent.  ",
                                "premises": ["P-1"],
                                "verifiable_by": ["T-1"],
                            }
                        ]
                    },
                }
            ),
            "specs/nodes/nested-explicit.yaml": json.dumps(
                {
                    "apiVersion": "specgraph.io/v0alpha1",
                    "kind": "Node",
                    "metadata": {"id": "node-4", "type": "spec"},
                    "spec": {
                        "acceptance": ["Context only."],
                        "atoms": {"intents": [{"statement": "Nested explicit intent."}]},
                    },
                }
            ),
            "specs/nodes/empty-explicit.yaml": json.dumps(
                {
                    "id": "SG-5",
                    "kind": "spec",
                    "acceptance": ["Still not counted."],
                    "atoms": {"intents": []},
                }
            ),
        },
    )

    report = module.build_snapshot(repo=str(repo), revision="HEAD")

    assert report["completeness"] == "complete"
    assert report["summary"]["node_count"] == 5
    assert report["summary"]["atom_count"] == 5
    assert report["summary"]["atom_count_by_origin"] == {
        "acceptance_criterion": 3,
        "explicit_intent": 2,
    }
    legacy = next(node for node in report["nodes"] if node["node_id"] == "SG-1")
    assert legacy["status"] == "reviewed"
    assert legacy["provenance"] == {"authority": None, "authored_by": None}
    assert len(report["profile"]["sha256"]) == 64
    assert len(report["analyzer_sha256"]) == 64
    explicit = next(atom for atom in report["atoms"] if atom["atom_id"] == "A-1")
    assert explicit["text"] == "Explicit intent."
    assert explicit["premises"] == ["P-1"]
    assert explicit["verifiable_by"] == ["T-1"]
    assert [item["code"] for item in report["diagnostics"]] == [
        "acceptance_not_counted",
        "acceptance_not_counted",
        "acceptance_not_counted",
    ]


def test_snapshot_marks_invalid_yaml_and_duplicate_node_ids_incomplete(tmp_path: Path) -> None:
    module = load_module()
    repo = make_repo(
        tmp_path,
        {
            "specs/nodes/bad.yaml": "id: SG-1\nacceptance: [unterminated\n",
            "specs/nodes/one.yaml": "id: SG-2\nkind: spec\nacceptance: [one]\n",
            "specs/nodes/two.yaml": """
id: SG-2
kind: spec
acceptance: [two]
atoms:
  intents:
    - id: duplicated
      statement: First declaration.
    - id: duplicated
      statement: Second declaration.
""",
        },
    )

    report = module.build_snapshot(repo=str(repo), revision="HEAD")

    assert report["completeness"] == "incomplete"
    assert report["summary"]["atom_count"] == 3
    assert [atom["text"] for atom in report["atoms"] if atom["origin"] == "explicit_intent"] == [
        "First declaration.",
        "Second declaration.",
    ]
    codes = {item["code"] for item in report["diagnostics"]}
    assert {"unreadable_yaml", "duplicate_node_id", "duplicate_atom_id"} <= codes
    assert report["summary"]["diagnostic_count"] == 4


def test_snapshot_marks_malformed_spec_envelope_incomplete(tmp_path: Path) -> None:
    module = load_module()
    repo = make_repo(
        tmp_path,
        {"specs/nodes/malformed.yaml": 'id: SG-1\nspec: "not a mapping"\n'},
    )

    report = module.build_snapshot(repo=str(repo), revision="HEAD")

    assert report["completeness"] == "incomplete"
    assert report["summary"]["node_count_by_mode"] == {"absent": 1}
    assert report["diagnostics"][0]["code"] == "invalid_spec_envelope"


def test_snapshot_omits_non_json_optional_metadata_and_reports_it(tmp_path: Path) -> None:
    module = load_module()
    repo = make_repo(
        tmp_path,
        {
            "specs/nodes/one.yaml": (
                "id: SG-1\natoms:\n  intents:\n    - statement: Count me.\n"
                "      premises: [2026-01-01]\n"
            )
        },
    )

    report = module.build_snapshot(repo=str(repo), revision="HEAD")

    assert report["completeness"] == "incomplete"
    assert report["summary"]["atom_count"] == 1
    assert "premises" not in report["atoms"][0]
    assert report["diagnostics"][0]["code"] == "invalid_intent_atom_attribute"
    json.dumps(report)


def test_snapshot_reads_exact_git_blobs_without_archive_attributes(tmp_path: Path) -> None:
    module = load_module()
    repo = make_repo(
        tmp_path,
        {
            ".gitattributes": (
                "specs/nodes/ignored.yaml export-ignore\n"
                "specs/nodes/substituted.yaml export-subst\n"
            ),
            "specs/nodes/ignored.yaml": "id: SG-1\nacceptance: [must remain visible]\n",
            "specs/nodes/substituted.yaml": "id: SG-2\nacceptance: ['$Format:%H$']\n",
        },
    )

    report = module.build_snapshot(repo=str(repo), revision="HEAD")

    assert report["completeness"] == "complete"
    assert report["summary"]["atom_count"] == 2
    assert {atom["text"] for atom in report["atoms"]} == {
        "must remain visible",
        "$Format:%H$",
    }


def test_snapshot_pathspec_cannot_be_interpreted_as_git_output_option(tmp_path: Path) -> None:
    module = load_module()
    repo = tmp_path / "git-options"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "Intent Atoms Test")
    git(repo, "config", "user.email", "intent-atoms@example.invalid")
    spec_root = f"--output={tmp_path}/escaped.tar"
    node = repo / spec_root / "one.yaml"
    node.parent.mkdir(parents=True)
    node.write_text("id: SG-1\nacceptance: [safe]\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "fixture")

    report = module.build_snapshot(repo=str(repo), revision="HEAD", spec_root=spec_root)

    assert report["summary"]["atom_count"] == 1
    assert not (tmp_path / "escaped.tar").exists()


def test_profile_digest_is_stable_across_json_formatting(tmp_path: Path) -> None:
    module = load_module()
    repo = make_repo(
        tmp_path,
        {"specs/nodes/one.yaml": "id: SG-1\nacceptance: [one]\n"},
    )
    original = json.loads(module.PROFILE_FILE.read_text(encoding="utf-8"))
    profile_file = tmp_path / "profile.json"
    module.PROFILE_FILE = profile_file
    profile_file.write_text(json.dumps(original, indent=2), encoding="utf-8")
    first = module.build_snapshot(repo=str(repo), revision="HEAD")
    profile_file.write_text(json.dumps(original, separators=(",", ":")), encoding="utf-8")
    second = module.build_snapshot(repo=str(repo), revision="HEAD")

    assert first["profile"]["sha256"] == second["profile"]["sha256"]


def test_snapshot_marks_missing_historical_spec_root_incomplete(tmp_path: Path) -> None:
    module = load_module()
    repo = make_repo(tmp_path, {"README.md": "Before the spec tree existed.\n"})

    report = module.build_snapshot(repo=str(repo), revision="HEAD")

    assert report["completeness"] == "incomplete"
    assert report["summary"]["atom_count"] == 0
    assert report["diagnostics"][0]["code"] == "missing_spec_root"


def test_snapshot_normalises_line_endings_but_preserves_inner_text(tmp_path: Path) -> None:
    module = load_module()
    repo = make_repo(
        tmp_path,
        {"specs/nodes/one.yaml": 'id: SG-1\nacceptance: ["first\\r\\nsecond"]\n'},
    )
    before_sha = git(repo, "rev-parse", "HEAD")
    (repo / "specs/nodes/one.yaml").write_text(
        'id: SG-1\nacceptance: ["first\\nsecond"]\n', encoding="utf-8"
    )
    git(repo, "add", "specs/nodes/one.yaml")
    git(repo, "commit", "-qm", "normalize line endings")

    before = module.build_snapshot(repo=str(repo), revision=before_sha)
    after = module.build_snapshot(repo=str(repo), revision="HEAD")

    assert before["atoms"][0]["text"] == "first\nsecond"
    assert after["atoms"][0]["text"] == "first\nsecond"


def test_snapshot_reports_absent_profile_fields_as_zero_atom_nodes(tmp_path: Path) -> None:
    module = load_module()
    repo = make_repo(
        tmp_path,
        {"specs/nodes/no-acceptance.yaml": "id: SG-1\nkind: spec\nobjective: Not counted.\n"},
    )

    report = module.build_snapshot(repo=str(repo), revision="HEAD")

    assert report["completeness"] == "complete"
    assert report["summary"]["node_count"] == 1
    assert report["summary"]["atom_count"] == 0
    assert report["nodes"][0]["mode"] == "absent"


def test_invalid_optional_atom_metadata_marks_partial_without_breaking_json(
    tmp_path: Path,
) -> None:
    module = load_module()
    repo = make_repo(
        tmp_path,
        {
            "specs/nodes/one.yaml": """
id: SG-1
kind: spec
atoms:
  intents:
    - id: A-1
      statement: Countable intent.
      premises: [2026-01-01]
"""
        },
    )

    report = module.build_snapshot(repo=str(repo), revision="HEAD")

    assert report["completeness"] == "incomplete"
    assert report["summary"]["atom_count"] == 1
    assert report["atoms"][0]["atom_id"] == "A-1"
    assert report["diagnostics"][0]["code"] == "invalid_intent_atom_attribute"
    json.dumps(report)


def test_snapshot_marks_ambiguous_fields_and_missing_node_identity_incomplete(
    tmp_path: Path,
) -> None:
    module = load_module()
    repo = make_repo(
        tmp_path,
        {
            "specs/nodes/ambiguous.yaml": """
id: SG-1
kind: spec
acceptance: [legacy]
spec:
  acceptance: [envelope]
""",
            "specs/nodes/missing-id.yaml": "acceptance: [unlinked]\n",
        },
    )

    report = module.build_snapshot(repo=str(repo), revision="HEAD")

    assert report["completeness"] == "incomplete"
    assert report["summary"]["atom_count"] == 0
    assert {item["code"] for item in report["diagnostics"]} == {
        "ambiguous_field_declaration",
        "missing_node_id",
    }


def test_spec_root_rejects_absolute_and_traversal_paths() -> None:
    module = load_module()

    for path in ("/tmp/specs", "specs/../private", ""):
        try:
            module._valid_spec_root(path)
        except ValueError:
            pass
        else:
            raise AssertionError(f"accepted invalid spec root: {path!r}")


def test_snapshot_cli_creates_output_parent_and_writes_artifact(tmp_path: Path) -> None:
    module = load_module()
    repo = make_repo(
        tmp_path,
        {"specs/nodes/one.yaml": "id: SG-1\nkind: spec\nacceptance: [one]\n"},
    )
    output = tmp_path / "runs" / "nested" / "snapshot.json"

    result = module.main(
        ["snapshot", "--repo", str(repo), "--revision", "HEAD", "--output", str(output)]
    )

    assert result == 0
    assert json.loads(output.read_text(encoding="utf-8"))["summary"]["atom_count"] == 1


def test_diff_ignores_reordering_and_file_moves_but_reports_changes(tmp_path: Path) -> None:
    module = load_module()
    first = """
id: SG-1
kind: spec
acceptance:
  - First criterion.
  - Second criterion.
"""
    explicit_first = """
id: SG-2
kind: spec
atoms:
  intents:
    - id: A-1
      statement: Original explicit intent.
"""
    repo = make_repo(
        tmp_path,
        {
            "specs/nodes/original.yaml": first,
            "specs/nodes/explicit.yaml": explicit_first,
        },
    )
    before_sha = git(repo, "rev-parse", "HEAD")
    old_path = repo / "specs/nodes/original.yaml"
    new_path = repo / "specs/nodes/renamed.yaml"
    old_path.rename(new_path)
    new_path.write_text(
        """
id: SG-1
kind: spec
acceptance:
  - " Second criterion. "
  - Third criterion.
""",
        encoding="utf-8",
    )
    (repo / "specs/nodes/explicit.yaml").write_text(
        """id: SG-2
kind: spec
atoms:
  intents:
    - id: A-1
      statement: Revised explicit intent.
""",
        encoding="utf-8",
    )
    git(repo, "add", "-A")
    git(repo, "commit", "-qm", "revise intent")
    after_sha = git(repo, "rev-parse", "HEAD")

    before = module.build_snapshot(repo=str(repo), revision=before_sha)
    after = module.build_snapshot(repo=str(repo), revision=after_sha)
    report = module.diff_snapshots(before, after)

    assert report["completeness"] == "complete"
    assert report["summary"] == {
        "counts_are_partial": False,
        "before_atom_count": 3,
        "after_atom_count": 3,
        "added_count": 1,
        "removed_count": 1,
        "modified_count": 1,
        "unchanged_count": 1,
        "net_count_delta": 0,
    }
    assert report["added"][0]["text"] == "Third criterion."
    assert report["removed"][0]["text"] == "First criterion."
    assert report["modified"][0]["atom_id"] == "A-1"
    assert report["modified"][0]["before"]["source_path"] == "specs/nodes/explicit.yaml"
    assert report["modified"][0]["after"]["source_path"] == "specs/nodes/explicit.yaml"


def test_diff_marks_incomplete_snapshots_and_rejects_incompatible_profiles(
    tmp_path: Path,
) -> None:
    module = load_module()
    repo = make_repo(
        tmp_path,
        {"specs/nodes/one.yaml": "id: SG-1\nkind: spec\nacceptance: [one]\n"},
    )
    snapshot = module.build_snapshot(repo=str(repo), revision="HEAD")
    incomplete = dict(snapshot)
    incomplete["completeness"] = "incomplete"
    report = module.diff_snapshots(snapshot, incomplete)
    assert report["completeness"] == "incomplete"
    assert report["summary"]["counts_are_partial"] is True

    incompatible = dict(snapshot)
    incompatible["profile"] = {**snapshot["profile"], "sha256": "0" * 64}
    try:
        module.diff_snapshots(snapshot, incompatible)
    except ValueError as error:
        assert "different profile" in str(error)
    else:
        raise AssertionError("accepted snapshots with different profile digests")


def test_diff_marks_a_change_from_acceptance_to_explicit_atom_mode(tmp_path: Path) -> None:
    module = load_module()
    repo = make_repo(
        tmp_path,
        {"specs/nodes/one.yaml": "id: SG-1\nkind: spec\nacceptance: [one]\n"},
    )
    before_sha = git(repo, "rev-parse", "HEAD")
    (repo / "specs/nodes/one.yaml").write_text(
        "id: SG-1\nkind: spec\natoms:\n  intents:\n    - id: A-1\n      statement: one\n",
        encoding="utf-8",
    )
    git(repo, "add", "specs/nodes/one.yaml")
    git(repo, "commit", "-qm", "make atom declaration explicit")

    before = module.build_snapshot(repo=str(repo), revision=before_sha)
    after = module.build_snapshot(repo=str(repo), revision="HEAD")
    report = module.diff_snapshots(before, after)

    assert report["summary"]["added_count"] == 1
    assert report["summary"]["removed_count"] == 1
    assert report["diagnostics"]["mode_transitions"] == [
        {"node_id": "SG-1", "before": "acceptance", "after": "explicit_intents"}
    ]


def test_replay_pins_first_parent_commits_and_writes_scoped_artifacts(
    tmp_path: Path,
) -> None:
    module = load_module()
    repo = make_repo(
        tmp_path,
        {"specs/nodes/one.yaml": "id: SG-1\nkind: spec\nacceptance: [one]\n"},
    )
    first_sha = git(repo, "rev-parse", "HEAD")
    git(repo, "commit", "--allow-empty", "-qm", "no spec change")
    middle_sha = git(repo, "rev-parse", "HEAD")
    (repo / "specs/nodes/one.yaml").write_text(
        "id: SG-1\nkind: spec\nacceptance: [one, two]\n", encoding="utf-8"
    )
    git(repo, "add", "specs/nodes/one.yaml")
    git(repo, "commit", "-qm", "add criterion")
    final_sha = git(repo, "rev-parse", "HEAD")
    output_dir = tmp_path / "runs" / "intent-atoms-replay"

    manifest = module.build_replay(repo=str(repo), revision="HEAD", count=30, output_dir=output_dir)

    assert manifest["selection"]["tip_commit_sha"] == final_sha
    assert len(manifest["analyzer_sha256"]) == 64
    assert manifest["selection"]["commit_shas_oldest_to_newest"] == [
        first_sha,
        middle_sha,
        final_sha,
    ]
    assert manifest["summary"] == {
        "snapshot_count": 3,
        "diff_count": 2,
        "incomplete_snapshot_count": 0,
        "net_atom_count_delta": 1,
        "added_count_total": 1,
        "removed_count_total": 0,
        "modified_count_total": 0,
        "source_mode_transition_count": 0,
    }
    assert (output_dir / "manifest.json").is_file()
    assert len(list(output_dir.glob("snapshot-*.json"))) == 3
    assert len(list(output_dir.glob("diff-*.json"))) == 2

    try:
        module.build_replay(repo=str(repo), revision="HEAD", count=1, output_dir=output_dir)
    except ValueError as error:
        assert "must be empty" in str(error)
    else:
        raise AssertionError("mixed a second replay into an existing output directory")


def test_replay_does_not_report_net_delta_from_an_incomplete_window(tmp_path: Path) -> None:
    module = load_module()
    repo = make_repo(
        tmp_path,
        {"specs/nodes/one.yaml": "id: SG-1\nkind: spec\nacceptance: [one]\n"},
    )
    (repo / "specs/nodes/one.yaml").write_text(
        "id: SG-1\nkind: spec\nacceptance: [unterminated\n", encoding="utf-8"
    )
    git(repo, "add", "specs/nodes/one.yaml")
    git(repo, "commit", "-qm", "introduce malformed historical spec")

    manifest = module.build_replay(
        repo=str(repo), revision="HEAD", count=2, output_dir=tmp_path / "partial-replay"
    )

    assert manifest["completeness"] == "incomplete"
    assert manifest["summary"]["incomplete_snapshot_count"] == 1
    assert manifest["summary"]["net_atom_count_delta"] is None
