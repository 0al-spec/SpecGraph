"""Immutable display facts; no graph lifecycle or publication authority."""

from dataclasses import dataclass
from enum import Enum


class DisplayState(str, Enum):
    CURRENT = "current"
    EMPTY = "empty"
    STALE = "stale"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class DisplayFacts:
    read_failed: bool
    has_snapshot: bool
    has_nodes: bool


@dataclass(frozen=True)
class SnapshotContinuityFacts:
    previous_revision_exists: bool
    observed_revision_exists: bool
