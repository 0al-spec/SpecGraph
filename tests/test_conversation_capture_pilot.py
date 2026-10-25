"""One source-backed CN-CAPTURE observation; no canonical or admission claim."""

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

import yaml

from test_conversation_notes import cli

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "docs/reviews/0045_cn_capture"
SELECTOR = f"tests/{Path(__file__).name}::test_cn_capture_saves_note_before_kind_selection"


def json_file(path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_cn_capture_binding_retains_draft_subjects_and_exact_source():
    from intent_decision_review.sources import GitSources, revision
    from subject_read_model_io import parse_subject_ref

    binding = json_file(PILOT / "bindings.json")
    excerpt = json_file(ROOT / binding["source_note"])
    proposal = yaml.safe_load((ROOT / binding["proposal"]["path"]).read_text())
    requirement = yaml.safe_load((ROOT / binding["requirement_candidate"]).read_text())
    criterion = yaml.safe_load((ROOT / binding["criterion_candidate"]).read_text())
    atom = next(a for a in proposal["atoms"]["intents"] if a["id"] == "CN-CAPTURE")
    assert binding["test_selector"] == SELECTOR
    assert binding["proposal"]["id"] == proposal["id"]
    assert binding["proposal"]["atom_id"] == atom["id"]
    assert not binding["canonical"] and binding["authority"] == "review_pending"
    assert requirement["proposed_record"]["revisions"][0]["statement"] == atom["statement"]
    membership = requirement["proposed_record"]["revisions"][0]["acceptance_criteria_refs"]
    assert membership == [
        {"subject": criterion["proposed_record"]["subject"], "mode": "exact", "revision": 1}
    ]
    for candidate in (requirement, criterion):
        assert candidate["artifact_kind"] == "subject_storage_candidate"
        assert candidate["gate_state"] == "review_pending"
        assert not candidate["canonical_adoption"] and not candidate["ready_for_materialization"]
        assert candidate["proposed_record"]["current_disposition"] is None
        assert candidate["proposed_record"]["revisions"][0]["provenance"] is None
        statement = candidate["proposed_record"]["revisions"][0]["statement"]
        assert (
            candidate["source_mapping"]["source_statement_sha256"]
            == hashlib.sha256(statement.encode()).hexdigest()
        )
        assert (
            candidate["source_mapping"]["proposed_destination"]["subject"]
            == candidate["proposed_record"]["subject"]
        )
        parse_subject_ref(candidate["proposed_record"]["subject"])
    citation = excerpt["note"]["sources"][0]
    assert citation["speaker"] == "human"
    archived = f"- `{excerpt['archive_excerpt_id']}`: «{citation['quote']}»"
    assert archived in (ROOT / excerpt["archive_path"]).read_text()
    assert citation["ref"] == f"operator-excerpt:{excerpt['archive_excerpt_id']}"
    assert not excerpt["canonical"]
    commit = revision(ROOT, "HEAD")
    sources = GitSources(ROOT, commit, commit)
    for reference in binding["implementation_refs"]:
        sources.declaration(reference)


def test_cn_capture_saves_note_before_kind_selection(tmp_path):
    binding = json_file(PILOT / "bindings.json")
    excerpt = json_file(ROOT / binding["source_note"])
    selected = excerpt["note"]
    output = Path(os.environ.get("CN_CAPTURE_EVIDENCE_DIR", str(tmp_path / "evidence")))
    output.mkdir(parents=True, exist_ok=True)
    sketch = output / "captured-sketch"
    # The new isolated sketch does not reconstruct the original note's parent.
    request = {
        "expected_revision": None,
        "source": selected["sources"][0],
        "changes": [
            {
                "op": "add",
                "id": selected["id"],
                "label": selected["label"],
                "detail": selected["detail"],
            }
        ],
    }
    curated_inputs = [
        "docs/reviews/0045_cn_capture/bindings.json",
        binding["source_note"],
        binding["requirement_candidate"],
        binding["criterion_candidate"],
        binding["proposal"]["path"],
        excerpt["archive_path"],
        "docs/proposals/0045_conversation_memory_exploration_vault.md",
    ]
    inputs = curated_inputs + [
        "tools/conversation_notes_cli.py",
        "tools/conversation_notes/api.py",
        "tools/conversation_notes/model.py",
        "tools/conversation_notes/store.py",
        "tools/conversation_notes/codec.py",
        "tools/conversation_notes/__init__.py",
        "tests/test_conversation_notes.py",
        "tests/test_conversation_capture_pilot.py",
        ".github/workflows/python-ci.yml",
    ]
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    hashes = {path: hashlib.sha256((ROOT / path).read_bytes()).hexdigest() for path in inputs}
    pinned = all(
        result.returncode == 0 and hashlib.sha256(result.stdout).hexdigest() == hashes[path]
        for path in inputs
        for result in [
            subprocess.run(["git", "show", f"{revision}:{path}"], cwd=ROOT, capture_output=True)
        ]
    )
    receipt = {
        "artifact_kind": "conversation_capture_test_observation",
        "schema_version": 1,
        "test_selector": SELECTOR,
        "proposal_atom": "CN-CAPTURE",
        "requirement_candidate": binding["requirement_candidate"],
        "criterion_candidate": binding["criterion_candidate"],
        "source_revision": revision,
        "source_file_sha256": hashes,
        "source_files_match_revision": pinned,
        "execution": {
            key: os.environ.get(key, "")
            for key in ("GITHUB_REPOSITORY", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT", "GITHUB_SHA")
        },
        "canonical_adoption": False,
        "fulfillment": "not_evaluated",
        "admission": "not_evaluated",
        "outcome": "incomplete",
        "commands": [],
    }
    for path in curated_inputs:
        target = output / "inputs" / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / path, target)

    def save():
        (output / "observation.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n"
        )

    def invoke(tool, payload=None):
        result = cli(sketch, tool, payload)
        receipt["commands"].append(
            {
                "tool": tool,
                "returncode": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        )
        save()  # A failing invocation retains its actual output and an incomplete observation.
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    (output / "request.json").write_text(json.dumps(request, ensure_ascii=False, indent=2) + "\n")
    save()
    assert invoke("read_notes")["revision"] is None
    updated = invoke("update_notes", request)
    restored = invoke("read_notes")
    assert updated["revision"] == restored["revision"]
    assert updated["previous_revision"] is None
    assert updated["diff"]["added"] == [
        {
            "id": selected["id"],
            "label": selected["label"],
            "detail": selected["detail"],
            "parent_id": None,
        }
    ]
    assert restored["nodes"] == [
        {
            "id": selected["id"],
            "label": selected["label"],
            "detail": selected["detail"],
            "parent_id": None,
            "sources": [request["source"]],
        }
    ]
    assert not restored["canonical"] and not updated["canonical"]
    assert restored["reviews"] == []
    assert "kind" not in request["changes"][0] and "kind" not in restored["nodes"][0]
    snapshot = Path(restored["snapshot_path"])
    assert {p.name for p in snapshot.iterdir()} == {"notes.hc", "notes.hcs", "metadata.json"}
    if os.environ.get("GITHUB_ACTIONS") == "true":
        assert pinned, "CI observation sources differ from the reported Git revision"
        assert receipt["execution"]["GITHUB_SHA"] == revision
        assert receipt["execution"]["GITHUB_RUN_ID"].isdecimal()
        assert receipt["execution"]["GITHUB_RUN_ATTEMPT"].isdecimal()
        assert "/" in receipt["execution"]["GITHUB_REPOSITORY"]
    receipt["captured_revision"] = restored["revision"]
    receipt["outcome"] = "passed"
    save()
