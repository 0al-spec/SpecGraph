"""Policy for passing through a clean, no-op repaired candidate handoff."""

from specification_core import PredicateSpec

from repaired_handoff_context import RepairedHandoffContext


def _is_clean_pre_sib_noop_passthrough(context: RepairedHandoffContext) -> bool:
    return (
        context.pre_sib_ready
        and not context.repair_loop_ready
        and not context.has_findings
        and context.applied_action_count == 0
        and context.context_required_count == 0
    )


CLEAN_PRE_SIB_NOOP_PASSTHROUGH = PredicateSpec(
    _is_clean_pre_sib_noop_passthrough,
    name="repaired_handoff.clean_pre_sib_noop_passthrough",
)
