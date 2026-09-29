"""SpecificationCore rules for candidate approval state."""

from specification_core import FirstMatch, PredicateSpec, TraceRecorder

from idea_maturity_lifecycle_context import LifecycleStateContext, decide

_SPEC = FirstMatch.with_fallback(
    (
        (
            PredicateSpec(
                lambda c: (
                    c.mapping(c.artifact("repaired_repair_session").get("readiness_impact")).get(
                        "ready_for_candidate_approval"
                    )
                    is True
                    or c.summary("repaired_repair_session").get("ready_for_candidate_approval")
                    is True
                    or c.summary("repaired_handoff").get("ready_for_candidate_approval") is True
                ),
                name="candidate_approval.ready",
            ),
            "ready",
        ),
        (
            PredicateSpec(
                lambda c: (
                    c.has_content("repaired_repair_session") or c.has_content("repaired_handoff")
                ),
                name="candidate_approval.repair_blocked",
            ),
            "blocked",
        ),
        (
            PredicateSpec(
                lambda c: c.has_content("candidate_graph"),
                name="candidate_approval.candidate_exists",
            ),
            "not_reached",
        ),
    ),
    "not_available",
    name="candidate_approval_state",
)


def candidate_approval_state(
    context: LifecycleStateContext, *, recorder: TraceRecorder | None = None
) -> str:
    return decide(_SPEC, context, recorder)
