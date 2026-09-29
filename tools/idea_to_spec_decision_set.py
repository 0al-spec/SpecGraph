"""Small, explicit wrapper for applying named decisions to one typed context."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Generic, TypeVar

Context = TypeVar("Context")


@dataclass(frozen=True)
class SpecField(Generic[Context]):
    name: str
    decide: Callable[[Context], str]


@dataclass(frozen=True)
class SpecSet(Generic[Context]):
    fields: tuple[SpecField[Context], ...]

    def __post_init__(self) -> None:
        names = [field.name for field in self.fields]
        if len(names) != len(set(names)):
            raise ValueError("SpecSet field names must be unique")

    def apply(self, context: Context) -> dict[str, str]:
        return {field.name: field.decide(context) for field in self.fields}
