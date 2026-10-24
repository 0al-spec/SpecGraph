import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

from conversation_notes.api import read_notes, update_notes  # noqa: E402
from conversation_notes.model import NotesError  # noqa: E402
from conversation_notes.store import NotesStore  # noqa: E402


def source(quote="Человек говорит, агент делает заметки.", speaker="human"):
    return {"ref": "conversation:pilot/turn:1", "quote": quote, "speaker": speaker}


def apply(root, changes, revision=None, citation=None):
    return update_notes(
        root, {"expected_revision": revision, "source": citation or source(), "changes": changes}
    )


def seed(root):
    return apply(
        root,
        [
            {"op": "add", "id": "conversation", "label": "Разговор"},
            {"op": "add", "id": "human", "label": "Человек", "parent_id": "conversation"},
            {"op": "add", "id": "agent", "label": "Агент", "parent_id": "conversation"},
            {"op": "add", "id": "notes", "label": "Заметки", "parent_id": "agent"},
        ],
    )


def cli(root, tool="read_notes", request=None, *options):
    return subprocess.run(
        [
            sys.executable,
            "-B",
            str(TOOLS / "conversation_notes_cli.py"),
            tool,
            "--workspace",
            str(root),
            *options,
        ],
        input=json.dumps(request, ensure_ascii=False) if request is not None else None,
        text=True,
        capture_output=True,
        check=False,
    )


def test_read_empty_does_not_create_workspace(tmp_path):
    root = tmp_path / "sketch"
    assert read_notes(root)["revision"] is None
    assert not root.exists()


def test_conversation_survives_new_process_and_preserves_source(tmp_path):
    first = seed(tmp_path)
    quote = "Назовём это «Фиксация мыслей».\nПока разместим рядом с человеком."
    correction = source(quote)
    second = apply(
        tmp_path,
        [
            {
                "op": "revise",
                "id": "notes",
                "label": "Фиксация мыслей",
                "detail": "Сохранять сразу",
            },
            {"op": "move", "id": "notes", "parent_id": "human"},
            {"op": "link", "source_id": "agent", "target_id": "notes", "label": "ведёт"},
        ],
        first["revision"],
        correction,
    )
    approved = apply(tmp_path, [{"op": "approve"}], second["revision"], source("Да, так верно."))
    result = cli(tmp_path, "read_notes", None, "--history-limit", "10")
    assert result.returncode == 0, result.stderr
    restored = json.loads(result.stdout)
    note = next(n for n in restored["nodes"] if n["id"] == "notes")
    assert note == {
        "id": "notes",
        "label": "Фиксация мыслей",
        "detail": "Сохранять сразу",
        "parent_id": "human",
        "sources": [source(), correction],
    }
    assert restored["revision"] == approved["revision"]
    assert restored["reviews"][0]["revision"] == second["revision"]
    assert [h["revision"] for h in restored["history"]] == [
        approved["revision"],
        second["revision"],
        first["revision"],
    ]
    assert not restored["canonical"]
    assert restored["links"][0]["sources"] == [correction]
    assert second["diff"]["updated"][0]["fields"]["label"] == {
        "before": "Заметки",
        "after": "Фиксация мыслей",
    }


def test_move_subtree_retains_descendant_identity_and_quotes(tmp_path):
    first = seed(tmp_path)
    apply(tmp_path, [{"op": "move", "id": "agent", "parent_id": "human"}], first["revision"])
    branch = read_notes(tmp_path, node_id="human")
    assert [n["id"] for n in branch["nodes"]] == ["human", "agent", "notes"]
    assert branch["nodes"][-1]["sources"] == [source()]
    assert branch["omitted_nodes"] == 1


@pytest.mark.parametrize("parent_id", [None, "group"])
@pytest.mark.parametrize("new_citation", [False, True])
def test_sibling_reorder_diff_matches_persisted_order(tmp_path, parent_id, new_citation):
    changes = [{"op": "add", "id": "group", "label": "Group"}] if parent_id else []
    changes.extend(
        [
            {"op": "add", "id": "a", "label": "A", "parent_id": parent_id},
            {"op": "add", "id": "b", "label": "B", "parent_id": parent_id},
            {"op": "add", "id": "child", "label": "Child", "parent_id": "a"},
        ]
    )
    first = apply(tmp_path, changes)
    citation = source("Move A after B.") if new_citation else source()
    result = cli(
        tmp_path,
        "update_notes",
        {
            "expected_revision": first["revision"],
            "source": citation,
            "changes": [{"op": "move", "id": "a", "parent_id": parent_id}],
        },
    )
    assert result.returncode == 0, result.stderr
    updated = json.loads(result.stdout)
    restored = json.loads(cli(tmp_path).stdout)
    assert restored["revision"] == updated["revision"] != first["revision"]
    assert [n["id"] for n in restored["nodes"] if n["parent_id"] == parent_id] == ["b", "a"]
    assert next(n for n in restored["nodes"] if n["id"] == "child")["sources"] == [source()]
    assert {n["id"]: n for n in updated["diff"]["updated"]} == {
        "a": {
            "id": "a",
            "fields": {"sibling_index": {"before": 0, "after": 1}},
            "sources_added": int(new_citation),
        },
        "b": {
            "id": "b",
            "fields": {"sibling_index": {"before": 1, "after": 0}},
            "sources_added": 0,
        },
    }


@pytest.mark.parametrize(
    "change",
    [
        {"op": "move", "id": "conversation", "parent_id": "notes"},
        {"op": "move", "id": "notes", "parent_id": "missing"},
        {"op": "add", "id": "notes", "label": "duplicate"},
        {"op": "add", "id": "../outside", "label": "unsafe"},
        {"op": "link", "source_id": "agent", "target_id": "missing", "label": "unknown"},
        {"op": "revise", "id": "missing", "label": "unknown"},
        {"op": "revise", "id": "notes", "label": "line\nbreak"},
        {"op": "revise", "id": "notes", "label": "invalid\u2028separator"},
        {"op": "revise", "id": "notes", "label": "ok", "unrecognized": True},
        {"op": "delete", "id": "notes"},
    ],
)
def test_bad_batch_never_publishes_partial_changes(tmp_path, change):
    first = seed(tmp_path)
    before = read_notes(tmp_path)
    with pytest.raises(NotesError):
        apply(
            tmp_path,
            [{"op": "revise", "id": "human", "label": "Must not leak"}, change],
            first["revision"],
        )
    assert read_notes(tmp_path) == before


def test_stale_agent_cannot_overwrite_newer_notes(tmp_path):
    first = seed(tmp_path)
    second = apply(
        tmp_path, [{"op": "revise", "id": "notes", "detail": "Fresh"}], first["revision"]
    )
    with pytest.raises(NotesError, match="Revision conflict"):
        apply(tmp_path, [{"op": "revise", "id": "notes", "detail": "Stale"}], first["revision"])
    assert read_notes(tmp_path)["revision"] == second["revision"]


def test_two_writers_compare_revision_inside_lock(tmp_path):
    first = seed(tmp_path)

    def write(label):
        request = {
            "expected_revision": first["revision"],
            "source": source(),
            "changes": [{"op": "revise", "id": "notes", "label": label}],
        }
        return cli(tmp_path, "update_notes", request)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(write, ["One", "Two"]))
    assert sorted(result.returncode for result in results) == [0, 2]
    assert "Revision conflict" in next(r.stderr for r in results if r.returncode == 2)


def test_interrupted_publication_keeps_complete_previous_snapshot(tmp_path, monkeypatch):
    first = seed(tmp_path)
    before = read_notes(tmp_path, history_limit=10)

    def interrupt(self, revision):
        raise OSError("simulated interruption before CURRENT")

    with monkeypatch.context() as patch:
        patch.setattr(NotesStore, "publish", interrupt)
        with pytest.raises(OSError, match="simulated"):
            apply(
                tmp_path,
                [{"op": "revise", "id": "notes", "label": "Unpublished"}],
                first["revision"],
            )
    assert read_notes(tmp_path, history_limit=10) == before
    apply(tmp_path, [{"op": "revise", "id": "notes", "label": "Retry"}], first["revision"])
    assert len(read_notes(tmp_path, history_limit=10)["history"]) == 2


def test_approval_records_exact_reviewed_revision_and_does_not_follow_edits(tmp_path):
    first = seed(tmp_path)
    approval = apply(tmp_path, [{"op": "approve"}], first["revision"], source("Одобряю."))
    edit = apply(
        tmp_path, [{"op": "revise", "id": "notes", "label": "Changed"}], approval["revision"]
    )
    result = read_notes(tmp_path)
    assert result["revision"] == edit["revision"]
    assert result["reviews"][0]["revision"] == first["revision"]
    assert result["canonical"] is False


def test_approval_cannot_be_mixed_with_unseen_edits_or_agent_quote(tmp_path):
    first = seed(tmp_path)
    with pytest.raises(NotesError, match="separately"):
        apply(
            tmp_path,
            [{"op": "revise", "id": "notes", "label": "Unseen"}, {"op": "approve"}],
            first["revision"],
        )
    with pytest.raises(NotesError, match="human quotation"):
        apply(tmp_path, [{"op": "approve"}], first["revision"], source("I approve", "agent"))
    assert read_notes(tmp_path)["revision"] == first["revision"]


@pytest.mark.parametrize(
    "bad_source",
    [
        {},
        {"ref": "x", "quote": "", "speaker": "human"},
        {"ref": "x", "quote": "text", "speaker": "unknown"},
    ],
)
def test_missing_or_invalid_attribution_is_not_saved(tmp_path, bad_source):
    with pytest.raises(NotesError):
        update_notes(
            tmp_path,
            {
                "expected_revision": None,
                "source": bad_source,
                "changes": [{"op": "add", "label": "Test"}],
            },
        )
    assert read_notes(tmp_path)["revision"] is None


def test_literal_hcs_strings_round_trip_without_yaml_unescaping(tmp_path):
    label = 'Мысль: "кавычки", apostrophe\'s, #tag и \\n — буквально 😀'
    result = apply(tmp_path, [{"op": "add", "label": label, "detail": "true"}])
    restored = read_notes(tmp_path)
    assert restored["nodes"][0]["label"] == label
    assert restored["nodes"][0]["detail"] == "true"
    assert restored["nodes"][0]["id"] == result["diff"]["added"][0]["id"]


def test_revise_can_attach_another_quote_without_changing_words(tmp_path):
    first = seed(tmp_path)
    second = apply(
        tmp_path, [{"op": "revise", "id": "notes"}], first["revision"], source("Их надо сохранять.")
    )
    assert second["diff"]["updated"] == [{"id": "notes", "fields": {}, "sources_added": 1}]
    assert len(read_notes(tmp_path, node_id="notes")["nodes"][0]["sources"]) == 2


def test_snapshot_tampering_and_bad_current_are_reported(tmp_path):
    first = seed(tmp_path)
    snapshot = Path(first["snapshot_path"])
    (snapshot / "notes.hc").write_text("Note#other\n", encoding="utf-8")
    with pytest.raises(NotesError, match="outside update_notes"):
        read_notes(tmp_path)
    (tmp_path / "CURRENT").write_text("../../elsewhere\n", encoding="utf-8")
    result = cli(tmp_path)
    assert result.returncode == 2
    assert result.stdout == ""
    assert "Invalid CURRENT" in json.loads(result.stderr)["error"]


def test_cli_input_file_and_invalid_json(tmp_path):
    request = tmp_path / "request.json"
    request.write_text(
        json.dumps(
            {
                "expected_revision": None,
                "source": source(),
                "changes": [{"op": "add", "label": "Saved"}],
            }
        ),
        encoding="utf-8",
    )
    result = cli(tmp_path / "sketch", "update_notes", None, "--input", str(request))
    assert result.returncode == 0, result.stderr
    assert json.loads(cli(tmp_path / "sketch").stdout)["nodes"][0]["label"] == "Saved"
    result = subprocess.run(
        [
            sys.executable,
            "-B",
            str(TOOLS / "conversation_notes_cli.py"),
            "update_notes",
            "--workspace",
            str(tmp_path / "sketch"),
        ],
        input="{bad",
        text=True,
        capture_output=True,
    )
    assert result.returncode == 2 and not result.stdout
    assert "error" in json.loads(result.stderr)


@pytest.mark.skipif(
    not os.environ.get("HYPERCODE_BIN"),
    reason="Optional reference Hypercode CLI compatibility check",
)
def test_reference_hypercode_reads_saved_sketch(tmp_path):
    label = 'Мысль: "quotes", apostrophe\'s, literal \\n 😀'
    saved = apply(
        tmp_path,
        [
            {"op": "add", "id": "root", "label": label},
            {"op": "add", "id": "child", "label": "Child", "parent_id": "root"},
        ],
    )
    snapshot = Path(saved["snapshot_path"])
    result = subprocess.run(
        [
            os.environ["HYPERCODE_BIN"],
            "emit",
            str(snapshot / "notes.hc"),
            "--hcs",
            str(snapshot / "notes.hcs"),
            "--ir-version",
            "2",
        ],
        text=True,
        capture_output=True,
        check=True,
    )
    document = json.loads(result.stdout)
    assert document["nodes"][0]["id"] == "root"
    assert document["nodes"][0]["properties"]["label"]["value"] == label
    assert document["nodes"][0]["children"][0]["id"] == "child"
