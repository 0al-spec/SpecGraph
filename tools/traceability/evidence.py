"""Immutable, revision-bound provider facts; no source collection or execution."""

import json
import re
from dataclasses import dataclass
from pathlib import Path

from intent_decision_review.sources import encoded

from .context import Declaration, ReferenceResolution
from .execution import ExecutionEvidence, PublicationExecutionSelection


def ordered(values):
    return tuple(sorted(values, key=lambda value: encoded(value.to_payload())))


@dataclass(frozen=True)
class EvidenceScope:
    repository_id: str
    source_revision: str
    spec_ids: tuple[str, ...]
    resolver_profile: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "spec_ids", tuple(sorted(self.spec_ids)))
        if not self.repository_id or not self.resolver_profile:
            raise ValueError("repository identity and resolver profile are required")
        if not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", self.source_revision):
            raise ValueError("evidence scope requires a full pinned Git revision")
        if (
            not self.spec_ids
            or not all(s and s == s.strip() for s in self.spec_ids)
            or len(self.spec_ids) != len(set(self.spec_ids))
        ):
            raise ValueError("subject selection must contain distinct explicit spec IDs")

    def to_payload(self) -> dict[str, object]:
        return dict(
            repository_id=self.repository_id,
            source_revision=self.source_revision,
            spec_ids=list(self.spec_ids),
            resolver_profile=self.resolver_profile,
        )


@dataclass(frozen=True)
class EvidenceRequest:
    repository_root: Path
    scope: EvidenceScope
    artifact_paths: tuple[str, ...] = ()
    execution_selection: PublicationExecutionSelection | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "artifact_paths", tuple(self.artifact_paths))
        if not self.repository_root.is_absolute():
            raise ValueError("repository root must be explicit and absolute")


@dataclass(frozen=True)
class ProviderIdentity:
    provider_id: str
    version: str
    profile: str
    files_sha256: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "files_sha256", tuple(sorted(tuple(p) for p in self.files_sha256)))
        if not self.provider_id or not self.version or not self.profile:
            raise ValueError("provider identity, version and profile are required")
        if len({p for p, _ in self.files_sha256}) != len(self.files_sha256):
            raise ValueError("duplicate analyzer source path")

    def to_payload(self) -> dict[str, object]:
        return dict(
            provider_id=self.provider_id,
            version=self.version,
            profile=self.profile,
            files_sha256=dict(self.files_sha256),
        )


@dataclass(frozen=True)
class SourceEvidence:
    path: str
    status: str
    sha256: str | None = None
    diagnostic: str | None = None

    def to_payload(self) -> dict[str, object]:
        return dict(
            path=self.path, status=self.status, sha256=self.sha256, diagnostic=self.diagnostic
        )


@dataclass(frozen=True)
class EvidenceDiagnostic:
    code: str
    owner: str | None = None
    index: int | None = None
    message: str | None = None

    def to_payload(self) -> dict[str, object]:
        return {k: v for k, v in vars(self).items() if v is not None}


@dataclass(frozen=True)
class NodeEvidence:
    spec_id: str
    atoms: tuple[Declaration, ...]
    links: tuple[ReferenceResolution, ...]
    inventory_complete: bool
    resolution_complete: bool
    diagnostics: tuple[EvidenceDiagnostic, ...] = ()
    source_status: str | None = None
    source_gate: str | None = None

    def __post_init__(self) -> None:
        if any(
            v is not None and not isinstance(v, str) for v in (self.source_status, self.source_gate)
        ):
            raise ValueError("source lifecycle values must be text or null")
        object.__setattr__(self, "atoms", ordered(self.atoms))
        object.__setattr__(
            self,
            "links",
            ordered(
                ReferenceResolution(r.declared, r.status, ordered(r.candidates)) for r in self.links
            ),
        )
        object.__setattr__(self, "diagnostics", ordered(self.diagnostics))
        if any(d.kind != "atom" for d in self.atoms):
            raise ValueError("atom inventory requires atom declarations")

    def to_payload(self) -> dict[str, object]:
        return {
            "spec_id": self.spec_id,
            "source_lifecycle": {"status": self.source_status, "gate_state": self.source_gate},
            "inventory": {"complete": self.inventory_complete, "observed_count": len(self.atoms)},
            "declaration_resolution": {"complete": self.resolution_complete},
            "atoms": [d.to_payload() for d in self.atoms],
            "links": [r.to_payload() for r in self.links],
            "diagnostics": [d.to_payload() for d in self.diagnostics],
        }


@dataclass(frozen=True)
class ProviderEvidence:
    identity: ProviderIdentity
    scope: EvidenceScope
    nodes: tuple[NodeEvidence, ...]
    sources: tuple[SourceEvidence, ...]
    collection_digest: str | None = None
    execution: ExecutionEvidence | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "nodes", tuple(sorted(self.nodes, key=lambda n: n.spec_id)))
        object.__setattr__(self, "sources", ordered(self.sources))
        if tuple(n.spec_id for n in self.nodes) != self.scope.spec_ids:
            raise ValueError(
                "provider must report every selected node, including unavailable nodes"
            )

    def to_payload(self) -> dict[str, object]:
        payload = dict(
            identity=self.identity.to_payload(),
            scope=self.scope.to_payload(),
            nodes=[n.to_payload() for n in self.nodes],
            sources=[s.to_payload() for s in self.sources],
            collection_digest=self.collection_digest,
        )
        if self.execution is not None:
            payload["execution"] = self.execution.to_payload()
        return payload


@dataclass(frozen=True)
class AgreementFacts:
    values: frozenset[str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "values", frozenset(self.values))


@dataclass(frozen=True)
class ResolutionCompletenessFacts:
    statuses: frozenset[str]

    def __post_init__(self) -> None:
        object.__setattr__(self, "statuses", frozenset(self.statuses))


@dataclass(frozen=True)
class EvidenceConflict:
    fact_kind: str
    key: tuple[str, ...]
    variants: tuple[tuple[str, tuple[str, ...]], ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "key", tuple(self.key))
        object.__setattr__(self, "variants", tuple((v, tuple(p)) for v, p in self.variants))

    def to_payload(self) -> dict[str, object]:
        return dict(
            fact_kind=self.fact_kind,
            key=list(self.key),
            variants=[
                {"value": json.loads(value), "providers": list(providers)}
                for value, providers in self.variants
            ],
        )
