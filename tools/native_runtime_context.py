"""Immutable facts used to decide whether an installation can run."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeReadyFacts:
    artifact_kind: str
    status: str
    schema_version: object
    source_commit: str
