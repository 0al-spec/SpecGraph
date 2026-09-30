"""SpecificationCore rules for candidate approval decision state."""

from specification_core import FirstMatch, PredicateSpec, TraceRecorder

from idea_maturity_candidate_approval_intent_spec import candidate_approval_intent_state
from idea_maturity_lifecycle_context import LifecycleStateContext, decide


def _state(c):
    summary = c.summary("candidate_approval_decision")
    decision = c.mapping(c.artifact("candidate_approval_decision").get("decision"))
    return c.text(summary.get("effective_state")) or c.text(decision.get("state"))


def _status(c):
    artifact = c.artifact("candidate_approval_decision")
    summary = c.summary("candidate_approval_decision")
    readiness = c.mapping(artifact.get("readiness"))
    return (
        c.text(summary.get("status"))
        or c.text(readiness.get("review_state"))
        or c.text(artifact.get("status"))
    )


def _exec_status(c):
    return c.text(c.summary("approval_execution").get("status")) or c.text(
        c.artifact("approval_execution").get("status")
    )


def _has_decision(c):
    return bool(c.artifact("candidate_approval_decision"))


def _has_execution(c):
    return bool(c.artifact("approval_execution"))


def _has_decision_reference(c):
    reference = c.artifact("approval_execution").get("candidate_approval_decision_ref")
    return bool(c.mapping(reference))


_SPEC = FirstMatch.with_fallback(
    (
        (
            PredicateSpec(
                lambda c: (
                    _has_decision(c)
                    and _state(c) == "approved"
                    and c.artifact("candidate_approval_decision").get("readiness", {}).get("ready")
                    is True
                ),
                name="approval_decision.approved_ready",
            ),
            "materialized",
        ),
        (
            PredicateSpec(
                lambda c: (
                    _has_decision(c)
                    and (
                        c.artifact("candidate_approval_decision").get("dry_run") is True
                        or _status(c) == "dry_run"
                    )
                ),
                name="approval_decision.dry_run",
            ),
            "dry_run",
        ),
        (
            PredicateSpec(
                lambda c: _has_decision(c) and c.is_failed(_status(c)),
                name="approval_decision.failed",
            ),
            "failed",
        ),
        (
            PredicateSpec(
                lambda c: (
                    _has_decision(c)
                    and (
                        c.is_blocked(_status(c))
                        or _state(c) in {"rejected", "needs_context", "superseded"}
                    )
                ),
                name="approval_decision.blocked",
            ),
            "blocked",
        ),
        (PredicateSpec(lambda c: _has_decision(c), name="approval_decision.unknown"), "unknown"),
        (
            PredicateSpec(
                lambda c: (
                    _has_execution(c)
                    and (
                        _has_decision_reference(c)
                        or c.summary("approval_execution").get("decision_written") is True
                    )
                ),
                name="approval_execution.materialized",
            ),
            "materialized",
        ),
        (
            PredicateSpec(
                lambda c: (
                    _has_execution(c) and c.artifact("approval_execution").get("dry_run") is True
                ),
                name="approval_execution.dry_run",
            ),
            "dry_run",
        ),
        (
            PredicateSpec(
                lambda c: _has_execution(c) and "failed" in _exec_status(c),
                name="approval_execution.failed",
            ),
            "failed",
        ),
        (
            PredicateSpec(
                lambda c: _has_execution(c) and "blocked" in _exec_status(c),
                name="approval_execution.blocked",
            ),
            "blocked",
        ),
        (PredicateSpec(lambda c: _has_execution(c), name="approval_execution.unknown"), "unknown"),
        (
            PredicateSpec(
                lambda c: candidate_approval_intent_state(c) in {"requested", "ready"},
                name="approval_decision.not_available",
            ),
            "not_available",
        ),
    ),
    "not_reached",
    name="candidate_approval_decision_state",
)


def candidate_approval_decision_state(
    context: LifecycleStateContext, *, recorder: TraceRecorder | None = None
) -> str:
    return decide(_SPEC, context, recorder)
