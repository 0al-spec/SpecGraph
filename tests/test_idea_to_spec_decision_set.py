from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.idea_to_spec_decision_set import SpecField, SpecSet  # noqa: E402


def test_spec_set_evaluates_named_fields_once_in_declaration_order() -> None:
    calls: list[str] = []

    def field(name: str) -> SpecField[int]:
        def decide(context: int) -> str:
            calls.append(name)
            return f"{name}:{context}"

        return SpecField(name, decide)

    decisions = SpecSet(fields=(field("first"), field("second")))

    assert decisions.apply(3) == {"first": "first:3", "second": "second:3"}
    assert calls == ["first", "second"]


def test_spec_set_rejects_duplicate_field_names() -> None:
    with pytest.raises(ValueError, match="field names must be unique"):
        SpecSet(fields=(SpecField("state", str), SpecField("state", str)))
