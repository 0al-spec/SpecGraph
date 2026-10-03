"""SG-SPEC-0070 / node-local exact IDs and duplicate prerequisites."""

from dataclasses import replace

from .context import BDDContext
from .policy import BDDPolicy, entry_skip, issue


class BDDScenarioIDsSpec(BDDPolicy):
    rule_ref = "SG-RFC-0223.native.node-local-ids"

    def skip_reason(self, context: BDDContext) -> str | None:
        return (
            super().skip_reason(context)
            or entry_skip(context)
            or (None if context.valid_ids else "invalid_id_values")
        )

    def findings(self, context: BDDContext):
        seen = set()
        findings = []
        for index, entry in enumerate(context.entries):
            if entry.id.value in seen:
                findings.append(
                    issue("duplicate_scenario_id", f"specification.bdd_scenarios[{index}].id")
                )
            seen.add(entry.id.value)
        return tuple(findings)

    def transition(self, context, findings):
        return replace(context, duplicate_ids=bool(findings))
