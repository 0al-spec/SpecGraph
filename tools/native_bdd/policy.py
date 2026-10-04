"""SpecificationCore base; eligibility is part of each concrete domain policy."""

from specification_core import Specification, TraceRecorder

from .context import BDDContext, BDDScenarioFinding, BDDScenarioPresence


class BDDPolicy(Specification[BDDContext]):
    spec_id = "SG-SPEC-0070"
    rule_ref: str

    def __init__(self) -> None:
        super().__init__(name=self.rule_ref)
        self._seal()

    def findings(self, context: BDDContext) -> tuple[BDDScenarioFinding, ...]:
        raise NotImplementedError

    def skip_reason(self, context: BDDContext) -> str | None:
        if context.profile != "bdd_scenarios_v1":
            return "unsupported_profile"
        if context.presence is BDDScenarioPresence.INVALID:
            return "invalid_container"
        return None

    def transition(
        self, context: BDDContext, findings: tuple[BDDScenarioFinding, ...]
    ) -> BDDContext:
        return context

    def _evaluate(self, candidate: BDDContext, recorder: TraceRecorder | None) -> bool:
        return not self.findings(candidate)


def issue(code: str, path: str) -> BDDScenarioFinding:
    return BDDScenarioFinding(code, path, code.replace("_", " "))


def entry_skip(context: BDDContext) -> str | None:
    return "no_scenarios" if not context.entries else None
