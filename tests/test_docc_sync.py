from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_docc_sync_module():
    module_path = ROOT / "tools" / "validate_docc_sync.py"
    spec = importlib.util.spec_from_file_location("_validate_docc_sync_under_test", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_docc_sync_contract_passes() -> None:
    module = _load_docc_sync_module()

    assert module.validate(ROOT / "tools" / "docc_sync_contract.json") == []


def test_docc_sync_rejects_empty_synchronized_documents(tmp_path) -> None:
    module = _load_docc_sync_module()
    source = tmp_path / "empty.md"
    source.write_text("", encoding="utf-8")
    mirror = tmp_path / "mirror.md"
    mirror.write_text("anchor\n", encoding="utf-8")
    contract = tmp_path / "contract.json"
    contract.write_text(
        json.dumps(
            {
                "groups": [
                    {
                        "id": "empty-source",
                        "docs": [str(source)],
                        "docc": [str(mirror)],
                        "required_terms": ["anchor"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    assert module.validate(contract) == [
        f"empty-source: {source} is empty",
        f"empty-source: {source} is missing required term 'anchor'",
    ]
