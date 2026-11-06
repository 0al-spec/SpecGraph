"""Only the reviewed, mandatory four-stage topology is admissible in v1."""

from specification_core import PredicateSpec

from .model import Effect, Port, Stage, VerificationRequest

SIGNATURES = (
    (Stage.PIN, Port.REQUEST, Port.PINNED, None, frozenset({Effect.READ_SOURCE})),
    (
        Stage.EXECUTE,
        Port.PINNED,
        Port.EXECUTION,
        Stage.PIN,
        frozenset({Effect.READ_SOURCE, Effect.EXECUTE_TEST, Effect.WRITE_OUTPUT}),
    ),
    (
        Stage.COLLECT,
        Port.EXECUTION,
        Port.COLLECTION,
        Stage.EXECUTE,
        frozenset({Effect.READ_SOURCE, Effect.READ_OUTPUT, Effect.WRITE_OUTPUT}),
    ),
    (
        Stage.REPORT,
        Port.COLLECTION,
        Port.REPORT,
        Stage.COLLECT,
        frozenset({Effect.READ_OUTPUT, Effect.WRITE_OUTPUT}),
    ),
)


def fixed_profile(request: VerificationRequest) -> bool:
    definition, registry = request.definition, request.registry
    if definition.profile != "verify-criteria/v1" or not registry.version:
        return False
    operations = {op.identity: op for op in registry.operations}
    if len(operations) != len(registry.operations) or any(
        not op.identity or not op.version for op in registry.operations
    ):
        return False
    if len(definition.steps) != len(SIGNATURES):
        return False
    for step, (stage, source, target, parent, effects) in zip(
        definition.steps, SIGNATURES, strict=True
    ):
        op = operations.get(step.operation_id)
        if (
            op is None
            or not step.mandatory
            or step.stage != stage
            or step.input_from != parent
            or (op.stage, op.input_port, op.output_port) != (stage, source, target)
            or op.version != step.operation_version
            or op.effects != effects
        ):
            return False
    return True


FIXED_PROFILE_SPEC: PredicateSpec[VerificationRequest] = PredicateSpec(
    fixed_profile,
    name="verification.fixed_profile",
)
