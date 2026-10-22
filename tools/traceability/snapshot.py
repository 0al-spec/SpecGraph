"""Pure assembly of provider facts; no collection, scoring, approval or I/O."""

from collections import defaultdict
from dataclasses import dataclass

from intent_decision_review.sources import digest, encoded

from .evidence import AgreementFacts, EvidenceConflict, EvidenceScope, ProviderEvidence
from .fact_agreement_spec import FACT_AGREEMENT_SPEC

SNAPSHOT_PROFILE = "specgraph.trace-snapshot/declarations-v1"


@dataclass(frozen=True)
class TraceSnapshot:
    scope: EvidenceScope
    reports: tuple[ProviderEvidence, ...]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "reports", tuple(sorted(self.reports, key=lambda r: r.identity.provider_id))
        )
        if not self.reports or len({r.identity.provider_id for r in self.reports}) != len(
            self.reports
        ):
            raise ValueError("snapshot requires distinct explicitly selected providers")
        if any(r.scope != self.scope for r in self.reports):
            raise ValueError("provider scope/revision does not match snapshot selection")

    @property
    def observed_subjects(self) -> tuple[tuple[str, str], ...]:
        return tuple(
            sorted(
                {(n.spec_id, a.reference) for r in self.reports for n in r.nodes for a in n.atoms}
            )
        )

    @property
    def conflicts(self) -> tuple[EvidenceConflict, ...]:
        groups = defaultdict(lambda: defaultdict(set))
        for report in self.reports:
            origin = report.identity.provider_id
            for node in report.nodes:
                for atom in node.atoms:
                    key = ("atom", node.spec_id, atom.reference)
                    groups[key][encoded(atom.to_payload())].add(origin)
                for link in node.links:
                    ref = link.declared
                    key = (
                        "link",
                        node.spec_id,
                        ref.owner,
                        ref.relation,
                        ref.target_kind,
                        ref.target,
                        ref.source_path,
                        ref.source_location,
                    )
                    groups[key][encoded(link.to_payload())].add(origin)
        return tuple(
            EvidenceConflict(
                key[0],
                key[1:],
                tuple(
                    (value, tuple(sorted(providers))) for value, providers in sorted(values.items())
                ),
            )
            for key, values in sorted(groups.items())
            if not FACT_AGREEMENT_SPEC.is_satisfied_by(AgreementFacts(frozenset(values)))
        )

    def to_payload(self) -> dict[str, object]:
        payload = {
            "artifact_kind": "trace_snapshot",
            "schema_version": 1,
            "profile": SNAPSHOT_PROFILE,
            "scope": self.scope.to_payload(),
            "reports": [r.to_payload() for r in self.reports],
            "observed_subjects": [dict(spec_id=s, atom_id=a) for s, a in self.observed_subjects],
            "observed_subject_count": len(self.observed_subjects),
            "conflicts": [c.to_payload() for c in self.conflicts],
            "execution": "not_collected",
            "fulfillment": "not_evaluated",
            "admission": "not_evaluated",
            "readiness": "not_evaluated",
            "canonical_mutations_allowed": False,
        }
        return {**payload, "content_sha256": digest(payload)}
