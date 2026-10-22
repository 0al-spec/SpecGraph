"""Explicit in-process provider selection. No dynamic imports or discovery."""

from dataclasses import dataclass
from typing import Protocol

from .evidence import EvidenceRequest, ProviderEvidence
from .snapshot import TraceSnapshot


class EvidenceProvider(Protocol):
    provider_id: str
    version: str

    def collect(self, request: EvidenceRequest) -> ProviderEvidence: ...


@dataclass(frozen=True)
class EvidenceRegistry:
    providers: tuple[EvidenceProvider, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "providers", tuple(self.providers))
        ids = [p.provider_id for p in self.providers]
        if not all(ids) or len(ids) != len(set(ids)):
            raise ValueError("provider registry requires distinct nonempty IDs")

    def collect(self, request: EvidenceRequest, provider_ids: tuple[str, ...]) -> TraceSnapshot:
        selected = tuple(sorted(provider_ids))
        if not selected or len(set(selected)) != len(selected):
            raise ValueError("select distinct explicit provider IDs")
        available = {p.provider_id: p for p in self.providers}
        if set(selected) - available.keys():
            raise ValueError("unknown provider ID")
        reports = []
        for identity in selected:
            provider = available[identity]
            report = provider.collect(request)
            if (report.identity.provider_id, report.identity.version) != (
                identity,
                provider.version,
            ):
                raise ValueError("provider result identity/version mismatch")
            reports.append(report)
        return TraceSnapshot(request.scope, tuple(reports))
