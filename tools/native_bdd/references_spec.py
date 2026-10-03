"""SG-SPEC-0070 / BDD-NATIVE-LOCAL-REFERENCE and TIMESTAMP."""

from .context import BDDContext
from .policy import BDDPolicy, issue


class BDDScenarioReferencesSpec(BDDPolicy):
    rule_ref = "SG-RFC-0223.native.node-local-references"

    def skip_reason(self, context: BDDContext) -> str | None:
        return (
            super().skip_reason(context)
            or (None if context.valid_ids else "invalid_id_values")
            or ("duplicate_scenario_ids" if context.duplicate_ids else None)
        )

    def findings(self, context: BDDContext):
        ids = {entry.id.value for entry in context.entries}
        findings = [issue("invalid_value", path) for path in context.malformed_reference_paths]
        for reference in context.references:
            if not reference.value.valid:
                findings.append(issue("invalid_value", reference.path))
            elif reference.value.value not in ids:
                findings.append(issue("unresolved_node_local_reference", reference.path))
        return tuple(findings)
