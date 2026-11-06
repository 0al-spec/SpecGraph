"""Collect one pinned specification's retained criterion observations."""

import subprocess
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

from intent_decision_review.sources import digest

from .criterion import (
    AttemptObservation,
    CriterionBinding,
    CriterionDecisionFacts,
    CriterionEvidence,
    CriterionFinding,
    CriterionRow,
    CriterionSource,
    FilePin,
    JournalDeclaration,
)
from .criterion_binding_integrity_spec import CRITERION_BINDING_INTEGRITY_SPEC
from .criterion_inputs import (
    PROFILE,
    BindingPlan,
    CriterionInventory,
    checked_hash,
    parse_inventory,
    parse_plan,
    pinned_blob,
    read_pin,
    sha256,
)
from .criterion_observation_outcome_spec import CRITERION_OBSERVATION_OUTCOME_SPEC
from .criterion_passport import PassportValidation, native_document, scenario_binding
from .cucumber_messages import CucumberMessages, JournalFinding
from .evidence import (
    EvidenceRequest,
    NodeEvidence,
    ProviderEvidence,
    ProviderIdentity,
    SourceEvidence,
)

PROVIDER_ID = "criterion.retained_cucumber"
PROVIDER_VERSION = "1.0.0"
PROVIDER_SOURCES = (
    "criterion.py",
    "criterion_binding_integrity_spec.py",
    "criterion_inputs.py",
    "criterion_observation_outcome_spec.py",
    "criterion_passport.py",
    "criterion_passport_binding_spec.py",
    "criterion_provider.py",
    "cucumber_messages.py",
    "fact_agreement_spec.py",
)
INPUT_ERRORS = (OSError, ValueError, yaml.YAMLError, subprocess.SubprocessError, RecursionError)


@dataclass(frozen=True)
class RetainedCriterionEvidenceProvider:
    validator: PassportValidation
    provider_id = PROVIDER_ID
    version = PROVIDER_VERSION

    def collect(self, request: EvidenceRequest) -> ProviderEvidence:
        if (
            request.criterion_selection is None
            or request.execution_selection is not None
            or request.artifact_paths
            or request.scope.resolver_profile != PROFILE
            or len(request.scope.spec_ids) != 1
        ):
            raise ValueError(
                "criterion provider requires the explicit one-spec criterion selection"
            )
        collector = CriterionCollection(request, self.validator)
        criterion, inventory, sources = collector.collect()
        spec_id = request.scope.spec_ids[0]
        root = Path(__file__).resolve().parent
        return ProviderEvidence(
            ProviderIdentity(
                self.provider_id,
                self.version,
                PROFILE,
                tuple(
                    (f"tools/traceability/{path}", sha256((root / path).read_bytes()))
                    for path in PROVIDER_SOURCES
                ),
            ),
            request.scope,
            (
                NodeEvidence(
                    spec_id,
                    (),
                    (),
                    False,
                    False,
                    source_status=inventory.status,
                    source_gate=inventory.gate_state,
                ),
            ),
            sources,
            collection_digest=digest(criterion.to_payload()),
            criterion=criterion,
        )


class CriterionCollection:
    """Run-local collection over explicitly selected immutable inputs."""

    def __init__(self, request: EvidenceRequest, validator: PassportValidation):
        self.request = request
        self.selection = request.criterion_selection
        self.validator = validator
        self.scope = dict(
            workspace=self.selection.workspace,
            repository=request.scope.repository_id,
            node_id=request.scope.spec_ids[0],
            revision=request.scope.source_revision,
            **asdict(self.selection.spec),
        )
        self.journal_pins = dict(self.selection.journals)
        self.sources: dict[str, SourceEvidence] = {}
        self.journals: dict[JournalDeclaration, tuple[CucumberMessages, str] | Exception] = {}

    def collect(self) -> tuple[CriterionEvidence, CriterionInventory, tuple[SourceEvidence, ...]]:
        selection = self.selection
        findings = []
        inventory = CriterionInventory((), None, None)
        inventory_complete = False
        passport = passport_identity = None
        plan = BindingPlan((), ())
        try:
            raw = pinned_blob(
                self.request.repository_root, self.scope["revision"], selection.spec.path
            )
            inventory = parse_inventory(
                raw, self.scope["node_id"], self.scope["revision"], selection.spec.path
            )
            checked_hash(raw, selection.spec)
            inventory_complete = True
            self.sources["spec"] = SourceEvidence(
                selection.spec.path, "checked", selection.spec.sha256
            )
        except INPUT_ERRORS as error:
            findings.append(input_finding("spec_input", error))
        try:
            raw = self.retained("passport", selection.passport)
            passport, passport_identity = native_document(raw, self.validator)
        except INPUT_ERRORS as error:
            findings.append(input_finding("passport_input", error))
        try:
            raw = self.retained("binding_plan", selection.plan)
            plan = parse_plan(raw, scope=self.scope, passport_sha256=selection.passport.sha256)
        except INPUT_ERRORS as error:
            findings.append(input_finding("binding_plan_input", error))

        bindings = {}
        for binding in plan.bindings:
            bindings.setdefault(binding.pointer, []).append(binding)
        journals = {}
        for journal in plan.journals:
            journals.setdefault(journal.artifact_id, []).append(journal)
        foreign = bindings.keys() - {source.pointer for source in inventory.sources}
        if inventory_complete and foreign:
            findings.append(
                CriterionFinding("invalid", "unknown_plan_pointer", ", ".join(sorted(foreign)))
            )
        # Reusing one passport criterion at distinct spec pointers is ambiguous.
        criterion_pointers = Counter(
            criterion for criterion, _ in {(b.criterion_id, b.pointer) for b in plan.bindings}
        )
        repeated_ids = {criterion for criterion, count in criterion_pointers.items() if count > 1}
        rows = tuple(
            self.row(
                source,
                tuple(bindings.get(source.pointer, ())),
                passport,
                journals,
                repeated_ids,
                tuple(findings),
            )
            for source in inventory.sources
        )
        evidence = CriterionEvidence(
            selection,
            inventory_complete,
            rows,
            passport_identity,
            tuple(sorted(findings)),
            plan.journals,
            tuple(binding for binding in plan.bindings if binding.pointer in foreign),
        )
        return evidence, inventory, tuple(self.sources.values())

    def retained(self, role: str, pin: FilePin) -> bytes:
        raw = read_pin(self.selection.retained_root, pin)
        self.sources[role] = SourceEvidence(pin.path, "checked", pin.sha256)
        return raw

    def journal(self, declaration: JournalDeclaration) -> tuple[CucumberMessages, str]:
        if declaration not in self.journals:
            try:
                journal = self.read_journal(declaration)
            except INPUT_ERRORS as error:
                journal = error
            self.journals[declaration] = journal
        loaded = self.journals[declaration]
        if isinstance(loaded, Exception):
            raise loaded
        return loaded

    def read_journal(self, declaration: JournalDeclaration) -> tuple[CucumberMessages, str]:
        pin = self.journal_pins.get(declaration.artifact_id)
        if pin is None:
            raise FileNotFoundError(f"no retained path selected for {declaration.artifact_id}")
        if declaration.sha256 != pin.sha256:
            raise ValueError(
                "journal fingerprint differs between the plan and the explicit selection"
            )
        raw = self.retained(f"journal:{declaration.artifact_id}", pin)
        root = self.request.repository_root
        feature = declaration.feature
        checked_hash(pinned_blob(root, declaration.test_source_revision, feature.path), feature)
        feature_raw = pinned_blob(root, declaration.execution_source_revision, feature.path)
        checked_hash(feature_raw, feature)
        checked_hash(
            pinned_blob(root, declaration.execution_source_revision, self.selection.spec.path),
            self.selection.spec,
        )
        return CucumberMessages.parse(raw), feature_raw.decode()

    def row(
        self,
        source: CriterionSource,
        bindings: tuple[CriterionBinding, ...],
        passport: dict | None,
        journals: dict[str, list[JournalDeclaration]],
        repeated_ids: set[str],
        global_findings: tuple[CriterionFinding, ...],
    ) -> CriterionRow:
        findings = list(global_findings)
        journal = None
        observation = None
        if len(bindings) > 1 or any(b.criterion_id in repeated_ids for b in bindings):
            findings.append(
                CriterionFinding("conflict", "criterion_bindings_disagree", source.pointer)
            )
        elif bindings and passport is not None and not findings:
            binding = bindings[0]
            try:
                scenario = scenario_binding(passport, source, binding, self.scope)
                candidates = journals.get(binding.artifact_id, ())
                if len(candidates) > 1:
                    raise JournalFinding(
                        "conflict", "journal_declarations_disagree", binding.artifact_id
                    )
                if not candidates:
                    raise ValueError("binding refers to an undeclared journal ID")
                journal = candidates[0]
                messages, feature = self.journal(journal)
                observation = messages.observe(journal, binding, scenario, feature)
                findings.extend(observation.findings)
            except JournalFinding as error:
                findings.append(error.finding)
            except INPUT_ERRORS as error:
                findings.append(input_finding("binding_input", error))
        return criterion_row(source, bindings, findings, journal, observation)


def input_finding(code: str, error: Exception) -> CriterionFinding:
    return CriterionFinding(
        "unavailable" if isinstance(error, (OSError, subprocess.TimeoutExpired)) else "invalid",
        code,
        str(error),
    )


def criterion_row(
    source: CriterionSource,
    bindings: tuple[CriterionBinding, ...],
    findings: list[CriterionFinding],
    journal: JournalDeclaration | None,
    observation: AttemptObservation | None,
) -> CriterionRow:
    steps = observation.steps if observation else ()
    facts = CriterionDecisionFacts(
        bool(bindings),
        frozenset(f.kind for f in findings),
        observation.run_success if observation else None,
        observation.case_finished if observation else False,
        frozenset(status for _, status in observation.case_step_statuses)
        if observation
        else frozenset(),
        bool(steps) and all(s.measurement_json is not None for s in steps),
        any(
            s.measurement_json is not None and s.measurement_json != s.assertion.expected_json
            for s in steps
        ),
    )
    return CriterionRow(
        source,
        bindings,
        CRITERION_BINDING_INTEGRITY_SPEC.decide(facts).value,
        CRITERION_OBSERVATION_OUTCOME_SPEC.decide(facts).value,
        tuple(sorted(set(findings))),
        journal,
        observation,
    )
