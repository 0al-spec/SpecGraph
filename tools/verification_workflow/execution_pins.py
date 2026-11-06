"""Resolve and recheck source, native passport, template and installed-tool pins."""

from dataclasses import asdict, replace
from pathlib import Path

from intent_decision_review.sources import digest, strict_json
from traceability.criterion_inputs import (
    checked_hash,
    parse_inventory,
    parse_plan,
    pinned_blob,
    sha256,
)
from traceability.criterion_passport import PassportValidation, native_document, scenario_binding
from traceability.criterion_provider import PROVIDER_ID, PROVIDER_VERSION

from .execution_model import ProducerAdapter
from .model import (
    CriterionTarget,
    ExpectedMeasurement,
    FilePin,
    Operation,
    OperationRegistry,
    PassportPin,
    Stage,
    ToolPin,
    VerificationRequest,
    VerificationScope,
    WorkflowDefinition,
    WorkflowStep,
)
from .profile_spec import SIGNATURES


def runtime_registry(adapter: ProducerAdapter) -> OperationRegistry:
    root = Path(__file__).resolve().parent
    tools = root.parent
    sources = (
        *root.glob("*.py"),
        *(tools / "traceability").glob("*.py"),
        tools / "criterion_observation_report.py",
    )
    fingerprint = digest({str(p.relative_to(tools)): sha256(p.read_bytes()) for p in sources})
    if sha256(adapter.implementation.read_bytes()) != adapter.identity.sha256:
        raise ValueError("reviewed producer implementation pin mismatch")
    pins = {
        Stage.PIN: ToolPin("verification.snapshot", "1", fingerprint),
        Stage.EXECUTE: adapter.identity,
        Stage.COLLECT: ToolPin(PROVIDER_ID, PROVIDER_VERSION, fingerprint),
        Stage.REPORT: ToolPin("verification.report", "1", fingerprint),
    }
    return OperationRegistry(
        "verification.execution/v1",
        tuple(
            Operation(stage.value, "1", stage, source, target, pins[stage], effects)
            for stage, source, target, _, effects in SIGNATURES
        ),
    )


def scope_locator(scope: VerificationScope) -> dict:
    return dict(
        workspace=scope.workspace,
        repository=scope.repository_id,
        node_id=scope.spec_id,
        revision=scope.declaration_revision,
        **asdict(scope.spec),
    )


def targets(
    repository: Path, scope: VerificationScope, template: bytes
) -> tuple[CriterionTarget, ...]:
    raw = pinned_blob(repository, scope.declaration_revision, scope.spec.path)
    checked_hash(raw, scope.spec)
    inventory = parse_inventory(raw, scope.spec_id, scope.declaration_revision, scope.spec.path)
    plan = parse_plan(
        template, scope=scope_locator(scope), passport_sha256=scope.passport.artifact.sha256
    )
    if len(plan.journals) != 1 or len(plan.bindings) != len(inventory.sources):
        raise ValueError("execution v1 requires one journal and one binding per criterion")
    bindings = {b.pointer: b for b in plan.bindings}
    if set(bindings) != {source.pointer for source in inventory.sources}:
        raise ValueError("template must bind the entire pinned inventory")
    return tuple(
        CriterionTarget(
            source,
            bindings[source.pointer].criterion_id,
            bindings[source.pointer].contract_ref_id,
            bindings[source.pointer].passport_binding_id,
            tuple(
                ExpectedMeasurement(a.id, a.media_type, a.expected_json)
                for a in bindings[source.pointer].assertions
            ),
        )
        for source in inventory.sources
    )


def prepare_request(
    repository: Path,
    *,
    request_id: str,
    workspace: str,
    repository_id: str,
    spec_id: str,
    declaration_revision: str,
    execution_revision: str,
    test_revision: str,
    spec_path: str,
    passport_path: str,
    template_path: str,
    adapter: ProducerAdapter,
    validator: PassportValidation,
) -> VerificationRequest:
    """Read-only convenience preparation; execute_verification rechecks every pin."""
    spec = pinned_blob(repository, declaration_revision, spec_path)
    passport = pinned_blob(repository, execution_revision, passport_path)
    template = pinned_blob(repository, execution_revision, template_path)
    _, identity = native_document(passport, validator)
    scope = VerificationScope(
        workspace,
        repository_id,
        spec_id,
        declaration_revision,
        execution_revision,
        test_revision,
        FilePin(spec_path, sha256(spec)),
        PassportPin(FilePin(passport_path, sha256(passport)), identity),
        FilePin(template_path, sha256(template)),
        (),
    )
    scope = replace(scope, criteria=targets(repository, scope, template))
    definition = WorkflowDefinition(
        "verify-criteria/v1",
        tuple(
            WorkflowStep(stage, stage.value, "1", parent) for stage, _, _, parent, _ in SIGNATURES
        ),
    )
    return VerificationRequest(request_id, scope, definition, runtime_registry(adapter))


def verify_inputs(
    repository: Path,
    request: VerificationRequest,
    adapter: ProducerAdapter,
    validator: PassportValidation,
) -> tuple[bytes, bytes]:
    scope = request.scope
    if runtime_registry(adapter) != request.registry:
        raise ValueError("selected runtime or producer implementation changed")
    passport = pinned_blob(repository, scope.execution_revision, scope.passport.artifact.path)
    template = pinned_blob(repository, scope.execution_revision, scope.binding_template.path)
    checked_hash(passport, scope.passport.artifact)
    checked_hash(template, scope.binding_template)
    document, identity = native_document(passport, validator)
    if (
        identity != scope.passport.identity
        or targets(repository, scope, template) != scope.criteria
    ):
        raise ValueError("passport identity or complete criterion inventory changed")
    checked_hash(pinned_blob(repository, scope.execution_revision, scope.spec.path), scope.spec)
    plan = parse_plan(
        template, scope=scope_locator(scope), passport_sha256=scope.passport.artifact.sha256
    )
    for journal in plan.journals:
        for revision in (scope.test_revision, scope.execution_revision):
            checked_hash(pinned_blob(repository, revision, journal.feature.path), journal.feature)
    sources = {target.source.pointer: target.source for target in scope.criteria}
    for binding in plan.bindings:
        scenario_binding(document, sources[binding.pointer], binding, scope_locator(scope))
    # Reject reserved run paths before publishing any copied passport bytes.
    if Path(scope.passport.artifact.path).parts[0] in {
        ".verification",
        "snapshot",
        "producer",
        "terminal.json",
        ".terminal.tmp",
    }:
        raise ValueError("passport path conflicts with the execution namespace")
    strict_json(template)
    return passport, template
