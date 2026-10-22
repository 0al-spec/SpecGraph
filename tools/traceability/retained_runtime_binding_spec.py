"""Retained native HTTP provenance belongs to the selected report, run and source."""

from specification_core import PredicateSpec

from .execution import RetainedRuntimeBindingFacts
from .execution_binding_spec import EXECUTION_BINDING_SPEC

RETAINED_RUNTIME_BINDING_SPEC: PredicateSpec[RetainedRuntimeBindingFacts] = PredicateSpec(
    lambda c: (
        bool(c.expected_revision)
        and c.observed_revision == c.expected_revision
        and EXECUTION_BINDING_SPEC.is_satisfied_by(c.execution)
        and bool(c.expected_bundle[0] and c.expected_bundle[1])
        and c.observed_bundle == c.expected_bundle
        and bool(c.expected_origin)
        and c.observed_origin == c.expected_origin
    ),
    name="publication.retained_runtime_binding",
)
