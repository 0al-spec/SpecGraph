"""SG-SPEC-0070 / BDD-NATIVE-UNKNOWN-PROFILE."""

from dataclasses import replace

from .context import BDDContext
from .policy import BDDPolicy, issue


class BDDProfileSelectionSpec(BDDPolicy):
    rule_ref = "SG-RFC-0223.native.profile-selection"

    def skip_reason(self, context: BDDContext) -> str | None:
        return None

    def safe_trace_label(self, profile: str) -> str:
        return profile if profile == "bdd_scenarios_v1" else "unsupported"

    def findings(self, context: BDDContext):
        return (
            ()
            if self.safe_trace_label(context.profile) != "unsupported"
            else (issue("unsupported_profile", "profile"),)
        )

    def transition(self, context, findings):
        return replace(context, trace_profile=self.safe_trace_label(context.profile))
