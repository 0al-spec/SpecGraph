"""An identified binding can be checked independently of its outcome."""

from specification_core import FirstMatch, PredicateSpec

from .criterion import BindingIntegrity, CriterionDecisionFacts

CRITERION_BINDING_INTEGRITY_SPEC: FirstMatch[CriterionDecisionFacts, BindingIntegrity] = (
    FirstMatch.with_fallback(
        (
            (
                PredicateSpec(lambda c: "conflict" in c.findings, name="criterion.conflict"),
                "conflict",
            ),
            (PredicateSpec(lambda c: "invalid" in c.findings, name="criterion.invalid"), "invalid"),
            (
                PredicateSpec(lambda c: "unavailable" in c.findings, name="criterion.unavailable"),
                "unavailable",
            ),
            (PredicateSpec(lambda c: not c.has_binding, name="criterion.unbound"), "unbound"),
        ),
        "checked",
        name="criterion.binding_integrity",
    )
)
