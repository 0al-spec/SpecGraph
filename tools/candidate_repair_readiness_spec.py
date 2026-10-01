"""SpecificationCore policy for candidate repair-preview readiness."""

from dataclasses import dataclass

from specification_core import PredicateSpec, TraceRecorder

from candidate_repair_readiness_context import CandidateRepairReadinessContext


def _is_noop_repair_loop(context: CandidateRepairReadinessContext) -> bool:
    return context.pre_sib_ready and context.action_count == 0


def _is_preview_ready(context: CandidateRepairReadinessContext) -> bool:
    return not context.has_findings and (
        context.applied_action_count > 0 or _is_noop_repair_loop(context)
    )


_SPEC = PredicateSpec(_is_preview_ready, name="candidate_repair.preview_ready")


@dataclass(frozen=True)
class CandidateRepairReadiness:
    ready: bool
    no_op_repair_loop: bool

    @property
    def status(self) -> str:
        return "repair_preview_ready" if self.ready else "repair_review_required"


def candidate_repair_readiness(
    context: CandidateRepairReadinessContext,
    *,
    recorder: TraceRecorder | None = None,
) -> CandidateRepairReadiness:
    return CandidateRepairReadiness(
        ready=_SPEC.is_satisfied_by(context, recorder=recorder),
        no_op_repair_loop=_is_noop_repair_loop(context),
    )
