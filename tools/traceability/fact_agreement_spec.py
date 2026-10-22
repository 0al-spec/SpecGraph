"""RFC 0226: distinct observations remain conflicting, without choosing a winner."""

from specification_core import PredicateSpec

from .evidence import AgreementFacts

FACT_AGREEMENT_SPEC: PredicateSpec[AgreementFacts] = PredicateSpec(
    lambda c: len(c.values) <= 1,
    name="trace.provider_facts_agree",
)
