"""Accumulate all eligible SpecificationCore policies in contract order."""

from specification_core import TraceRecorder

from .context import BDDContext, BDDResult, BDDScenario, BDDScenarioPresence, PolicyOutcome
from .fields_spec import BDDScenarioFieldsSpec
from .ids_spec import BDDScenarioIDsSpec
from .presence_spec import BDDContainerPresenceSpec
from .profile_spec import BDDProfileSelectionSpec
from .references_spec import BDDScenarioReferencesSpec
from .values_spec import BDDScenarioValuesSpec

POLICIES = (
    BDDProfileSelectionSpec(),
    BDDContainerPresenceSpec(),
    BDDScenarioFieldsSpec(),
    BDDScenarioValuesSpec(),
    BDDScenarioIDsSpec(),
    BDDScenarioReferencesSpec(),
)


def evaluate(
    context: BDDContext, source_sha256: str, *, recorder: TraceRecorder | None = None
) -> BDDResult:
    findings = []
    outcomes = []
    for policy in POLICIES:
        skip = policy.skip_reason(context)
        if skip:
            if recorder is not None:
                recorder.skipped(policy.rule_ref)
            outcomes.append(PolicyOutcome(policy.rule_ref, "skipped", skip))
            continue
        passed = policy.is_satisfied_by(context, recorder=recorder)
        current_findings = policy.findings(context)
        findings.extend(current_findings)
        outcomes.append(PolicyOutcome(policy.rule_ref, "satisfied" if passed else "unsatisfied"))
        context = policy.transition(context, current_findings)
    presence = BDDScenarioPresence.INVALID if findings else context.presence
    scenarios = (
        ()
        if findings
        else tuple(
            BDDScenario(e.id.value, e.title.value, tuple(step.value for step in e.steps))
            for e in context.entries
        )
    )
    skips = (
        ()
        if POLICIES[3].skip_reason(context)
        else tuple((i, "invalid_entry") for i, e in enumerate(context.entries) if not e.is_mapping)
    )
    return BDDResult(
        context.profile,
        presence,
        tuple(findings),
        tuple(outcomes),
        scenarios,
        source_sha256,
        context.trace_profile,
        skips,
    )
