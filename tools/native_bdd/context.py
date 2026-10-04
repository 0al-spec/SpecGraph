"""Immutable original-type facts for SG-SPEC-0070 native BDD policies."""

from dataclasses import dataclass
from enum import Enum


class BDDScenarioPresence(str, Enum):
    ABSENT = "absent"
    EMPTY = "explicit_empty"
    PRESENT = "present"
    INVALID = "invalid"


@dataclass(frozen=True)
class TextInput:
    value: str | None

    @property
    def valid(self) -> bool:
        return self.value is not None and bool(self.value.strip())


@dataclass(frozen=True)
class ScenarioInput:
    is_mapping: bool
    id: TextInput
    title_supplied: bool
    title: TextInput
    steps_is_list: bool
    steps: tuple[TextInput, ...]
    unknown_fields: tuple[str, ...]


@dataclass(frozen=True)
class ReferenceInput:
    value: TextInput
    path: str


@dataclass(frozen=True)
class BDDContext:
    profile: str
    native_supplied: bool
    alternate_supplied: bool
    native_is_list: bool
    entries: tuple[ScenarioInput, ...]
    references: tuple[ReferenceInput, ...]
    malformed_reference_paths: tuple[str, ...] = ()
    presence: BDDScenarioPresence = BDDScenarioPresence.INVALID
    duplicate_ids: bool = False
    trace_profile: str = "unsupported"

    @property
    def valid_ids(self) -> bool:
        return all(e.is_mapping and e.id.valid for e in self.entries)


@dataclass(frozen=True)
class BDDScenarioFinding:
    code: str
    path: str
    message: str
    severity: str = "error"


@dataclass(frozen=True)
class PolicyOutcome:
    rule_ref: str
    outcome: str
    skip_reason: str | None = None


@dataclass(frozen=True)
class BDDScenario:
    id: str
    title: str | None
    steps: tuple[str, ...]


@dataclass(frozen=True)
class BDDResult:
    profile: str
    presence: BDDScenarioPresence
    findings: tuple[BDDScenarioFinding, ...]
    policies: tuple[PolicyOutcome, ...]
    scenarios: tuple[BDDScenario, ...]
    source_sha256: str
    trace_profile: str = "unsupported"
    entry_skips: tuple[tuple[int, str], ...] = ()
    canonical_mutations_allowed: bool = False
    code_mutations_allowed: bool = False
    evidence_status: str = "not_evaluated"

    @property
    def extracted_count(self) -> int | None:
        return None if self.presence is BDDScenarioPresence.INVALID else len(self.scenarios)

    @property
    def events(self) -> tuple[dict, ...]:
        return (
            {
                "event": "bdd.declaration.classified",
                "profile": self.trace_profile,
                "presence": self.presence.value,
                "finding_codes": tuple(f.code for f in self.findings),
                "source_sha256": self.source_sha256,
            },
        ) + tuple(
            {
                "event": "bdd.policy.evaluated",
                "rule_ref": p.rule_ref,
                "outcome": p.outcome,
                "skip_reason": p.skip_reason,
            }
            for p in self.policies
        )
