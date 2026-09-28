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


def test_spec_root_rejects_absolute_and_traversal_paths() -> None:
    module = load_module()

    for path in ("/tmp/specs", "specs/../private", ""):
        try:
            module._valid_spec_root(path)
        except ValueError:
            pass
        else:
            raise AssertionError(f"accepted invalid spec root: {path!r}")
