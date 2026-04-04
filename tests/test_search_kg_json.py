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


def test_find_matches_with_cache_request_response_pair(tmp_path: Path) -> None:
    (tmp_path / "ideas.json").write_text(
        json.dumps({"notes": "Agent memory needs fast response cache"}), encoding="utf-8"
    )
    cache_file = tmp_path / ".search_kg_cache.json"

    first_matches, first_cache_hit = search_kg_json.find_matches_with_cache(
        json_dir=tmp_path,
        query="memory response",
        limit=5,
        cache_file=cache_file,
        use_cache=True,
    )
    second_matches, second_cache_hit = search_kg_json.find_matches_with_cache(
        json_dir=tmp_path,
        query="memory response",
        limit=5,
        cache_file=cache_file,
        use_cache=True,
    )

    assert first_cache_hit is False
    assert second_cache_hit is True
    assert cache_file.exists()
    assert [m.text for m in second_matches] == [m.text for m in first_matches]
