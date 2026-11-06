"""The selected passport declaration must explicitly bind this criterion and test."""

from specification_core import PredicateSpec

from .criterion import PassportBindingFacts

CRITERION_PASSPORT_BINDING_SPEC = PredicateSpec[PassportBindingFacts](
    lambda c: (
        c.selected_text == c.passport_text
        and (c.provider, c.relation) == ("specgraph", "implements")
        and c.selected_locator == c.passport_locator
        and c.criterion_id in c.declared_criteria
        and c.contract_ref_id in c.declared_contracts
        and bool(c.test_elements)
    ),
    name="criterion.exact_passport_binding",
)
