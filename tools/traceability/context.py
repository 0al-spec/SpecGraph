"""Immutable declarations and references, independent of Git and artifact I/O."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Declaration:
    kind: str
    reference: str
    source_path: str
    source_location: str
    source_sha256: str
    syntax_kind: str = "authored_id"

    def to_payload(self) -> dict[str, str]:
        return dict(vars(self))


@dataclass(frozen=True)
class DeclaredReference:
    owner: str
    relation: str
    target_kind: str
    target: str
    source_path: str
    source_location: str

    def to_payload(self) -> dict[str, str]:
        return dict(vars(self))


@dataclass(frozen=True)
class ReferenceFacts:
    supported_syntax: bool
    source_available: bool
    candidate_count: int
    expected_kind: bool = True


@dataclass(frozen=True)
class ReferenceResolution:
    declared: DeclaredReference
    status: str
    candidates: tuple[Declaration, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "candidates", tuple(self.candidates))

    def to_payload(self) -> dict[str, object]:
        return {
            "declared": self.declared.to_payload(),
            "status": self.status,
            "candidates": [item.to_payload() for item in self.candidates],
        }
