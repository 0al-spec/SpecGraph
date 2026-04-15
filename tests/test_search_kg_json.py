from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

_search_path = Path(__file__).resolve().parents[1] / "tools" / "search_kg_json.py"
_spec = importlib.util.spec_from_file_location("search_kg_json", _search_path)
assert _spec and _spec.loader
search_kg_json = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = search_kg_json
_spec.loader.exec_module(search_kg_json)


def test_iter_text_nodes_walks_nested_tree() -> None:
    payload = {
        "conversation": [
            {"role": "user", "content": "Need success criteria"},
            {"role": "assistant", "content": ["Define goals", "Track limits"]},
        ]
    }

    nodes = list(search_kg_json.iter_text_nodes(payload))

    assert ("$.conversation[0].content", "Need success criteria") in nodes
    assert ("$.conversation[1].content[1]", "Track limits") in nodes


def test_find_matches_scores_and_limits(tmp_path: Path) -> None:
    (tmp_path / "a.json").write_text(
        json.dumps({"msg": "Project goal and success criteria"}), encoding="utf-8"
    )
    (tmp_path / "b.json").write_text(
        json.dumps({"msg": "Limitations and constraints"}), encoding="utf-8"
    )
    (tmp_path / "broken.json").write_text("{not-valid", encoding="utf-8")

    matches = search_kg_json.find_matches(
        json_dir=tmp_path, query="goal criteria limitations", limit=1
    )

    assert len(matches) == 1
    assert matches[0].file.name in {"a.json", "b.json"}
    assert matches[0].score >= 1
    assert matches[0].kind in {"goal", "acceptance", "constraint"}


def test_find_matches_skips_non_utf8_json_file(tmp_path: Path) -> None:
    (tmp_path / "good.json").write_text(
        json.dumps({"msg": "success criteria and constraints"}), encoding="utf-8"
    )
    (tmp_path / "bad-encoding.json").write_bytes(b'{"msg":"\xff"}')

    matches = search_kg_json.find_matches(json_dir=tmp_path, query="success criteria", limit=5)

    assert len(matches) == 1
    assert matches[0].file.name == "good.json"


def test_find_matches_rejects_negative_limit(tmp_path: Path) -> None:
    (tmp_path / "a.json").write_text(json.dumps({"msg": "anything"}), encoding="utf-8")

    try:
        search_kg_json.find_matches(json_dir=tmp_path, query="anything", limit=-1)
    except ValueError as exc:
        assert "non-negative" in str(exc)
    else:
        raise AssertionError("Expected ValueError for negative limit")


def test_extract_requirements_from_text_detects_structured_sections() -> None:
    text = """
    Primary Goal
    - Keep stable terminology

    Constraints
    - Do not implement runtime code

    Success Criteria
    - Acceptance evidence aligns 1:1
    """

    extracted = search_kg_json.extract_requirements_from_text(
        text=text,
        path="$.messages[0].content",
    )

    assert len(extracted) >= 3
    kinds = {item.kind for item in extracted}
    assert "goal" in kinds
    assert "constraint" in kinds
    assert "acceptance" in kinds
    assert any(item.heading == "Success Criteria" for item in extracted)
    assert all(item.signal >= 3 for item in extracted)
    assert all(item.source_form == "line" for item in extracted)
    assert all(item.source_index > 0 for item in extracted)


def test_find_matches_can_filter_by_kind(tmp_path: Path) -> None:
    (tmp_path / "a.json").write_text(
        json.dumps(
            {
                "msg": "\n".join(
                    [
                        "Success Criteria",
                        "- Acceptance evidence aligns",
                        "Risks",
                        "- Data inconsistency risk",
                    ]
                )
            }
        ),
        encoding="utf-8",
    )

    matches = search_kg_json.find_matches(
        json_dir=tmp_path,
        query="acceptance risk",
        limit=10,
        kind="acceptance",
    )

    assert matches
    assert all(match.kind == "acceptance" for match in matches)


def test_find_matches_keeps_non_bullet_requirement_lines(tmp_path: Path) -> None:
    text = "\n".join(
        [
            "Do not implement runtime code",
            "Do not edit unrelated files",
            "Must preserve stable spec IDs",
            "Should keep terminology consistent",
            "Avoid broad refactors in this task",
            "Do not trust stale worktree paths",
            "Need to validate acceptance evidence",
            "Do not skip dependency checks",
            "Should report blockers clearly",
            "Do not hide failed validations",
            "Need to keep outputs deterministic",
            "Should keep changes focused",
        ]
    )
    assert len(text) > 240

    (tmp_path / "notes.json").write_text(json.dumps({"notes": text}), encoding="utf-8")

    matches = search_kg_json.find_matches(
        json_dir=tmp_path,
        query="runtime code deterministic",
        limit=10,
    )

    assert matches
    assert any("runtime code" in match.text.lower() for match in matches)


def test_find_matches_with_cache_request_response_pair(tmp_path: Path) -> None:
    (tmp_path / "ideas.json").write_text(
        json.dumps({"notes": "Success criteria: response cache must be fast"}), encoding="utf-8"
    )
    cache_file = tmp_path / ".search_kg_cache.json"

    first_matches, first_cache_hit = search_kg_json.find_matches_with_cache(
        json_dir=tmp_path,
        query="response cache",
        limit=5,
        cache_file=cache_file,
        use_cache=True,
    )
    second_matches, second_cache_hit = search_kg_json.find_matches_with_cache(
        json_dir=tmp_path,
        query="response cache",
        limit=5,
        cache_file=cache_file,
        use_cache=True,
    )

    assert first_cache_hit is False
    assert second_cache_hit is True
    assert cache_file.exists()
    assert [m.text for m in second_matches] == [m.text for m in first_matches]
    assert [m.kind for m in second_matches] == [m.kind for m in first_matches]


def test_collect_requirement_records_captures_provenance_shape(tmp_path: Path) -> None:
    (tmp_path / "ideas.json").write_text(
        json.dumps(
            {
                "conversation": {
                    "content": "\n".join(
                        [
                            "Constraints",
                            "- Must preserve stable IDs",
                            "Success Criteria",
                            "- Acceptance evidence aligns 1:1",
                        ]
                    )
                }
            }
        ),
        encoding="utf-8",
    )

    records = search_kg_json.collect_requirement_records(tmp_path)

    assert len(records) == 2
    assert {record.kind for record in records} == {"constraint", "acceptance"}
    assert all(record.file.name == "ideas.json" for record in records)
    assert all(record.requirement_id.startswith("req-") for record in records)
    assert any(record.heading == "Constraints" for record in records)
    assert any(record.heading == "Success Criteria" for record in records)


def test_build_requirement_artifacts_provide_projection_and_provenance(tmp_path: Path) -> None:
    (tmp_path / "ideas.json").write_text(
        json.dumps(
            {
                "notes": "\n".join(
                    [
                        "Goal",
                        "- Keep the graph readable",
                        "Risks",
                        "- Over-atomized ladders are hard to review",
                    ]
                )
            }
        ),
        encoding="utf-8",
    )

    records = search_kg_json.collect_requirement_records(tmp_path)
    artifact_dir = tmp_path / "artifacts"
    projection_path, provenance_path = search_kg_json.write_requirement_artifacts(
        artifact_dir=artifact_dir,
        json_dir=tmp_path,
        records=records,
    )

    projection = json.loads(projection_path.read_text(encoding="utf-8"))
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))

    assert projection["artifact_kind"] == "requirement_projection"
    assert projection["requirement_count"] == 2
    assert projection["by_kind"]["goal"] == 1
    assert projection["by_kind"]["risk"] == 1
    assert projection["requirements"][0]["projection_links"]

    assert provenance["artifact_kind"] == "requirement_provenance"
    assert provenance["record_count"] == 2
    assert provenance["provenance_records"][0]["requirement_id"].startswith("req-")
    assert provenance["provenance_records"][0]["json_path"].startswith("$.")


def test_main_can_dump_requirements_and_write_artifacts_json(tmp_path: Path, capsys) -> None:
    (tmp_path / "ideas.json").write_text(
        json.dumps(
            {
                "notes": "\n".join(
                    [
                        "Assumptions",
                        "- Assume the viewer stays read-only",
                        "Constraints",
                        "- Do not mutate canonical specs directly",
                    ]
                )
            }
        ),
        encoding="utf-8",
    )
    artifact_dir = tmp_path / "derived"
    original_argv = sys.argv
    sys.argv = [
        "search_kg_json.py",
        "--json-dir",
        str(tmp_path),
        "--dump-requirements",
        "--format",
        "json",
        "--artifact-dir",
        str(artifact_dir),
    ]
    try:
        exit_code = search_kg_json.main()
    finally:
        sys.argv = original_argv

    assert exit_code == 0
    captured = capsys.readouterr()
    dumped = json.loads(captured.out)
    assert len(dumped) == 2
    assert {item["kind"] for item in dumped} == {"assumption", "constraint"}
    assert (artifact_dir / "requirement_projection.json").exists()
    assert (artifact_dir / "requirement_provenance.json").exists()
    assert "[artifacts] projection:" in captured.err


def test_main_can_write_artifacts_without_query(tmp_path: Path, capsys) -> None:
    (tmp_path / "ideas.json").write_text(
        json.dumps({"notes": "Goal: Keep grouped aggregate nodes visible."}),
        encoding="utf-8",
    )
    artifact_dir = tmp_path / "derived"
    original_argv = sys.argv
    sys.argv = [
        "search_kg_json.py",
        "--json-dir",
        str(tmp_path),
        "--artifact-dir",
        str(artifact_dir),
    ]
    try:
        exit_code = search_kg_json.main()
    finally:
        sys.argv = original_argv

    assert exit_code == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "[artifacts] projection:" in captured.err
    assert (artifact_dir / "requirement_projection.json").exists()
    assert (artifact_dir / "requirement_provenance.json").exists()
