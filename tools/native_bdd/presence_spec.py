"""SG-SPEC-0070 / BDD-NATIVE-ABSENT, EMPTY, ALTERNATE, AMBIGUOUS."""

from dataclasses import replace

from .context import BDDContext, BDDScenarioPresence
from .policy import BDDPolicy, issue


class BDDContainerPresenceSpec(BDDPolicy):
    rule_ref = "SG-RFC-0223.native.container-presence"

    def skip_reason(self, context: BDDContext) -> str | None:
        return "unsupported_profile" if context.profile != "bdd_scenarios_v1" else None

    def findings(self, context: BDDContext):
        if context.alternate_supplied:
            code = "ambiguous_container" if context.native_supplied else "unsupported_container"
            return (issue(code, "specification"),)
        if context.native_supplied and not context.native_is_list:
            return (issue("invalid_container_type", "specification.bdd_scenarios"),)
        return ()

    def presence(self, context: BDDContext) -> BDDScenarioPresence:
        if self.findings(context):
            return BDDScenarioPresence.INVALID
        if not context.native_supplied:
            return BDDScenarioPresence.ABSENT
        return BDDScenarioPresence.PRESENT if context.entries else BDDScenarioPresence.EMPTY

    def transition(self, context, findings):
        return replace(context, presence=self.presence(context))
