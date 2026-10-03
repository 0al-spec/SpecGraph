"""SG-SPEC-0070 / BDD-NATIVE-UNKNOWN-FIELD and COMBINED-ERROR."""

from .context import BDDContext
from .policy import BDDPolicy, entry_skip, issue


class BDDScenarioFieldsSpec(BDDPolicy):
    rule_ref = "SG-RFC-0223.native.scenario-fields"

    def skip_reason(self, context: BDDContext) -> str | None:
        return super().skip_reason(context) or entry_skip(context)

    def findings(self, context: BDDContext):
        findings = []
        for index, entry in enumerate(context.entries):
            path = f"specification.bdd_scenarios[{index}]"
            if not entry.is_mapping:
                findings.append(issue("invalid_entry", path))
                continue
            if entry.title_supplied and not entry.title.valid:
                findings.append(issue("invalid_value", path + ".scenario"))
            findings.extend(
                issue("unsupported_field", path + "." + key) for key in entry.unknown_fields
            )
        return tuple(findings)
