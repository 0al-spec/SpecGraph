"""First provider: reuse one pinned publication declaration collection, never tests."""

import hashlib
import subprocess
from pathlib import Path

import yaml

from .evidence import (
    EvidenceDiagnostic,
    EvidenceRequest,
    NodeEvidence,
    ProviderEvidence,
    ProviderIdentity,
    ResolutionCompletenessFacts,
    SourceEvidence,
)
from .publication import PROFILE, analyzer_identity, collect_publication_links
from .resolution_completeness_spec import RESOLUTION_COMPLETENESS_SPEC


class PublicationEvidenceProvider:
    provider_id = "publication.declarations"
    version = "1.0.0"

    def identity(self) -> ProviderIdentity:
        tools = Path(__file__).resolve().parents[1]
        hashes = dict(analyzer_identity()["files_sha256"])
        for path in (
            "traceability/evidence.py",
            "traceability/publication_provider.py",
            "traceability/providers.py",
            "traceability/snapshot.py",
            "traceability/fact_agreement_spec.py",
            "traceability/resolution_completeness_spec.py",
            "publication_trace_snapshot.py",
        ):
            hashes[path] = hashlib.sha256((tools / path).read_bytes()).hexdigest()
        return ProviderIdentity(self.provider_id, self.version, PROFILE, tuple(hashes.items()))

    def collect(self, request: EvidenceRequest) -> ProviderEvidence:
        if request.scope.resolver_profile != PROFILE:
            raise ValueError("publication provider requires the exact-links v1 profile")
        if request.scope.spec_ids != ("SG-SPEC-0071",):
            raise ValueError("publication provider supports only the explicit SG-SPEC-0071 cohort")
        if request.artifact_paths:
            raise ValueError("declaration provider does not consume execution artifacts")
        identity = self.identity()
        try:
            collection = collect_publication_links(
                request.repository_root, request.scope.source_revision
            )
            report = collection.to_payload()
            lifecycle = report["source_lifecycle"]
            if any(v is not None and not isinstance(v, str) for v in lifecycle.values()):
                raise ValueError("source lifecycle values must be text or null")
        except (
            ValueError,
            TypeError,
            OSError,
            subprocess.CalledProcessError,
            yaml.YAMLError,
        ) as error:
            # Required-source failure is explicit incomplete evidence, never an
            # apparently complete empty atom inventory or a successful test.
            node = NodeEvidence(
                "SG-SPEC-0071",
                (),
                (),
                False,
                False,
                (EvidenceDiagnostic("publication_source_unavailable", message=str(error)),),
            )
            return ProviderEvidence(identity, request.scope, (node,), ())
        if (
            report["source_revision"] != request.scope.source_revision
            or report["spec_id"] != "SG-SPEC-0071"
        ):
            raise ValueError("publication collection does not match the selected scope")
        node = NodeEvidence(
            report["spec_id"],
            collection.atom_declarations,
            collection.resolutions,
            report["atom_inventory"]["complete"],
            RESOLUTION_COMPLETENESS_SPEC.is_satisfied_by(
                ResolutionCompletenessFacts(frozenset(r.status for r in collection.resolutions))
            ),
            tuple(EvidenceDiagnostic(**item) for item in report["findings"])
            + tuple(
                EvidenceDiagnostic("duplicate_id", owner=item["id"], message=item["kind"])
                for item in report["duplicate_ids"]
            ),
            report["source_lifecycle"]["status"],
            report["source_lifecycle"]["gate_state"],
        )
        sources = tuple(
            SourceEvidence(path=path, **value) for path, value in report["sources"].items()
        )
        return ProviderEvidence(identity, request.scope, (node,), sources, report["content_sha256"])
