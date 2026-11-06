"""Require one exact, FeaturePassport-bound inventory before accepting stage facts."""

import re

from specification_core import PredicateSpec

from .model import VerificationScope


def pinned_scope(scope: VerificationScope) -> bool:
    passport = scope.passport.identity
    if not all(
        (
            scope.workspace,
            scope.repository_id,
            scope.spec_id,
            passport.passport_id,
            passport.feature_id,
            passport.version,
            passport.status,
        )
    ):
        return False
    if any(
        not re.fullmatch(r"[0-9a-f]{64}", value)
        for value in (
            passport.validator_sha256,
            passport.schema_sha256,
        )
    ) or not re.fullmatch(r"(?:[0-9a-f]{40}|[0-9a-f]{64})", passport.validator_contract_revision):
        return False
    ids = [target.criterion_id for target in scope.criteria]
    pointers = [target.source.pointer for target in scope.criteria]
    if len(set(ids)) != len(ids) or pointers != [f"/acceptance/{i}" for i in range(len(ids))]:
        return False
    for target in scope.criteria:
        assertion_ids = [e.assertion_id for e in target.expectations]
        if (
            not all((target.criterion_id, target.contract_ref_id, target.passport_binding_id))
            or not assertion_ids
            or len(set(assertion_ids)) != len(assertion_ids)
            or (target.source.path, target.source.sha256, target.source.revision)
            != (scope.spec.path, scope.spec.sha256, scope.declaration_revision)
        ):
            return False
    return True


PINNED_SCOPE_SPEC: PredicateSpec[VerificationScope] = PredicateSpec(
    pinned_scope,
    name="verification.feature_passport_scope",
)
