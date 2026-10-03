"""SG-SPEC-0070 / BDD-NATIVE-UNKNOWN-PROFILE."""

from dataclasses import replace

from .context import BDDContext
from .policy import BDDPolicy, issue


class BDDProfileSelectionSpec(BDDPolicy):
    rule_ref = "SG-RFC-0223.native.profile-selection"

    def skip_reason(self, context: BDDContext) -> str | None:
        return None

    def findings(self, context: BDDContext):
        return (
            ()
            if context.profile == "bdd_scenarios_v1"
            else (issue("unsupported_profile", "profile"),)
        )

    def transition(self, context, findings):
        return replace(context, trace_profile="unsupported" if findings else context.profile)
