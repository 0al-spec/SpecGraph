"""SG-SPEC-0070 / BDD-NATIVE-EXACT-STEPS, TIMESTAMP, COMBINED-ERROR."""

from .context import BDDContext
from .policy import BDDPolicy, entry_skip, issue


class BDDScenarioValuesSpec(BDDPolicy):
    rule_ref = "SG-RFC-0223.native.scenario-values"

    def skip_reason(self, context: BDDContext) -> str | None:
        return super().skip_reason(context) or entry_skip(context)

    def findings(self, context: BDDContext):
        findings = []
        for index, entry in enumerate(context.entries):
            if not entry.is_mapping:
                continue
            path = f"specification.bdd_scenarios[{index}]"
            if not entry.id.valid:
                findings.append(issue("invalid_value", path + ".id"))
            if not entry.steps_is_list or not entry.steps:
                findings.append(issue("invalid_value", path + ".steps"))
            else:
                findings.extend(
                    issue("invalid_value", f"{path}.steps[{i}]")
                    for i, step in enumerate(entry.steps)
                    if not step.valid
                )
        return tuple(findings)
