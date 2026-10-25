"""Immutable facts for the bounded authored Intent graph policies."""

from dataclasses import dataclass


@dataclass(frozen=True)
class IntentGraphAppendContext:
    before_workspace: str
    after_workspace: str
    before_records: tuple[tuple[str, str], ...]
    after_records: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class IntentDerivationContext:
    source_class: str
    source_mode: str
    source_workspace: str
    target_workspace: str
    source_revision_resolved: bool
    target_revision_resolved: bool
